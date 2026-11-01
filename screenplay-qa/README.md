# CrewAI Screenplay Writer — AI QA Assignment

Manob Raj Saikia · AI Quality & Automation Engineer evaluation

A reproducible evaluation of the real CrewAI discussion-to-dialogue example, with 12 manual cases, a structured dataset, deterministic source-execution regressions, and opt-in live semantic evaluation.

**Recorded result:** 42 passed, 5 expected upstream failures. Real Gemini evidence and case-by-case conclusions are in [LIVE_RESULTS.md](LIVE_RESULTS.md). The five upstream defects remain observable.

**Loom URL: PENDING — record using VIDEO_SCRIPT.md and replace this line before submission.**

**GitHub submission URL: PENDING**

## Setup and commands

Use Python 3.12; CrewAI 0.108.0 requires >=3.10,<3.13. These commands run from the `screenplay-qa` project directory.

For a new standard Python virtual environment:

```powershell
py -3.12 -m venv .venv-live
.\.venv-live\Scripts\python.exe -m pip install -r requirements-live.txt
.\.venv-live\Scripts\python.exe -m pip check
```

The existing environment used for this submission was created with uv and has no pip module. Do not reinstall it just for recording. To install/check dependencies in that environment, use:

```powershell
uv pip install --python .venv-live\Scripts\python.exe -r requirements-live.txt
uv pip check --python .venv-live\Scripts\python.exe
```

For offline-only setup, install `requirements.txt` instead. Offline tests do not require credentials, CrewAI or model calls:

```powershell
.\.venv-live\Scripts\python.exe -m pytest -q
.\.venv-live\Scripts\python.exe -m pytest tests/test_target.py --runxfail -q
```

`--runxfail` intentionally exits 1 and exposes the five real defect assertions. Strict xfails are never counted as passed product requirements. Synthetic transport tests are not model evidence.

For live runs, create a local `.env` using `.env.example` as a template if needed. Set `GEMINI_API_KEY` there without committing it. The optional `TARGET_MODEL` and `JUDGE_MODEL` default to `gemini-3.5-flash-lite`; use bare model IDs, with no `gemini/` prefix. OpenAI credentials are unused. Existing shell variables take precedence over `.env`.

```powershell
# Explicitly load .env; do not display its contents during recording.
$out = "results/recording-$(Get-Date -Format yyyyMMdd-HHmmss)"
.\.venv-live\Scripts\python.exe -m qa.run --env-file .env --case TC-001 --output $out
# Sequential full smoke campaign, excluding offline-only TC-012:
.\.venv-live\Scripts\python.exe -m qa.run --env-file .env --interval 20 --output "results/campaign-$(Get-Date -Format yyyyMMdd-HHmmss)"
```

A comma-separated `--case TC-002,TC-003` selects a subset. `--repeats` defaults to 1. The runner refuses to overwrite existing case evidence. Exit 1 can mean a measured target-quality failure even when execution and judging completed: inspect `execution_status`, `quality_status`, `checks` and the underlying error separately. A missing key exits at preflight without fabricated results.

## Recorded results and evidence

See [LIVE_RESULTS.md](LIVE_RESULTS.md) for per-case evidence and review notes. Actual totals: **13/13 target runs completed across 11 live cases, 65 task outputs, 39,420 target tokens, 11 completed semantic judgments, and 0 quality passes**. Two rejection-contract cases intentionally have no semantic judge. TC-008 has three samples; TC-012 remains offline. No provider/harness execution failure or missing telemetry occurred in this campaign. Final offline result: **42 passed, 5 xfailed**; forced source-defect reproduction: **5 failed, 2 passed**. Recorded outputs and JUnit XML are under `evidence/final-*`. The vendor hash-integrity test passed.

The preserved TC-001 baseline completed in 14.64 seconds using 2,505 target tokens, with five task outputs and a completed judge. Its failed source binding, voice retention and groundedness are quality failures, not harness crashes. The remaining campaign preserves each actual output under `evidence/live/`; earlier logs under `results/` are not overwritten. Historical offline evidence and `live-preflight.txt` describe earlier states and are not the current results.

The target uses Gemini through a saved real CrewAI LLM class; the temporary vendor facade does not supply the adapter's base class. Tested Python/package versions and the full installed package list are in `evidence/live/environment.json`. Real target calls, task outputs, native response token telemetry and separate JSON judge calls have been validated. The transitive graph is recorded, not fully locked.

## Gemini behavior and limits

Checked official documentation on 1 November 2026: Google's [pricing table](https://ai.google.dev/gemini-api/docs/pricing) lists free-tier text input/output for Gemini 3.5 Flash-Lite. Its [deprecation page](https://ai.google.dev/gemini-api/docs/deprecations) recommends 3.5 Flash-Lite or 3.8 Flash for new projects and restricts 2.5 access to prior users. Check account/region eligibility and actual quotas in [AI Studio](https://aistudio.google.com/). A paid project can incur charges; no model or provider fallback is used.

