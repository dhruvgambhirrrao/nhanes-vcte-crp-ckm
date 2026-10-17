# STROBE Flowchart and Participant Disposition Waterfall: Study 2.0 (VCTE & hs-CRP)

This document details the complete, step-by-step participant disposition following the STROBE (Strengthening the Reporting of Observational Studies in Epidemiology) guidelines for complex survey cohorts.

## Part 1: Parent NHANES 2017–2023 Universe to Primary Complete-Case Cohort

| Sequential Step | Criteria Applied | Participants Retained ($N$) | Excluded ($N$) | Notes |
| :--- | :--- | :--- | :--- | :--- |
| **1. Total Survey Population** | NHANES 2017–March 2020 (`P_`) and 2021–2023 (`_L`) | **27,493** | 0 | Full NCHS design universe |
| **2. Age >=20** | Age >=20 | **17,041** | 10,452 | Parent cohort sequential exclusion |
| **3. Positive MEC and appropriate laboratory weights** | Positive MEC and appropriate laboratory weights | **15,296** | 1,745 | Parent cohort sequential exclusion |
| **4. No identified pregnancy** | No identified pregnancy | **15,168** | 128 | Parent cohort sequential exclusion |
| **5. No extreme hematology** | No extreme hematology | **15,165** | 3 | Parent cohort sequential exclusion |
| **6. Complete positive core blood biomarkers** | Complete positive core blood biomarkers | **13,119** | 2,046 | Parent cohort sequential exclusion |
| **7. Complete staging and medication variables** | Complete staging and medication variables | **11,382** | 1,737 | Parent cohort sequential exclusion |
| **8. Primary PREVENT age domain 30-79** | Primary PREVENT age domain 30-79 | **9,382** | 2,000 | Parent cohort sequential exclusion |
| **9. PREVENT input domain or independently established advanced disease** | PREVENT input domain or independently established advanced disease | **8,812** | 570 | Parent cohort sequential exclusion |
| **10. Common complete-case cohort for Models 1-3** | Common complete-case cohort for Models 1-3 | **7,756** | 1,056 | Parent cohort sequential exclusion |

## Part 2: Study 2.0 VCTE Elastography & hs-CRP Inclusion Waterfall

| Sequential Step | Criteria Applied | Participants Retained ($N$) | Excluded ($N$) | Cumulative Excluded ($N$) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Primary Analytic Cohort** | Pre-VCTE complete-case adults aged 30–79 | **7,756** | 0 | 0 |
| **2. VCTE Examination Record** | Present in `P_LUX` or `LUX_L` | **7,756** | 0 | 0 |
| **3. Complete VCTE Exam** | Exam status complete (`LUAXSTAT == 1`) | **7,052** | 704 | 704 |
| **4. Positive Stiffness & CAP** | `LUXSMED > 0` and `LUXCAPM > 0` | **7,052** | 0 | 704 |
| **5. Measurement Validity** | At least 10 valid measures (`LUANMVGP >= 10`) | **7,052** | 0 | 704 |
| **6. Measurement Reliability** | IQR / Median stiffness $\le 30.0\%$ (`LUXSIQRM <= 30.0`) | **7,052** | 0 | 704 |
| **7. Bridged hs-CRP Available** | Non-missing serum hs-CRP (`LBXHSCRP > 0`) | **7,043** | 9 | 713 |

**Final Primary Analytic Cohort for Study 2.0:** **N = 7,043** US adults aged 30–79 years.

## Part 3: Secondary Adult Core Cohort (Ages $\ge 20$) VCTE Waterfall

| Sequential Step | Criteria Applied | Participants Retained ($N$) | Excluded ($N$) | Cumulative Excluded ($N$) |
| :--- | :--- | :--- | :--- | :--- |
| **1. Secondary Core Cohort** | Adult core cohort aged $\ge 20$ | **13,119** | 0 | 0 |
| **2. Complete VCTE Exam** | Exam status complete (`LUAXSTAT == 1`) | **11,604** | 1,515 | 1,515 |
| **3. Reliability Criteria** | Positive stiffness and CAP, $\ge 10$ measures and IQR/M $\le 30.0\%$ | **11,603** | 1 | 1,516 |
| **4. Valid hs-CRP** | Non-missing serum hs-CRP | **11,585** | 18 | 1,534 |

**Final Secondary Adult Core Cohort for Study 2.0:** **N = 11,585** US adults aged $\ge 20$ years.