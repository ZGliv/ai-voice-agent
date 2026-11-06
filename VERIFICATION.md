# Jarvis verification

## Current acceptance snapshot — 2026-10-29

The dated entries below are historical evidence, not a single current feature list. Older statements such as “no tools,” manual Terminal hosting, and pending Tailscale sign-in have been superseded.

| Requirement | Current evidence | Remaining limit |
| --- | --- | --- |
| Orb-only main screen | Live browser at phone dimensions reports no visible text; hidden settings/history remain reachable. | No physical iPhone visual acceptance yet. |
| Continuous spoken exchange | Browser audio fixtures exercise endpointing, playback, relistening, interruption, pause and lifecycle recovery; actual production audio requests run native Whisper → Qwen → selected Fish voice. | Physical iPhone speaker echo, Bluetooth/car audio and permission/autoplay behavior need user testing. No background listening or interruption during reasoning. |
| Selected voice | Actual Fish s2.1-pro-free calls produced audible WAVs; no paid fallback. | Availability/latency depend on Fish. No exact actor-identity claim. |
| Project memory | Real-model fixture evidence plus tests cover selection, recall, separate decisions/steps, correction and completion. | Local-model interpretation can still be wrong; memory changes require an explicit request. |
| Tell Jarvis to build and open a site | Production spoken scoreboard job e138693022cd4abbb535294eba01eef0 completed; desktop/mobile 12-step browser checks passed; independent job-watch navigation and scoring/reset worked. | Primarily static previews; arbitrary backend provisioning and public deployment are not automatic. |
| Work stays on the Mac | Running com.projectroom.jarvis LaunchAgent, isolated job workspaces and private local data. | Codex prompts/context go through the signed-in OpenAI account; speech text goes to Fish. Mac must stay awake and signed in. |
| Phone connectivity | Current Tailscale status shows Mac online and an online iOS peer; private HTTPS /api/health reports all dependencies ready. | These checks originate on the Mac and do not prove actual iPhone audio or cellular-path performance. |
| Recovery and verification | Latest suites: 100 Python and 26 JavaScript tests passed. Source archive path scan found no listed credential/database/model paths. | Synthetic fixtures and automated checks are not proof of physical-device behavior or perfect model output. |

Next acceptance gate: user tests a spoken exchange on the connected iPhone, then interruption and returning after switching apps. An async question has been sent. The intermittent long transcription measurement remains unexplained; new per-turn preparation/recognition timings support diagnosis if it recurs. The goal remains active.

## Historical verification — 2026-10-16


## Real inference (not model mocks)

- Existing cached Whisper base transcribed a 6.28-second Piper / LJ Speech fixture exactly: “This is a synthetic test recording. Please tell me one interesting fact about the moon in a single sentence.”
- Local qwen3:8b returned a real answer, and Piper generated a nonempty playable WAV. First measured turn: transcription 9.94s, reasoning 6.24s, synthesis 2.90s, total 19.1s. Subsequent warm turns were faster. No model download or paid API was used.
- Actual browser MediaRecorder encoded a **synthetic Web Audio stream** into WebM, uploaded it, and completed Whisper → Qwen3 → Piper. Transcript matched the fixture, response was real, and the MediaStream track ended on send. No physical microphone was recorded. Chrome's file-device fixture initially produced silence; the app correctly rejected it. The final recording test used an explicitly injected synthetic stream, not a fake model response.
- Browser file-upload path also completed real transcription / response / audio. Browser playback advanced and reported real audio duration, with the test muted to avoid playing sound into the room.
- Text turn “Remember that my test planet is Neptune” followed by page reload and “What was my test planet?” returned “Your test planet was Neptune.” Conversation context and generated audio survived multiple companion restarts.

## Recovery and correctness

`python3 tests/acceptance_api.py` runs real local acceptance against the companion, then deletes only its own test conversation.

- Cancellation during actual transcription: terminal `cancelled` state in **0.32s**, no answer or audio published. The local child process was terminated. Retry completed the original audio turn successfully.
- Silence: rejected with an explicit no-audible-speech error; no fabricated transcript.
- Invalid audio bytes: failed visibly; no fabricated transcript or silent “success.”
- Concurrent text submissions: one 202, one 409; no overlapping model jobs.
- Host and cross-origin checks: 403. Old `/record` endpoint: 404.
- Export contained all four test turns; Delete removed conversation and source / generated audio.
- Eight automated tests cover persistence, restart interruption, model errors, process cancellation, no audio on cancellation, resume at speech stage, failed-input preservation, and concurrency gating. `npm test`: 8/8 pass.
- `npm run build` passes. `npm audit`: zero vulnerabilities (Vite updated to 8.3.4).

## Browser / responsive acceptance

Playwright / Chrome, widths **1440 and 375**:

- Home and real conversation UI, naturally wrapping text, no horizontal overflow.
- Microphone permission explicitly denied in the test context: meaningful error; typing remained usable.
- Real text submission, persisted history after reload, follow-up context, audio playback, JSON export, file upload.
- Recording and finish/send using synthetic stream; stopped tracks confirmed.
- No page JavaScript errors in successful flow runs. Connection errors during intentional companion restarts were surfaced as disconnected state.
- Screenshots are genuine rendered UI with clearly synthetic test content, not fabricated application data.

Preferred evidence in `output/playwright/`: `voice-mobile-final.png`, `voice-recorded-1440.png`, `voice-conversation-1440.png`. Final hosted screenshots are separate.

## Scope / remaining limits

This is a **working local pilot**. Vercel is a stable launcher and downloadable source, not a cloud inference service. Models and companion must be running on the computer. History is filesystem-local, not synchronized or encrypted. Export is transcript JSON only; no import yet. English, 60-second / 10 MB input, one job at a time; 500 turns / 500 MB library limit. Physical microphone hardware and Safari/iOS were not tested. No wake word, tools, browser automation, continuous conversation or interruption while generating (cancel first).

Original archive/recovery untouched. Existing ShortGen environment/model reused read-only. New service spend: **$0**.

## Hosted acceptance

Production entry point: https://ai-voice-agent-archive.vercel.app/ . Existing Vercel project/protection retained. At 375px and 1440px, the page clearly identifies itself as a launcher, shows setup/privacy information, and downloads the companion source. No automatic requests to localhost occur. A deliberate **Open local companion** click opens the running local app successfully; cross-site API calls remain rejected. The source archive was checked to exclude model binaries, environment files, credentials and conversation data. Screenshots: `voice-hosted-1440.png`, `voice-hosted-375.png`.

Four known temporary test conversations were removed. One explicitly labeled synthetic recording conversation remains locally for review; it can be deleted from the UI.

## October 29 project-memory slice

- 14 unit tests pass, including SQLite project isolation, restart persistence,
  source-project validation, source retention after conversation deletion,
  edit/complete/remove, and exact-origin/cross-site guards. Tests use temporary data.
- Production build passes. Source archive includes project_memory.py and new UI.
- Browser acceptance used a separate database at `/tmp/project-room-companion-verification`;
  all saved content was explicitly labeled as verification fixtures. No personal notes changed.
- Saved a Knightly decision in the UI; real Qwen3/Piper recalled it. First response
  exposed ambiguous `open` decision semantics; corrected context to `confirmed`.
- Restarted the server, reloaded, began a new conversation, and obtained the actual
  reply: “Your confirmed decision is: Knightly should use a calm coach and revisit
  knight forks before adding new lessons.” It cited the saved date. This text-input
  plus spoken-output turn measured 7.7 seconds; this is not a microphone latency result.
- Saved and completed a next step through the UI. Desktop and 390px mobile layouts
  inspected; no mobile horizontal overflow. These browser checks do not establish
  physical-phone microphone, VPN connectivity, or continuous conversation.
- Tailscale connection and physical-device acceptance remain pending user sign-in.
  No automatic Codex/Claude dispatch or Muse integration is represented as shipped.

- Project-switch UI check found a brief stale-note display while loading; corrected
  immediate clearing and verified Bullproof displays no Knightly notes.
- Tailscale installer downloaded via official Homebrew cask and opened. Terminal
  installation could not finish because macOS requires an administrator password.
  User will approve locally; no password was requested in chat.


