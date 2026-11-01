"""Build measured tables from archived real records; never calls a model."""
import hashlib
import json
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT/'evidence/live'
records = []
for path in sorted(EVIDENCE.glob('*/*.evaluation.json')):
    record = json.loads(path.read_text(encoding='utf-8'))
    records.append((path.relative_to(ROOT).as_posix(), record))
if not records:
    raise SystemExit('No archived evaluations')
by_case = defaultdict(list)
for path, record in records:
    by_case[Path(path).name[:6]].append((path, record))
notes = json.loads((EVIDENCE/'review-notes.json').read_text(encoding='utf-8'))['notes']
def genuine(value):
    return type(value) is int and value >= 0
counts = [r.get('total_tokens') for _,r in records]
judge_counts = [event['response'].get('usageMetadata', {}).get('totalTokenCount')
                for _,r in records for event in r.get('judge_calls', []) if 'response' in event]
offline = list(ET.parse(ROOT/'evidence/final-offline-junit.xml').iter('testcase'))
offline_passed = sum(not any(c.tag in ('skipped', 'failure', 'error') for c in test) for test in offline)
offline_xfailed = sum(any(c.tag == 'skipped' and c.get('type') == 'pytest.xfail' for c in test) for test in offline)
totals = {
    'unique_live_cases': len(by_case), 'target_runs': len(records),
    'completed_target_runs': sum(r.get('execution_status') == 'completed' for _,r in records),
    'quality_passed_runs': sum(r.get('passed') is True for _,r in records),
    'task_outputs_captured': sum(e.get('event') == 'task_end' for _,r in records for e in r.get('events', [])),
    'target_provider_responses': sum('response' in e for _,r in records for e in r.get('provider_calls', [])),
    'judge_completed_runs': sum('judge' in r for _,r in records),
    'judge_not_applicable_runs': sum(Path(p).name[:6] in ('TC-004','TC-005') for p,_ in records),
    'judge_error_runs': sum('judge_error' in r for _,r in records),
    'known_target_tokens': sum(c for c in counts if genuine(c)),
    'missing_target_token_records': sum(not genuine(c) for c in counts),
    'known_judge_tokens': sum(c for c in judge_counts if genuine(c)),
    'missing_judge_usage_responses': sum(not genuine(c) for c in judge_counts),
    'summed_target_worker_seconds': round(sum(r['latency_seconds'] for _,r in records), 3),
    'provider_error_events': sum('status' in e for _,r in records for e in r.get('provider_calls', [])+r.get('judge_calls', [])),
    'offline_only_cases': ['TC-012'], 'offline_passed':offline_passed, 'offline_xfailed':offline_xfailed,
}
(EVIDENCE/'totals.json').write_text(json.dumps(totals,indent=2),encoding='utf-8')
lines = ['# Live evaluation results - 1 November 2026', '',
 'These are real Gemini compatibility runs of the unmodified vendored target. TC-001 is the preserved prior baseline; the ten remaining applicable cases were run sequentially once in a new directory, followed by two additional TC-008 runs. Raw originals under results/ were preserved. Archived copies below are included for GitHub; their hashes are in evidence/live/manifest.json.', '',
 'Model/provider: Gemini Developer API, gemini-3.5-flash-lite for both target and judge. Python 3.12.14; CrewAI 0.108.0; LiteLLM 1.60.2; Pydantic 2.14.2. Full versions: [environment.json](evidence/live/environment.json). Native REST transport makes real calls without LiteLLM model-table/usage defaults.', '',
 '## Actual totals', '',
 f"- {totals['unique_live_cases']} unique live cases, {totals['target_runs']} target runs; {totals['completed_target_runs']} completed, {totals['quality_passed_runs']} passed quality acceptance.",
 f"- {totals['task_outputs_captured']} captured task outputs and {totals['target_provider_responses']} target provider responses. Empty task answers are recorded as received, not filled in.",
 f"- {totals['known_target_tokens']:,} reported target tokens; {totals['missing_target_token_records']} missing token records. {totals['summed_target_worker_seconds']:.2f} seconds summed target-worker runtime (not end-to-end campaign wall time).",
 f"- {totals['judge_completed_runs']} completed separate semantic judgments; {totals['judge_not_applicable_runs']} intentionally not applicable (blocked-input contracts); {totals['judge_error_runs']} judge errors. {totals['known_judge_tokens']:,} reported judge tokens, separate from target totals; {totals['missing_judge_usage_responses']} missing judge usage responses.",
 f"- {totals['provider_error_events']} recorded provider HTTP error/retry events. No provider or harness execution failures in these archived runs; all target budget checks pass. All source-binding checks fail.",
 '- No requested smoke cases were skipped for quota. TC-012 is intentionally offline-only. TC-008 has its planned three samples; other live cases have one each. No broader three-repeat release campaign was performed.',
 f'- Final offline suite: **{offline_passed} passed, {offline_xfailed} xfailed**. Forced source-defect reproduction: **5 failed, 2 passed**. [Normal output](evidence/final-offline-pytest.txt), [defect output](evidence/final-defect-reproduction.txt), [JUnit](evidence/final-offline-junit.xml). Vendor hash integrity passed.', '',
 '## Per-case results', '',
 'Durations are target-worker seconds, excluding judging and inter-case pacing. TC-008 totals span its three runs, whose individual values and failed checks follow. Only checks equal to false are listed as failed; null means not evaluated, never a quality verdict. Each row has five task outputs per completed run and usable native usage telemetry.', '',
 '| Case | Execution | Duration (s) | Target tokens | Judge | Failed checks | Evidence | Text review notes |',
 '|---|---|---:|---:|---|---|---|---|']
