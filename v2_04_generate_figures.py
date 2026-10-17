"""Generate publication-grade 600 DPI figures for Study 2.0 (V2.1 Patch).
Exports TIFF (600 DPI LZW), vector EPS, and PNG formats.
Figure 1: Forest plot of Joint VCTE and hs-CRP phenotypes across Models, Outcomes, and Subgroups.
Figure 2: Head-to-Head Diagnostic Comparison: Age-dependent false-positive inflation of FIB-4 vs VCTE and 100% empirical weighted ROC curves.
"""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Patch

BASE = Path(__file__).resolve().parent
RESULTS_DIR = BASE / 'results'
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Set high-quality publication styling
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['mathtext.fontset'] = 'dejavusans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 0.8

def load_data():
    with open(RESULTS_DIR / 'statistical_output_v2.json') as f:
        data = json.load(f)
    return data

def make_figure_1(data):
    """
    Figure 1: Forest plot of Joint Phenotypes (Low/Low, Low/High, High/Low, Dual High)
    across Models 1, 2, 3 and Secondary Outcomes & Subgroups.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 7.8), dpi=600, gridspec_kw={'width_ratios': [1.1, 0.9]})
    
    # Left Panel: Main Models 1-3 & Secondary Outcomes for the Dual High Group
    # Comparison of Joint Groups in Model 2 (Co-Primary)
    m2 = data['models']['Model 2']['interaction']
    j_ors = m2['joint_OR']
    
    groups = [
        'Dual High VCTE (≥8.0 kPa) +\nHigh hs-CRP (≥2.0 mg/L)',
        'High VCTE (≥8.0 kPa) /\nLow hs-CRP (<2.0 mg/L)',
        'Low VCTE (<8.0 kPa) /\nHigh hs-CRP (≥2.0 mg/L)',
        'Low VCTE (<8.0 kPa) /\nLow hs-CRP (<2.0 mg/L) [Ref]'
    ]
    
    ors = [j_ors[3]['or_value'], j_ors[2]['or_value'], j_ors[1]['or_value'], 1.0]
    lowers = [j_ors[3]['lower'], j_ors[2]['lower'], j_ors[1]['lower'], 1.0]
    uppers = [j_ors[3]['upper'], j_ors[2]['upper'], j_ors[1]['upper'], 1.0]
    
    y_pos = np.arange(len(groups))
    colors = ['#B91C1C', '#D97706', '#2563EB', '#4B5563']
    
    ax1.axvline(1.0, color='#666666', linestyle='--', linewidth=0.9, alpha=0.8)
    
    for i in range(len(groups)):
        if i == 3:
            ax1.plot(ors[i], y_pos[i], 's', color=colors[i], markersize=7.5)
        else:
            ax1.errorbar(ors[i], y_pos[i], xerr=[[ors[i]-lowers[i]], [uppers[i]-ors[i]]],
                         fmt='o', color=colors[i], ecolor=colors[i], elinewidth=2.0,
                         capsize=4, capthick=1.5, markersize=7)
            # Label
            ax1.text(uppers[i] * 1.06, y_pos[i], f"OR {ors[i]:.2f} ({lowers[i]:.2f}–{uppers[i]:.2f})",
                     va='center', ha='left', fontsize=9.2, fontweight='bold', color=colors[i])

    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(groups, fontsize=9.5, fontweight='medium')
    ax1.set_xlabel('Adjusted Odds Ratio for Advanced CKM Syndrome (Stages 3–4)', fontsize=10, fontweight='bold')
    ax1.set_title('A. Joint Phenotypes in Co-Primary Model (Model 2)\nSurvey-Weighted Taylor Series Linearization (df=40)',
                  fontsize=10.5, fontweight='bold', pad=12, loc='left')
    ax1.set_xlim(0.4, 8.0)
    ax1.set_ylim(-0.95, 3.5)
    ax1.set_xscale('log')
    ax1.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax1.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax1.set_xticks([0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0])
    ax1.grid(axis='x', linestyle=':', alpha=0.5)
    
    # Text box for interaction metrics in Model 2 placed cleanly in axes fraction coords
    reri = m2['RERI_OR']['estimate']
    reri_lo = m2['RERI_OR']['lower']
    reri_hi = m2['RERI_OR']['upper']
    ap = m2['AP_OR']['estimate'] * 100
    mp = m2['multiplicative_p']
    prev_int = m2['prevalence_interaction']
    
    annot_text = (
        f"Interaction Metrics (Co-Primary Model 2):\n"
        f"• Multiplicative p = {mp:.4f}\n"
        f"• Odds-Scale RERI = {reri:.2f} (95% CI: {reri_lo:.2f}–{reri_hi:.2f})\n"
        f"• Odds-Scale AP = {ap:.1f}% (descriptive contrast)\n"
        f"• Standardized Prevalence Interaction:\n"
        f"  +{prev_int['estimate']*100:.1f} percentage points (95% CI: {prev_int['lower']*100:.1f}–{prev_int['upper']*100:.1f})"
    )
    ax1.text(0.04, 0.04, annot_text, transform=ax1.transAxes, fontsize=8.2, va='bottom', ha='left',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8FAFC', edgecolor='#CBD5E1', linewidth=1.0))

    # Right Panel: Dual High Phenotype across Models, Outcomes, and Subgroups
    categories = [
        'Model 1 (Demographics)',
        'Model 2 (Co-Primary)',
        'Model 3 (Extended Clinical)',
        'Clinical CVD (Model 2)',
        'Kidney Abnormality / CKD',
        'Very-High-Risk CKD (KDIGO)',
        'Men',
        'Women',
        'Age ≥ 65 Years',
        'Age < 65 Years',
        'Diabetes Mellitus',
        'No Diabetes'
    ]
    
    m1_j3 = data['models']['Model 1']['interaction']['joint_OR'][3]
    m2_j3 = data['models']['Model 2']['interaction']['joint_OR'][3]
    m3_j3 = data['models']['Model 3']['interaction']['joint_OR'][3]
    cvd_j3 = data['secondary_outcomes']['clinical_cvd_M2']['interaction']['joint_OR'][3]
    ckd_j3 = data['secondary_outcomes']['ckd_M2']['interaction']['joint_OR'][3]
    vh_ckd_j3 = data['secondary_outcomes']['very_high_ckd_M2']['interaction']['joint_OR'][3]
    men_j3 = data['subgroups']['men']['interaction']['joint_OR'][3]
    women_j3 = data['subgroups']['women']['interaction']['joint_OR'][3]
    old65_j3 = data['subgroups']['age_ge_65']['interaction']['joint_OR'][3]
    young65_j3 = data['subgroups']['age_lt_65']['interaction']['joint_OR'][3]
    diab_j3 = data['subgroups']['diabetes']['interaction']['joint_OR'][3]
    nodiab_j3 = data['subgroups']['no_diabetes']['interaction']['joint_OR'][3]
    
    right_items = [
        m1_j3, m2_j3, m3_j3,
        cvd_j3, ckd_j3, vh_ckd_j3,
        men_j3, women_j3,
        old65_j3, young65_j3,
        diab_j3, nodiab_j3
    ]
    
    r_ors = [x['or_value'] for x in right_items]
    r_lowers = [x['lower'] for x in right_items]
    r_uppers = [x['upper'] for x in right_items]
    
    y_pos2 = np.arange(len(categories))[::-1]
    
    ax2.axvline(1.0, color='#666666', linestyle='--', linewidth=0.9, alpha=0.8)
    
    bar_colors = ['#B91C1C']*3 + ['#7C3AED']*3 + ['#0284C7']*2 + ['#0D9488']*2 + ['#D97706']*2
    
    for i in range(len(categories)):
        ax2.errorbar(r_ors[i], y_pos2[i], xerr=[[r_ors[i]-r_lowers[i]], [r_uppers[i]-r_ors[i]]],
                     fmt='s', color=bar_colors[i], ecolor=bar_colors[i], elinewidth=1.8,
                     capsize=3.5, capthick=1.2, markersize=5.5)
        ax2.text(r_uppers[i] * 1.05, y_pos2[i], f"{r_ors[i]:.2f} ({r_lowers[i]:.2f}–{r_uppers[i]:.2f})",
                 va='center', ha='left', fontsize=8.0, color='#1E293B', fontweight='medium')

    ax2.set_yticks(y_pos2)
    ax2.set_yticklabels(categories, fontsize=9, fontweight='medium')
    ax2.set_xlabel('Adjusted Odds Ratio (Dual High vs Reference)', fontsize=10, fontweight='bold')
    ax2.set_title('B. Dual High Phenotype Across Models & Subgroups\nSurvey-Weighted Associations with 95% Confidence Intervals',
                  fontsize=10.5, fontweight='bold', pad=12, loc='left')
    ax2.set_xlim(0.4, 12.0)
    ax2.set_xscale('log')
    ax2.xaxis.set_major_formatter(ticker.ScalarFormatter())
    ax2.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax2.set_xticks([0.5, 0.7, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 10.0])
    ax2.grid(axis='x', linestyle=':', alpha=0.5)
    
    plt.tight_layout()
    
    fig_stem = RESULTS_DIR / 'figure_1_vcte_crp_forest'
    plt.savefig(f"{fig_stem}.png", dpi=600, bbox_inches='tight')
    plt.savefig(f"{fig_stem}.tiff", dpi=600, pil_kwargs={'compression': 'tiff_lzw'}, bbox_inches='tight')
    plt.savefig(f"{fig_stem}.eps", format='eps', bbox_inches='tight')
    # Compact preview generated directly from this figure, not a stale image.
    preview_name = 'V2_Figure_1' if fig_stem.name.startswith('figure_1_') else 'V2_Figure_2'
    plt.savefig(RESULTS_DIR / (preview_name + '.jpg'), dpi=150, bbox_inches='tight')
    plt.close()
    print("Exported Figure 1 in PNG, TIFF (600 DPI), and EPS formats.")

def make_figure_2(data):
    """
    Figure 2: Head-to-Head Diagnostic and Discrimination Comparison:
    Panel A: Age-dependent false-positive rate explosion of FIB-4 vs VCTE (4 groups including age-calibrated).
    Panel B: Discrimination ROC Curves plotted from 100% empirical survey-weighted coordinates.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14.0, 6.2), dpi=600)
    
    # Panel A: Diagnostic Misclassification & False Positive Explosion (4 groups)
    diag = data['diagnostic_fib4_vs_vcte']
    age_groups = [
        'Younger Adults\n(30–64)\nFIB-4 ≥1.30',
        'Older Adults\n(65–79)\nStandard ≥1.30',
        'Older Adults\n(65–79)\nAge-Calib ≥2.00',
        'Overall Cohort\n(30–79)\nFIB-4 ≥1.30'
    ]
    
    fpr_vals = [
        diag['age_lt_65']['false_positive_rate'] * 100,
        diag['age_ge_65']['false_positive_rate'] * 100,
        diag['age_calibrated_ge_65']['false_positive_rate'] * 100,
        diag['overall']['false_positive_rate'] * 100
    ]
    
    spec_vals = [
        diag['age_lt_65']['specificity'] * 100,
        diag['age_ge_65']['specificity'] * 100,
        diag['age_calibrated_ge_65']['specificity'] * 100,
        diag['overall']['specificity'] * 100
    ]
    
    ppv_vals = [
        diag['age_lt_65']['ppv'] * 100,
        diag['age_ge_65']['ppv'] * 100,
        diag['age_calibrated_ge_65']['ppv'] * 100,
        diag['overall']['ppv'] * 100
    ]
    
    x = np.arange(len(age_groups))
    width = 0.25
    
    rects1 = ax1.bar(x - width, fpr_vals, width, label='False-Positive Rate (%)', color='#EF4444', edgecolor='#B91C1C', linewidth=1.1)
    rects2 = ax1.bar(x, spec_vals, width, label='Specificity (%)', color='#3B82F6', edgecolor='#1D4ED8', linewidth=1.1)
    rects3 = ax1.bar(x + width, ppv_vals, width, label='Positive Predictive Value (%)', color='#F59E0B', edgecolor='#D97706', linewidth=1.1)
    
    for rect in rects1:
        height = rect.get_height()
        ax1.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.5, fontweight='bold', color='#B91C1C')
    for rect in rects2:
        height = rect.get_height()
        ax1.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.0, color='#1E3A8A')
    for rect in rects3:
        height = rect.get_height()
        ax1.annotate(f'{height:.1f}%',
                    xy=(rect.get_x() + rect.get_width() / 2, height),
                    xytext=(0, 4), textcoords="offset points",
                    ha='center', va='bottom', fontsize=8.0, color='#78350F')

    ax1.set_ylabel('Survey-Weighted Percentage (%)', fontsize=10, fontweight='bold')
    ax1.set_title('A. FIB-4 Inaccuracy Across Age Strata\n4.5x False-Positive Surge in Elderly & Age-Calibration Trade-off',
                  fontsize=10.5, fontweight='bold', pad=12, loc='left')
    ax1.set_xticks(x)
    ax1.set_xticklabels(age_groups, fontsize=8.8, fontweight='medium')
    ax1.set_ylim(0, 140)
    ax1.set_yticks(np.arange(0, 101, 20))
    ax1.grid(axis='y', linestyle=':', alpha=0.5)
    ax1.legend(loc='upper left', frameon=True, fontsize=8.0)
    
    # Highlight annotation for the 4.5x surge (target y=68.5 to sit cleanly above 63.8% label)
    ax1.annotate('4.5x False-Positive Surge\n(63.8% vs 14.3%)',
                 xy=(1 - width, 68.5), xytext=(0.45, 80),
                 arrowprops=dict(arrowstyle="->", color='#991B1B', lw=1.5),
                 fontsize=8.2, fontweight='bold', color='#991B1B',
                 bbox=dict(boxstyle="round,pad=0.4", facecolor="#FEE2E2", edgecolor="#F87171"))

    # Reserve headroom so the sensitivity callout cannot cover bars or values.
    callout = (
        "Age-Calibrated Cutoff (≥2.00):\n"
        f"• FPR drops: {fpr_vals[1]:.1f}% → {fpr_vals[2]:.1f}%\n"
        f"• Sensitivity drops: {100*diag['age_ge_65']['sensitivity']:.1f}% → "
        f"{100*diag['age_calibrated_ge_65']['sensitivity']:.1f}%"
    )
    ax1.text(2.45, 120, callout, ha='center', va='center', fontsize=8.0,
             bbox=dict(boxstyle='round,pad=0.4', facecolor='#F8FAFC', edgecolor='#CBD5E1'))

    # Panel B: 100% EMPIRICAL SURVEY-WEIGHTED ROC CURVES (ZERO SIMULATION)
    roc = data['roc_curves']
    disc_models = data['discrimination']['models']
    
    vcte_fpr = np.array(roc['vcte_M2']['fpr'])
    vcte_tpr = np.array(roc['vcte_M2']['tpr'])
    vcte_auc = disc_models['vcte_M2']['auc']
    
    fib4_fpr = np.array(roc['fib4_M2']['fpr'])
    fib4_tpr = np.array(roc['fib4_M2']['tpr'])
    fib4_auc = disc_models['fib4_M2']['auc']
    
    dual_fpr = np.array(roc['dual_vcte_crp_M2']['fpr'])
    dual_tpr = np.array(roc['dual_vcte_crp_M2']['tpr'])
    dual_auc = disc_models['dual_vcte_crp_M2']['auc']
    
    ax2.plot(vcte_fpr, vcte_tpr, color='#1E40AF', linewidth=2.2, label=f'Model 2 + Direct VCTE Stiffness (AUC = {vcte_auc:.4f})')
    ax2.plot(fib4_fpr, fib4_tpr, color='#DC2626', linewidth=2.0, linestyle='--', label=f'Model 2 + Formula FIB-4 (AUC = {fib4_auc:.4f})')
    ax2.plot(dual_fpr, dual_tpr, color='#0D9488', linewidth=1.8, linestyle='-.', label=f'Model 2 + Dual VCTE & hs-CRP (AUC = {dual_auc:.4f})')
    ax2.plot([0, 1], [0, 1], color='#94A3B8', linestyle=':', linewidth=1.2, label='Chance (AUC = 0.5000)')
    
    ax2.set_xlabel('1 – Specificity (False Positive Rate)', fontsize=10, fontweight='bold')
    ax2.set_ylabel('Sensitivity (True Positive Rate)', fontsize=10, fontweight='bold')
    ax2.set_title('B. Multivariable Discrimination for Advanced CKM\nEmpirical Survey-Weighted ROC Curves (No Parametric Assumptions)',
                  fontsize=10.5, fontweight='bold', pad=12, loc='left')
    ax2.set_xlim(0, 1.0)
    ax2.set_ylim(0, 1.02)
    ax2.grid(True, linestyle=':', alpha=0.5)
    ax2.legend(loc='lower right', frameon=True, fontsize=8.5)
    
    # Apparent discrimination does not establish clinical utility.
    ax2.text(0.40, 0.28, "Apparent in-sample discrimination.\nSimilar AUCs do not establish\nincremental clinical utility.", fontsize=8.0,
             transform=ax2.transAxes,
             bbox=dict(boxstyle='round,pad=0.5', facecolor='#F8FAFC', edgecolor='#CBD5E1', linewidth=1.0))

    plt.tight_layout()
    
    fig_stem = RESULTS_DIR / 'figure_2_vcte_vs_fib4_diagnostic'
    plt.savefig(f"{fig_stem}.png", dpi=600, bbox_inches='tight')
    plt.savefig(f"{fig_stem}.tiff", dpi=600, pil_kwargs={'compression': 'tiff_lzw'}, bbox_inches='tight')
    plt.savefig(f"{fig_stem}.eps", format='eps', bbox_inches='tight')
    # Compact preview generated directly from this figure, not a stale image.
    preview_name = 'V2_Figure_1' if fig_stem.name.startswith('figure_1_') else 'V2_Figure_2'
    plt.savefig(RESULTS_DIR / (preview_name + '.jpg'), dpi=150, bbox_inches='tight')
    plt.close()
    print("Exported Figure 2 in PNG, TIFF (600 DPI), and EPS formats.")

def main():
    data = load_data()
    make_figure_1(data)
    make_figure_2(data)
    print("=== Figure Generation Completed Successfully ===")

if __name__ == '__main__':
    main()