## October 29 private HTTPS connection

- Tailscale reports Mac online; initially no peer devices. User enabled Serve.
- Serve configuration proxies only private HTTPS port 443 to 127.0.0.1:4321;
  no public Funnel configuration was enabled.
- Actual HTTPS /api/health returned ready with all four local dependencies.
- An API request with an unrelated Origin returned 403.
- Saved the exact origin outside the repository and restarted the companion;
  all 14 tests passed. Phone microphone/playback remains unverified.
- Generated three redesign concepts; application UI is unchanged pending selection.


## October 29 JARVIS orb implementation

- Production build and all 14 backend tests pass. Existing private HTTPS service
  serves the updated frontend; no public portfolio deployment.
- Inspected 390px and 1440px layouts. Fixed mobile headline/status overlap and
  opaque glow-plane background before final screenshots. No horizontal overflow.
- Synthetic browser microphone stream through actual MediaRecorder/Web Audio:
  quiet amplitude yielded 0.058, louder amplitude 0.901. Discard returned to idle
  without uploading or saving the test recording. Physical microphone not tested.
- Existing synthetic Piper reply playback drove the analyser (observed 0.049),
  then pause returned to idle. Test output was silenced downstream of the analyser.
- Compared orb pixel captures across time: normal motion changed; reduced-motion
  captures were identical. Project selector and takeaway editor/cancel exercised.
- No page errors observed during final checks. Physical phone performance and
  microphone permissions remain device-level acceptance, not claimed by desktop tests.

### Minimal conversation surface (2026-10-29)
Production build passed. Browser checks at 1440×1000 and 390×844 confirm the orb/message-only opening view. Saved chat retrieval works; reload resets to a fresh conversation with history collapsed and prior chats preserved. New conversation closes the drawer. Synthetic microphone audio drives the orb through the inline control; discard stops recording without saving.

## October 29 local voice and tool upgrade
- 21 unit tests pass, including idempotent memory writes, project scoping, job drafting without execution, allowlist enforcement, cancellation, interrupted state, and preserved retry stages. Production Vite build passes.
- Isolated real-model tests: warm short text reply completed with audio in 1.17s (first text 0.49s; reasoning 0.85s; synthesis 0.22s). Cold first test took 11.12s. A voice fixture took 9.22s (transcription 3.47s, reasoning 5.27s, synthesis 0.31s). These are individual observations, not latency guarantees.
- Local Qwen tool calls saved a decision, read it back, and prepared a Codex job. Test data stayed in /tmp/jarvis-upgrade-test; production memory was not populated with fixtures.
- Real signed-in Codex CLI read a throwaway repository, then a separate job wrote VERIFIED.txt in an isolated worktree. Verified exact bytes and absence from the original checkout. Start exercised through mobile browser controls; API cancellation returned cancelled.
- Live Tailscale HTTPS health reports British Alan speech and all dependencies ready. Desktop 1440×1000/mobile 390×844 retain the minimal opening view with hidden history, transcript and jobs. Browser project memory and job results showed actual tool output without overflow.
- Existing production SQLite library backed up privately before migration. The Mac server is running the upgraded code. Physical iPhone microphone/playback acceptance remains open. Text streams, but full speech still starts after synthesis; continuous conversation/barge-in is not implemented.
- Additional automatic saved-memory snapshots in Codex handoffs were not added pending explicit authorization after automatic approval review blocked that external transfer. Task-only Codex jobs work.

- Follow-up: Zack explicitly authorized the saved-context transfer. Drafts now persist a bounded immutable project-memory snapshot, displayed before launch and included in the Codex prompt. Snapshot regression test added; prior blocker resolved.

- Final snapshot checks: 23 tests pass, including exact context in runner stdin and explicit sandbox/worktree flags. Browser review card displayed the actual saved decision before launch at 390px with no overflow. No browser page errors in final checks.

## October 29 spoken website workflow
- Real synthetic spoken request passed through Whisper and local Qwen, called build_website without project selection or extra confirmation, and launched signed-in Codex. Job 13c5bc6b943f40cabeb209f4112d0085 completed in about 134 seconds in isolated /tmp/jarvis-workflow-test.
- Browser live view automatically navigated to the generated After Hours site. Timer counted 25:00 → 24:58, paused unchanged, reset to 25:00. Mobile 390×844 had no horizontal overflow; screenshot inspected. Test server suppressed OS browser launch, so this test establishes automatic page handoff but not physical-phone initiation.
- Separate preview origin tested for static serving, blocked dotfiles/traversal, escaped symlinks, and Host validation. Generated previews have connect-src none and cannot invoke companion endpoints.
- Only static previews are automatically served. Codex final report is visible; no unsupported backend behavior is represented as working.
- Final 30 tests and production build passed; diff whitespace check passed. Backed up production SQLite, restarted the idle Mac service, and confirmed private HTTPS health ready with no active turn. Production UI reload retained the minimal entry surface. Cloud speech remains disabled pending audition.

## October 29 Fish voice adapter
- 34 tests pass; production build passes. Mocked provider tests verify exact free-model header/reference ID, no paid retry on HTTP 402, cancelled request makes no call, and credential saved owner-only only after sample succeeds.
- Restarted idle production companion. Private HTTPS settings display the Fish key field and actual unconnected state at mobile size without overflow. No private key or live Fish speech was available during this check. Live speech acceptance awaits the user connecting their key through Settings.

- Live follow-up: user connected Fish through Settings successfully. Private HTTPS /api/voice reports connected=true, s2.1-pro-free, Jarvis (MCU); sample endpoint returned a valid 3.68-second 24 kHz WAV. This confirms real provider synthesis and private delivery, not physical-phone microphone acceptance.

## Orb-only conversational capture
- 34 Python regressions and 3 JavaScript endpoint/WAV tests pass; Vite build passes.
- Real browser AudioWorklet fed a synthetic spoken fixture on isolated port 4322: zero idle uploads, exactly two automatic voice uploads, two real model replies and automatic return to listening. First model pipeline recorded 6.1s, excluding input/playback time. Test uses local Piper, not a claim of measured Fish latency.
- Tapping orb stopped capture: MediaStreamTrack.readyState ended. Right-click opened history/settings. Desktop 1440×1000 and mobile 390×844 inspected; resting body has no visible text and no overflow. Physical phone/noisy-car endpointing and OS background limitations remain unverified.

## Public-web research delegation
- 37 Python tests and 4 JavaScript tests pass, plus production build. Coverage includes standalone research workspace policy, idempotent launch, report lookup, source link escaping, and blocking a second job even when 41 newer drafts hide the active job from the display list.
- Real local-model request launched Codex job 478fae21d60b4a1baab1781194d6a6b0 with --search. Actual events showed live searches of official Fish documentation; report.md and a cited final response were produced. Mobile progress page showed Research title, completed report, and three working-source anchor elements without overflow.
- Fresh conversation c6b18a6c2b2b4dfb83aeaf0afd13e55e completed with an audited read_job_result call for the completed job and a spoken summary. Prior same-conversation recall could reuse its history, so it was not counted as proof of a fresh tool read. No fixture research was inserted into production memory.

## Spoken task announcements
- 40 Python tests and 7 JavaScript tests passed. Standard npm test now runs both suites.
- Browser verification used the real completed research job, seeded the browser watched state to represent returning after completion, and fed a synthetic silent microphone. Actual local Piper announcement was generated and played; phases were off→starting→listening→speaking→settling→listening. One POST, seen state persisted, no repeat during subsequent polls, and no visible home text.
- The test verifies foreground delivery and reload queue behavior, not locked-phone push. Production uses its connected Fish provider through the same synthesis selection.

## Follow-up job snapshots
- 44 Python tests and 7 JavaScript tests pass. Added checks for preserving uncommitted parent work, omitting credentials/symlinks, rejecting active/missing or redirected parent workspaces, and correct tool dispatch.
- Real local-model follow-up found the prior After Hours job and launched a linked child; worker changed Start focus to Begin focus and produced a new preview.
- Browser automatically opened the child preview. Timer counted down, paused at 24:58 across a wait, reset to 25:00, and retained Begin focus label. Mobile had no horizontal overflow. Original task link resolved to the parent job ID. SHA-256 hashes of every original site file were unchanged.
- Codex worker still reported its browser verification unavailable; the checks above were performed by this development session. This does not establish automatic browser testing within every Jarvis job.

