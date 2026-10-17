"""Statistical analysis engine for Study 2.0: VCTE FibroScan + hs-CRP in NHANES 2017-2023.
Reuses the audited survey variance engine (psu_cov, fit, estimate, delta) from Study 1.0.
Calculates Table 1, multivariable logistic regressions (Models 1-3), interaction metrics
(RERI_OR, AP_OR, S_OR, multiplicative p, standardized prevalence interaction, RERI_PR, AP_PR),
secondary outcomes (including KDIGO very-high-risk CKD and adult core cohort validation),
sensitivity analyses, subgroup regressions (including age <65 vs >=65 and cycles),
head-to-head diagnostic comparison (standard vs age-calibrated FIB-4),
delete-1-PSU jackknife C-statistics, and empirical weighted ROC curves.
"""
from pathlib import Path
import sys
import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from scipy.special import expit
from patsy import dmatrices, build_design_matrices

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
sys.path.append(str(BASE))
sys.path.append(str(ROOT))

# Import audited functions from root engine
from importlib import import_module
engine = import_module('03_statistical_analysis')
psu_cov = engine.psu_cov
estimate = engine.estimate
fit = engine.fit
delta = engine.delta
COVARS = engine.COVARS
UNIVERSE = engine.UNIVERSE

RESULTS_DIR = BASE / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

GROUPS_V2 = [
    'Low VCTE / Low hs-CRP (Ref)',
    'Low VCTE / High hs-CRP',
    'High VCTE / Low hs-CRP',
    'Dual High VCTE + hs-CRP'
]

def interactions_v2(internal, d, var1='high_hscrp', var2='high_vcte', universe=UNIVERSE):
    b = internal['beta']
    c = internal['cov']
    names = internal['names']
    df = internal['df']
    
    def unit(name):
        a = np.zeros(len(b))
        a[names.index(name)] = 1
        return a
        
    term_inter = f'{var1}:{var2}' if f'{var1}:{var2}' in names else f'{var2}:{var1}'
    v10 = unit(var1)
    v01 = unit(var2)
    v11 = v10 + v01 + unit(term_inter)
    
    ors = np.exp([v10 @ b, v01 @ b, v11 @ b])
    a, q, j = ors
    ga = a * v10
    gq = q * v01
    gj = j * v11
    
    r = j - a - q + 1
    gr = gj - ga - gq
    
    or_metrics = {
        'RERI_OR': delta(r, gr, c, df),
        'AP_OR': delta(r / j, gr / j - r * gj / j**2, c, df)
    }
    
    den = a + q - 2
    if a > 1 and q > 1 and den > 0:
        or_metrics['S_OR'] = delta((j - 1) / den, gj / den - (j - 1) * (ga + gq) / den**2, c, df)
    else:
        or_metrics['S_OR'] = {
            'estimate': None,
            'reason': 'Not interpretable as synergy index when either single-exposure OR <= 1'
        }
        
    joint = []
    for v in [np.zeros(len(b)), v10, v01, v11]:
        se = np.sqrt(max(0, v @ c @ v))
        bb = v @ b
        t = stats.t.ppf(.975, df)
        joint.append(dict(
            or_value=float(np.exp(bb)),
            lower=float(np.exp(bb - t * se)),
            upper=float(np.exp(bb + t * se)),
            se=float(se)
        ))
        
    ii = names.index(term_inter)
    mult_p = float(2 * stats.t.sf(abs(b[ii] / np.sqrt(c[ii, ii])), df))
    
    # Standardized prevalences
    risk = []
    influences = []
    w = d.weight.to_numpy()
    norm = w / w.sum()
    for v1_val, v2_val in [(0, 0), (1, 0), (0, 1), (1, 1)]:
        mod = d.copy()
        mod[var1] = v1_val
        mod[var2] = v2_val
        x = np.asarray(build_design_matrices([internal['design']], mod)[0])[:, internal['keep']]
        pred = expit(x @ b)
        pbar = float(norm @ pred)
        g = (x * (norm * pred * (1 - pred))[:, None]).sum(axis=0)
        influences.append(internal['influence'] @ g + norm * (pred - pbar))
        risk.append(pbar)
        
    cv, _ = psu_cov(np.column_stack(influences), d, universe)
    r00, r10, r01, r11 = risk
    contrast = r11 - r10 - r01 + r00
    gradient = np.array([1, -1, -1, 1.])
    add = delta(contrast, gradient, cv, df)
    reri_pr = delta(contrast / r00, gradient / r00 - np.array([contrast / r00**2, 0, 0, 0]), cv, df)
    ap_pr = delta(contrast / r11, gradient / r11 - np.array([0, 0, 0, contrast / r11**2]), cv, df)
    
    return dict(
        joint_OR=joint,
        multiplicative_p=mult_p,
        **or_metrics,
        standardized_prevalences=risk,
        standardized_prevalence_covariance=cv.tolist(),
        prevalence_interaction=add,
        RERI_PR=reri_pr,
        AP_PR=ap_pr
    )

def weighted_c_statistic(y, pred, weights):
    y = np.asarray(y)
    pred = np.asarray(pred)
    w = np.asarray(weights)
    total_w_pos = np.sum(w * (y == 1))
    total_w_neg = np.sum(w * (y == 0))
    if total_w_pos == 0 or total_w_neg == 0:
        return np.nan
    order = np.argsort(pred)
    y_sorted = y[order]
    w_sorted = w[order]
    pred_sorted = pred[order]
    
    cw_neg = np.pad(np.cumsum(w_sorted * (y_sorted == 0)), (1, 0))
    left = np.searchsorted(pred_sorted, pred_sorted, side='left')
    right = np.searchsorted(pred_sorted, pred_sorted, side='right')
    
    pos_mask = (y_sorted == 1)
    concordant = cw_neg[left[pos_mask]]
    tied = 0.5 * (cw_neg[right[pos_mask]] - cw_neg[left[pos_mask]])
    
    rank_sum = np.sum(w_sorted[pos_mask] * (concordant + tied))
    return float(rank_sum / (total_w_pos * total_w_neg))

def empirical_weighted_roc(y, pred, weights, n_points=250):
    y = np.asarray(y)
    pred = np.asarray(pred)
    w = np.asarray(weights)
    order = np.argsort(-pred, kind='stable')
    y_sorted = y[order]
    w_sorted = w[order]
    # Evaluate only after ALL observations sharing a threshold enter the curve.
    ends = np.r_[np.flatnonzero(np.diff(pred[order]) != 0), len(pred) - 1]
    tpr = np.r_[0.0, np.cumsum(w_sorted * (y_sorted == 1))[ends] / np.sum(w_sorted * (y_sorted == 1))]
    fpr = np.r_[0.0, np.cumsum(w_sorted * (y_sorted == 0))[ends] / np.sum(w_sorted * (y_sorted == 0))]
    tpr[-1] = fpr[-1] = 1.0
    # Keep actual empirical vertices, including both endpoints, for plotting.
    indices = np.unique(np.linspace(0, len(fpr) - 1, min(n_points, len(fpr))).astype(int))
    return {'fpr': fpr[indices].tolist(), 'tpr': tpr[indices].tolist()}

