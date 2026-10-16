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