## Private phone preview origin
- 47 Python + 7 JavaScript tests pass. Added proxy-host allowlisting, missing-selection behavior, static-only paths, and persisted selected-job restoration checks.
- Actual Open on this device click on the completed follow-up job navigated to private Tailscale HTTPS :8443. Browser timer paused at 24:58 across a wait and reset to 25:00. Mobile viewport had no overflow.
- HTTPS GET returned 200 with connect-src none and the preview CSP. A request to control /api/jobs carrying the preview Origin was rejected 403. Tailscale Serve status showed separate 443→4321 and 8443→4323 mappings without Funnel configuration.
- One shared preview slot, not simultaneous per-job preview origins. Physical-phone VPN and microphone checks remain outside this desktop verification.


### Browser checks before website handoff — 2026-10-29
Added bounded declarative interaction checks at desktop and mobile sizes, with private screenshots and a structured report. Failed or unavailable verification prevents automatic preview navigation and is surfaced in job details and the completion announcement. Missing interaction plans are explicitly load-only checks. Real After Hours timer fixture passed start/countdown/pause/reset at both sizes; an intentionally impossible assertion failed both. 52 Python and 9 JavaScript tests passed. This does not yet provide automatic repair, physical-phone testing, or exhaustive site verification. Browser checks reuse the configured existing Playwright session; if it is closed, verification reports unavailable.


### One bounded browser repair — 2026-10-29
Failed preview checks now trigger one Codex repair in the same isolated workspace, limited to five minutes. The original validated check plan is frozen and rerun, so edits to the plan cannot manufacture a pass. Initial and repaired screenshots/reports are retained separately. Unavailable browsers do not trigger repair. Cancellation and unresolved failures remain visible; there is no repeated repair loop.
Verified with an existing timer fixture containing a deliberately omitted Reset handler: real browser checks failed at desktop/mobile, a real Codex repair restored the handler, and the original six steps passed at both sizes. The initial build for this experiment was a seeded fixture, not a newly generated site. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-repair-e152mlrj/jobs/3416633acda243eaae0c556deb1c3a60/. 56 Python + 9 JavaScript tests passed, including frozen checks, unavailable-browser behavior, cancellation, and a failed repair stopping after one attempt.


### Spoken cancellation — 2026-10-29
Added cancel_job to the local voice model. A fresh job_status lookup in the same turn is required before cancellation; exact IDs are enforced. The shared cancellation path stops the registered job process and preserves saved files. Terminal jobs remain terminal, and repeated cancellation is harmless. Job-status verification summaries are bounded to four failed checks, with full evidence still available through read_job_result. Stale terminal-job progress is omitted to prevent misleading narration.
Verified the actual Qwen tool loop with “Stop that website build, please”: job_status → cancel_job, test process exited via SIGTERM, status cancelled. A completed task remained completed and was accurately described as already completed. Test used an isolated database and harmless sleeping process, not a user job. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-cancel-gnyhsv_c. Microphone transcription was not part of this tool-routing test.


### Audio interruption recovery — 2026-10-29
Live conversations now detect suspended/interrupted/closed audio contexts, release microphone tracks, and stop showing a false listening state. Interrupted playback retains its reply URL for replay after a tap. Stopping during audio-context resume cannot request the microphone afterward. Reply downloads are abortable on Stop and bounded to 20 seconds; old wake-lock requests cannot attach to a newer session.
Verified real Chromium AudioContext suspension through the live HTTPS app using a synthetic silent microphone stream: listening → off, track ended, one tap → listening with empty visible text. The owned temporary test tab was closed. Unit coverage also checks interrupted reply retention, startup-stop race, and download cancellation. 60 Python + 12 JavaScript tests passed. This is browser simulation of interruption, not proof of iOS phone-call/background behavior; locked/background listening remains unsupported.


### Complete and reopen next steps by voice — 2026-10-29
Added set_next_step_status after a required same-turn read_memory lookup. Only next steps in the selected project can change status; decisions, other projects, unobserved IDs and invalid statuses are rejected. Content and original source stay intact. Memory reads accept a text query, return at most 30 items/12k characters, and label recent-candidate fallback when wording does not match exactly.
Verified actual local Qwen routing for marking “Test phone playback” done and reopening it despite paraphrased user wording. Both calls used real returned IDs and persisted the correct status in an isolated database: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-memory-update-wcyp32qr. These were text-input tool-loop tests, not physical microphone tests.


### Reopen a finished website by voice — 2026-10-29
Added open_job_preview after a required same-turn job_status lookup. Only completed jobs with valid confined preview manifests are opened; repeated calls in a turn are deduplicated. The existing Mac button shares this path. The tool carries verification warnings and explicitly describes opening on the Mac, not the current phone.
Actual Qwen test: “Open the timer website you built on my Mac, please” called job_status → open_job_preview and replied “Opening the timer website on your Mac.” A real restored static preview served its expected After Hours content. The Mac opener was intercepted to avoid another system-browser tab, so this test proves routing and serving, not a newly observed macOS window. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-open-preview-x1oxbpb4. 66 Python + 12 JavaScript tests passed.


### Native local transcription — 2026-10-29
Added cancellable whisper.cpp adapter using the same multilingual Base model. Installed model SHA-1: 465707469ff3a37a2b9b8d8f89f2f99de7299dac, matching the upstream whisper.cpp model table. Native mode is selected when whisper-cli and DATA/models/ggml-base.bin exist; otherwise the existing Python worker remains. No audio is uploaded for transcription, no runtime downloads, and Fish voice is unchanged. Temporary transcripts and diagnostic files are removed after each call; Stop terminates the native process.
Three clean synthetic phrases: warm Python Base 1.856/1.892/1.886 seconds versus initial native 0.742/0.361/0.399 seconds, with the same or improved wording. Integrated adapter reruns were 0.331/0.244/0.231 seconds. Full synthetic audio → native transcription → Qwen → Piper test completed with timings 0.52/7.90/1.43 seconds and valid reply audio. Evidence: /tmp/jarvis-stt-bench/results.json and /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-native-turn-c3qj2l5s. These are synthetic clean-speech results, not noisy-car or physical-phone accuracy claims. 70 Python + 12 JavaScript tests passed.


### Prepare the conversation prompt at startup — 2026-10-29
Fixed Ollama warm-up context mismatch (default 4096 versus conversational 8192). A shared LLM_CONTEXT and system_prompt now keep startup and new-conversation requests aligned. Warm-up uses a one-token local chat with the real system/tool prefix; its output is discarded and no tools are executed. This moves prefix processing out of the first user reply.
Controlled same-question measurements after context resets: matching context only 5.805s (5.303s prompt processing), matching context plus prompt preparation 0.575s (0.102s prompt processing). Integrated warm_reasoning function: 0.563s reply, 0.102s prompt processing. Evidence /tmp/jarvis-prefill-bench.json. This compares a short new-conversation reply, not all tasks or end-to-end voice latency. Cache reuse may vary with project scope, context, other Ollama clients, and time since warm-up. Existing 82 tests passed.


### Independent Mac background service — 2026-10-29
Installed per-user LaunchAgent com.projectroom.jarvis, RunAtLoad/KeepAlive with a 10-second throttle. Jarvis no longer depends on a Codex exec session; logs are private under DATA/logs. SIGTERM now runs cleanup for speech, native transcription, preview servers and job processes. The manual launcher opens the existing service instead of competing for port 4321.
Background macOS reads of the Documents catalog stalled during initial verification. The service now reads a private copied catalog at DATA/project-catalog.json through VOICE_PROJECT_CATALOG. Memory and job databases are unchanged. Run python3 mac_service.py refresh-catalog from an authorized terminal after changing Project Room catalog data; this is a snapshot, not live sync.
Verified a controlled idle SIGTERM: launchd replaced PID 16141 with 16230, ready health returned in 3.59 seconds, and all old child processes were gone. Physical reboot/login was not performed; login startup is configured in the plist. Mac must remain awake and signed in.


