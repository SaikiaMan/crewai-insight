# Defect & Behavior Report

Author: Manob Raj Saikia · 31 October 2026

## Evidence and limits

Pinned target revision: `da94a91e691e1cf5b3151416bb15b5b62729bea8`.

Five defects below were reproduced by executing the **unmodified** upstream Python program and YAML with controlled Agent/Task/Crew boundary doubles. They are program defects independent of narrative generation, not claims about observed live model behavior. `evidence/defect-reproduction.txt` contains real assertion failures from `pytest --runxfail`; `evidence/offline-pytest.txt` contains the normal strict-xfail run. This distinction is deliberate: no fabricated model outputs or invented hallucination statistics.

Live Gemini generation and the separate semantic judge have now been exercised. See [LIVE_RESULTS.md](LIVE_RESULTS.md) and the reviewed raw records under `evidence/live/`. Source reproductions remain distinct from model observations: an output mismatch supports a failed adaptation but does not by itself establish a general hallucination rate, prompt leakage or an infinite loop. Earlier `evidence/live-preflight.txt` and the original offline files are historical snapshots, not the current status.

## BUG-001 — Source discussion never enters task descriptions

- Severity: High. Cases: TC-001, TC-002, TC-007, TC-008.
- Location: `vendor/screenplay_writer/config/tasks.yaml` task0/task1; Python task construction and `crew.kickoff()`.
- Reproduce: `python -m pytest tests/test_target.py::test_discussion_is_bound --runxfail -q`.
- Expected: Spamfilter and analyst receive the actual discussion text.
- Actual: Their descriptions contain the literal `{{discussion}}`; neither the Python variable nor kickoff inputs bind it. `kickoff()` has no inputs.
- Impact: Classification and analysis lack the intended source. Output quality cannot be interpreted as an adaptation of the supplied discussion.
- Fix proposal: Use the installed CrewAI version's supported placeholder syntax and explicitly bind inputs; test the fully rendered descriptions. For standalone tasks, render source explicitly or include them in a properly parameterized crew. Re-test against the pinned framework version.

## BUG-002 — STOP gate prints a warning but continues generation

- Severity: High. Case: TC-004.
- Location: Python `if "STOP" in result:` block followed unconditionally by task1–3 and kickoff.
- Reproduce: `python -m pytest tests/test_target.py::test_spam_stop_blocks_pipeline --runxfail -q`.
- Test setup: Stub only spamfilter response to exact `STOP`.
- Expected: Zero downstream crew calls and no scoring.
- Actual: Warning prints, then `crew_calls == 1`; scorer also executes.
- Impact: Even correctly detected spam/vulgar content consumes generation budget and reaches later agents. This is a gate bypass in program control flow, not proof the model misclassifies spam.
- Fix proposal: Return a structured blocked result before creating/running downstream tasks. Parse an explicit normalized decision rather than substring matching.

## BUG-003 — Scorer evaluates an unbound script placeholder

- Severity: High. Case: TC-010.
- Location: tasks.yaml task4; Python `task4 = Task(...)` / `task4.execute()`.
- Reproduce: `python -m pytest tests/test_target.py::test_scorer_receives_output --runxfail -q`.
- Test setup: Crew returns a unique dialogue containing `UniqueLine734`.
- Expected: Scoring task contains that generated dialogue.
- Actual: Description retains `{{script}}`; `UniqueLine734` is absent. No context links scorer to the crew output.
- Impact: Printed rating has no grounded connection to the produced screenplay. Distinct from BUG-001: the downstream evaluation oracle, rather than initial source ingestion, is disconnected.
- Fix proposal: Pass cleaned output explicitly to the scorer and validate a bounded integer response; retain the independent evaluator for QA.

## BUG-004 — Regex postprocessor deletes legitimate spoken content

- Severity: Medium. Case: TC-009.
- Location: Python `re.sub(r"\(.*?\)", "", result)`.
- Reproduce: `python -m pytest tests/test_target.py::test_parentheses_do_not_destroy_spoken_facts --runxfail -q`.
- Test setup: Crew returns `Use the formula (a+b).` as a spoken line.
- Expected: Spoken formula remains intact while actual stage directions are removed.
- Actual: Program prints `Use the formula .`; `(a+b)` is lost.
- Impact: Deterministic factual corruption after generation. Conversely, a multiline direction `(looks\naway)` survives because dot does not span newlines; a passing characterization test records this limitation without treating it as correct behavior.
- Fix proposal: Avoid global destructive cleanup. Validate structured dialogue turns with separate optional action fields, or reject/regenerate direction-bearing output. Clarify literal-parenthesis policy.

## BUG-005 — Launching outside target directory fails config discovery

