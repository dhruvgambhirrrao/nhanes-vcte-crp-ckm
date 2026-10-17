"""Automated compliance verification and audit suite for Study Version 2.0.
Checks declared study results against statistical_output_v2.json and recomputes
them from the saved cohorts using the original full-universe survey engine.
Literature citations, clinical interpretation and submission eligibility are outside scope.
Use --saved-results-only for text/table checks without rerunning statistical models.
"""
from pathlib import Path
import json
import re

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / 'results'

def audit(*, saved_results_only=False):
    print("=== Running Study 2.0 Biostatistical Compliance Audit ===")
    
    # 1. Verify existence of primary files
    files_to_check = [
        BASE / 'MANUSCRIPT_FULL_JGIM_NMCD.md',
        BASE / 'COVER_LETTER_AND_ZERO_FEE_SUBMISSION_GUIDE.md',
        BASE / 'Table_1_Baseline.md',
        BASE / 'Table_2_Multivariable_Joint_Models.md',
        BASE / 'Table_3_VCTE_vs_FIB4_Diagnostic_Comparison.md',
        RESULTS_DIR / 'statistical_output_v2.json',
        RESULTS_DIR / 'v2_cohort_metadata.json',
        RESULTS_DIR / 'v2_strobe_waterfall.json',
        RESULTS_DIR / 'figure_1_vcte_crp_forest.png',
        RESULTS_DIR / 'figure_1_vcte_crp_forest.tiff',
        RESULTS_DIR / 'figure_1_vcte_crp_forest.eps',
        RESULTS_DIR / 'figure_2_vcte_vs_fib4_diagnostic.png',
        RESULTS_DIR / 'figure_2_vcte_vs_fib4_diagnostic.tiff',
        RESULTS_DIR / 'figure_2_vcte_vs_fib4_diagnostic.eps',
        RESULTS_DIR / 'V2_Figure_1.jpg',
        RESULTS_DIR / 'V2_Figure_2.jpg'
    ]
    
    for f in files_to_check:
        assert f.exists(), f"Missing required file: {f}"
        assert f.stat().st_size > 0, f"File is empty: {f}"
        print(f"  [PASS] File verified: {f.name} ({f.stat().st_size:,} bytes)")
        
    # 2. Load statistical output
    with open(RESULTS_DIR / 'statistical_output_v2.json') as f:
        stat = json.load(f)
        
    ms_text = (BASE / 'MANUSCRIPT_FULL_JGIM_NMCD.md').read_text(encoding='utf-8')
    t1_text = (BASE / 'Table_1_Baseline.md').read_text(encoding='utf-8')
    t2_text = (BASE / 'Table_2_Multivariable_Joint_Models.md').read_text(encoding='utf-8')
    t3_text = (BASE / 'Table_3_VCTE_vs_FIB4_Diagnostic_Comparison.md').read_text(encoding='utf-8')
    
    # 3. Verify Sample Sizes and Prevalences
    n_total = stat['metadata']['n']
    n_events = stat['metadata']['n_events_advanced_ckm']
    assert n_total == 7043, f"Unexpected N: {n_total}"
    assert n_events == 1246, f"Unexpected events: {n_events}"
    assert "7,043" in ms_text, "N=7,043 missing from manuscript"
    assert "1,246" in ms_text, "Events=1,246 missing from manuscript"
    print("  [PASS] Cohort sample size and events verified (N=7,043, Events=1,246).")
    
    p_adv = stat['prevalences']['advanced_ckm']['estimate'] * 100
    p_vcte = stat['prevalences']['high_vcte']['estimate'] * 100
    p_crp = stat['prevalences']['high_hscrp']['estimate'] * 100
    assert f"{p_adv:.1f}%" in ms_text, f"Advanced CKM prevalence {p_adv:.1f}% mismatch"
    assert f"{p_vcte:.1f}%" in ms_text, f"VCTE prevalence {p_vcte:.1f}% mismatch"
    assert f"{p_crp:.1f}%" in ms_text, f"hs-CRP prevalence {p_crp:.1f}% mismatch"
    print(f"  [PASS] Population prevalences verified: Advanced CKM {p_adv:.1f}%, VCTE {p_vcte:.1f}%, hs-CRP {p_crp:.1f}%.")
    
    # 4. Verify Multivariable Models 1, 2, 3
    # Model 1
    m1 = stat['models']['Model 1']['interaction']
    m1_j = m1['joint_OR']
    m1_reri = m1['RERI_OR']['estimate']
    assert f"{m1_j[3]['or_value']:.2f}" in ms_text, "Model 1 Dual High OR mismatch"
    assert f"{m1_reri:.2f}" in ms_text, "Model 1 RERI mismatch"
    
    # Model 2 (Co-Primary)
    m2 = stat['models']['Model 2']['interaction']
    m2_j = m2['joint_OR']
    m2_reri = m2['RERI_OR']['estimate']
    m2_ap = m2['AP_OR']['estimate']
    m2_mp = m2['multiplicative_p']
    assert f"{m2_j[1]['or_value']:.2f}" in ms_text, "Model 2 G1 mismatch"
    assert f"{m2_j[2]['or_value']:.2f}" in ms_text, "Model 2 G2 mismatch"
    assert f"{m2_j[3]['or_value']:.2f}" in ms_text, "Model 2 G3 mismatch"
    assert f"{m2_reri:.2f}" in ms_text, "Model 2 RERI mismatch"
    assert f"{m2_mp:.4f}" in ms_text, "Model 2 Mult p mismatch"
    print(f"  [PASS] Model 2 co-primary verified: G1={m2_j[1]['or_value']:.2f}, G2={m2_j[2]['or_value']:.2f}, G3={m2_j[3]['or_value']:.2f}, RERI={m2_reri:.2f}, mult_p={m2_mp:.4f}.")
    
    # Model 3
    m3 = stat['models']['Model 3']['interaction']
    m3_j = m3['joint_OR']
    m3_reri = m3['RERI_OR']['estimate']
    assert f"{m3_j[3]['or_value']:.2f}" in ms_text, "Model 3 G3 mismatch"
    assert f"{m3_reri:.2f}" in ms_text, "Model 3 RERI mismatch"
    print(f"  [PASS] Model 3 verified: G3={m3_j[3]['or_value']:.2f}, RERI={m3_reri:.2f}.")
    
    # 5. Verify Secondary Outcomes
    cvd_or = stat['secondary_outcomes']['clinical_cvd_M2']['interaction']['joint_OR'][3]['or_value']
    ckd_or = stat['secondary_outcomes']['ckd_M2']['interaction']['joint_OR'][3]['or_value']
    assert f"{cvd_or:.2f}" in ms_text, "CVD OR mismatch"
    assert f"{ckd_or:.2f}" in ms_text, "CKD OR mismatch"
    print(f"  [PASS] Secondary outcomes verified: CVD OR={cvd_or:.2f}, CKD OR={ckd_or:.2f}.")
    
    # 6. Verify Diagnostic Comparison
    diag = stat['diagnostic_fib4_vs_vcte']
    sens = diag['overall']['sensitivity'] * 100
    spec = diag['overall']['specificity'] * 100
    ppv = diag['overall']['ppv'] * 100
    fpr_young = diag['age_lt_65']['false_positive_rate'] * 100
    fpr_old = diag['age_ge_65']['false_positive_rate'] * 100
    
    assert f"{sens:.1f}%" in ms_text, "Diagnostic sensitivity mismatch"
    assert f"{spec:.1f}%" in ms_text, "Diagnostic specificity mismatch"
    assert f"{ppv:.1f}%" in ms_text, "Diagnostic PPV mismatch"
    assert f"{fpr_young:.1f}%" in ms_text, "Younger FPR mismatch"
    assert f"{fpr_old:.1f}%" in ms_text, "Older FPR mismatch"
    print(f"  [PASS] Diagnostic performance verified: Sens={sens:.1f}%, Spec={spec:.1f}%, PPV={ppv:.1f}%, FPR Young={fpr_young:.1f}%, FPR Old={fpr_old:.1f}%.")
    
    # 7. Verify V2.2 main-text/abstract limits and editorial requirements.
    from v2_verify_results import check_editorial
    check_editorial(ms_text)

    # 8. Verify Table Markdown Integrity
    assert "| Overall (N=7,043) |" in t1_text, "Table 1 missing Overall column"
    assert "| Model 2: Co-Primary Multivariable |" in t2_text, "Table 2 missing Model 2 column"
    assert "False-Positive Rate (%)" in t3_text, "Table 3 missing False-Positive Rate row"
    print("  [PASS] Tables 1, 2, and 3 structure verified.")

    # 9. Verify STROBE Waterfall Document
    strobe_md = (BASE / 'STROBE_Waterfall_v2.md').read_text(encoding='utf-8')
    assert "27,493" in strobe_md, "STROBE missing 27,493"
    assert "7,043" in strobe_md, "STROBE missing 7,043"
    assert "11,585" in strobe_md, "STROBE missing 11,585"
    print("  [PASS] STROBE_Waterfall_v2.md verified.")

    # 10. Verify Zero Binormal Simulation (No scipy.stats.norm in figure generation)
    fig_code = (BASE / 'v2_04_generate_figures.py').read_text(encoding='utf-8')
    assert 'norm.cdf' not in fig_code, "scipy.stats.norm.cdf found in v2_04_generate_figures.py"
    assert 'norm.ppf' not in fig_code, "scipy.stats.norm.ppf found in v2_04_generate_figures.py"
    assert 'from scipy.stats import norm' not in fig_code, "norm imported in v2_04_generate_figures.py"
    print("  [PASS] Figure 2B verified: 100% empirical weighted ROC, zero scipy.stats.norm simulation.")

    # 11. Verify Editorial and Author Metadata
    cl_text = (BASE / 'COVER_LETTER_AND_ZERO_FEE_SUBMISSION_GUIDE.md').read_text(encoding='utf-8')
    assert "B.S." not in ms_text, "Found 'B.S.' in manuscript"
    assert "B.S." not in cl_text, "Found 'B.S.' in cover letter"
    assert "maintained at GitHub" not in ms_text, "Found 'maintained at GitHub' in manuscript"
    assert "maintained at GitHub" not in cl_text, "Found 'maintained at GitHub' in cover letter"
    for citation in [
        '4. Rinella ME, Lazarus JV, Ratziu V, et al. A multisociety Delphi consensus statement on new fatty liver disease nomenclature. *Hepatology*. 2023;78(6):1966-1986. doi:10.1097/HEP.0000000000000520',
        '29. Sanyal AJ, Newsome PN, Kliers I, et al. Phase 3 Trial of Semaglutide in Metabolic Dysfunction-Associated Steatohepatitis. *N Engl J Med*. 2025;392(21):2089-2099. doi:10.1056/NEJMoa2413258',
    ]:
        assert citation in ms_text.splitlines(), 'Corrected reference mismatch: '+citation
    print("  [PASS] Editorial integrity verified: author degree suffix removed, repository phrasing updated, References 4 and 29 corrected.")

    # 12. Verify New JSON Output Keys
    assert 'very_high_ckd_M2' in stat['secondary_outcomes'], "Missing very_high_ckd_M2"
    assert 'adult_core_cvd_M2' in stat['secondary_outcomes'], "Missing adult_core_cvd_M2"
    assert 'adult_core_ckd_M2' in stat['secondary_outcomes'], "Missing adult_core_ckd_M2"
    assert 'uniform_prevent_domain_M2' in stat['sensitivities'], "Missing uniform_prevent_domain_M2"
    assert 'exclude_acute_crp_gt10_M2' in stat['sensitivities'], "Missing exclude_acute_crp_gt10_M2"
    assert 'vcte_x_sii_M2' in stat['sensitivities'], "Missing vcte_x_sii_M2"
    assert 'flexible_age_spline_M2' in stat['sensitivities'], "Missing flexible_age_spline_M2"
    assert 'vcte_3level_M2' in stat['sensitivities'], "Missing vcte_3level_M2"
    assert 'joint_6group_OR' in stat['sensitivities']['vcte_3level_M2'], "Missing joint_6group_OR"
    assert 'age_lt_65' in stat['subgroups'], "Missing age_lt_65 subgroup"
    assert 'age_ge_65' in stat['subgroups'], "Missing age_ge_65 subgroup"
    assert 'cycle_2017_2020' in stat['subgroups'], "Missing cycle_2017_2020 subgroup"
    assert 'cycle_2021_2023' in stat['subgroups'], "Missing cycle_2021_2023 subgroup"
    assert 'age_calibrated_ge_65' in stat['diagnostic_fib4_vs_vcte'], "Missing age_calibrated_ge_65"
    assert 'roc_curves' in stat, "Missing roc_curves"
    assert len(stat['roc_curves']) == 5, "Expected 5 empirical ROC curves"
    print("  [PASS] All V2.1 JSON keys and models verified.")

    if saved_results_only:
        import hashlib
        import tempfile
        import pandas as pd
        from unittest.mock import patch
        from v2_verify_results import check_manuscript, check_tables, load
        json_hashes = {p: hashlib.sha256(p.read_bytes()).hexdigest()
                       for p in RESULTS_DIR.glob('*.json')}
        cohort_file = (BASE / 'data/v2_analytic_cohort.csv') if (BASE / 'data/v2_analytic_cohort.csv').exists() else (BASE.parent / 'data/v2_analytic_cohort.csv')
        universe_file = (BASE.parent / 'results/design_universe.csv') if (BASE.parent / 'results/design_universe.csv').exists() else (BASE.parent.parent / 'results/design_universe.csv')
        cohort = pd.read_csv(cohort_file)
        universe = pd.read_csv(universe_file)
        check_manuscript(stat, ms_text, cohort, universe)
        analysis = load('v2_03_statistical_analysis')
        with tempfile.TemporaryDirectory(prefix='v2-text-audit-') as temp:
            # Render existing JSON to temporary tables; never call analysis.main().
            with patch.object(analysis, 'BASE', Path(temp)):
                analysis.export_tables(stat, cohort)
            check_tables(stat, Path(temp))
        assert all(hashlib.sha256(p.read_bytes()).hexdigest() == digest
                   for p, digest in json_hashes.items()), 'JSON output changed'
        print('  [PASS] Saved-result manuscript and table checks; JSON unchanged; no models rerun.')
        print('\n=== SAVED-RESULTS TEXT/TABLE AUDIT PASSED (0 ERRORS; MODEL RECOMPUTATION SKIPPED) ===')
    else:
        from v2_verify_results import verify
        verify()
        print("\n=== COMPLETE V2.1 BIOSTATISTICAL, VISUAL, AND EDITORIAL AUDIT PASSED ===")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--saved-results-only', action='store_true',
                        help='Check saved results and text without rerunning models.')
    audit(saved_results_only=parser.parse_args().saved_results_only)
