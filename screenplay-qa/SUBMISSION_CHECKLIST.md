# Recording and submission checklist

Status: technical evidence prepared locally; **assignment not fully submitted**.

- [x] Preserve vendored source and verify provenance hashes.
- [x] Run final offline regressions and preserve intentional defect failures.
- [x] Exercise real Gemini generation, task traces, usage telemetry and independent judging.
- [ ] Read LIVE_RESULTS.md and sign off on judge disagreements and the stated coverage limitations.
- [ ] Decide whether further repeat evaluation is needed before making release claims.
- [x] Credential scan completed with no findings; rerun `python scripts/check_submission.py` before committing.
- [ ] Record a 5-8 minute Loom using VIDEO_SCRIPT.md. Keep `.env` closed.
- [ ] Replace README's pending Loom URL with the real accessible link.
- [ ] Create the GitHub repository and verify the evidence links in its rendered Markdown.
- [ ] Add the real GitHub URL below and verify both links signed out.
- [ ] Submit through the requested assignment channel yourself.

Loom URL: **PENDING**

GitHub URL: **PENDING**

## Local Git preparation (no automatic publishing)

From the project directory, after reviewing the credential scan:

```powershell
.\.venv-live\Scripts\python.exe scripts/check_submission.py
git init
git add .
git status --short
git diff --cached --stat
git check-ignore .env .venv-live/Scripts/python.exe results/gemini/TC-001-1.evaluation.json
git commit -m "Add screenplay QA harness and reviewed Gemini evaluation evidence"
```

Review the staged file list before committing. `.env`, `.env.*` except the placeholder `.env.example`, environments, caches and scratch `results/` are excluded. The curated evidence under `evidence/live/` is intentionally included. No key value should appear in a diff, command output, video, issue or README. The scanner checks intended source/docs/evidence and known local key values without printing them; it is a safeguard, not a guarantee against every possible secret format.

Create the remote repository and push only after the final human review. This package has not created a GitHub repository, published a site, recorded a Loom, or sent an email. If email is the requested submission route, use the assignment's specified recipient and subject; no email is sent by this tooling.


Optional local snapshot (contains reviewed evidence but excludes .env, environments and scratch results):

```powershell
.\.venv-live\Scripts\python.exe scripts/package_submission.py
```

Regenerate it after adding the actual Loom/GitHub links. The packager scans credentials first and refuses to overwrite an existing ZIP. Creating this file does not publish or submit anything.
