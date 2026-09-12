#!/usr/bin/env python3
"""Mechanical audit of the frozen confirmatory summaries and revised source.

This script verifies the numerical invariants used by Figures 1--6 and S1--S6,
bidirectional LaTeX/BibTeX citation integrity, absence of legacy material after a
single end{document}, and byte identity of the preserved V3 main figure assets.
"""
from pathlib import Path
import hashlib, re
import pandas as pd

ROOT=Path(__file__).resolve().parent.parent
MAIN=ROOT/'figure_data'/'main'
SUPP=ROOT/'figure_data'/'supplementary'

def close(a,b,tol=1e-6):
    assert abs(float(a)-float(b)) <= tol, (a,b,tol)

def main():
    # R3 online fairness
    s1=pd.read_csv(SUPP/'S1_R3_budget_parity.csv')
    assert len(s1)==6 and set(s1.scenario_evals)=={25100} and set(s1.evaluated_candidates)=={250}

    # R4D mean-impact control
    s2=pd.read_csv(SUPP/'S2_R4D_mean_impact_control.csv')
    assert list(s2.eta)==[0,.15,.35,.55,.70]
    assert s2.target_mean_multiplier.nunique()==1
    close(s2.target_mean_multiplier.iloc[0],1.052489)
    assert [round(v,4) for v in s2.kappa]==[.6953,.7646,.9000,1.1418,1.4816]
    env=pd.read_csv(MAIN/'Fig2_environment.csv')
    close(env.iloc[0].fano,1.02); close(env.iloc[-1].fano,11.02)

    # R4D routing persistence
    p=pd.read_csv(MAIN/'Fig3_persistence_routing.csv')
    ort=p[p.method.eq('OR-Tools')].set_index('eta')
    close(ort.loc[0.0,'cvar95'],60.741); close(ort.loc[0.7,'cvar95'],113.244)

    # R4E1 nine-day confirmatory primary analysis
    s3=pd.read_csv(SUPP/'S3_R4E1_crossday_gains.csv')
    assert list(s3.day)==list(range(1,10)) and (s3.delta_J>0).all() and (s3.delta_tail>0).all()
    close(s3.delta_J.mean(),8.611341,1e-6); close(s3.delta_tail.mean(),7.276041,1e-6)
    m4=pd.read_csv(MAIN/'Fig4_crossday.csv')
    pd.testing.assert_frame_equal(s3,m4,check_exact=True)

    # R4E2 zero-shot integrity
    s4=pd.read_csv(SUPP/'S4_R4E2_zero_shot_audit.csv')
    assert list(s4.target_day)==list(range(2,10))
    assert s4.completed_reports.sum()==80
    for c in ['budget_pass','weights_unchanged','no_target_training','no_target_validation','no_target_updates']:
        assert s4[c].sum()==80

    # R5-H bounded causal recourse
    s5=pd.read_csv(SUPP/'S5_R5H_operational_by_day.csv')
    assert s5.runs.sum()==180 and s5.episodes.sum()==391 and s5.attempts.sum()==523
    assert s5.changes.sum()==87 and s5.cap_terminations.sum()==194
    s6=pd.read_csv(SUPP/'S6_R5H_decision_outcomes.csv')
    z={(r.level,r.category):(int(r['count']),int(r.denominator)) for _,r in s6.iterrows()}
    assert z[('conditional_change','positive conditional gain')]==(87,87)
    assert z[('changed_run','realized improve')]==(18,65)
    assert z[('changed_run','realized tie')]==(3,65)
    assert z[('changed_run','realized worsen')]==(44,65)
    assert z[('change_location','next customer changed')]==(19,87)
    assert z[('change_location','later suffix only')]==(68,87)
    counts=pd.read_csv(MAIN/'Fig6D_counts.csv')
    q={(r.level,r.category):int(r['count']) for _,r in counts.iterrows()}
    assert q[('attempt','total')]==523 and q[('attempt','changed')]==87 and q[('attempt','capped')]==194
    assert q[('run','total')]==180 and q[('run','with_change')]==65
    assert [q[('run',k)] for k in ['improve','tie','worsen']]==[18,3,44]

    # Source constraints / no legacy tail
    tex=(ROOT/'manuscript'/'CVRPTW_Memory_Revised.tex').read_text()
    assert tex.count(r'\end{document}')==1
    assert tex.count(r'\section{Related Work}')==1
    assert len(re.findall(r'figures/main/pdf/Fig[1-6]_',tex))==6
    required=['exogenous','no route-to-Hawkes feedback','0.95','nine Athens-derived','18 improve','3 tie','44 worsen']
    low=tex.lower()
    for phrase in required:
        assert phrase.lower() in low, phrase

    # Bidirectional citation/BibTeX integrity
    cited=set()
    for m in re.finditer(r'\\cite\w*\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}',tex):
        cited.update(k.strip() for k in m.group(1).split(',') if k.strip())
    bib=(ROOT/'manuscript'/'cvrptw_references_revised.bib').read_text()
    bkeys=set(re.findall(r'^@\w+\{([^,]+),',bib,re.M))
    assert cited==bkeys, (sorted(cited-bkeys), sorted(bkeys-cited))

    # Byte identity of preserved V3 figures
    hashes=pd.read_csv(ROOT/'audits'/'MAIN_FIGURES_V3_ORIGINAL_SHA256.csv')
    for _,r in hashes.iterrows():
        p=ROOT/'figures'/'main'/r['format']/r['filename']
        assert p.exists()
        assert hashlib.sha256(p.read_bytes()).hexdigest()==r['sha256_original_v3']

    print('FROZEN RESULT AUDIT: PASS')
    print('R3 parity: 6/6 methods at 25,100 scenario evals and 250 candidates')
    print('R4E1: 9/9 days positive; mean delta J=8.611341, mean delta tail=7.276041')
    print('R4E2: 80/80 structural zero-shot reports pass')
    print('R5-H: 523 attempts, 87 changes, realized changed-run outcomes 18/3/44')
    print(f'Citations: {len(cited)} used = {len(bkeys)} bibliography entries')
    print('Main Figures 1-6 V3: byte-identical in PDF/PNG/TIFF')

if __name__=='__main__':
    main()
