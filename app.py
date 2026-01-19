# app.py
# Amberstone – Client Risk Profiler (Theme #1: Dark / Institutional)
# COMPLETE FULL APP (no missing sections)
#
# Key request implemented:
# - Divider under nav buttons is VERY TIGHT using correct Streamlit selector:
#   div[data-testid="stMarkdown"] > hr { margin-top/bottom ... !important; }
#
# Also kept:
# - Header top edge visible
# - Reduced nav-to-divider gap
# - Questions font larger than answers (radio/selectbox/checkbox)
# - PDF logo uses Logo_orange.png ONLY; UI uses Logo_white.png
# - PDF logo shifted slightly left + ~40% more space under logo
# - Results page includes: Summary, Export, Allocation Caps, Alternatives gating, Robustness, File note

import base64
from pathlib import Path
from datetime import datetime
from io import BytesIO

import streamlit as st

# PDF
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(page_title="Amberstone – Client Risk Profiler", layout="wide")

# ============================================================
# THEME CONSTANTS (Theme #1 – Dark)
# ============================================================
BG = "#0e1117"
PANEL = "#121721"
PANEL_2 = "#0f1520"
BORDER = "#1f2430"
TEXT = "#f2f2f2"
MUTED = "#b9c0cc"
DIVIDER = "#2a2f3a"
ACCENT = "#D2A679"

# ============================================================
# LOGO FILES
# ============================================================
UI_LOGO_FILE = "Logo_white.png"      # UI header logo
PDF_LOGO_FILE = "Logo_orange.png"    # PDF-only logo

# ============================================================
# HELPERS
# ============================================================
def load_logo_base64(filename: str) -> str | None:
    p = Path(filename)
    if not p.exists():
        return None
    return base64.b64encode(p.read_bytes()).decode("utf-8")

def load_logo_for_pdf(filename: str):
    p = Path(filename)
    if not p.exists():
        return None
    return ImageReader(str(p))

def wrap_text_to_lines(text: str, max_chars: int) -> list[str]:
    words = (text or "").split()
    lines, cur = [], ""
    for w in words:
        if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
            cur = f"{cur} {w}".strip()
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