### Coding jobs verified under launchd — 2026-10-29
Found and fixed missing Codex discovery under the service’s restricted PATH. Installer now carries the discovered Codex executable’s directory into the LaunchAgent PATH, including the app-bundled CLI. Added installer regression coverage for this and for refusing an occupied port.
Ran an explicitly labelled “Jarvis Service Check” through the production conversation API: Qwen selected build_website, launchd-hosted companion launched the signed-in Codex worker, worker wrote a real isolated counter site and six browser actions, and the existing browser session passed all checks on desktop and mobile. Job 41f6ce58d0a948d2a8afa42059d43cc1, conversation bb5c108efdf547b89d9a18fddb461875. The generated site is explicitly a test fixture, retained for review, not client work. Screenshots are in the job’s verification/initial folder. No deployment or paid service was introduced. 72 Python + 12 JavaScript tests passed.


### Tap to interrupt a spoken reply — 2026-10-29
Tapping the orb during active playback now stops that reply and resumes listening after a short 120ms settling interval while keeping the microphone/context alive. Tapping while listening still pauses the session; holding opens history/settings. Audio downloads use the waiting state until playback actually begins. Accessible orb label reflects interrupt versus pause. This is tap interruption, not voice barge-in.
Verified in the live built frontend with isolated browser API fixtures, a real AudioContext, synthetic microphone input and a real WAV reply: speaking → tap → listening, microphone track remained live, only one getUserMedia call, resting visible text empty. Unit tests cover playback cancellation and retained session. 72 Python + 13 JavaScript tests passed. Also removed accidental dependencies on the real Documents catalog from unit test setups after an OS file-access stall; catalog behavior has its own fixture tests. No production memory or conversations were changed by this browser test.


### Search older jobs conversationally — 2026-10-29
job_status now accepts up to eight distinctive search words across task text and project identity, querying the full database rather than only recent UI rows. Results remain bounded to five with has_more. User text uses parameterized literal LIKE matching; percent/underscore characters are escaped. Status reports expose has_report instead of a truncated report so report questions use read_job_result.
Actual Qwen test located an old hockey-roster fixture behind 45 newer jobs, then called read_job_result with its correct saved ID. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-history-search-lrkys148. Unit tests cover beyond-40 retrieval, result limits, literal wildcard/SQL input and input bounds. 74 Python + 13 JavaScript tests passed. Search is keyword matching, not semantic/vector search.


### Background noise and unheard-turn recovery — 2026-10-29
Controlled native-transcription tests found that pure noise/hum produced sound-only annotations such as “(water running)” and “(soft music)”. Added a narrow whole-annotation filter that preserves spoken sentences mentioning these sounds. An unheard terminal turn now bypasses reasoning/speech, retains source audio for optional retry, and lets an active voice session resume listening. Three unheard clips within 30 seconds pause the microphone with an actionable notice, preventing repeated processing. Successful playback clears that count.
Verified real noisy WAV through the native backend: status unheard, zero model calls, no reply audio. Evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-noise-turn-2jmecsbb. Browser fixture test using real AudioContext returned listening/live mic/empty text after two clips and off/ended mic after the third. 76 Python + 14 JavaScript tests passed. Synthetic speech at 0 dB SNR still lost words; these changes do not establish noisy-car speech accuracy. Raw benchmark /tmp/jarvis-noise-bench/results.json.


### Speech-model comparison — 2026-10-29
Compared the deployed native Base model with upstream native Small English using eight synthetic Samantha-voice commands, each clean and with deterministic 10 dB white noise. Commands included negation, cancellation, memory, opening a prior build, research, and new work. Word errors ignore punctuation/case.

| Model | Audio | Word errors / reference words | Mean transcription |
| --- | --- | --- | --- |
| base | clean | 0/68 | 0.281s |
| base | 10db | 4/68 | 0.237s |
| small.en | clean | 0/68 | 0.484s |
| small.en | 10db | 3/68 | 0.424s |

Both models preserved “Do not start a new coding job” in this set. Small English slightly reduced aggregate noisy word errors but changed “Mark” to “Smart”; it also regressed a longer 20 dB command in the earlier benchmark. Kept Base live: the small aggregate improvement does not justify the latency increase and instruction-word regression on this evidence. These are synthetic tests, not physical-phone/car measurements. Detailed results: /tmp/jarvis-command-bench/results.json and /tmp/jarvis-small-noise-results.json. The unused Small English model download was removed from /tmp; no live model/config changed.


### Select a project after greeting — 2026-10-29
Previously unscoped conversations can now select a project after greetings or brainstorming, through both the voice tool and API. Re-selecting the same project is harmless; an already scoped conversation with history cannot be reassigned or cleared. Existing greeting turns remain intact. Updated the old relabelling regression fixture to explicitly start with a selected project.
Verified 78 Python and 14 JavaScript tests. Re-ran browser voice fixture against the built HTTPS frontend: speaking → tap → listening, one microphone request, microphone remained live, visible text empty. This uses synthetic microphone/audio and mocked API responses, not a physical-phone or actual-model selection test.


### Bounded project handoff and real conversation check — 2026-10-29
Selecting a project now uses the same 30-item/12,000-character memory bound as read_memory, with has_more when truncated. All saved data is preserved; read_memory can search older notes. This closes an unbounded tool-result path as a project accumulates notes. Regression fixture uses 40 long notes and confirms payload size plus unchanged storage.
Actual local Qwen check in an isolated database: greeting → “Let's work on Parlay. What did we leave off with?” → select_project(parl-ai) → accurate saved next step about testing saved picks on a phone. The greeting remained intact; no coding task or cloud speech was invoked. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-project-conversation-291psxr5/result.json. 79 Python + 14 JavaScript tests passed. This verifies model/tool continuity, not physical microphone accuracy.


### Voice interruption during playback — 2026-10-29
Added local interruption detection during active playback only when MediaStreamTrack.getSettings reports echoCancellation=true. Uses a 350 ms calibration window, adaptive residual energy threshold, 320 ms sustained onset, and a bounded 700 ms microphone buffer. Stops the current source and preserves captured onset into the following turn; playback onended cannot reset that recording. Existing tap interruption and no-AEC fallback remain intact. No extra cloud service or upload of idle playback-monitoring audio.
79 Python + 18 JavaScript tests passed. Tests cover steady residual energy, short-click rejection, sustained onset, no-AEC fallback, preserved PCM onset, and one submission. Live built browser test with real AudioContext, synthetic microphone oscillator and WAV playback, mocked API/echo-cancellation setting: speaking → voice input → listening without a tap, one microphone request, exactly two total submissions (original and interruption), zero visible text. Script /tmp/jarvis-voice-interrupt.js. These are controlled signal tests, not physical acoustic-echo or car-noise validation; energy detection can respond to loud environmental noise. Browser settings reference: https://developer.mozilla.org/en-US/docs/Web/API/MediaStreamTrack/getSettings .


### Correct saved notes conversationally — 2026-10-29
Added update_memory for explicit corrections to an existing decision/next step. Requires an ID observed through read_memory in the same turn and selected project, validates 1–2,000 characters, and checks the observed content hash to reject concurrent edits. Preserves identity, source, kind and status; records previous/replacement wording in the existing tool audit. Repeated identical calls do not create notes or overwrite the original correction audit.
82 Python + 18 JavaScript tests passed, covering correction, repeat calls, preserved source/status, concurrent edits, cross-project IDs and invalid content. Actual Qwen fixture read the saved red-accent decision, updated that exact item to cyan while retaining the minimal layout, and gave an accurate confirmation. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-memory-correction-6v68zadf/result.json. An earlier artificial repeated-character ID fixture was shortened by the model and safely rejected with no mutation; the production-shaped UUID fixture succeeded. This is model/tool verification with isolated data, not microphone testing.


