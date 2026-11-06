import plistlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch,MagicMock
import mac_service as service

class MacServiceTests(unittest.TestCase):
 def test_installer_keeps_bundled_codex_in_service_path(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'dist').mkdir();(root/'dist/index.html').write_text('built')
   plist=root/'LaunchAgents/jarvis.plist';data=root/'data'
   probe=MagicMock();probe.__enter__.return_value.connect_ex.return_value=111
   def which(name):return '/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS/codex' if name=='codex' else '/opt/homebrew/bin/python3'
   with patch.object(service,'ROOT',root),patch.object(service,'DATA',data),patch.object(service,'PLIST',plist),patch.object(service,'loaded',return_value=False),patch.object(service,'refresh_catalog'),patch.object(service.shutil,'which',side_effect=which),patch('socket.socket',return_value=probe),patch.object(service.subprocess,'run') as run:
    service.install()
   config=plistlib.loads(plist.read_bytes())
   self.assertIn('/Applications/ChatGPT.app/Contents/Resources/codex-cli/CodexCLI.app/Contents/MacOS',config['EnvironmentVariables']['PATH'].split(':'))
   self.assertEqual(config['EnvironmentVariables']['VOICE_PROJECT_CATALOG'],str(data/'project-catalog.json'))
   self.assertTrue(config['KeepAlive']);self.assertTrue(config['RunAtLoad']);run.assert_called_once()
 def test_install_does_not_compete_with_an_existing_listener(self):
  probe=MagicMock();probe.__enter__.return_value.connect_ex.return_value=0
  with patch.object(service,'loaded',return_value=False),patch.object(service,'refresh_catalog'),patch('socket.socket',return_value=probe),patch.object(service.subprocess,'run') as run:
   with self.assertRaises(SystemExit):service.install()
   run.assert_not_called()