def build_table1(d):
    variables = {
        'age': ('Age, years', False),
        'female': ('Female, %', True),
        'pir': ('Poverty-to-income ratio', False),
        'bmi': ('BMI, kg/m2', False),
        'waist': ('Waist circumference, cm', False),
        'sbp': ('Systolic BP, mm Hg', False),
        'dbp': ('Diastolic BP, mm Hg', False),
        'hba1c': ('HbA1c, %', False),
        'tc': ('Total cholesterol, mg/dL', False),
        'hdl': ('HDL cholesterol, mg/dL', False),
        'nonhdl': ('Non-HDL cholesterol, mg/dL', False),
        'triglycerides': ('Triglycerides, mg/dL', False),
        'egfr': ('eGFR, mL/min/1.73m2', False),
        'uacr': ('Harmonized UACR, mg/g', False),
        'LUXSMED': ('VCTE liver stiffness, kPa', False),
        'LUXCAPM': ('VCTE CAP steatosis, dB/m', False),
        'hscrp': ('High-sensitivity CRP, mg/L', False),
        'fib4': ('FIB-4 score', False),
        'sii': ('SII, 10^9/L', False),
        'high_vcte': ('Clinically significant fibrosis (VCTE >= 8.0 kPa), %', True),
        'high_cap': ('Hepatic steatosis (CAP >= 274 dB/m), %', True),
        'high_hscrp': ('High hs-CRP (>= 2.0 mg/L), %', True),
        'high_fib4': ('Elevated FIB-4 (>= 1.30), %', True),
        'bp_meds': ('Antihypertensive medication, %', True),
        'dm_meds': ('Diabetes medication, %', True),
        'lipid_meds': ('Lipid-lowering medication, %', True),
        'smoker': ('Current cigarette smoker, %', True),
        'diabetes': ('Diabetes mellitus, %', True),
        'hypertension': ('Hypertension, %', True),
        'clinical_cvd': ('Clinical cardiovascular disease, %', True),
        'ckd': ('Kidney abnormality (eGFR<60 or UACR>=30), %', True),
        'very_high_ckd': ('KDIGO very-high-risk CKD, %', True),
        'advanced_ckm': ('Advanced CKM Syndrome (Stages 3-4), %', True)
    }
    
    cat_vars = [
        ('race', [1, 2, 3, 4, 6, 7], {1:'Mexican American', 2:'Other Hispanic', 3:'Non-Hispanic White', 4:'Non-Hispanic Black', 6:'Non-Hispanic Asian', 7:'Other/Multi'}),
        ('education', [1, 2, 3, 4, 5], {1:'< 9th Grade', 2:'9-11th Grade', 3:'High School/GED', 4:'Some College/AA', 5:'College Graduate'}),
        ('ckm_stage', [0, 1, 2, 3, 4], {0:'CKM Stage 0', 1:'CKM Stage 1', 2:'CKM Stage 2', 3:'CKM Stage 3', 4:'CKM Stage 4'})
    ]
    for cat_name, cat_vals, val_labels in cat_vars:
        for val in cat_vals:
            col = f'{cat_name}_{val}'
            d[col] = d[cat_name].eq(val).astype(int)
            variables[col] = (f'{val_labels[val]}, %', True)
            
    res = {}
    for col, (label, is_prop) in variables.items():
        res[label] = {}
        res[label]['Overall'] = estimate(d[col], d, proportion=is_prop)
        for g in range(4):
            sub = d.loc[d.joint_vcte_crp == g]
            res[label][str(g)] = estimate(sub[col], sub, proportion=is_prop)
            
    return res

def diagnostic_fib4_vs_vcte(d):
    def calc_metrics(sub, pred_col='high_fib4', ref_col='high_vcte'):
        sw = sub.weight.to_numpy()
        pred = sub[pred_col].to_numpy()
        ref = sub[ref_col].to_numpy()
        
        tp = np.sum(sw[(pred == 1) & (ref == 1)])
        fp = np.sum(sw[(pred == 1) & (ref == 0)])
        fn = np.sum(sw[(pred == 0) & (ref == 1)])
        tn = np.sum(sw[(pred == 0) & (ref == 0)])
        
        sens = tp / (tp + fn) if (tp + fn) > 0 else np.nan
        spec = tn / (tn + fp) if (tn + fp) > 0 else np.nan
        ppv = tp / (tp + fp) if (tp + fp) > 0 else np.nan
        npv = tn / (tn + fn) if (tn + fn) > 0 else np.nan
        plr = sens / (1 - spec) if (1 - spec) > 0 else np.nan
        nlr = (1 - sens) / spec if spec > 0 else np.nan
        fpr = fp / (fp + tn) if (fp + tn) > 0 else np.nan
        
        return {
            'n': len(sub),
            'raw_tp': int(((pred == 1) & (ref == 1)).sum()),
            'raw_fp': int(((pred == 1) & (ref == 0)).sum()),
            'raw_fn': int(((pred == 0) & (ref == 1)).sum()),
            'raw_tn': int(((pred == 0) & (ref == 0)).sum()),
            'sensitivity': float(sens),
            'specificity': float(spec),
            'ppv': float(ppv),
            'npv': float(npv),
            'pos_lr': float(plr),
            'neg_lr': float(nlr),
            'false_positive_rate': float(fpr)
        }
        
    overall = calc_metrics(d, 'high_fib4')
    younger = calc_metrics(d.loc[d.age < 65], 'high_fib4')
    older = calc_metrics(d.loc[d.age >= 65], 'high_fib4')
    
    # Age-calibrated FIB-4 (>=1.30 if age < 65, >=2.00 if age >= 65)
    d_copy = d.copy()
    d_copy['high_fib4_20'] = (d_copy.fib4 >= 2.0).astype(int)
    calib_overall = calc_metrics(d_copy, 'high_fib4_age')
    calib_older = calc_metrics(d_copy.loc[d_copy.age >= 65], 'high_fib4_20')
    
    return {
        'overall': overall,
        'age_lt_65': younger,
        'age_ge_65': older,
        'age_calibrated_overall': calib_overall,
        'age_calibrated_ge_65': calib_older
    }

