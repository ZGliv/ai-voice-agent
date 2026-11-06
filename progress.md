# AI Voice Agent recovery

Authorized by parent overnight portfolio stream: preserve archive/orb; real local STT → LLM → speech; durable history, cancel/retry, text fallback; synthetic tests only; no new paid services.

Isolated source in ~/Developer/ai-voice-agent. Original archive and shared recovery untouched. Existing Whisper base model found and verified; no downloads needed. Original fake success paths and host-mic endpoint discarded.

First real 6.3s fixture loop: exact transcript; actual local Qwen3 response; Piper WAV; 19.1s combined stages on this Mac. Additional acceptance in progress; see VERIFICATION.md for final evidence.

Completed: real browser recording via synthetic stream and file upload, real model inference/playback, denial fallback, cancel in 0.32s + retry, silence/invalid errors, concurrent submission guard, durable context/restart, export/delete. Hosted handoff and source download verified at 375/1440. Root owns catalog. No paid services. One synthetic review conversation remains, no personal microphone content.


October 29: Zack authorized Project Room companion development. Local slice now
links conversations to catalog project IDs, persists reviewed decisions/next
steps, recalls them across chats, and supports edit/complete/export/manual agent
briefs. 14 tests and real Qwen3/Piper recall passed after restart. Phone access
while Mac stays on is the chosen architecture; exact HTTPS origin support is
prepared. Tailscale installer is open pending local administrator approval and
sign-in. Codex/Claude worker execution, automatic result review and Muse dispatch
remain future work; no launch button pretends they exist. See README.md.

October 29 follow-up: Tailscale installation/sign-in complete, Serve enabled by
Zack, private HTTPS health verified and cross-origin request rejected. Exact
origin persisted in private local config. Redesign requested toward movie JARVIS;
three visual concepts generated, selection pending. Voice audition only.

JARVIS follow-up: user clarified responsive orb is the goal and requested direct
implementation. Built Three.js holographic geometry, mic/playback amplitude
response, reduced-motion behavior, cyan interface, and collapsed project memory.
Verified via actual private HTTPS, desktop/mobile browser, synthetic mic and real
reply playback; source voice unchanged. See VERIFICATION.md.

## 2026-10-29 — Quiet conversation interface
- Confirmed direction: default view is only the responsive JARVIS orb and message field with inline microphone/send. No heading, status badge, setup link, project picker, or empty transcript on the main surface.
- History drawer starts collapsed on every load, with a fresh unsaved conversation. Existing chats remain available. Project memory, upload/speech options, export/delete, and settings live in the drawer.
- Verified private HTTPS desktop 1440×1000 and mobile 390×844, saved-chat retrieval, reload reset, preserved history, new-conversation drawer dismissal, and no horizontal overflow. Inline microphone and audio-reactive orb verified with synthetic audio, then discarded. Physical phone microphone not exercised.

## 2026-10-29 — Faster local voice and real tools
- User authorized faster replies, British Jarvis-style speech, memory tools and local Codex jobs. Keep the Mac/Tailscale architecture.
- Warm persistent Whisper/Piper workers, streamed Qwen text, cached dependency probes, faster active updates, British Alan model and concise companion personality implemented. Voice weights remain outside the repository.
- Model tools select a project, read/save decisions/next steps, prepare a Codex task and read status. Writes are tied to their source turn and deduplicated on retry.
- Codex runs via signed-in CLI in separate worktrees after reviewing and tapping Start. Registry maps known catalog projects to verified local Git folders. Status/result/session records persist; cancel and restart interruption handled. Test writes used a throwaway repository only.
- Automatic saved-memory snapshots for Codex were blocked by approval review; asked whether to send these private notes to OpenAI. Do not add them without the reply.

- Zack explicitly approved sending the selected project's saved decisions and next steps to OpenAI with Codex jobs. Added an immutable bounded snapshot at draft time, visible for review before launch. Earlier approval-review blocker is resolved by this explicit authorization.

## 2026-10-29 — Voice acceptance correction
- Zack rejected stock British Piper Alan as the desired final voice. The target is the literal film JARVIS sound, with @blakeestephens on Instagram as the specific setup reference. Do not treat a generic British voice as meeting this requirement.
- Screenshot supplied as a visual reference; it contains no audio. Public Blake Stephens course page identifies a Base44 build but does not establish the voice provider/model. Requested the specific reel link to inspect the audio and setup details. Current voice remains a fallback pending identification; no replacement voice has been selected.

