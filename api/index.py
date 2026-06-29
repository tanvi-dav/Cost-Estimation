"""
api/index.py
============
Flask web application (the website). Vercel cannot run an interactive CLI, so
this layer exposes the SAME calculation engine (cocomo.py / fpa.py /
transcript_ai.py) through a browser.

Routes
------
GET  /          landing page (choose a mode)
GET  /analyze   AI analysis form (paste meeting notes)
POST /analyze   run the LLM (or offline demo analyzer) and show the dashboard
GET  /manual    manual COCOMO calculator form (rate every cost driver)
POST /manual    compute and show the report

Local run:   pip install -r requirements.txt && python api/index.py
Deploy:      vercel        (vercel.json routes all traffic here)
Live LLM:    set GEMINI_API_KEY and untick "Demo mode" on the AI page.
"""

from __future__ import annotations

import os
import sys

# Make the root modules importable when this file lives in /api on Vercel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load a local .env file (never committed) so GEMINI_API_KEY is picked up
# automatically. Safe no-op if python-dotenv isn't installed or there's no .env.
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))
except ImportError:
    pass

from flask import Flask, request  # noqa: E402

import web_ui as ui  # noqa: E402
from app import FACTOR_TO_DRIVER, _normalise_rating  # reuse the CLI mapping
from cocomo import CocomoEstimator  # noqa: E402
from constants import PROJECT_TYPE_LABELS  # noqa: E402
from fpa import FunctionPointAnalyzer  # noqa: E402
from transcript_ai import (AnalyzerConfig, TranscriptAnalyzer,  # noqa: E402
                           offline_analyze)

app = Flask(__name__)


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _project_type_key(raw: str) -> str:
    key = (raw or "organic").lower().replace("-", "_").replace(" ", "_")
    return key if key in PROJECT_TYPE_LABELS else "organic"


def _drivers_from_analysis(analysis: dict) -> dict[str, str]:
    drivers: dict[str, str] = {}
    for key, code in FACTOR_TO_DRIVER.items():
        factor = analysis.get(key)
        if factor and factor.get("value"):
            drivers[code] = _normalise_rating(code, factor["value"])
    return drivers


# ---------------------------------------------------------------------------
# Landing
# ---------------------------------------------------------------------------
@app.get("/")
def index() -> str:
    return ui.render_landing()


# ---------------------------------------------------------------------------
# AI analysis
# ---------------------------------------------------------------------------
@app.get("/analyze")
def analyze_form() -> str:
    return ui.render_analyze_form()


@app.post("/analyze")
def analyze() -> str:
    transcript = (request.form.get("transcript") or "").strip()
    if not transcript:
        return ui.render_error("Please paste some meeting notes first.",
                               back_href="/analyze")

    #demo = request.form.get("demo") is not None
    monthly = _to_float(request.form.get("monthly"), 8000.0)
    kloc_override = request.form.get("kloc")

    # 1) Choose the engine and record what actually happened (for the banner).
    #if demo:
    analysis = offline_analyze(transcript)
    notice = ("demo", "Demo mode: analysed with the offline analyzer "
                      "(no API key used).")
    # else:
    #     analyzer = TranscriptAnalyzer(AnalyzerConfig(use_llm=True))
    #     if analyzer.llm_ready():
    #         try:
    #             analysis = analyzer._analyze_with_llm(transcript)
    #             notice = ("live", "Analysed with the live LLM "
    #                               f"({analyzer.config.model}).")
    #         except Exception as exc:  # network / quota / parse failure
    #             analysis = offline_analyze(transcript)
    #             notice = ("warn", f"Live LLM call failed ({exc}). "
    #                               "Fell back to the offline analyzer.")
    #     else:
    #         analysis = offline_analyze(transcript)
    #         notice = ("warn", "No GEMINI_API_KEY (or google-genai package) "
    #                           "detected, so the offline analyzer was used. "
    #                           "Set your key to enable live mode.")

    # 2) Project type comes from the model.
    project_type = _project_type_key(
        str(analysis.get("project_type", {}).get("value", "organic"))
    )

    # 3) Size: explicit override > size stated in notes > derive from FPA.
    fpa_result = None
    kloc_note = ""
    kloc_factor = analysis.get("kloc", {}) or {}
    if kloc_override:
        kloc = _to_float(kloc_override, 1.0)
        kloc_note = f"Using your KLOC override of {kloc:g}."
    elif kloc_factor.get("value") and not kloc_factor.get("needs_confirmation"):
        kloc = float(kloc_factor["value"])
        ev = ", ".join(kloc_factor.get("evidence", [])) or "stated in the notes"
        kloc_note = f"Size taken from the notes ({ev}): {kloc:g} KLOC."
    else:
        fp_block = analysis.get("function_points", {}) or {}
        counts = {k: v for k, v in fp_block.items() if isinstance(v, dict)}
        fpa_result = FunctionPointAnalyzer().analyze(counts, [3] * 14, "default")
        kloc = max(fpa_result.kloc, 0.5)  # floor avoids zero-size demos
        kloc_note = (f"No size was stated, so it was derived from the inferred "
                     f"function points: {fpa_result.afp:.0f} AFP × "
                     f"{fpa_result.loc_per_fp} LOC/FP ≈ {kloc:.2f} KLOC.")

    # 4) Build COCOMO drivers from the analysis and compute.
    drivers = _drivers_from_analysis(analysis)
    result = CocomoEstimator(monthly_cost_per_person=monthly).estimate(
        kloc, project_type, drivers
    )

    return ui.render_results(result, mode="AI", notice=notice,
                             analysis=analysis, fpa_result=fpa_result,
                             kloc_note=kloc_note, back_href="/analyze")


# ---------------------------------------------------------------------------
# Manual calculator
# ---------------------------------------------------------------------------
@app.get("/manual")
def manual_form() -> str:
    return ui.render_manual_form()


@app.post("/manual")
def manual() -> str:
    project_type = _project_type_key(request.form.get("ptype", "organic"))
    kloc = _to_float(request.form.get("kloc"), 0.0)
    if kloc <= 0:
        return ui.render_error("Please enter a KLOC value greater than zero.",
                               back_href="/manual")
    monthly = _to_float(request.form.get("monthly"), 8000.0)

    # One rating per cost driver (default Nominal if missing).
    from constants import COST_DRIVERS
    drivers = {code: request.form.get(code, "Nominal") for code in COST_DRIVERS}

    result = CocomoEstimator(monthly_cost_per_person=monthly).estimate(
        kloc, project_type, drivers
    )
    notice = ("demo", "Calculated from your manual inputs.")
    return ui.render_results(result, mode="Manual", notice=notice,
                             back_href="/manual")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Open  http://localhost:{port}  in your browser.\n")
    app.run(debug=True, port=port)