### Follow-up routing and current decisions — 2026-10-29
continue_job now requires a job ID observed through job_status in the same turn. Project follow-ups capture the latest bounded project memory, including corrected decisions, while keeping the parent's original snapshot unchanged. Standalone jobs retain their prior context.
84 Python + 18 JavaScript tests passed. Actual Qwen routing fixture initially invented a hockey-scoreboard ID; the guard rejected it without starting work. The model then searched real job_status, chose the correct hockey fixture rather than a newer recipe fixture, and created exactly one child with the parent's actual files copied into a separate workspace. Worker start was deliberately substituted with workspace preparation: this proves model routing, drafting and copying, not a new completed website. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-followup-routing-sriov2jl/result.json. Tests also verify a corrected cyan decision reaches the child while the parent retains its original red snapshot.


### Multiple memories in one request — 2026-10-29
Fixed save_memory caching by tool name, which silently discarded second and later notes in one turn. Save audit now retains each distinct project/kind/content request; exact retries return the existing item. Legacy single-note audits remain supported. A retry after correction preserves the corrected content, and a retry after deletion does not recreate the removed note.
87 Python + 18 JavaScript tests passed. Actual Qwen request to remember a cyan-accent decision and separately save phone-testing and keyboard-access next steps produced three tool calls and exactly three correctly typed saved notes. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-multi-memory-2m4zcgst/result.json. Model/tool verification used an isolated database and no cloud speech.


### Lost submission acknowledgement recovery — 2026-10-29
Voice and text submissions now carry a per-request UUID, use a 20-second timeout, and retry once after transport/server failure with the identical body and ID. Client errors are not retried. The Mac persists request-to-turn identity and an input fingerprint in SQLite before launching work; duplicate requests return the original turn before the busy check, and mismatched input with the same ID is rejected. Mappings cascade when turns are deleted. No offline queue or cross-reload resend was added.
89 Python + 21 JavaScript tests passed. Real isolated HTTP handler accepted a repeated audio request while busy with the same turn ID and exactly one launch invocation, then rejected conflicting bytes with 409 (worker launch mocked). Fixture /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-http-retry-1ns3b5_6. Browser fixture aborted the first upload acknowledgement and verified a second upload with the same request ID, successful reply playback, tap-to-listen, live microphone, and no visible text. Script /tmp/jarvis-network-retry.js. This tests controlled connection failure, not a physical mobile-network handover. Backend was restarted before serving the new retrying frontend.


### Ready speech no longer waits for drawer data — 2026-10-29
Split the foreground voice poll from independently throttled history, memory and job refreshes. Health and current-conversation requests run concurrently; ready speech can begin before drawer requests finish, and further voice polls do not wait on them. Background failures do not replace the speaking/listening state. Added 10-second default API timeouts (submission requests retain their own 20-second retry timeout), guarded stale conversation responses, and preserved recovery when a conversation is deleted elsewhere.
Existing 89 Python + 21 JavaScript tests passed. Built frontend browser fixture delayed history/job responses by 4 seconds: an already-ready synthetic reply started in 394 ms after submission acknowledgement, followed by successful tap-to-listen with the same microphone and no visible text. Script /tmp/jarvis-ready-speech.js. This measures client delivery of a ready mocked response, not transcription, reasoning, speech generation, or real phone-network end-to-end latency.


### Build watcher connection recovery — 2026-10-29
The job progress page now aborts stalled requests after 10 seconds and resumes its existing polling loop. Preview/cancel/device actions disable their button while pending to avoid duplicate clicks. Preview feedback says a request was made rather than claiming a visible Mac window.
Built successfully. Browser fixture stalled the first progress request for 12 seconds, observed the timeout notice, then confirmed recovery with five polls. Repeated preview clicks during a 1.2-second response produced one request and a disabled pending button. Separate browser fixtures on the Mac loopback URL confirmed failed/unavailable verification stayed on the progress view, while passed verification navigated to the controlled preview. Scripts /tmp/jarvis-watch-reconnect.js and /tmp/jarvis-preview-gate.js. These are frontend/network/navigation tests with mocked job data, not new Codex builds or physical phone tests.


### Keyword fallback for older project memory — 2026-10-29
read_memory retains exact phrase priority, then ranks whole-word keyword overlap across the selected project's saved items. Common function words are ignored, ties preserve recency, and output retains the existing 30-item/12,000-character bound. Partial results explicitly use keyword_candidates and instruct the model to inspect full content or clarify ambiguity. No embeddings, new service, or memory rewrites.
91 Python + 21 JavaScript tests passed. Actual Qwen query “keyboard testing on the phone” found and accurately recalled an older keyboard-access next step behind 40 newer phone-related notes, including its open status and before-showing-the-project condition. All 41 stored items remained unchanged. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-memory-keywords-l6b4voll/result.json. This is lexical matching, not general semantic recall; notes without shared wording may still need a more specific query.


### Cross-project check-in — 2026-10-29
Added read-only project_overview for questions such as “What are my next steps across projects?” Returns open saved steps, latest saved decisions, counts and explicitly dated catalog fields. Prioritises projects with open steps, excludes completed steps from suggestions, preserves conversation scope and all notes, and bounds pages to ten projects/12,000 characters with next_offset.
93 Python + 21 JavaScript tests passed. Actual Qwen fixture retrieved the saved phone-testing step for Parlay and timer-demo step for Portfolio without switching scope, changing notes or launching jobs. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-project-overview-u0_g3k73/result.json. The initial project-name filter caused ordinary “next steps” requests to filter everything out; removed that optional filter after model testing. The final reply accurately named both saved steps and omitted internal tool names, but still used Markdown despite the voice-style prompt; speech formatting remains a refinement to verify.


### Clean presentation markup before speech — 2026-10-29
Added speech_text.for_speech at the synthesis boundary for Fish and Piper. Removes Markdown headings, bullets, paired emphasis, code-fence markers and inline backticks; Markdown links speak their label. Original output_text stays unchanged in history. Numbered steps, negative values, negation, code content and exponent notation are preserved.
98 Python + 21 JavaScript tests passed, including both synthesis-provider paths with unchanged history and valid output audio. A real configured s2.1-pro-free Fish call for the project check-in produced 5.96 seconds of audio in 3.77 seconds. Local native transcription recovered the expected phone-testing and timer-demo wording without formatting markers. Evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-spoken-checkin-6icmuo30/result.json and reply.wav. This verifies the selected free voice path and intelligible fixture wording, not subjective voice quality or physical-phone playback. No paid fallback or credential changes.


### Orb rendering efficiency and reduced motion — 2026-10-29
Normal animation is capped at 30 FPS with time-based smoothing. Reduced-motion mode renders only on state/size changes, freezes energy-driven opacity/scaling, and still updates state colour. Page hide/visibility and WebGL loss stop scheduling; resume/restore schedules again. Preserved the existing globe/rings/glow design and orb-only surface.
Instrumented real WebGL calls in the reused browser: baseline at mobile viewport was 5,400 reduced-motion and 5,445 normal draw calls per second; updated idle reduced-motion was zero and normal was 1,170 (about 78% fewer). A desktop resize triggered one 45-draw frame in reduced mode; synthetic pagehide produced zero draws and pageshow resumed. Inspected mobile390×844 and desktop1440×900 screenshots. Re-ran the synthetic browser voice-interruption flow successfully with one microphone, two expected submissions and zero visible text. Build passed. Evidence scripts /tmp/jarvis-orb-render-check.js, /tmp/jarvis-orb-lifecycle-check.js; screenshots /tmp/jarvis-orb-render-mobile.png and /tmp/jarvis-orb-render-desktop.png. Draw-call reductions are browser measurements, not measured physical-phone battery savings; lifecycle events were simulated.


### Phone home-screen launch metadata — 2026-10-29
Added a same-origin standalone manifest (start URL /), Jarvis name, dark launch/theme colours, Apple web-app metadata, and 180/192/512 PNG icons captured from the application's existing rendered orb. No service worker, offline content, push notifications or background listening was added. Mac/Tailscale connectivity and browser microphone permission remain required.
Build passed. HTTPS checks confirmed application/manifest+json plus valid PNG dimensions/MIME types; icon visually inspected. Browser Page.getAppManifest returned no parse errors, and mobile viewport retained zero visible text with the expected Apple title/icon metadata. Script /tmp/jarvis-manifest-check.js. Physical iPhone installation/standalone microphone behavior remains unverified. Apple instructions: https://support.apple.com/en-lamr/guide/iphone/iphea86e5236/ios .


