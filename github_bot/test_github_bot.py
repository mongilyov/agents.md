import contextlib
import io
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import github_bot as bot


class HelperTests(unittest.TestCase):
    def test_credentials_only_for_selected_https_repo(self):
        for protocol, host, path, expected in [
            ('https', 'github.com', 'owner/repo.git', True),
            ('https', 'github.com', 'owner/other.git', False),
            ('https', 'example.com', 'owner/repo.git', False),
            ('http', 'github.com', 'owner/repo.git', False),
        ]:
            output = io.StringIO()
            with patch.dict(os.environ, {'BOT_REPOSITORY': 'owner/repo', 'BOT_INSTALLATION_TOKEN': 'test-secret'}), \
                 patch('sys.argv', ['helper', '_credential', 'get']), \
                 patch('sys.stdin', io.StringIO(f'protocol={protocol}\nhost={host}\npath={path}\n')), \
                 contextlib.redirect_stdout(output):
                bot.credential()
            self.assertEqual('password=test-secret' in output.getvalue(), expected)

    def test_installation_owner_mismatch_never_mints_token(self):
        config = {'repository': 'owner/repo', 'app_id': 1, 'installation_id': 2}
        with patch.object(bot, 'jwt', return_value='jwt'), patch.object(bot, 'api') as api:
            api.side_effect = [{'id': 1}, {'account': {'login': 'someone-else'}}]
            with self.assertRaises(bot.BotError):
                with bot.Session(config):
                    pass
            self.assertEqual(api.call_count, 2)

    def test_token_scoped_and_revoked_on_failure(self):
        config = {'repository': 'owner/repo', 'app_id': 1, 'installation_id': 2}
        with patch.object(bot, 'jwt', return_value='jwt'), patch.object(bot, 'api') as api:
            api.side_effect = [
                {'id': 1, 'slug': 'my-app'}, {'account': {'login': 'owner'}},
                {'token': 'test-token', 'expires_at': 'later', 'permissions': {}},
                {'id': 3, 'login': 'my-app[bot]'}, None]
            with self.assertRaises(RuntimeError):
                with bot.Session(config):
                    raise RuntimeError('operation failed')
            self.assertEqual(api.call_args_list[2].args[-1], {'repositories': ['repo']})
            self.assertEqual(api.call_args_list[3].args[-1], 'test-token')
            self.assertEqual(api.call_args_list[-1].args, ('DELETE', '/installation/token', 'test-token'))

    def test_failed_authenticated_identity_revokes_token(self):
        config = {'repository': 'owner/repo', 'app_id': 1, 'installation_id': 2}
        with patch.object(bot, 'jwt', return_value='jwt'), patch.object(bot, 'api') as api:
            api.side_effect = [
                {'id': 1, 'slug': 'my-app'}, {'account': {'login': 'owner'}},
                {'token': 'test-token', 'expires_at': 'later', 'permissions': {}},
                bot.BotError('identity failed'), None]
            with self.assertRaises(bot.BotError):
                with bot.Session(config):
                    pass
            self.assertEqual(api.call_args_list[-1].args, ('DELETE', '/installation/token', 'test-token'))

    def test_real_local_commit_identity_without_changing_config(self):
        # A disposable repository only; no network, real key, or user checkout.
        with tempfile.TemporaryDirectory() as directory:
            def git(*args):
                return subprocess.check_output(['git', '-C', directory, *args], stderr=subprocess.DEVNULL, text=True).strip()
            git('init')
            git('remote', 'add', 'origin', 'https://github.com/owner/repo.git')
            git('config', 'user.name', 'Human')
            git('config', 'user.email', 'human@example.test')
            git('config', 'commit.gpgsign', 'false')
            git('config', 'core.hooksPath', '/dev/null')
            Path(directory, 'example.txt').write_text('example\n')
            git('add', 'example.txt')
            session = bot.Session({'repository': 'owner/repo'})
            session.token = 'test-secret'
            session.login = 'example[bot]'
            session.email = '123+example[bot]@users.noreply.github.com'
            with contextlib.redirect_stdout(io.StringIO()):
                bot.git_run(session, directory, ['commit', '-m', 'test'], identity=True)
            self.assertEqual(git('log', '-1', '--format=%an|%ae|%cn|%ce'),
                             f'{session.login}|{session.email}|{session.login}|{session.email}')
            self.assertEqual(git('config', 'user.name'), 'Human')
            session.repo = 'owner/other'
            with self.assertRaises(bot.BotError):
                bot.git_run(session, directory, ['push', 'unused'])


if __name__ == '__main__':
    unittest.main()
