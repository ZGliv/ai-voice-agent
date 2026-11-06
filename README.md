# AI Voice Agent

**Think out loud.** A real, local voice conversation app, recovered from the original Jarvis / AI Voice Agent prototype. The blue procedural orb remains; the backend has been replaced so every successful turn requires actual model output.

The Vercel site is a launcher and setup guide. The working app runs at **http://127.0.0.1:4321** on the computer running the companion. There is no hosted inference or remote access to your microphone.

## Open on this Mac or phone

This Mac runs Jarvis as the login service `com.projectroom.jarvis`; no Terminal window needs to stay open. Open http://127.0.0.1:4321 on the Mac, or https://zacks-macbook-pro.tail7e2d89.ts.net/ on your Tailscale-connected phone. Keep the Mac awake and signed in.

To check the installed service:

```sh
cd ~/Developer/ai-voice-agent
python3 mac_service.py status
```

If it is already running, do not start another companion process. For a separate installation without the service, run `python3 companion.py` manually and keep that Terminal open; Control-C stops that manual process. `Start Voice Agent.command` is also available for a manual launch.

The built frontend is included in the downloadable source archive. In this checkout, rebuild after editing with `npm ci && npm run build`.

Existing dependencies are reused read-only:

- `.venv-kyutai` (Python 3.12, pinned `requirements-kyutai.txt`) and cached `kyutai/stt-1b-en_fr-candle` for continuous local recognition and semantic end-of-turn detection.
- Native Whisper Small English remains the file-upload/maximum-turn fallback; cached Base is retained.
- FFmpeg for decoding browser WebM / M4A / WAV, bounded to 60 seconds.
- Ollama at `127.0.0.1:11434`, installed `qwen3:8b`. Start the Ollama app if setup says reasoning is unavailable.
- `~/Developer/shortgen/.venv/bin/python` with Piper 1.4.2.
- `~/.local/share/ai-voice-agent/models/en_GB-alan-medium.onnx` and its JSON config (Piper Alan, British English).

No model, package or external account is downloaded automatically. No ShortGen files or packages are modified.

## Use

1. Tap the orb and allow microphone access. Speak normally; Kyutai receives ordered audio chunks on your Mac while you speak. Its semantic end signal plus a transcript-stability check submits the completed turn automatically.
2. Hear the reply through the selected Fish voice, then speak again without tapping. With browser-confirmed echo cancellation, speaking during playback interrupts it. A tap can stop the current reply; generating replies still require cancellation before a new turn.
3. Hold/right-click the orb for history, text input and settings. The resting screen has no text. Each page load starts a new conversation with history collapsed.
4. The Mac must remain awake and signed in. Phone access uses the private Tailscale HTTPS link. Browser suspension releases the microphone and preserves pending playback for the next tap; locked-screen voice is not guaranteed.
5. Saved history and memory remain local. Export downloads JSON; deleting a conversation removes its audio. Fish receives reply text for speech; the selected free model has no paid fallback.

## Local storage and bounds

Default data directory: `~/.local/share/ai-voice-agent`. It holds `history.sqlite3` and generated WAV replies. Directory/files are private to the current OS user through filesystem permissions; they are **not encrypted at rest**. Uploaded recordings are removed after a successful turn. Failed or cancelled recordings stay available for retry until the conversation is deleted.

One turn runs at a time across all tabs. Up to 100 conversations / 500 turns / 500 MB of stored audio. Export and delete older conversations if the limit is reached. A power loss marks in-progress turns interrupted on the next start. Do not run two companions against the same data directory simultaneously.

English speech recognition in this pilot. Local Qwen3 can hallucinate. Its tools select projects, read/save decisions and next steps, prepare or start Codex jobs, build new websites, and read job status. It has no direct shell or browser access, wake word, or background listening. Responses have a 300-token limit per model step. No barge-in while a reply is generating; cancel it first. Latency depends on hardware and other local models running.

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

Start Ollama before using the app. Download the British Alan voice files (about 63 MB for the ONNX model):

