# AI Voice Agent

**Think out loud.** A real, local voice conversation app, recovered from the original Jarvis / AI Voice Agent prototype. The blue procedural orb remains; the backend has been replaced so every successful turn requires actual model output.

The Vercel site is a launcher and setup guide. The working app runs at **http://127.0.0.1:4321** on the computer running the companion. There is no hosted inference or remote access to your microphone.

## Start on this Mac

```sh
cd ~/Developer/ai-voice-agent
python3 companion.py
```

Open http://127.0.0.1:4321. Keep Terminal open. Control-C stops the companion. You can also double-click `Start Voice Agent.command` after allowing that local script in macOS if prompted.

The built frontend is included in the downloadable source archive. In this checkout, rebuild after editing with `npm ci && npm run build`.

Existing dependencies are reused read-only:

- `/opt/homebrew/bin/whisper`, cached `~/.cache/whisper/base.pt` (Whisper base, CPU / 4 threads).
- FFmpeg for decoding browser WebM / M4A / WAV, bounded to 60 seconds.
- Ollama at `127.0.0.1:11434`, installed `qwen3:8b`. Start the Ollama app if setup says reasoning is unavailable.
- `~/Developer/shortgen/.venv/bin/python` with Piper 1.4.2.
- `~/Developer/shortgen/models/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx` and its JSON config.

No model, package or external account is downloaded automatically. No ShortGen files or packages are modified.

## Use

1. Choose **Start talking**. Your browser asks for microphone permission. Nothing records beforehand.
2. Choose **Finish & send**, or wait for the 60-second limit. **Discard** stops and throws away an unfinished browser recording.
3. The app transcribes, answers with the up to the last eight completed turns as context (16,000-character input budget), then synthesizes a spoken response. Stage status is visible throughout.
4. Press play to hear the reply, or opt into **Speak replies**. Browsers can still require a playback gesture.
5. Type instead, or upload an audio file under 10 MB / 60 seconds. If a dependency is unavailable, the app shows an error and retains completed steps. A missing speech engine does not discard a generated text answer.
6. **Stop response** terminates the current child process. **Retry this turn** resumes from the last saved stage. Reload or restart the companion without losing the conversation.
7. History is local. Export downloads a JSON transcript (no audio); Delete removes that conversation and its audio files. No transcript import or account sync yet.

## Local storage and bounds

Default data directory: `~/.local/share/ai-voice-agent`. It holds `history.sqlite3` and generated WAV replies. Directory/files are private to the current OS user through filesystem permissions; they are **not encrypted at rest**. Uploaded recordings are removed after a successful turn. Failed or cancelled recordings stay available for retry until the conversation is deleted.

One turn runs at a time across all tabs. Up to 100 conversations / 500 turns / 500 MB of stored audio. Export and delete older conversations if the limit is reached. A power loss marks in-progress turns interrupted on the next start. Do not run two companions against the same data directory simultaneously.

English speech recognition in this pilot. Local Qwen3 can hallucinate; it has no web, files, tools, action permissions, wake word, or background listening. Responses have a 180-token output limit. No barge-in while a reply is generating; cancel it first. Latency depends on hardware and other local models running.

The server binds only `127.0.0.1`. Same-origin, Host and Fetch Metadata checks reject cross-site requests, and there is no permissive CORS. The HTTPS launcher links to the local app instead of silently probing localhost or bypassing local-network permissions. Other users/programs with access to this OS account can access this local app. This is not a remotely authenticated server.

## Install on another computer (manual, free local dependencies)

macOS example, Python 3.12 recommended:

```sh
brew install python@3.12 ffmpeg ollama
python3.12 -m venv .venv
.venv/bin/pip install openai-whisper==20250625 piper-tts==1.4.2
.venv/bin/python -c "import whisper; whisper.load_model('base')"
ollama pull qwen3:8b
```

Start Ollama before using the app. Download the two LJ Speech files separately from the pinned model revision below (about 114 MB for the ONNX model):

- [en_US-ljspeech-high.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/c10ece1aade47bb51c153c893d14e5bf8e5b7117/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx)
- [en_US-ljspeech-high.onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/c10ece1aade47bb51c153c893d14e5bf8e5b7117/en/en_US/ljspeech/high/en_US-ljspeech-high.onnx.json)

Place both in a `models` folder, then:

```sh
VOICE_WHISPER="$PWD/.venv/bin/whisper" \
VOICE_PIPER_PYTHON="$PWD/.venv/bin/python" \
VOICE_PIPER_MODEL="$PWD/models/en_US-ljspeech-high.onnx" \
python3 companion.py
```

If building the frontend yourself, Node.js 22.12+ / 24 and `npm ci && npm run build` are needed. The Python companion itself uses only the standard library; model tools run as isolated child processes.

Configuration: `VOICE_PORT` (default 4321), `VOICE_DATA_DIR`, `VOICE_WHISPER`, `VOICE_WHISPER_MODELS`, `VOICE_WHISPER_MODEL` (default `base`, existing `.pt` only), `VOICE_PIPER_PYTHON`, `VOICE_PIPER_MODEL`. This pilot intentionally fixes Ollama to the local endpoint and qwen3:8b; no cloud fallback is accepted.

## Development and verification

```sh
npm test
npm run build
npm audit
python3 companion.py
```

`tests/synthetic-prompt.wav` is a clearly synthetic Piper / LJ Speech fixture. It is not the user's voice. See `VERIFICATION.md` for actual acceptance results, and `docs/PROVENANCE.md` for source/model provenance.

## Next improvements

- Faster warm transcription worker and partial transcription.
- Transcript correction before sending; longer conversations with explicit summaries.
- Import/export with audio, configurable local voice/model selection.
- Signed desktop companion packaging and accessible setup diagnostics.
- Broader language/device testing. Remote access would require a separate authentication/security design.