- Exact reference reel: https://www.instagram.com/reel/Dd3fVr1Tbuk/ . Opened in browser and inspected visible frames/caption. Frames show a central cyan HUD, a separate laptop with code/work output, and a later restaurant-style site preview. The visible caption does not identify the voice model; no audio-provider attribution verified.
- Zack clarified the desired interaction: ask aloud for a website, have the Mac visibly start the build, and see the completed site. Current task drafting/job runner is a foundation, but visible live progress, spoken launch confirmation, and automatic local preview handoff remain missing. Do not equate the existing runner with that full experience.

## 2026-10-29 — Spoken build to live preview
- Explicit spoken work requests now authorize immediate Codex launch; planning still supports drafts. Selected-project saved memory remains included with prior consent. New websites have a separate local workspace without a selected project.
- Mac opens real progress view, then navigates to a separate-origin static preview on completion. Cancel, final report, saved workspace and reopening previews supported. Home remains orb and composer only.
- Real synthetic spoken request built After Hours focus timer via Codex, browser automatically navigated to preview; start/pause/reset and mobile overflow checked. Demo is isolated in /tmp/jarvis-workflow-test, not production memory.
- Cloud speech allowed only after showing voice and cost. Fish Audio Jarvis (MCU) model 612b878b113047d9a770c069c8b4fdfe is a candidate, not verified Blake attribution or exact/authorized Paul Bettany voice. Free API model available; s2.1-pro $15/M UTF-8 bytes (~$1.25/hour provider estimate). No cloud activation or charges.

## 2026-10-29 — Approved Fish voice connection
- Zack auditioned and selected Fish Jarvis (MCU), approved cloud speech and requested free model first. Implemented free-only adapter and private Settings connection with an actual sample before credential persistence. No paid fallback.
- Private HTTPS connection form deployed and checked at mobile viewport. 34 tests pass including free-model/voice request, payment refusal without retry, cancellation, and owner-only credential storage after success.
- No Fish key was configured at deployment. Zack has created one and was directed to paste it only into Jarvis Settings. Live provider verification remains dependent on that connection; do not claim actual Fish playback before it succeeds.

- Live follow-up: user connected Fish through Settings successfully. Private HTTPS /api/voice reports connected=true, s2.1-pro-free, Jarvis (MCU); sample endpoint returned a valid 3.68-second 24 kHz WAV. This confirms real provider synthesis and private delivery, not physical-phone microphone acceptance.

## 2026-10-29 — Orb-only continuous conversation
- User explicitly requested automatic back-and-forth listening and then a normal screen containing only the orb, no text. Preserved cyan orb; moved text/transcripts into the history drawer. Tap starts/pauses; hold/right-click opens drawer.
- AudioWorklet capture, adaptive energy endpointing, short pre-roll, automatic send after 1.15s silence, automatic spoken playback and re-listening. Silence stays local; pause/hidden page stops microphone. Browser-permitted autostart attempted; initial gesture may still be required. No voice barge-in yet.
- Two synthetic spoken turns through actual Whisper/Qwen/Piper in isolated server completed listening→waiting→speaking→listening, with no second tap and no idle uploads. Actual stopped track reported ended. Production uses the same client with already-connected Fish speech.
- Broader active goal remains: improve agent capability and keep the private URL updated. Next gaps include stronger workers, browser verification, phone previews, durable task continuation and completion updates. Do not mark this broad goal achieved based on this voice slice.

## 2026-10-29 — Research delegation
- Added public-web research_task without project selection, using installed Codex with --search, an isolated workspace, report.md, and the existing real-progress UI. Added read_job_result and audited fresh reads; reports expose clickable sources in the existing drawer/progress view. No extra home UI.
- Real natural-language request launched research job 478fae21d60b4a1baab1781194d6a6b0 in /tmp/jarvis-research-test, searched official Fish documentation and completed a cited report. Mobile report displayed three source links without horizontal overflow.
- Research uses the signed-in Codex account, no new paid service or cloud hosting. Broader goal remains active: follow-up editing, browser verification, phone previews and completion delivery still need work.

## 2026-10-29 — Spoken task completion
- Added status-based cached completion announcements, using selected Fish/Piper speech. Browser tracks watched tasks across reloads, waits for a quiet active voice session, plays once, then resumes listening. No new home text/controls.
- Verified actual completed research job through local Piper synthesis and browser playback: listening→speaking→settling→listening, one announcement request, seen state persisted, and resting visible text remained empty. Python/JS regression suite covers quiet-time gating, reload, old-task suppression, retry backoff, cache, and busy rejection.
- No locked-phone push or background delivery is claimed. Broader goal remains active.