# ============================================================
# PDF EXPORT (PDF LOGO = Logo_orange.png ONLY)
# - logo x shifted left by 2mm
# - vertical spacing under logo increased by ~40%
# ============================================================
def build_pdf_bytes(results: dict, firm_name: str = "Amberstone Capital", logo_file: str = PDF_LOGO_FILE) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    left = 18 * mm
    right = 18 * mm
    top = height - 18 * mm
    y = top

    def gap(mult=1.0):
        nonlocal y
        y -= 6 * mm * mult

    def rule():
        nonlocal y
        c.setLineWidth(0.7)
        c.line(left, y, width - right, y)
        gap(0.9)

    def title(txt):
        nonlocal y
        c.setFont("Helvetica-Bold", 16)
        c.drawString(left, y, txt)
        gap(1.2)

    def h2(txt):
        nonlocal y
        c.setFont("Helvetica-Bold", 11.5)
        c.drawString(left, y, txt)
        gap(0.9)

    def kv(key, value):
        nonlocal y
        c.setFont("Helvetica-Bold", 10)
        c.drawString(left, y, f"{key}:")
        c.setFont("Helvetica", 10)
        c.drawString(left + 55 * mm, y, str(value))
        gap(0.9)

    def para(txt, max_chars=110):
        nonlocal y
        c.setFont("Helvetica", 10)
        for ln in wrap_text_to_lines(txt, max_chars=max_chars):
            c.drawString(left, y, ln)
            gap(0.75)
        gap(0.25)

    # --- Logo (PDF-only) ---
    logo = load_logo_for_pdf(logo_file)
    if logo:
        logo_w = 42 * mm
        logo_h = 16 * mm
        logo_x = left - (2 * mm)
        c.drawImage(logo, logo_x, y - logo_h, width=logo_w, height=logo_h, mask="auto")
        y -= (logo_h + 8.4 * mm)  # ~40% more than 6mm
    else:
        gap(0.8)

    # Header
    title("Client Risk Profile Summary")
    c.setFont("Helvetica", 10)
    c.drawString(left, y, firm_name)
    c.drawRightString(width - right, y, datetime.now().strftime("%Y-%m-%d %H:%M"))
    gap(1.1)
    rule()

    # Summary
    h2("Summary")
    kv("Risk attitude score", f"{results['risk_attitude_score']}/100")
    kv("Risk attitude category", results["risk_attitude_band"])
    kv("Capacity for loss", results["capacity_band"])
    kv("Capacity points", f"{results['cap_points']}/30")
    kv("Capacity policy cap", results["capacity_max_allowed_band"])
    kv("Final risk category", results["final_band"])
    kv("Capacity override applied", "Yes" if results["override_applied"] else "No")
    rule()

    # Allocation caps
    h2("Allocation Caps")
    base_limits = results["base_limits"]
    final_limits = results["final_limits"]

    kv("Base Max Equity", f"{base_limits['max_equity']}%")
    kv("Base Max Sukuk", f"{base_limits['max_sukuk']}%")
    kv("Base Max Alternatives", f"{base_limits['max_alternatives']}%")
    gap(0.2)
    kv("Final Max Equity", f"{final_limits['max_equity']}%")
    kv("Final Max Sukuk", f"{final_limits['max_sukuk']}%")
    kv("Final Max Alternatives", f"{final_limits['max_alternatives']}%")

    if results["alt_forced_zero_reasons"]:
        gap(0.2)
        h2("Alternatives Gating")
        para("Alternatives were gated to 0% due to:")
        for r in results["alt_forced_zero_reasons"]:
            para(f"• {r}", max_chars=110)

    rule()

    # Robustness
    h2("Robustness Checks")
    if results["flags"]:
        para("Flags:")
        for f in results["flags"]:
            para(f"• {f}", max_chars=110)
    else:
        para("No robustness flags triggered.")
    rule()

    # Capacity inputs
    h2("Capacity Inputs")
    cap = results["capacity_inputs"]
    kv("Emergency fund", cap["emergency_months"])
    kv("Income stability", cap["income_stability"])
    kv("Withdrawal likelihood (3y)", cap["withdrawal_need"])
    kv("Debt burden", cap["debt_burden"])
    kv("Portfolio dependence (3–5y)", cap["portfolio_dependence"])
    rule()

    # Footer disclaimer
    c.setFont("Helvetica-Oblique", 9)
    disclaimer = (
        "Internal advisory tool only. This document provides risk profiling information, not investment advice. "
        "Final suitability decisions rest with the adviser."
    )
    for ln in wrap_text_to_lines(disclaimer, max_chars=120):
        c.drawString(left, y, ln)
        gap(0.7)

    c.showPage()
    c.save()
    return buf.getvalue()

