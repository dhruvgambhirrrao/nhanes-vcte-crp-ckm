"""Cohort engineering for Study 2.0: VCTE FibroScan + hs-CRP in NHANES 2017-2023.
Merges physical elastography (LUX) and high-sensitivity CRP (HSCRP) onto the
audited primary analytic cohort (ages 30-79) and secondary adult core cohort (ages >=20).
Applies strict clinical quality standards and CDC forward bridging equations.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DATA_DIR = ROOT / 'data'
RESULTS_DIR = BASE / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)
(BASE / 'data').mkdir(parents=True, exist_ok=True)

def load_lux():
    p = pd.read_sas(DATA_DIR / 'P_LUX.xpt')
    l = pd.read_sas(DATA_DIR / 'LUX_L.xpt')
    p['cycle'] = '2017-2020'
    l['cycle'] = '2021-2023'
    cols = ['SEQN', 'cycle', 'LUAXSTAT', 'LUXSMED', 'LUXCAPM', 'LUANMVGP', 'LUXSIQRM']
    lux = pd.concat([p[cols], l[cols]], ignore_index=True)
    lux['SEQN'] = lux['SEQN'].astype(int)
    return lux

def load_hscrp():
    p = pd.read_sas(DATA_DIR / 'P_HSCRP.xpt')
    l = pd.read_sas(DATA_DIR / 'HSCRP_L.xpt')
    p['cycle'] = '2017-2020'
    l['cycle'] = '2021-2023'
    cols = ['SEQN', 'cycle', 'LBXHSCRP']
    crp = pd.concat([p[cols], l[cols]], ignore_index=True)
    crp['SEQN'] = crp['SEQN'].astype(int)
    return crp

def process_cohort(cohort_path, is_primary=True):
    d = pd.read_csv(cohort_path)
    n_initial = len(d)
    
    lux = load_lux()
    crp = load_hscrp()
    
    m = d.merge(lux, on=['SEQN', 'cycle'], how='left')
    m = m.merge(crp, on=['SEQN', 'cycle'], how='left')
    
    # Sequential STROBE exclusions
    # 1. Has VCTE record
    step1_has_lux = m.LUAXSTAT.notna()
    # 2. Complete exam (LUAXSTAT == 1)
    step2_complete_exam = step1_has_lux & (m.LUAXSTAT == 1)
    # 3. Valid stiffness and CAP values
    step3_valid_values = step2_complete_exam & (m.LUXSMED > 0) & (m.LUXCAPM > 0)
    # 4. >= 10 valid measurements (LUANMVGP >= 10)
    step4_valid_measures = step3_valid_values & (m.LUANMVGP >= 10)
    # 5. IQR/M <= 30.0% (LUXSIQRM <= 30.0)
    step5_reliable_iqrm = step4_valid_measures & (m.LUXSIQRM <= 30.0)
    # 6. Non-missing hs-CRP
    step6_valid_crp = step5_reliable_iqrm & m.LBXHSCRP.notna() & (m.LBXHSCRP > 0)
    
    waterfall = {
        'initial_analytic_cohort': int(n_initial),
        'step1_has_vcte_record': int(step1_has_lux.sum()),
        'step2_complete_vcte_exam': int(step2_complete_exam.sum()),
        'step3_positive_smed_capm': int(step3_valid_values.sum()),
        'step4_ge10_valid_measures': int(step4_valid_measures.sum()),
        'step5_reliable_iqrm_le30pct': int(step5_reliable_iqrm.sum()),
        'step6_nonmissing_hscrp_final': int(step6_valid_crp.sum()),
        'excluded_incomplete_vcte': int(n_initial - step2_complete_exam.sum()),
        'excluded_unreliable_vcte': int(step2_complete_exam.sum() - step5_reliable_iqrm.sum()),
        'excluded_missing_hscrp': int(step5_reliable_iqrm.sum() - step6_valid_crp.sum())
    }
    
    final = m.loc[step6_valid_crp].copy()
    
    # hs-CRP Bridging: Cobas 6000 (2017-2020) to Cobas 8000 (2021-2023)
    # Equation: Cobas 8000 = -0.08653 + 0.9672 * Cobas 6000 (LOD = 0.08 mg/L)
    final['hscrp_raw'] = final['LBXHSCRP']
    final['hscrp'] = np.where(
        final['cycle'] == '2017-2020',
        np.maximum(0.08, -0.08653 + 0.9672 * final['LBXHSCRP']),
        final['LBXHSCRP']
    )
    
    # Physical Liver Exposures
    # Clinically significant fibrosis (>= F2): LUXSMED >= 8.0 kPa
    final['high_vcte'] = (final['LUXSMED'] >= 8.0).astype(int)
    final['vcte_cat'] = pd.cut(
        final['LUXSMED'],
        bins=[-np.inf, 8.0, 12.0, np.inf],
        labels=[0, 1, 2],
        right=False
    ).astype(int)
    
    final['log2_kpa'] = np.log2(final['LUXSMED'])
    # Weighted mean and SD for standardization
    w = final['weight'].to_numpy()
    w_norm = w / w.sum()
    mean_kpa = np.sum(w_norm * final['log2_kpa'])
    sd_kpa = np.sqrt(np.sum(w_norm * (final['log2_kpa'] - mean_kpa)**2))
    final['log2_kpa_z'] = (final['log2_kpa'] - mean_kpa) / sd_kpa
    
    # Hepatic Steatosis: CAP >= 274 dB/m (moderate steatosis >= S2)
    final['high_cap'] = (final['LUXCAPM'] >= 274.0).astype(int)
    final['high_cap_248'] = (final['LUXCAPM'] >= 248.0).astype(int) # S1
    final['high_cap_285'] = (final['LUXCAPM'] >= 285.0).astype(int) # S3
    mean_cap = np.sum(w_norm * final['LUXCAPM'])
    sd_cap = np.sqrt(np.sum(w_norm * (final['LUXCAPM'] - mean_cap)**2))
    final['cap_z'] = (final['LUXCAPM'] - mean_cap) / sd_cap
    
    # Orthogonal Systemic Inflammation (hs-CRP)
    final['high_hscrp'] = (final['hscrp'] >= 2.0).astype(int)
    final['high_hscrp_3'] = (final['hscrp'] >= 3.0).astype(int)
    
    # Weighted upper tertile cutoff
    sorted_idx = np.argsort(final['hscrp'].to_numpy())
    cum_w = np.cumsum(w_norm[sorted_idx])
    t3_cutoff = float(final['hscrp'].to_numpy()[sorted_idx[np.searchsorted(cum_w, 2/3)]])
    final['high_hscrp_t3'] = (final['hscrp'] >= t3_cutoff).astype(int)
    
    final['log2_hscrp'] = np.log2(final['hscrp'])
    mean_crp = np.sum(w_norm * final['log2_hscrp'])
    sd_crp = np.sqrt(np.sum(w_norm * (final['log2_hscrp'] - mean_crp)**2))
    final['log2_hscrp_z'] = (final['log2_hscrp'] - mean_crp) / sd_crp
    
    # 4 Joint Phenotypes (VCTE / hs-CRP)
    # 0: Low / Low
    # 1: Low VCTE / High hs-CRP
    # 2: High VCTE / Low hs-CRP
    # 3: High VCTE / High hs-CRP
    conditions = [
        (final['high_vcte'] == 0) & (final['high_hscrp'] == 0),
        (final['high_vcte'] == 0) & (final['high_hscrp'] == 1),
        (final['high_vcte'] == 1) & (final['high_hscrp'] == 0),
        (final['high_vcte'] == 1) & (final['high_hscrp'] == 1)
    ]
    final['joint_vcte_crp'] = np.select(conditions, [0, 1, 2, 3], default=-1)
    
    # Model Covariates
    final['age10'] = (final['age'] - 55) / 10.0
    final['sbp10'] = (final['sbp'] - 130) / 10.0
    final['bmi5'] = final['bmi'] / 5.0
    final['waist10'] = final['waist'] / 10.0
    final['nonhdl50'] = final['nonhdl'] / 50.0
    final['log_tg'] = np.log(final['triglycerides'])
    
    # Ensure FIB-4 and SII comparisons
    if 'fib4' in final.columns and 'high_fib4' not in final.columns:
        final['high_fib4'] = (final['fib4'] >= 1.30).astype(int)
        
    meta = {
        'n': len(final),
        'n_events_advanced_ckm': int(final['advanced_ckm'].sum()) if 'advanced_ckm' in final.columns else None,
        'mean_kpa_log2': float(mean_kpa),
        'sd_kpa_log2': float(sd_kpa),
        'mean_cap': float(mean_cap),
        'sd_cap': float(sd_cap),
        'mean_hscrp_log2': float(mean_crp),
        'sd_hscrp_log2': float(sd_crp),
        'hscrp_t3_cutoff': float(t3_cutoff),
        'vcte_prevalence_ge8': float(np.sum(w_norm * final['high_vcte'])),
        'hscrp_prevalence_ge2': float(np.sum(w_norm * final['high_hscrp'])),
        'joint_group_counts': {int(g): int((final['joint_vcte_crp'] == g).sum()) for g in range(4)}
    }
    
    return final, waterfall, meta

def main():
    print("=== Engineering V2 Primary Cohort (Ages 30-79) ===")
    primary_path = DATA_DIR / 'analytic_cohort.csv'
    final_primary, waterfall_primary, meta_primary = process_cohort(primary_path, is_primary=True)
    
    final_primary.to_csv(BASE / 'data' / 'v2_analytic_cohort.csv', index=False)
    with open(RESULTS_DIR / 'v2_strobe_waterfall.json', 'w') as f:
        json.dump(waterfall_primary, f, indent=2)
    with open(RESULTS_DIR / 'v2_cohort_metadata.json', 'w') as f:
        json.dump(meta_primary, f, indent=2)
        
    print(f"Primary Analytic N: {len(final_primary)}")
    print("Primary Waterfall:", json.dumps(waterfall_primary, indent=2))
    print("Primary Meta:", json.dumps(meta_primary, indent=2))
    
    print("\n=== Engineering V2 Secondary Cohort (Ages >=20) ===")
    secondary_path = ROOT / 'results' / 'adult_core_cohort.csv'
    if secondary_path.exists():
        final_secondary, waterfall_secondary, meta_secondary = process_cohort(secondary_path, is_primary=False)
        final_secondary.to_csv(BASE / 'data' / 'v2_adult_core_cohort.csv', index=False)
        with open(RESULTS_DIR / 'v2_secondary_waterfall.json', 'w') as f:
            json.dump(waterfall_secondary, f, indent=2)
        print(f"Secondary Core N: {len(final_secondary)}")

if __name__ == '__main__':
    main()