### Hands-free conversation pause — 2026-10-29
Added pause_listening for explicit “stop listening”/“pause our conversation” requests. Stores a per-turn client action; the active browser finishes the acknowledgement then stops its microphone and audio context. Background coding/research jobs are untouched. A deliberate tap or voice interruption during acknowledgement overrides the pending pause; an audio interruption retains the pause action if the acknowledgement is replayed. Resuming requires tapping the orb.
99 Python + 23 JavaScript tests passed. Actual Qwen selected pause_listening for “Stop listening now, but keep working on the website,” left the running job fixture unchanged, and explained tap-to-resume. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-pause-command-avce__9j/result.json. Browser fixture with real AudioContext/WAV playback confirmed speaking → off with ended microphone track and zero visible text, then tap → listening with a live track. Script /tmp/jarvis-pause-browser.js. This verifies local model routing and browser controls separately; no physical-phone recognition claim.


### Local conversation-model comparison and memory instruction — 2026-10-29
Compared already-installed qwen3:8b and qwen2.5-coder:7b on eight synthetic prompts with the same tool surface, 8192 context and deterministic sampling. No returned tools were executed in the comparison, and the installed cloud model was not called. Current Qwen3 met six of eight response expectations at mean0.80s; the coding model met two at mean1.29s. This is a small warm-prompt routing sample, not a broad model benchmark or end-to-end voice latency measure. The save-two criterion requires both correctly typed items in the initial response; other action criteria check the first tool. Evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-model-bench-kwa8ad1m/results.json.
Kept Qwen3. Added a concrete instruction/example to avoid merging a decision and a next step into a different action. Actual model/tool test saved “Use cyan accents” as a decision and “Test on phone” as a separate next step with accurate confirmation; fixture /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-memory-separation-0q5jnqah/result.json. Repeating the eight prompts met seven expectations at mean0.84s, evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-model-refinement-hzyczdrq/results.json. The model still sometimes invents a follow-up job ID before lookup; existing same-turn job_status enforcement blocks that mutation and earlier full-loop tests proved recovery. No claim of perfect tool selection.


### Full spoken build workflow — 2026-10-29
Submitted a clearly labelled synthetic spoken request through the running production audio endpoint: build a hockey scoreboard test fixture, separate Home/Away scoring buttons, reset, and browser checks. Turn 3e89fc53b8f24689871ac1b97a919af6 transcribed the requirements, invoked a real signed-in Codex job e138693022cd4abbb535294eba01eef0, and produced selected Fish free-model acknowledgement audio. The isolated job completed and the companion browser verifier passed all 12 interaction steps at desktop and mobile sizes, with no reported JavaScript errors, missing local assets or horizontal overflow.
A separate real browser visit to the local job-watch URL automatically navigated to http://127.0.0.1:62247/. Independently clicked both scoring buttons (1:1) and reset (0:0). This proves browser handoff logic and actual generated-site interactions, not visibility of a native window or physical-phone microphone/audio behavior. The shared phone preview was not replaced.
The production turn took 16.38s transcribing, 4.55s thinking and 6.57s synthesizing. Replaying the identical WAV directly through native Whisper measured 0.57s with unchanged defaults, 0.32s greedy and 1.16s CPU-only; clean fixture wording was preserved. Kept current recognition settings because the production outlier has not been isolated and one clean sample does not establish noisy-speech accuracy. Evidence: /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-live-workflow-wordqw88/state.json and transcription-benchmark.json; actual job workspace and verification remain in the private data directory.


### Interruption calibration tolerates brief startup transients — 2026-10-29
Changed InterruptionDetector startup calibration from peak RMS to median RMS across its existing 350ms window. A brief loud click/cough no longer raises the threshold for the entire reply. Kept the sustained-onset requirement, existing noise floor and echo-cancellation gate; sustained residual playback energy remains rejected. Speech filling most of the initial calibration window can still delay interruption; this energy-based detector does not identify speakers.
16 focused detector/lifecycle tests passed, including new transient-then-speech and sustained-echo regressions. Built and verified the live bundle in the reused browser with a synthetic microphone: 90ms loud startup tone did not interrupt playback, following sustained speech-level tone did, microphone remained live with one acquisition, and exactly one follow-up audio submission occurred. Main view retained zero visible text. Script /tmp/jarvis-interrupt-transient.js. Physical phone/car echo behavior remains unverified.


### Separate audio preparation from recognition latency — 2026-10-29
Added transcription_detail under each audio turn's existing timings JSON: audio_preparation, audio_seconds and recognition. Measurements persist before/after recognition, including unheard results, with no extra microphone capture or third-party transmission. History sums only the three top-level processing stages, avoiding double counting nested diagnostics; existing turns remain compatible.
12 companion tests and build passed. Safely restarted the idle LaunchAgent (PID32745→35760, ready in1.05s, no previous child processes left). Actual production synthetic “What is two plus two?” returned “4.” with audio: preparation0.037s, recognition0.564s, total transcription0.60s, reasoning0.23s, selected Fish free synthesis0.70s. This short warm fixture does not establish typical phone latency or explain the previous16.38s outlier. Evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-latency-check-en9ox7x1/result.json.


### Shorter acknowledgements when work starts — 2026-10-29
Updated the conversation instruction with concrete one-sentence launch acknowledgements for builds, research and follow-ups. Applies when launching a job is the only request; errors/warnings and other requested actions still require accurate explanation. No output truncation or change to job/tool permissions.
Actual local Qwen tests using clearly synthetic tool results showed that a generic brevity instruction did not reliably help, so it was not shipped. Concrete examples reduced the scoreboard launch acknowledgement from32 words to9 and preserved error explanation. Final instruction tested with both deterministic sampling and production temperature0.4: three short success acknowledgements, explicit busy-job explanation. Evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-ack-check-aai0egbx/results.json and jarvis-ack-check-v4b9szba/results.json. No jobs or speech requests executed by these fixtures. This checks response content, not end-to-end latency or guaranteed compliance on all prompts. 47 tool tests passed. Idle Mac service restarted ready (PID35760→36565) with no previous children left.


### Preserve pending speech across app switching — 2026-10-29
Added an explicit LiveConversation.suspend path for visibility loss, pagehide and interrupted audio contexts. It remembers the current reply URL and pause-after action before releasing microphone/context and aborting download. Tracking begins before the audio fetch, closing the gap where refresh had already consumed liveTurn but backgrounding discarded its in-flight reply. Deliberate stop/interruption retains existing behavior; a new conversation still clears pending speech.
10 lifecycle tests passed, including suspension during fetch and replay with pause-after preserved. Browser fixture with actual AudioContext, a synthetic microphone and delayed audio route simulated visibility loss during download: microphone track ended, state off, next tap replayed the reply, exactly two audio downloads but only one submitted voice turn. Script /tmp/jarvis-background-reply.js. Build passed and live frontend updated. This covers simulated lifecycle behavior, not physical iPhone suspension or restoration after a tab is evicted; a fully reloaded page still begins a new conversation.


### Recovery guidance matches the Mac service — 2026-10-29
Replaced stale settings instructions to start companion.py and keep Terminal open with the actual background-service setup, Mac-awake/Tailscale requirements and a read-only mac_service.py status command. The copy button now copies that status command. README opening instructions distinguish this installed service from an optional manual launch on another installation. Verified launchctl reports the current service running.
Built and checked settings at390×844 in the reused live browser: resting surface had zero visible text, hold/right-click drawer opened settings, the copy handler emitted the correct status command through a clipboard stub, and the dialog closed correctly. No actual clipboard, service or credential changes were made during that browser check.


