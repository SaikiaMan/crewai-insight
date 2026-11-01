# CrewAI Screenplay QA Assignment

A reproducible quality evaluation of the CrewAI Screenplay Writer example, covering discussion-to-dialogue generation, source fidelity, spam rejection, formatting, and execution telemetry.

The project includes 12 test cases, a structured evaluation dataset, offline regression tests, an optional Gemini evaluation runner, and preserved evidence. The upstream implementation is retained for auditing; its known defects are intentionally reproduced.

## Recorded results

- **Offline suite:** 42 passed and 5 expected failures.
- **Live campaign:** 13 target runs completed across 11 cases, producing 65 task outputs and 11 semantic judgments.
- **Quality outcome:** 0 live runs met every quality check. Completed execution does not imply correct output.

These are recorded results, not a fresh run. See the [live results and limitations](screenplay-qa/LIVE_RESULTS.md) and [defect report](screenplay-qa/DEFECT_REPORT.md) for evidence and interpretation.

## Quick start

Use Python 3.12. Run the following PowerShell commands from the repository root:

```powershell
cd screenplay-qa
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest -q
```

Offline tests require no API keys or model calls. Five tests are marked as expected failures because they demonstrate known upstream defects. To expose their assertions directly:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_target.py --runxfail -q
```

That command intentionally returns a nonzero exit code when the defects reproduce.

## Optional live evaluation

From `screenplay-qa`, install the live dependencies and create your local configuration:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-live.txt
Copy-Item .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. Keep credentials local and out of commits. `TARGET_MODEL` and `JUDGE_MODEL` can be configured with bare Gemini model IDs; see `.env.example` for defaults. Live calls require provider access and may incur charges.

Run a single case with a unique evidence directory:

```powershell
$output = "results/smoke-$(Get-Date -Format yyyyMMdd-HHmmss)"
.\.venv\Scripts\python.exe -m qa.run --env-file .env --case TC-001 --output $output
```

For the full live smoke campaign:

```powershell
$output = "results/campaign-$(Get-Date -Format yyyyMMdd-HHmmss)"
.\.venv\Scripts\python.exe -m qa.run --env-file .env --interval 20 --output $output
```

TC-012 is offline-only and is excluded from the live campaign. The runner preserves logs, traces, evaluations, and campaign summaries. A nonzero exit can indicate a measured quality failure; inspect the recorded execution status and checks. Existing case evidence is not overwritten.

## Project guide

| Path | Contents |
| --- | --- |
| [screenplay-qa/README.md](screenplay-qa/README.md) | Detailed setup, architecture, evaluation boundaries, and provider behavior |
| [TEST_SUITE.md](screenplay-qa/TEST_SUITE.md) | 12 cases, acceptance criteria, and thresholds |
| [eval_dataset.json](screenplay-qa/eval_dataset.json) | Case inputs and execution budgets |
| [qa/](screenplay-qa/qa/) | Target execution, live runner, checks, and Gemini adapter |
| [tests/](screenplay-qa/tests/) | Offline regressions and evaluator tests |
| [DEFECT_REPORT.md](screenplay-qa/DEFECT_REPORT.md) | Five reproduced upstream defects and proposed fixes |
| [LIVE_RESULTS.md](screenplay-qa/LIVE_RESULTS.md) | Measured outcomes and manual review notes |
| [evidence/](screenplay-qa/evidence/) | Preserved test output, live traces, and provenance |
| [vendor/screenplay_writer/](screenplay-qa/vendor/screenplay_writer/) | Upstream source snapshot |
| [SUBMISSION_CHECKLIST.md](screenplay-qa/SUBMISSION_CHECKLIST.md) | Submission preparation checklist |
| [VIDEO_SCRIPT.md](screenplay-qa/VIDEO_SCRIPT.md) | Walkthrough recording guide |

## Evaluation boundaries

Offline tests exercise the original Python source with controlled framework responses. Live evaluation uses a compatibility facade for the modern CrewAI API and injects dataset input without repairing the upstream prompt placeholders or spam gate. Target and judge use separate calls but currently share a model, so their judgments may be correlated. The campaign is smoke-test evidence, not a reliability estimate.

## Attribution

The upstream Screenplay Writer example is by Toon Beerten from [crewAIInc/crewAI-examples](https://github.com/crewAIInc/crewAI-examples), preserved at revision `da94a91e691e1cf5b3151416bb15b5b62729bea8`. Its README declares the MIT License. See the [original README](screenplay-qa/vendor/screenplay_writer/README.md) and [provenance record](screenplay-qa/evidence/provenance.json) for source details.
