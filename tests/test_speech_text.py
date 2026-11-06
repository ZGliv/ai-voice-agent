import unittest
from speech_text import for_speech

class SpeechTextTests(unittest.TestCase):
    def test_project_checkin_keeps_words_without_presentation_markup(self):
        self.assertEqual(for_speech('Your next steps:\n\n- **Parlay**: Test on a phone.\n- **Portfolio**: Add the timer demo.'), 'Your next steps:\nParlay: Test on a phone.\nPortfolio: Add the timer demo.')
    def test_preserves_numbers_negation_code_and_math(self):
        raw='Do not deploy. Keep 3.5 seconds and -5 degrees.\n1. Check x * y and 2**3**2.\n2. Keep __init__ intact.'
        self.assertEqual(for_speech(raw),raw)
        self.assertEqual(for_speech('```python\nprint("Hello")\n```'), 'print("Hello")')
    def test_links_and_inline_formatting(self):
        self.assertEqual(for_speech('# Result\nRead [the report](https://example.com/report). Run `npm test`, then *stop*.'),'Result\nRead the report. Run npm test, then stop.')
    def test_plain_text_is_unchanged(self):
        raw='Good evening, Zack. Your next step is ready.'
        self.assertEqual(for_speech(raw),raw)
