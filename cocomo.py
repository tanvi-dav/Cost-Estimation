"""
cocomo.py
=========
The COCOMO calculation engine. This module is pure calculation: it has no
knowledge of the terminal, the web layer or the LLM, which keeps the maths
testable and reusable everywhere (CLI, Flask/Vercel, unit tests).

Model implemented: Intermediate COCOMO (Boehm, 1981).
    Effort   = a * (KLOC ** b) * EAF      [person-months]
    Schedule = c * (Effort ** d)          [calendar months]
    Staff    = Effort / Schedule          [people]
    Cost     = Effort * monthly_cost_per_person
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constants import (
    COST_DRIVERS,
    DEFAULT_MONTHLY_COST_PER_PERSON,
    DEFAULT_PROJECT_CATEGORY,
    HOURS_PER_PERSON_MONTH,
    PROJECT_CATEGORIES,
    PROJECT_TYPE_LABELS,
)
from utils import banner, money


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------
@dataclass
class CocomoResult:
    """Immutable-ish bundle of every output value, ready for printing/JSON."""
    project_type: str
    category: str
    kloc: float
    eaf: float
    effort_pm: float          # person-months
    schedule_months: float
    average_staff: float
    effort_hours: float
    cost: float
    currency: str
    driver_ratings: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialise for the web/JSON layer."""
        return {
            "project_type": PROJECT_TYPE_LABELS.get(self.project_type, self.project_type),
            "category": PROJECT_CATEGORIES.get(self.category, {}).get("label", self.category),
            "kloc": round(self.kloc, 2),
            "eaf": round(self.eaf, 3),
            "effort_pm": round(self.effort_pm, 2),
            "schedule_months": round(self.schedule_months, 2),
            "average_staff": round(self.average_staff, 1),
            "effort_hours": round(self.effort_hours, 0),
            "cost": round(self.cost, 0),
            "currency": self.currency,
            "driver_ratings": self.driver_ratings,
        }


# ---------------------------------------------------------------------------
# Reusable calculation functions (required by the brief)
# ---------------------------------------------------------------------------
def calculate_eaf(driver_ratings: dict[str, str]) -> float:
    """
    Effort Adjustment Factor = product of all chosen effort multipliers.

    ``driver_ratings`` maps a driver code (e.g. "RELY") to a rating label
    (e.g. "High"). Unknown drivers/ratings are ignored (treated as Nominal).
    """
    eaf = 1.0
    for code, rating in driver_ratings.items():
        driver = COST_DRIVERS.get(code)
        if not driver:
            continue
        multiplier = driver["ratings"].get(rating)
        if multiplier is not None:
            eaf *= multiplier
    return eaf


def _validate_project_type(project_type: str) -> str:
    """Normalise and validate the option key ('basic' or 'intermediate')."""
    key = project_type.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in PROJECT_TYPE_LABELS:
        raise ValueError(
            f"Unknown project type '{project_type}'. "
            f"Expected one of: {', '.join(PROJECT_TYPE_LABELS)}"
        )
    return key


def _validate_category(category: str) -> str:
    """Normalise and validate the project category key (organic/semi_detached/embedded)."""
    key = category.strip().lower().replace("-", "_").replace(" ", "_")
    if key not in PROJECT_CATEGORIES:
        raise ValueError(
            f"Unknown project category '{category}'. "
            f"Expected one of: {', '.join(PROJECT_CATEGORIES)}"
        )
    return key


def calculate_effort(kloc: float, eaf: float = 1.0,
                     category: str = DEFAULT_PROJECT_CATEGORY,
                     project_type: str = "basic") -> float:
    """Effort in person-months: a * KLOC^b * EAF, using the category's a/b.

    Boehm's Basic and Intermediate models publish different "a" coefficients
    for the same category (Organic/Embedded differ; Semi-Detached matches),
    so ``project_type`` selects which "a" to use.
    """
    if kloc <= 0:
        raise ValueError("KLOC must be greater than zero.")
    coeffs = PROJECT_CATEGORIES[_validate_category(category)]
    ptype = _validate_project_type(project_type)
    a = coeffs["a_intermediate"] if ptype == "intermediate" else coeffs["a_basic"]
    return a * (kloc ** coeffs["b"]) * eaf


def calculate_schedule(effort_pm: float, category: str = DEFAULT_PROJECT_CATEGORY) -> float:
    """Development schedule in calendar months: c * Effort^d, using the category's c/d."""
    if effort_pm <= 0:
        raise ValueError("Effort must be greater than zero.")
    coeffs = PROJECT_CATEGORIES[_validate_category(category)]
    return coeffs["c"] * (effort_pm ** coeffs["d"])


