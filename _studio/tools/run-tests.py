"""Run every _studio/tools/tests/**/*.test.mjs with node --test and every
_studio/tools/check-*.py, one line per suite. Exits non-zero if any fails.

    python _studio/tools/run-tests.py
"""
import pathlib, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]
suites = [(['node', '--test', str(f)], f.relative_to(HERE).as_posix()) for f in sorted((HERE / 'tests').rglob('*.test.mjs'))]
suites += [([sys.executable, str(f)], f.name) for f in sorted(HERE.glob('check-*.py'))]
failed = 0
for cmd, name in suites:
    r = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout + r.stderr).strip().splitlines()
    if r.returncode == 0:
        tally = [line[2:] for line in out if line.startswith(('# pass', '# fail', '# skipped'))
                 and line != '# skipped 0']  # node's summary
        print(f'ok   {name}: {", ".join(tally) or (out[-1] if out else "")}', flush=True)
    else:
        failed += 1
        print(f'FAIL {name}', *('    ' + line for line in out[-15:]), sep='\n', flush=True)
print(f'{len(suites) - failed} of {len(suites)} suites passed')
sys.exit(1 if failed else 0)
