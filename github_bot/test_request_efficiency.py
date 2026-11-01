import unittest
from unittest.mock import patch
import github_bot as bot
from test_review_requests import ReviewSession


class RequestEfficiencyTests(unittest.TestCase):
    def test_pending_request_reads_pr_only_once(self):
        session = ReviewSession()
        session.prs[1]['requested_reviewers'] = [{'login': 'Reviewer'}]
        with patch.object(session, 'request', wraps=session.request) as request:
            result = bot.request_review(session, 1, ['reviewer'])
        self.assertEqual(request.call_args_list, [(('GET', '/pulls/1'),)])
        self.assertEqual(result['action'], 'already requested')
        self.assertEqual(session.writes, [])

    def test_rerequest_reuses_identity_and_still_verifies_after_write(self):
        session = ReviewSession()
        session.prs[1]['requested_reviewers'] = [
            {'login': 'Reviewer', 'node_id': 'USER_1', 'type': 'User'}]
        result = {'data': {'rerequestReviews': {'pullRequest': {'id': 'PR_1'}}}}
        with patch.object(bot, 'api', return_value=result) as api, \
                patch.object(session, 'request', wraps=session.request) as request:
            bot.request_review(session, 1, ['reviewer'], rerequest=True)
        api.assert_called_once()
        self.assertEqual(api.call_args.args[:3], ('POST', '/graphql', session.token))
        self.assertEqual(api.call_args.args[3]['variables']['users'], ['USER_1'])
        self.assertEqual(request.call_count, 2)
