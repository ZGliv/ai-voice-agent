#!/bin/zsh
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
cd -- "${0:A:h}"
if launchctl print "gui/$(id -u)/com.projectroom.jarvis" >/dev/null 2>&1; then
  open http://127.0.0.1:4321/
else
  if [[ -x .venv/bin/python ]]; then
    .venv/bin/python companion.py
  else
    python3 companion.py
  fi
fi
