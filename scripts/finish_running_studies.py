"""Finish report exports when the already-running, frozen sweeps succeed.

This is a one-shot local pipeline, not a scheduler. It never starts simulations,
changes their configuration, or touches the closed Noxim study.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/report_pipeline'
MATLAB = Path('C:/Program Files/MATLAB/R2026b/bin/matlab.exe')
EXPECTED = {'fair': 1944, 'qos': 3888}


def read(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def ready(study):
    base = ROOT / f'results/{study}_comparison'
    progress = read(base / 'progress.json')
    if not progress:
        return False
    assert not progress.get('failed_cases'), f'{study}: recorded simulation failure'
    count = 'actual_rows' if study == 'fair' else 'completed_runs'
    if not (progress.get('complete') and progress[count] == EXPECTED[study]):
        return False
    if study == 'fair':
        manifest = read(base / 'manifest.json')
        return bool(manifest and manifest.get('complete') and manifest['actual_rows'] == 1944)
    # Wait for the runner's final results and every worker-change preservation
    # check, not just the progress file written immediately before runner exit.
    if not (base / 'results.json').exists():
        return False
    audits = list((base / 'interrupted_attempts').glob('*/administration.json'))
    return all((read(p) or {}).get('final_preservation_check_passed') for p in audits)


def command(study, stage):
    if stage == 'prepare':
        root = ROOT.as_posix()
        linux = '/mnt/' + root[0].lower() + root[2:]
        return ['wsl', '-d', 'Ubuntu-24.04', '--cd', linux, '--',
                'python3', f'scripts/prepare_{study}_results.py']
    root = ROOT.as_posix().replace("'", "''")
    folder = f'results/{study}_report'
    batch = (f"cd('{root}'); addpath('matlab'); "
             f"plot_primary_results('{folder}'); verify_primary_results('{folder}');")
    return [str(MATLAB), '-wait', '-nojvm', '-noFigureWindows', '-logfile',
            str(ROOT / folder / 'matlab_export.log'), '-batch', batch]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Readiness only; do not wait or export')
    parser.add_argument('--studies', nargs='+', choices=list(EXPECTED), default=list(EXPECTED),
                        help='Reports to wait for; select qos when the old fair sweep is paused')
    args = parser.parse_args()
    selected = {name: EXPECTED[name] for name in args.studies}
    if args.check:
        print(json.dumps({s: ready(s) for s in selected}, indent=2))
        return
    assert os.name == 'nt', 'Launch on Windows to use the installed MATLAB.'
    assert MATLAB.is_file(), 'MATLAB executable missing'
    OUT.mkdir(parents=True, exist_ok=True)
    lock = OUT / 'active.lock'
    with lock.open('x') as handle:
        handle.write(str(os.getpid()))
    state = dict(pid=os.getpid(), status='waiting', complete=False,
                 requested_studies=list(selected), studies={})

    def save():
        temp = OUT / 'progress.tmp'
        temp.write_text(json.dumps(state, indent=2) + '\n')
        temp.replace(OUT / 'progress.json')

    def run(study, stage):
        state['status'] = f'{study}_{stage}'
        save()
        print(f'{study}: {stage}', flush=True)
        with (OUT / f'{study}_{stage}.log').open('w') as log:
            # Shell-free arguments retain paths with spaces and literal text.
            result = subprocess.run(command(study, stage), cwd=ROOT,
                                    stdout=log, stderr=subprocess.STDOUT)
        assert result.returncode == 0, f'{study} {stage} failed; see its pipeline log'

    try:
        save()
        while len(state['studies']) != len(selected):
            for study, count in selected.items():
                if study in state['studies'] or not ready(study):
                    continue
                run(study, 'prepare')
                run(study, 'matlab')
                base = ROOT / f'results/{study}_report'
                data = read(base / 'validation.json')
                figures = read(base / 'figure_verification.json')
                assert data['complete'] and data['checks_passed'] and data['runs'] == count
                assert figures['complete_study'] and figures['checks_passed']
                assert figures['measured_runs'] == count
                assert figures['individual_figures'] == 72 and figures['comparison_pages'] == 10
                assert figures['verified_lines'] == 396
                state['studies'][study] = dict(runs=count, figures=82, verified_lines=396,
                                               checks_passed=True)
                state['status'] = 'waiting'
                save()
                print(f'{study}: verified full report', flush=True)
            if len(state['studies']) != len(selected):
                time.sleep(30)
        state.update(status='complete', complete=True)
        save()
        print('Requested full BookSim reports exported and verified. No PPT or Noxim work performed.', flush=True)
    except BaseException as exc:
        state.update(status='failed', error=repr(exc))
        save()
        raise
    finally:
        lock.unlink()


if __name__ == '__main__':
    main()
