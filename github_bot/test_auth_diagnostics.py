import contextlib
import io
from email.message import Message
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError
import github_bot as bot

class DiagnosticsTests(unittest.TestCase):
    def fail_http(self, code, headers=None, token='installation-secret'):
        h=Message()
        for key,value in (headers or {}).items(): h[key]=value
        err=HTTPError('https://api.github.com/users/example%5Bbot%5D',code,'secret response',h,io.BytesIO(b'private-key-and-token'))
        opener=Mock();opener.open.side_effect=err
        with patch.object(bot.urllib.request,'build_opener',return_value=opener):
            with self.assertRaises(bot.BotError) as caught:
                bot.api('GET','/users/example%5Bbot%5D',token)
        message=str(caught.exception)
        self.assertNotIn('installation-secret',message)
        self.assertNotIn('private-key-and-token',message)
        self.assertNotIn('secret response',message)
        return message
    def test_exhausted_primary_rate_limit(self):
        m=self.fail_http(403,{'X-RateLimit-Remaining':'0','X-RateLimit-Limit':'5000','X-RateLimit-Reset':'1900000000'})
        self.assertIn('primary rate limit exhausted',m)
        self.assertIn('remaining=0',m);self.assertIn('reset_epoch=1900000000',m)
        self.assertIn('authenticated',m)
    def test_retry_after_without_exhaustion(self):
        m=self.fail_http(429,{'Retry-After':'60','X-RateLimit-Remaining':'40'})
        self.assertIn('retry_after_seconds=60',m)
        self.assertIn('rate limit',m)
    def test_ambiguous_403_does_not_claim_permissions_or_stacks(self):
        m=self.fail_http(403)
        self.assertIn('cause is not established',m)
        self.assertNotIn('stack',m.lower())
    def test_unauthenticated_request_is_identified(self):
        self.assertIn('unauthenticated',self.fail_http(403,token=None))
    def test_untrusted_headers_are_not_echoed(self):
        m=self.fail_http(403,{'Retry-After':'installation-secret','X-RateLimit-Remaining':'123 installation-secret','X-RateLimit-Reset':'9'*100,'X-Secret':'private-key-and-token'})
        self.assertNotIn('retry_after_seconds=',m)
        self.assertNotIn('remaining=',m)
        self.assertNotIn('reset_epoch=',m)

class CleanupTests(unittest.TestCase):
    def config(self): return {'repository':'owner/repo','app_id':1,'installation_id':2}
    def prefix(self,grant=None):
        return [{'id':1,'slug':'bot'},{'account':{'login':'owner'}},grant or {'token':'test-token','permissions':{},'expires_at':'later'}]
    def test_malformed_grant_metadata_revokes_created_token(self):
        s=bot.Session(self.config())
        with patch.object(bot,'jwt',return_value='jwt'),patch.object(bot,'api') as api:
            api.side_effect=self.prefix({'token':'test-token'})+[None]
            with self.assertRaises(KeyError): s.__enter__()
            self.assertEqual(api.call_args_list[-1].args,('DELETE','/installation/token','test-token'))
            self.assertIsNone(s.token)
    def test_parse_error_during_identity_revokes_created_token(self):
        s=bot.Session(self.config())
        with patch.object(bot,'jwt',return_value='jwt'),patch.object(bot,'api') as api:
            api.side_effect=self.prefix()+[ValueError('invalid JSON'),None]
            with self.assertRaises(ValueError): s.__enter__()
            self.assertEqual(api.call_args_list[-1].args,('DELETE','/installation/token','test-token'))
            self.assertIsNone(s.token)
    def test_revoke_failure_preserves_original_error_and_clears_token(self):
        s=bot.Session(self.config())
        with patch.object(bot,'jwt',return_value='jwt'),patch.object(bot,'api') as api,contextlib.redirect_stderr(io.StringIO()) as stderr:
            api.side_effect=self.prefix()+[bot.BotError('identity failed'),ValueError('revocation parse failed secret')]
            with self.assertRaisesRegex(bot.BotError,'identity failed'): s.__enter__()
            self.assertIsNone(s.token)
            self.assertNotIn('secret',stderr.getvalue())

if __name__=='__main__': unittest.main()
