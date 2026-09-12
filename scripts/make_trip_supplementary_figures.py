#!/usr/bin/env python3
"""Generate TRIP supplementary figures S1--S6 from confirmatory R3/R4/R5 summaries only.

Style intentionally mirrors make_trip_revision_figures_v3.py: 180/120 mm physical widths,
sans-serif 7--7.5 pt text, Okabe-Ito/Tol-derived palette, vector PDF plus 600-dpi PNG
and 1000-dpi LZW TIFF, no bbox_inches='tight'. No route map or geographic coordinate is
created by this script.
"""
from pathlib import Path
import argparse, io
import pandas as pd
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image

PNG_DPI=600; TIFF_DPI=1000; MM=1/25.4; W_FULL=180*MM; W_MID=120*MM
INK='#222222'; MUTED='#6B6B6B'; RULE='#D0D0D0'
C={'cvar':'#0072B2','mean':'#E69F00','ortools':'#6B6B6B','env':'#3B4B8C','env2':'#B0456E','alns':'#4D4D4D','rlff':'#CC6677','rlgru':'#117733','dddas':'#6A3D9A','improve':'#1A9E77','tie':'#A0A0A0','worsen':'#D55E00','retained':'#DCDCDC'}
def pick_font():
    av={f.name for f in font_manager.fontManager.ttflist}
    for n in ('Arial','Helvetica','Helvetica Neue','Liberation Sans','TeX Gyre Heros','DejaVu Sans'):
        if n in av:return n
    return 'DejaVu Sans'
FONT=pick_font(); FS=7.; FSL=7.5; FSS=6.4; FLET=9.
mpl.rcParams.update({'font.family':'sans-serif','font.sans-serif':[FONT,'DejaVu Sans'],'font.size':FS,'axes.labelsize':FSL,'axes.titlesize':FSL,'xtick.labelsize':FS,'ytick.labelsize':FS,'legend.fontsize':FS,'axes.linewidth':.6,'axes.edgecolor':INK,'axes.labelcolor':INK,'axes.spines.top':False,'axes.spines.right':False,'xtick.color':INK,'ytick.color':INK,'xtick.major.width':.6,'ytick.major.width':.6,'xtick.major.size':2.8,'ytick.major.size':2.8,'xtick.direction':'out','ytick.direction':'out','text.color':INK,'lines.linewidth':1.3,'lines.markersize':4.2,'legend.frameon':False,'pdf.fonttype':42,'ps.fonttype':42,'figure.facecolor':'white','savefig.facecolor':'white'})
def panel(ax,letter,title):
    ax.annotate(letter.lower(),(0,1),xycoords='axes fraction',xytext=(-30,7),textcoords='offset points',ha='left',va='baseline',fontsize=FLET,fontweight='bold')
    ax.annotate(title,(0,1),xycoords='axes fraction',xytext=(-20,7),textcoords='offset points',ha='left',va='baseline',fontsize=FSL)
def save(fig,stem,out):
    for s in ('pdf','png','tiff'):(out/s).mkdir(parents=True,exist_ok=True)
    fig.savefig(out/'pdf'/f'{stem}.pdf')
    fig.savefig(out/'png'/f'{stem}.png',dpi=PNG_DPI)
    b=io.BytesIO(); fig.savefig(b,format='png',dpi=TIFF_DPI); b.seek(0)
    Image.open(b).convert('RGB').save(out/'tiff'/f'{stem}.tiff',compression='tiff_lzw',dpi=(TIFF_DPI,TIFF_DPI)); plt.close(fig)

