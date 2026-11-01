"""Real execution only: no replayed or fabricated model results."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from qa.case_checks import case_checks
from qa.checks import format_checks, telemetry_checks, judge, METRICS


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--case', default='all', help='TC-001 etc., default all')
    parser.add_argument('--repeats', type=int, default=1)
    parser.add_argument('--output', default='results/live')
    parser.add_argument('--env-file', help='Explicit dotenv file; existing shell values take precedence')
    parser.add_argument('--interval', type=float, default=20, help='Seconds between cases/repeats (default 20)')
    args = parser.parse_args()
    if args.env_file:
        from dotenv import load_dotenv
        if not Path(args.env_file).is_file():
            parser.error('--env-file does not exist')
        load_dotenv(args.env_file, override=False)
    if args.interval < 0:
        parser.error('--interval must be nonnegative')
    if args.repeats < 1:
        parser.error('--repeats must be positive')
    if not os.environ.get('GEMINI_API_KEY'):
        parser.error('GEMINI_API_KEY required for target and independent judge; no live results generated')
    cases = json.loads((Path(__file__).resolve().parents[1]/'eval_dataset.json').read_text(encoding='utf-8'))['cases']
    requested = set(args.case.split(','))
    applicable = {c['id'] for c in cases if c['id'] != 'TC-012'}
    if args.case != 'all' and not requested <= applicable:
        parser.error('Unknown or offline-only case ID')
    selected = [c for c in cases if c['id'] != 'TC-012' and (args.case == 'all' or c['id'] in requested)]
    if not selected:
        parser.error('Unknown case ID')
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=True)
    for case in selected:
        for repetition in range(args.repeats):
            if any(out.glob(f"{case['id']}-{repetition+1}.*")):
                parser.error('Evidence already exists; choose a NEW --output directory')
    summary = []
    stopped = False
    for case in selected:
        for repetition in range(args.repeats):
            if summary:
                time.sleep(args.interval)
            started_at = datetime.now(timezone.utc).isoformat()
            prefix = out/f"{case['id']}-{repetition+1}"
            input_path = prefix.with_suffix('.input.json')
            trace_path = prefix.with_suffix('.trace.json')
            input_path.write_text(json.dumps(case), encoding='utf-8')
            trace_path.unlink(missing_ok=True)  # never reuse a stale prior run
            start = time.monotonic()
            timed_out = False
            with prefix.with_suffix('.log').open('w', encoding='utf-8') as log:
                try:
                    proc = subprocess.run([sys.executable, '-m', 'qa.live_worker', str(input_path), str(trace_path)],
                                          stdout=log, stderr=subprocess.STDOUT,
                                          env={**os.environ, 'PYTHONIOENCODING': 'utf-8'},
                                          timeout=case['limits']['latency_seconds'])
                    code = proc.returncode
                except subprocess.TimeoutExpired:
                    timed_out, code = True, -1
            record = json.loads(trace_path.read_text(encoding='utf-8')) if trace_path.exists() else {'error': 'Worker failed; see log', 'worker_log': prefix.with_suffix('.log').read_text(encoding='utf-8')}
            record['started_at_utc'] = started_at
            record['worker_exit_code'] = code
            record['timed_out'] = timed_out
            if timed_out:
                record.setdefault('error', 'Worker exceeded latency timeout')
            elif code != 0:
                record.setdefault('error', f'Worker exited with code {code}; see log')
            record['latency_seconds'] = time.monotonic()-start
            checks = telemetry_checks(record, case['limits'])
            checks['completed'] = code == 0 and not timed_out and 'error' not in record
            record['execution_status'] = 'completed' if checks['completed'] else 'failed'
            record['quality_status'] = 'evaluated' if checks['completed'] else 'not_evaluated'
            if checks['completed']:
                tasks = record.get('tasks', [])
                checks['inputs_bound'] = bool(tasks) and all('{{discussion}}' not in t['description'] and '{{script}}' not in t['description'] for t in tasks)
                text = record.get('dialogue', '')
                if case['expected'] == 'blocked':
                    checks['spam_gate'] = record.get('crew_calls') == 0
                else:
                    format_result = format_checks(text)
                    if case['id'] == 'TC-009':
                        format_result['no_directions'] = format_checks(text.replace('(a+b)', 'FORMULA'))['no_directions']
                    checks.update(format_result)
                    try:
                        record['judge_calls'] = []
                        rating = judge(case['premise'], text, record['judge_calls'])
                        record['judge'] = rating
                        checks['judge_available'] = True
                        checks.update({k: rating[k] >= case['thresholds'][k] for k in METRICS})
                    except Exception as exc:
                        record['judge_error'] = f'{type(exc).__name__}: {exc}'
                        record['judge_traceback'] = traceback.format_exc()
                        record['quality_status'] = 'partially_evaluated'
                        checks['judge_available'] = False
                        checks.update(dict.fromkeys(METRICS))
                checks.update(case_checks(case, record))
            else:
                # Null explicitly means not evaluated, never an output-quality verdict.
                names = ['inputs_bound', *METRICS, 'judge_available']
                names += (['spam_gate'] if case['expected'] == 'blocked' else list(format_checks('')))
                names += list(case_checks(case, record))
                checks.update(dict.fromkeys(names))
            record['checks'] = checks
            record['passed'] = all(value is True for value in checks.values())
            prefix.with_suffix('.evaluation.json').write_text(json.dumps(record, indent=2), encoding='utf-8')
            row = {'case': case['id'], 'repeat': repetition+1, 'passed': record['passed'], 'checks': checks,
                   'latency_seconds': record['latency_seconds'], 'total_tokens': record.get('total_tokens'),
                   'execution_status': record['execution_status'], 'quality_status': record['quality_status'],
                   'error': record.get('error')}
            summary.append(row)
            print(json.dumps(row), flush=True)
            if any(event.get('kind') == 'quota_exhausted'
                   for event in record.get('provider_calls', []) + record.get('judge_calls', [])):
                stopped = True
                break
        if stopped:
            break
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    (out/'campaign.json').write_text(json.dumps({
        'requested_cases': [c['id'] for c in selected], 'requested_repeats': args.repeats,
        'executed_runs': len(summary), 'stopped_on_exhausted_quota': stopped,
        'skipped_cases': [c['id'] for c in selected if c['id'] not in {r['case'] for r in summary}]
    }, indent=2), encoding='utf-8')
    return 0 if not stopped and all(r['passed'] for r in summary) else 1


if __name__ == '__main__':
    raise SystemExit(main())
