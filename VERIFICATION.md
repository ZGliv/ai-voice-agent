# Verification — 2026-10-16

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
