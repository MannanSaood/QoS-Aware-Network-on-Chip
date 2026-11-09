"""Build the CHR-OE study binary in its own tree (.deps/booksim2_chr).

Starts from the frozen QoS source tree, after checking every source file
against the frozen build manifest, then adds the CHR routes. The frozen tree
and its binary are only read, never modified. See docs/CHR_OE_CANDIDATE_SPEC.md.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from setup import patch

ROOT=Path(__file__).resolve().parents[1]
FROZEN=ROOT/'.deps/booksim2_qos'
FROZEN_BINARY_SHA='bb3f1024a6308c2ed1e99d429a20b0ef373d06c8fdda29a26cf62fe02a178a24'
DEST=ROOT/'.deps/booksim2_chr'

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    p=argparse.ArgumentParser(); p.add_argument('--jobs',type=int,default=4); a=p.parse_args()
    fsrc=FROZEN/'src'
    assert sha(fsrc/'booksim')==FROZEN_BINARY_SHA,'Frozen QoS binary hash mismatch'
    manifest=json.loads((FROZEN/'build_manifest.json').read_text())
    assert manifest['qos_binary_sha256']==FROZEN_BINARY_SHA,'Frozen manifest does not describe the frozen binary'
    for rel,digest in manifest['sources_sha256'].items():
        assert sha(fsrc/rel)==digest,f'Frozen source drifted from its manifest: {rel}'
    src=DEST/'src'
    if src.exists(): shutil.rmtree(src)
    shutil.copytree(fsrc,src,ignore=shutil.ignore_patterns('*.o','*.d','booksim','*.log'))
    # Current algorithm headers: xy/dyad/topsis/common must be byte-identical to the frozen copies.
    for rel in ['common/mesh.hpp','common/select.hpp','xy/routing.hpp','dyad/routing.hpp','topsis/routing.hpp']:
        assert sha(ROOT/'algorithms'/rel)==sha(fsrc/'noc_algorithms'/rel),f'Baseline algorithm changed: {rel}'
    shutil.copytree(ROOT/'algorithms',src/'noc_algorithms',dirs_exist_ok=True)
    for f in (ROOT/'simulators/booksim_chr').glob('*.*'):
        if f.suffix in ('.hpp','.cpp'): shutil.copyfile(f,src/f.name)
    ext=src/'noc_extension.cpp'
    patch(ext,'#include "noc_extension.hpp"','#include "noc_extension.hpp"\n#include "chr_routes.hpp"')
    patch(ext,'    gRoutingFunctionMap["noc_topsis_mesh"]=&topsis;',
        '    gRoutingFunctionMap["noc_topsis_mesh"]=&topsis;\n    chr_register(config);')
    patch(ext,'void noc_sample(const std::vector<Network*>& nets,int time) {',
        'void noc_sample(const std::vector<Network*>& nets,int time) {\n    chr_tick(nets,time);')
    patch(ext,'void noc_finish() {','void noc_finish() {\n    chr_finish();')
    hpp=src/'routers/iq_router.hpp'
    patch(hpp,'  virtual int GetUsedCredit(int o) const;',
        '  virtual int GetUsedCredit(int o) const;\n  bool ChrOutputVCFree(int o, int vc) const;')
    cpp=src/'routers/iq_router.cpp'
    patch(cpp,'int IQRouter::GetBufferOccupancy(int i) const {',
        'bool IQRouter::ChrOutputVCFree(int o, int vc) const\n{\n  return _next_buf[o]->IsAvailableFor(vc);\n}\n\nint IQRouter::GetBufferOccupancy(int i) const {')
    subprocess.run(['make',f'-j{a.jobs}'],cwd=src,check=True)
    assert sha(fsrc/'booksim')==FROZEN_BINARY_SHA,'Frozen binary changed during CHR build'
    out=dict(frozen_qos_binary_sha256=FROZEN_BINARY_SHA,chr_binary_sha256=sha(src/'booksim'),
             sources_sha256={str(f.relative_to(src)).replace('\\','/'):sha(f)
                             for f in sorted(src.rglob('*')) if f.suffix in ('.cpp','.hpp','.l','.y')},
             note='CHR-OE study build: frozen QoS tree plus CHR routes, per-cycle filter hook and free-VC accessor.')
    (DEST/'build_manifest.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k!='sources_sha256'},indent=2))

if __name__=='__main__': main()
