"""
constants.py
============
Single source of truth for every numeric constant used by the estimator.

References
----------
* Boehm, B. W. (1981). *Software Engineering Economics*. Prentice-Hall.
  (Basic + Intermediate COCOMO coefficients and the 15 effort multipliers.)
* Albrecht, A. J. (1979). "Measuring Application Development Productivity".
  Proc. IBM Applications Development Symposium. (Function Point Analysis.)
* ISO/IEC 20926:2009 — IFPUG Functional Size Measurement Method
  (function-type weights and the 14 General System Characteristics / VAF).
* Jones, C. (2008). *Applied Software Measurement* — backfiring / "gearing"
  LOC-per-function-point ratios (approximate, language dependent).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# COCOMO project modes (Basic COCOMO coefficients a, b, c, d)
#   Effort  = a * (KLOC ** b) * EAF        [person-months]
#   Schedule= c * (Effort ** d)            [calendar months]
# ---------------------------------------------------------------------------
COCOMO_COEFFICIENTS: dict[str, dict[str, float]] = {
    "organic":       {"a": 2.4, "b": 1.05, "c": 2.5, "d": 0.38},
    "semi_detached": {"a": 3.0, "b": 1.12, "c": 2.5, "d": 0.35},
    "embedded":      {"a": 3.6, "b": 1.20, "c": 2.5, "d": 0.32},
}

# Human-readable labels for the three modes (used by menus / reports).
PROJECT_TYPE_LABELS: dict[str, str] = {
    "organic": "Organic",
    "semi_detached": "Semi-Detached",
    "embedded": "Embedded",
}

# ---------------------------------------------------------------------------
# Intermediate COCOMO effort multipliers (Boehm, 1981).
# Each driver maps a qualitative rating -> a numeric multiplier.
# EAF (Effort Adjustment Factor) = product of the chosen multipliers.
# A rating that does not exist for a driver simply is not listed; any driver
# left unspecified defaults to "Nominal" (multiplier 1.00).
# ---------------------------------------------------------------------------
COST_DRIVERS: dict[str, dict] = {
    # --- Product attributes ---
    "RELY": {"name": "Required Software Reliability",
             "ratings": {"Very Low": 0.75, "Low": 0.88, "Nominal": 1.00,
                         "High": 1.15, "Very High": 1.40}},
    "DATA": {"name": "Database Size",
             "ratings": {"Low": 0.94, "Nominal": 1.00, "High": 1.08,
                         "Very High": 1.16}},
    "CPLX": {"name": "Product Complexity",
             "ratings": {"Very Low": 0.70, "Low": 0.85, "Nominal": 1.00,
                         "High": 1.15, "Very High": 1.30, "Extra High": 1.65}},
    # --- Platform / hardware attributes ---
    "TIME": {"name": "Execution Time Constraint",
             "ratings": {"Nominal": 1.00, "High": 1.11, "Very High": 1.30,
                         "Extra High": 1.66}},
    "STOR": {"name": "Main Storage Constraint",
             "ratings": {"Nominal": 1.00, "High": 1.06, "Very High": 1.21,
                         "Extra High": 1.56}},
    "VIRT": {"name": "Virtual Machine Volatility",
             "ratings": {"Low": 0.87, "Nominal": 1.00, "High": 1.15,
                         "Very High": 1.30}},
    "TURN": {"name": "Computer Turnaround Time",
             "ratings": {"Low": 0.87, "Nominal": 1.00, "High": 1.07,
                         "Very High": 1.15}},
    # --- Personnel attributes ---
    "ACAP": {"name": "Analyst Capability",
             "ratings": {"Very Low": 1.46, "Low": 1.19, "Nominal": 1.00,
                         "High": 0.86, "Very High": 0.71}},
    "AEXP": {"name": "Applications Experience",
             "ratings": {"Very Low": 1.29, "Low": 1.13, "Nominal": 1.00,
                         "High": 0.91, "Very High": 0.82}},
    "PCAP": {"name": "Programmer Capability",
             "ratings": {"Very Low": 1.42, "Low": 1.17, "Nominal": 1.00,
                         "High": 0.86, "Very High": 0.70}},
    "VEXP": {"name": "Virtual Machine Experience",
             "ratings": {"Very Low": 1.21, "Low": 1.10, "Nominal": 1.00,
                         "High": 0.90}},
    "LEXP": {"name": "Programming Language Experience",
             "ratings": {"Very Low": 1.14, "Low": 1.07, "Nominal": 1.00,
                         "High": 0.95}},
    # --- Project attributes ---
    "MODP": {"name": "Modern Programming Practices",
             "ratings": {"Very Low": 1.24, "Low": 1.10, "Nominal": 1.00,
                         "High": 0.91, "Very High": 0.82}},
    "TOOL": {"name": "Use of Software Tools",
             "ratings": {"Very Low": 1.24, "Low": 1.10, "Nominal": 1.00,
                         "High": 0.91, "Very High": 0.83}},
    "SCED": {"name": "Required Development Schedule",
             "ratings": {"Very Low": 1.23, "Low": 1.08, "Nominal": 1.00,
                         "High": 1.04, "Very High": 1.10}},
}

# Boehm treats one person-month as 152 working hours.
HOURS_PER_PERSON_MONTH: int = 152

# Default fully-loaded cost of one developer for one month (override anywhere).
DEFAULT_MONTHLY_COST_PER_PERSON: float = 8000.0
DEFAULT_CURRENCY: str = "£"

# Confidence threshold below which the AI must ask the user to confirm.
CONFIDENCE_THRESHOLD: int = 80

# ---------------------------------------------------------------------------
# Function Point Analysis (Albrecht / IFPUG, ISO/IEC 20926:2009)
# ---------------------------------------------------------------------------
# Unadjusted weights per function type and complexity band.
FP_WEIGHTS: dict[str, dict[str, int]] = {
    "EI":  {"low": 3, "average": 4, "high": 6},   # External Inputs
    "EO":  {"low": 4, "average": 5, "high": 7},   # External Outputs
    "EQ":  {"low": 3, "average": 4, "high": 6},   # External Inquiries
    "ILF": {"low": 7, "average": 10, "high": 15},  # Internal Logical Files
    "EIF": {"low": 5, "average": 7, "high": 10},  # External Interface Files
}

FP_TYPE_NAMES: dict[str, str] = {
    "EI": "External Inputs",
    "EO": "External Outputs",
    "EQ": "External Inquiries",
    "ILF": "Internal Logical Files",
    "EIF": "External Interface Files",
}

# The 14 General System Characteristics, each rated 0 (no influence) - 5 (strong).
GSC_FACTORS: list[str] = [
    "Data communications",
    "Distributed data processing",
    "Performance",
    "Heavily used configuration",
    "Transaction rate",
    "Online data entry",
    "End-user efficiency",
    "Online update",
    "Complex processing",
    "Reusability",
    "Installation ease",
    "Operational ease",
    "Multiple sites",
    "Facilitate change",
]

# VAF = 0.65 + 0.01 * sum(GSC). Constants from the IFPUG method.
VAF_BASE: float = 0.65
VAF_FACTOR: float = 0.01

# Approximate backfiring / gearing factors: average source LOC per function point.
# Language dependent and only indicative (Jones, 2008).
LOC_PER_FP: dict[str, int] = {
    "python": 40,
    "javascript": 47,
    "typescript": 50,
    "java": 53,
    "c#": 54,
    "c++": 53,
    "c": 128,
    "default": 53,
}