`qa/gemini.py` calls the native [generateContent REST API](https://ai.google.dev/api/generate-content) through the installed CrewAI LLM interface, without upgrading CrewAI/LiteLLM or substituting old model metadata. No extra Gemini SDK is needed. The target has no external tools; the adapter rejects tool calls.

The transport attempts each call at most three times for HTTP 429 and transient 500/502/503/504 errors, respecting `Retry-After` and Google `RetryInfo.retryDelay` before exponential backoff. Explicit daily/zero quota and billing exhaustion stop immediately. An unknown 429 receives bounded retries. Guidance above 60 seconds stops rather than retrying early. Agent retries are disabled so they cannot multiply transport retries. The campaign pauses 20 seconds between cases and stops on exhausted target or judge quota; skipped cases are listed in `campaign.json`.

Each target subprocess has a 300-second hard timeout. The <=20,000 target-token budget is an after-run assertion, not a spend cap. Native `usageMetadata.totalTokenCount` is retained and summed across received target responses, including spam filtering and scoring. Missing telemetry remains null and fails; a total on failed execution may be partial. Judge responses and usage are separate and excluded from target totals. Reported latency measures the target worker, excluding judge time and inter-case pacing.

Task outputs, provider responses, tracebacks, retry details and logs are preserved. Failed execution leaves quality checks null/not evaluated; judge failure leaves deterministic checks intact and semantic scores unevaluated. A hard timeout may leave only the worker log. TC-004/005 intentionally have no semantic judge because their contract is rejection without generation. Raw traces contain synthetic source data and should still be reviewed before sharing.

Target and judge are separate calls but currently use the same model. Their biases, outages and quota errors may be correlated; the judge is independent of the upstream scorer, not statistically independent of the generator. Manual review found that an unbound attack cannot establish injection resistance and an unrelated English output cannot establish multilingual capacity. Passing format or keyword checks do not prove source fidelity. Judge disagreements are retained and flagged in LIVE_RESULTS.md. Single samples are smoke evidence, not a reliability estimate.

## What is executed

- `vendor/screenplay_writer/`: unchanged upstream Python, YAML and README at revision `da94a91e691e1cf5b3151416bb15b5b62729bea8`. Hashes in `evidence/provenance.json`.
- `qa/target.py`: runpy executes the original source with controlled external Agent/Task/Crew responses. This proves Python-level behavior only.
- `qa/live_worker.py`: executes original source with a narrow modern API facade: `Task.execute()` → `execute_sync().raw`, Crew output → `.raw`, integer verbosity → bool. It replaces the hard-coded discussion assignment via AST to supply dataset input; **does not substitute task placeholders or repair the spam gate**. This is a compatibility run, not an exact historical-environment reproduction.
- `qa/checks.py`: strict Markdown/telemetry validation and an independent JSON LLM judge for coherence, voice retention, policy adherence and groundedness.
- `qa/run.py`: timeout, repetitions, evidence storage and explicit failure aggregation.

No external tools are configured in this example. Sequential tasks and disabled delegation are checked; task-output traces support handoff inspection. The Gemini transport records provider calls and retry details. Hidden reasoning and token-by-token framework execution are not instrumented. The runner does not claim to measure hidden chain-of-thought.

## Deliverables

| File | Purpose |
|---|---|
| TEST_SUITE.md | 12 cases with inputs, targets, preconditions, strategies and thresholds |
| eval_dataset.json | Exact mapped premises and budgets |
| tests/ | Source-execution defect reproductions and evaluator self-tests |
| DEFECT_REPORT.md | 5 reproduced defects, fixes proposed, evidence boundaries |
| evidence/ | Reviewed live records, actual offline output, raw failure reproduction and provenance |
| LIVE_RESULTS.md | Per-case measured results, review notes and limitations |
| SUBMISSION_CHECKLIST.md | Remaining recording, GitHub and submission steps |
| VIDEO_SCRIPT.md | Approximately 6–7 minute walkthrough and recording checklist |

Manual-only acceptance criteria and scope limits are called out in TEST_SUITE.md. A judge score is probabilistic evidence; review specific numbers, source attribution, language fidelity and adversarial outputs yourself. Default sample size is smoke-test evidence, not a statistical reliability claim.

## Before submitting

1. Review LIVE_RESULTS.md, the raw evidence and the pending human-review limitations. The smoke campaign does not replace repeated release evaluation.
2. Record the 5–8 minute Loom walkthrough and replace the pending URL above.
3. Create a GitHub repository, commit this directory and submit its URL with the Loom URL.
4. Email subject: **Interest: AI Automation Developer Assignment – Manob Raj Saikia**.

No email has been sent and no public GitHub repository has been created by this package.

## Upstream attribution

CrewAI Screenplay Writer example by Toon Beerten, from crewAIInc/crewAI-examples. Its README declares MIT License. The upstream snapshot contains no example-local LICENSE text; this package does not invent additional upstream terms. Upstream source is included for auditability; see original README and source URL in provenance.

## Astra revision

Added case-specific deterministic assertions, excluded offline-only TC-012 from live runs, preserved literal formula parentheses in the format contract, and prevented semantic judging of failed target executions. A positive keyword check supplements human review; it cannot establish correct attribution or meaning.

