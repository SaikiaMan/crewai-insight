# Loom demonstration: 5-8 minutes (aim for 6:45)

This script uses actual stored evidence. Recording and Loom/GitHub links are still pending. Record screen and voice; use a readable terminal font. Close `.env`, personal tabs and credential settings. Never show key values. Rehearse the live command before recording; a provider failure must remain visible rather than being presented as a completed generation.

## 0:00-0:40 - System and scope

"I evaluated the pinned CrewAI Screenplay Writer. It adapts discussion into two-speaker dialogue. Spam filtering and scoring are standalone tasks; analyst, scriptwriter and formatter form a sequential crew. No external tools or delegation are configured. I preserved the upstream source and all five documented defects."

Show `vendor/screenplay_writer/screenplay_writer.py` and `evidence/provenance.json`. Do not edit source. Show the actual dialogue-only requirement rather than expecting scene headers.

## 0:40-1:25 - Test strategy

Show `TEST_SUITE.md`, then the short premises for TC-002, TC-004, TC-007, TC-009 and TC-011 in `eval_dataset.json`.

"The twelve cases cover source/position retention, format, spam rejection, empty and long input, injection, supplied numbers, literal formulas, scoring, multilingual meaning and launch paths. Budgets and four semantic thresholds are explicit. I distinguish deterministic source defects, live model observations, provider failures and judge limitations. TC-012 is an offline startup test. The run counts and incomplete review coverage are listed in LIVE_RESULTS.md."

## 1:25-2:15 - Show the actual offline results

From the project directory:

```powershell
.\.venv-live\Scripts\python.exe -m pytest -q
.\.venv-live\Scripts\python.exe -m pytest tests/test_target.py --runxfail -q
```

"Normal execution gives 42 passes and five strict expected failures. Disabling xfail gives five failed and two passed target tests, exposing the actual assertions. Exit 1 here is intentional. These tests execute real upstream Python with controlled external boundaries; their synthetic outputs are not model evidence."

## 2:15-3:20 - Run a real Gemini case

```powershell
$out = "results/recording-$(Get-Date -Format yyyyMMdd-HHmmss)"
.\.venv-live\Scripts\python.exe -m qa.run --env-file .env --case TC-001 --output $out
```

While it runs, show `qa/live_worker.py` and `qa/gemini.py`:

"All five agents receive the real CrewAI LLM subclass before the vendor facade is installed. The native Gemini API preserves raw response usage instead of inventing zeros. Target and judge use separate requests, currently to the same model, so their errors and biases can be correlated. Retries are bounded and honor provider guidance; exhausted quota stops the campaign. Fresh output directories prevent evidence overwrite."

Point out the current run's actual execution status and checks. It may exit 1 because source binding fails while execution completes. If quota or network fails, explain it honestly and use the archived completed case for the rest of the demonstration.

## 3:20-4:20 - Task traces, tokens and semantic judging

Use the reviewed baseline for a stable demonstration; do not describe it as the new recording run:

```powershell
$record = Get-Content evidence/live/baseline/TC-001-1.evaluation.json -Raw | ConvertFrom-Json
$record | Select-Object execution_status, quality_status, latency_seconds, total_tokens | Format-List
$record.events | Where-Object event -eq task_end | Select-Object role, raw | Format-List
$record.judge | Format-List
$record.checks | Format-List
```

"The archived TC-001 completed in 14.64 seconds, used 2,505 target tokens, captured all five task outputs and completed independent semantic judging. Its quality still failed: the source discussion was unbound, speakers were replaced and source facts were missing. Formatting alone would have missed this. Judge usage is separate; reported latency is target worker time."

Show `LIVE_RESULTS.md` for the actual campaign totals, judge status, failed checks and per-case evidence links. Do not round a missing token count to zero or describe unavailable judging as an output-quality failure.

## 4:20-5:40 - Five defects and live evidence boundaries

Show `DEFECT_REPORT.md` with matching source lines:

1. Literal `{{discussion}}` stays in spamfilter/analyst inputs; show it in a saved task description and compare an unrelated live output with its source.
2. Exact STOP prints a warning but still runs the crew. The offline forced-STOP test proves this path. Live spamfilter output may be empty, so live nonblocking alone does not prove an exact-STOP bypass.
3. Scorer sees literal `{{script}}`; a generated score or missing-script response is not grounded scoring.
4. The regex deletes spoken `(a+b)` in the offline reproduction. Compare TC-009 before/after cleanup: if the formula was already absent, do not attribute that live loss to regex deletion.
5. Config uses the launch working directory. TC-012 reproduces FileNotFoundError offline; the live adapter's working-directory change is not an upstream repair.

"Fix proposals are documented, not silently applied. The evaluation remains a baseline of the original target."

## 5:40-6:30 - Manual review and limitations

Show the review notes in `LIVE_RESULTS.md`:

"I reviewed actual dialogue against speaker positions, supplied counts, June, formula content and language. The injection case never bound the attack into the target task, so no observed marker is not proof of injection resistance. Likewise unrelated English dialogue cannot test Hindi comprehension. Some judge coherence/policy scores disagree with the visible dialogue; I retain the original scores and flag them instead of changing thresholds. This is smoke evidence, not a calibrated reliability or hallucination-rate estimate."

## 6:30-6:45 - Close and submission state

"Priority is source binding, real rejection control flow, grounded scoring, safe cleanup and stable config resolution. The harness and evidence package are ready for review. Final completion still requires human sign-off, the Loom recording and a GitHub submission link."

After recording: confirm 5-8 minutes, replace the pending Loom URL in README, verify link access signed out, create the GitHub repository and complete SUBMISSION_CHECKLIST.md. Nothing has been published or emailed automatically.
