import copy
import unittest
from unittest.mock import patch
import github_bot as bot
from test_pr_workflow import FakeSession

class ReviewSession(FakeSession):
    def __init__(self):
        super().__init__()
        self.prs[1].update(draft=False, requested_reviewers=[], user={'login':'author'})
    def request(self, method, path, data=None):
        if method=='POST' and '/requested_reviewers' in path:
            self.writes.append((method,path,data))
            self.prs[1]['requested_reviewers']=[{'login':r} for r in data['reviewers']]
            return copy.deepcopy(self.prs[1])
        return super().request(method,path,data)

class ReviewTests(unittest.TestCase):
    def test_request_and_repeat_noop(self):
        s=ReviewSession()
        bot.request_review(s,1,['reviewer'])
        bot.request_review(s,1,['Reviewer'])
        self.assertEqual(len(s.writes),1)
        self.assertEqual(s.writes[0][1],'/pulls/1/requested_reviewers')
    def test_rerequest_uses_notification_endpoint_once(self):
        s=ReviewSession(); s.prs[1]['requested_reviewers']=[{'login':'reviewer'}]
        bot.request_review(s,1,['reviewer'],rerequest=True)
        self.assertEqual(s.writes,[('POST','/pulls/1/requested_reviewers/rerequest',{'reviewers':['reviewer']})])
    def test_refuse_draft_closed_author_missing_permissions(self):
        for case in ['draft','closed','author','permissions']:
            s=ReviewSession()
            if case=='draft': s.prs[1]['draft']=True
            if case=='closed': s.prs[1]['state']='closed'
            if case=='permissions': s.permissions={}
            with self.assertRaises(bot.BotError):
                bot.request_review(s,1,['author' if case=='author' else 'reviewer'])
            self.assertEqual(s.writes,[])
    def test_requires_verified_request(self):
        s=ReviewSession()
        orig=s.request
        def request(method,path,data=None):
            if method=='POST': return {}
            return orig(method,path,data)
        s.request=request
        with self.assertRaises(bot.BotError): bot.request_review(s,1,['reviewer'])
    def test_ambiguous_notification_is_not_retried(self):
        s=ReviewSession()
        orig=s.request
        def request(method,path,data=None):
            result=orig(method,path,data)
            if method=='POST': raise bot.BotError('lost response')
            return result
        s.request=request
        with self.assertRaises(bot.BotError): bot.request_review(s,1,['reviewer'],rerequest=True)
        self.assertEqual(len(s.writes),1)
    def test_cli(self):
        a=bot.parser().parse_args(['request-review','--pr','1','--reviewers','reviewer','--rerequest'])
        self.assertTrue(a.rerequest)
        self.assertEqual(bot.parser().parse_args(['fetch']).command,'fetch')
        self.assertEqual(bot.parser().parse_args(['pr','--pr','1']).pr,1)
        self.assertEqual(bot.parser().parse_args(['checks','--pr','1']).pr,1)
    def test_permission_report_detects_missing_reads(self):
        report=bot.permission_report({'contents':'write','pull_requests':'write','metadata':'read'})
        self.assertEqual(set(report['missing']),{'checks:read','actions:read','statuses:read'})
    def test_checks_pin_head_and_report_inaccessible(self):
        s=ReviewSession(); s.prs[1]['head']['sha']='abc123'
        orig=s.request
        def request(method,path,data=None):
            if path.startswith('/commits/abc123/check-runs'): raise bot.BotError('denied')
            if path.startswith('/commits/abc123/status'): return {'state':'pending','total_count':0,'statuses':[]}
            if path.startswith('/actions/runs?head_sha=abc123'): return {'total_count':0,'workflow_runs':[]}
            return orig(method,path,data)
        s.request=request
        result=bot.read_checks(s,1)
        self.assertEqual(result['head_sha'],'abc123')
        self.assertEqual(result['check_runs']['error'],'denied')
        self.assertEqual(result['workflow_runs']['items'],[])


class EditPrTests(unittest.TestCase):
    def test_update_only_supplied_fields_and_verify(self):
        s=ReviewSession(); orig=s.request
        def request(method,path,data=None):
            if method=='PATCH':
                s.writes.append((method,path,data)); s.prs[1].update(data)
                return copy.deepcopy(s.prs[1])
            return orig(method,path,data)
        s.request=request
        bot.edit_pr(s,1,body='New description')
        self.assertEqual(s.writes,[('PATCH','/pulls/1',{'body':'New description'})])
        self.assertEqual(bot.parser().parse_args(['edit-pr','--pr','1','--body-file','body']).pr,1)
    def test_refuse_empty_or_unconfirmed_edit(self):
        s=ReviewSession()
        with self.assertRaises(bot.BotError): bot.edit_pr(s,1)
        orig=s.request
        s.request=lambda method,path,data=None: {} if method=='PATCH' else orig(method,path,data)
        with self.assertRaises(bot.BotError): bot.edit_pr(s,1,body='New description')

if __name__=='__main__': unittest.main()
