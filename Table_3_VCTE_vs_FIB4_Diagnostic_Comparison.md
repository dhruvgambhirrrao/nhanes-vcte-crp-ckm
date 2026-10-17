# Table 3. Head-to-Head Diagnostic and Discrimination Performance: Indirect FIB-4 vs Direct VCTE FibroScan

Diagnostic test parameters evaluate the performance of FIB-4 against the reference standard of direct VCTE liver stiffness $\ge 8.0$ kPa. Values are survey-weighted estimates.

| Diagnostic Metric | Overall Cohort: FIB-4 ≥1.30 (Ages 30–79, N=7,043) | Younger Adults: FIB-4 ≥1.30 (Ages 30–64, N=5,223) | Older Adults: Standard FIB-4 ≥1.30 (Ages 65–79, N=1,820) | Older Adults: Age-Calibrated FIB-4 ≥2.00 (Ages 65–79, N=1,820) |
| :--- | :--- | :--- | :--- | :--- |
| Unweighted Sample Count ($N$) | 7,043 | 5,223 | 1,820 | 1,820 |
| True Positives ($n$) | 329 | 156 | 173 | 68 |
| False Positives ($n$) | 1,750 | 741 | 1,009 | 275 |
| False Negatives ($n$) | 488 | 405 | 83 | 188 |
| True Negatives ($n$) | 4,476 | 3,921 | 555 | 1,289 |
| **Sensitivity (%)** | 34.8% | 24.6% | 64.6% | 29.0% |
| **Specificity (%)** | 75.8% | 85.7% | 36.2% | 82.5% |
| **Positive Predictive Value (PPV, %)** | 14.5% | 15.8% | 13.2% | 19.9% |
| **Negative Predictive Value (NPV, %)** | 90.8% | 91.2% | 87.2% | 88.5% |
| **Positive Likelihood Ratio (+LR)** | 1.44 | 1.72 | 1.01 | 1.65 |
| **Negative Likelihood Ratio (-LR)** | 0.86 | 0.88 | 0.98 | 0.86 |
| **False-Positive Rate (%)** | 24.2% | 14.3% | 63.8% | 17.5% |

### Discrimination for Advanced CKM Syndrome (Stages 3–4)

C-statistic confidence intervals use the survey-weighted delete-1-PSU jackknife ($df=40$), conditional on full-sample fitted predictions. These are apparent in-sample estimates, not external or cross-validated performance.

| Model Specification | Survey-Weighted C-Statistic / AUC | 95% Confidence Interval | Contrast vs Reference Model |
| :--- | :--- | :--- | :--- |
| **Base Model 2 (Demographics + Socioeconomic + Adiposity)** | 0.8636 | 0.8495–0.8777 | Reference for Additive Value |
| **Model 2 + Direct VCTE Stiffness** | 0.8636 | 0.8494–0.8777 | $\Delta\text{AUC} = -0.0002$ (-0.0013–0.0009 vs FIB-4) |
| **Model 2 + Formula FIB-4** | 0.8638 | 0.8496–0.8780 | Reference for Biomarker Comparison |
| **Model 2 + Direct VCTE & hs-CRP** | 0.8643 | 0.8503–0.8783 | $\Delta\text{AUC} = +0.0007$ (-0.0007–0.0021 vs Base) |
| **Model 2 + Formula FIB-4 & SII** | 0.8652 | 0.8512–0.8792 | Comparison Dual Formula Model |

*Key Clinical Finding:* In adults aged $\ge 65$, standard FIB-4 $\ge 1.30$ generates a false-positive rate of 63.8% (specificity 36.2%), driven by chronological age in the formula numerator. Calibrating the FIB-4 threshold to $\ge 2.00$ in older adults reduces false positives to 17.5% (specificity 82.5%), but sensitivity falls steeply to 29.0%. These diagnostic comparisons use VCTE as the reference threshold and do not establish biopsy accuracy or age-independent performance.