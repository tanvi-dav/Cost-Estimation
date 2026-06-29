"""
fpa.py
======
Function Point Analysis (Albrecht 1979; IFPUG / ISO/IEC 20926:2009).

FPA sizes software from its *functionality* rather than guessed lines of code,
then bridges to COCOMO by converting Adjusted Function Points (AFP) into KLOC
using a language-dependent backfiring ratio.

Pipeline:
    UFP = Σ (count * weight)                     (unadjusted function points)
    VAF = 0.65 + 0.01 * Σ(GSC ratings)           (value adjustment factor)
    AFP = UFP * VAF                              (adjusted function points)
    LOC = AFP * loc_per_fp ;  KLOC = LOC / 1000  (bridge to COCOMO)
"""

from __future__ import annotations

from dataclasses import dataclass, field

from constants import (
    FP_TYPE_NAMES,
    FP_WEIGHTS,
    GSC_FACTORS,
    LOC_PER_FP,
    VAF_BASE,
    VAF_FACTOR,
)
from utils import banner


@dataclass
class FpaResult:
    """All FPA outputs, ready for reports / JSON / feeding into COCOMO."""
    ufp: int
    vaf: float
    afp: float
    language: str
    loc_per_fp: int
    loc: float
    kloc: float
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    gsc_total: int = 0

    def to_dict(self) -> dict:
        return {
            "ufp": self.ufp,
            "vaf": round(self.vaf, 3),
            "afp": round(self.afp, 1),
            "language": self.language,
            "loc_per_fp": self.loc_per_fp,
            "loc": round(self.loc, 0),
            "kloc": round(self.kloc, 2),
            "gsc_total": self.gsc_total,
            "counts": self.counts,
        }


def calculate_ufp(counts: dict[str, dict[str, int]]) -> int:
    """
    Unadjusted Function Points.

    ``counts`` maps each function type to its low/average/high counts, e.g.::

        {"EI": {"low": 3, "average": 2, "high": 1}, "ILF": {"average": 4}, ...}

    Missing types or bands are treated as zero.
    """
    ufp = 0
    for ftype, weights in FP_WEIGHTS.items():
        band_counts = counts.get(ftype, {})
        for band, weight in weights.items():
            ufp += int(band_counts.get(band, 0)) * weight
    return ufp


def calculate_vaf(gsc_ratings: list[int]) -> float:
    """
    Value Adjustment Factor = 0.65 + 0.01 * Σ(ratings).

    Expects up to 14 ratings, each 0-5. Anything missing counts as 0; values
    are clamped to the valid 0-5 range. Result ranges from 0.65 to 1.35.
    """
    total = sum(max(0, min(5, int(r))) for r in gsc_ratings[:len(GSC_FACTORS)])
    return VAF_BASE + VAF_FACTOR * total


def calculate_afp(ufp: int, vaf: float) -> float:
    """Adjusted Function Points = UFP * VAF."""
    return ufp * vaf


def fp_to_kloc(afp: float, language: str = "default") -> tuple[float, int]:
    """Convert AFP to KLOC via backfiring. Returns (kloc, loc_per_fp_used)."""
    loc_per_fp = LOC_PER_FP.get(language.strip().lower(), LOC_PER_FP["default"])
    loc = afp * loc_per_fp
    return loc / 1000.0, loc_per_fp


class FunctionPointAnalyzer:
    """High-level façade for the FPA pipeline."""

    def analyze(self,
                counts: dict[str, dict[str, int]],
                gsc_ratings: list[int] | None = None,
                language: str = "default") -> FpaResult:
        gsc_ratings = gsc_ratings or [0] * len(GSC_FACTORS)
        ufp = calculate_ufp(counts)
        vaf = calculate_vaf(gsc_ratings)
        afp = calculate_afp(ufp, vaf)
        kloc, loc_per_fp = fp_to_kloc(afp, language)
        return FpaResult(
            ufp=ufp,
            vaf=vaf,
            afp=afp,
            language=language,
            loc_per_fp=loc_per_fp,
            loc=afp * loc_per_fp,
            kloc=kloc,
            counts=counts,
            gsc_total=sum(max(0, min(5, int(r))) for r in gsc_ratings),
        )


def generate_fpa_report(result: FpaResult) -> str:
    """Human-readable FPA report."""
    lines = [banner("FUNCTION POINT ANALYSIS REPORT"), ""]
    lines.append(f"{'Function Type':<26}{'Low':>5}{'Avg':>5}{'High':>5}")
    lines.append("-" * 41)
    for ftype, name in FP_TYPE_NAMES.items():
        band = result.counts.get(ftype, {})
        lines.append(
            f"{name:<26}{band.get('low', 0):>5}"
            f"{band.get('average', 0):>5}{band.get('high', 0):>5}"
        )
    lines += [
        "",
        f"Unadjusted Function Points (UFP): {result.ufp}",
        f"Sum of GSC ratings:               {result.gsc_total} / 70",
        f"Value Adjustment Factor (VAF):    {result.vaf:.2f}",
        f"Adjusted Function Points (AFP):   {result.afp:.1f}",
        f"Backfiring ({result.language}):   {result.loc_per_fp} LOC/FP",
        f"Estimated Size:                   {result.loc:,.0f} LOC "
        f"({result.kloc:.2f} KLOC)",
        "",
        "=" * 41,
    ]
    return "\n".join(lines)