- [en_GB-alan-medium.onnx](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx)
- [en_GB-alan-medium.onnx.json](https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_GB/alan/medium/en_GB-alan-medium.onnx.json)
- [Voice model card and provenance](https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_GB/alan/medium/MODEL_CARD)

Place both in a `models` folder, then:

```sh
VOICE_WHISPER="$PWD/.venv/bin/whisper" \
VOICE_PIPER_PYTHON="$PWD/.venv/bin/python" \
VOICE_PIPER_MODEL="$PWD/models/en_GB-alan-medium.onnx" \
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

- Streaming transcription (reply text and audio already stream).
- Transcript correction before sending; longer conversations with explicit summaries.
- Import/export with audio, configurable local voice/model selection.
- Signed desktop companion packaging and accessible setup diagnostics.
- Broader language/device testing. Remote access would require a separate authentication/security design.

## Project Room companion — October 29, 2026

The local app now reads the existing Project Room catalog from
`~/Documents/Project Room` (override `VOICE_PROJECT_ROOM`). Select a project,
talk or type, and use **Save a takeaway** to review and save a decision or next
step. New conversations about that project include up to 30 recent takeaways within a 12,000-character context budget. Decisions
are confirmed notes; next steps can be completed or reopened. Edit, remove,
inspect the original thought, export JSON, or copy an agent brief.

Private takeaways live in the companion's existing SQLite database. The catalog
is a dated reference, not live status. No hosted owner records are imported or
changed, and nothing is published to the public portfolio. Removing a
conversation preserves explicitly saved project takeaways, including the saved
original thought; remove the takeaway separately to erase it. The model cannot
save or launch work by claiming to do so: tools persist confirmed memory requests and launch explicitly requested work. The manual memory editor remains available.

### Local tools and Codex jobs

Say or type “Remember this decision: …”, “Save this as our next step: …”, or “What did we decide?”. Select a project in the drawer, or name it at the start of a new conversation. Memory writes retain the source utterance and are idempotent across a retry.

Explicit requests such as “Have Codex fix …” start work immediately in the selected configured project. “Build me a new website …” creates a separate local project without requiring project selection. Planning requests can still prepare a draft for the Start button. Each draft captures up to 30 saved decisions/next steps within a 12,000-character budget. Review this immutable snapshot in the job card. Zack explicitly authorized including this project memory on October 29. The CLI uses your signed-in Codex account; tasks, the snapshot and relevant repository context go to OpenAI. Speech and memory remain local. No new API subscription is configured.

Only project IDs registered in private `VOICE_DATA_DIR/codex-projects.json` can run jobs. This is a JSON object mapping catalog project IDs to absolute Git repository paths; no model-supplied filesystem path is executed. Eight current local Git projects are available on this Mac; registry entries without an existing Git folder are excluded. Add other canonical repositories deliberately after verifying them.

Existing-project jobs create a detached Git worktree; new sites get their own Git workspace. Jobs use `codex exec --cd <workspace> --sandbox workspace-write` with approvals disabled, sandbox network disabled, and no extra writable roots. Each starts from the repository's latest commit; uncommitted edits are not copied. One job runs at a time. Publication, pushes, deployments, messaging, and billing changes are outside the job instruction. No sandbox bypass flags are used.

The drawer retains job status, final report, and session ID. Cancel stops the process group; interrupted jobs are not automatically restarted. A 30-minute limit stops runaway jobs. Private logs and reports live under `VOICE_DATA_DIR/jobs/<id>`. Completed means the Codex process returned a report, not independent acceptance of its changes. Review the report/worktree before adopting the work. The voice agent can read status, but does not silently turn a worker report into a saved decision.

Claude Code and Muse dispatch are not implemented. The working integration is the installed Codex CLI, with no VPS.

### Private phone access (connected October 29)

Zack selected **phone access while the Mac stays on**. Use Tailscale Serve and
keep this Python server bound to loopback. Install/sign in on Mac and phone,
allow VPN/HTTPS setup, and restrict access to Zack's devices in the tailnet.
Do not use public Funnel for this service. Tailscale 1.104.4 is installed and signed in. Private Serve HTTPS is enabled and verified from the Mac. Physical phone acceptance is still pending.

After obtaining the Mac's actual Tailscale HTTPS origin, start the companion with
`VOICE_REMOTE_ORIGIN` set to that exact origin (scheme and host, no path), then
run `tailscale serve 4321`. The server permits only its local origins and that
explicit HTTPS origin, retains cross-site request guards, and enables its private
UI only when served by the companion. The static hosted site remains a launcher.
The configured origin is **not authentication**; Tailscale access controls provide
remote authentication. Do not expose the port through a public proxy.

The Mac must remain awake; closed-lid/sleep behavior and real iPhone microphone,
playback and interrupted-network recovery still need physical-device acceptance.
No VPS or hosted coding worker has been installed. Tailscale Serve runs in the background; the companion itself still needs to be running.

References checked October 29:
- https://tailscale.com/docs/features/tailscale-serve
- https://learn.chatgpt.com/docs/non-interactive-mode
- https://code.claude.com/docs/en/headless
- https://ai.meta.com/muse/

The verified HTTPS origin is saved privately in `VOICE_DATA_DIR/remote-origin`
(default `~/.local/share/ai-voice-agent/remote-origin`). `VOICE_REMOTE_ORIGIN`
overrides this value. Normal Python or command-file starts read that setting.
No remote-origin file or private memory is included in the source archive.

### Visual direction requested October 29

Zack requested a substantial redesign to emulate JARVIS from Iron Man, including
a cinematic holographic interface and voice. Three rendered Product Design
concepts were presented, in this displayed order: Arc Companion, Stark Workbench,
Holographic Presence. Zack subsequently clarified that he wants a responsive AI orb with JARVIS styling and explicitly requested direct implementation. The working interface now uses a procedural Three.js holographic orb; no concept image is treated as an exact approved layout. Project memory and conversations are preserved. A Mac Daniel British
voice audition was generated; the app still uses Piper and no exact film-voice
match has been claimed.

### Responsive JARVIS orb

The UI now uses live spherical wire lines, particles, segmented rotating rings,
and a luminous core. Mic amplitude drives the orb while recording; a Web Audio
analyser also measures actual reply playback. Thinking/transcription/synthesis
have distinct state treatment, with faster orbital motion during processing.
Reduced-motion preference freezes decorative movement and scale while retaining
textual state and subtle signal brightness. Project memory is a disclosure so
voice controls remain prominent. This does not change the Piper voice or add
continuous conversation or automatic agent execution.

### Spoken build and preview workflow
An explicit build request opens a live progress page on the Mac. It displays real Codex events and supports cancellation. When Codex produces a valid `.jarvis-preview.json` pointing to a dedicated static output directory, a separate loopback preview server starts and the progress page navigates to the finished site. The phone can follow progress and ask to open a completed site on the Mac; Mac-local previews remain available, and Open on this device selects a separate private HTTPS preview for phone access.

Static HTML/CSS/JavaScript sites and available static app builds are supported. Backend services, dependency downloads, and arbitrary server applications are not automatically provisioned. Generated pages cannot call the companion API. Workspaces and reports persist under the private data directory; the drawer can reopen a preview after restart.

Cloud speech is approved for evaluation only. Candidate: [Fish Audio Jarvis (MCU)](https://fish.audio/m/612b878b113047d9a770c069c8b4fdfe/). Provider/API selection awaits audition. This is not a verified licensed Paul Bettany voice or a verified identification of Blake Stephens' setup. As checked October 29, Fish API lists s2.1-pro-free at $0 and s2.1-pro at $15/M UTF-8 bytes, approximately $1.25 per hour using their estimate. The web demo may use a different model. No paid cloud speech is enabled.

### Fish Jarvis voice (free model)
Zack selected the Fish Audio Jarvis (MCU) voice on October 29 and authorized reply text to be sent to Fish for speech. Open the private companion, expand history → Settings → Fish API key → Connect & test free voice. Create the key at https://fish.audio/app/api-keys/; never put it in chat or repository files. The connection first synthesizes a short sample. Only after success does it store the key in `VOICE_DATA_DIR/fish-api-key` with owner-only permissions. Keys are not returned by APIs, exported with conversations, or included in jobs/source archives.

The adapter always sends `model: s2.1-pro-free` with reference ID `612b878b113047d9a770c069c8b4fdfe`. No paid fallback, automatic top-up, or subscription is configured. Fish errors preserve the text response for retry; they do not silently change voices. Settings can remove the credential and restore local Alan. Only reply text and the selected voice ID go to Fish. Speech remains AI-generated; exact identity/Blake attribution is not verified. Free service latency and availability are not guaranteed.

### Orb-only conversation
The normal screen is just the orb. Tap to start/pause; hold it (or right-click / Shift+F10) for history and settings. A keyboard-focusable history control is also revealed on pointer movement. Previous text input, transcripts, exports, jobs and settings stay in the drawer.

While the visible page is listening, a local AudioWorklet detects voice activity, keeps a short pre-roll, and sends a WAV after roughly 1.15 seconds of silence. Idle audio is discarded. Jarvis automatically plays the response and returns to listening. During playback, voice interruption is enabled only when the microphone track reports active echo cancellation. A local energy detector calibrates for 350 ms and requires 320 ms of sustained input above its residual-noise threshold; a rolling 700 ms buffer preserves the onset. Tapping also interrupts. Browsers without confirmed echo cancellation retain tap-only interruption. This is energy detection, not speaker identification: loud ambient sound or imperfect echo cancellation may interrupt a reply. Physical phone-speaker/car behavior still needs acceptance testing. Pause, opening the drawer, leaving the page, or hiding it releases microphone tracks. A screen wake lock is requested when supported, not guaranteed.

Previously granted permission allows an automatic start attempt, but browser audio restrictions may still require tapping the orb each visit. Physical phone/locked-screen operation is not guaranteed. Kyutai transcribes internally; there is no manual Send/transcript step in conversational mode. Background noise and recognition errors can still affect turn detection.

### Public-web research
Ask Jarvis to research a question or compare current options. `research_task` starts a signed-in Codex worker with live web search in a separate local workspace; no project selection is required. Research instructions request primary sources, direct citations, evidence versus inference, and a saved report.md. Tasks may not sign into accounts, publish, contact people or purchase. The task goes to OpenAI through Codex and public search queries go to its search service. Shell network access remains disabled.

Ask for the findings afterward: job_status locates tasks and read_job_result retrieves a persisted report. The existing history drawer and progress page show the actual report with clickable HTTP(S) sources. This does not yet provide background push notifications or automatic verification of every source claim. Read calls are audited by job ID/status and are never reused as cached results.

### Spoken task completion
While an active voice session is listening and you are not speaking, Jarvis can announce that a watched task has finished or stopped. The announcement uses the selected speech voice, is generated from a fixed factual status message, and is cached; worker output is never used as speech instructions. It then returns to listening. Task reports remain in history.

Watched/pending states are remembered in this browser across reloads. Old completed tasks are not all replayed on first use. Announcements wait while you talk, while another response is active, or while the page is hidden/paused. This is foreground voice-session delivery, not push notifications or background listening on a locked phone.

### Follow-up work
Ask Jarvis to change or continue a previous task. It identifies the saved job and uses continue_job to create a linked child job from a snapshot of the previous workspace, including uncommitted files. The original files, report, and preview remain untouched. Both the progress view and task card link back to the original.

Snapshots omit Git metadata, credentials/environment files, dependency caches, and symlinks; omitted paths are recorded for the worker in .jarvis-copy-notes.txt. Copies are limited to 30,000 files / 500 MiB. The child uses a fresh Git repository, not the original commit history. Existing-project dependencies may need setup before it can run a build. A previous preview manifest is removed from the snapshot, so the worker must explicitly produce a new one after the follow-up.

### Phone previews
The live setup serves previews privately through Tailscale at https://zacks-macbook-pro.tail7e2d89.ts.net:8443/ (loopback service 4323). Jarvis controls remain on the separate default HTTPS origin. Nothing uses public Funnel. From a completed task, choose Open on this device. Static absolute asset paths continue to work because the selected site occupies the preview root.

This is one shared preview slot: selecting another site changes what that address serves, including other open preview tabs. The selected job ID is saved privately and its validated preview is restored on restart. API requests from the preview origin are rejected, and generated sites retain a restrictive content policy. Physical phone acceptance still requires Tailscale connection; desktop verification used the actual private HTTPS address at mobile dimensions.

For another installation, configure private Tailscale Serve HTTPS on a different port/origin from the control app, proxy it to 127.0.0.1:4323, and save its exact HTTPS origin in VOICE_DATA_DIR/remote-preview-origin before starting the companion. Never expose preview content on the control API origin.


Native transcription: when `whisper-cli` is installed and `~/.local/share/ai-voice-agent/models/ggml-base.bin` exists, the companion uses whisper.cpp on this Mac. Obtain the matching model from the [upstream model instructions](https://github.com/ggml-org/whisper.cpp/tree/master/models); models are not included in the source archive. Without the binary or model at startup, the existing Python Whisper worker is used. Health reports which backend is selected. Restart after changing model installation.


On this Mac, Jarvis runs as the user LaunchAgent `com.projectroom.jarvis`, automatically starting at login and restarting after exit. Manage it from the repository with `python3 mac_service.py status`, `install`, or `uninstall`. Uninstall stops the service but preserves memory, recordings and jobs. Logs live in `~/.local/share/ai-voice-agent/logs/`. The Mac must be awake and signed in for phone access.

The service uses a private snapshot of the Project Room catalog so background access does not depend on Documents permission prompts. After editing that catalog, run `python3 mac_service.py refresh-catalog` in an authorized terminal. This refreshes catalog metadata only; saved project memory remains live in Jarvis’s database.


Saved notes can be corrected conversationally: “Change the saved colour decision to cyan; keep the minimal layout.” Jarvis reads the selected project’s notes, identifies the exact item, and updates its wording rather than creating a contradictory duplicate. It preserves completion status and source metadata, records the previous wording in the tool audit, and rejects stale or cross-project updates. Ambiguous corrections should prompt a clarification.

Ask “Give me a quick check-in across my projects. What are my next steps?” for a read-only overview of saved open steps and decisions. Catalog suggestions are labelled as dated reference, not live repository status. This does not switch projects or start jobs.


For an iPhone home-screen shortcut, open the private Tailscale HTTPS link in Safari, choose Share → Add to Home Screen, enable Open as Web App, and add Jarvis. The icon and standalone launch metadata are included. This still needs the Mac awake, Tailscale connected, and foreground microphone permission; it does not provide offline or locked-screen listening. See [Apple's instructions](https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios). Physical-device installation remains to be tested.

Say “Stop listening” or “Pause our conversation” to pause after the acknowledgement. Coding jobs continue. Tap the orb to resume; a paused microphone cannot hear a wake word.


### Streaming the selected Fish voice
Live replies use the same saved voice and `s2.1-pro-free`, streaming PCM to the browser as Fish generates it. Completed replies are saved as WAV for replay. Interrupting cancels unfinished speech and releases the voice turn before a follow-up is submitted; background coding jobs continue. App switching pauses capture and retains the reply for replay on return. No new paid service or paid fallback is enabled.
Incremental reply text now feeds Fish’s WebSocket while the answer is being generated. Casual conversation routes and answers in one local generation, sending only the spoken portion to Fish. Explicit action and memory requests bypass that shortcut and resolve through tools before the speech-only response. The first stable sentence is flushed immediately, then subsequent text arrives over the same connection. Transcription still completes before routing. Install `requirements.txt` into the repository `.venv` and run `.venv/bin/python companion.py` to enable this path; the launcher/login-service installer prefers that interpreter. Without these dependencies the existing HTTP audio stream remains available. Pricing checked October30,2026: free model $0/M UTF-8 bytes, paid S2.1 Pro $15/M UTF-8 bytes; user approval is required before switching to a paid model. Official pricing: https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits .

Recognition now prefers native Small English when its local model is installed, with Base retained as the installation fallback. This improves the recorded greeting that Base misheard; it does not guarantee recognition accuracy. Runtime health identifies the active model.

The login service performs native recognizer warm-up and uses Interactive scheduling for spoken requests. This reduces cold-start/resource-throttling risk; cold startup, long tool work and provider/network delays can still take longer than casual replies.

Historical conversational timing (October31, endpoint superseded by Kyutai below): endpoint silence is750ms (previously1150ms); interruption requires240ms sustained onset after echo calibration (previously320ms). On browsers confirming echo cancellation, the mic resumes immediately after playback instead of ignoring400ms of the next utterance. Other devices retain the speaker-tail guard. Active-turn polling is150ms. Qwen requests now retain the model in memory with keep_alive=-1 to avoid the30-minute idle unload; the current8K-context runner uses about6.55GB. Model eviction/restart and provider/network latency can still delay replies. Voice/reference/free Fish model are unchanged.

### Previous rolling recognition implementation (superseded November 1)
Live microphone capture sends rolling WAV snapshots to the private Mac about every1.2seconds, with a final candidate at a200ms pause. This is repeated local Whisper decoding of the growing utterance, not a stateful cloud ASR stream. Only conversational answers may be prepared during a pause; tools never execute from drafts. Fish's same free connection opens alongside recognition, and prepared speech stays silent until final submission. Continued speech invalidates the candidate. Final reuse requires matching session/revision, conversation and exact audio bytes; otherwise the normal recognition path runs. Idle audio is not sent; audio remains on the Mac, while candidate reply text goes to the already-configured Fish service. Discarded candidates may consume free-tier requests.
Uncommitted drafts expire after90seconds or on replacement/cancellation; marked orphan drafts are removed after restart. Normal turn/history behavior begins only after final submission. Connection/preview failures fall back to the existing final-audio path. Same voice612b878b113047d9a770c069c8b4fdfe and model s2.1-pro-free, no paid fallback. Measured browser follow-up latency2.28–2.36seconds after last word; this does not achieve consistent sub-second replies.

### Kyutai streaming recognition — November 1, 2026
Live microphone capture now sends ordered 240ms PCM packets to a persistent Apple-silicon MLX worker. Kyutai's semantic VAD head determines the end of the turn, with at least 480ms since the last transcript token and a browser check that speech has not resumed. The old 750ms silence cutoff and speculative Whisper/answer drafts are not used by the live frontend. The final transcript is bound to the exact accepted PCM, conversation and packet sequence; no tools run on partial transcripts. The 55-second maximum-turn fallback remains.

Install the optional worker on another Apple-silicon Mac with Python 3.12:
```sh
python3.12 -m venv .venv-kyutai
.venv-kyutai/bin/pip install -r requirements-kyutai.txt
.venv-kyutai/bin/python -c "from huggingface_hub import snapshot_download; snapshot_download('kyutai/stt-1b-en_fr-candle', allow_patterns=['config.json','*.safetensors','*.model'])"
```
Restart the companion after installation. Runtime model loading is cache-only. Health reports `Kyutai streaming · semantic turns` once warmed. This is local recognition, not a paid API. Missing worker/model produces a reconnect/setup error, never a silent paid switch.

Production speech remains Fish reference `612b878b113047d9a770c069c8b4fdfe`, model `s2.1-pro-free`. The system prompt addresses the user as sir and asks for concise British responses. Exact named-project status questions use a bounded read-only snapshot directly; a missing project is reported honestly. Other actions retain the existing guarded tool loop. Cancelled model streams close their connection to release generation.

Moshi q4 was benchmarked separately and is not used for production speech. See VERIFICATION.md for measured performance and limitations. Recognition streaming does not eliminate model-generation, Fish or network latency; this does not establish sub-second conversation.
