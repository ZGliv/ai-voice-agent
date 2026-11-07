"""Audio and WebSocket plumbing for Twilio Media Streams, in pure Python.

Twilio streams 8 kHz G.711 mu-law; Kyutai listens and Fish speaks at 24 kHz PCM16.
The companion venv has no numpy and Python 3.13+ removed audioop, so the codec,
resamplers and the small server-side WebSocket (RFC 6455) live here.
"""
import array, base64, hashlib, json, math, os, socket, ssl, struct, threading
from urllib.parse import urlparse

BIAS=0x84;CLIP=32635

def _encode(sample):
    sign=0x80 if sample<0 else 0
    sample=min(-sample if sign else sample,CLIP)+BIAS
    exponent=min(7,max(0,(sample>>7).bit_length()-1))
    mantissa=(sample>>(exponent+3))&0x0F
    return ~(sign|(exponent<<4)|mantissa)&0xFF

def _decode(byte):
    byte=~byte&0xFF
    sample=((((byte&0x0F)<<3)+BIAS)<<((byte>>4)&7))-BIAS
    return -sample if byte&0x80 else sample

ENCODE=bytes(_encode(s-65536 if s>=32768 else s) for s in range(65536))
DECODE=[_decode(b) for b in range(256)]

def _lowpass(taps=31,cutoff=3400,rate=24000):
    # Windowed-sinc low-pass so 24 kHz speech folds cleanly into the 8 kHz phone band.
    middle=(taps-1)/2;weights=[]
    for n in range(taps):
        x=n-middle
        sinc=2*cutoff/rate if x==0 else math.sin(2*math.pi*cutoff/rate*x)/(math.pi*x)
        weights.append(sinc*(0.54-0.46*math.cos(2*math.pi*n/(taps-1))))
    total=sum(weights)
    return [w/total for w in weights]

TAPS=_lowpass()

class Downsampler:
    """24 kHz PCM16 -> 8 kHz mu-law, stateful across chunks."""
    def __init__(self):
        self.history=[0]*(len(TAPS)-1);self.phase=0;self.odd=b''
    def process(self,pcm):
        pcm=self.odd+pcm;cut=len(pcm)//2*2;self.odd=pcm[cut:]
        samples=array.array('h');samples.frombytes(pcm[:cut])
        buffer=self.history+samples.tolist();size=len(TAPS);out=bytearray()
        position=self.phase
        while position<len(samples):
            window=buffer[position:position+size]
            value=int(sum(t*s for t,s in zip(TAPS,window)))
            out.append(ENCODE[max(-32768,min(32767,value))&0xFFFF])
            position+=3
        self.phase=position-len(samples)
        self.history=buffer[-(size-1):]
        return bytes(out)

class Upsampler:
    """8 kHz mu-law -> 24 kHz PCM16 by linear interpolation (plenty for recognition)."""
    def __init__(self):self.last=0
    def process(self,mulaw):
        out=array.array('h');last=self.last
        for byte in mulaw:
            sample=DECODE[byte];step=(sample-last)/3
            out.extend((int(last+step),int(last+2*step),sample));last=sample
        self.last=last
        return out.tobytes()

GUID='258EAFA5-E914-47DA-95CA-C5AB0DC85B11'

def accept_key(key):
    return base64.b64encode(hashlib.sha1((key+GUID).encode()).digest()).decode()

class Closed(Exception):pass

class Socket:
    """An upgraded connection. Server side (default): masked frames in, unmasked out.
    Client side (client=True, e.g. to Deepgram): every outgoing frame is masked, as RFC 6455 requires."""
    def __init__(self,reader,writer,client=False,raw=None):
        self.reader=reader;self.writer=writer;self.lock=threading.Lock();self.closed=False;self.client=client;self.raw=raw
    def _read(self,size):
        data=self.reader.read(size)
        if len(data)!=size:raise Closed()
        return data
    def _frame(self,opcode,payload):
        size=len(payload);bit=0x80 if self.client else 0
        if size<126:header=struct.pack('!BB',0x80|opcode,bit|size)
        elif size<65536:header=struct.pack('!BBH',0x80|opcode,bit|126,size)
        else:header=struct.pack('!BBQ',0x80|opcode,bit|127,size)
        if self.client:
            mask=os.urandom(4);header+=mask
            payload=bytes(b^mask[i%4] for i,b in enumerate(payload))
        with self.lock:
            if self.closed:raise Closed()
            try:self.writer.write(header+payload);self.writer.flush()
            except OSError:self.closed=True;raise Closed() from None
    def send(self,value):self._frame(1,json.dumps(value,separators=(',',':')).encode())
    def send_bytes(self,data):self._frame(2,data)
    def close(self):
        try:self._frame(8,struct.pack('!H',1000))
        except Closed:pass
        self.closed=True
        if self.raw:
            try:self.raw.shutdown(socket.SHUT_RDWR)
            except OSError:pass
            self.raw.close()
    def receive(self):
        """Next text message as a dict; answers pings; raises Closed at the end."""
        message=b''
        while True:
            first,second=self._read(2)
            opcode=first&0x0F;size=second&0x7F
            if size==126:size=struct.unpack('!H',self._read(2))[0]
            elif size==127:size=struct.unpack('!Q',self._read(8))[0]
            if size>1<<20:raise Closed()
            mask=self._read(4) if second&0x80 else b'\0\0\0\0'
            payload=bytes(b^mask[i%4] for i,b in enumerate(self._read(size)))
            if opcode==8:self.close();raise Closed()
            if opcode==9:self._frame(10,payload);continue
            if opcode==10:continue
            message+=payload
            if first&0x80:
                try:return json.loads(message)
                except ValueError:message=b'';continue

def connect(url,headers=None,timeout=10):
    """Open a client WebSocket (wss:// or ws://) and return a client-mode Socket."""
    parts=urlparse(url);secure=parts.scheme=='wss'
    port=parts.port or (443 if secure else 80)
    raw=socket.create_connection((parts.hostname,port),timeout=timeout)
    if secure:raw=ssl.create_default_context().wrap_socket(raw,server_hostname=parts.hostname)
    key=base64.b64encode(os.urandom(16)).decode()
    path=(parts.path or '/')+('?'+parts.query if parts.query else '')
    lines=[f'GET {path} HTTP/1.1',f'Host: {parts.netloc}','Upgrade: websocket','Connection: Upgrade',
      f'Sec-WebSocket-Key: {key}','Sec-WebSocket-Version: 13',*[f'{k}: {v}' for k,v in (headers or {}).items()]]
    raw.sendall(('\r\n'.join(lines)+'\r\n\r\n').encode())
    reader=raw.makefile('rb');status=reader.readline()
    response={}
    while (line:=reader.readline()) not in (b'\r\n',b'\n',b''):
        name,_,value=line.decode('latin-1').partition(':');response[name.strip().lower()]=value.strip()
    if b' 101 ' not in status or response.get('sec-websocket-accept')!=accept_key(key):
        raw.close();raise Closed('handshake refused: '+status.decode('latin-1').strip()[:80])
    return Socket(reader,raw.makefile('wb'),client=True,raw=raw)