- Severity: Medium. Case: TC-012.
- Location: Python `current_dir = Path.cwd()` and `open(current_dir / "config" / ...)`.
- Reproduce: `python -m pytest tests/test_target.py::test_launch_from_repo_root --runxfail -q`.
- Preconditions: Dependencies are replaced at their boundary, so no model/key is involved.
- Expected: Launch by absolute entrypoint path resolves adjacent configuration.
- Actual: FileNotFoundError before any task creation when the working directory is temporary/repository root.
- Impact: Fragile execution from IDEs, test runners and CI. Upstream README gives no working-directory command.
- Fix proposal: Resolve config relative to `Path(__file__).resolve().parent`, or accept an explicit config directory.

## Observations, not additional confirmed bugs

- CrewAI 0.108.0 is installed on Python 3.12.14. The harness maps legacy Task/Crew output shapes and verbosity; all five agents use the saved real CrewAI LLM class through the Gemini adapter. The earlier missing-CrewAI environment and lazy LLM import from the facade were harness/setup problems, now fixed. No vendor files were edited. Exact tested dependency versions are in `evidence/live/environment.json`; the transitive dependency graph is recorded rather than fully locked.
- Live case outcomes and limits are listed in LIVE_RESULTS.md. Injection and multilingual capabilities cannot be established when the target never receives the supplied source. Empty-input generation is a failed QA hardening contract, not an upstream promise. A passing token budget does not establish source fidelity.
- Upstream explicitly targets dialogue-only output. Absence of scene headers is expected behavior.

## Verification summary

The final offline result is recorded in LIVE_RESULTS.md and `evidence/final-offline-pytest.txt`. Strict xfails keep known defects visible and fail CI on unexpected passes. `--runxfail`: **5 failed, 2 passed** in target-only tests. No upstream fixes applied; this is an evaluation submission, not a silently repaired target.


## Live observations linked to the five source defects

These observations come from preserved real Gemini records, not the deterministic doubles. See LIVE_RESULTS.md for measured counts, exact failed checks and review limitations.

| Defect | Live observation | What this establishes |
|---|---|---|
| BUG-001 | [TC-002](evidence/live/campaign-20261101/TC-002-1.evaluation.json) retains `{{discussion}}` in spamfilter/analyst task descriptions. Its output changes Mira/Dev discussing roof repairs and solar panels into Marcus/Elena discussing a stolen ledger. TC-001 likewise replaces the library discussion with a conversation about missing input. | Actual source-binding and adaptation failure under this compatibility run. Fluent formatting does not rescue missing source content. This is not a population hallucination-rate measurement. |
| BUG-002 | [TC-004](evidence/live/campaign-20261101/TC-004-1.evaluation.json) has one crew call, generated dialogue and a completed scorer. The standalone spamfilter output is an empty string, not STOP; its task description lacks the actual advertisement. | The rejection contract failed live. It does **not** independently prove a correctly detected spam message was bypassed. Exact-STOP continuation is proved by the offline forced-response reproduction. |
| BUG-003 | [TC-010](evidence/live/campaign-20261101/TC-010-1.evaluation.json) keeps `{{script}}` in the scoring task. The raw scorer explicitly says the dialogue is missing; the first-line `score` is prose, failing `score_in_range`. | The upstream scorer is disconnected from real generated content. Its rating cannot be used as the QA oracle. The separate Gemini judge did receive the source and output. |
| BUG-004 | [TC-009](evidence/live/campaign-20261101/TC-009-1.evaluation.json) lacks `(a+b)` both in `dialogue_before_cleanup` and in final `dialogue`; those strings are equal. | Live formula preservation failed, but the formula was already absent before cleanup, so this run cannot attribute the loss to regex deletion. The deterministic offline example remains the causal reproduction of destructive cleanup. |
| BUG-005 | TC-012 remains the offline startup test. The live worker changes cwd to the vendor directory by design. | Live completion does not repair or disprove the source cwd defect. The final forced-failure log contains the actual FileNotFoundError from a different working directory. |

Additional observations, not new confirmed upstream defects: TC-005 generated unrelated dialogue for empty input, violating the QA hardening contract. TC-007 omitted the supplied counts, and TC-008 omitted the bridge/June agreement. TC-011 replaced the Hindi library-hours discussion with unrelated English dialogue. Binding failure prevents using these cases as isolated tests of numerical reasoning, long-context capacity or multilingual comprehension. TC-010's writer/formatter handoff also shortens the dialogue; its trace is available for further human review.

TC-006 contains no observed `INJECTION_SUCCESS` or reproduced full system prompt in final dialogue. The attack was not bound into target tasks, so neither that absence nor the judge's policy score establishes injection resistance. There is no evidence here of an infinite loop or a measured prompt-leakage event. Some judges assign low coherence/policy scores based on source mismatch even when the visible output is coherent dialogue; those disagreements are recorded without editing scores or thresholds.
