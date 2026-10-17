"""Read-only recomputation and location-specific numerical checks for v2.

All regenerated outputs are confined to a temporary directory. This verifies
the saved analysis, not the validity of clinical claims or bibliography.
"""
from pathlib import Path
import contextlib
import hashlib
import importlib.util
import io
import json
import re
import shutil
import tempfile
from unittest.mock import patch
import numpy as np
import pandas as pd
from scipy import stats

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent


def load(name, folder=BASE):
    spec = importlib.util.spec_from_file_location(name, folder / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def equal(a, b, path='root'):
    if isinstance(a, dict):
        assert a.keys() == b.keys(), path + ': keys differ'
        for k in a:
            equal(a[k], b[k], path + '/' + str(k))
    elif isinstance(a, list):
        assert len(a) == len(b), path
        for k, (x, y) in enumerate(zip(a, b)):
            equal(x, y, path + '/' + str(k))
    elif isinstance(a, (int, float)) and not isinstance(a, bool):
        assert np.isclose(a, b, rtol=1e-7, atol=1e-9, equal_nan=False), (path, a, b)
    else:
        assert a == b, (path, a, b)


def rows(text):
    return [[c.strip() for c in line.strip('|').split('|')]
            for line in text.splitlines() if line.startswith('|')]


def manuscript_word_counts(text):
    """Count rendered words, including section headings and numeric estimates.

    Exclude Markdown/TeX control syntax and standalone operators. Decimal,
    hyphenated and range tokens count as one word; abstract headings are excluded.
    Main text is Sections 1-5 only; keywords, declarations and legends are excluded.
    """
    def count(part):
        part = re.sub(r'\\(?:text|mathrm|mathbf|operatorname)\{([^{}]*)\}', r'\1', part)
        part = re.sub(r'\\[A-Za-z]+', ' ', part)
        part = re.sub(r'[$`*{}_^#]', '', part)
        return len(re.findall(r"[A-Za-z0-9]+(?:[’'.,:/–-][A-Za-z0-9]+)*", part))
    main = text.split('## 1. INTRODUCTION', 1)[1].split('## CONFLICT OF INTEREST STATEMENT', 1)[0]
    abstract = text.split('## ABSTRACT', 1)[1].split('**Keywords:**', 1)[0]
    abstract = re.sub(r'\*\*(?:Background|Methods|Results|Conclusions):\*\*', '', abstract)
    return count('1. INTRODUCTION\n'+main), count(abstract)


def check_editorial(text):
    main, abstract = manuscript_word_counts(text)
    assert main <= 3000, f'Main text exceeds 3000 words: {main}'
    assert abstract <= 300, f'Abstract exceeds 300 words: {abstract}'
    assert f'**Word Count:** {main:,} main-text words; {abstract} abstract words' in text
    assert '## FIGURE LEGENDS' in text and text.index('## FIGURE LEGENDS') > text.index('## REFERENCES')
    assert not re.search(r'Zero[- ]Hallucination', text, re.I)
    assert not re.search(r'`[^`]*[a-z]+_[a-z_0-9]+[^`]*`', text), 'Internal model key in prose'
    for key in ['very_high_ckd','adult_core_cvd_M2','adult_core_ckd_M2','steatosis_high_cap_M2',
                'hscrp_ge3_M2','raw_unbridged_hscrp_M2','vcte_3level_M2','continuous_kpa_crp_M2',
                'exclude_acute_crp_gt10_M2','uniform_prevent_domain_M2','flexible_age_spline_M2',
                'vcte_x_sii_M2','log2_kpa_z','log2_fib4_z','log2_hscrp_z','log2_sii_z']:
        assert key not in text, 'Internal model key: '+key
    methods=text.split('## 2. METHODS',1)[1].split('## 3. RESULTS',1)[0]
    for field in ['WTMECPRP','WTPH2YR','LUAXSTAT','LUANMVGP','LUXSIQRM','LBXHSCRP']:
        assert field in methods, 'Missing official field: '+field
    cover=(BASE/'COVER_LETTER_AND_ZERO_FEE_SUBMISSION_GUIDE.md').read_text(encoding='utf8')
    assert f'Word count: {main:,} main-text words; Abstract: {abstract} words;' in cover
    assert not re.search(r'Zero[- ]Hallucination',cover,re.I)
    for name in ['Table_1_Baseline.md','Table_3_VCTE_vs_FIB4_Diagnostic_Comparison.md']:
        table=(BASE/name).read_text(encoding='utf8')
        assert '>=' not in table and 'log2_' not in table
    print(f'  [PASS] V2.2 editorial checks: main text {main:,} words; abstract {abstract} words; legends, metadata and terminology verified.')


def check_tables(stat, expected_dir, actual_dir=BASE):
    for name in ['Table_1_Baseline.md', 'Table_2_Multivariable_Joint_Models.md',
                 'Table_3_VCTE_vs_FIB4_Diagnostic_Comparison.md']:
        actual = rows((actual_dir / name).read_text(encoding='utf8'))
        expected = rows((expected_dir / name).read_text(encoding='utf8'))
        assert actual == expected, name + ': table cell/header differs from JSON rendering'
        assert (actual_dir/name).read_text(encoding='utf8') == (expected_dir/name).read_text(encoding='utf8'), name + ': full table text differs'
    # Independent unit check: HbA1c is already in percent, not a proportion.
    row = next(r for r in rows((actual_dir / 'Table_1_Baseline.md').read_text(encoding='utf8'))
               if r[0] == 'HbA1c, %')
    for cell, group in zip(row[1:], ['Overall', '0', '1', '2', '3']):
        vals = [float(v) for v in re.findall(r'\d+\.\d+', cell)]
        ref = stat['table1']['HbA1c, %'][group]
        assert vals == [round(ref[k], 1) for k in ['estimate', 'lower', 'upper']]


def check_manuscript(s, text, d, universe):
    """Check study-result locations, including all model CIs and stated p-values."""
    def need(scope, token):
        assert token in scope, 'Manuscript missing/mismatched: ' + token
    def ci(v, key='estimate', scale=1, digits=2, percent=False):
        suffix = '%' if percent else ''
        return (f"{scale*v[key]:.{digits}f}{suffix} (95% CI: "
                f"{scale*v['lower']:.{digits}f}{suffix}–{scale*v['upper']:.{digits}f}{suffix}")
    def section(start, end):
        return text.split(start, 1)[1].split(end, 1)[0]
    abstract = section('## ABSTRACT', '## 1. INTRODUCTION')
    baseline = section('### 3.1 ', '### 3.2 ')
    models = section('### 3.2 ', '### 3.3 ')
    secondary = section('### 3.3 ', '### 3.4 ')
    sensitivity = section('### 3.4 ', '### 3.5 ')
    diagnostic = section('### 3.5 ', '## 4. DISCUSSION')
    need(text, f"$N = {len(universe):,}$")
    need(text, f"all {len(universe[['stratum','psu']].drop_duplicates())} stratum–PSU combinations and {universe.stratum.nunique()} pseudo-strata")
    need(abstract, f"{s['metadata']['n']:,} adults")
    need(abstract, f"$n={s['metadata']['n_events_advanced_ckm']:,}$")
    need(text, '$df = 40$')
    need(baseline, f"{d.weight.sum()/1e6:.1f} million")
    flow = json.loads((BASE/'results/v2_strobe_waterfall.json').read_text())
    need(baseline, f"{flow['initial_analytic_cohort']:,} eligible participants")
    need(baseline, f"{flow['step5_reliable_iqrm_le30pct']:,} ({100*flow['step5_reliable_iqrm_le30pct']/flow['initial_analytic_cohort']:.1f}%)")
    for key in ['advanced_ckm', 'high_vcte', 'high_hscrp']:
        need(abstract, f"{100*s['prevalences'][key]['estimate']:.1f}%")
        need(baseline, ci(s['prevalences'][key], scale=100, digits=1, percent=True))
    for g in range(4):
        line = next(x for x in baseline.splitlines() if x.startswith(f'- **Group {g} '))
        need(line, f"{100*s['prevalences']['joint_groups'][g]['estimate']:.1f}% weighted")
        need(line, f"$n = {s['metadata']['joint_group_counts'][str(g)]:,}$")
    line = next(x for x in baseline.splitlines() if x.startswith('As shown in **Table 1**'))
    for label, unit, scale in [('BMI, kg/m2','kg/m²',1),('Waist circumference, cm','cm',1),
                                ('HbA1c, %','%',1),('Diabetes mellitus, %','%',100)]:
        v=s['table1'][label]['3']
        token=ci(v,scale=scale,digits=1,percent=unit=='%')
        if unit!='%': token=token.replace(' (95%',f' {unit} (95%')
        need(line,token)
    for g in range(4):
        v=s['table1']['Advanced CKM Syndrome (Stages 3-4), %'][str(g)]
        need(line,ci(v,scale=100,digits=1,percent=True))
    for number in [1,2,3]:
        scope=models.split(f'In **Model {number}**',1)[1].split('In **Model ',1)[0]
        model=s['models'][f'Model {number}']; it=model['interaction']
        for g in [1,2,3]:
            bullet=next(x for x in scope.splitlines() if x.startswith(f'- Group {g} '))
            v=it['joint_OR'][g];need(bullet,ci(v,key='or_value'))
            match=re.search(r'\$p ([=<]) ([\d.]+)\$',bullet)
            if match:
                p=2*stats.t.sf(abs(np.log(v['or_value'])/v['se']),model['df'])
                assert (p<float(match[2])) if match[1]=='<' else f'{p:.3f}'==match[2]
        need(scope,f"$p = {it['multiplicative_p']:.4f}$")
        for label,key in [('RERI','RERI_OR'),('AP','AP_OR')]:
            bullet=next(x for x in scope.splitlines() if label in x and x.strip().startswith('-'))
            need(bullet,ci(it[key]))
            match=re.search(r'\$p ([=<]) ([\d.]+)\$',bullet)
            if match:
                p=2*stats.t.sf(abs(it[key]['estimate']/it[key]['se']),model['df'])
                assert (p<float(match[2])) if match[1]=='<' else f'{p:.3f}'==match[2]
        if number==1:need(scope,ci(it['S_OR']))
    for label,key in [('Chronic Kidney Disease (CKD)','ckd_M2'),('Clinical Cardiovascular Disease','clinical_cvd_M2'),
                       ('Very-High-Risk Chronic Kidney Disease','very_high_ckd_M2')]:
        line=next(x for x in secondary.splitlines() if x.startswith('- **'+label))
        it=s['secondary_outcomes'][key]['interaction'];need(line,ci(it['joint_OR'][3],key='or_value'))
        need(line,f"RERI: {it['RERI_OR']['estimate']:.2f}")
        if key in ['ckd_M2','clinical_cvd_M2']:
            separator=' to ' if key=='ckd_M2' else '–'
            need(line,f"RERI: {it['RERI_OR']['estimate']:.2f}, 95% CI: {it['RERI_OR']['lower']:.2f}{separator}{it['RERI_OR']['upper']:.2f}")
            need(line,f"$p = {it['multiplicative_p']:.4f}$")
    kidney=next(x for x in secondary.splitlines() if x.startswith('- **Chronic Kidney'))
    for g in [1,2]:need(kidney,f"{s['secondary_outcomes']['ckd_M2']['interaction']['joint_OR'][g]['or_value']:.2f}")
    need(secondary, ci(s['secondary_outcomes']['adult_core_cvd_M2']['interaction']['joint_OR'][3], key='or_value'))
    need(secondary, ci(s['secondary_outcomes']['adult_core_ckd_M2']['interaction']['joint_OR'][3], key='or_value'))
    for label,key in [('Sex Stratification','men'),('Sex Stratification','women'),
                       ('Age Stratification (<60','age_lt_60'),('Age Stratification (<60','age_ge_60'),
                       ('Age Stratification (<65','age_lt_65'),('Age Stratification (<65','age_ge_65'),
                       ('Metabolic Status','diabetes'),('Metabolic Status','no_diabetes'),
                       ('NHANES Survey Cycles','cycle_2017_2020'),('NHANES Survey Cycles','cycle_2021_2023')]:
        line=next(x for x in secondary.splitlines() if x.startswith('- **'+label))
        it=s['subgroups'][key]['interaction'];need(line,ci(it['joint_OR'][3],key='or_value'))
        if 'RERI:' in line:need(line,f"RERI: {it['RERI_OR']['estimate']:.2f}")
        if key in ['men','women','age_ge_60','age_ge_65','diabetes','no_diabetes']:
            need(line, f"$p = {it['multiplicative_p']:.4f}$")
    for label,key in [('1. **Steatosis','steatosis_high_cap_M2'),('2. **Alternative','hscrp_ge3_M2'),('3. **Unbridged','raw_unbridged_hscrp_M2'),
                       ('6. **Exclusion of Acute','exclude_acute_crp_gt10_M2'),('7. **Symmetric PREVENT','uniform_prevent_domain_M2'),
                       ('8. **Flexible Non-Linear','flexible_age_spline_M2'),('9. **VCTE $\\times$ Systemic','vcte_x_sii_M2')]:
        line=next(x for x in sensitivity.splitlines() if x.startswith(label))
        result=s['sensitivities'][key]; it=result['interaction']
        need(line,ci(it['joint_OR'][3],key='or_value'))
        need(line,f"RERI: {it['RERI_OR']['estimate']:.2f}")
        need(line,f"$p = {it['multiplicative_p']:.4f}$")
        if '$N =' in line:need(line,f"$N = {result['n']:,}$")
    severity=s['sensitivities']['vcte_3level_M2']
    line=next(x for x in sensitivity.splitlines() if x.startswith('4. **Three-Level'))
    for cat in [1,2]:
        v=severity['joint_6group_OR'][f'cat{cat}_crp1']
        need(line,ci(v,key='or_value'))
        p=2*stats.t.sf(abs(np.log(v['or_value'])/v['se']),severity['df'])
        need(line,f'$p = {p:.4f}$')
        idx=severity['parameter_names'].index(f'C(vcte_cat)[T.{cat}]:high_hscrp')
        p=2*stats.t.sf(abs(severity['beta'][idx]/np.sqrt(severity['covariance'][idx][idx])),severity['df'])
        need(line,f'product interaction $p = {p:.3f}$')
    line=next(x for x in sensitivity.splitlines() if x.startswith('5. **Continuous'))
    continuous=s['sensitivities']['continuous_kpa_crp_M2']
    for term in ['log2_hscrp_z','log2_kpa_z','log2_kpa_z:log2_hscrp_z']:
        idx=continuous['parameter_names'].index(term)
        beta=continuous['beta'][idx];se=np.sqrt(continuous['covariance'][idx][idx])
        crit=stats.t.ppf(.975,continuous['df'])
        need(line,f'{np.exp(beta):.2f}')
        need(line,f"95% CI: {np.exp(beta-crit*se):.2f}–{np.exp(beta+crit*se):.2f}")
        need(line,f"$p = {2*stats.t.sf(abs(beta/se),continuous['df']):.4f}$")
    diag=s['diagnostic_fib4_vs_vcte']
    for label,key in [('Sensitivity','sensitivity'),('Specificity','specificity'),('Positive Predictive Value (PPV)','ppv'),('Negative Predictive Value (NPV)','npv'),('False-Positive Rate','false_positive_rate')]:
        need(diagnostic,f"**{label}:** {100*diag['overall'][key]:.1f}%")
    need(diagnostic,f"**Positive Likelihood Ratio (+LR):** {diag['overall']['pos_lr']:.2f}")
    need(diagnostic,f"{100*(1-diag['overall']['sensitivity']):.1f}%")
    for label,key in [('Younger Adults','age_lt_65'),('Older Adults (Ages 65–79','age_ge_65')]:
        line=next(x for x in diagnostic.splitlines() if x.startswith('- **'+label))
        need(line,f"$N = {diag[key]['n']:,}$")
        for metric in ['specificity','false_positive_rate']:need(line,f"{100*diag[key][metric]:.1f}%")
    need(diagnostic,f"{100*diag['age_lt_65']['ppv']:.1f}%")
    need(diagnostic,f"{diag['age_ge_65']['false_positive_rate']/diag['age_lt_65']['false_positive_rate']:.1f}-fold")
    need(diagnostic, f"false-positive rate from {100*diag['age_ge_65']['false_positive_rate']:.1f}% down to {100*diag['age_calibrated_ge_65']['false_positive_rate']:.1f}%")
    calibrated=diagnostic.split('- **Age-Calibrated FIB-4 Strategy',1)[1].split('**Severe',1)[0]
    for label,key in [('Sensitivity','sensitivity'),('Specificity','specificity'),('Positive Predictive Value (PPV)','ppv'),('Negative Predictive Value (NPV)','npv'),('False-Positive Rate','false_positive_rate')]:
        need(calibrated,f"**{label}:** {100*diag['age_calibrated_overall'][key]:.1f}%")
    need(calibrated,f"**Positive Likelihood Ratio (+LR):** {diag['age_calibrated_overall']['pos_lr']:.2f}")
    for label,key in [('Younger Adults','age_lt_65'),('Older Adults (Ages','age_ge_65'),('Older Adults with Age-Calibrated','age_calibrated_ge_65')]:
        line=next(x for x in diagnostic.splitlines() if x.startswith('- **'+label))
        for metric in ['sensitivity','specificity','ppv','false_positive_rate']:
            need(line,f"{100*diag[key][metric]:.1f}%")
        need(line,f"+LR: {diag[key]['pos_lr']:.2f}")
    for key in ['base_M2', 'vcte_M2', 'fib4_M2', 'dual_vcte_crp_M2', 'dual_fib4_sii_M2']:
        need(diagnostic,ci(s['discrimination']['models'][key],key='auc',digits=4))
    for v in s['discrimination']['contrasts'].values():
        need(diagnostic,f"95% CI: {v['lower']:.4f} to {v['upper']:.4f}")
    # Repeated abstract/discussion estimates and confidence intervals.
    for g in [1,2,3]:need(abstract,ci(s['models']['Model 2']['interaction']['joint_OR'][g],key='or_value'))
    for key in ['clinical_cvd_M2','ckd_M2']:need(abstract,ci(s['secondary_outcomes'][key]['interaction']['joint_OR'][3],key='or_value'))
    need(abstract,f"odds-scale RERI {s['models']['Model 2']['interaction']['RERI_OR']['estimate']:.2f} (95% CI: {s['models']['Model 2']['interaction']['RERI_OR']['lower']:.2f}–{s['models']['Model 2']['interaction']['RERI_OR']['upper']:.2f}; AP: {s['models']['Model 2']['interaction']['AP_OR']['estimate']:.2f})")
    need(abstract,f"standardized prevalence interaction +{100*s['models']['Model 2']['interaction']['prevalence_interaction']['estimate']:.1f} percentage points (95% CI: {100*s['models']['Model 2']['interaction']['prevalence_interaction']['lower']:.1f}–{100*s['models']['Model 2']['interaction']['prevalence_interaction']['upper']:.1f}; prevalence-scale RERI: {s['models']['Model 2']['interaction']['RERI_PR']['estimate']:.2f}, AP: {100*s['models']['Model 2']['interaction']['AP_PR']['estimate']:.1f}%)")


def verify():
    a=load('v2_03_statistical_analysis'); c=load('v2_02_cohort_engineering')
    original=BASE/'results/statistical_output_v2.json'; digest=hashlib.sha256(original.read_bytes()).hexdigest()
    saved=json.loads(original.read_text()); d=pd.read_csv(BASE/'data/v2_analytic_cohort.csv')
    assert Path(a.engine.__file__).resolve()==ROOT/'03_statistical_analysis.py'
    u=pd.read_csv(ROOT/'results/design_universe.csv');pd.testing.assert_frame_equal(a.UNIVERSE,u)
    demos=[]
    for filename,cycle in [('P_DEMO.xpt','2017-2020'),('DEMO_L.xpt','2021-2023')]:
        raw=pd.read_sas(ROOT/'data'/filename)
        demos.append(pd.DataFrame({'SEQN':raw.SEQN.astype(int),'cycle':cycle,
                    'stratum':cycle+'_'+raw.SDMVSTRA.astype(int).astype(str),'psu':raw.SDMVPSU.astype(int)}))
    expected=pd.concat(demos,ignore_index=True)
    pd.testing.assert_frame_equal(u[list(expected)],expected,check_dtype=False)
    ids=u[['stratum','psu']].drop_duplicates()
    assert len(ids)-u.stratum.nunique()==40 and len(u)==27493
    # Zero-score domain test: retain the full design even for a one-person domain.
    _,df=a.psu_cov(np.ones((1,1)),d.iloc[:1],u);assert df==40
    # Rebuild both cohorts from original v1 cohorts and raw LUX/HSCRP files.
    for input_file,output_file in [(ROOT/'data/analytic_cohort.csv','v2_analytic_cohort.csv'),
                                  (ROOT/'results/adult_core_cohort.csv','v2_adult_core_cohort.csv')]:
        rebuilt,flow,meta=c.process_cohort(input_file)
        actual=pd.read_csv(BASE/'data'/output_file)
        pd.testing.assert_frame_equal(rebuilt.reset_index(drop=True),actual,check_dtype=False,rtol=1e-10,atol=1e-10)
        flow_file='v2_strobe_waterfall.json' if output_file=='v2_analytic_cohort.csv' else 'v2_secondary_waterfall.json'
        equal(flow,json.loads((BASE/'results'/flow_file).read_text()))
        if output_file=='v2_analytic_cohort.csv':equal(saved['metadata'],json.loads(json.dumps(meta)))
        pre=actual.cycle.eq('2017-2020')
        for col,raw,intercept,slope in [('alt','LBXSATSI',1.477,.9663),('triglycerides','LBXSTR',.8567,1.012),('albumin_urine','URXUMA',1.381,.8407)]:
            np.testing.assert_allclose(actual[col],np.where(pre,intercept+slope*actual[raw],actual[raw]),equal_nan=True)
        np.testing.assert_allclose(actual.base_weight,np.where(pre,actual.WTMECPRP,actual.WTPH2YR))
        np.testing.assert_allclose(actual.weight,actual.base_weight*np.where(pre,3.2/5.2,2/5.2))
        np.testing.assert_allclose(actual.hscrp,np.where(pre,np.maximum(.08,-.08653+.9672*actual.LBXHSCRP),actual.LBXHSCRP))
    manifest=json.loads((BASE/'results/v2_download_manifest.json').read_text())
    for name,item in manifest.items():
        if name.endswith('.xpt'):assert hashlib.sha256((ROOT/'data'/name).read_bytes()).hexdigest()==item['sha256']
    # Nontrivial tied-score regression case; old AUC implementation returned 1.
    assert a.weighted_c_statistic([0,1],[.5,.5],[1,2])==.5
    # Tied ROC scores must enter at one threshold, independent of row order.
    for y,w in [([0,1],[1,2]),([1,0],[2,1])]:
        assert a.empirical_weighted_roc(y,[.5,.5],w)=={'fpr':[0.,1.],'tpr':[0.,1.]}
    y=np.array([0,1,0,1,1]);pred=np.array([.8,.8,.2,.5,.2]);w=np.array([2.,1.,3.,4.,2.])
    curve=a.empirical_weighted_roc(y,pred,w)
    np.testing.assert_allclose(np.trapezoid(curve['tpr'],curve['fpr']),a.weighted_c_statistic(y,pred,w))
    equal(curve,a.empirical_weighted_roc(y[::-1],pred[::-1],w[::-1]))
    with tempfile.TemporaryDirectory(prefix='v2-audit-') as temp:
        tmp=Path(temp);(tmp/'data').mkdir();(tmp/'results').mkdir()
        (tmp/'sources').mkdir()
        shutil.copy2(ROOT/'sources/prevent_reference.Rmd',tmp/'sources/prevent_reference.Rmd')
        # Rebuild the parent waterfall from raw XPTs; confine all writes to temp.
        parent=load('02_cohort_engineering',ROOT);parent.BASE=tmp;parent.R=tmp/'results'
        read_sas=pd.read_sas
        with patch.object(pd,'read_sas',side_effect=lambda p,*args,**kw:read_sas(ROOT/'data'/Path(p).name,*args,**kw)), contextlib.redirect_stdout(io.StringIO()):
            parent.main()
        equal(json.loads((tmp/'results/strobe_waterfall.json').read_text()),json.loads((ROOT/'results/strobe_waterfall.json').read_text()))
        shutil.copy2(BASE/'data/v2_analytic_cohort.csv',tmp/'data/v2_analytic_cohort.csv')
        shutil.copy2(BASE/'data/v2_adult_core_cohort.csv',tmp/'data/v2_adult_core_cohort.csv')
        shutil.copy2(BASE/'results/v2_cohort_metadata.json',tmp/'results/v2_cohort_metadata.json')
        shutil.copy2(BASE/'results/v2_strobe_waterfall.json',tmp/'results/v2_strobe_waterfall.json')
        shutil.copy2(BASE/'results/v2_secondary_waterfall.json',tmp/'results/v2_secondary_waterfall.json')
        a.BASE=tmp;a.RESULTS_DIR=tmp/'results'
        with contextlib.redirect_stdout(io.StringIO()):a.main()
        recalculated=json.loads((tmp/'results/statistical_output_v2.json').read_text())
        equal(saved,recalculated)
        check_tables(saved,tmp)
        assert rows((BASE/'STROBE_Waterfall_v2.md').read_text(encoding='utf8'))==rows((tmp/'STROBE_Waterfall_v2.md').read_text(encoding='utf8')), 'STROBE rows differ from verified cohort flows'
        for curve in saved['roc_curves'].values():
            for axis in ['fpr','tpr']:
                assert curve[axis][0]==0 and curve[axis][-1]==1
                assert np.all(np.diff(curve[axis])>=0)
        check_manuscript(saved,(BASE/'MANUSCRIPT_FULL_JGIM_NMCD.md').read_text(encoding='utf8'),d,u)
        check_editorial((BASE/'MANUSCRIPT_FULL_JGIM_NMCD.md').read_text(encoding='utf8'))
    assert hashlib.sha256(original.read_bytes()).hexdigest()==digest
    print('  [PASS] Full raw demographic universe, df=40, inherited assay bridges, WTPH2YR, both cohorts, all saved models/SEs/CIs/interactions, diagnostics/AUC and Table 1 estimates recomputed.')
    print('  [PASS] Every table cell and declared manuscript study-result locations match; original JSON unchanged.')


if __name__=='__main__':verify()