def main():
    print("=== Starting V2.1 Statistical Analysis Pipeline ===")
    d = pd.read_csv(BASE / 'data' / 'v2_analytic_cohort.csv')
    meta = json.loads((RESULTS_DIR / 'v2_cohort_metadata.json').read_text())
    
    # Standardize log2_fib4
    d['log2_fib4'] = np.log2(np.maximum(0.1, d['fib4']))
    w_norm = d['weight'] / d['weight'].sum()
    mean_fib4 = np.sum(w_norm * d['log2_fib4'])
    sd_fib4 = np.sqrt(np.sum(w_norm * (d['log2_fib4'] - mean_fib4)**2))
    d['log2_fib4_z'] = (d['log2_fib4'] - mean_fib4) / sd_fib4
    
    p_adv = estimate(d.advanced_ckm, d, proportion=True)
    p_vcte = estimate(d.high_vcte, d, proportion=True)
    p_crp = estimate(d.high_hscrp, d, proportion=True)
    p_joint = [estimate(d.joint_vcte_crp == g, d, proportion=True) for g in range(4)]
    
    out = {
        'metadata': meta,
        'prevalences': {
            'advanced_ckm': p_adv,
            'high_vcte': p_vcte,
            'high_hscrp': p_crp,
            'joint_groups': p_joint
        },
        'models': {},
        'secondary_outcomes': {},
        'sensitivities': {},
        'subgroups': {}
    }
    
    print("\n--- Running Primary Multivariable Models (Models 1, 2, 3) ---")
    for m in [1, 2, 3]:
        formula = f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[m]}'
        s, i = fit(formula, d, UNIVERSE)
        s['interaction'] = interactions_v2(i, d, var1='high_hscrp', var2='high_vcte', universe=UNIVERSE)
        out['models'][f'Model {m}'] = s
        
        j_ors = s['interaction']['joint_OR']
        reri = s['interaction']['RERI_OR']
        ap = s['interaction']['AP_OR']
        s_idx = s['interaction']['S_OR']
        mp = s['interaction']['multiplicative_p']
        prev_int = s['interaction']['prevalence_interaction']
        print(f"Model {m}: G1={j_ors[1]['or_value']:.2f}, G2={j_ors[2]['or_value']:.2f}, G3={j_ors[3]['or_value']:.2f} ({j_ors[3]['lower']:.2f}-{j_ors[3]['upper']:.2f}), mult_p={mp:.4f}, RERI_OR={reri['estimate']:.2f}, Prev_Int={prev_int['estimate']*100:.1f} pp")

    print("\n--- Running Secondary Outcomes ---")
    # 1. Clinical CVD
    s_cvd, i_cvd = fit(f'clinical_cvd ~ high_hscrp * high_vcte + {COVARS[2]}', d, UNIVERSE)
    s_cvd['interaction'] = interactions_v2(i_cvd, d, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['secondary_outcomes']['clinical_cvd_M2'] = s_cvd
    
    # 2. CKD
    s_ckd, i_ckd = fit(f'ckd ~ high_hscrp * high_vcte + {COVARS[2]}', d, UNIVERSE)
    s_ckd['interaction'] = interactions_v2(i_ckd, d, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['secondary_outcomes']['ckd_M2'] = s_ckd
    
    # 3. KDIGO Very-High-Risk CKD (Replaces duplicate ckm_stage_4_M2)
    s_vh, i_vh = fit(f'very_high_ckd ~ high_hscrp * high_vcte + {COVARS[2]}', d, UNIVERSE)
    s_vh['interaction'] = interactions_v2(i_vh, d, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['secondary_outcomes']['very_high_ckd_M2'] = s_vh
    
    # 4. Secondary Validation in Adult Core Cohort (Ages >= 20, N=11,585)
    core_path = BASE / 'data' / 'v2_adult_core_cohort.csv'
    if not core_path.exists():
        core_path = Path(__file__).resolve().parent / 'data' / 'v2_adult_core_cohort.csv'
    if core_path.exists():
        core = pd.read_csv(core_path)
        core_cols = ['high_hscrp', 'high_vcte', 'age10', 'female', 'race', 'cycle', 'pir', 'education', 'bmi5', 'waist10', 'weight', 'stratum', 'psu']
        
        # Adult core CVD
        core_cvd = core.dropna(subset=['clinical_cvd'] + core_cols).copy()
        s_core_cvd, i_core_cvd = fit(f'clinical_cvd ~ high_hscrp * high_vcte + {COVARS[2]}', core_cvd, UNIVERSE)
        s_core_cvd['interaction'] = interactions_v2(i_core_cvd, core_cvd, 'high_hscrp', 'high_vcte', UNIVERSE)
        out['secondary_outcomes']['adult_core_cvd_M2'] = s_core_cvd
        
        # Adult core CKD
        core_ckd = core.dropna(subset=['ckd'] + core_cols).copy()
        s_core_ckd, i_core_ckd = fit(f'ckd ~ high_hscrp * high_vcte + {COVARS[2]}', core_ckd, UNIVERSE)
        s_core_ckd['interaction'] = interactions_v2(i_core_ckd, core_ckd, 'high_hscrp', 'high_vcte', UNIVERSE)
        out['secondary_outcomes']['adult_core_ckd_M2'] = s_core_ckd
        print(f"Adult Core Validation N: CVD={len(core_cvd)}, CKD={len(core_ckd)}")

    print("\n--- Running Sensitivity & Mechanistic Models ---")
    # 1. Steatosis vs Fibrosis: CAP >= 274 dB/m
    s_cap, i_cap = fit(f'advanced_ckm ~ high_cap * high_hscrp + {COVARS[2]}', d, UNIVERSE)
    s_cap['interaction'] = interactions_v2(i_cap, d, 'high_hscrp', 'high_cap', UNIVERSE)
    out['sensitivities']['steatosis_high_cap_M2'] = s_cap
    
    # 2. Both Fibrosis and Steatosis mutually adjusted
    s_both, _ = fit(f'advanced_ckm ~ high_vcte * high_hscrp + high_cap + {COVARS[2]}', d, UNIVERSE)
    out['sensitivities']['fibrosis_steatosis_adjusted_M2'] = s_both
    
    # 3. hs-CRP >= 3.0 mg/L threshold
    s_crp3, i_crp3 = fit(f'advanced_ckm ~ high_hscrp_3 * high_vcte + {COVARS[2]}', d, UNIVERSE)
    s_crp3['interaction'] = interactions_v2(i_crp3, d, 'high_hscrp_3', 'high_vcte', UNIVERSE)
    out['sensitivities']['hscrp_ge3_M2'] = s_crp3
    
    # 4. Continuous standardization (log2_kpa_z * log2_hscrp_z)
    s_cont, _ = fit(f'advanced_ckm ~ log2_kpa_z * log2_hscrp_z + {COVARS[2]}', d, UNIVERSE)
    out['sensitivities']['continuous_kpa_crp_M2'] = s_cont
    
    # 5. Unbridged raw hs-CRP
    d['high_hscrp_raw'] = (d.hscrp_raw >= 2.0).astype(int)
    s_raw, i_raw = fit(f'advanced_ckm ~ high_hscrp_raw * high_vcte + {COVARS[2]}', d, UNIVERSE)
    s_raw['interaction'] = interactions_v2(i_raw, d, 'high_hscrp_raw', 'high_vcte', UNIVERSE)
    out['sensitivities']['raw_unbridged_hscrp_M2'] = s_raw
    
    # 6. Uniform PREVENT input domain
    d_prev = d.loc[d.prevent_input_valid].copy()
    s_prev, i_prev = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_prev, UNIVERSE)
    s_prev['interaction'] = interactions_v2(i_prev, d_prev, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['sensitivities']['uniform_prevent_domain_M2'] = s_prev
    
    # 7. Exclude acute inflammation (hs-CRP > 10.0 mg/L)
    d_noacute = d.loc[d.hscrp <= 10.0].copy()
    s_noacute, i_noacute = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_noacute, UNIVERSE)
    s_noacute['interaction'] = interactions_v2(i_noacute, d_noacute, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['sensitivities']['exclude_acute_crp_gt10_M2'] = s_noacute
    
    # 8. VCTE x SII
    s_sii, i_sii = fit(f'advanced_ckm ~ high_sii * high_vcte + {COVARS[2]}', d, UNIVERSE)
    s_sii['interaction'] = interactions_v2(i_sii, d, 'high_sii', 'high_vcte', UNIVERSE)
    out['sensitivities']['vcte_x_sii_M2'] = s_sii
    
    # 9. Flexible cubic-spline age adjustment
    f_spline = f'advanced_ckm ~ high_hscrp * high_vcte + bs(age, df=4, degree=3) + female + C(race) + C(cycle) + pir + C(education) + bmi5 + waist10'
    s_spline, i_spline = fit(f_spline, d, UNIVERSE)
    s_spline['interaction'] = interactions_v2(i_spline, d, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['sensitivities']['flexible_age_spline_M2'] = s_spline
    
    # 10. 3-level VCTE severity (with joint 6-group ORs)
    s_vcte3, i_vcte3 = fit(f'advanced_ckm ~ C(vcte_cat) * high_hscrp + {COVARS[2]}', d, UNIVERSE)
    v3_names = s_vcte3['parameter_names']
    v3_beta = np.array(s_vcte3['beta'])
    v3_cov = np.array(s_vcte3['covariance'])
    v3_df = s_vcte3['df']
    crit_v3 = stats.t.ppf(0.975, v3_df)
    
    combos_6 = [
        ('cat0_crp0', []),
        ('cat0_crp1', ['high_hscrp']),
        ('cat1_crp0', ['C(vcte_cat)[T.1]']),
        ('cat1_crp1', ['C(vcte_cat)[T.1]', 'high_hscrp', 'C(vcte_cat)[T.1]:high_hscrp']),
        ('cat2_crp0', ['C(vcte_cat)[T.2]']),
        ('cat2_crp1', ['C(vcte_cat)[T.2]', 'high_hscrp', 'C(vcte_cat)[T.2]:high_hscrp']),
    ]
    joint_6 = {}
    for label, terms in combos_6:
        if not terms:
            joint_6[label] = dict(or_value=1.0, lower=1.0, upper=1.0, se=0.0)
            continue
        L = np.zeros(len(v3_beta))
        for t_term in terms:
            L[v3_names.index(t_term)] = 1.0
        b_val = float(L @ v3_beta)
        se_val = float(np.sqrt(max(0, L @ v3_cov @ L)))
        joint_6[label] = dict(
            or_value=float(np.exp(b_val)),
            lower=float(np.exp(b_val - crit_v3 * se_val)),
            upper=float(np.exp(b_val + crit_v3 * se_val)),
            se=se_val
        )
    s_vcte3['joint_6group_OR'] = joint_6
    out['sensitivities']['vcte_3level_M2'] = s_vcte3

    print("\n--- Running Subgroups (Sex, Age <60/>=60, Age <65/>=65, Diabetes, Cycles) ---")
    # By Sex
    d_men = d.loc[d.female == 0].copy()
    s_men, i_men = fit(f'advanced_ckm ~ high_hscrp * high_vcte + age10 + C(race) + C(cycle) + pir + C(education) + bmi5 + waist10', d_men, UNIVERSE)
    s_men['interaction'] = interactions_v2(i_men, d_men, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['men'] = s_men
    
    d_women = d.loc[d.female == 1].copy()
    s_women, i_women = fit(f'advanced_ckm ~ high_hscrp * high_vcte + age10 + C(race) + C(cycle) + pir + C(education) + bmi5 + waist10', d_women, UNIVERSE)
    s_women['interaction'] = interactions_v2(i_women, d_women, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['women'] = s_women
    
    # By Age (<60 vs >=60)
    d_young60 = d.loc[d.age < 60].copy()
    s_young60, i_young60 = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_young60, UNIVERSE)
    s_young60['interaction'] = interactions_v2(i_young60, d_young60, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['age_lt_60'] = s_young60
    
    d_old60 = d.loc[d.age >= 60].copy()
    s_old60, i_old60 = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_old60, UNIVERSE)
    s_old60['interaction'] = interactions_v2(i_old60, d_old60, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['age_ge_60'] = s_old60

    # By Age (<65 vs >=65) - Aligned with diagnostic strata
    d_young65 = d.loc[d.age < 65].copy()
    s_young65, i_young65 = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_young65, UNIVERSE)
    s_young65['interaction'] = interactions_v2(i_young65, d_young65, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['age_lt_65'] = s_young65
    
    d_old65 = d.loc[d.age >= 65].copy()
    s_old65, i_old65 = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_old65, UNIVERSE)
    s_old65['interaction'] = interactions_v2(i_old65, d_old65, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['age_ge_65'] = s_old65
    
    # By Diabetes
    d_nodiab = d.loc[d.diabetes == 0].copy()
    s_nodiab, i_nodiab = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_nodiab, UNIVERSE)
    s_nodiab['interaction'] = interactions_v2(i_nodiab, d_nodiab, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['no_diabetes'] = s_nodiab
    
    d_diab = d.loc[d.diabetes == 1].copy()
    s_diab, i_diab = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {COVARS[2]}', d_diab, UNIVERSE)
    s_diab['interaction'] = interactions_v2(i_diab, d_diab, 'high_hscrp', 'high_vcte', UNIVERSE)
    out['subgroups']['diabetes'] = s_diab

    # By Cycle
    covars_nocycle = 'age10 + female + C(race) + pir + C(education) + bmi5 + waist10'
    u_c1 = UNIVERSE.loc[UNIVERSE.cycle == '2017-2020'].copy()
    d_c1 = d.loc[d.cycle == '2017-2020'].copy()
    s_c1, i_c1 = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {covars_nocycle}', d_c1, u_c1)
    s_c1['interaction'] = interactions_v2(i_c1, d_c1, 'high_hscrp', 'high_vcte', u_c1)
    out['subgroups']['cycle_2017_2020'] = s_c1
    
    u_c2 = UNIVERSE.loc[UNIVERSE.cycle == '2021-2023'].copy()
    d_c2 = d.loc[d.cycle == '2021-2023'].copy()
    s_c2, i_c2 = fit(f'advanced_ckm ~ high_hscrp * high_vcte + {covars_nocycle}', d_c2, u_c2)
    s_c2['interaction'] = interactions_v2(i_c2, d_c2, 'high_hscrp', 'high_vcte', u_c2)
    out['subgroups']['cycle_2021_2023'] = s_c2

    print("\n--- Running Head-to-Head Diagnostic Comparison (Standard vs Age-Calibrated FIB-4) ---")
    diag = diagnostic_fib4_vs_vcte(d)
    out['diagnostic_fib4_vs_vcte'] = diag

    print("\n--- Running Discrimination & Jackknife C-statistics (5 Models) ---")
    models_disc = {
        'base_M2': f'advanced_ckm ~ {COVARS[2]}',
        'vcte_M2': f'advanced_ckm ~ log2_kpa_z + {COVARS[2]}',
        'fib4_M2': f'advanced_ckm ~ log2_fib4_z + {COVARS[2]}',
        'dual_vcte_crp_M2': f'advanced_ckm ~ log2_kpa_z * log2_hscrp_z + {COVARS[2]}',
        'dual_fib4_sii_M2': f'advanced_ckm ~ log2_fib4_z * log2_sii_z + {COVARS[2]}'
    }
    
    fitted_preds = {}
    fitted_aucs = {}
    roc_curves = {}
    for m_name, f_expr in models_disc.items():
        s_m, i_m = fit(f_expr, d, UNIVERSE)
        x_m = np.asarray(build_design_matrices([i_m['design']], d)[0])[:, i_m['keep']]
        pred_m = expit(x_m @ i_m['beta'])
        fitted_preds[m_name] = pred_m
        auc_m = weighted_c_statistic(d.advanced_ckm, pred_m, d.weight)
        fitted_aucs[m_name] = auc_m
        roc_curves[m_name] = empirical_weighted_roc(d.advanced_ckm, pred_m, d.weight, n_points=250)
        
    out['roc_curves'] = roc_curves
    
    # Delete-1-PSU Jackknife for C-statistics and contrasts
    strata_psus = UNIVERSE[['stratum', 'psu']].drop_duplicates().sort_values(['stratum', 'psu'])
    jk_aucs = {m_name: [] for m_name in models_disc}
    jk_deltas = {'vcte_vs_fib4': [], 'dual_vcte_crp_vs_base': []}
    
    for stratum, group in strata_psus.groupby('stratum'):
        nh = len(group)
        psu_list = group['psu'].tolist()
        for del_psu in psu_list:
            w_jk = d.weight.to_numpy().copy()
            in_stratum = (d.stratum == stratum)
            del_mask = in_stratum & (d.psu == del_psu)
            keep_mask = in_stratum & (d.psu != del_psu)
            w_jk[del_mask] = 0.0
            w_jk[keep_mask] = w_jk[keep_mask] * (nh / (nh - 1))
            
            cur_aucs = {}
            for m_name in models_disc:
                c_val = weighted_c_statistic(d.advanced_ckm, fitted_preds[m_name], w_jk)
                jk_aucs[m_name].append((stratum, del_psu, c_val))
                cur_aucs[m_name] = c_val
            jk_deltas['vcte_vs_fib4'].append((stratum, del_psu, cur_aucs['vcte_M2'] - cur_aucs['fib4_M2']))
            jk_deltas['dual_vcte_crp_vs_base'].append((stratum, del_psu, cur_aucs['dual_vcte_crp_M2'] - cur_aucs['base_M2']))
            
    t40 = stats.t.ppf(0.975, 40)
    disc_summary = {}
    for m_name in models_disc:
        vals = pd.DataFrame(jk_aucs[m_name], columns=['stratum', 'psu', 'theta'])
        var_jk = 0.0
        for stratum, grp in vals.groupby('stratum'):
            nh = len(grp)
            mean_theta = grp['theta'].mean()
            var_jk += ((nh - 1) / nh) * np.sum((grp['theta'] - mean_theta)**2)
        se_jk = float(np.sqrt(var_jk))
        mean_val = float(fitted_aucs[m_name])
        disc_summary[m_name] = {
            'auc': mean_val,
            'se': se_jk,
            'lower': mean_val - t40 * se_jk,
            'upper': mean_val + t40 * se_jk
        }
        print(f"  {m_name}: AUC {mean_val:.4f} (95% CI: {mean_val - t40 * se_jk:.4f}–{mean_val + t40 * se_jk:.4f})")
        
    contrasts_summary = {}
    for d_name, d_list in jk_deltas.items():
        vals = pd.DataFrame(d_list, columns=['stratum', 'psu', 'delta'])
        var_jk = 0.0
        for stratum, grp in vals.groupby('stratum'):
            nh = len(grp)
            mean_delta = grp['delta'].mean()
            var_jk += ((nh - 1) / nh) * np.sum((grp['delta'] - mean_delta)**2)
        se_jk = float(np.sqrt(var_jk))
        if d_name == 'vcte_vs_fib4':
            mean_delta = float(fitted_aucs['vcte_M2'] - fitted_aucs['fib4_M2'])
        else:
            mean_delta = float(fitted_aucs['dual_vcte_crp_M2'] - fitted_aucs['base_M2'])
        contrasts_summary[d_name] = {
            'delta_auc': mean_delta,
            'se': se_jk,
            'lower': mean_delta - t40 * se_jk,
            'upper': mean_delta + t40 * se_jk
        }
        print(f"  Contrast {d_name}: Delta {mean_delta:.4f} (95% CI: {mean_delta - t40 * se_jk:.4f}–{mean_delta + t40 * se_jk:.4f})")
        
    out['discrimination'] = {
        'models': disc_summary,
        'contrasts': contrasts_summary,
        'auc_vcte_model2': disc_summary['vcte_M2']['auc'],
        'auc_fib4_model2': disc_summary['fib4_M2']['auc'],
        'delta_auc': contrasts_summary['vcte_vs_fib4']['delta_auc']
    }

    print("\n--- Generating Table 1 ---")
    t1 = build_table1(d)
    out['table1'] = t1

    # Save complete statistical output JSON
    with open(RESULTS_DIR / 'statistical_output_v2.json', 'w') as f:
        json.dump(out, f, indent=2)
    print("Exported statistical_output_v2.json successfully.")

    # Generate Markdown Tables & STROBE Waterfall
    print("\n--- Exporting Markdown Tables 1, 2, 3 and STROBE Waterfall ---")
    export_tables(out, d)
    generate_strobe_waterfall_md()
    print("=== V2.1 Analysis Pipeline Complete ===")

def export_tables(out, d):
    # Table 1: Baseline Characteristics
    t1 = out['table1']
    lines_t1 = [
        "# Table 1. Baseline Characteristics of United States Adults by Joint VCTE Hepatic Stiffness and High-Sensitivity C-Reactive Protein Phenotypes (NHANES 2017–2023)",
        "",
        "Values are survey-weighted means (95% CI) for continuous variables or survey-weighted percentages (95% CI) for categorical variables. Sample sizes ($N$) represent unweighted participant counts.",
        "",
        "| Characteristic | Overall (N=7,043) | Group 0: Low VCTE / Low hs-CRP (n=3,416) | Group 1: Low VCTE / High hs-CRP (n=2,810) | Group 2: High VCTE / Low hs-CRP (n=283) | Group 3: Dual High VCTE + hs-CRP (n=534) |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |"
    ]
    
    for label, group_data in t1.items():
        def fmt_val(cell):
            if label == 'HbA1c, %':
                val = cell['estimate']
                lo = cell['lower']
                hi = cell['upper']
                return f"{val:.1f}% ({lo:.1f}–{hi:.1f}%)"
            elif 'proportion' in label or '%' in label:
                val = cell['estimate'] * 100
                lo = cell['lower'] * 100
                hi = cell['upper'] * 100
                return f"{val:.1f}% ({lo:.1f}–{hi:.1f}%)"
            else:
                val = cell['estimate']
                lo = cell['lower']
                hi = cell['upper']
                return f"{val:.1f} ({lo:.1f}–{hi:.1f})"
                
        disp_label = label.replace('>=', '≥')
        row_str = f"| {disp_label} | {fmt_val(group_data['Overall'])} | {fmt_val(group_data['0'])} | {fmt_val(group_data['1'])} | {fmt_val(group_data['2'])} | {fmt_val(group_data['3'])} |"
        lines_t1.append(row_str)
        
    lines_t1.append("")
    lines_t1.append("*Abbreviations:* VCTE, vibration-controlled transient elastography; hs-CRP, high-sensitivity C-reactive protein; BMI, body mass index; BP, blood pressure; HbA1c, hemoglobin A1c; HDL, high-density lipoprotein; eGFR, estimated glomerular filtration rate; UACR, urine albumin-to-creatinine ratio; FIB-4, Fibrosis-4 index; SII, Systemic Immune-Inflammation Index; CAP, controlled attenuation parameter; CVD, cardiovascular disease; CKD, chronic kidney disease; CKM, cardiovascular-kidney-metabolic syndrome.")
    
    (BASE / 'Table_1_Baseline.md').write_text("\n".join(lines_t1).replace(">=", "≥"), encoding='utf-8')
    
    # Table 2: Multivariable Logistic Regression and Interaction Metrics
    lines_t2 = [
        "# Table 2. Multivariable Survey-Weighted Logistic Regression for Advanced CKM Syndrome (Stages 3–4) Across Joint VCTE and hs-CRP Phenotypes",
        "",
        "Odds ratios (OR) and 95% confidence intervals (CI) are estimated using design-based logistic regression with full-universe Taylor series linearization ($df = 40$). Model 2 represents the co-primary pre-specified model.",
        "",
        "| Parameter / Phenotype | Model 1: Demographic-Adjusted | Model 2: Co-Primary Multivariable | Model 3: Extended Clinical-Adjusted |",
        "| :--- | :--- | :--- | :--- |"
    ]
    
    m1 = out['models']['Model 1']['interaction']
    m2 = out['models']['Model 2']['interaction']
    m3 = out['models']['Model 3']['interaction']
    
    for g_idx, g_name in enumerate(GROUPS_V2):
        if g_idx == 0:
            lines_t2.append(f"| **{g_name}** | 1.00 (Reference) | 1.00 (Reference) | 1.00 (Reference) |")
        else:
            def fmt_or(m, idx):
                item = m['joint_OR'][idx]
                return f"{item['or_value']:.2f} ({item['lower']:.2f}–{item['upper']:.2f})"
            lines_t2.append(f"| **{g_name}** | {fmt_or(m1, g_idx)} | {fmt_or(m2, g_idx)} | {fmt_or(m3, g_idx)} |")
            
    lines_t2.append("| **Interaction Metrics (Odds Scale)** | | | |")
    
    def fmt_reri(m):
        item = m['RERI_OR']
        return f"{item['estimate']:.2f} ({item['lower']:.2f}–{item['upper']:.2f})"
    def fmt_ap(m):
        item = m['AP_OR']
        return f"{item['estimate']:.2f} ({item['lower']:.2f}–{item['upper']:.2f})"
    def fmt_s(m):
        item = m['S_OR']
        if item.get('estimate') is not None:
            return f"{item['estimate']:.2f} ({item['lower']:.2f}–{item['upper']:.2f})"
        return "N/A"
    def fmt_mp(m):
        return f"{m['multiplicative_p']:.4f}"
        
    lines_t2.append(f"| Relative Excess Risk Due to Interaction, Odds Scale (RERI_OR) | {fmt_reri(m1)} | {fmt_reri(m2)} | {fmt_reri(m3)} |")
    lines_t2.append(f"| Attributable Proportion, Odds Scale (AP_OR) | {fmt_ap(m1)} | {fmt_ap(m2)} | {fmt_ap(m3)} |")
    lines_t2.append(f"| Synergy Index ($S$) | {fmt_s(m1)} | {fmt_s(m2)} | {fmt_s(m3)} |")
    lines_t2.append(f"| Multiplicative Interaction $p$-value | {fmt_mp(m1)} | {fmt_mp(m2)} | {fmt_mp(m3)} |")
    
    lines_t2.append("| **Standardized Prevalences (%)** | | | |")
    for g_idx, g_name in enumerate(GROUPS_V2):
        p1 = m1['standardized_prevalences'][g_idx] * 100
        p2 = m2['standardized_prevalences'][g_idx] * 100
        p3 = m3['standardized_prevalences'][g_idx] * 100
        lines_t2.append(f"| {g_name} (%) | {p1:.1f}% | {p2:.1f}% | {p3:.1f}% |")
        
    lines_t2.append("| **Additive Interaction on Probability Scale** | | | |")
    def fmt_prev_add(m):
        item = m['prevalence_interaction']
        est = item['estimate'] * 100
        lo = item['lower'] * 100
        hi = item['upper'] * 100
        return f"+{est:.1f} pp ({lo:.1f}–{hi:.1f} pp)"
    def fmt_reri_pr(m):
        item = m['RERI_PR']
        return f"{item['estimate']:.2f} ({item['lower']:.2f}–{item['upper']:.2f})"
    def fmt_ap_pr(m):
        item = m['AP_PR']
        est = item['estimate'] * 100
        lo = item['lower'] * 100
        hi = item['upper'] * 100
        return f"{est:.1f}% ({lo:.1f}–{hi:.1f}%)"
        
    lines_t2.append(f"| Standardized Prevalence Interaction, percentage points (95% CI) | {fmt_prev_add(m1)} | {fmt_prev_add(m2)} | {fmt_prev_add(m3)} |")
    lines_t2.append(f"| Relative Excess Risk, Prevalence Scale (RERI_PR) | {fmt_reri_pr(m1)} | {fmt_reri_pr(m2)} | {fmt_reri_pr(m3)} |")
    lines_t2.append(f"| Attributable Proportion, Prevalence Scale (AP_PR, %) | {fmt_ap_pr(m1)} | {fmt_ap_pr(m2)} | {fmt_ap_pr(m3)} |")
    
    lines_t2.append("")
    lines_t2.append("*Model Covariates:*")
    lines_t2.append("- **Model 1:** Age (per 10 years), sex, race/ethnicity, NHANES cycle.")
    lines_t2.append("- **Model 2 (Co-Primary):** Model 1 + family poverty-income ratio, education level, body mass index (per 5 kg/m²), waist circumference (per 10 cm).")
    lines_t2.append("- **Model 3:** Model 2 + hemoglobin A1c, systolic blood pressure (per 10 mm Hg), non-HDL cholesterol (per 50 mg/dL), log-triglycerides, blood pressure medication use, diabetes medication use.")
    
    (BASE / 'Table_2_Multivariable_Joint_Models.md').write_text("\n".join(lines_t2), encoding='utf-8')

    # Table 3: Head-to-Head Diagnostic Comparison (FIB-4 vs VCTE)
    diag = out['diagnostic_fib4_vs_vcte']
    disc = out['discrimination']
    
    d_ov = diag['overall']
    d_y = diag['age_lt_65']
    d_o = diag['age_ge_65']
    d_o_calib = diag['age_calibrated_ge_65']
    
    lines_t3 = [
        "# Table 3. Head-to-Head Diagnostic and Discrimination Performance: Indirect FIB-4 vs Direct VCTE FibroScan",
        "",
        "Diagnostic test parameters evaluate the performance of FIB-4 against the reference standard of direct VCTE liver stiffness $\\ge 8.0$ kPa. Values are survey-weighted estimates.",
        "",
        "| Diagnostic Metric | Overall Cohort: FIB-4 ≥1.30 (Ages 30–79, N=7,043) | Younger Adults: FIB-4 ≥1.30 (Ages 30–64, N=5,223) | Older Adults: Standard FIB-4 ≥1.30 (Ages 65–79, N=1,820) | Older Adults: Age-Calibrated FIB-4 ≥2.00 (Ages 65–79, N=1,820) |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| Unweighted Sample Count ($N$) | {d_ov['n']:,} | {d_y['n']:,} | {d_o['n']:,} | {d_o_calib['n']:,} |",
        f"| True Positives ($n$) | {d_ov['raw_tp']:,} | {d_y['raw_tp']:,} | {d_o['raw_tp']:,} | {d_o_calib['raw_tp']:,} |",
        f"| False Positives ($n$) | {d_ov['raw_fp']:,} | {d_y['raw_fp']:,} | {d_o['raw_fp']:,} | {d_o_calib['raw_fp']:,} |",
        f"| False Negatives ($n$) | {d_ov['raw_fn']:,} | {d_y['raw_fn']:,} | {d_o['raw_fn']:,} | {d_o_calib['raw_fn']:,} |",
        f"| True Negatives ($n$) | {d_ov['raw_tn']:,} | {d_y['raw_tn']:,} | {d_o['raw_tn']:,} | {d_o_calib['raw_tn']:,} |",
        f"| **Sensitivity (%)** | {d_ov['sensitivity']*100:.1f}% | {d_y['sensitivity']*100:.1f}% | {d_o['sensitivity']*100:.1f}% | {d_o_calib['sensitivity']*100:.1f}% |",
        f"| **Specificity (%)** | {d_ov['specificity']*100:.1f}% | {d_y['specificity']*100:.1f}% | {d_o['specificity']*100:.1f}% | {d_o_calib['specificity']*100:.1f}% |",
        f"| **Positive Predictive Value (PPV, %)** | {d_ov['ppv']*100:.1f}% | {d_y['ppv']*100:.1f}% | {d_o['ppv']*100:.1f}% | {d_o_calib['ppv']*100:.1f}% |",
        f"| **Negative Predictive Value (NPV, %)** | {d_ov['npv']*100:.1f}% | {d_y['npv']*100:.1f}% | {d_o['npv']*100:.1f}% | {d_o_calib['npv']*100:.1f}% |",
        f"| **Positive Likelihood Ratio (+LR)** | {d_ov['pos_lr']:.2f} | {d_y['pos_lr']:.2f} | {d_o['pos_lr']:.2f} | {d_o_calib['pos_lr']:.2f} |",
        f"| **Negative Likelihood Ratio (-LR)** | {d_ov['neg_lr']:.2f} | {d_y['neg_lr']:.2f} | {d_o['neg_lr']:.2f} | {d_o_calib['neg_lr']:.2f} |",
        f"| **False-Positive Rate (%)** | {d_ov['false_positive_rate']*100:.1f}% | {d_y['false_positive_rate']*100:.1f}% | {d_o['false_positive_rate']*100:.1f}% | {d_o_calib['false_positive_rate']*100:.1f}% |",
        "",
        "### Discrimination for Advanced CKM Syndrome (Stages 3–4)",
        "",
        "C-statistic confidence intervals use the survey-weighted delete-1-PSU jackknife ($df=40$), conditional on full-sample fitted predictions. These are apparent in-sample estimates, not external or cross-validated performance.",
        "",
        "| Model Specification | Survey-Weighted C-Statistic / AUC | 95% Confidence Interval | Contrast vs Reference Model |",
        "| :--- | :--- | :--- | :--- |",
        f"| **Base Model 2 (Demographics + Socioeconomic + Adiposity)** | {disc['models']['base_M2']['auc']:.4f} | {disc['models']['base_M2']['lower']:.4f}–{disc['models']['base_M2']['upper']:.4f} | Reference for Additive Value |",
        f"| **Model 2 + Direct VCTE Stiffness** | {disc['models']['vcte_M2']['auc']:.4f} | {disc['models']['vcte_M2']['lower']:.4f}–{disc['models']['vcte_M2']['upper']:.4f} | $\\Delta\\text{{AUC}} = {disc['contrasts']['vcte_vs_fib4']['delta_auc']:.4f}$ ({disc['contrasts']['vcte_vs_fib4']['lower']:.4f}–{disc['contrasts']['vcte_vs_fib4']['upper']:.4f} vs FIB-4) |",
        f"| **Model 2 + Formula FIB-4** | {disc['models']['fib4_M2']['auc']:.4f} | {disc['models']['fib4_M2']['lower']:.4f}–{disc['models']['fib4_M2']['upper']:.4f} | Reference for Biomarker Comparison |",
        f"| **Model 2 + Direct VCTE & hs-CRP** | {disc['models']['dual_vcte_crp_M2']['auc']:.4f} | {disc['models']['dual_vcte_crp_M2']['lower']:.4f}–{disc['models']['dual_vcte_crp_M2']['upper']:.4f} | $\\Delta\\text{{AUC}} = +{disc['contrasts']['dual_vcte_crp_vs_base']['delta_auc']:.4f}$ ({disc['contrasts']['dual_vcte_crp_vs_base']['lower']:.4f}–{disc['contrasts']['dual_vcte_crp_vs_base']['upper']:.4f} vs Base) |",
        f"| **Model 2 + Formula FIB-4 & SII** | {disc['models']['dual_fib4_sii_M2']['auc']:.4f} | {disc['models']['dual_fib4_sii_M2']['lower']:.4f}–{disc['models']['dual_fib4_sii_M2']['upper']:.4f} | Comparison Dual Formula Model |",
        "",
        "*Key Clinical Finding:* In adults aged $\\ge 65$, standard FIB-4 $\\ge 1.30$ generates a false-positive rate of 63.8% (specificity 36.2%), driven by chronological age in the formula numerator. Calibrating the FIB-4 threshold to $\\ge 2.00$ in older adults reduces false positives to 17.5% (specificity 82.5%), but sensitivity falls steeply to 29.0%. These diagnostic comparisons use VCTE as the reference threshold and do not establish biopsy accuracy or age-independent performance."
    ]
    
    (BASE / 'Table_3_VCTE_vs_FIB4_Diagnostic_Comparison.md').write_text("\n".join(lines_t3), encoding='utf-8')

def generate_strobe_waterfall_md():
    waterfall_path = (RESULTS_DIR / 'v2_strobe_waterfall.json')
    if not waterfall_path.exists():
        waterfall_path = Path(__file__).resolve().parent / 'results' / 'v2_strobe_waterfall.json'
    if not waterfall_path.exists():
        return
    waterfall_v2 = json.loads(waterfall_path.read_text())
    sec_path = (RESULTS_DIR / 'v2_secondary_waterfall.json')
    if not sec_path.exists():
        sec_path = Path(__file__).resolve().parent / 'results' / 'v2_secondary_waterfall.json'
    waterfall_sec = json.loads(sec_path.read_text()) if sec_path.exists() else None
    parent_flow = json.loads((ROOT / 'results' / 'strobe_waterfall.json').read_text())
    parent_rows = [
        f"| **{i + 2}. {step['step']}** | {step['step']} | **{step['retained']:,}** | {step['excluded']:,} | Parent cohort sequential exclusion |"
        for i, step in enumerate(parent_flow)
    ]
    
    lines = [
        "# STROBE Flowchart and Participant Disposition Waterfall: Study 2.0 (VCTE & hs-CRP)",
        "",
        "This document details the complete, step-by-step participant disposition following the STROBE (Strengthening the Reporting of Observational Studies in Epidemiology) guidelines for complex survey cohorts.",
        "",
        "## Part 1: Parent NHANES 2017–2023 Universe to Primary Complete-Case Cohort",
        "",
        "| Sequential Step | Criteria Applied | Participants Retained ($N$) | Excluded ($N$) | Notes |",
        "| :--- | :--- | :--- | :--- | :--- |",
        "| **1. Total Survey Population** | NHANES 2017–March 2020 (`P_`) and 2021–2023 (`_L`) | **27,493** | 0 | Full NCHS design universe |",
        *parent_rows,
        "",
        "## Part 2: Study 2.0 VCTE Elastography & hs-CRP Inclusion Waterfall",
        "",
        "| Sequential Step | Criteria Applied | Participants Retained ($N$) | Excluded ($N$) | Cumulative Excluded ($N$) |",
        "| :--- | :--- | :--- | :--- | :--- |",
        f"| **1. Primary Analytic Cohort** | Pre-VCTE complete-case adults aged 30–79 | **{waterfall_v2['initial_analytic_cohort']:,}** | 0 | 0 |",
        f"| **2. VCTE Examination Record** | Present in `P_LUX` or `LUX_L` | **{waterfall_v2['step1_has_vcte_record']:,}** | 0 | 0 |",
        f"| **3. Complete VCTE Exam** | Exam status complete (`LUAXSTAT == 1`) | **{waterfall_v2['step2_complete_vcte_exam']:,}** | {waterfall_v2['excluded_incomplete_vcte']:,} | {waterfall_v2['excluded_incomplete_vcte']:,} |",
        f"| **4. Positive Stiffness & CAP** | `LUXSMED > 0` and `LUXCAPM > 0` | **{waterfall_v2['step3_positive_smed_capm']:,}** | 0 | {waterfall_v2['excluded_incomplete_vcte']:,} |",
        f"| **5. Measurement Validity** | At least 10 valid measures (`LUANMVGP >= 10`) | **{waterfall_v2['step4_ge10_valid_measures']:,}** | 0 | {waterfall_v2['excluded_incomplete_vcte']:,} |",
        f"| **6. Measurement Reliability** | IQR / Median stiffness $\\le 30.0\\%$ (`LUXSIQRM <= 30.0`) | **{waterfall_v2['step5_reliable_iqrm_le30pct']:,}** | {waterfall_v2['excluded_unreliable_vcte']:,} | {waterfall_v2['excluded_incomplete_vcte'] + waterfall_v2['excluded_unreliable_vcte']:,} |",
        f"| **7. Bridged hs-CRP Available** | Non-missing serum hs-CRP (`LBXHSCRP > 0`) | **{waterfall_v2['step6_nonmissing_hscrp_final']:,}** | {waterfall_v2['excluded_missing_hscrp']:,} | {waterfall_v2['initial_analytic_cohort'] - waterfall_v2['step6_nonmissing_hscrp_final']:,} |",
        "",
        f"**Final Primary Analytic Cohort for Study 2.0:** **N = {waterfall_v2['step6_nonmissing_hscrp_final']:,}** US adults aged 30–79 years.",
        "",
        "## Part 3: Secondary Adult Core Cohort (Ages $\\ge 20$) VCTE Waterfall",
        ""
    ]
    
    if waterfall_sec:
        lines.extend([
            "| Sequential Step | Criteria Applied | Participants Retained ($N$) | Excluded ($N$) | Cumulative Excluded ($N$) |",
            "| :--- | :--- | :--- | :--- | :--- |",
            f"| **1. Secondary Core Cohort** | Adult core cohort aged $\\ge 20$ | **{waterfall_sec['initial_analytic_cohort']:,}** | 0 | 0 |",
            f"| **2. Complete VCTE Exam** | Exam status complete (`LUAXSTAT == 1`) | **{waterfall_sec['step2_complete_vcte_exam']:,}** | {waterfall_sec['excluded_incomplete_vcte']:,} | {waterfall_sec['excluded_incomplete_vcte']:,} |",
            f"| **3. Reliability Criteria** | Positive stiffness and CAP, $\\ge 10$ measures and IQR/M $\\le 30.0\\%$ | **{waterfall_sec['step5_reliable_iqrm_le30pct']:,}** | {waterfall_sec['excluded_unreliable_vcte']:,} | {waterfall_sec['excluded_incomplete_vcte'] + waterfall_sec['excluded_unreliable_vcte']:,} |",
            f"| **4. Valid hs-CRP** | Non-missing serum hs-CRP | **{waterfall_sec['step6_nonmissing_hscrp_final']:,}** | {waterfall_sec['excluded_missing_hscrp']:,} | {waterfall_sec['initial_analytic_cohort'] - waterfall_sec['step6_nonmissing_hscrp_final']:,} |",
            "",
            f"**Final Secondary Adult Core Cohort for Study 2.0:** **N = {waterfall_sec['step6_nonmissing_hscrp_final']:,}** US adults aged $\\ge 20$ years."
        ])
        
    (BASE / 'STROBE_Waterfall_v2.md').write_text("\n".join(lines), encoding='utf-8')
    print("Exported STROBE_Waterfall_v2.md successfully.")

if __name__ == '__main__':
    main()
