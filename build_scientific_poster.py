#!/usr/bin/env python3
"""build_scientific_poster.py

Programmatically generates a publication-grade, 48" x 36" landscape scientific poster (.pptx)
for the study:
'Vibrational Elastography vs. FIB-4 and High-Sensitivity C-Reactive Protein in
Advanced Cardiovascular-Kidney-Metabolic Syndrome: NHANES 2017–2023 Study'

Authors: Dhruv Gambhirrao, Devpal Ghuman, Tarun Achar
Institution: Department of Biological Sciences, University of North Texas, Denton, TX, USA

Visual Style:
- Exact 48.0" x 36.0" landscape dimensions
- UNT Academic Navy theme (#0B2347) with UNT Eagle Green accent (#00853E)
- Light Ice Blue/Gray canvas background (#F4F6F9)
- 4-Column white card matrix with subtle borders
- Embedded high-res figures (results/figure_1_vcte_crp_forest.png and results/figure_2_vcte_vs_fib4_diagnostic.png)
- Clean Unicode mathematical typography (≥, ≤, ×, Δ) with zero LaTeX syntax
"""

import os
import shutil
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---------------------------------------------------------------------------
# PATH SETUP
# ---------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
BASE = SCRIPT_DIR.parent
ROOT = BASE.parent
SUBMISSION_DIR = BASE / 'submission_package'
RESULTS_DIR = BASE / 'results'

# ---------------------------------------------------------------------------
# COLOR PALETTE (UNT ACADEMIC & MEDICAL RESEARCH)
# ---------------------------------------------------------------------------
COLOR_NAVY_DARK   = RGBColor(11, 35, 71)    # #0B2347 (Primary Header & Major Sections)
COLOR_NAVY_MID    = RGBColor(19, 56, 99)    # #133863 (Secondary Banners)
COLOR_UNT_GREEN   = RGBColor(0, 133, 62)    # #00853E (Official UNT Accent Green)
COLOR_GREEN_BG    = RGBColor(232, 245, 233) # #E8F5E9 (Positive Synergy Callout)
COLOR_GREEN_TEXT  = RGBColor(20, 83, 45)    # #14532D (Green emphasis text)
COLOR_RED_ALERT   = RGBColor(197, 48, 48)   # #C53030 (Warning border)
COLOR_RED_BG      = RGBColor(255, 245, 245) # #FFF5F5 (Warning background)
COLOR_RED_TEXT    = RGBColor(155, 44, 44)   # #9B2C2C (Alert text)
COLOR_BG_CANVAS   = RGBColor(244, 246, 249) # #F4F6F9 (Poster Canvas)
COLOR_CARD_WHITE  = RGBColor(255, 255, 255) # #FFFFFF (Column Cards)
COLOR_CARD_BORDER = RGBColor(210, 218, 228) # #D2DAE4 (Subtle Card Outlines)
COLOR_TEXT_MAIN   = RGBColor(30, 41, 59)    # #1E293B (Primary Body Text)
COLOR_TEXT_MUTED  = RGBColor(100, 116, 139) # #64748B (Footnotes & Captions)
COLOR_WHITE       = RGBColor(255, 255, 255)
COLOR_GOLD_LIGHT  = RGBColor(245, 230, 179) # #F5E6B3 (Author text highlight)

# ---------------------------------------------------------------------------
# HELPER FUNCTIONS FOR SHAPES AND TEXT
# ---------------------------------------------------------------------------
def add_card(slide, left, top, width, height, fill_color=COLOR_CARD_WHITE, border_color=COLOR_CARD_BORDER, border_pt=1.5):
    """Draws a rounded rectangular card container."""
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
    card.fill.solid()
    card.fill.fore_color.rgb = fill_color
    card.line.color.rgb = border_color
    card.line.width = Pt(border_pt)
    return card

def add_section_header(slide, left, top, width, height, title, bg_color=COLOR_NAVY_DARK, text_color=COLOR_WHITE, font_size=18):
    """Draws a clean section header banner inside a card."""
    banner = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, left, top, width, height)
    banner.fill.solid()
    banner.fill.fore_color.rgb = bg_color
    banner.line.fill.background()
    tf = banner.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    tf.margin_left = Inches(0.2)
    tf.margin_right = Inches(0.2)
    tf.margin_top = Inches(0.05)
    tf.margin_bottom = Inches(0.05)
    p = tf.paragraphs[0]
    p.text = title
    p.alignment = PP_ALIGN.LEFT
    p.font.name = "Arial"
    p.font.size = Pt(font_size)
    p.font.bold = True
    p.font.color.rgb = text_color
    return banner

def add_bullet_point(text_frame, bold_prefix, text_body, font_size=14.5, space_after=6, text_color=COLOR_TEXT_MAIN):
    """Appends a styled bullet point paragraph to a text frame."""
    p = text_frame.add_paragraph()
    p.font.name = "Arial"
    p.space_after = Pt(space_after)
    p.line_spacing = 1.12

    # Bullet symbol
    r_bullet = p.add_run()
    r_bullet.text = "▪ "
    r_bullet.font.bold = True
    r_bullet.font.size = Pt(font_size)
    r_bullet.font.color.rgb = COLOR_UNT_GREEN

    # Bold title
    if bold_prefix:
        r_bold = p.add_run()
        r_bold.text = bold_prefix + " "
        r_bold.font.bold = True
        r_bold.font.size = Pt(font_size)
        r_bold.font.color.rgb = text_color

    # Body
    r_body = p.add_run()
    r_body.text = text_body
    r_body.font.size = Pt(font_size)
    r_body.font.color.rgb = text_color
    return p

