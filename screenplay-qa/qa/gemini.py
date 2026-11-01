"""Gemini REST transport; no SDK retries, replay, or inferred token usage."""
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

DEFAULT_MODEL = 'gemini-3.5-flash-lite'
MAX_ATTEMPTS = 3
MAX_WAIT = 60


def model_name(variable):
    model = os.environ.get(variable, DEFAULT_MODEL)
    if not re.fullmatch(r'gemini-[a-zA-Z0-9.-]+', model):
        raise ValueError(f'{variable} must be a bare Gemini model ID')
    return model


class GeminiError(RuntimeError):
    def __init__(self, status, payload, kind):
        self.status, self.payload, self.kind = status, payload, kind
        super().__init__(f'Gemini HTTP {status} ({kind}): {json.dumps(payload)}')


def retry_policy(status, payload, headers, attempt):
    text = json.dumps(payload).lower()
    exhausted = any(s in text for s in (
        'perday', 'per_day', 'per day', 'daily', 'credit_balance',
        'insufficient_quota', 'billing', 'limit: 0', 'quota exhausted'))
    if exhausted:
        return 'quota_exhausted', None
    if status not in (429, 500, 502, 503, 504):
        return 'provider_error', None
    kind = 'transient_rate_limit' if status == 429 else 'transient_server_error'
    waits = [2 ** attempt]
    retry_after = headers.get('Retry-After')
    if retry_after:
        try:
            waits.append(float(retry_after))
        except ValueError:
            try:
                waits.append((parsedate_to_datetime(retry_after) - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                pass
    for detail in payload.get('error', {}).get('details', []):
        if detail.get('@type', '').endswith('RetryInfo'):
            delay = detail.get('retryDelay', '')
            if re.fullmatch(r'[0-9.]+s', delay):
                waits.append(float(delay[:-1]))
        if detail.get('@type', '').endswith('QuotaFailure'):
            for violation in detail.get('violations', []):
                if str(violation.get('quotaValue', '')) == '0':
                    return 'quota_exhausted', None
    wait = max(waits)
    # Do not shorten provider guidance to fit our budget: stop instead.
    return kind, wait if wait <= MAX_WAIT and attempt < MAX_ATTEMPTS - 1 else None


def generate(model, messages, *, json_mode=False, events=None):
    system = []
    contents = []
    for message in messages:
        if message['role'] == 'system':
            system.append({'text': message['content']})
        else:
            contents.append({'role': 'model' if message['role'] == 'assistant' else 'user',
                             'parts': [{'text': message['content']}]})
    body = {'contents': contents}
    if system:
        body['systemInstruction'] = {'parts': system}
    if json_mode:
        body['generationConfig'] = {'temperature': 0, 'responseMimeType': 'application/json'}
    request = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent',
        data=json.dumps(body).encode('utf-8'),
        headers={'x-goog-api-key': os.environ['GEMINI_API_KEY'], 'Content-Type': 'application/json'})
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                result = json.load(response)
            if events is not None:
                events.append({'model': model, 'response': result})
            candidates = result.get('candidates', [])
            if not candidates or candidates[0].get('finishReason') != 'STOP':
                raise ValueError('Gemini did not return a completed candidate; see response evidence')
            text = ''.join(p.get('text', '') for p in candidates[0].get('content', {}).get('parts', [])
                           if not p.get('thought'))
            if not text.strip():
                raise ValueError('Gemini returned no text; see response evidence')
            return text
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode('utf-8', errors='replace')
            try:
                payload = json.loads(raw)
            except ValueError:
                payload = {'error': {'message': raw}}
            kind, wait = retry_policy(exc.code, payload, exc.headers, attempt)
            if events is not None:
                events.append({'model': model, 'attempt': attempt + 1, 'status': exc.code,
                               'kind': kind, 'error': payload, 'retry_seconds': wait})
            if wait is None:
                raise GeminiError(exc.code, payload, kind) from None
            time.sleep(wait)


def target_llm(events, llm_class):
    # The caller saves the real class before installing the vendor facade.
    class GeminiLLM(llm_class):
        def __init__(self):
            super().__init__(model=model_name('TARGET_MODEL'), timeout=60)

        def supports_function_calling(self):
            return False

        def supports_stop_words(self):
            return False

        def call(self, messages, tools=None, callbacks=None, available_functions=None):
            if tools:
                raise ValueError('This target has no tools; Gemini adapter does not implement tools')
            if isinstance(messages, str):
                messages = [{'role': 'user', 'content': messages}]
            return generate(self.model, messages, events=events)

    return GeminiLLM()


def total_tokens(events):
    responses = [event['response'] for event in events if 'response' in event]
    counts = [response.get('usageMetadata', {}).get('totalTokenCount') for response in responses]
    if not counts or any(type(count) is not int or count < 0 for count in counts):
        return None
    return sum(counts)
