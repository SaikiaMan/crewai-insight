"""Scan the files intended for submission without displaying secret values."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
roots = ['qa', 'tests', 'vendor', 'evidence', 'scripts', '.github']
files = [p for p in ROOT.iterdir() if p.is_file() and
         (p.suffix in ('.md', '.txt', '.json', '.ini') or p.name in ('.gitignore', '.env.example'))]
for name in roots:
    files.extend(p for p in (ROOT/name).rglob('*') if p.is_file() and
                 '__pycache__' not in p.parts and p.suffix != '.pyc' and
                 (not p.name.startswith('.env') or p.name == '.env.example'))
secrets = []
env_file = ROOT/'.env'
if env_file.exists():
    for line in env_file.read_text(encoding='utf-8').splitlines():
        name, sep, value = line.partition('=')
        if sep and any(word in name.upper() for word in ('KEY', 'SECRET', 'TOKEN')):
            value = value.strip().strip(chr(34)).strip(chr(39))
            if len(value) >= 16:
                secrets.append(value)
patterns = [re.compile(r'AIza[0-9A-Za-z_-]{30,}'),
            re.compile(r'sk-(?:proj-)?[A-Za-z0-9_-]{20,}'),
            re.compile(r'AQ\.[A-Za-z0-9_-]{30,}')]
findings = []
for path in sorted(set(files)):
    content = path.read_text(encoding='utf-8', errors='replace')
    if any(secret in content for secret in secrets) or any(p.search(content) for p in patterns):
        findings.append(path.relative_to(ROOT).as_posix())
print(json.dumps({'files_scanned': len(set(files)), 'credential_findings': findings,
                  'scope': 'submission source/docs/evidence; excludes .env, results and environments'}, indent=2))
raise SystemExit(1 if findings else 0)