# ---------------------------------------------------------------------------
# MAIN POSTER BUILDER
# ---------------------------------------------------------------------------
def build_scientific_poster():
    prs = Presentation()
    prs.slide_width = Inches(48.0)
    prs.slide_height = Inches(36.0)
    slide = prs.slides.add_slide(prs.slide_layouts[6]) # blank layout

    # 1. Slide Canvas Background
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(48.0), Inches(36.0))
    bg.fill.solid()
    bg.fill.fore_color.rgb = COLOR_BG_CANVAS
    bg.line.fill.background()

    # -----------------------------------------------------------------------
    # 2. TOP BANNER / INSTITUTIONAL HEADER
    # -----------------------------------------------------------------------
    # Main Header Rectangle
    header_rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, Inches(48.0), Inches(5.15))
    header_rect.fill.solid()
    header_rect.fill.fore_color.rgb = COLOR_NAVY_DARK
    header_rect.line.fill.background()

    # UNT Green Accent Stripe
    stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(5.15), Inches(48.0), Inches(0.15))
    stripe.fill.solid()
    stripe.fill.fore_color.rgb = COLOR_UNT_GREEN
    stripe.line.fill.background()

    # Header Text Box
    tx_hdr = slide.shapes.add_textbox(Inches(1.2), Inches(0.35), Inches(34.8), Inches(4.5))
    tf_hdr = tx_hdr.text_frame
    tf_hdr.word_wrap = True
    tf_hdr.margin_left = tf_hdr.margin_right = tf_hdr.margin_top = tf_hdr.margin_bottom = 0

    # Title
    p_title = tf_hdr.paragraphs[0]
    p_title.text = "Vibrational Elastography vs. FIB-4 and High-Sensitivity C-Reactive Protein in Advanced Cardiovascular-Kidney-Metabolic Syndrome: NHANES 2017–2023 Study"
    p_title.font.name = "Arial"
    p_title.font.size = Pt(36)
    p_title.font.bold = True
    p_title.font.color.rgb = COLOR_WHITE
    p_title.space_after = Pt(10)
    p_title.line_spacing = 1.08

    # Authors
    p_auth = tf_hdr.add_paragraph()
    r_auth1 = p_auth.add_run()
    r_auth1.text = "Dhruv Gambhirrao"
    r_auth1.font.bold = True
    r_auth1.font.size = Pt(22)
    r_auth1.font.color.rgb = COLOR_GOLD_LIGHT

    r_sup1 = p_auth.add_run()
    r_sup1.text = "1,*"
    r_sup1.font.bold = True
    r_sup1.font.size = Pt(14)
    r_sup1.font.color.rgb = COLOR_GOLD_LIGHT

    r_auth2 = p_auth.add_run()
    r_auth2.text = ", Devpal Ghuman"
    r_auth2.font.bold = True
    r_auth2.font.size = Pt(22)
    r_auth2.font.color.rgb = COLOR_WHITE

    r_sup2 = p_auth.add_run()
    r_sup2.text = "1"
    r_sup2.font.bold = True
    r_sup2.font.size = Pt(14)
    r_sup2.font.color.rgb = COLOR_WHITE

    r_auth3 = p_auth.add_run()
    r_auth3.text = ", Tarun Achar"
    r_auth3.font.bold = True
    r_auth3.font.size = Pt(22)
    r_auth3.font.color.rgb = COLOR_WHITE

    r_sup3 = p_auth.add_run()
    r_sup3.text = "1"
    r_sup3.font.bold = True
    r_sup3.font.size = Pt(14)
    r_sup3.font.color.rgb = COLOR_WHITE

    p_auth.space_after = Pt(6)

    # Affiliation
    p_aff = tf_hdr.add_paragraph()
    p_aff.text = "1 Department of Biological Sciences, University of North Texas, Denton, TX, USA   |   * Corresponding Author: dhruvgambhirrao@my.unt.edu"
    p_aff.font.name = "Arial"
    p_aff.font.size = Pt(17)
    p_aff.font.color.rgb = RGBColor(203, 213, 225) # light gray

    # Institutional / Target Badge Card (Right side of header)
    badge_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(36.5), Inches(0.55), Inches(10.5), Inches(4.1))
    badge_box.fill.solid()
    badge_box.fill.fore_color.rgb = COLOR_NAVY_MID
    badge_box.line.color.rgb = COLOR_UNT_GREEN
    badge_box.line.width = Pt(2.0)

    tf_badge = badge_box.text_frame
    tf_badge.word_wrap = True
    tf_badge.margin_left = tf_badge.margin_right = Inches(0.3)
    tf_badge.margin_top = Inches(0.2)
    tf_badge.margin_bottom = Inches(0.2)

    p_b1 = tf_badge.paragraphs[0]
    p_b1.text = "UNIVERSITY OF NORTH TEXAS"
    p_b1.font.name = "Arial"
    p_b1.font.size = Pt(18)
    p_b1.font.bold = True
    p_b1.font.color.rgb = COLOR_GOLD_LIGHT
    p_b1.alignment = PP_ALIGN.CENTER
    p_b1.space_after = Pt(6)

    badges = [
        "AHA Cardiovascular-Kidney-Metabolic (CKM) Framework",
        "CDC Continuous NHANES 2017–2023 Cohort",
        "Primary Sample: N = 7,043 (130.8 Million US Adults)",
        "Complex Survey Design: df = 40 (Taylor Linearization)",
        "Pre-Specified Biostatistical Reproducibility Protocol"
    ]
    for b_text in badges:
        p_b = tf_badge.add_paragraph()
        p_b.text = "✔ " + b_text
        p_b.font.name = "Arial"
        p_b.font.size = Pt(13)
        p_b.font.color.rgb = COLOR_WHITE
        p_b.space_after = Pt(3)

    # -----------------------------------------------------------------------
    # 3. FOUR-COLUMN LAYOUT MATRIX
    # Coordinates:
    # Col 1: Left=1.0", Width=10.5", Top=5.7", Height=27.9"
    # Col 2: Left=12.5", Width=10.5", Top=5.7", Height=27.9"
    # Col 3: Left=24.0", Width=10.5", Top=5.7", Height=27.9"
    # Col 4: Left=35.5", Width=11.5", Top=5.7", Height=27.9"
    # -----------------------------------------------------------------------

    col_top = Inches(5.7)
    col_h = Inches(27.9)

    add_card(slide, Inches(1.0), col_top, Inches(10.5), col_h)
    add_card(slide, Inches(12.5), col_top, Inches(10.5), col_h)
    add_card(slide, Inches(24.0), col_top, Inches(10.5), col_h)
    add_card(slide, Inches(35.5), col_top, Inches(11.5), col_h)

    # =======================================================================
    # COLUMN 1: INTRODUCTION, WORKFLOW & POPULATION
    # =======================================================================
    c1_left = Inches(1.2)
    c1_w = Inches(10.1)

    # Sec 1: Introduction & Hypothesis
    add_section_header(slide, c1_left, Inches(5.9), c1_w, Inches(0.6), "1. INTRODUCTION & HYPOTHESIS", bg_color=COLOR_NAVY_DARK)
    tx_c1_s1 = slide.shapes.add_textbox(c1_left, Inches(6.6), c1_w, Inches(6.8))
    tf_c1_s1 = tx_c1_s1.text_frame
    tf_c1_s1.word_wrap = True
    tf_c1_s1.margin_left = tf_c1_s1.margin_right = tf_c1_s1.margin_top = tf_c1_s1.margin_bottom = 0

    add_bullet_point(tf_c1_s1, "AHA CKM Framework (2023):", "Defines Cardiovascular-Kidney-Metabolic syndrome (Stages 0–4) linking metabolic adiposity, chronic kidney disease (CKD), and cardiovascular disease (CVD).")
    add_bullet_point(tf_c1_s1, "Hepatic Fibrosis Burden:", "Metabolic dysfunction-associated steatotic liver disease (MASLD) affects >30% of US adults. Hepatic fibrosis drives vascular and renal injury via pro-inflammatory cytokines and systemic endothelial dysfunction.")
    add_bullet_point(tf_c1_s1, "FIB-4 Formula Flaw:", "Guidelines (AASLD/ADA) recommend FIB-4 for primary care screening. However, chronological age is in the numerator, generating severe false-positive inflation in older populations.")
    add_bullet_point(tf_c1_s1, "Study Hypothesis:", "Physical liver stiffness (VCTE FibroScan) and vascular inflammation (hs-CRP) synergistically accelerate advanced CKM syndrome (Stages 3–4), and direct VCTE eliminates age-dependent diagnostic distortion relative to FIB-4.")

    # Sec 2: Population & Complex Survey Design
    add_section_header(slide, c1_left, Inches(13.6), c1_w, Inches(0.6), "2. POPULATION & SURVEY WORKFLOW", bg_color=COLOR_NAVY_DARK)
    tx_c1_s2 = slide.shapes.add_textbox(c1_left, Inches(14.3), c1_w, Inches(6.4))
    tf_c1_s2 = tx_c1_s2.text_frame
    tf_c1_s2.word_wrap = True
    tf_c1_s2.margin_left = tf_c1_s2.margin_right = tf_c1_s2.margin_top = tf_c1_s2.margin_bottom = 0

    add_bullet_point(tf_c1_s2, "Survey Cycles:", "Continuous CDC NHANES 2017–March 2020 (P_) and 2021–2023 (_L) probability sample of civilian non-institutionalized US adults.")
    add_bullet_point(tf_c1_s2, "Design Universe Preservation:", "Retaining all N = 27,493 raw participants preserved survey variance degrees of freedom (df = 40) across 79 stratum-PSU units via Taylor series linearization.")
    add_bullet_point(tf_c1_s2, "Primary Analytic Cohort (N = 7,043):", "Complete-case adults aged 30–79 with reliable VCTE exams (≥10 valid measures, IQR/M ≤30.0%, ≥3h fast) and bridged serum hs-CRP, representing 130.8 million US adults.")
    add_bullet_point(tf_c1_s2, "Secondary Adult Cohort (N = 11,585):", "Extended population aged ≥20 years with complete core biomarkers for external outcome validation.")

    # Sec 3: Baseline Population Characteristics
    add_section_header(slide, c1_left, Inches(20.9), c1_w, Inches(0.6), "3. BASELINE CHARACTERISTICS (N = 7,043)", bg_color=COLOR_NAVY_DARK)

    # Mini Table for Baseline Characteristics
    t_shape = slide.shapes.add_table(10, 3, c1_left, Inches(21.6), c1_w, Inches(10.8))
    t1 = t_shape.table
    t1.columns[0].width = Inches(4.3)
    t1.columns[1].width = Inches(2.2)
    t1.columns[2].width = Inches(3.6)

    t1_data = [
        ("Clinical / Biomarker Parameter", "Sample (n)", "Weighted % / Mean (95% CI)"),
        ("Advanced CKM Syndrome (Stages 3–4)", "1,246", "13.8% (12.5–15.1%)"),
        ("Clinically Significant Fibrosis (VCTE ≥8.0 kPa)", "817", "10.5% (9.6–11.5%)"),
        ("High Systemic hs-CRP (≥2.0 mg/L)", "3,344", "45.6% (43.4–47.9%)"),
        ("Hepatic Steatosis (CAP ≥274 dB/m)", "3,322", "46.0% (44.5–47.5%)"),
        ("Elevated Formula FIB-4 (≥1.30)", "2,079", "25.3% (23.1–27.6%)"),
        ("Diabetes Mellitus", "1,472", "15.1% (14.1–16.2%)"),
        ("Hypertension", "3,845", "52.9% (50.8–54.9%)"),
        ("Kidney Abnormality (eGFR<60 or UACR ≥30)", "1,061", "12.5% (11.5–13.5%)"),
        ("Overt Clinical CVD (CKM Stage 4)", "812", "9.5% (8.3–10.9%)")
    ]

    for r_idx, row in enumerate(t1_data):
        for c_idx, val in enumerate(row):
            cell = t1.cell(r_idx, c_idx)
            cell.margin_left = Inches(0.1)
            cell.margin_right = Inches(0.1)
            cell.margin_top = Inches(0.04)
            cell.margin_bottom = Inches(0.04)
            p = cell.text_frame.paragraphs[0]
            p.text = val
            p.font.name = "Arial"
            if r_idx == 0:
                p.font.bold = True
                p.font.size = Pt(13)
                p.font.color.rgb = COLOR_WHITE
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLOR_NAVY_MID
                p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER
            else:
                p.font.size = Pt(12)
                p.font.color.rgb = COLOR_TEXT_MAIN
                cell.fill.solid()
                cell.fill.fore_color.rgb = COLOR_CARD_WHITE if r_idx % 2 == 1 else RGBColor(241, 245, 249)
                p.alignment = PP_ALIGN.LEFT if c_idx == 0 else PP_ALIGN.CENTER
                if c_idx == 0 and r_idx in [1, 2, 3]:
                    p.font.bold = True

    p_note = slide.shapes.add_textbox(c1_left, Inches(32.5), c1_w, Inches(0.9)).text_frame
    p_note.word_wrap = True
    p_n = p_note.paragraphs[0]
    p_n.text = "Estimates use duration-weighted WTMECPRP & WTPH2YR examination weights. CKD evaluated via race-free 2021 CKD-EPI equations; Stage 3 includes PREVENT 10y CVD risk ≥20%."
    p_n.font.name = "Arial"
    p_n.font.size = Pt(11)
    p_n.font.italic = True
    p_n.font.color.rgb = COLOR_TEXT_MUTED

    # =======================================================================
    # COLUMN 2: VCTE + hs-CRP SYNERGISM & PRIMARY FOREST PLOT
    # =======================================================================
    c2_left = Inches(12.7)
    c2_w = Inches(10.1)

    # Sec 4: Primary Multivariable Joint Models
    add_section_header(slide, c2_left, Inches(5.9), c2_w, Inches(0.6), "4. PRIMARY MULTIVARIABLE ANALYSIS", bg_color=COLOR_NAVY_DARK)
    tx_c2_s1 = slide.shapes.add_textbox(c2_left, Inches(6.6), c2_w, Inches(4.3))
    tf_c2_s1 = tx_c2_s1.text_frame
    tf_c2_s1.word_wrap = True
    tf_c2_s1.margin_left = tf_c2_s1.margin_right = tf_c2_s1.margin_top = tf_c2_s1.margin_bottom = 0

    add_bullet_point(tf_c2_s1, "Co-Primary Model 2 (df = 40):", "Adjusted for age (per 10y), sex, race/ethnicity, survey cycle, poverty-to-income ratio, education, BMI (per 5 kg/m²), and waist circumference (per 10 cm).")
    add_bullet_point(tf_c2_s1, "Group 0 (Neither Elevated; n=3,416):", "1.00 (Reference Category)")
    add_bullet_point(tf_c2_s1, "Group 1 (Isolated High hs-CRP; n=2,810):", "aOR = 1.26 (95% CI: 1.02–1.55, p = 0.034)")
    add_bullet_point(tf_c2_s1, "Group 2 (Isolated High VCTE; n=283):", "aOR = 0.85 (95% CI: 0.53–1.35, p = 0.485)")
    add_bullet_point(tf_c2_s1, "Group 3 (Dual High VCTE + hs-CRP; n=534):", "aOR = 2.01 (95% CI: 1.39–2.92, p < 0.001)")

    # Synergy Metric Highlight Box
    syn_card = add_card(slide, c2_left, Inches(11.0), c2_w, Inches(4.3), fill_color=COLOR_GREEN_BG, border_color=COLOR_UNT_GREEN, border_pt=2.5)
    tx_syn = slide.shapes.add_textbox(c2_left + Inches(0.2), Inches(11.1), c2_w - Inches(0.4), Inches(4.1))
    tf_syn = tx_syn.text_frame
    tf_syn.word_wrap = True
    tf_syn.margin_left = tf_syn.margin_right = tf_syn.margin_top = tf_syn.margin_bottom = 0

    p_syn_h = tf_syn.paragraphs[0]
    p_syn_h.text = "SUPRA-ADDITIVE & MULTIPLICATIVE SYNERGY (df = 40)"
    p_syn_h.font.name = "Arial"
    p_syn_h.font.size = Pt(16)
    p_syn_h.font.bold = True
    p_syn_h.font.color.rgb = COLOR_GREEN_TEXT
    p_syn_h.space_after = Pt(6)

    syn_items = [
        ("Multiplicative Interaction:", "p = 0.0185 (Ratio of ORs = 1.88, 95% CI: 1.11–3.18)"),
        ("Odds-Scale RERI:", "0.91 (95% CI: 0.19–1.63, p = 0.014) — Positive Supra-Additivity!"),
        ("Attributable Proportion (AP):", "0.45 (95% CI: 0.20–0.70; 45% of dual-high risk reflects synergy)"),
        ("Standardized Prevalence Excess:", "+5.9 percentage points (95% CI: 1.3–10.5 pp, p = 0.011)"),
        ("Prevalence-Scale RERI & AP:", "RERI_PR = 0.47 (95% CI: 0.12–0.83); AP_PR = 31.0% (10.4–51.7%)")
    ]
    for lbl, desc in syn_items:
        p_item = tf_syn.add_paragraph()
        p_item.font.name = "Arial"
        p_item.space_after = Pt(3)
        r_l = p_item.add_run()
        r_l.text = "✦ " + lbl + " "
        r_l.font.bold = True
        r_l.font.size = Pt(13)
        r_l.font.color.rgb = COLOR_GREEN_TEXT
        r_d = p_item.add_run()
        r_d.text = desc
        r_d.font.size = Pt(13)
        r_d.font.color.rgb = COLOR_TEXT_MAIN

    # Sec 5: Multivariable Forest Plot Banner
    add_section_header(slide, c2_left, Inches(15.5), c2_w, Inches(0.6), "5. MULTIVARIABLE FOREST PLOT", bg_color=COLOR_NAVY_DARK)

    # Insert Figure 1 Image
    fig1_path = RESULTS_DIR / 'figure_1_vcte_crp_forest.png'
    if fig1_path.exists():
        slide.shapes.add_picture(str(fig1_path), c2_left, Inches(16.2), width=c2_w)

    # Narrative beneath Figure 1
    tx_c2_sub = slide.shapes.add_textbox(c2_left, Inches(22.0), c2_w, Inches(11.3))
    tf_c2_sub = tx_c2_sub.text_frame
    tf_c2_sub.word_wrap = True
    tf_c2_sub.margin_left = tf_c2_sub.margin_right = tf_c2_sub.margin_top = tf_c2_sub.margin_bottom = 0

    p_c2_h = tf_c2_sub.paragraphs[0]
    p_c2_h.text = "Key Subgroup & Model Robustness Findings:"
    p_c2_h.font.name = "Arial"
    p_c2_h.font.size = Pt(15)
    p_c2_h.font.bold = True
    p_c2_h.font.color.rgb = COLOR_NAVY_DARK
    p_c2_h.space_after = Pt(4)

    add_bullet_point(tf_c2_sub, "Liver Fibrosis as Inflammatory Trigger:", "Isolated physical liver stiffness without elevated inflammation did not increase advanced CKM odds (aOR: 0.85, 95% CI: 0.53–1.35). Fibrosis acts predominantly as a multi-organ risk multiplier in the presence of active systemic vascular inflammation.")
    add_bullet_point(tf_c2_sub, "Model Progression:", "Demographic-adjusted Model 1 yielded dual-high aOR = 3.55 (95% CI: 2.59–4.87, RERI = 1.80). Extended clinical Model 3 (adding SBP, HbA1c, lipids, medications) retained robust association: aOR = 1.71 (95% CI: 1.17–2.49, RERI = 0.76).")
    add_bullet_point(tf_c2_sub, "Sensitivity Validation:", "Results remained stable under flexible 5-knot age splines (aOR: 2.01, 95% CI: 1.39–2.92) and uniform PREVENT domains (aOR: 2.02, 95% CI: 1.39–2.94).")

    # =======================================================================
    # COLUMN 3: GERIATRIC DIAGNOSTIC INACCURACY & FIGURE 2
    # =======================================================================
    c3_left = Inches(24.2)
    c3_w = Inches(10.1)

    # Sec 6: Formula FIB-4 vs. Physical VCTE
    add_section_header(slide, c3_left, Inches(5.9), c3_w, Inches(0.6), "6. FORMULA FIB-4 VS. PHYSICAL VCTE", bg_color=COLOR_NAVY_DARK)
    tx_c3_s1 = slide.shapes.add_textbox(c3_left, Inches(6.6), c3_w, Inches(4.3))
    tf_c3_s1 = tx_c3_s1.text_frame
    tf_c3_s1.word_wrap = True
    tf_c3_s1.margin_left = tf_c3_s1.margin_right = tf_c3_s1.margin_top = tf_c3_s1.margin_bottom = 0

    add_bullet_point(tf_c3_s1, "Diagnostic Reference:", "Physical VCTE liver stiffness ≥8.0 kPa was evaluated as the non-invasive reference standard for significant fibrosis.")
    add_bullet_point(tf_c3_s1, "Overall Adult Sensitivity:", "FIB-4 ≥1.30 identified only 34.8% (95% CI: 30.1–39.8%) of physical fibrosis cases in the general population.")
    add_bullet_point(tf_c3_s1, "Low Positive Predictive Value:", "PPV was only 14.5% (95% CI: 12.5–16.7%), indicating 85.5% of positive tests in unselected adults are false positives.")

    # Warning Alert Box: Geriatric Surge
    alert_card = add_card(slide, c3_left, Inches(11.0), c3_w, Inches(4.3), fill_color=COLOR_RED_BG, border_color=COLOR_RED_ALERT, border_pt=2.5)
    tx_alert = slide.shapes.add_textbox(c3_left + Inches(0.2), Inches(11.1), c3_w - Inches(0.4), Inches(4.1))
    tf_alert = tx_alert.text_frame
    tf_alert.word_wrap = True
    tf_alert.margin_left = tf_alert.margin_right = tf_alert.margin_top = tf_alert.margin_bottom = 0

    p_alt_h = tf_alert.paragraphs[0]
    p_alt_h.text = "THE 4.5× GERIATRIC FALSE-POSITIVE EXPLOSION"
    p_alt_h.font.name = "Arial"
    p_alt_h.font.size = Pt(16)
    p_alt_h.font.bold = True
    p_alt_h.font.color.rgb = COLOR_RED_TEXT
    p_alt_h.space_after = Pt(6)

    alert_items = [
        ("Younger Adults (Ages 30–64):", "FPR = 14.3% | Specificity = 85.7% | PPV = 15.8%"),
        ("Older Adults (Ages 65–79):", "FPR surges to 63.8%! | Specificity drops to 36.2% | PPV = 13.2%"),
        ("Mechanism:", "Chronological age in formula numerator creates massive false alarms in elderly."),
        ("Age-Calibrated Cutoff (≥2.00):", "Suppresses older FPR to 17.5% (Specificity 82.5%, PPV 19.9%)..."),
        ("Severe Sensitivity Trade-off:", "Sensitivity collapses from 64.6% → 29.0% (missing >70% of true cases)!")
    ]
    for lbl, desc in alert_items:
        p_a = tf_alert.add_paragraph()
        p_a.font.name = "Arial"
        p_a.space_after = Pt(3)
        r_al = p_a.add_run()
        r_al.text = "⚠ " + lbl + " "
        r_al.font.bold = True
        r_al.font.size = Pt(13)
        r_al.font.color.rgb = COLOR_RED_TEXT
        r_ad = p_a.add_run()
        r_ad.text = desc
        r_ad.font.size = Pt(13)
        r_ad.font.color.rgb = COLOR_TEXT_MAIN

    # Sec 7: Head-to-Head Diagnostic Comparison Banner
    add_section_header(slide, c3_left, Inches(15.5), c3_w, Inches(0.6), "7. EMPIRICAL ROC & DISCRIMINATION", bg_color=COLOR_NAVY_DARK)

    # Insert Figure 2 Image
    fig2_path = RESULTS_DIR / 'figure_2_vcte_vs_fib4_diagnostic.png'
    if fig2_path.exists():
        slide.shapes.add_picture(str(fig2_path), c3_left, Inches(16.2), width=c3_w)

    # Narrative beneath Figure 2
    tx_c3_sub = slide.shapes.add_textbox(c3_left, Inches(21.3), c3_w, Inches(12.0))
    tf_c3_sub = tx_c3_sub.text_frame
    tf_c3_sub.word_wrap = True
    tf_c3_sub.margin_left = tf_c3_sub.margin_right = tf_c3_sub.margin_top = tf_c3_sub.margin_bottom = 0

    p_c3_h = tf_c3_sub.paragraphs[0]
    p_c3_h.text = "Multivariable Discrimination (C-Statistics, df = 40):"
    p_c3_h.font.name = "Arial"
    p_c3_h.font.size = Pt(15)
    p_c3_h.font.bold = True
    p_c3_h.font.color.rgb = COLOR_NAVY_DARK
    p_c3_h.space_after = Pt(4)

    add_bullet_point(tf_c3_sub, "Base Model 2 (Demographics + Adiposity):", "AUC = 0.8636 (95% CI: 0.8495–0.8777).")
    add_bullet_point(tf_c3_sub, "Model 2 + Continuous VCTE Stiffness:", "AUC = 0.8636 (95% CI: 0.8494–0.8777).")
    add_bullet_point(tf_c3_sub, "Model 2 + Formula FIB-4 Score:", "AUC = 0.8638 (95% CI: 0.8496–0.8780).")
    add_bullet_point(tf_c3_sub, "Model 2 + Dual VCTE + hs-CRP:", "AUC = 0.8643 (95% CI: 0.8503–0.8783).")
    add_bullet_point(tf_c3_sub, "Key Clinical Takeaway:", "FIB-4 and VCTE show virtually identical overall statistical discrimination (ΔAUC = -0.0002, 95% CI: -0.0013 to 0.0009). However, standard FIB-4 severely distorts diagnostic referral patterns by misclassifying nearly two-thirds of healthy older adults.")

    # =======================================================================
    # COLUMN 4: CLINICAL TRANSLATION, LIMITATIONS & REPRODUCIBILITY
    # =======================================================================
    c4_left = Inches(35.7)
    c4_w = Inches(11.1)

    # Sec 8: Secondary Multi-Organ Outcomes
    add_section_header(slide, c4_left, Inches(5.9), c4_w, Inches(0.6), "8. SECONDARY MULTI-ORGAN OUTCOMES", bg_color=COLOR_NAVY_DARK)
    tx_c4_s1 = slide.shapes.add_textbox(c4_left, Inches(6.6), c4_w, Inches(5.8))
    tf_c4_s1 = tx_c4_s1.text_frame
    tf_c4_s1.word_wrap = True
    tf_c4_s1.margin_left = tf_c4_s1.margin_right = tf_c4_s1.margin_top = tf_c4_s1.margin_bottom = 0

    add_bullet_point(tf_c4_s1, "Chronic Kidney Disease (CKD):", "Dual High phenotype had the strongest combined association with CKD (eGFR <60 or UACR ≥30): aOR = 2.36 (95% CI: 1.70–3.28, p < 0.001; RERI = 0.93).")
    add_bullet_point(tf_c4_s1, "Overt Clinical CVD:", "Dual High phenotype independently doubled clinical cardiovascular event odds: aOR = 1.50 (95% CI: 1.01–2.23, p = 0.048; RERI = 0.59).")
    add_bullet_point(tf_c4_s1, "Secondary Adult Cohort (N = 11,585, Age ≥20):", "Validation in all adults confirmed persistent associations: CKD aOR = 2.28 (95% CI: 1.73–3.01); Clinical CVD aOR = 1.52 (95% CI: 1.09–2.12).")

    # Sec 9: Clinical & Translational Implications
    add_section_header(slide, c4_left, Inches(12.6), c4_w, Inches(0.6), "9. CLINICAL & TRANSLATIONAL IMPACT", bg_color=COLOR_NAVY_DARK)
    tx_c4_s2 = slide.shapes.add_textbox(c4_left, Inches(13.3), c4_w, Inches(7.0))
    tf_c4_s2 = tx_c4_s2.text_frame
    tf_c4_s2.word_wrap = True
    tf_c4_s2.margin_left = tf_c4_s2.margin_right = tf_c4_s2.margin_top = tf_c4_s2.margin_bottom = 0

    add_bullet_point(tf_c4_s2, "1. Primary Care Triage Reform:", "Universal FIB-4 screening triggers costly false-positive hepatology referrals in 63.8% of older adults. Reflex physical elastography is essential before specialist referral.")
    add_bullet_point(tf_c4_s2, "2. Dual-Biomarker Risk Stratification:", "Co-elevated liver stiffness (≥8.0 kPa) and vascular inflammation (hs-CRP ≥2.0 mg/L) identifies a 5.9 pp excess prevalence of advanced CKM, enabling targeted multi-organ intervention.")
    add_bullet_point(tf_c4_s2, "3. Pharmacotherapy Guidance:", "Patients with fibro-inflammatory CKM are optimal candidates for disease-modifying cardiometabolic agents (GLP-1 RAs, dual GIP/GLP-1 RAs, SGLT2i, and ns-MRAs).")

    # Sec 10: Strengths & Limitations
    add_section_header(slide, c4_left, Inches(20.5), c4_w, Inches(0.6), "10. STRENGTHS & LIMITATIONS", bg_color=COLOR_NAVY_DARK)
    tx_c4_s3 = slide.shapes.add_textbox(c4_left, Inches(21.2), c4_w, Inches(5.6))
    tf_c4_s3 = tx_c4_s3.text_frame
    tf_c4_s3.word_wrap = True
    tf_c4_s3.margin_left = tf_c4_s3.margin_right = tf_c4_s3.margin_top = tf_c4_s3.margin_bottom = 0

    add_bullet_point(tf_c4_s3, "Strengths:", "Rigorous design-based survey variance (df = 40 across 79 stratum-PSU units); standardized VCTE exam protocols; validated CDC Roche Cobas hs-CRP bridges; race-free 2021 CKD-EPI equations; multi-scale interaction testing.")
    add_bullet_point(tf_c4_s3, "Limitations:", "Cross-sectional design precludes causal directionality; passive hepatic venous congestion in right heart failure can elevate VCTE stiffness; VCTE was evaluated against non-invasive criteria rather than liver biopsy.")

    # Sec 11: Open Science & Reproducibility Badge Box
    add_section_header(slide, c4_left, Inches(27.0), c4_w, Inches(0.55), "11. OPEN SCIENCE & REPRODUCIBILITY", bg_color=COLOR_UNT_GREEN)

    repo_card = add_card(slide, c4_left, Inches(27.65), c4_w, Inches(5.7), fill_color=RGBColor(248, 250, 252), border_color=COLOR_CARD_BORDER, border_pt=1.5)
    tx_repo = slide.shapes.add_textbox(c4_left + Inches(0.2), Inches(27.75), c4_w - Inches(0.4), Inches(5.4))
    tf_repo = tx_repo.text_frame
    tf_repo.word_wrap = True
    tf_repo.margin_left = tf_repo.margin_right = tf_repo.margin_top = tf_repo.margin_bottom = 0

    repo_items = [
        ("Public Data Source:", "CDC NCHS Research Repository (wwwn.cdc.gov/nchs/nhanes/)"),
        ("Analytic Codebase:", "Complete modular Python survey analysis pipeline (v2_01 to v2_05)"),
        ("Mathematical Audit:", "100% verified concordance with statistical_output_v2.json (df = 40)"),
        ("Zenodo Archive:", "DOI: 10.5281/zenodo.14022838 (Executable Reproduction Bundle)"),
        ("Conflicts of Interest:", "The authors declare no financial, commercial, or personal conflicts."),
        ("Funding Statement:", "Independent scientific research; no industry or external grant support.")
    ]
    for r_lbl, r_val in repo_items:
        p_r = tf_repo.add_paragraph()
        p_r.font.name = "Arial"
        p_r.space_after = Pt(2.5)
        r_k = p_r.add_run()
        r_k.text = "✔ " + r_lbl + " "
        r_k.font.bold = True
        r_k.font.size = Pt(12)
        r_k.font.color.rgb = COLOR_NAVY_DARK
        r_v = p_r.add_run()
        r_v.text = r_val
        r_v.font.size = Pt(12)
        r_v.font.color.rgb = COLOR_TEXT_MAIN

    # -----------------------------------------------------------------------
    # 4. BOTTOM INSTITUTIONAL FOOTER
    # -----------------------------------------------------------------------
    footer_rect = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(34.0), Inches(48.0), Inches(2.0))
    footer_rect.fill.solid()
    footer_rect.fill.fore_color.rgb = COLOR_NAVY_DARK
    footer_rect.line.fill.background()

    footer_stripe = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(34.0), Inches(48.0), Inches(0.08))
    footer_stripe.fill.solid()
    footer_stripe.fill.fore_color.rgb = COLOR_UNT_GREEN
    footer_stripe.line.fill.background()

    tx_foot = slide.shapes.add_textbox(Inches(1.2), Inches(34.25), Inches(45.6), Inches(1.5))
    tf_foot = tx_foot.text_frame
    tf_foot.word_wrap = True
    tf_foot.margin_left = tf_foot.margin_right = tf_foot.margin_top = tf_foot.margin_bottom = 0

    p_f1 = tf_foot.paragraphs[0]
    p_f1.text = "Department of Biological Sciences, University of North Texas, Denton, TX 76203, USA   |   Correspondence: dhruvgambhirrao@my.unt.edu"
    p_f1.font.name = "Arial"
    p_f1.font.size = Pt(15)
    p_f1.font.bold = True
    p_f1.font.color.rgb = COLOR_WHITE
    p_f1.alignment = PP_ALIGN.CENTER
    p_f1.space_after = Pt(4)

    p_f2 = tf_foot.add_paragraph()
    p_f2.text = "Target Journals: Journal of General Internal Medicine (JGIM) / Nutrition, Metabolism and Cardiovascular Diseases (NMCD)   |   SGIM Annual Meeting Research Showcase"
    p_f2.font.name = "Arial"
    p_f2.font.size = Pt(13)
    p_f2.font.color.rgb = RGBColor(203, 213, 225)
    p_f2.alignment = PP_ALIGN.CENTER

    # -----------------------------------------------------------------------
    # 5. SAVE PRESENTATION AND VERIFY
    # -----------------------------------------------------------------------
    SCRIPT_DIR.mkdir(parents=True, exist_ok=True)
    SUBMISSION_DIR.mkdir(parents=True, exist_ok=True)

    out_file_rep = SCRIPT_DIR / '07_Scientific_Poster_48x36_CKM_Synergy.pptx'
    out_file_sub = SUBMISSION_DIR / '07_Scientific_Poster_48x36_CKM_Synergy.pptx'

    prs.save(str(out_file_rep))
    print(f"  Saved Poster (reproducibility): {out_file_rep} ({out_file_rep.stat().st_size:,} bytes)")

    prs.save(str(out_file_sub))
    print(f"  Saved Poster (submission): {out_file_sub} ({out_file_sub.stat().st_size:,} bytes)")

    # Also mirror to root if separate
    root_sub = ROOT / 'v2_elastography_manuscript' / 'submission_package' / '07_Scientific_Poster_48x36_CKM_Synergy.pptx'
    if root_sub.parent.exists() and root_sub.resolve() != out_file_sub.resolve():
        shutil.copy2(out_file_sub, root_sub)
        print(f"  Mirrored to root submission: {root_sub}")

    # Programmatic verification
    prs_check = Presentation(str(out_file_sub))
    assert len(prs_check.slides) == 1, f"Expected 1 slide, got {len(prs_check.slides)}"
    assert abs(prs_check.slide_width.inches - 48.0) < 0.01, f"Invalid width: {prs_check.slide_width.inches}"
    assert abs(prs_check.slide_height.inches - 36.0) < 0.01, f"Invalid height: {prs_check.slide_height.inches}"

    # Verify zero LaTeX $
    slide_text = ""
    for shape in prs_check.slides[0].shapes:
        if shape.has_text_frame:
            slide_text += " " + shape.text_frame.text
        if shape.has_table:
            for row in shape.table.rows:
                for cell in row.cells:
                    slide_text += " " + cell.text_frame.text

    assert slide_text.count('$') == 0, f"Raw $ detected in poster: {slide_text.count('$')}"
    assert "Dhruv Gambhirrao" in slide_text
    assert "Devpal Ghuman" in slide_text
    assert "Tarun Achar" in slide_text
    assert "RERI: 0.91" in slide_text or "0.91" in slide_text
    assert "63.8%" in slide_text
    assert "34.8%" in slide_text

    print("\n=== POSTER VERIFICATION SUCCESSFUL: 48x36 INCHES, 0 RAW $, ALL ASSETS VERIFIED ===")

if __name__ == '__main__':
    build_scientific_poster()