## 2026-10-29 — Continue previous work
- Added continue_job tool, parent_id lineage, confined saved-workspace snapshots, and original-task links. Explicit follow-up requests work without selecting a new project. Original output stays intact.
- Real natural-language test asked to update the previously built After Hours timer, without supplying a job ID. Jarvis located parent 13c5bc6b943f40cabeb209f4112d0085 and launched child 0a346558ce474eafaf93c35c22a95256. Revised button label survived reset, timer start/pause/reset worked, and original site hashes were unchanged.
- Dependency/credential caches and symlinks are intentionally not copied; omissions are recorded for the worker. Child gets a fresh Git repository, not full original Git history. Broader active goal still includes browser verification automation, phone previews, and broader app integrations.

## 2026-10-29 — Private phone previews
- Added separate-origin shared static preview slot on loopback 4323 with private Tailscale HTTPS 8443. No Funnel. Completed jobs offer Open on this device; existing Mac opening remains. Selecting another site replaces the shared slot, disclosed beside the control.
- Selected job ID persists privately and is validated/restored at startup. Preview root remains a dedicated build directory; dotfiles/traversal rejected and controls reject the preview origin.
- Verified actual generated timer via HTTPS 8443 at 390×844: button navigation, countdown, pause, reset, no horizontal overflow; explicit cross-origin control API request returned 403. Physical phone connectivity not independently observed.
- Broader active goal still includes worker browser verification and additional app capabilities.


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


### Speech quality comparison — 2026-10-29
Completed clean/noisy command comparison of Base versus Small English. Retained Base after the larger model added latency and still misrecognized an action word. Results and limitations recorded in VERIFICATION.md; no production model change.


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


### Current acceptance audit and iPhone enrollment — 2026-10-29
Revalidated actual Tailscale status: Mac online, one online iOS peer. Both loopback and private HTTPS health report ready with native Whisper, Qwen3:8b and selected Fish free voice; no active turn. Ran current26 JavaScript tests successfully; last100-Python suite still matches backend state. Source archive path scan found no listed secrets/database/model paths among80 entries. Added a current acceptance snapshot to the existing VERIFICATION.md to distinguish current capabilities from historical prototype limitations. Asked for physical-phone back-and-forth feedback asynchronously; no answer or device-audio success inferred from connectivity. No service restart or user-data mutation.


### Same-voice free Fish streaming — 2026-10-30
User confirmed the selected Jarvis voice is non-negotiable and authorized streaming improvements, with cost review before any paid switch. Official Fish documentation confirms HTTP audio streaming and incremental-text WebSocket TTS; both list s2.1-pro-free. Current pricing: free model $0/M UTF-8 bytes; paid s2.1-pro $15/M UTF-8 bytes. No model, voice ID, subscription or paid fallback changed. Sources: https://docs.fish.audio/features/realtime-streaming ; https://docs.fish.audio/api-reference/endpoint/websocket/tts-live ; https://docs.fish.audio/developer-guide/models-pricing/pricing-and-rate-limits .
Live conversation now streams 24kHz mono PCM from Fish through the guarded same-origin /api/turns/:id/audio-stream endpoint into a bounded browser audio queue, rather than waiting for complete MP3 download/conversion. Uses identical voice612b878b113047d9a770c069c8b4fdfe, model s2.1-pro-free and balanced latency setting. Completed WAV remains available for history. Partial PCM is temporary and removed after completion/cancellation/failure. Transport includes terminal success/error frames, buffering bounds and timeouts; incomplete speech cannot masquerade as a complete clip. Background suspension preserves replay; known provider failures retain text for explicit retry instead of looping unavailable audio.
Interruptions cancel only the current speech turn, stop queued playback, and wait for the server to release it before submitting the next utterance. Coding jobs are unaffected. Coalesced network reads initially exposed a parser bound bug during browser testing; fixed frame-by-frame validation and added regression coverage.
102 Python +31 JavaScript tests passed across the final scoped runs; build passes with the existing large-bundle warning now just above500kB. Real free-model probe: firstPCM1.454s, complete4.505s for7.056s audio. Real HTTPS browser flow with synthetic microphone, muted speaker output and actual Whisper/Qwen/Fish: turn4b517a0cdeb74032999d4ff1411c371c began playback while server was synthesizing; Fish firstPCM0.641s versus full synthesis7.73s. Transcription1.16s and reasoning1.61s occurred first. Then a separate interrupted stream49e157d797dc46569e019d2e53bf2ded ended cancelled with text preserved and no committed partial audio; follow-up a4830a84d42c42a6b4cc2206b5a1c41c completed normally (transcription.44s, reasoning.23s, Fish firstPCM.609s). No browser exceptions or main-screen text.
Scripts: /tmp/jarvis-real-stream-browser.js, /tmp/jarvis-real-stream-interrupt.js, /tmp/jarvis-background-stream.js. Browser suspension fixture released microphone and replayed with two audio downloads/one submitted turn. These establish streaming, cancellation and lifecycle behavior in Chrome with a synthetic mic, not physical iPhone performance or subjective voice similarity. Existing voice reference/model remain unchanged.
Scope: this implements HTTP output streaming. Full utterance recognition and final answer generation still precede synthesis. Token-to-Fish WebSocket streaming is supported by Fish but is not wired to the current tool-capable model loop; streaming tentative action claims before tool results would require additional routing and validation. No claim of instant end-to-end response.


