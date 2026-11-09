"""Run helper for the CHR-OE study. Writes only under results/chr_study.

Reuses the frozen demand generator and router configuration from
qos_common.py (imported, not modified), but runs the CHR binary.
"""
import json
import os
from pathlib import Path
import subprocess
import time
from qos_common import ROOT, sha, config, trace  # noqa: F401  (trace re-exported)

CHR_BINARY=ROOT/'.deps/booksim2_chr/src/booksim'
SAQR_BINARY=ROOT/'.deps/booksim2_saqr/src/booksim'
STUDY=ROOT/'results/chr_study'
SAQR_STUDY=ROOT/'results/saqr_study'
TUNING_ENV=('NOC_CHR_ALPHA_SHIFT','NOC_CHR_T_ON','NOC_CHR_T_OFF','NOC_CHR_MARGIN','NOC_CHR_FREE_PENALTY',
            'NOC_SAQR_T_ON','NOC_SAQR_T_OFF','NOC_SAQR_ALPHA_SHIFT','NOC_SAQR_MARGIN','NOC_SAQR_REGIONAL_SHIFT',
            'NOC_SAQR_RATIO_NUM','NOC_SAQR_RATIO_DEN','NOC_SAQR_CLASS_MASK',
            'NOC_SAQR_CRIT_GATE','NOC_SAQR_CRIT_RATIO_NUM','NOC_SAQR_CRIT_RATIO_DEN',
            'NOC_SAQR_BE_GATE','NOC_SAQR_BE_RATIO_NUM','NOC_SAQR_BE_RATIO_DEN','NOC_SAQR_BE_STALL',
            'NOC_SAQR_REGIME_ON','NOC_SAQR_REGIME_OFF','NOC_SAQR_REGIME_FLOOR','NOC_SAQR_REGIME_SHIFT','NOC_SAQR_REGIME_OBSERVE','NOC_SAQR_O1TURN_MASK')

def run(directory,demand,k,algorithm,seed,mode,warm=5000,cycles=20000,classes=2,vcs=4,depth=8,
        chr_env=None,timeout=7200,binary=None):
    directory=Path(directory).resolve()
    binary=Path(binary or CHR_BINARY)
    assert STUDY.resolve() in directory.parents or SAQR_STUDY.resolve() in directory.parents,'Study runs must write under results/chr_study or results/saqr_study'
    directory.mkdir(parents=True,exist_ok=True)
    cfg=directory/'config.cfg'; cfg.write_text(config(k,algorithm,seed,mode,classes,vcs,depth))
    chr_env=dict(chr_env or {})
    assert set(chr_env)<=set(TUNING_ENV),f'Unknown CHR override: {set(chr_env)-set(TUNING_ENV)}'
    env={key:value for key,value in os.environ.items() if key not in TUNING_ENV}
    env.update(NOC_TRACE=str(Path(demand).resolve()),NOC_WARMUP=str(warm),NOC_MEASURE=str(cycles),
               NOC_SKIP_DRAIN='1',NOC_QOS_MODE=mode,NOC_METRICS=str(directory/'aggregate.json'),
               NOC_QOS_METRICS=str(directory/'classes.json'),NOC_CHR_METRICS=str(directory/'chr.json'),NOC_SAQR_METRICS=str(directory/'saqr.json'),
               **{key:str(value) for key,value in chr_env.items()})
    start=time.perf_counter()
    with (directory/'run.log').open('w') as out:
        subprocess.run([str(binary),str(cfg)],stdout=out,stderr=subprocess.STDOUT,env=env,check=True,timeout=timeout)
    result=dict(k=k,algorithm=algorithm,seed=seed,mode=mode,warm=warm,cycles=cycles,classes=classes,vcs=vcs,depth=depth,
                binary_sha256=sha(binary),trace_sha256=sha(demand),config_sha256=sha(cfg),chr_env=chr_env,
                wall_seconds=time.perf_counter()-start,
                aggregate=json.loads((directory/'aggregate.json').read_text()),
                qos=json.loads((directory/'classes.json').read_text()),
                chr=json.loads((directory/'chr.json').read_text()),
                saqr=json.loads((directory/'saqr.json').read_text()) if (directory/'saqr.json').exists() else None)
    (directory/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    return result
