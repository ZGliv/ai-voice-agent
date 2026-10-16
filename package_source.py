"""Package only source + built UI; never include local data, credentials or model binaries."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
root=Path(__file__).resolve().parent
files=['public/favicon.svg','vercel.json','.gitignore','README.md','VERIFICATION.md','companion.py','synthesize.py','package.json','package-lock.json','vite.config.js','index.html','Start Voice Agent.command','package_source.py']
for folder in ['src','docs','tests','dist']:
    files += [str(p.relative_to(root)) for p in (root/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.zip']
with ZipFile(root/'public/voice-agent-source.zip','w',ZIP_DEFLATED) as archive:
    for name in files:
        if (root/name).is_file():archive.write(root/name,'ai-voice-agent/'+name)
print('Packaged companion source and built UI. No models or conversation data.')
