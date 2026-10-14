"""Read-only snapshot of the three current studies."""
import json
import argparse
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser(); parser.add_argument('--sections',action='store_true'); args=parser.parse_args()
for name,path,count in [
    ('QoS',ROOT/'results/qos_comparison/progress.json','completed_runs'),
    ('Single-class',ROOT/'results/fair_comparison/progress.json','actual_rows'),
    ('BookSim-Noxim',ROOT.parent/'Paper-TOPSIS-Reproduction/results/cross_simulator/progress.json','completed_runs'),
]:
    try:
        status=json.loads(path.read_text())
        failures=status.get('failed_cases',[])
        suffix=f'; recorded failed cases: {len(failures)}' if 'failed_cases' in status else ''
        if status.get('paused'): suffix+='; PAUSED by user'
        print(f'{name}: {status[count]}/{status["expected_runs"]} completed'+suffix)
        if failures: print(json.dumps(failures,indent=2))
    except (FileNotFoundError,json.JSONDecodeError):
        print(name+': status unavailable or being written')

if args.sections:
    base=ROOT/'results/qos_comparison'; counts=Counter()
    protocol=json.loads((base/'protocol.json').read_text())
    expected=Counter((c['k'],c['traffic']) for c in protocol['cases'])
    for case in protocol['cases']:
        for mode in protocol['modes']:
            for algorithm in protocol['algorithms']:
                path=base/'cases'/case['name']/(mode+'_'+algorithm)/'result.json'
                try:
                    row=json.loads(path.read_text())
                    assert row['binary_sha256']==protocol['binary_sha256'] and row['qos']['integrity_errors']==0
                    counts[case['k'],case['traffic']]+=1
                except (FileNotFoundError,json.JSONDecodeError): pass
    for key,number in sorted(counts.items()):
        target=expected[key]*6
        print(f'  QoS {key[0]}x{key[0]} {key[1]}: {number}/{target} individual receipts'+(' COMPLETE' if number==target else ' partial'))
