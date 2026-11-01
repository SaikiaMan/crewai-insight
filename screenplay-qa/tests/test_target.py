"""Expected failures execute original upstream control flow, not a reimplementation."""
import re
import pytest
from qa.target import execute_target


@pytest.mark.xfail(strict=True, reason='BUG-001: no discussion interpolation')
def test_discussion_is_bound():
    trace = execute_target()
    descriptions = [t.description for t in trace['tasks'][:2]]
    assert all('{{discussion}}' not in d for d in descriptions)
    assert 'Keith' in descriptions[0]


@pytest.mark.xfail(strict=True, reason='BUG-002: STOP never stops crew')
def test_spam_stop_blocks_pipeline():
    trace = execute_target(spam='STOP')
    assert trace['crew_calls'] == 0


@pytest.mark.xfail(strict=True, reason='BUG-003: scorer never receives generated script')
def test_scorer_receives_output():
    trace = execute_target(dialogue='## Alice:\nUniqueLine734.\n\n## Bob:\nYes.')
    assert 'UniqueLine734' in trace['tasks'][-1].description
    assert '{{script}}' not in trace['tasks'][-1].description


@pytest.mark.xfail(strict=True, reason='BUG-004: regex deletes legitimate spoken text')
def test_parentheses_do_not_destroy_spoken_facts():
    trace = execute_target(dialogue='## Alice:\nUse the formula (a+b).\n\n## Bob:\nAgreed.')
    assert '(a+b)' in trace['stdout']


@pytest.mark.xfail(strict=True, reason='BUG-005: configuration paths depend on launch directory')
def test_launch_from_repo_root(tmp_path):
    execute_target(cwd=tmp_path)


def test_actual_orchestration_contract():
    trace = execute_target()
    assert trace['crew_calls'] == 1
    assert len(trace['tasks']) == 5
    assert trace['crew_config']['process'] == 'sequential'
    assert [t.agent.kwargs['config']['role'].strip() for t in trace['crew_config']['tasks']] == ['analyse', 'scriptwriter', 'formatter']
    assert all(not a.kwargs['allow_delegation'] for a in trace['crew_config']['agents'])
    assert all('tools' not in a.kwargs for a in trace['crew_config']['agents'])


def test_multiline_direction_cleanup_limitation():
    trace = execute_target(dialogue='## Alice:\n(looks\naway)\nHello.\n## Bob:\nHi.')
    assert '(looks\naway)' in trace['stdout']  # observed limitation, not a quality pass