October30: User approved incremental text streaming only with unchanged voice/free model. Implemented Fish WebSocket text/audio overlap, small local conversation/tool routing, confirmed-action speech-only pass, cancellation, and Mac .venv service runtime. Free header remains mandatory; no paid fallback. Isolated comparison first PCM2.168s vs7.47s previous path; not a latency promise. See VERIFICATION.md for scope/evidence. Phone testing remains unconfirmed.

October30 follow-up: User reported a silent greeting and requested consistent response speed. Actual turn b10c00ecb3ef474abf6c8e01bcf1f075 was misrecognized as “Terrace. It's all on, do it.” and cancelled after15.3s without an answer. Removed the extra conversation classifier call: single generation uses a nonspoken SAY/TOOLS prefix, tolerating trailing spaces; explicit memory/action requests bypass it. Local Small English recognized the recorded greeting as “Jervis, what's going on?” in1.565s and passed cancellation/negation spot checks. Installed verified upstream native model, kept Base, selected Small English on this Mac. Same Fish free reference/model. Physical iPhone playback still requires user verification.

Final replay4032736767be410d8aa53cf26089d8be completed with correct greeting response and automatic return to listening; recognition.857s and first PCM1.476s afterward. Actual native warm-up and interactive LaunchAgent scheduling added after cold service recognition spike. Arithmetic first PCM1.551s after recognition. Ready on existing private link; no paid switch.

October31: User requested quicker natural back-and-forth, spoken interruption, unchanged free voice. Reduced endpoint silence1150→750ms, onset threshold320→240ms, active polling300→150ms. Removed400ms post-playback microphone gap only with confirmed echo cancellation; preserved noise/click checks and non-AEC fallback. Changed all Qwen calls to keep_alive=-1 after observing cold first-turn7.35s thinking and30-minute expiry; model now remains resident (~6.55GB) confirmed via Ollama ps. Real HTTPS spoken barge-in stopped playback280ms after synthetic speech onset; interrupted server turn cancelled/no partial WAV, complete next question answered. This is muted Chrome with injected mic, not physical iPhone echo validation.

October31: Implemented requested rolling local recognition and cancellable conversational preparation, with exact final-audio matching before adoption and no speculative tools. Preconnects unchanged free Fish voice alongside local recognition. Corrected speech invalidates drafts; temporary preparation expires/cleans up. Verified real HTTPS response overlap, voice interruption and correction across a pause. Best measured last-word-to-reply2.277s versus3.093s prior; not under1s. Same free model/voice, private Mac hosting. Remaining floor: recognition plus Fish first audio.


November1: Replaced live rolling Whisper snapshots/fixed750ms endpoint with persistent local Kyutai STT1B and semantic turn detection. Added transcript stability after an initial final-word cutoff; exact PCM receipt prevents mismatched transcript adoption. Preserved exact free Fish voice. Live corrected-question and spoken-barge-in checks pass:258ms interruption,3.212s last-word-to-reply on arithmetic. Prompt/style now addresses sir; closed cancelled Ollama connections. Diagnosed slow project/complex answers: missing Parlay catalog entry caused irrelevant/hallucinated status, and conceptual questions entered action routing. Added narrow read-only project retrieval/missing-status answer and clearer conversational routing; final complex text probe first audio1.49s, excluding endpoint. Moshi q4 benchmark on M4 Pro24GB was0.81× realtime (20.88s audio in25.65s), so not enabled for production. Audio/report saved in output.121 Python +41 JS tests and build verified; physical-phone testing and consistent sub-second latency remain open. Details/evidence in VERIFICATION.md.
