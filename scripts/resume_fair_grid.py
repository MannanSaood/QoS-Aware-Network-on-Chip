"""Explicitly resume the user-paused study after checking preserved evidence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/fair_comparison'

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=4); a=p.parse_args()
    assert 1<=a.jobs<=8
    state=json.loads((OUT/'pause.json').read_text()); assert state['paused'],'Study is not paused'
    audit=Path(state['audit']); hashes=json.loads((audit.parent/'preserved_evidence_hashes.json').read_text())
    def verify():
        assert all(hashlib.sha256((OUT/path).read_bytes()).hexdigest()==h for path,h in hashes.items()),'Preserved completed evidence changed'
    verify()
    state.update(paused=False,status='resuming'); (OUT/'pause.json').write_text(json.dumps(state,indent=2)+'\n')
    result=subprocess.run([sys.executable,'scripts/run_fair_grid.py','--jobs',str(a.jobs)],cwd=ROOT)
    verify()
    state.update(status='complete' if result.returncode==0 else 'needs_attention',runner_exit_code=result.returncode,
                 preservation_checks_passed=True)
    (OUT/'pause.json').write_text(json.dumps(state,indent=2)+'\n')
    assert result.returncode==0,'Resume failed: inspect the grid logs'

if __name__=='__main__': main()
