"""Design-based weighted logistic estimation and domain-aware Taylor linearization.
The independent strata/PSU universe comes from full demographic files. Non-domain
members contribute zero score; never discard PSUs before variance calculation.
"""
from pathlib import Path
import json, warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.special import expit
from patsy import dmatrices, build_design_matrices
BASE=Path(__file__).resolve().parent; R=BASE/'results'
UNIVERSE=pd.read_csv(R/'design_universe.csv')
GROUPS=['Low SII / Low FIB-4','High SII / Low FIB-4','Low SII / Elevated FIB-4','High SII / Elevated FIB-4']
M1='age10 + female + C(race) + C(cycle)'
M2=M1+' + pir + C(education) + bmi5 + waist10'
M3=M2+' + hba1c + sbp10 + nonhdl50 + log_tg + bp_meds + dm_meds'
COVARS={1:M1,2:M2,3:M3}

def psu_cov(influence,data,universe=UNIVERSE):
    influence=np.asarray(influence); influence=influence.reshape(len(data),-1)
    k=influence.shape[1]
    ids=universe[['stratum','psu']].drop_duplicates()
    frame=pd.DataFrame(influence,columns=list(range(k)))
    frame['stratum']=data.stratum.to_numpy(); frame['psu']=data.psu.to_numpy()
    sums=frame.groupby(['stratum','psu'])[list(range(k))].sum()
    scores=ids.merge(sums,on=['stratum','psu'],how='left').fillna(0)
    cov=np.zeros((k,k)); df=0
    for _,h in scores.groupby('stratum'):
        a=h[list(range(k))].to_numpy(); nh=len(a)
        assert nh>=2, 'Singleton PSU requires an explicit variance policy'
        centered=a-a.mean(axis=0); cov+=nh/(nh-1)*(centered.T@centered); df+=nh-1
    return cov,df

def estimate(x,d,universe=UNIVERSE,proportion=False):
    x=np.asarray(x,float); ok=np.isfinite(x)
    sub=d.loc[ok]; x=x[ok]; w=sub.weight.to_numpy()
    p=np.average(x,weights=w)
    cov,df=psu_cov((w*(x-p)/w.sum())[:,None],sub,universe)
    se=np.sqrt(cov[0,0]); t=stats.t.ppf(.975,df)
    if proportion and 0<p<1:
        z=np.log(p/(1-p)); sez=se/(p*(1-p)); lo,hi=expit([z-t*sez,z+t*sez])
    else: lo,hi=p-t*se,p+t*se
    return dict(n=len(sub),estimate=float(p),se=float(se),lower=float(lo),upper=float(hi),df=df)

def fit(formula,d,universe=UNIVERSE):
    y,X=dmatrices(formula,d,return_type='dataframe',NA_action='raise')
    names=list(X); design=X.design_info; x=X.to_numpy(); y=y.to_numpy().ravel()
    # Only constant nuisance columns are removed (e.g. sex in a sex-specific model).
    keep=[i for i,n in enumerate(names) if n=='Intercept' or np.ptp(x[:,i])>0]
    x=x[:,keep]; names=[names[i] for i in keep]
    assert np.linalg.matrix_rank(x)==x.shape[1], ('Rank deficiency',formula)
    w=d.weight.to_numpy(); w=w/w.mean()
    res=sm.GLM(y,x,family=sm.families.Binomial(),freq_weights=w).fit(maxiter=150,tol=1e-10)
    assert res.converged
    mu=res.fittedvalues; h=(x.T*(w*mu*(1-mu)))@x
    bread=np.linalg.inv(h); scores=x*(w*(y-mu))[:,None]
    influence=scores@bread.T
    cov,df=psu_cov(influence,d,universe)
    se=np.sqrt(np.maximum(np.diag(cov),0)); crit=stats.t.ppf(.975,df)
    rows={}
    for i,n in enumerate(names):
        rows[n]=dict(beta=float(res.params[i]),se=float(se[i]),or_value=float(np.exp(res.params[i])),lower=float(np.exp(res.params[i]-crit*se[i])),upper=float(np.exp(res.params[i]+crit*se[i])),p=float(2*stats.t.sf(abs(res.params[i]/se[i]),df)))
    serial=dict(n=len(d),events=int(y.sum()),formula=formula,df=df,parameters=rows,beta=res.params.tolist(),covariance=cov.tolist(),parameter_names=names,converged=True,max_score=float(np.max(np.abs(scores.sum(axis=0)))),condition_number=float(np.linalg.cond(h)))
    internal=dict(beta=res.params,cov=cov,design=design,keep=keep,names=names,influence=influence,df=df)
    return serial,internal

