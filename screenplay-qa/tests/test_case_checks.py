from qa.case_checks import case_checks


def test_formula_loss_detected():
    assert not case_checks({'id': 'TC-009', 'expected': 'dialogue'}, {'dialogue': 'Use the formula .'})['formula_retained']


def test_out_of_range_score_detected():
    assert not case_checks({'id': 'TC-010', 'expected': 'dialogue'}, {'score': '11'})['score_in_range']


def test_blocked_case_cannot_generate():
    checks = case_checks({'id': 'TC-004', 'expected': 'blocked'}, {'dialogue': 'A script', 'events': [{'role': 'scorer'}]})
    assert not any(checks.values())


def test_number_loss_detected():
    assert not case_checks({'id': 'TC-007', 'expected': 'dialogue'}, {'dialogue': 'There are 17 lamps.'})['supplied_numbers_retained']
