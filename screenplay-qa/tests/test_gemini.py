"""Synthetic transport contracts; never live-generation evidence."""
import io
import json
import urllib.error
import pytest
from qa.gemini import generate, retry_policy, total_tokens, GeminiError


def test_retry_guidance_and_budget():
    payload = {'error': {'details': [{'@type': 'type.googleapis.com/google.rpc.RetryInfo', 'retryDelay': '12.5s'}]}}
    assert retry_policy(429, payload, {'Retry-After': '20'}, 0) == ('transient_rate_limit', 20)
    assert retry_policy(429, payload, {}, 2)[1] is None
    assert retry_policy(429, payload, {'Retry-After': '90'}, 0)[1] is None
    assert retry_policy(403, {}, {}, 0) == ('provider_error', None)


@pytest.mark.parametrize('message', ['quota exceeded per day', 'billing disabled', 'limit: 0'])
def test_exhausted_quota_is_not_retried(message):
    assert retry_policy(429, {'error': {'message': message}}, {}, 0) == ('quota_exhausted', None)


def test_real_usage_required():
    assert total_tokens([]) is None
    assert total_tokens([{'response': {}}]) is None
    assert total_tokens([{'response': {'usageMetadata': {'totalTokenCount': True}}}]) is None
    assert total_tokens([{'response': {'usageMetadata': {'totalTokenCount': 19}}}]) == 19


def test_transport_retries_and_preserves_provider_evidence(monkeypatch):
    calls, waits, evidence = [], [], []
    def urlopen(request, timeout):
        calls.append(request)
        assert request.full_url.endswith('/gemini-test:generateContent')
        assert 'key=' not in request.full_url
        if len(calls) < 3:
            raise urllib.error.HTTPError(request.full_url, 429, 'rate limit', {'Retry-After': '3'},
                                         io.BytesIO(b'{"error":{"message":"too many requests"}}'))
        return io.BytesIO(json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': 'actual transport fixture'}]}}],
                                     'usageMetadata': {'totalTokenCount': 23}}).encode())
    monkeypatch.setenv('GEMINI_API_KEY', 'contract-test-only')
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    monkeypatch.setattr('qa.gemini.time.sleep', waits.append)
    assert generate('gemini-test', [{'role': 'user', 'content': 'hello'}], events=evidence) == 'actual transport fixture'
    assert len(calls) == 3
    assert waits == [3, 3]
    assert evidence[0]['status'] == 429
    assert total_tokens(evidence) == 23


def test_retry_count_is_bounded(monkeypatch):
    calls = []
    def urlopen(request, timeout):
        calls.append(1)
        raise urllib.error.HTTPError(request.full_url, 429, 'rate limit', {}, io.BytesIO(b'{"error":{}}'))
    monkeypatch.setenv('GEMINI_API_KEY', 'contract-test-only')
    monkeypatch.setattr('urllib.request.urlopen', urlopen)
    monkeypatch.setattr('qa.gemini.time.sleep', lambda seconds: None)
    with pytest.raises(GeminiError, match='transient_rate_limit'):
        generate('gemini-test', [{'role': 'user', 'content': 'hello'}])
    assert len(calls) == 3


def test_adapter_uses_saved_llm_inside_vendor_facade(monkeypatch):
    import sys
    import types
    from qa.gemini import target_llm

    class SavedLLM:
        def __init__(self, **kwargs):
            self.model = kwargs['model']

    # Reproduce the module replacement that previously broke the lazy import.
    monkeypatch.setitem(sys.modules, 'crewai', types.ModuleType('crewai'))
    adapter = target_llm([], SavedLLM)
    assert isinstance(adapter, SavedLLM)
    assert adapter.model.startswith('gemini-')
