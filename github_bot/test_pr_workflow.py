import copy
import unittest
from unittest.mock import patch
import github_bot as bot


def pr(n, base='main', head='first', draft=True):
    return {'number': n, 'node_id': f'PR_{n}', 'state': 'open', 'merged': False,
            'draft': draft, 'html_url': f'https://github.com/owner/repo/pull/{n}',
            'base': {'ref': base, 'repo': {'full_name': 'owner/repo'}},
            'head': {'ref': head, 'repo': {'full_name': 'owner/repo'}}}


class FakeSession:
    repo = 'owner/repo'
    token = 'secret-test-token'

    def __init__(self):
        self.prs = {1: pr(1), 2: pr(2, 'first', 'second')}
        self.stack = None
        self.writes = []
        self.permissions = {'pull_requests': 'write'}

    def require(self, permission):
        if self.permissions.get(permission) != 'write':
            raise bot.BotError('missing permission')

    def request(self, method, path, data=None):
        if method == 'GET':
            if path.startswith('/pulls/'):
                return copy.deepcopy(self.prs[int(path.split('/')[-1])])
            if path.startswith('/stacks?'):
                n = int(path.split('=')[-1])
                return [copy.deepcopy(self.stack)] if self.stack and n in [p['number'] for p in self.stack['pull_requests']] else []
            if path == '/stacks/7':
                return copy.deepcopy(self.stack)
            if path == '':
                return {'default_branch': 'master'}
        self.writes.append((method, path, data))
        if path == '/stacks':
            self.stack = {'number': 7, 'open': True, 'pull_requests': [self.prs[n] for n in data['pull_requests']]}
            return copy.deepcopy(self.stack)
        if path == '/pulls':
            return {'html_url': 'https://github.com/owner/repo/pull/3'}
        raise AssertionError((method, path, data))


