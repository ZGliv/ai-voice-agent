"""Real local Piper synthesis. Model and engine are installed separately, never simulated."""
import sys, wave
from pathlib import Path
from piper import PiperVoice, SynthesisConfig
model, source, destination = sys.argv[1:]
voice = PiperVoice.load(model)
with wave.open(destination, 'wb') as output:
    voice.synthesize_wav(Path(source).read_text(), output,
        syn_config=SynthesisConfig(length_scale=1, volume=.8))
