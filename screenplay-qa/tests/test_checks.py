import json
from pathlib import Path
import pytest
from qa.checks import format_checks, telemetry_checks, validate_judgment

GOOD = '## Alice:\nI disagree.\n\n## Bob:\nLet us discuss it.'


def test_good_format():
    assert all(format_checks(GOOD).values())


@pytest.mark.parametrize('text', ['', 'INT. ROOM - DAY\nAlice: Hi', '## Alice:\nHi.\n## Alice:\nHi.', 'Preface\n'+GOOD, '## Alice:\n\n## Bob:\nHi.', GOOD+'\n(smiles)'])
def test_bad_format(text):
    assert not all(format_checks(text).values())


@pytest.mark.parametrize('value', [None, -1, float('nan'), float('inf'), True, '12', 101])
def test_bad_telemetry(value):
    assert not telemetry_checks({'total_tokens': value}, {'total_tokens': 100})['total_tokens']


def test_budget_boundary():
    assert all(telemetry_checks({'latency_seconds': 300, 'total_tokens': 20000}, {'latency_seconds': 300, 'total_tokens': 20000}).values())


@pytest.mark.parametrize('score', [-0.1, 1.1, True, float('nan'), '0.9'])
def test_bad_judge_response(score):
    with pytest.raises(ValueError):
        validate_judgment(dict(coherence=score, voice_retention=1, policy_adherence=1, groundedness=1, evidence='reason'))


def test_dataset_contract():
    data = json.loads((Path(__file__).parents[1]/'eval_dataset.json').read_text(encoding='utf-8'))
    assert len(data['cases']) >= 10
    assert len({c['id'] for c in data['cases']}) == len(data['cases'])
    for case in data['cases']:
        assert case['premise'] is not None
        assert set(case['thresholds']) == {'coherence', 'voice_retention', 'policy_adherence', 'groundedness'}
        assert case['limits']['total_tokens'] > 0


def test_judge_http_contract(monkeypatch):
    import io
    from qa.checks import judge
    received = []
    rating = dict(coherence=.9, voice_retention=.9, policy_adherence=1, groundedness=1, evidence='Positions retained.')
    def fake_urlopen(request, timeout):
        received.append(json.loads(request.data))
        assert timeout == 60
        return io.BytesIO(json.dumps({'candidates': [{'finishReason': 'STOP', 'content': {'parts': [{'text': json.dumps(rating)}]}}]}).encode())
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-for-contract-test')
    monkeypatch.setattr('urllib.request.urlopen', fake_urlopen)
    assert judge('source data', GOOD) == rating
    assert received[0]['generationConfig']['responseMimeType'] == 'application/json'
    assert json.loads(received[0]['contents'][0]['parts'][0]['text'])['source'] == 'source data'


def test_judge_requires_evidence():
    with pytest.raises(ValueError):
        validate_judgment(dict(coherence=1, voice_retention=1, policy_adherence=1, groundedness=1, evidence=''))


def test_pinned_source_integrity():
    import hashlib
    root = Path(__file__).parents[1]
    metadata = json.loads((root/'evidence/provenance.json').read_text(encoding='utf-8'))
    for relative, expected in metadata['sha256'].items():
        assert hashlib.sha256((root/relative).read_bytes()).hexdigest() == expected
