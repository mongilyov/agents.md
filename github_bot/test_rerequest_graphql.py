import unittest
from unittest.mock import patch
import github_bot as bot
from test_review_requests import ReviewSession

class RerequestTests(unittest.TestCase):
    def run_request(self, response=None, error=None, pending=True):
        s=ReviewSession()
        if pending: s.prs[1]['requested_reviewers']=[{'login':'reviewer'}]
        calls=[]
        def api(method,path,token,data=None):
            calls.append((method,path,token,data))
            if method=='GET': return {'login':'reviewer','node_id':'USER_1','type':'User'}
            if error: raise error
            return response
        with patch.object(bot,'api',side_effect=api):
            result=bot.request_review(s,1,['Reviewer','reviewer'],rerequest=True)
        return s,calls,result
    def test_authenticated_mutation_once(self):
        s,calls,result=self.run_request({'data':{'rerequestReviews':{'pullRequest':{'id':'PR_1'}}}})
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0][:3],('GET','/users/reviewer',s.token))
        self.assertEqual(calls[1][:3],('POST','/graphql',s.token))
        self.assertEqual(calls[1][3]['variables'],{'id':'PR_1','users':['USER_1']})
        self.assertIn('rerequestReviews',calls[1][3]['query'])
        self.assertEqual(s.writes,[])
        self.assertEqual(result['action'],'rerequested')
    def test_errors_and_wrong_pr_fail_even_if_already_pending(self):
        for response in [{'errors':[{'message':'secret-test-token'}]}, {}, {'data':{'rerequestReviews':None}}, {'data':{'rerequestReviews':{'pullRequest':{'id':'WRONG'}}}}]:
            with self.subTest(response=response):
                with self.assertRaises(bot.BotError) as e:
                    self.run_request(response)
                self.assertNotIn('secret-test-token',str(e.exception))
    def test_http_failure_no_retry_or_rest_fallback(self):
        s=ReviewSession(); s.prs[1]['requested_reviewers']=[{'login':'reviewer'}]
        with patch.object(bot,'api',side_effect=[{'login':'reviewer','node_id':'USER_1','type':'User'},bot.BotError('HTTP 500')]) as api:
            with self.assertRaises(bot.BotError): bot.request_review(s,1,['reviewer'],True)
        self.assertEqual(api.call_count,2)
        self.assertEqual(s.writes,[])
    def test_requires_pending_state_after_success(self):
        with self.assertRaises(bot.BotError):
            self.run_request({'data':{'rerequestReviews':{'pullRequest':{'id':'PR_1'}}}},pending=False)
    def test_invalid_identity_prevents_mutation(self):
        for identity in [{}, {'login':'other','node_id':'USER_1','type':'User'}, {'login':'reviewer','node_id':'USER_1','type':'Bot'}]:
            with patch.object(bot,'api',return_value=identity) as api:
                with self.assertRaises(bot.BotError): bot.request_review(ReviewSession(),1,['reviewer'],True)
                self.assertEqual(api.call_count,1)
