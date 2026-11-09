"""Pull Actions results from the `saqr-results` branch into the local results tree.

Copies result.json files that do not exist locally. Where a run exists on both sides
(local and Actions), the metric blocks must be identical; any difference is reported
and nothing is overwritten. Usage: python3 ci/saqr_actions/fetch_results.py [results-branch]
"""
import io
import sys
import json
import subprocess
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KEYS = ('aggregate', 'qos', 'chr', 'saqr', 'binary_sha256', 'config_sha256', 'trace_sha256', 'chr_env')


def main():
    branch = sys.argv[1] if len(sys.argv) > 1 else 'saqr-results'
    subprocess.run(['git', 'fetch', '-q', 'origin', branch], cwd=ROOT, check=True)
    data = subprocess.run(['git', 'archive', 'FETCH_HEAD', 'results', 'ci_status'], cwd=ROOT, check=True, capture_output=True).stdout
    new = same = differ = 0; diffs = []
    with tarfile.open(fileobj=io.BytesIO(data)) as tar:
        for m in tar.getmembers():
            if not m.isfile():
                continue
            b = tar.extractfile(m).read()
            if m.name.startswith('ci_status/'):
                dst = ROOT / 'results' / 'saqr_study' / ('actions_status' if branch == 'saqr-results' else f'actions_status_{branch}') / m.name[len('ci_status/'):]
                dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b); continue
            dst = ROOT / m.name
            if dst.exists():
                a, r = json.loads(dst.read_text()), json.loads(b)
                if all(a.get(k) == r.get(k) for k in KEYS): same += 1
                else: differ += 1; diffs.append(m.name)
                continue
            dst.parent.mkdir(parents=True, exist_ok=True); dst.write_bytes(b); new += 1
    print(f'fetched {new} new receipts; {same} overlap identically; {differ} DIFFER')
    for d in diffs[:20]:
        print('DIFFERS', d)


if __name__ == '__main__':
    main()