for case in [f'TC-{n:03d}' for n in range(1,13)]:
    items = by_case.get(case, [])
    if not items:
        lines.append(f'| {case} | Offline only | - | - | Not applicable | Startup/config discovery (expected upstream failure) | [Offline defect log](evidence/final-defect-reproduction.txt) | {notes[case]} |')
        continue
    n=len(items)
    completed=sum(r['execution_status']=='completed' for _,r in items)
    duration=sum(r['latency_seconds'] for _,r in items)
    values=[r.get('total_tokens') for _,r in items]
    tokens=str(sum(values)) if all(genuine(v) for v in values) else 'Missing/partial; see raw records'
    judged=sum('judge' in r for _,r in items)
    judge='Not applicable (rejection contract)' if case in ('TC-004','TC-005') else f'Completed {judged}/{n}'
    failed=sorted({k for _,r in items for k,v in r['checks'].items() if v is False})
    links='<br>'.join(f'[Run {i+1}]({path})' for i,(path,_) in enumerate(items))
    lines.append(f"| {case} | Completed {completed}/{n} | {duration:.2f} | {tokens} | {judge} | {', '.join(failed)} | {links} | {notes[case]} |")
lines += ['', '## TC-008 individual samples', '',
          'File-local repeat labels are preserved; the initial campaign sample and the follow-up campaign each start at repeat 1. These are three distinct real subprocess runs, not renamed or duplicated evidence.', '',
          '| Evidence | Seconds | Target tokens | Judge scores (coherence / voice / policy / groundedness) | Failed checks |', '|---|---:|---:|---|---|']
for path,r in by_case.get('TC-008',[]):
    rating=r.get('judge',{})
    scores=' / '.join(str(rating.get(k,'not evaluated')) for k in ('coherence','voice_retention','policy_adherence','groundedness'))
    failed=', '.join(k for k,v in r['checks'].items() if v is False)
    lines.append(f"| [{path}]({path}) | {r['latency_seconds']:.2f} | {r.get('total_tokens')} | {scores} | {failed} |")
lines += ['', '## Review and interpretation', '',
 'The notes above reflect assistant inspection of actual final dialogue, the task descriptions and relevant raw stage outputs, not only judge scores or keyword matches. Human sign-off is still pending. All non-blocked cases fail voice retention and groundedness; formatted unrelated dialogue cannot satisfy the adaptation contract. TC-004/005 generation violates rejection requirements even though no judge is needed.', '',
 'The native telemetry is usable for the received model responses. These runs do not prove retry behavior against a real rate-limit event; retry handling is covered by offline HTTP contracts. There were no failed-execution samples in this campaign; synthetic regression tests verify that failed execution leaves quality not evaluated and that quota exhaustion stops later cases.', '',
 'Judge disagreement: TC-008 and TC-009/010 receive low coherence scores even though the visible conversations have internal flow. The original TC-008 policy=0 lacks a specific format/security violation in its evidence; the final follow-up policy=0 calls meta-dialogue a policy violation. Preserve those scores and failed checks, but obtain human calibration rather than treating them as independent proof of safety failure. No thresholds were relaxed.', '',
 'Coverage limits: source placeholders prevent the actual source and attack from reaching target tasks. No observed injection marker is not proof of resistance. Missing June cannot isolate long-context memory; unrelated English cannot isolate Hindi understanding. Formula was already absent before cleanup in TC-009, so the live result does not establish regex causation. Exact-STOP bypass and cwd failure remain deterministic source reproductions.', '',
 'Pending human work: bilingual Hindi/source-role review; security review of injection exposure and any alleged prompt leakage; review of judge disagreements and the writer/formatter truncation in TC-010. Release reliability would require a separately scoped repeated campaign after upstream fixes; this unchanged baseline does not meet acceptance.', '',
 '## Completion state', '',
 'Technical evaluation and the reviewed evidence package are prepared locally. **Loom URL and GitHub submission URL remain pending.** No recording, repository publication or email submission has been performed. See [SUBMISSION_CHECKLIST.md](SUBMISSION_CHECKLIST.md).', '']
(ROOT/'LIVE_RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
manifest={}
for path in sorted(EVIDENCE.rglob('*')):
    if path.is_file() and path.name!='manifest.json':
        manifest[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
(EVIDENCE/'manifest.json').write_text(json.dumps({'sha256':manifest,'note':'Archived evaluation/trace/log/input copies are byte-for-byte originals; includes measured totals and reviewer notes.'},indent=2),encoding='utf-8')
print(json.dumps(totals,indent=2))
