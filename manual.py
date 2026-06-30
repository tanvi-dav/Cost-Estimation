"""
manual.py
=========
Mode 2 (Manual COCOMO) and the interactive Function Point Analysis flow.
This module owns ONLY the terminal interaction; every number is produced by
cocomo.py / fpa.py so the maths is identical to the AI and web paths.
"""

from __future__ import annotations

from cocomo import CocomoEstimator, generate_report
from constants import (
    COST_DRIVERS,
    DEFAULT_CURRENCY,
    DEFAULT_MONTHLY_COST_PER_PERSON,
    DEFAULT_PROJECT_CATEGORY,
    FP_TYPE_NAMES,
    GSC_FACTORS,
    LOC_PER_FP,
    PROJECT_CATEGORIES,
    PROJECT_TYPE_LABELS,
)
from fpa import FunctionPointAnalyzer, generate_fpa_report
from utils import ask_choice, ask_float, ask_yes_no, banner


def _choose_project_type() -> str:
    """Prompt for the COCOMO mode and return its internal key."""
    keys = list(PROJECT_TYPE_LABELS.keys())
    idx = ask_choice("Select Project Type",
                     [PROJECT_TYPE_LABELS[k] for k in keys])
    return keys[idx]


def _choose_category() -> str:
    """Prompt for the project category (Organic/Semi-Detached/Embedded)."""
    keys = list(PROJECT_CATEGORIES.keys())
    labels = [f"{PROJECT_CATEGORIES[k]['label']} - {PROJECT_CATEGORIES[k]['description']}"
              for k in keys]
    default = keys.index(DEFAULT_PROJECT_CATEGORY)
    idx = ask_choice("Select Project Category", labels, default_index=default)
    return keys[idx]


def _collect_driver_ratings() -> dict[str, str]:
    """Ask the user to rate every intermediate-COCOMO cost driver."""
    ratings: dict[str, str] = {}
    print("\nRate each cost driver (press Enter for Nominal):")
    for code, driver in COST_DRIVERS.items():
        labels = list(driver["ratings"].keys())
        default = labels.index("Nominal") if "Nominal" in labels else 0
        idx = ask_choice(driver["name"], labels, default_index=default)
        ratings[code] = labels[idx]
    return ratings


def run_manual_fpa(language: str | None = None) -> float:
    """
    Interactive FPA. Returns the derived KLOC so it can feed COCOMO.
    """
    print(banner("FUNCTION POINT ANALYSIS"))
    counts: dict[str, dict[str, int]] = {}
    print("\nEnter the number of components for each function type and band.")
    for ftype, name in FP_TYPE_NAMES.items():
        print(f"\n{name} ({ftype})")
        counts[ftype] = {
            "low": int(ask_float("  Low complexity count")),
            "average": int(ask_float("  Average complexity count")),
            "high": int(ask_float("  High complexity count")),
        }

    print("\nRate the 14 General System Characteristics (0 = none ... 5 = strong):")
    gsc = [int(ask_float(f"  {i + 1:>2}. {name}")) for i, name in enumerate(GSC_FACTORS)]

    if language is None:
        langs = list(LOC_PER_FP.keys())
        idx = ask_choice("Implementation language (for LOC conversion)", langs,
                         default_index=langs.index("default"))
        language = langs[idx]

    result = FunctionPointAnalyzer().analyze(counts, gsc, language)
    print("\n" + generate_fpa_report(result))
    return result.kloc


def run_manual() -> None:
    """Top-level Manual COCOMO Calculator flow.

    Option 1 - Basic:        KLOC + monthly cost only (EAF fixed at 1.0).
    Option 2 - Intermediate: also rate every cost driver to build the EAF.
    """
    print(banner("Manual COCOMO Calculator"))

    project_type = _choose_project_type()
    category = _choose_category()

    kloc = ask_float("\nEstimated size in KLOC (thousands of lines of code)",
                     minimum=0.01)

    ratings: dict[str, str] = {}
    if project_type == "intermediate":
        ratings = _collect_driver_ratings()

    monthly = DEFAULT_MONTHLY_COST_PER_PERSON
    if ask_yes_no(f"\nUse default cost of {DEFAULT_CURRENCY}{monthly:,.0f}/dev/month?",
                  default=True) is False:
        monthly = ask_float("Enter monthly cost per developer", minimum=0.0)

    estimator = CocomoEstimator(monthly_cost_per_person=monthly)
    result = estimator.estimate(kloc, project_type, ratings, category=category)
    print("\n" + generate_report(result))