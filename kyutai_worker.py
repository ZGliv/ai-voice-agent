"""Persistent Apple-silicon Kyutai STT worker; audio remains on this Mac.
Adapted to the official delayed-streams-modeling stt_from_mic_mlx example.
"""
import base64,json,sys,time
import numpy as np
import mlx.core as mx
import rustymimi,sentencepiece
from huggingface_hub import hf_hub_download
from moshi_mlx import models,utils
REPO='kyutai/stt-1b-en_fr-candle'
def cached(name):return hf_hub_download(REPO,name,local_files_only=True)
config=json.load(open(cached('config.json')))
cfg=models.LmConfig.from_config_dict(config)
model=models.Lm(cfg);model.set_dtype(mx.bfloat16)
model.load_pytorch_weights(cached(config.get('moshi_name','model.safetensors')),cfg,strict=True)
tokenizer=sentencepiece.SentencePieceProcessor(cached(config['tokenizer_name']))
mimi=rustymimi.Tokenizer(cached(config['mimi_name']),num_codebooks=cfg.other_codebooks)
model.warmup()
session=None;gen=None;text='';samples=0;high=0;last_text_step=0
for line in sys.stdin:
 try:
  request=json.loads(line)
  if request.get('warm'):print(json.dumps({'ready':True}),flush=True);continue
  if request['session']!=session:
   session=request['session'];text='';samples=0;high=0;last_text_step=0;mimi.reset()
   for cache in model.transformer_cache:cache.reset()
   gen=models.LmGen(model=model,max_steps=900,text_sampler=utils.Sampler(top_k=25,temp=0),audio_sampler=utils.Sampler(top_k=250,temp=.8),check=False)
  pcm=np.frombuffer(base64.b64decode(request['pcm']),dtype='<i2').astype(np.float32)/32768
  if len(pcm)%1920 or len(pcm)>1920*12:raise ValueError('Invalid frames')
  started=time.monotonic();prob=0
  for frame in pcm.reshape(-1,1920):
   if gen.step_idx>=890:raise ValueError('Turn too long')
   codes=mimi.encode_step(frame[None,None,:]);codes=mx.array(codes).transpose(0,2,1)[:,:,:cfg.other_codebooks]
   token,heads=gen.step_with_extra_heads(codes[0]);token=token[0].item();prob=float(heads[2][0,0,0].item())
   if token not in (0,3):
    text+=tokenizer.id_to_piece(token).replace('▁',' ');last_text_step=gen.step_idx
   high=high+1 if prob>=.65 else 0;samples+=1920
  # Callers may tighten end-of-turn detection (phone calls); defaults suit the microphone.
  need_high=min(6,max(2,int(request.get('end_high',3))));need_quiet=min(12,max(3,int(request.get('end_quiet',6))))
  print(json.dumps({'text':text.strip(),'end':high>=need_high and gen.step_idx-last_text_step>=need_quiet and bool(text.strip()),'probability':prob,'samples':samples,'processing_ms':round((time.monotonic()-started)*1000,1)}),flush=True)
 except Exception:
  session=None;print(json.dumps({'error':'Streaming recognition failed. Reconnect the microphone.'}),flush=True)