def s1(data,out):
    d=pd.read_csv(data/'S1_R3_budget_parity.csv'); x=np.arange(len(d))
    fig,axs=plt.subplots(1,2,figsize=(W_FULL,72*MM),layout='constrained')
    cols=[C['mean'],C['cvar'],C['rlff'],C['rlff'],C['rlgru'],C['rlgru']]
    axs[0].bar(x,d.scenario_evals/1000,color=cols,width=.68); axs[0].set_ylabel('Scenario evaluations (thousands)'); axs[0].set_xticks(x,d.method,rotation=35,ha='right'); axs[0].set_ylim(0,28); panel(axs[0],'a','Matched stochastic search budget')
    axs[1].bar(x,d.evaluated_candidates,color=cols,width=.68); axs[1].set_ylabel('Evaluated candidates'); axs[1].set_xticks(x,d.method,rotation=35,ha='right'); axs[1].set_ylim(0,280); panel(axs[1],'b','Matched candidate budget')
    axs[1].text(.98,.92,'all methods: exact parity',transform=axs[1].transAxes,ha='right',va='top',fontsize=FSS,color=MUTED)
    save(fig,'FigS1_R3_budget_parity',out)

def s2(data,out):
    d=pd.read_csv(data/'S2_R4D_mean_impact_control.csv')
    fig,axs=plt.subplots(1,2,figsize=(W_FULL,68*MM),layout='constrained')
    axs[0].plot(d.eta,d.kappa,'o-',color=C['env']); axs[0].set_xlabel(r'Hawkes branching ratio, $\eta$'); axs[0].set_ylabel(r'Matched impact coefficient, $\kappa_\eta$'); panel(axs[0],'a','Coefficient required by mean-impact matching')
    axs[1].plot(d.eta,d.target_mean_multiplier,'o-',color=C['env2']); axs[1].axhline(d.target_mean_multiplier.iloc[0],ls='--',lw=.8,color=MUTED); axs[1].set_ylim(1.045,1.060); axs[1].set_xlabel(r'Hawkes branching ratio, $\eta$'); axs[1].set_ylabel('Target mean travel-time multiplier'); panel(axs[1],'b','Frozen continuous-time mean target')
    save(fig,'FigS2_R4D_mean_impact_control',out)

def s3(data,out):
    d=pd.read_csv(data/'S3_R4E1_crossday_gains.csv')
    fig,ax=plt.subplots(figsize=(W_MID,85*MM),layout='constrained')
    ax.scatter(d.delta_J,d.delta_tail,s=26,color=C['cvar'],zorder=3)
    for _,r in d.iterrows(): ax.annotate(str(int(r.day)),(r.delta_J,r.delta_tail),xytext=(4,3),textcoords='offset points',fontsize=FSS)
    ax.axvline(0,color=RULE,lw=.7); ax.axhline(0,color=RULE,lw=.7); ax.set_xlabel(r'$\Delta J_{\mathrm{CVaR}}$ (Mean $-$ CVaR)'); ax.set_ylabel(r'$\Delta \mathrm{CVaR}_{0.95}$ tardiness'); panel(ax,'a','Nine-day joint improvement pattern')
    ax.text(.98,.04,'all 9 days in upper-right quadrant',transform=ax.transAxes,ha='right',va='bottom',fontsize=FSS,color=MUTED)
    save(fig,'FigS3_R4E1_joint_crossday_gains',out)

def s4(data,out):
    d=pd.read_csv(data/'S4_R4E2_zero_shot_audit.csv')
    fig,axs=plt.subplots(1,2,figsize=(W_FULL,70*MM),layout='constrained')
    axs[0].bar(d.target_day,d.completed_reports,color=C['rlgru'],width=.62); axs[0].set_xticks(d.target_day); axs[0].set_xlabel('Target day'); axs[0].set_ylabel('Frozen source checkpoints'); axs[0].set_ylim(0,11.2); panel(axs[0],'a','Zero-shot transfer coverage')
    labels=['budget pass','weights unchanged','no target training','no target validation','no target updates']; vals=[d.budget_pass.sum(),d.weights_unchanged.sum(),d.no_target_training.sum(),d.no_target_validation.sum(),d.no_target_updates.sum()]
    y=np.arange(len(labels)); axs[1].barh(y,vals,color=C['alns'],height=.58); axs[1].set_yticks(y,labels); axs[1].invert_yaxis(); axs[1].set_xlim(0,84); axs[1].set_xlabel('Reports satisfying audit / 80'); panel(axs[1],'b','Structural audit across 80 transfers')
    for yy,v in zip(y,vals): axs[1].text(v+1,yy,f'{v}/80',va='center',fontsize=FSS)
    save(fig,'FigS4_R4E2_zero_shot_audit',out)

