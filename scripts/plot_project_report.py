"""Portable fallback for the same curated figure definitions as MATLAB."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from run_experiments import ROOT

def main():
    report=ROOT/'results/report'; out=report/'python_figures'; out.mkdir(parents=True,exist_ok=True)
    specs=json.loads((report/'figures.json').read_text(encoding='utf-8'))
    plt.rcParams.update({'font.size':12,'axes.spines.top':False,'axes.spines.right':False,'pdf.fonttype':42})
    colors=['#0072B2','#D55E00','#009E73']; styles=['-','--','-.']
    for spec in specs:
        fig,ax=plt.subplots(figsize=(9,6)); fig.subplots_adjust(left=.15,right=.97,bottom=.25,top=.8)
        for i,series in enumerate(spec['series']):
            x=np.array(series['x']); mu=np.array(series['mean']); ci=np.array(series['ci95'])
            ax.fill_between(x,np.maximum(0,mu-ci),mu+ci,color=colors[i],alpha=.09,linewidth=0)
            ax.plot(x,mu,color=colors[i],ls=styles[i],lw=2.5,label=series['label'])
        if spec['reference'] is not None:
            ax.axhline(spec['reference'],ls=':',color='.3',lw=1.3)
        if spec['xmesh']:
            ax.set_xscale('log',base=2); ax.set_xticks([4,8,16,32],['4×4 (16)','8×8 (64)','16×16 (256)','32×32 (1024)'])
        else: ax.set_xticks(spec['series'][0]['x'])
        ax.set_ylim(bottom=0); ax.set_xlim(min(spec['series'][0]['x']),max(spec['series'][0]['x']))
        ax.set(xlabel=spec['xlabel'],ylabel=spec['ylabel']); ax.grid(alpha=.12); ax.legend(frameon=False)
        fig.suptitle(spec['title'],fontsize=16,fontweight='bold',y=.97)
        fig.text(.5,.9,spec['context'],ha='center',fontsize=11,color='.3')
        import textwrap
        note='Lines: three-seed means; shading: 95% t-intervals.\n'+textwrap.fill(spec['caption'],100)
        fig.text(.15,.03,note,fontsize=9,color='.3')
        for ext in ['png','pdf']: fig.savefig(out/(spec['stem']+'.'+ext),dpi=300)
        plt.close(fig)
    print(f'Exported {len(specs)} single-metric figures to {out}')

if __name__=='__main__': main()