### Accurate summary after the action-round limit — 2026-10-29
After all four permitted action rounds are used, the voice pipeline now makes one final local-model call without exposing tools. It receives every tool result and an instruction to distinguish confirmed outcomes, errors and unfinished requests. It cannot execute additional actions; a returned tool call is rejected in favour of the existing safe fallback. Ordinary shorter turns are unchanged.
100 Python tests passed, including a regression that executes exactly four mocked actions and verifies a fifth summary call has no tools, receives the last error and produces saved audio. Actual Qwen with synthetic select/save/missing-step/start results replied: “I’ve saved the decision to keep the orb cyan. No phone testing step was found. The website update is starting now.” No fixture actions or cloud speech were executed in that model check. Evidence /var/folders/vy/jxmr81414nz_0pgw12l73r040000gp/T/jarvis-final-summary-59ytgml9/result.json. Idle service restarted ready PID36565→38024 with no old child processes left. This improves bounded multi-step reporting; it does not remove the action limit or guarantee perfect model summaries.


### Same-voice free Fish streaming — 2026-10-30
User confirmed the selected Jarvis voice is non-negotiable and authorized streaming improvements, with cost review before any paid switch. Official Fish documentation confirms HTTP audio streaming and incremental-text WebSocket TTS; both list s2.1-pro-free. Current pricing: free model $0/M UTF-8 bytes; paid s2.1-pro $15/M UTF-8 bytes. No model, voice ID, subscription or paid fallback changed. Sources: https://docs.fish.audio/features/realtime-streaming ; https://docs.fish.audio/api-reference/endpoint/websocket/tts-live ; https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits .
Live conversation now streams 24kHz mono PCM from Fish through the guarded same-origin /api/turns/:id/audio-stream endpoint into a bounded browser audio queue, rather than waiting for complete MP3 download/conversion. Uses identical voice612b878b113047d9a770c069c8b4fdfe, model s2.1-pro-free and balanced latency setting. Completed WAV remains available for history. Partial PCM is temporary and removed after completion/cancellation/failure. Transport includes terminal success/error frames, buffering bounds and timeouts; incomplete speech cannot masquerade as a complete clip. Background suspension preserves replay; known provider failures retain text for explicit retry instead of looping unavailable audio.
Interruptions cancel only the current speech turn, stop queued playback, and wait for the server to release it before submitting the next utterance. Coding jobs are unaffected. Coalesced network reads initially exposed a parser bound bug during browser testing; fixed frame-by-frame validation and added regression coverage.
102 Python +31 JavaScript tests passed across the final scoped runs; build passes with the existing large-bundle warning now just above500kB. Real free-model probe: firstPCM1.454s, complete4.505s for7.056s audio. Real HTTPS browser flow with synthetic microphone, muted speaker output and actual Whisper/Qwen/Fish: turn4b517a0cdeb74032999d4ff1411c371c began playback while server was synthesizing; Fish firstPCM0.641s versus full synthesis7.73s. Transcription1.16s and reasoning1.61s occurred first. Then a separate interrupted stream49e157d797dc46569e019d2e53bf2ded ended cancelled with text preserved and no committed partial audio; follow-up a4830a84d42c42a6b4cc2206b5a1c41c completed normally (transcription.44s, reasoning.23s, Fish firstPCM.609s). No browser exceptions or main-screen text.
Scripts: /tmp/jarvis-real-stream-browser.js, /tmp/jarvis-real-stream-interrupt.js, /tmp/jarvis-background-stream.js. Browser suspension fixture released microphone and replayed with two audio downloads/one submitted turn. These establish streaming, cancellation and lifecycle behavior in Chrome with a synthetic mic, not physical iPhone performance or subjective voice similarity. Existing voice reference/model remain unchanged.
Scope: this implements HTTP output streaming. Full utterance recognition and final answer generation still precede synthesis. Token-to-Fish WebSocket streaming is supported by Fish but is not wired to the current tool-capable model loop; streaming tentative action claims before tool results would require additional routing and validation. No claim of instant end-to-end response.


## Incremental text to Fish — October 30, 2026
Supersedes the HTTP-only scope above. Added a bounded MessagePack WebSocket sender/receiver, preserving reference 612b878b113047d9a770c069c8b4fdfe and explicit model s2.1-pro-free. No paid fallback. Stable text chunks are sent while the final speech-only Qwen pass generates them; first chunk is flushed. Small JSON routing handles casual conversation without the full tool catalog; action requests retain the guarded tool loop and confirmed outcomes before speech. Unexpected tool calls in the final speech-only pass fail without execution. The PCM endpoint can now stream during thinking. Cancellation terminates the text/audio stream and prevents partial WAV publication.
Real isolated four-sentence rainbow comparison: previous HTTP path first audio at 6.78s thinking +0.690s Fish =7.47s; incremental path .702s routing +1.466s first Fish audio =2.168s. Text completed1.610s after routing. This is one sequential local comparison, not a latency guarantee or controlled benchmark. Independent delayed-text probe produced first audio at1.545s before final text at2.003s. Same free model/reference throughout.
Installed pinned websockets15.0.1 and msgpack1.1.2 in repo .venv; login service preserves existing env/catalog/PATH and now runs that interpreter. Existing HTTP path remains for retries/dependency absence. 106 Python tests and31 JavaScript tests passed, followed by15 companion tests including the new unexpected-final-tool regression. No physical iPhone or subjective voice evaluation performed.

Live HTTPS browser validation after service reload (synthetic microphone, muted speakers,390×844 viewport): turn35f5cbffe3c2472baac962ed1803d470 began playback while status was thinking, completed and returned to listening; first PCM.684s routing+1.557s Fish=2.241s after transcription (transcription1.78s). No main-screen text or browser exceptions. Tap interruption bbdd857d5b564f24ae52c02b3ae5645c cancelled with saved answer/no committed partial WAV; follow-up6c8592b6abac46378e139cbbe9240092 completed. Follow-up routing took8.375s, so latency remains variable and incremental speech does not eliminate model/routing delays. Build/source archive pass; existing501kB bundle warning remains.


## Silent greeting and routing follow-up — October30,2026
Removed two-pass classification for casual speech. One no-tools generation emits a nonspoken SAY prefix and streams its answer, or routes to the guarded tool loop. Explicit memory/action terms bypass this shortcut; real model probing revealed invented project decisions without this guard. Protocol whitespace is tolerated and never spoken. Tool confirmations still follow actual outcomes, and no tools execute from the conversational pass. 109 Python tests passed, including one-call speech/prefix, memory/action bypass, and unexpected-tool rejection. Isolated four-sentence reply first PCM=.384s to stream creation+1.100s=1.484s, versus2.168s in preceding implementation; not a controlled latency guarantee.
Recorded user greeting: Base yielded “Terrace. It's all on, do it.”; adding names as a decoder prompt did not repair it and was not deployed. Small English yielded “Jervis, what's going on?” (native1.565s; Python6.39s), so deployed native Small English. Native negation/cancel fixtures remained correct (.594s/.484s). Upstream model SHA256 c6138d6d58ecc8322097e0f987c32f1be8bb0a18532a3f88f734d1bbf9c41e5d verified; source https://huggingface.co/ggerganov/whisper.cpp/blob/main/ggml-small.en.bin. This actual user recording justifies revisiting the earlier synthetic-only Base decision. Original recording/history preserved.

Service-path validation: initial Small English replay had17.566s recognition; a warm repeat was1.211s. Added actual native warm-up inference (previous warm() only checked file existence) and set LaunchAgent ProcessType=Interactive per local launchd.plist guidance to avoid standard service resource throttling. These are mitigations, not proof the one-off spike cannot recur. Final authenticated HTTPS replay of the user's recorded greeting:4032736767be410d8aa53cf26089d8be, transcript “Jervis. What's going on?”, answer “I'm here, Zack. What's on your mind?”, recognition.857s, preparation.098s, first PCM1.476s after recognition; combined server preparation/recognition/first PCM2.436s, excluding endpointing/network/browser buffer. Completed playback and resumed listening, no visible text or browser errors. Synthetic microphone replay, muted output; jobs-list response isolated as empty to avoid unrelated completion announcements. This does not establish physical iPhone speaker output.
Arithmetic follow-up499f69449ea841fbab9feb369b3f7f53 completed with first PCM1.551s after recognition; compared with9.618s previously. That interruption script did not capture a valid first greeting turn, so it is evidence for the arithmetic response only, not a new interruption validation. Existing interruption tests remain in place. Warm-up regression plus native and service tests pass. Service health ready, native Small English, unchanged free Fish voice.


