"""Failure-path tests only; these are not live model evidence."""
import builtins
import json
import sys
from types import SimpleNamespace

from qa import live_worker, run


def test_bootstrap_exception_is_saved(monkeypatch, tmp_path):
    destination = tmp_path / 'trace.json'
    original_import = builtins.__import__

    def import_without_crewai(name, *args, **kwargs):
        if name == 'crewai':
            raise ModuleNotFoundError("No module named 'crewai'")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, '__import__', import_without_crewai)
    monkeypatch.setattr(sys, 'argv', ['worker', 'unused.json', str(destination)])
    assert live_worker.main() == 1
    record = json.loads(destination.read_text())
    assert record['error'] == "ModuleNotFoundError: No module named 'crewai'"
    assert 'import crewai as real' in record['traceback']
    assert 'total_tokens' not in record


def test_failed_worker_does_not_evaluate_quality(monkeypatch, tmp_path):
    def failed_worker(command, **kwargs):
        assert command[0] == sys.executable
        kwargs['stdout'].write('ModuleNotFoundError: test dependency missing\n')
        return SimpleNamespace(returncode=1)

    def unexpected_judge(*args):
        raise AssertionError('Judge must not run after target failure')

    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-no-request')
    monkeypatch.setattr(run.subprocess, 'run', failed_worker)
    monkeypatch.setattr(run, 'judge', unexpected_judge)
    monkeypatch.setattr(sys, 'argv', ['run', '--case', 'TC-001', '--output', str(tmp_path)])
    assert run.main() == 1
    record = json.loads((tmp_path / 'TC-001-1.evaluation.json').read_text())
    assert record['execution_status'] == 'failed'
    assert record['quality_status'] == 'not_evaluated'
    assert record['checks']['completed'] is False
    assert record['checks']['total_tokens'] is False
    for name in ('headers', 'no_directions', 'inputs_bound', 'coherence', 'judge_available'):
        assert record['checks'][name] is None
    assert 'ModuleNotFoundError' in record['worker_log']


def test_campaign_stops_on_exhausted_quota(monkeypatch, tmp_path):
    calls = []
    def exhausted_worker(command, **kwargs):
        from pathlib import Path
        calls.append(command)
        Path(command[-1]).write_text(json.dumps({
            'error': 'Gemini quota exhausted',
            'provider_calls': [{'kind': 'quota_exhausted', 'status': 429}],
        }), encoding='utf-8')
        return SimpleNamespace(returncode=1)
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-no-request')
    monkeypatch.setattr(run.subprocess, 'run', exhausted_worker)
    monkeypatch.setattr(sys, 'argv', ['run', '--case', 'TC-002,TC-003', '--output', str(tmp_path)])
    assert run.main() == 1
    assert len(calls) == 1
    campaign = json.loads((tmp_path / 'campaign.json').read_text())
    assert campaign['stopped_on_exhausted_quota'] is True
    assert campaign['skipped_cases'] == ['TC-003']
    result = json.loads((tmp_path / 'TC-002-1.evaluation.json').read_text())
    assert result['quality_status'] == 'not_evaluated'
    assert result['checks']['groundedness'] is None


def test_existing_evidence_is_never_overwritten(monkeypatch, tmp_path):
    import pytest
    evidence = tmp_path / 'TC-001-1.evaluation.json'
    evidence.write_text('existing evidence')
    monkeypatch.setenv('GEMINI_API_KEY', 'test-only-no-request')
    monkeypatch.setattr(sys, 'argv', ['run', '--case', 'TC-001', '--output', str(tmp_path)])
    with pytest.raises(SystemExit) as exc:
        run.main()
    assert exc.value.code == 2
    assert evidence.read_text() == 'existing evidence'
