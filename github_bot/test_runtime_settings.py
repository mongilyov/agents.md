import contextlib
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import github_bot as bot

class RuntimeSettingsTests(unittest.TestCase):
    def args(self,*extra):
        return bot.parser().parse_args(['--app-id','123','--installation-id','456','--repo','owner/repo','--checkout','/project',*extra,'check'])
    def test_build_settings_without_config_reads(self):
        with tempfile.TemporaryDirectory() as d:
            key=Path(d)/'key.pem';key.write_text('test placeholder')
            with patch.dict(os.environ,{'GITHUB_APP_PRIVATE_KEY_PATH':str(key)}),patch.object(Path,'read_text',side_effect=AssertionError('config file read')):
                result=bot.runtime_settings(self.args())
            self.assertEqual(result,{'app_id':123,'installation_id':456,'repository':'owner/repo','checkout':'/project','private_key':str(key)})
    def test_local_key_path_reused_without_environment(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); key=root/'app.pem'; key.write_text('placeholder')
            (root/'.github-bot-key-path').write_text(str(key)+'\n')
            args=self.args(); args.checkout=d
            with patch.dict(os.environ,{},clear=True):
                self.assertEqual(bot.runtime_settings(args)['private_key'],str(key))

    def test_environment_overrides_local_file(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); key=root/'override.pem'; key.write_text('placeholder')
            (root/'.github-bot-key-path').write_text('/stale-local-path')
            args=self.args(); args.checkout=d
            with patch.dict(os.environ,{'GITHUB_APP_PRIVATE_KEY_PATH':str(key)}):
                self.assertEqual(bot.runtime_settings(args)['private_key'],str(key))

    def test_invalid_local_file_fails_without_echoing_contents(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d); args=self.args(); args.checkout=d
            for value in ['', 'relative.pem', '/missing-private-path', '/one\n/two', '-----BEGIN PRIVATE KEY-----\nsecret']:
                (root/'.github-bot-key-path').write_text(value)
                with patch.dict(os.environ,{},clear=True), self.assertRaises(bot.BotError) as e:
                    bot.runtime_settings(args)
                if value: self.assertNotIn(value,str(e.exception))

    def test_missing_key_environment(self):
        with patch.dict(os.environ,{},clear=True):
            with self.assertRaisesRegex(bot.BotError,'GITHUB_APP_PRIVATE_KEY_PATH'):
                bot.runtime_settings(self.args())
    def test_invalid_paths_not_echoed(self):
        for value in ['relative-secret.pem','/nonexistent-secret-path.pem']:
            with patch.dict(os.environ,{'GITHUB_APP_PRIVATE_KEY_PATH':value}):
                with self.assertRaises(bot.BotError) as e: bot.runtime_settings(self.args())
                self.assertNotIn(value,str(e.exception))
    def test_missing_and_invalid_ids_fail_before_authentication(self):
        for name,value in [('app_id',None),('app_id',0),('installation_id',-1),('repo',None),('checkout',None)]:
            args=self.args();setattr(args,name,value)
            with patch.object(bot,'Session') as session:
                with self.assertRaises(bot.BotError):bot.runtime_settings(args)
                session.assert_not_called()
    def test_old_config_flag_is_not_supported(self):
        with contextlib.redirect_stderr(io.StringIO()),self.assertRaises(SystemExit):
            bot.parser().parse_args(['--config','old.json','check'])
    def test_credential_subcommand_does_not_require_runtime_settings(self):
        with patch('sys.argv',['helper','_credential','get']),patch.object(bot,'credential') as credential,patch.object(bot,'runtime_settings') as settings:
            bot.main()
            credential.assert_called_once();settings.assert_not_called()

if __name__=='__main__':unittest.main()
