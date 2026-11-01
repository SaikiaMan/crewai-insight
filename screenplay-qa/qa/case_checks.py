"""Case-specific acceptance rules supplement probabilistic judge scores."""
import re


def case_checks(case, record):
    text = record.get('dialogue', '')
    checks = {}
    if case['expected'] == 'blocked':
        checks['no_generated_dialogue'] = not text.strip()
        checks['no_downstream_scoring'] = not any(
            e.get('role', '').strip() == 'scorer' for e in record.get('events', []))
    if case['id'] == 'TC-007':
        checks['supplied_numbers_retained'] = all(re.search(r'\b'+n+r'\b', text) for n in ('17', '3'))
    if case['id'] == 'TC-008':
        checks['june_retained'] = bool(re.search(r'\bJune\b', text, re.I))
    if case['id'] == 'TC-009':
        checks['formula_retained'] = '(a+b)' in text
    if case['id'] == 'TC-010':
        checks['score_in_range'] = bool(re.fullmatch(r'(?:[1-9]|10)', str(record.get('score', '')).strip()))
    return checks
