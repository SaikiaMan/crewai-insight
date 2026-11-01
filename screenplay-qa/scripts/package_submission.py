"""Create a local submission ZIP from an explicit allowlist, after secret scanning."""
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--output', default=str(root.parent / ('screenplay-qa-submission-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.zip')))
args = parser.parse_args()
output = Path(args.output).resolve()
if output.exists():
    parser.error('Output already exists; choose a new filename')
subprocess.run([sys.executable, str(root/'scripts/check_submission.py')], cwd=root, check=True)
files = [p for p in root.iterdir() if p.is_file() and
         (p.suffix in ('.md', '.txt', '.json', '.ini') or p.name in ('.gitignore', '.env.example'))]
for name in ('qa', 'tests', 'vendor', 'evidence', 'scripts', '.github'):
    files.extend(p for p in (root/name).rglob('*') if p.is_file() and
                 '__pycache__' not in p.parts and p.suffix != '.pyc' and
                 (not p.name.startswith('.env') or p.name == '.env.example'))
with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(set(files)):
        archive.write(path, 'screenplay-qa/' + path.relative_to(root).as_posix())
with zipfile.ZipFile(output) as archive:
    assert archive.testzip() is None
    assert all('/results/' not in name and '/.venv' not in name and
               (not Path(name).name.startswith('.env') or Path(name).name == '.env.example')
               for name in archive.namelist())
print(f'Created {output} ({len(set(files))} files, {output.stat().st_size} bytes); excludes keys, environments and scratch results.')
