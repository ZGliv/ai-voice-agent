# Provenance

Original application: `/Users/Test/Documents/Code Archive/Archive/jarvis_iterations/aiVoiceAgent`. The original directory and its environment files/models were preserved. Repaired vertex/fragment shaders were copied from `/Users/Test/Documents/Project Room/work/recovery-oct15/ai-voice-agent/frontend/src`; the orb's procedural geometry and blue/cyan/orange state vocabulary were retained. Directional shading, sizing, state transitions, reduced motion and WebGL fallback were added.

Original backend limitations: Gemma and Lessac model files were 11-byte placeholders. Development-mode fallbacks could return dummy transcripts, fixed answers or silent audio. The unauthenticated `/record` route used the host microphone. None of that backend is served here; the new companion has no `/record` route and never opens a host microphone.

Real runtime components:

- [OpenAI Whisper](https://github.com/openai/whisper), release 20250625, MIT code/model weights. Cached base.pt, CPU inference. The CLI is given the absolute existing model path, preventing its named-model downloader from running.
- [Ollama chat API](https://docs.ollama.com/api/chat), local qwen3:8b (8.2B / Q4_K_M). `think:false`, no remote tools or cloud model. [Qwen3](https://github.com/QwenLM/Qwen3) is Apache 2.0.
- [Piper](https://github.com/OHF-Voice/piper1-gpl), installed piper-tts 1.4.2, GPL 3.0. The engine is installed separately, not redistributed inside the hosted UI/source zip.
- [LJ Speech dataset](https://keithito.com/LJ-Speech-Dataset/), public domain. Piper [model card](https://huggingface.co/rhasspy/piper-voices/blob/c10ece1aade47bb51c153c893d14e5bf8e5b7117/en/en_US/ljspeech/high/MODEL_CARD) inherits the dataset license. Model SHA256 `5d4f08ba6a2a48c44592eed3ce56bf85e9de3dd4e20df90541ae68a8310c029a`. Reused read-only from ShortGen's verified local installation.
- FFmpeg installed locally for decoding input audio. Three.js 0.154.0 (MIT), Vite 8.3.4 (MIT).

No macOS system voice recordings were used. All test audio is generated from the clearly labeled synthetic prompt using Piper / LJ Speech. No real personal microphone recording was made by the agent.

## British voice added October 29, 2026
The active local voice is Piper en_GB-alan-medium, downloaded from rhasspy/piper-voices (en/en_GB/alan/medium). Its MODEL_CARD, ONNX and JSON files are stored under ~/.local/share/ai-voice-agent/models and excluded from source packages. Model card: https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_GB/alan/medium/MODEL_CARD . This is a stock British voice with an original Jarvis-style conversational prompt, not an actor voice clone.


November 1, 2026: `kyutai_worker.py` follows Kyutai's official [MLX microphone example](https://github.com/kyutai-labs/delayed-streams-modeling/blob/main/scripts/stt_from_mic_mlx.py) (MIT source repository), using its semantic VAD head and cached [STT 1B weights](https://huggingface.co/kyutai/stt-1b-en_fr-candle). The separate experimental benchmark uses [Moshiko MLX q4](https://huggingface.co/kyutai/moshiko-mlx-q4) through [moshi-mlx](https://github.com/kyutai-labs/moshi/tree/main/moshi_mlx). Model weights retain their upstream licenses; no weights are bundled in the source archive. Moshi benchmark user input was synthesized with macOS Samantha and is explicitly a fixture. The current configured Fish voice is unchanged; the historical Piper attribution above describes the fallback, not the selected production voice.