class WorkflowTests(unittest.TestCase):
    def test_create_draft_default_and_ready_opt_in(self):
        for ready in (False, True):
            with self.subTest(ready=ready):
                args = bot.parser().parse_args(['create-pr', '--head', 'branch', '--title', 'Title', '--body-file', 'body'] + (['--ready'] if ready else []))
                s = FakeSession()
                with patch.object(bot, 'body_file', return_value='Body'):
                    bot.create_pr(s, args)
                self.assertEqual(s.writes[0][2]['draft'], not ready)
                self.assertEqual(s.writes[0][2]['base'], 'master')

    def test_cli_commands(self):
        self.assertEqual(bot.parser().parse_args(['ready', '--pr', '1']).pr, 1)
        self.assertEqual(bot.parser().parse_args(['stack', '--prs', '1', '2']).prs, [1, 2])

    def test_ready_mutation_uses_bot_token_and_verifies(self):
        s = FakeSession()
        def mutate(method, path, token, data):
            self.assertEqual((method, path, token), ('POST', '/graphql', s.token))
            self.assertEqual(data['variables'], {'id': 'PR_1'})
            self.assertIn('markPullRequestReadyForReview', data['query'])
            s.prs[1]['draft'] = False
            return {'data': {'markPullRequestReadyForReview': {'pullRequest': {'id': 'PR_1', 'isDraft': False}}}}
        with patch.object(bot, 'api', side_effect=mutate):
            self.assertFalse(bot.mark_ready(s, 1)['draft'])

    def test_already_ready_does_not_mutate(self):
        s = FakeSession()
        s.prs[1]['draft'] = False
        with patch.object(bot, 'api') as api:
            bot.mark_ready(s, 1)
            api.assert_not_called()

    def test_ready_errors_are_sanitized(self):
        with patch.object(bot, 'api', return_value={'errors': [{'message': 'secret-test-token'}]}):
            with self.assertRaises(bot.BotError) as error:
                bot.mark_ready(FakeSession(), 1)
            self.assertNotIn('secret-test-token', str(error.exception))

    def test_ready_does_not_claim_success_if_still_draft(self):
        with patch.object(bot, 'api', return_value={'data': {}}):
            with self.assertRaises(bot.BotError):
                bot.mark_ready(FakeSession(), 1)

    def test_ready_rejects_wrong_repo_or_closed(self):
        for field in ('repo', 'closed'):
            s = FakeSession()
            if field == 'repo':
                s.prs[1]['base']['repo']['full_name'] = 'other/repo'
            else:
                s.prs[1]['state'] = 'closed'
            with patch.object(bot, 'api') as api:
                with self.assertRaises(bot.BotError):
                    bot.mark_ready(s, 1)
                api.assert_not_called()

    def test_stack_creates_bottom_to_top_and_is_idempotent(self):
        s = FakeSession()
        result = bot.register_stack(s, [1, 2])
        self.assertEqual(result['number'], 7)
        self.assertEqual(s.writes, [('POST', '/stacks', {'pull_requests': [1, 2]})])
        bot.register_stack(s, [1, 2])
        self.assertEqual(len(s.writes), 1)

    def test_invalid_stack_never_writes(self):
        for case in ('duplicate', 'short', 'negative', 'reverse', 'fork', 'foreign-base', 'closed', 'cycle'):
            with self.subTest(case=case):
                s = FakeSession()
                numbers = [1, 2]
                if case == 'duplicate': numbers = [1, 1]
                if case == 'short': numbers = [1]
                if case == 'negative': numbers = [-1, 2]
                if case == 'reverse': numbers = [2, 1]
                if case == 'fork': s.prs[2]['head']['repo']['full_name'] = 'other/repo'
                if case == 'foreign-base': s.prs[2]['base']['repo']['full_name'] = 'other/repo'
                if case == 'closed': s.prs[2]['state'] = 'closed'
                if case == 'cycle': s.prs[1]['base']['ref'] = 'second'
                with self.assertRaises(bot.BotError):
                    bot.register_stack(s, numbers)
                self.assertEqual(s.writes, [])

    def test_partial_or_different_existing_stack_refused(self):
        for members in ([1], [1, 2, 3], [2, 1]):
            s = FakeSession()
            s.stack = {'number': 7, 'open': True, 'pull_requests': [{'number': n} for n in members]}
            with self.assertRaises(bot.BotError):
                bot.register_stack(s, [1, 2])
            self.assertEqual(s.writes, [])

    def test_ready_recovers_when_response_is_lost(self):
        s = FakeSession()
        def lost_response(*args):
            s.prs[1]['draft'] = False
            raise bot.BotError('connection lost')
        with patch.object(bot, 'api', side_effect=lost_response) as api:
            self.assertFalse(bot.mark_ready(s, 1)['draft'])
            self.assertEqual(api.call_count, 1)

    def test_stack_recovers_when_response_is_lost_without_reposting(self):
        s = FakeSession()
        request = s.request
        def lost_response(method, path, data=None):
            result = request(method, path, data)
            if method == 'POST':
                raise bot.BotError('connection lost')
            return result
        s.request = lost_response
        self.assertEqual(bot.register_stack(s, [1, 2])['number'], 7)
        self.assertEqual(len(s.writes), 1)

    def test_stack_does_not_claim_unverified_success(self):
        s = FakeSession()
        request = s.request
        def not_created(method, path, data=None):
            if method == 'POST':
                return {'number': 7}
            return request(method, path, data)
        s.request = not_created
        with self.assertRaises(bot.BotError):
            bot.register_stack(s, [1, 2])

    def test_permission_denial_never_writes(self):
        s = FakeSession()
        s.permissions = {}
        with self.assertRaises(bot.BotError): bot.register_stack(s, [1, 2])
        with patch.object(bot, 'api') as api:
            with self.assertRaises(bot.BotError): bot.mark_ready(s, 1)
            api.assert_not_called()
        self.assertEqual(s.writes, [])


if __name__ == '__main__':
    unittest.main()
