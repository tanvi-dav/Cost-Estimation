"""
api/index.py
============
Flask web application (the website). Exposes the calculation engine
(cocomo.py / fpa.py / transcript_ai.py) through a browser. Demo mode only -
the transcript analyzer is the deterministic, keyword-based offline analyzer
(no live AI/LLM call).

Routes
------
GET  /          landing page (choose a mode)
GET  /analyze   demo analysis form (paste meeting notes)
POST /analyze   run the keyword-based demo analyzer and show the dashboard
GET  /manual    manual COCOMO calculator form (Basic or Intermediate)
POST /manual    compute and show the report

Local run:   pip install -r requirements.txt && python api/index.py
Deploy:      vercel        (vercel.json routes all traffic here)
"""

from __future__ import annotations

import os
import sys

# Make the root modules importable when this file lives in /api on Vercel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, request  # noqa: E402

import web_ui as ui  # noqa: E402
from app import FACTOR_TO_DRIVER, _category_key, _normalise_rating, _project_type_key  # noqa: E402
from cocomo import CocomoEstimator  # noqa: E402
from constants import COST_DRIVERS, DEFAULT_PROJECT_CATEGORY  # noqa: E402
from transcript_ai import offline_analyze  # noqa: E402

app = Flask(__name__)


def _to_float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
# Demo keyword analysis
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

    monthly = _to_float(request.form.get("monthly"), 8000.0)
    kloc_override = request.form.get("kloc")

    analysis = offline_analyze(transcript)
    notice = ("demo", "Analysed with the keyword-based demo analyser.")

    # Recommended option (Basic vs Intermediate) comes from the analyzer.
    project_type = _project_type_key(
        str(analysis.get("project_type", {}).get("value", "basic"))
    )

    # Size: explicit override > size stated in notes > ask the user.
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
        return ui.render_error(
            "Couldn't determine a project size from your notes. Please add a "
            "KLOC override and try again.",
            back_href="/analyze",
        )

    # Cost drivers only matter for the Intermediate option.
    drivers = _drivers_from_analysis(analysis) if project_type == "intermediate" else {}
    result = CocomoEstimator(monthly_cost_per_person=monthly).estimate(
        kloc, project_type, drivers
    )

    return ui.render_results(result, mode="Automated", notice=notice,
                             analysis=analysis, transcript=transcript,
                             kloc_note=kloc_note, back_href="/analyze")


# ---------------------------------------------------------------------------
# Manual calculator
# ---------------------------------------------------------------------------
@app.get("/manual")
def manual_form() -> str:
    return ui.render_manual_form()


@app.post("/manual")
def manual() -> str:
    project_type = _project_type_key(request.form.get("ptype", "basic"))
    category = _category_key(request.form.get("category", DEFAULT_PROJECT_CATEGORY))
    kloc = _to_float(request.form.get("kloc"), 0.0)
    if kloc <= 0:
        return ui.render_error("Please enter a KLOC value greater than zero.",
                               back_href="/manual")
    monthly = _to_float(request.form.get("monthly"), 8000.0)

    # One rating per cost driver (default Nominal if missing). Only used by
    # CocomoEstimator.estimate() when project_type == "intermediate".
    drivers = {code: request.form.get(code, "Nominal") for code in COST_DRIVERS}

    result = CocomoEstimator(monthly_cost_per_person=monthly).estimate(
        kloc, project_type, drivers, category=category
    )
    notice = ("demo", "Calculated from your manual inputs.")
    return ui.render_results(result, mode="Manual", notice=notice,
                             back_href="/manual")


if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n  Open  http://localhost:{port}  in your browser.\n")
    app.run(debug=True, port=port)