def delta(value,gradient,cov,df):
    se=float(np.sqrt(max(0,np.asarray(gradient)@cov@np.asarray(gradient))))
    t=stats.t.ppf(.975,df)
    return dict(estimate=float(value),se=se,lower=float(value-t*se),upper=float(value+t*se))

def interactions(internal,d,universe=UNIVERSE):
    b=internal['beta']; c=internal['cov']; names=internal['names']; df=internal['df']
    def unit(name):
        a=np.zeros(len(b)); a[names.index(name)]=1; return a
    v10=unit('high_sii'); v01=unit('high_fib4'); v11=v10+v01+unit('high_sii:high_fib4')
    ors=np.exp([v10@b,v01@b,v11@b]); a,q,j=ors
    ga=a*v10; gq=q*v01; gj=j*v11
    r=j-a-q+1; gr=gj-ga-gq
    or_metrics={'RERI_OR':delta(r,gr,c,df),'AP_OR':delta(r/j,gr/j-r*gj/j**2,c,df)}
    den=a+q-2
    if a>1 and q>1 and den>0:
        or_metrics['S_OR']=delta((j-1)/den,gj/den-(j-1)*(ga+gq)/den**2,c,df)
    else: or_metrics['S_OR']={'estimate':None,'reason':'Not interpretable as synergy index when either single-exposure OR <=1'}
    joint=[]
    for v in [np.zeros(len(b)),v10,v01,v11]:
        se=np.sqrt(v@c@v); bb=v@b; t=stats.t.ppf(.975,df)
        joint.append(dict(or_value=float(np.exp(bb)),lower=float(np.exp(bb-t*se)),upper=float(np.exp(bb+t*se))))
    ii=names.index('high_sii:high_fib4')
    p=float(2*stats.t.sf(abs(b[ii]/np.sqrt(c[ii,ii])),df))
    # Survey-standardized prevalences; influence includes empirical covariate
    # distribution uncertainty and its covariance with fitted coefficients.
    risk=[]; influences=[]
    w=d.weight.to_numpy(); norm=w/w.sum()
    for hs,hf in [(0,0),(1,0),(0,1),(1,1)]:
        mod=d.copy(); mod['high_sii']=hs; mod['high_fib4']=hf
        x=np.asarray(build_design_matrices([internal['design']],mod)[0])[:,internal['keep']]
        pred=expit(x@b); pbar=float(norm@pred)
        g=(x*(norm*pred*(1-pred))[:,None]).sum(axis=0)
        influences.append(internal['influence']@g+norm*(pred-pbar))
        risk.append(pbar)
    cv,_=psu_cov(np.column_stack(influences),d,universe)
    r00,r10,r01,r11=risk
    contrast=r11-r10-r01+r00
    gradient=np.array([1,-1,-1,1.])
    add=delta(contrast,gradient,cv,df)
    reri=delta(contrast/r00,gradient/r00-np.array([contrast/r00**2,0,0,0]),cv,df)
    ap=delta(contrast/r11,gradient/r11-np.array([0,0,0,contrast/r11**2]),cv,df)
    return dict(joint_OR=joint,multiplicative_p=p,**or_metrics,standardized_prevalences=risk,standardized_prevalence_covariance=cv.tolist(),prevalence_interaction=add,RERI_PR=reri,AP_PR=ap)

