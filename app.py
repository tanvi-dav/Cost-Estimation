"""
app.py
======
Command-line entry point and the interactive "explainable AI" transcript flow
(Mode 1). Run with:  python app.py

Modes
-----
1. Analyze Meeting Transcript  -> AI infers parameters, you confirm each one
2. Manual COCOMO Estimation    -> you enter every value
3. Function Point Analysis      -> size a project from its functionality
4. Exit
"""

from __future__ import annotations

from cocomo import CocomoEstimator, generate_report
from constants import (
    COST_DRIVERS,
    DEFAULT_MONTHLY_COST_PER_PERSON,
    PROJECT_TYPE_LABELS,
)
from manual import run_manual, run_manual_fpa
from transcript_ai import TranscriptAnalyzer
from utils import ask_choice, ask_float, ask_yes_no, banner, read_transcript

# Maps the AI's factor keys to intermediate-COCOMO driver codes for the EAF.
FACTOR_TO_DRIVER = {
    "required_reliability": "RELY",
    "complexity": "CPLX",
    "programmer_capability": "PCAP",
    "analyst_capability": "ACAP",
    "platform_constraints": "TIME",
    "memory_constraints": "STOR",
    "storage_constraints": "DATA",
    "schedule_constraints": "SCED",
    "team_experience": "AEXP",
    "modern_practices": "MODP",
    "software_tools": "TOOL",
}

# Normalise loosely-worded ratings onto the labels each driver actually supports.
RATING_ALIASES = {
    "medium": "Nominal",
    "average": "Nominal",
    "normal": "Nominal",
    "very high": "Very High",
    "very low": "Very Low",
}


def _normalise_rating(driver_code: str, raw_value: str) -> str:
    """Return a rating label that exists for ``driver_code`` (else 'Nominal')."""
    valid = COST_DRIVERS[driver_code]["ratings"]
    if raw_value in valid:
        return raw_value
    alias = RATING_ALIASES.get(str(raw_value).strip().lower())
    if alias and alias in valid:
        return alias
    title = str(raw_value).strip().title()
    return title if title in valid else "Nominal"


def _confirm_factor(label: str, factor: dict) -> str:
    """
    Show one factor's evidence/reasoning and let the user accept or override.
    Returns the final agreed value.
    """
    print(f"\n--- {label} ---")
    print(f"Suggested:  {factor.get('value')}")
    print(f"Confidence: {factor.get('confidence')}%")
    evidence = factor.get("evidence") or []
    if evidence:
        print("Evidence:")
        for item in evidence:
            print(f"  • {item}")
    print(f"Reasoning:  {factor.get('reasoning', '(none)')}")

    if not factor.get("needs_confirmation") and not ask_yes_no(
        "Confidence is high. Review/change this anyway?", default=False
    ):
        return factor.get("value")

    # Offer the valid labels for whichever driver this maps to (if any).
    driver = FACTOR_TO_DRIVER.get(_label_to_key(label))
    options = (list(COST_DRIVERS[driver]["ratings"].keys()) if driver
               else ["Low", "Medium", "High", "Very High"])
    if not ask_yes_no("Do you agree with the suggested value?", default=True):
        idx = ask_choice("Choose the correct value", options)
        return options[idx]
    return factor.get("value")


def _label_to_key(label: str) -> str:
    return label.lower().replace(" ", "_").replace("-", "_")


def run_transcript_analysis() -> None:
    """Mode 1: explainable AI analysis of a requirements transcript."""
    print(banner("AI Transcript Analysis"))
    transcript = read_transcript()
    if not transcript.strip():
        print("No transcript provided.")
        return

    print("\nAnalysing transcript... (LLM if configured, else offline analyzer)")
    analysis = TranscriptAnalyzer().analyze(transcript)

    # --- Project type ---
    pt_factor = analysis.get("project_type", {})
    pt_value = _confirm_factor("Project Type", pt_factor) or "Organic"
    project_type = pt_value.lower().replace("-", "_").replace(" ", "_")
    if project_type not in PROJECT_TYPE_LABELS:
        project_type = "organic"

    # --- Cost drivers (build EAF inputs) + reasoning summary ---
    driver_ratings: dict[str, str] = {}
    reasoning: dict[str, dict] = {}
    for key, code in FACTOR_TO_DRIVER.items():
        factor = analysis.get(key)
        if not factor:
            continue
        label = key.replace("_", " ").title()
        agreed = _confirm_factor(label, factor)
        driver_ratings[code] = _normalise_rating(code, agreed)
        reasoning[label] = {"value": agreed, "reason": factor.get("reasoning")}

    # --- Size (KLOC): from FPA, from the AI, or from the user ---
    kloc = _resolve_kloc(analysis.get("kloc", {}), analysis.get("function_points"))

    # --- Cost assumption ---
    monthly = DEFAULT_MONTHLY_COST_PER_PERSON
    if not ask_yes_no(f"\nUse default cost of £{monthly:,.0f}/dev/month?", default=True):
        monthly = ask_float("Enter monthly cost per developer", minimum=0.0)

    result = CocomoEstimator(monthly_cost_per_person=monthly).estimate(
        kloc, project_type, driver_ratings
    )
    print("\n" + generate_report(result, reasoning))


def _resolve_kloc(kloc_factor: dict, fp_block: dict | None) -> float:
    """Decide the KLOC to use, asking the user only when necessary."""
    value = kloc_factor.get("value")
    if value and not kloc_factor.get("needs_confirmation"):
        print(f"\nEstimated size from transcript: {value} KLOC "
              f"({kloc_factor.get('confidence')}% confidence).")
        if ask_yes_no("Accept this size?", default=True):
            return float(value)

    # Offer to derive it from Function Point Analysis.
    if fp_block and ask_yes_no(
        "\nSize is uncertain. Derive it from Function Point Analysis?", default=True
    ):
        from fpa import FunctionPointAnalyzer
        counts = {k: v for k, v in fp_block.items() if isinstance(v, dict)}
        if counts:
            res = FunctionPointAnalyzer().analyze(counts, [3] * 14, "default")
            print(f"FPA-derived size: {res.kloc:.2f} KLOC "
                  f"(AFP={res.afp:.0f}).")
            if ask_yes_no("Use this FPA-derived size?", default=True):
                return res.kloc
        return run_manual_fpa()

    print("\nI cannot accurately estimate the project size.")
    return ask_float("Please enter the estimated KLOC", minimum=0.01)


def main() -> None:
    """Application loop."""
    while True:
        print("\n" + banner("COCOMO Project Estimator"))
        choice = ask_choice(
            "Select an option",
            ["Analyze Meeting Transcript (AI)",
             "Manual COCOMO Estimation",
             "Function Point Analysis",
             "Exit"],
        )
        if choice == 0:
            run_transcript_analysis()
        elif choice == 1:
            run_manual()
        elif choice == 2:
            run_manual_fpa()
        else:
            print("Goodbye.")
            break


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\nInterrupted. Goodbye.")
