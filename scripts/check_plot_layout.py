"""Render a clearly labeled layout preview from completed transpose cases only."""
import json
from prepare_report import ROOT,read,series,NAMES
rows=read('transpose_load')
loads=sorted({float(r['offered_flits_per_node_cycle']) for r in rows})
complete=[x for x in loads if sum(float(r['offered_flits_per_node_cycle'])==x for r in rows)==18]
rows=[r for r in rows if float(r['offered_flits_per_node_cycle']) in complete]
spec=dict(stem='layout_preview_p99',title='Transpose — p99 latency',
          context='LAYOUT PREVIEW | completed three-seed loads only | BookSim 8×8',
          xlabel='Offered load (flits/node/cycle)',ylabel='p99 latency (cycles)',xmesh=False,reference=None,
          caption='Tail delay: read with throughput; unfinished packets are excluded.',
          series=[series(rows,'latency_p99_cycles','offered_flits_per_node_cycle',NAMES[a],a,'booksim') for a in NAMES])
out=ROOT/'results/layout_preview'; out.mkdir(exist_ok=True)
(out/'figures.json').write_text(json.dumps([spec],ensure_ascii=False),encoding='utf-8')
print('Layout preview uses these measured loads:',complete)