def run_model(d,model=3,outcome='advanced_ckm',universe=UNIVERSE,covars=None):
    f=outcome+' ~ high_sii * high_fib4 + '+(covars or COVARS[model])
    s,i=fit(f,d,universe); s['interaction']=interactions(i,d,universe)
    return s

def prep_secondary(d,meta):
    d=d.copy()
    d['age10']=(d.age-55)/10; d['sbp10']=(d.sbp-130)/10; d['bmi5']=d.bmi/5; d['waist10']=d.waist/10
    d['nonhdl50']=d.nonhdl/50; d['log_tg']=np.log(d.triglycerides)
    d['high_sii']=(d.sii>=meta['sii_cutoffs'][str(2/3)]).astype(int); d['high_fib4']=(d.fib4>=1.3).astype(int)
    return d

def main():
    d=pd.read_csv(BASE/'data'/'analytic_cohort.csv')
    meta=json.loads((R/'cohort_metadata.json').read_text())
    out={'cohort':meta,'design':dict(method='Weighted binomial pseudo-likelihood; stratified PSU Taylor linearization, full-universe zero-score domain handling',df_rule='PSUs minus strata, t inference; no model-parameter subtraction',pooling='Exploratory duration mixture: 3.2/5.2 and 2/5.2. Not uninterrupted 2017-2023 surveillance.',weights='2017-2020 WTMECPRP; 2021-2023 WTPH2YR'),'models':{},'sensitivities':{},'secondary':{},'subgroups':{}}
    out['prevalence']=estimate(d.advanced_ckm,d,proportion=True)
    for m in [1,2,3]:
        out['models'][f'Model {m}']=run_model(d,m); print('Model',m,out['models'][f'Model {m}']['interaction'],flush=True)
    # Group/continuous weighted Table 1, all entries with sample denominators and design CIs.
    tab={}
    variables={'age':'Age, years','female':'Female, proportion','bmi':'BMI, kg/m2','waist':'Waist, cm','pir':'Income-to-poverty ratio','sbp':'Systolic BP, mm Hg','dbp':'Diastolic BP, mm Hg','hba1c':'HbA1c, %','tc':'Total cholesterol, mg/dL','hdl':'HDL cholesterol, mg/dL','nonhdl':'Non-HDL cholesterol, mg/dL','triglycerides':'Nonfasting biochemistry triglycerides, mg/dL','egfr':'eGFR, mL/min/1.73m2','uacr':'Harmonized UACR, mg/g','sii':'SII','fib4':'FIB-4','bp_meds':'BP medication, proportion','dm_meds':'Diabetes medication, proportion','lipid_meds':'Cholesterol medication, proportion','smoker':'Current smoker, proportion','diabetes':'Diabetes, proportion','hypertension':'Hypertension, proportion','clinical_cvd':'Clinical CVD, proportion','ckd':'Kidney abnormality, proportion','advanced_ckm':'Advanced operational CKM, proportion'}
    for cat,values in [('race',[1,2,3,4,6,7]),('education',[1,2,3,4,5]),('ckm_stage',list(range(5))),('cycle',['2017-2020','2021-2023'])]:
        for val in values:
            key=f'{cat}_{val}'; d[key]=d[cat].eq(val).astype(int); variables[key]=key+', proportion'
    for key,label in variables.items():
        tab[label]={}
        for g in ['Overall',0,1,2,3]:
            dd=d if g=='Overall' else d.loc[d.joint==g]
            tab[label][str(g)]=estimate(dd[key],dd,proportion=('proportion' in label))
    out['table1']=tab
    out['group_n']={str(g):int((d.joint==g).sum()) for g in range(4)}
    # Continuous and categorized SII, with adjusted continuous SII x FIB-4 interaction.
    for label,exposure in [('SII per weighted SD log2','log2_sii_z'),('SII tertiles','C(sii_tertile)'),('SII quartiles','C(sii_quartile)'),('Continuous SII by FIB-4','log2_sii_z * high_fib4')]:
        s,_=fit('advanced_ckm ~ '+exposure+' + high_fib4 + '+M3,d)
        out['sensitivities'][label]=s
    for label,change,outcome in [
        ('Age-specific FIB-4',{'high_fib4':'high_fib4_age'},'advanced_ckm'),
        ('Median SII',{'high_sii':'high_sii_median'},'advanced_ckm'),
        ('Statin input all zero',{},'advanced_statin0'),
        ('Statin input all one',{},'advanced_statin1'),
        ('Unbridged urine and ALT',{'high_fib4':'raw_fib4_high'},'advanced_unbridged')]:
        dd=d.copy(); dd['raw_fib4_high']=(dd.fib4_unbridged>=1.3).astype(int)
        for target,source in change.items(): dd[target]=dd[source]
        out['sensitivities'][label]=run_model(dd,outcome=outcome)
    out['sensitivities']['Flexible age adjustment']=run_model(d,covars=M3.replace('age10','bs(age, df=4, degree=3)'))
    out['sensitivities']['Smoking adjustment']=run_model(d,covars=M3+' + smoker')
    dd=d.loc[d.age>=35].copy()
    out['sensitivities']['Age >=35']=run_model(dd)
    dd=d.loc[d.RIDEXPRG.ne(3)].copy()
    out['sensitivities']['Exclude indeterminate pregnancy']=run_model(dd)
    dd=d.copy(); dd.weight=dd.base_weight*.5
    out['sensitivities']['Equal cycle weights']=run_model(dd)
    dd=d.copy(); dd.weight=dd.mec_weight*np.where(dd.cycle.eq('2017-2020'),3.2/5.2,2/5.2)
    out['sensitivities']['Requested MEC weights (nonpreferred)']=run_model(dd)
    for label,mask in [('Female',d.female==1),('Male',d.female==0),('Age <65',d.age<65),('Age >=65',d.age>=65),('2017-2020',d.cycle=='2017-2020'),('2021-2023',d.cycle=='2021-2023')]:
        dd=d.loc[mask].copy()
        universe=UNIVERSE.loc[UNIVERSE.cycle==label] if label in ['2017-2020','2021-2023'] else UNIVERSE
        # Age strata use requested age-specific FIB-4 cutoff.
        if label.startswith('Age'): dd['high_fib4']=dd.high_fib4_age
        out['subgroups'][label]=run_model(dd,universe=universe)
    for cat in ['female','cycle']:
        nuisance=M3.replace(' + female','') if cat=='female' else M3
        s,_=fit('advanced_ckm ~ high_sii * high_fib4 * C('+cat+') + '+nuisance,d)
        out['sensitivities']['Three-way interaction by '+cat]=s
    a=prep_secondary(pd.read_csv(R/'adult_core_cohort.csv'),meta)
    required=['age10','female','race','cycle','pir','education','bmi5','waist10','hba1c','sbp10','nonhdl50','log_tg','bp_meds','dm_meds']
    for outcome in ['clinical_cvd','ckd']:
        dd=a.dropna(subset=required+[outcome])
        out['secondary'][outcome]=run_model(dd,outcome=outcome)
    # Missingness comparison before socioeconomic exclusions.
    eligible=pd.read_csv(R/'primary_eligible_cohort.csv')
    eligible['included']=eligible.SEQN.isin(d.SEQN).astype(int)
    out['complete_case_comparison']={}
    for g in [0,1]:
        dd=eligible.loc[eligible.included==g]
        out['complete_case_comparison'][str(g)]={v:estimate(dd[v],dd,proportion=v in ['female','advanced_ckm']) for v in ['age','female','advanced_ckm']}
    (R/'statistical_output.json').write_text(json.dumps(out,indent=2,allow_nan=False))
    def fmt(v,scale=1): return f"{scale*v['estimate']:.2f} ({scale*v['lower']:.2f}, {scale*v['upper']:.2f})"
    lines=['# Table 1. Primary complete-case cohort','', 'Weighted means or percentages (95% CI); n is unweighted. Percentages use logit confidence intervals. Full domain survey design retained.','',
           '| Characteristic | Overall | G1 | G2 | G3 | G4 |','|---|---:|---:|---:|---:|---:|',
           '| n | '+str(len(d))+' | '+' | '.join(str(out['group_n'][str(g)]) for g in range(4))+' |']
    for label,row in tab.items(): lines.append('| '+label.replace('proportion','%')+' | '+' | '.join(fmt(row[g],100 if 'proportion' in label else 1) for g in ['Overall','0','1','2','3'])+' |')
    lines+=['','G1: low SII/low FIB-4; G2: high SII/low FIB-4; G3: low SII/elevated FIB-4; G4: both high. High SII is the pooled survey-weighted upper tertile.','Race codes: 1 Mexican American, 2 other Hispanic, 3 non-Hispanic White, 4 non-Hispanic Black, 6 non-Hispanic Asian, 7 other/multiracial. Education: 1 <9th grade, 2 9th-11th grade, 3 high school/GED, 4 some college/AA, 5 college graduate.']
    (BASE/'Table_1_Full_Baseline_Characteristics.md').write_text('\n'.join(lines),encoding='utf8')
    lines=['# Table 2. Regression and interaction models','','OR-based RERI/AP are descriptive odds-scale contrasts, not causal risk interaction. Standardized prevalence interaction is the additive probability-scale contrast. All analyses are exploratory; no multiplicity correction.','']
    for section in ['models','secondary','subgroups','sensitivities']:
        lines+=['## '+section,'','| Analysis | n / events | G2 OR (95% CI) | G3 OR (95% CI) | G4 OR (95% CI) | Multiplicative p | RERI-OR (95% CI) | AP-OR fraction (95% CI) | Standardized prevalence interaction, percentage points (95% CI) |','|---|---:|---|---|---|---|---|---|---|']
        for label,s in out[section].items():
            if 'interaction' not in s: continue
            it=s['interaction']; ors=it['joint_OR']
            cells=[f"{o['or_value']:.3f} ({o['lower']:.3f}, {o['upper']:.3f})" for o in ors[1:]]
            lines.append('| '+label+f" | {s['n']} / {s['events']} | "+' | '.join(cells)+f" | {it['multiplicative_p']:.4g} | "+fmt(it['RERI_OR'])+' | '+fmt(it['AP_OR'])+' | '+fmt(it['prevalence_interaction'],100)+' |')
        lines.append('')
    lines+=['## Additional primary interaction metrics','','| Model | S-OR (95% CI) | Standardized RERI-PR (95% CI) | Standardized AP-PR, % (95% CI) | Standardized prevalence G1 / G2 / G3 / G4, % |','|---|---|---|---|---|']
    for label,s in out['models'].items():
        it=s['interaction']; smetric=it['S_OR']
        sval=fmt(smetric) if smetric['estimate'] is not None else smetric['reason']
        lines.append('| '+label+' | '+sval+' | '+fmt(it['RERI_PR'])+' | '+fmt(it['AP_PR'],100)+' | '+' / '.join(f'{100*p:.2f}' for p in it['standardized_prevalences'])+' |')
    for label,s in out['sensitivities'].items():
        if 'interaction' in s: continue
        lines+=['## '+label,'','| Term | OR | 95% CI | p |','|---|---:|---|---:|']
        for term,v in s['parameters'].items():
            if term.startswith(('log2','C(sii','high_fib4','high_sii')):
                lines.append(f"| {term} | {v['or_value']:.4f} | {v['lower']:.4f}, {v['upper']:.4f} | {v['p']:.5g} |")
    lines+=['','Model 1: age, sex, race/ethnicity, cycle. Model 2 adds income, education, BMI and waist. Model 3 adds HbA1c, systolic pressure, non-HDL cholesterol, log nonfasting biochemistry triglycerides, BP and glycemic medication use. Model 3 conditions on components of the outcome and is descriptive, potentially overadjusted. Age subgroups use age-specific FIB-4 thresholds; other subgroups use 1.3.']
    (BASE/'Table_2_Regression_and_Interaction_Models.md').write_text('\n'.join(lines),encoding='utf8')
    print('Saved statistical_output.json',flush=True)
if __name__=='__main__': main()