## Natural turn-taking — October31,2026
35 JavaScript tests and17 scoped Python companion tests pass. Added bounded750ms endpoint,240ms barge-in, immediate post-playback capture with confirmed echo cancellation regressions; existing click/noise/negation/cancel behavior preserved. Build passes with existing501kB bundle warning. Qwen keep_alive=-1 on all speech/tool/warm requests; Ollama ps expiry2319 and6,553,210,912bytes loaded confirms retention. Official semantics: https://docs.ollama.com/faq#how-do-i-keep-a-model-loaded-in-memory-or-make-it-unload-immediately . About6.55GB stays resident; no idle cost or speech-provider changes, but competing models/restarts may still evict it.
Actual private HTTPS browser test /tmp/jarvis-real-barge-in.js: played four-sentence rainbow response, then injected a spoken arithmetic interruption (no tap). Turn4ebee819a8cb429b827df59a1a2d802e cancelled without saved partial WAV; d7f732995c6e4591b2f7d40a72056f0c completed as “What is two plus two?”→“Two plus two is four.” Interruption280ms, silence-to-submit788ms, speech-end-to-next-playback4104ms. Thus stopping feels faster, but the next answer is not instantaneous; recognition1.644s plus Fish1.082s still dominate. No browser errors/main text. Synthetic mic and muted output, jobs-list isolated empty; no physical phone echo/acoustic validation.

Final run after residency change:0651d6f5f2f34f62846483c8cf4b1ad6 cancelled/no partial WAV;40b11cae4ad1422dbe9a5644a628992c completed correct arithmetic reply. Interruption241ms, silence-to-submit787ms, speech-end-to-playback3093ms; native recognition.584s and first Fish PCM1.246s. No browser errors or visible main text. These two runs show241–280ms interruption and3.1–4.1s complete follow-up latency; they do not guarantee timing under load/on iPhone.


## Rolling recognition and cancellable answer preparation — October31,2026
Added live_drafts.py and src/live-drafts.js. Rolling snapshots use local native Whisper, short-pause candidates prepare no-tools conversational speech, and the existing free Fish connection overlaps recognition. Nothing is audible/retrievable as a turn until final POST. Exact bytes/conversation/revision gate adoption. Explicit action/memory requests retain their recognized text but wait until final submission before entering the normal guarded tool loop. Higher revisions/tombstones invalidate delayed requests; one candidate at a time; inference serialized on replacement; expiry90s and restart orphan cleanup. Final mismatches cancel the old draft, then fall back. Tests cover no tools/speech on action drafts, changed final audio, stale upload rejection, session isolation, post-cancel late creation, one final blob matching latest snapshot, and prepared-turn publication.
114 Python tests passed before final two draft tests; subsequent5 draft tests and18 companion tests passed.38 JavaScript tests pass. Build passes with existing~503kB bundle warning.
Actual HTTPS synthetic-mic barge-in:03c3d251db6947e3ad4053fcc18f9d92 cancelled;abf4a0cd962b4723a685142013a87e4e reused preparation and answered correctly; interruption240ms, last-word-to-first-reply2360ms. With early Fish connection:c177bdf75a2d47b5a4bd5872e9119722 cancelled;595407bbfbc04bf7a3d183bf9caa7e9a reused preparation; interruption260ms, last-word-to-first-reply2277ms. Previous comparable run3093ms. Small sequential samples, not a statistical latency guarantee. No sub-second result.
Correction fixture /tmp/jarvis-draft-correction.js plays “What is two plus two?” +420ms pause +“Actually, what is three plus three?”. Result2a7e4ccf172445aeb033e716dfaf8dbe: multiple draft uploads/two invalidations, exactly one final audio POST, full corrected transcript, answer included three-plus-three-is-six. No old draft played before commit. No browser errors/main-screen text. Tests use synthetic microphones, muted speaker output and isolated empty jobs-list responses; physical iPhone acoustic/echo behavior remains unverified.


## November 1, 2026 — Kyutai semantic streaming and Moshi benchmark

Current live path: ordered 240ms PCM packets → persistent local Kyutai STT 1B → semantic VAD head plus 480ms transcript stability → local Qwen → incremental same-voice Fish free streaming. The fixed 750ms live endpoint and rolling Whisper drafts are superseded. Exact final PCM/conversation/sequence receipt is checked before using the transcript. Legacy file/maximum-turn recognition remains available. Cancellation now shuts down the model HTTP connection; a local streaming-server regression confirms the server sees disconnect.

Actual private HTTPS browser, 390×844, synthetic microphone and muted speakers:
- Final barge-in `ceb8d4aa7b2a4a8bb53f5c1e5f548fbb` cancelled with no committed partial WAV. Follow-up `3063a7203fab4d3caad6acd885a4e19b` transcribed the entire “What is 2 plus 2?” and completed with audio. Playback interruption258ms; final-word-to-submit1706ms; final-word-to-playback3212ms. No browser exceptions, no visible main-screen text.
- Correction `32923a55e8564232811bc27430a6899c` preserved “What is 2 plus 2? Actually, what is 3 plus 3?” across a420ms pause and submitted one audio turn. Reply started while synthesis was active; returned to listening. The answer included both results rather than solely the corrected question.
- Initial semantic integration did prematurely submit “What is 2 plus”; that failed attempt is not counted as success. Transcript stability was added and complete-word tests repeated.
- Standalone Kyutai packet median about114–117ms for240ms audio (warm fixture). End-of-turn still adds latency. No physical iPhone microphone/echo or subjective naturalness acceptance is established.

Complex response diagnosis and checks (isolated temporary database, real Qwen and existing free Fish; action tools blocked):
- The real configured catalog has no Parlay entry. Old routing listed unrelated projects and could invent a Parlay status, taking17–28seconds thinking. Narrow named-project check-ins now retrieve bounded local facts directly and explicitly report missing projects. Final missing-Parlay probe produced “Sir, I do not have the Parlay project in my configured catalog yet.” First audio about1.73seconds after text submission; full completion3.52seconds. No fabricated catalog entry was added.
- A conceptual question about semantic turn detection incorrectly entered action routing. Clarified general-knowledge SAY versus action TOOLS and stopped the noun “pause” from forcing the action path. The same question's final probe completed, with Sir address, no tools, and first audio about1.49seconds after text submission (routing.267 + Fish first_audio1.224). Full generated audio finished8.67seconds after text submission; this is not first-response latency. Tool-bearing tasks may still take longer.
- The spoken address is applied consistently to streamed answers. Prompts retain concise British demeanor and avoid claiming unfinished work succeeded.

Moshi: `kyutai/moshiko-mlx-q4`, M4 Pro24GiB, MLX, normal Jarvis models resident. A20.88-second synthetic spoken question/silence fixture took25.65seconds compute (0.81× real time), p50 frame91.8ms / p95 107.7ms against an80ms budget. Model load4.95seconds, peak MLX allocation5.2GB. It produced a greeting and offer to assist; first nonquiet audio at timeline.4seconds was an unsolicited greeting, NOT a measured response latency. This offline run does not establish real-time natural conversation and was slower than real time. Production voice was not changed. Artifacts: `output/moshi-conversation.wav` (synthetic user left / Moshi right), `output/moshi-response.wav`, `output/moshi-benchmark.json`, `output/moshi-benchmark.py`. Weights remain in the local Hugging Face cache; no cloud inference charge or paid switch.

Validation:121 Python tests and41 JavaScript tests; production build passes with existing >500kB bundle warning. Includes receipt binding, stream cancellation, semantic mode ignoring legacy silence cutoff, model disconnect, and named-project routing. Real Mac login service restarted only while idle, with old children cleaned up. Exact Fish voice612b878b113047d9a770c069c8b4fdfe and model s2.1-pro-free preserved. Performance numbers are individual warm fixtures, not a latency guarantee. Consistent sub-second interaction remains unachieved.
