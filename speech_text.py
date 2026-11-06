"""Remove presentation markup from speech without changing saved response text."""
import re


def for_speech(text):
    # Keep code/content and list order; remove only Markdown presentation markers.
    text=re.sub(r'^\s*(```|~~~)[^\n]*$', '', text, flags=re.MULTILINE)
    text=re.sub(r'^\s{0,3}#{1,6}\s+', '', text, flags=re.MULTILINE)
    text=re.sub(r'^\s*[-*+]\s+(?=\S)', '', text, flags=re.MULTILINE)
    text=re.sub(r'\[([^\]\n]+)\]\(https?://[^\s)]+\)', r'\1', text)
    text=re.sub(r'(?<!\w)\*\*(?=\S)(.+?)(?<=\S)\*\*(?!\w)', r'\1', text)
    text=re.sub(r'(?<![\w*])\*(?=\S)([^*\n]+?)(?<=\S)\*(?![\w*])', r'\1', text)
    text=re.sub(r'`([^`\n]+)`', r'\1', text)
    text=re.sub(r'\n[ \t]*\n+', '\n', text)
    return text.strip() or 'The response is saved in your conversation history.'
