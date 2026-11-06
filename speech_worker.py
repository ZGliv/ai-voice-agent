"""Private JSON-lines worker: keep one speech model loaded between turns."""
import json, sys, wave
mode, model = sys.argv[1:]
if mode == 'speech':
    from piper import PiperVoice, SynthesisConfig
    engine = PiperVoice.load(model)
else:
    import torch, whisper
    torch.set_num_threads(4)
    engine = whisper.load_model(model, device='cpu')
for line in sys.stdin:
    try:
        job = json.loads(line)
        if job.get('warm'): result = {'ready': True}
        elif mode == 'speech':
            with wave.open(job['destination'], 'wb') as output:
                engine.synthesize_wav(job['text'], output, syn_config=SynthesisConfig(length_scale=.95, volume=.85))
            result = {'ready': True}
        else:
            result = engine.transcribe(job['source'], language='en', fp16=False, verbose=None)
            result = {'text': result['text'], 'segments': [{'no_speech_prob': s.get('no_speech_prob',0)} for s in result['segments']]}
        print(json.dumps(result), flush=True)
    except Exception:
        print(json.dumps({'error': 'The local speech worker failed.'}), flush=True)
