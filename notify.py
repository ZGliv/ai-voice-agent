"""Proactive reach: Telegram messages to Zack.

Uses DATA/telegram.json ({"token": "...", "chat_id": "..."}) when present, otherwise
reuses the bot already configured for Claude Code's Telegram plugin. Send-only: the
plugin keeps receiving replies, so the two never compete for updates.
"""
import json, os, threading
from pathlib import Path
from urllib.request import Request, urlopen

PLUGIN=Path.home()/'.claude/channels/telegram'
LOCK=threading.Lock()

def telegram(data):
    try:
        saved=json.loads((data/'telegram.json').read_text())
        if saved.get('token') and saved.get('chat_id'):return {'token':saved['token'],'chat_id':str(saved['chat_id'])}
    except (OSError,ValueError):pass
    try:
        token=next((line.split('=',1)[1].strip().strip('"\'') for line in (PLUGIN/'.env').read_text().splitlines() if line.startswith('TELEGRAM_BOT_TOKEN=')),'')
        allowed=json.loads((PLUGIN/'access.json').read_text()).get('allowFrom') or []
        if token and allowed:return {'token':token,'chat_id':str(allowed[0])}
    except (OSError,ValueError):pass
    return None

def ready(data):
    return telegram(data) is not None

def send(core,text):
    """Best-effort message; returns True when Telegram accepted it."""
    config=telegram(core.DATA)
    text=(text or '').strip()
    if not config or not text:return False
    body=json.dumps({'chat_id':config['chat_id'],'text':('🔵 JARVIS\n'+text)[:4000],'disable_web_page_preview':True}).encode()
    with LOCK:
        try:
            with urlopen(Request(f"https://api.telegram.org/bot{config['token']}/sendMessage",data=body,headers={'Content-Type':'application/json'}),timeout=10) as response:
                return json.load(response).get('ok') is True
        except Exception:return False
