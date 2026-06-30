"""
app.py
======
Command-line entry point. Demo mode only - the transcript analyzer is the
deterministic, keyword-based offline analyzer (no live AI/LLM call).
Run with:  python app.py

Modes
-----
1. Analyze Meeting Transcript (Demo) -> keyword analyzer infers parameters,
                                         you confirm each one
2. Manual COCOMO Estimation          -> Basic (Option 1) or Intermediate
                                         (Option 2), you enter every value
3. Function Point Analysis           -> size a project from its functionality
4. Exit
"""

from __future__ import annotations

from cocomo import CocomoEstimator, generate_report
from constants import (
    COST_DRIVERS,
    DEFAULT_MONTHLY_COST_PER_PERSON,
    DEFAULT_PROJECT_CATEGORY,
    PROJECT_CATEGORIES,
    PROJECT_TYPE_LABELS,
)
from manual import run_manual, run_manual_fpa
from transcript_ai import offline_analyze
from utils import ask_choice, ask_float, ask_yes_no, banner, read_transcript

# Maps the demo analyzer's factor keys to intermediate-COCOMO driver codes
# for the EAF (only used when the recommended option is "Intermediate").
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


def _project_type_key(raw_value: str) -> str:
    """Map the analyzer's 'Basic'/'Intermediate' label onto a valid key."""
    key = str(raw_value).strip().lower().replace("-", "_").replace(" ", "_")
    return key if key in PROJECT_TYPE_LABELS else "basic"


def _category_key(raw_value: str) -> str:
    """Map the analyzer's category label onto a valid PROJECT_CATEGORIES key."""
    key = str(raw_value).strip().lower().replace("-", "_").replace(" ", "_")
    return key if key in PROJECT_CATEGORIES else DEFAULT_PROJECT_CATEGORY


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
    """Mode 1: keyword-based demo analysis of a requirements transcript."""
    print(banner("Analyse Meeting Transcript"))
    transcript = read_transcript()
    if not transcript.strip():
        print("No transcript provided.")
        return

    analysis = offline_analyze(transcript)

    # --- Recommended option (Basic vs Intermediate) ---
    ptype_factor = analysis.get("project_type", {})
    print(f"\nRecommended option: {ptype_factor.get('value')} "
          f"({ptype_factor.get('confidence')}% confidence)")
    print(f"Reasoning: {ptype_factor.get('reasoning', '')}")
    project_type = _project_type_key(ptype_factor.get("value", "basic"))
    if ask_yes_no("Use this option?", default=True) is False:
        idx = ask_choice("Choose the option", list(PROJECT_TYPE_LABELS.values()))
        project_type = list(PROJECT_TYPE_LABELS.keys())[idx]

    # --- Project category (Organic / Semi-Detached / Embedded) ---
    cat_factor = analysis.get("category", {})
    category = _category_key(cat_factor.get("value", DEFAULT_PROJECT_CATEGORY))
    if cat_factor:
        print(f"\nRecommended category: {PROJECT_CATEGORIES[category]['label']} "
              f"({cat_factor.get('confidence')}% confidence)")
        print(f"Reasoning: {cat_factor.get('reasoning', '')}")
    if not cat_factor or ask_yes_no("Use this category?", default=True) is False:
        keys = list(PROJECT_CATEGORIES.keys())
        idx = ask_choice("Choose the project category",
                         [PROJECT_CATEGORIES[k]['label'] for k in keys],
                         default_index=keys.index(category))
        category = keys[idx]

    # --- Cost drivers (build EAF inputs) + reasoning summary ---
    # Only needed for the Intermediate option.
    driver_ratings: dict[str, str] = {}
    reasoning: dict[str, dict] = {}
    if project_type == "intermediate":
        for key, code in FACTOR_TO_DRIVER.items():
            factor = analysis.get(key)
            if not factor:
                continue
            label = key.replace("_", " ").title()
            agreed = _confirm_factor(label, factor)
            driver_ratings[code] = _normalise_rating(code, agreed)
            reasoning[label] = {"value": agreed, "reason": factor.get("reasoning")}

    # --- Size (KLOC): from FPA, from the analyzer, or from the user ---
    kloc = _resolve_kloc(analysis.get("kloc", {}), analysis.get("function_points"))

    # --- Cost assumption ---
    monthly = DEFAULT_MONTHLY_COST_PER_PERSON
    if not ask_yes_no(f"\nUse default salary of £{monthly:,.0f}/dev/month?", default=True):
        monthly = ask_float("Enter average developer salary per month", minimum=0.0)

    result = CocomoEstimator(monthly_cost_per_person=monthly).estimate(
        kloc, project_type, driver_ratings, category=category
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
            ["Analyse Meeting Transcript",
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