# ============================================================
# CSS – Theme #1 + very tight divider under nav
# ============================================================
st.markdown(
    f"""
    <style>
      .stApp {{
        background-color: {BG};
        color: {TEXT};
      }}

      /* Show top edge of header reliably */
      .block-container {{
        max-width: 1040px;
        padding-top: 3.0rem !important;
        padding-left: 1.2rem !important;
        padding-right: 1.2rem !important;
        margin: 0 auto;
      }}

      html, body, p, div, span, label, li {{
        color: {TEXT};
      }}
      .stCaption, small {{
        color: {MUTED} !important;
      }}

      /* IMPORTANT: Streamlit divider from st.markdown('---') is a <hr> inside stMarkdown.
         Make it VERY tight. This is the correct selector that actually works. */
      div[data-testid="stMarkdown"] > hr {{
        border: none;
        border-top: 1px solid {DIVIDER};
        margin-top: 0.10rem !important;
        margin-bottom: 0.10rem !important;
      }}

      .amber-header {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 18px;
        padding: 1.35rem 1.35rem;
        margin-top: 0.2rem;
        margin-bottom: 0.35rem;   /* tighter to nav */
      }}

      .amber-title {{
        color: {TEXT};
        font-size: 2.4rem;
        font-weight: 750;
        margin: 0;
        line-height: 1.12;
      }}

      .amber-subtitle {{
        color: {MUTED};
        font-size: 1.15rem;
        margin-top: 0.45rem;
      }}

      .accent-line {{
        height: 3px;
        width: 100%;
        background: {ACCENT};
        border-radius: 999px;
        margin-top: 0.8rem;
        opacity: 0.85;
      }}

      .card {{
        background: {PANEL_2};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 1.1rem 1.1rem;
      }}

      /* Summary cards */
      .summary-grid {{
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }}
      @media (max-width: 900px) {{
        .summary-grid {{ grid-template-columns: 1fr; }}
      }}
      .summary-card {{
        background: {PANEL};
        border: 1px solid {BORDER};
        border-radius: 16px;
        padding: 1rem 1rem;
      }}
      .summary-label {{
        color: {MUTED};
        font-size: 0.95rem;
        margin-bottom: 0.35rem;
      }}
      .summary-value {{
        color: {TEXT};
        font-size: 1.55rem;
        font-weight: 700;
        line-height: 1.25;
        word-break: break-word;
        overflow-wrap: anywhere;
        white-space: normal;
      }}

      /* Questionnaire: questions > answers */
      div[data-testid="stRadio"] > label,
      div[data-testid="stSelectbox"] > label,
      div[data-testid="stCheckbox"] > label {{
        font-size: 1.90rem !important;
        font-weight: 700 !important;
        line-height: 1.99 !important;
      }}
      div[data-testid="stRadio"] div[role="radiogroup"] {{
        justify-content: center;
      }}
      div[data-testid="stRadio"] div[role="radiogroup"] label span {{
        font-size: 1.10rem !important;
        font-weight: 550 !important;
        white-space: nowrap !important;
      }}
      div[data-testid="stSelectbox"] div[role="button"] {{
        font-size: 1.10rem !important;
      }}

      /* Nav buttons: compact and subtle */
      .navbtn button {{
        background: transparent !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
        border-radius: 12px !important;
        padding-top: 0.35rem !important;
        padding-bottom: 0.35rem !important;
      }}
      .navbtn button:hover {{
        background: {PANEL} !important;
      }}

      /* Primary buttons (submit/download) */
      button[kind="primary"] {{
        background-color: #1f2a44 !important;
        color: {TEXT} !important;
        border: 1px solid #2f3b5c !important;
        border-radius: 12px !important;
      }}
      button[kind="primary"]:hover {{
        background-color: #26335a !important;
      }}


      /* --- Responsive header (Option 2: mobile-friendly but consistent branding) --- */
      .amber-header .header-row {{
        display: flex;
        align-items: center;
        gap: 18px;
        flex-wrap: nowrap;
      }}

      .amber-header .brand-logo {{
        width: clamp(110px, 18vw, 145px);
        min-width: 110px;
        height: auto;
        flex: 0 0 auto;
      }}

      .amber-header .brand-text {{
        flex: 1 1 auto;
        min-width: 0;
      }}

      .amber-header .brand-subtitle {{
        white-space: normal;
      }}

      @media (max-width: 600px) {{
        .amber-header {{
          padding: 1.1rem 1.1rem;
        }}
        .amber-header .header-row {{
          gap: 12px;
        }}
        .amber-header .brand-logo {{
          width: 120px;
          min-width: 120px;
        }}
        .amber-title {{
          font-size: 1.85rem;
          line-height: 1.1;
        }}
        .amber-subtitle {{
          font-size: 1.0rem;
          margin-top: 0.25rem;
        }}
      }}
    
      /* =========================================================
         FORCE APP LOOK CONSISTENT REGARDLESS OF BROWSER THEME
         (prevents white/pale text on white backgrounds)
         ========================================================= */

      :root {{
        color-scheme: dark;
      }}

      /* Selectbox closed field: force dark background and light text */
      div[data-testid="stSelectbox"] div[role="button"] {{
        background: {PANEL_2} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
      }}

      /* Placeholder/value inside selectbox */
      div[data-testid="stSelectbox"] div[role="button"] span {{
        color: {TEXT} !important;
        opacity: 1 !important;
      }}

      /* Dropdown list container */
      div[role="listbox"] {{
        background: {PANEL} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
      }}

      /* Dropdown options + nested text */
      div[role="option"], div[role="option"] * {{
        background: {PANEL} !important;
        color: {TEXT} !important;
        opacity: 1 !important;
      }}

      /* Hover option */
      div[role="option"]:hover, div[role="option"]:hover * {{
        background: {PANEL_2} !important;
        color: {TEXT} !important;
        opacity: 1 !important;
      }}

      /* Keep widget question labels bright (prevents “pale” questions) */
      label[data-testid="stWidgetLabel"] p {{
        color: {TEXT} !important;
        opacity: 1 !important;
      }}

      /* If any text inputs ever get added, keep them consistent too */
      input, textarea {{
        background: {PANEL_2} !important;
        color: {TEXT} !important;
        border: 1px solid {BORDER} !important;
      }}

</style>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# UI LOGO (base64)
# ============================================================
logo_b64 = load_logo_base64(UI_LOGO_FILE)
logo_html = (
    f"<img class='brand-logo' src='data:image/png;base64,{logo_b64}' style='height:auto;' />"
    if logo_b64
    else '<div style="color:#fff; font-weight:700;">[Logo_white.png missing]</div>'
)

# ============================================================
# HEADER (single)
# ============================================================
st.markdown(
    f"""
    <div class="amber-header">
      <div class="header-row">
        <div>{logo_html}</div>
        <div class="brand-text">
          <div class="amber-title">Amberstone – Client Risk Profiler</div>
          <div class="amber-subtitle brand-subtitle">
            Internal risk-profiling tool (Risk Attitude + Capacity for Loss). Outputs maximum strategic allocation caps only.
          </div>
        </div>
      </div>
      <div class="accent-line"></div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# STATE / NAV
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "questionnaire"
if "results" not in st.session_state:
    st.session_state.results = None

def go_questionnaire():
    st.session_state.page = "questionnaire"
    st.rerun()

def go_results():
    st.session_state.page = "results"
    st.rerun()

# Nav buttons under header
nav_left, nav_right = st.columns([1, 1])
with nav_left:
    st.markdown('<div class="navbtn">', unsafe_allow_html=True)
    if st.button("Questionnaire", use_container_width=True):
        go_questionnaire()
    st.markdown("</div>", unsafe_allow_html=True)

with nav_right:
    st.markdown('<div class="navbtn">', unsafe_allow_html=True)
    if st.session_state.results is None:
        st.button("Results", use_container_width=True, disabled=True)
    else:
        if st.button("Results", use_container_width=True):
            go_results()
    st.markdown("</div>", unsafe_allow_html=True)

# This divider is now VERY tight due to the CSS selector above
st.markdown("---")

# ============================================================
# DEFINITIONS
# ============================================================
with st.expander("Definitions & advisory notes", expanded=False):
    st.markdown(
        """
**Alternatives (current scope):**
- Publicly traded **REITs**
- Publicly traded **commodity funds**
- Optionally, some publicly traded equities may be treated as “alternative-like” internally (classification only)

**Reminder (advisory use):**
- Risk attitude ≠ suitability by itself. Also consider time horizon, need to take risk, and liquidity needs.
- This tool outputs **maximum caps**, not target allocations.
        """
    )

# ============================================================
# CORE LOGIC DATA
# ============================================================
LIKERT = ["Strongly agree", "Agree", "No strong opinion", "Disagree", "Strongly disagree"]
LIKERT_TO_NUM = {
    "Strongly disagree": 1,
    "Disagree": 2,
    "No strong opinion": 3,
    "Agree": 4,
    "Strongly agree": 5,
}

ITEMS = [
    ("People who know me would describe me as cautious with money.", False),
    ("I’m comfortable investing in assets that can fall in value as well as rise (e.g., equities).", True),
    ("I usually prefer safer options even if that reduces long-term return potential.", False),
    ("I tend to take a long time to decide on investment choices.", False),
    ("I see financial risk more as an opportunity than a danger.", True),
    ("I generally prefer cash deposits over market-based investments.", False),
    ("I find investing concepts fairly easy to understand.", True),
    ("I’m willing to accept meaningful ups and downs to pursue higher returns.", True),
    ("I have limited experience with funds, shares, or market investing.", False),
    ("I often feel anxious about investment decisions after I make them.", False),
    ("I’d rather accept higher investment risk than simply save more to reach my goals.", True),
    ("I’m not comfortable with the short-term swings that markets can experience.", False),
]

def category_from_score(score_0_100: int) -> str:
    if score_0_100 <= 25:
        return "Very Cautious (0–25)"
    if score_0_100 <= 33:
        return "Cautious (26–33)"
    if score_0_100 <= 44:
        return "Moderately Cautious (34–44)"
    if score_0_100 <= 56:
        return "Balanced (45–56)"
    if score_0_100 <= 67:
        return "Moderately Adventurous (57–67)"
    if score_0_100 <= 79:
        return "Adventurous (68–79)"
    return "Very Adventurous (80–100)"

MAX_POLICY = {
    "Very Cautious (0–25)": {"max_equity": 0,  "max_sukuk": 100, "max_alternatives": 0},
    "Cautious (26–33)": {"max_equity": 20, "max_sukuk": 80,  "max_alternatives": 0},
    "Moderately Cautious (34–44)": {"max_equity": 30, "max_sukuk": 70, "max_alternatives": 0},
    "Balanced (45–56)": {"max_equity": 40, "max_sukuk": 60, "max_alternatives": 0},
    "Moderately Adventurous (57–67)": {"max_equity": 60, "max_sukuk": 35, "max_alternatives": 5},
    "Adventurous (68–79)": {"max_equity": 70, "max_sukuk": 20, "max_alternatives": 10},
    "Very Adventurous (80–100)": {"max_equity": 70, "max_sukuk": 0, "max_alternatives": 30},
}

BAND_ORDER = [
    "Very Cautious (0–25)",
    "Cautious (26–33)",
    "Moderately Cautious (34–44)",
    "Balanced (45–56)",
    "Moderately Adventurous (57–67)",
    "Adventurous (68–79)",
    "Very Adventurous (80–100)",
]

def band_at_or_below(current_band: str, max_band: str) -> str:
    return BAND_ORDER[min(BAND_ORDER.index(current_band), BAND_ORDER.index(max_band))]

def compute_results(inputs: dict) -> dict:
    # Risk attitude scoring
    responses_scored = []
    responses_raw = []
    neutral_count = 0

    for (_, is_normal), choice in zip(ITEMS, inputs["attitude_choices"]):
        if choice == "No strong opinion":
            neutral_count += 1
        raw = LIKERT_TO_NUM[choice]
        scored = raw if is_normal else (6 - raw)
        responses_raw.append(raw)
        responses_scored.append(scored)

    raw_total = sum(responses_scored)  # 12..60
    risk_attitude_score = round((raw_total - 12) / (60 - 12) * 100)
    risk_attitude_band = category_from_score(risk_attitude_score)

    # Capacity for loss scoring
    emergency_months = inputs["emergency_months"]
    income_stability = inputs["income_stability"]
    withdrawal_need = inputs["withdrawal_need"]
    debt_burden = inputs["debt_burden"]
    portfolio_dependence = inputs["portfolio_dependence"]

    cap_points = 0
    cap_points += {"< 3 months": 0, "3–6 months": 2, "6–12 months": 4, "12+ months": 6}[emergency_months]
    cap_points += {
        "Unstable/variable": 0,
        "Somewhat stable": 2,
        "Stable (salaried/contracted)": 4,
        "Very stable (multiple reliable sources)": 6,
    }[income_stability]
    cap_points += {"Very likely": 0, "Somewhat likely": 2, "Unlikely": 4, "Very unlikely": 6}[withdrawal_need]
    cap_points += {"High / hard to service": 0, "Moderate": 2, "Low": 4, "None": 6}[debt_burden]
    cap_points += {"Highly dependent": 0, "Somewhat dependent": 2, "Not very dependent": 4, "Not dependent": 6}[portfolio_dependence]

    if cap_points <= 10:
        capacity_band = "Low capacity for loss"
    elif cap_points <= 20:
        capacity_band = "Medium capacity for loss"
    else:
        capacity_band = "High capacity for loss"

    CAPACITY_MAX_BAND = {
        "Low capacity for loss": "Moderately Cautious (34–44)",
        "Medium capacity for loss": "Balanced (45–56)",
        "High capacity for loss": "Very Adventurous (80–100)",
    }
    capacity_max_allowed_band = CAPACITY_MAX_BAND[capacity_band]

    final_band = band_at_or_below(risk_attitude_band, capacity_max_allowed_band)
    override_applied = final_band != risk_attitude_band

    # Alternatives gating
    limited_experience = responses_raw[8] >= 4
    needs_liquidity_soon = withdrawal_need in ["Very likely", "Somewhat likely"]
    low_capacity = capacity_band == "Low capacity for loss"
    limited_experience_gate = inputs["limited_experience_gate"]

    alt_forced_zero_reasons = []
    if needs_liquidity_soon:
        alt_forced_zero_reasons.append("Large withdrawal likely within 3 years")
    if low_capacity:
        alt_forced_zero_reasons.append("Low capacity for loss")
    if limited_experience_gate and limited_experience:
        alt_forced_zero_reasons.append("Client indicates limited investment experience")

    base_limits = MAX_POLICY[final_band].copy()
    final_limits = base_limits.copy()

    if alt_forced_zero_reasons:
        final_limits["max_alternatives"] = 0

    removed_alt = base_limits["max_alternatives"] - final_limits["max_alternatives"]
    if removed_alt > 0:
        final_limits["max_sukuk"] = min(100, final_limits["max_sukuk"] + removed_alt)

    # Robustness flags
    flags = []
    if neutral_count >= 6:
        flags.append("Many neutral answers (6+). Consider clarifying and reassessing.")
    raw_stmt12 = responses_raw[11]
    if risk_attitude_score >= 68 and raw_stmt12 >= 4:
        flags.append("High score but strong discomfort with market swings—discuss suitability carefully.")
    if risk_attitude_score >= 68 and limited_experience:
        flags.append("High score but self-reported limited experience—consider education / simplification.")

    # Alternatives scope text
    alts_in_scope = []
    if inputs["alt_scope_reits"]:
        alts_in_scope.append("Public REITs")
    if inputs["alt_scope_commodities"]:
        alts_in_scope.append("Commodity funds")
    if inputs["alt_equities_toggle"]:
        alts_in_scope.append("Selected equities treated as 'alternative-like' (internal classification)")

    return {
        "risk_attitude_score": risk_attitude_score,
        "risk_attitude_band": risk_attitude_band,
        "neutral_count": neutral_count,
        "cap_points": cap_points,
        "capacity_band": capacity_band,
        "capacity_max_allowed_band": capacity_max_allowed_band,
        "final_band": final_band,
        "override_applied": override_applied,
        "base_limits": base_limits,
        "final_limits": final_limits,
        "alt_forced_zero_reasons": alt_forced_zero_reasons,
        "flags": flags,
        "alts_in_scope": alts_in_scope,
        "capacity_inputs": {
            "emergency_months": emergency_months,
            "income_stability": income_stability,
            "withdrawal_need": withdrawal_need,
            "debt_burden": debt_burden,
            "portfolio_dependence": portfolio_dependence,
        },
    }

# ============================================================
# QUESTIONNAIRE PAGE
# ============================================================
if st.session_state.page == "questionnaire":
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Questionnaire")

    with st.form("risk_profiler_form", clear_on_submit=False):
        st.markdown("### A) Risk attitude")
        attitude_choices = []
        for i, (statement, _) in enumerate(ITEMS, start=1):
            choice = st.radio(
                f"{i}) {statement}",
                LIKERT,
                index=None,
                horizontal=True,
                key=f"att_{i}",
            )
            attitude_choices.append(choice)

        st.markdown("---")
        st.markdown("### B) Capacity for loss")

        emergency_months = st.selectbox(
            "1) Months of essential expenses held in readily accessible cash/cash-equivalents",
            ["< 3 months", "3–6 months", "6–12 months", "12+ months"],
            index=None,
            key="cap_emergency",
        )
        income_stability = st.selectbox(
            "2) Income stability",
            ["Unstable/variable", "Somewhat stable", "Stable (salaried/contracted)", "Very stable (multiple reliable sources)"],
            index=None,
            key="cap_income",
        )
        withdrawal_need = st.selectbox(
            "3) Likelihood of needing a large withdrawal in the next 3 years",
            ["Very likely", "Somewhat likely", "Unlikely", "Very unlikely"],
            index=None,
            key="cap_withdrawal",
        )
        debt_burden = st.selectbox(
            "4) Debt burden (excluding a manageable primary residence mortgage, if applicable)",
            ["High / hard to service", "Moderate", "Low", "None"],
            index=None,
            key="cap_debt",
        )
        portfolio_dependence = st.selectbox(
            "5) Dependence on this portfolio for near-term living costs (next 3–5 years)",
            ["Highly dependent", "Somewhat dependent", "Not very dependent", "Not dependent"],
            index=None,
            key="cap_dependence",
        )

        st.markdown("---")
        st.markdown("### C) Alternatives scope & gates")

        alt_scope_reits = st.checkbox("Include publicly traded REITs as Alternatives", value=True, key="alt_reits")
        alt_scope_commodities = st.checkbox("Include commodity funds as Alternatives", value=True, key="alt_cmdty")
        alt_equities_toggle = st.checkbox(
            "Allow some publicly traded equities to be treated as 'alternative-like' internally (optional)",
            value=False,
            key="alt_eq",
        )
        limited_experience_gate = st.checkbox(
            "Gate Alternatives to 0% if client indicates limited investment experience",
            value=True,
            key="alt_gate_exp",
        )

        submitted = st.form_submit_button("Submit and view results →", type="primary")

    if submitted:
        missing = []
        for idx, v in enumerate(attitude_choices, start=1):
            if v is None:
                missing.append(f"Risk attitude question {idx}")
        if emergency_months is None: missing.append("Capacity: emergency fund")
        if income_stability is None: missing.append("Capacity: income stability")
        if withdrawal_need is None: missing.append("Capacity: withdrawal likelihood")
        if debt_burden is None: missing.append("Capacity: debt burden")
        if portfolio_dependence is None: missing.append("Capacity: portfolio dependence")

        if missing:
            st.error("Please answer all questions before viewing results.\n\nMissing:\n- " + "\n- ".join(missing))
        else:
            inputs = {
                "attitude_choices": attitude_choices,
                "emergency_months": emergency_months,
                "income_stability": income_stability,
                "withdrawal_need": withdrawal_need,
                "debt_burden": debt_burden,
                "portfolio_dependence": portfolio_dependence,
                "alt_scope_reits": alt_scope_reits,
                "alt_scope_commodities": alt_scope_commodities,
                "alt_equities_toggle": alt_equities_toggle,
                "limited_experience_gate": limited_experience_gate,
            }
            st.session_state.results = compute_results(inputs)
            go_results()

    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RESULTS PAGE (ALL SECTIONS)
# ============================================================
else:
    results = st.session_state.results
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Results")

    if results is None:
        st.info("No results found. Please complete the questionnaire first.")
    else:
        st.markdown("### Summary")
        summary_html = f"""
        <div class="summary-grid">
          <div class="summary-card">
            <div class="summary-label">Risk attitude score</div>
            <div class="summary-value">{results['risk_attitude_score']}/100</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Risk attitude category</div>
            <div class="summary-value">{results['risk_attitude_band']}</div>
          </div>
          <div class="summary-card">
            <div class="summary-label">Capacity for loss</div>
            <div class="summary-value">{results['capacity_band']}</div>
          </div>
        </div>
        """
        st.markdown(summary_html, unsafe_allow_html=True)

        st.write(f"**Capacity points:** {results['cap_points']}/30")
        st.write(f"**Capacity policy cap:** {results['capacity_max_allowed_band']}")

        if results["override_applied"]:
            st.warning(
                f"Risk attitude suggests **{results['risk_attitude_band']}**, "
                f"but capacity policy caps recommendation at **{results['final_band']}**."
            )
        else:
            st.success("No capacity-based override applied.")

        st.markdown("---")
        st.markdown("### Export")
        pdf_bytes = build_pdf_bytes(results, firm_name="Amberstone Capital", logo_file=PDF_LOGO_FILE)
        pdf_filename = f"Amberstone_Risk_Profile_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
            type="primary",
        )

        st.markdown("---")
        st.markdown("### Allocation caps")
        st.write(f"**Final risk category:** {results['final_band']}")

        base_limits = results["base_limits"]
        final_limits = results["final_limits"]

        lc, rc = st.columns(2)
        with lc:
            st.markdown("**Base policy caps (by final band)**")
            st.write(f"- Max Equity: {base_limits['max_equity']}%")
            st.write(f"- Max Sukuk: {base_limits['max_sukuk']}%")
            st.write(f"- Max Alternatives: {base_limits['max_alternatives']}%")
        with rc:
            st.markdown("**Final recommended caps (after gates)**")
            st.write(f"- Max Equity: {final_limits['max_equity']}%")
            st.write(f"- Max Sukuk: {final_limits['max_sukuk']}%")
            st.write(f"- Max Alternatives: {final_limits['max_alternatives']}%")

        if results["alt_forced_zero_reasons"]:
            st.warning("**Alternatives gated to 0%** due to:\n- " + "\n- ".join(results["alt_forced_zero_reasons"]))

        st.markdown("---")
        st.markdown("### Robustness checks")
        if results["flags"]:
            st.warning("Flags:\n- " + "\n- ".join(results["flags"]))
        else:
            st.success("No robustness flags triggered.")

        st.markdown("---")
        st.markdown("### Client file note (copy/paste)")
        cap_in = results["capacity_inputs"]
        file_note = f"""
Amberstone – Risk profiling summary

Risk attitude (12-statement):
- Score: {results['risk_attitude_score']}/100
- Category: {results['risk_attitude_band']}
- Neutral responses: {results['neutral_count']}/12

Capacity for loss:
- Points: {results['cap_points']}/30
- Band: {results['capacity_band']}
- Capacity policy cap: {results['capacity_max_allowed_band']}

Final risk category (after capacity cap):
- {results['final_band']}
- Capacity override applied: {"Yes" if results["override_applied"] else "No"}

Alternatives scope:
- {", ".join(results["alts_in_scope"]) if results["alts_in_scope"] else "None"}

Alternatives gate outcome:
- {"Gated to 0% (" + "; ".join(results["alt_forced_zero_reasons"]) + ")" if results["alt_forced_zero_reasons"] else "Not gated"}

Base policy caps (by final band):
- Max Equity: {base_limits['max_equity']}%
- Max Sukuk: {base_limits['max_sukuk']}%
- Max Alternatives: {base_limits['max_alternatives']}%

Final recommended caps (after gates):
- Max Equity: {final_limits['max_equity']}%
- Max Sukuk: {final_limits['max_sukuk']}%
- Max Alternatives: {final_limits['max_alternatives']}%

Capacity inputs:
- Emergency fund: {cap_in['emergency_months']}
- Income stability: {cap_in['income_stability']}
- Withdrawal likelihood (3y): {cap_in['withdrawal_need']}
- Debt burden: {cap_in['debt_burden']}
- Portfolio dependence (3–5y): {cap_in['portfolio_dependence']}

Robustness flags:
- {"None" if not results["flags"] else "; ".join(results["flags"])}
""".strip()
        st.code(file_note, language="text")

    st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "Amberstone Capital | Internal advisory tool only. "
    "This application provides risk profiling information, not investment advice. "
    "Final suitability decisions rest with the adviser."
)