def s5(data,out):
    d=pd.read_csv(data/'S5_R5H_operational_by_day.csv'); x=np.arange(len(d)); w=.23
    fig,ax=plt.subplots(figsize=(W_MID,82*MM),layout='constrained')
    ax.bar(x-w,d.attempts,width=w,label='attempts',color=C['alns']); ax.bar(x,d.changes,width=w,label='route changes',color=C['dddas']); ax.bar(x+w,d.cap_terminations,width=w,label='cap terminations',color=C['env2']); ax.set_xticks(x,[f'Day {v}' for v in d.day]); ax.set_ylabel('Count'); ax.legend(loc='upper left',ncol=1); panel(ax,'a','DDDAS action selectivity by day')
    save(fig,'FigS5_R5H_operational_counts',out)

def s6(data,out):
    d=pd.read_csv(data/'S6_R5H_decision_outcomes.csv')
    def count(level, category):
        row=d.loc[d['level'].eq(level) & d['category'].eq(category), 'count']
        if row.empty:
            raise KeyError(f'Missing S6 row: {level} / {category}')
        return int(row.iloc[0])
    def denom(level, category):
        row=d.loc[d['level'].eq(level) & d['category'].eq(category), 'denominator']
        if row.empty:
            raise KeyError(f'Missing S6 denominator: {level} / {category}')
        return int(row.iloc[0])

    conditional_positive=count('conditional_change','positive conditional gain')
    executed_changes=denom('conditional_change','positive conditional gain')
    improved=count('changed_run','realized improve')
    tied=count('changed_run','realized tie')
    worsened=count('changed_run','realized worsen')
    changed_runs=denom('changed_run','realized improve')
    next_customer=count('change_location','next customer changed')
    later_suffix=count('change_location','later suffix only')

    fig,axs=plt.subplots(1,3,figsize=(W_FULL,68*MM),layout='constrained')
    axs[0].bar([0],[conditional_positive],color=C['improve'],width=.55)
    axs[0].set_xticks([0],['conditional\ngain > 0'])
    axs[0].set_ylim(0,max(5,executed_changes*1.10))
    axs[0].set_ylabel('Executed changes')
    axs[0].text(0,conditional_positive+executed_changes*.025,
                f'{conditional_positive}/{executed_changes}',ha='center',fontsize=FSS)
    panel(axs[0],'a','Decision-time criterion')

    vals=[improved,tied,worsened]
    labs=['improve','tie','worsen']
    cols=[C['improve'],C['tie'],C['worsen']]
    axs[1].bar(np.arange(3),vals,color=cols,width=.62)
    axs[1].set_xticks(np.arange(3),labs,rotation=20)
    axs[1].set_ylim(0,max(vals)*1.14)
    axs[1].set_ylabel(f'Changed runs / {changed_runs}')
    panel(axs[1],'b','Ex-post realized objective')

    vals2=[next_customer,later_suffix]
    labs2=['next customer','later suffix']
    axs[2].bar(np.arange(2),vals2,color=[C['env2'],C['dddas']],width=.62)
    axs[2].set_xticks(np.arange(2),labs2,rotation=20)
    axs[2].set_ylim(0,max(vals2)*1.10)
    axs[2].set_ylabel(f'Route modifications / {executed_changes}')
    panel(axs[2],'c','Where the suffix changes')
    save(fig,'FigS6_R5H_conditional_vs_realized',out)

def main():
    here=Path(__file__).resolve().parent
    root=here.parent
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,default=root/'figure_data'/'supplementary')
    ap.add_argument('--out',type=Path,default=root/'figures'/'supplementary')
    a=ap.parse_args()
    for fn in (s1,s2,s3,s4,s5,s6): fn(a.data,a.out)
if __name__=='__main__': main()