def calculate_staff(effort_pm: float, schedule_months: float) -> float:
    """Average team size: Effort / Schedule."""
    if schedule_months <= 0:
        raise ValueError("Schedule must be greater than zero.")
    return effort_pm / schedule_months


def estimate_cost(effort_pm: float,
                  monthly_cost_per_person: float = DEFAULT_MONTHLY_COST_PER_PERSON
                  ) -> float:
    """Total labour cost = effort (person-months) * monthly cost per person."""
    return effort_pm * monthly_cost_per_person


# ---------------------------------------------------------------------------
# Object-oriented wrapper that ties the functions together
# ---------------------------------------------------------------------------
class CocomoEstimator:
    """High-level façade over the calculation functions."""

    def __init__(self,
                 monthly_cost_per_person: float = DEFAULT_MONTHLY_COST_PER_PERSON,
                 currency: str = "£") -> None:
        self.monthly_cost_per_person = monthly_cost_per_person
        self.currency = currency

    def estimate(self,
                 kloc: float,
                 project_type: str,
                 driver_ratings: dict[str, str] | None = None,
                 category: str = DEFAULT_PROJECT_CATEGORY) -> CocomoResult:
        """Run the full COCOMO pipeline and return a CocomoResult.

        ``category`` (organic / semi_detached / embedded) selects the a/b/c/d
        coefficients (Boehm, 1981).

        Option 1 ("basic"): EAF is fixed at 1.0; cost drivers are ignored.
        Option 2 ("intermediate"): EAF = product of the given cost drivers.
        """
        ptype = _validate_project_type(project_type)
        category = _validate_category(category)
        driver_ratings = driver_ratings or {}
        if ptype == "basic":
            eaf = 1.0
            driver_ratings = {}
        else:
            eaf = calculate_eaf(driver_ratings)
        effort_pm = calculate_effort(kloc, eaf, category, ptype)
        schedule = calculate_schedule(effort_pm, category)
        staff = calculate_staff(effort_pm, schedule)
        cost = estimate_cost(effort_pm, self.monthly_cost_per_person)
        return CocomoResult(
            project_type=ptype,
            category=category,
            kloc=kloc,
            eaf=eaf,
            effort_pm=effort_pm,
            schedule_months=schedule,
            average_staff=staff,
            effort_hours=effort_pm * HOURS_PER_PERSON_MONTH,
            cost=cost,
            currency=self.currency,
            driver_ratings=driver_ratings,
        )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------
def generate_report(result: CocomoResult,
                    reasoning: dict[str, dict] | None = None) -> str:
    """
    Build the textual COCOMO estimation report.

    ``reasoning`` is the optional per-factor explanation captured during AI
    analysis: {factor_name: {"value": ..., "reason": ...}}.
    """
    lines: list[str] = [banner("COCOMO ESTIMATION REPORT"), ""]
    coeffs = PROJECT_CATEGORIES.get(result.category, {})
    a_key = "a_intermediate" if result.project_type == "intermediate" else "a_basic"
    lines += [
        f"Project Type:        {PROJECT_TYPE_LABELS.get(result.project_type, result.project_type)}",
        f"Project Category:    {coeffs.get('label', result.category)} "
        f"(a={coeffs.get(a_key)}, b={coeffs.get('b')}, c={coeffs.get('c')}, d={coeffs.get('d')})",
        f"Estimated Size:      {result.kloc:.1f} KLOC",
        f"Effort Adj. Factor:  {result.eaf:.3f}",
        f"Estimated Effort:    {result.effort_pm:.2f} Person-Months",
        f"                     ({result.effort_hours:,.0f} hours @ "
        f"{HOURS_PER_PERSON_MONTH} h/PM)",
        f"Development Time:    {result.schedule_months:.1f} Months",
        f"Average Team:        {result.average_staff:.1f} Developers",
        f"Estimated Cost:      {money(result.cost, result.currency)}",
    ]

    if result.driver_ratings:
        lines += ["", "Selected Cost Drivers"]
        for code, rating in result.driver_ratings.items():
            name = COST_DRIVERS.get(code, {}).get("name", code)
            mult = COST_DRIVERS.get(code, {}).get("ratings", {}).get(rating, 1.0)
            lines.append(f"  {name:<32} {rating:<10} (x{mult:.2f})")

    if reasoning:
        lines += ["", "Reasoning Summary"]
        for factor, detail in reasoning.items():
            lines.append(f"\n{factor}:\n  {detail.get('value', 'n/a')}")
            reason = detail.get("reason") or detail.get("reasoning")
            if reason:
                lines.append(f"  Reason: {reason}")

    lines += ["", "=" * 30]
    return "\n".join(lines)