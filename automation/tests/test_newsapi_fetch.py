import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import urllib.request
import zipfile

from cryptography.fernet import Fernet, InvalidToken

spec=importlib.util.spec_from_file_location('collector',Path(__file__).parents[1]/'newsapi_fetch.py')
c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
NOW=datetime(2026,9,18,20,17,tzinfo=timezone.utc)


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.key=Fernet.generate_key()
        self.state=c.prepare_state(None,NOW,'test-1')

    def empty(self,w,key):
        return dict(status='ok',totalResults=0,articles=[])

    def test_delay_and_initial_window(self):
        self.assertEqual(len(self.state['pending']),48)
        self.assertLessEqual(c.dt(self.state['cursor']),NOW-timedelta(hours=24,minutes=15))
        self.assertTrue(all(c.dt(w['end'])-c.dt(w['start'])==timedelta(hours=1) for w in self.state['pending']))

    def test_redirect_does_not_forward_credentials(self):
        request = urllib.request.Request('https://newsapi.org/v2/everything', headers={'X-Api-Key':'fake'})
        self.assertIsNone(c.NoRedirect().redirect_request(request, None, 302, '', {}, 'https://example.com'))

    def test_non_object_response_is_error(self):
        with patch.object(c.urllib.request, 'build_opener') as opener:
            opener.return_value.open.return_value.__enter__.return_value.read.return_value = b'[]'
            response = c.fetch(self.state['pending'][0], 'fake')
        self.assertEqual(response['code'], 'invalid_response')

    def test_encryption_and_tamper_detection(self):
        cipher=c.seal({'article':'private text'},self.key)
        self.assertNotIn(b'private text',cipher)
        self.assertEqual(c.unseal(cipher,self.key)['article'],'private text')
        with self.assertRaises(InvalidToken):
            c.unseal(cipher[:-8]+b'xxxxxxxx',self.key)

    def test_crash_reservation_prevents_second_quota(self):
        later=c.prepare_state(copy.deepcopy(self.state),NOW+timedelta(minutes=2),'retry')
        self.assertEqual(later['reserved'],0)

    def test_completed_windows_not_fetched_twice(self):
        state,batch=c.collect(self.state,NOW,'fake',self.key,self.empty)
        self.assertEqual(batch['requests'],48)
        state=c.prepare_state(state,NOW+timedelta(minutes=2),'retry')
        state,batch=c.collect(state,NOW,'fake',self.key,self.empty)
        self.assertEqual(batch['requests'],0)
        self.assertFalse(state['pending'])

    def test_new_day_adds_windows_and_recovers_quota(self):
        state,_=c.collect(self.state,NOW,'fake',self.key,self.empty)
        state=c.prepare_state(state,NOW+timedelta(hours=24,minutes=16),'day2')
        self.assertEqual(len(state['pending']),24)
        self.assertEqual(state['reserved'],80)

    def test_quota_covers_requests_later_than_prepare(self):
        state,_=c.collect(self.state,NOW,'fake',self.key,self.empty)
        state=c.prepare_state(state,NOW+timedelta(hours=24,minutes=1),'day2')
        self.assertEqual(state['reserved'],32)

    def test_truncation_stays_unresolved(self):
        state,batch=c.collect(self.state,NOW,'fake',self.key,
            lambda w,k:dict(status='ok',totalResults=101,articles=[]))
        self.assertEqual(len(state['pending']),48)
        self.assertEqual(batch['coverage_status'],'incomplete')

    def test_quota_error_stops_immediately(self):
        state,batch=c.collect(self.state,NOW,'fake',self.key,
            lambda w,k:dict(status='error',code='rateLimited',http_status=429))
        self.assertEqual(batch['requests'],1)
        self.assertEqual(state['reservations'][-1]['count'],1)
        self.assertEqual(len(state['pending']),48)

    def test_provider_error_never_counts_complete(self):
        state,batch=c.collect(self.state,NOW,'fake',self.key,lambda w,k:dict(status='error',code='network_or_parse_error'))
        self.assertEqual(len(state['pending']),48)
        self.assertEqual(batch['requests'],3)

    def test_diagnostic_probe_preserves_quota_and_bounds_calls(self):
        for window in self.state['pending']:
            window['attempts']=1
            window['last_attempt']=c.iso(NOW)
        state,batch=c.collect(self.state,NOW,'fake',self.key,self.empty,probe=True)
        self.assertEqual(batch['requests'],1)
        self.assertEqual(len(state['pending']),47)
        state['reserved']=0
        _,batch=c.collect(state,NOW,'fake',self.key,self.empty,probe=True)
        self.assertEqual(batch['requests'],0)

    def test_raw_payload_and_first_seen_preserved(self):
        def request(w,k):
            return dict(status='ok',totalResults=1,articles=[dict(url='https://example.com/article',
                publishedAt=w['start'],title='Original text',source={'name':'Test'})])
        state,batch=c.collect(self.state,NOW,'fake',self.key,request)
        w=c.unseal(c.seal(batch,self.key),self.key)['windows'][0]
        self.assertEqual(w['response']['articles'][0]['title'],'Original text')
        self.assertIn('fetched_at',w)
        self.assertFalse(state['pending'])

    def test_out_of_window_article_not_complete(self):
        state,_=c.collect(self.state,NOW,'fake',self.key,
            lambda w,k:dict(status='ok',totalResults=1,articles=[dict(url='https://example.com',publishedAt=c.iso(NOW))]))
        self.assertEqual(len(state['pending']),48)

    def test_gap_expiry_is_explicit(self):
        state=c.prepare_state(self.state,NOW+timedelta(days=40),'later')
        self.assertGreater(state['expired_windows'],0)
        self.assertLessEqual(len(state['pending']),28*24)

    def test_missing_state_requires_explicit_bootstrap(self):
        with self.assertRaises(RuntimeError):c.restore(self.key,[],False)
        self.assertIsNone(c.restore(self.key,[],True))

    def test_no_fallback_from_newest_expired_state(self):
        with self.assertRaises(RuntimeError):
            c.restore(self.key,[dict(id=99,name='newsapi-state-a',expired=False,created_at=c.iso(NOW)),
                               dict(id=2,name='newsapi-state-b',expired=True,created_at=c.iso(NOW+timedelta(minutes=1)))],True)

    def test_newest_artifact_selected_by_time_not_id(self):
        payload=io.BytesIO()
        with zipfile.ZipFile(payload,'w') as z:
            z.writestr('state.enc',c.seal(self.state,self.key))
        artifacts=[dict(id=99,name='newsapi-state-old-final',expired=False,created_at=c.iso(NOW)),
                   dict(id=2,name='newsapi-state-new-final',expired=False,created_at=c.iso(NOW+timedelta(minutes=1)))]
        with patch.object(c,'gh_bytes',return_value=payload.getvalue()) as get:
            c.restore(self.key,artifacts,False)
        self.assertTrue(get.call_args.args[0].endswith('/2/zip'))

    def test_secret_whitespace_normalized_without_accepting_internal_controls(self):
        with patch.dict(os.environ, {'NEWSAPI_KEY':' fake-key\r\n'}):
            self.assertEqual(c.provider_key(),'fake-key')
        with patch.dict(os.environ, {'NEWSAPI_KEY':'fake\nkey'}):
            with self.assertRaises(ValueError): c.provider_key()

    def test_daily_budget_and_retry_backoff(self):
        state,batch=c.collect(self.state,NOW,'fake',self.key,
            lambda w,k:dict(status='ok',totalResults=101,articles=[]))
        state=c.prepare_state(state,NOW+timedelta(minutes=5),'retry')
        self.assertEqual(state['reserved'],32)
        state,batch=c.collect(state,NOW+timedelta(minutes=5),'fake',self.key,self.empty)
        self.assertEqual(batch['requests'],0)


if __name__=='__main__':unittest.main()
