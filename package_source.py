"""Package only source + built UI; never include local data, credentials or model binaries."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path(__file__).resolve().parent
files=['public/favicon.svg','public/manifest.webmanifest','public/apple-touch-icon.png','public/icon-192.png','public/icon-512.png','vercel.json','.gitignore','README.md','VERIFICATION.md','companion.py','project_memory.py','synthesize.py','speech_worker.py','speech_text.py','local_runtime.py','native_transcriber.py','mac_service.py','companion_tools.py','codex_jobs.py','site_preview.py','preview_verifier.py','preview_verifier.js','job_announcements.py','fish_voice.py','fish_text_stream.py','live_drafts.py','kyutai_worker.py','streaming_recognition.py','requirements-kyutai.txt','requirements.txt','package.json','package-lock.json','vite.config.js','index.html','Start Voice Agent.command','package_source.py']
for folder in ['src','docs','tests','dist']:
    files += [str(p.relative_to(root)) for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.zip']
with ZipFile(root/'public/voice-agent-source.zip','w',ZIP_DEFLATED) as archive:
    for name in files:
        if (root/name).is_file():archive.write(root/name,'ai-voice-agent/'+name)
print('Packaged companion source and built UI. No models or conversation data.')
