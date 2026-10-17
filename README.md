# Reproducibility Archive: Direct Physical Vibration-Controlled Transient Elastography vs. Formula-Based FIB-4 and High-Sensitivity C-Reactive Protein in Advanced CKM Syndrome (NHANES 2017–2023)

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.14022838.svg)](https://doi.org/10.5281/zenodo.14022838)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Survey Design: df=40](https://img.shields.io/badge/Survey%20Design-df%3D40-success.svg)]()
[![Zero-Hallucination Audit](https://img.shields.io/badge/Biostatistical%20Audit-100%25%20Verified-brightgreen.svg)]()

---

## Authors & Affiliations
* **Dhruv Gambhirrao** (First & Corresponding Author) — Department of Biological Sciences, University of North Texas, Denton, TX, USA; Email: `dhruvgambhirrao@my.unt.edu`
* **Devpal Ghuman** — Department of Biological Sciences, University of North Texas, Denton, TX, USA; Email: `dsg3583@gmail.com`
* **Tarun Achar** — Department of Biological Sciences, University of North Texas, Denton, TX, USA; Email: `tarunah.achar@gmail.com`

**Target Journals:** *Journal of General Internal Medicine (JGIM)* / *Nutrition, Metabolism and Cardiovascular Diseases (NMCD)*  
**Conference Submission:** Society of General Internal Medicine (SGIM) 2027 Annual Meeting

---

## Executive Summary of Findings

This study investigates the co-pathological synergy between direct physical liver stiffness (measured via Vibration-Controlled Transient Elastography [VCTE] FibroScan) and systemic vascular inflammation (measured via high-sensitivity C-reactive protein [hs-CRP]) in predicting **Advanced Cardiovascular-Kidney-Metabolic (CKM) Syndrome** (AHA Stages 3–4: clinical cardiovascular disease, very-high-risk chronic kidney disease, or elevated 10-year PREVENT risk $\ge 20\%$).

Using nationally representative complex survey data from CDC NHANES (2017–2023; $N = 7,043$ analytic cohort representing $\approx 150.2$ million non-institutionalized US adults; 40 degrees of freedom, $df = 40$), we demonstrate:

1. **Supra-Additive Biological Synergism:**
   * In multivariable survey-weighted logistic regression adjusting for demographics, SES, BMI, and waist circumference (Model 2), individuals with **Dual High VCTE ($\ge 8.0\text{ kPa}$) and hs-CRP ($\ge 3.0\text{ mg/L}$)** exhibit an adjusted Odds Ratio of **$2.01$** ($95\%\text{ CI: } 1.34\text{--}3.03$, $p = 0.0016$).
   * Relative Excess Risk due to Interaction on the odds scale: **$\text{RERI}_{\text{OR}} = 0.91$** ($95\%\text{ CI: } 0.10\text{--}1.72$, $p = 0.0287$).
   * Attributable Proportion: **$\text{AP}_{\text{OR}} = 0.45$** ($45.1\%$ of joint risk is attributable strictly to biological interaction).
   * Synergy Index: **$S_{\text{OR}} = 9.17$** ($95\%\text{ CI: } 1.04\text{--}81.18$); Multiplicative interaction $p = 0.0185$.
   * Retained significance in full cardiometabolic biomarker adjustment (Model 3: Dual High OR = $1.71$, $95\%\text{ CI: } 1.15\text{--}2.54$, $p = 0.0102$; $\text{RERI} = 0.76$, $95\%\text{ CI: } 0.02\text{--}1.51$, $p = 0.0454$).

2. **Secondary Clinical Outcomes:**
   * Independent association with Clinical Cardiovascular Disease (Model 2 OR = **$1.50$**, $95\%\text{ CI: } 1.06\text{--}2.12$, $p = 0.0245$).
   * Markedly elevated risk for KDIGO High/Very-High-Risk Chronic Kidney Disease (Model 2 OR = **$2.36$**, $95\%\text{ CI: } 1.55\text{--}3.59$, $p = 0.0002$; KDIGO Stage 4/5 CKD OR = **$3.65$**, $95\%\text{ CI: } 1.48\text{--}9.01$, $p = 0.0069$).

3. **Catastrophic Diagnostic Failure of Formula-Based FIB-4:**
   * The standard guideline cutpoint of $\text{FIB-4} \ge 1.30$ demonstrated an overall sensitivity of only **$34.8\%$** and a positive predictive value (PPV) of **$14.5\%$**, corresponding to an **$85.5\%$ false-positive rate** upon triage.
   * **Age-Confounding Surge:** In younger adults ($<65$ years), the false-positive rate was $14.3\%$; in older adults ($65\text{--}79$ years), the false-positive rate escalated **$4.5\times$ to $63.8\%$** ($p < 0.0001$).
   * **Age-Calibrated Mitigation:** Calibrating the FIB-4 threshold to $\ge 2.0$ in older adults ($\ge 65$ years) slashed the older-adult false-positive rate down to **$30.0\%$** (a $53\%$ relative reduction) while boosting specificity from $36.2\%$ to $70.0\%$.

4. **Discriminative Superiority of Direct Physical Elastography:**
   * Adding dual direct VCTE + hs-CRP to base demographic risk yielded a statistically significant increase in the survey-weighted $C$-statistic ($\text{AUC} = 0.7766$ vs $0.7550$, **$\Delta\text{AUC} = +0.0216$**, $95\%\text{ CI: } +0.0053\text{ to }+0.0380$, $p = 0.0107$).
   * In contrast, dual formula-based markers (FIB-4 + Systemic Immune-Inflammation Index [SII]) provided virtually zero incremental discrimination over base risk ($\text{AUC} = 0.7562$, **$\Delta\text{AUC} = +0.0012$**, $95\%\text{ CI: } -0.0005\text{ to }+0.0029$, $p = 0.1706$).

---

## Directory Architecture

```
reproducibility_archive/
├── README.md                                  # Complete reproduction guide and documentation
├── CITATION.cff                               # Citation metadata format (v1.2.0)
├── LICENSE                                    # MIT Open Source License (2026)
├── requirements.txt                           # Pinned Python package dependencies
│
├── 03_statistical_analysis.py                 # Core domain-aware Taylor Series variance engine
├── v2_01_ingest_lux_hscrp.py                  # Step 1: CDC NHANES XPT downloader & SHA-256 verifier
├── v2_02_cohort_engineering.py                # Step 2: Complex survey cohort merging & assay bridging
├── v2_03_statistical_analysis.py              # Step 3: Complex survey regression, synergy & ROC engine
├── v2_04_generate_figures.py                  # Step 4: High-resolution (600 DPI) figure generator
├── v2_05_audit.py                             # Step 5: Full automated compliance audit suite
├── v2_verify_results.py                       # Step 6: Numerical precision & zero-hallucination verification
├── build_docx_submission.py                   # Step 7: Word (.docx) publication document generator
├── build_scientific_poster.py                 # Step 8: 48" x 36" academic poster generator (.pptx)
│
├── MANUSCRIPT_FULL_JGIM_NMCD.md               # Complete verified manuscript (2,395 words, 50 refs)
├── COVER_LETTER_AND_ZERO_FEE_SUBMISSION_GUIDE.md # Cover letter & author submission instructions
├── STROBE_Waterfall_v2.md                     # STROBE participant attrition waterfall
├── Table_1_Baseline.md                        # Table 1: Weighted baseline characteristics
├── Table_2_Multivariable_Joint_Models.md      # Table 2: Multivariable regression & biological synergy
├── Table_3_VCTE_vs_FIB4_Diagnostic_Comparison.md # Table 3: Diagnostic comparison & age-stratification
│
├── 07_Scientific_Poster_48x36_CKM_Synergy.pptx # Ready-to-print 48"x36" scientific conference poster
│
├── data/
│   └── v2_analytic_cohort.csv                 # Primary analytic cohort (N=7,043; complete data)
│
└── results/
    ├── statistical_output_v2.json             # Audited master statistical JSON (752 KB)
    ├── v2_cohort_metadata.json                # Cohort verification metadata
    ├── v2_strobe_waterfall.json               # STROBE attrition counts and exclusion reasons
    ├── v2_download_manifest.json              # SHA-256 checksums of CDC SAS transport files
    ├── design_universe.csv                    # Complete demographic sampling universe (df=40)
    ├── figure_1_vcte_crp_forest.png           # Figure 1: 600 DPI multivariable forest plot (PNG)
    ├── figure_1_vcte_crp_forest.tiff          # Figure 1: Publication TIFF
    ├── figure_1_vcte_crp_forest.eps           # Figure 1: Vector EPS
    ├── figure_2_vcte_vs_fib4_diagnostic.png   # Figure 2: 600 DPI diagnostic comparison & ROCs (PNG)
    ├── figure_2_vcte_vs_fib4_diagnostic.tiff  # Figure 2: Publication TIFF
    ├── figure_2_vcte_vs_fib4_diagnostic.eps   # Figure 2: Vector EPS
    ├── V2_Figure_1.jpg                        # Journal web preview Figure 1
    └── V2_Figure_2.jpg                        # Journal web preview Figure 2
```

---

## Complex Survey Methodology & CDC Data Sources

### Survey Design Integrity ($df = 40$)
NHANES employs a complex, stratified, multi-stage, unequal-probability sampling design. To guarantee nationally representative inferences without standard-error deflation:
1. **Sampling Universe:** The complete raw sampling universe ($N = 27,493$ across 2017–March 2020 and 2021–2023) was preserved in `results/design_universe.csv`. Taylor Series Linearization calculates variance across all primary sampling units (`SDMVPSU`) within sampling strata (`SDMVSTRA`), yielding exactly **40 degrees of freedom** ($df = 40$).
2. **Survey Weights:** MEC examination weights (`WTMECPRP` for 2017–March 2020 pre-pandemic; `WTPH2YR` for 2021–2023 post-pandemic) were pooled following CDC National Center for Health Statistics (NCHS) guidance:
   $$\text{Weight} = \text{Base Weight} \times \begin{cases} 3.2 / 5.2 & (\text{2017--2020}) \\ 2.0 / 5.2 & (\text{2021--2023}) \end{cases}$$
3. **Harmonization & Deming Regression Assay Bridging:**
   * Alanine Aminotransferase (ALT): $\text{ALT}_{\text{bridged}} = 1.477 + 0.9663 \times \text{LBXSATSI}$
   * Serum Triglycerides: $\text{TG}_{\text{bridged}} = 0.8567 + 1.012 \times \text{LBXSTR}$
   * Urine Albumin: $\text{Alb}_{\text{bridged}} = 1.381 + 0.8407 \times \text{URXUMA}$
   * hs-CRP: $\text{hs-CRP}_{\text{bridged}} = \max(0.08, -0.08653 + 0.9672 \times \text{LBXHSCRP})$

---

## Replication Instructions

### Prerequisites
* Python 3.11 or higher
* Recommended: Virtual environment

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
# or: .venv\Scripts\activate    # On Windows

# Install pinned dependencies
pip install -r requirements.txt
```

---

### Option A: Instant Verification Audit (Zero-Recomputation Mode)
To instantly verify every reported number, sample size, odds ratio, confidence interval, p-value, and table against the audited JSON without re-downloading or re-fitting models:

```bash
python v2_05_audit.py --saved-results-only
```
**Expected Output:**
```
=== Running Study 2.0 Biostatistical Compliance Audit ===
  [PASS] File verified: MANUSCRIPT_FULL_JGIM_NMCD.md (31,274 bytes)
  ...
  [PASS] Cohort sample size and events verified (N=7,043, Events=1,246).
  [PASS] Population prevalences verified: Advanced CKM 13.8%, VCTE 10.5%, hs-CRP 45.6%.
  [PASS] Model 2 co-primary verified: G1=1.26, G2=0.85, G3=2.01, RERI=0.91, mult_p=0.0185.
  [PASS] Model 3 verified: G3=1.71, RERI=0.76.
  [PASS] Secondary outcomes verified: CVD OR=1.50, CKD OR=2.36.
  [PASS] Diagnostic performance verified: Sens=34.8%, Spec=75.8%, PPV=14.5%, FPR Young=14.3%, FPR Old=63.8%.
  [PASS] V2.2 editorial checks: main text 2,395 words; abstract 239 words; legends, metadata and terminology verified.
  [PASS] Saved-result manuscript and table checks; JSON unchanged; no models rerun.

=== SAVED-RESULTS TEXT/TABLE AUDIT PASSED (0 ERRORS; MODEL RECOMPUTATION SKIPPED) ===
```

---

### Option B: Full Re-Execution Pipeline (From Raw CDC NHANES Data)
To re-download the live CDC files, re-engineer cohorts, re-fit all complex survey GLM regressions, and re-render figures:

```bash
# 1. Download CDC NHANES SAS Transport (.XPT) files & verify SHA-256
python v2_01_ingest_lux_hscrp.py

# 2. Build analytic cohort, apply Deming assay bridges, and generate STROBE flow
python v2_02_cohort_engineering.py

# 3. Fit survey-weighted multivariable logistic regressions, RERI synergy, and ROC curves
python v2_03_statistical_analysis.py

# 4. Generate 600 DPI publication-grade figures (PNG, TIFF, EPS)
python v2_04_generate_figures.py

# 5. Run full compliance audit and numerical recomputation check
python v2_05_audit.py
```

---

### Option C: Build Word (.docx) Submission Package and Scientific Poster (.pptx)
To generate the formatted Word documents for journal upload and the 48" x 36" presentation poster:

```bash
# Generate Word documents (.docx) with academic three-line tables and embedded figures
python build_docx_submission.py

# Generate 48" x 36" academic conference poster (.pptx)
python build_scientific_poster.py
```

---

## Citation & Metadata
To cite this repository or study:
```bibtex
@article{gambhirrao2026vcte_ckm,
  title={Direct Physical Vibration-Controlled Transient Elastography vs. Formula-Based FIB-4 and High-Sensitivity C-Reactive Protein in Advanced Cardiovascular-Kidney-Metabolic Syndrome: A Nationally Representative Complex Survey Cohort Study (NHANES 2017--2023)},
  author={Gambhirrao, Dhruv and Ghuman, Devpal and Achar, Tarun},
  journal={Journal of General Internal Medicine / NMCD (Under Review)},
  year={2026},
  version={2.3.0},
  doi={10.5281/zenodo.14022838},
  url={https://github.com/dhruvgambhirrrao/nhanes-vcte-crp-ckm}
}
```

---

## License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details. NHANES data are in the public domain and provided by the Centers for Disease Control and Prevention (CDC) National Center for Health Statistics (NCHS).
