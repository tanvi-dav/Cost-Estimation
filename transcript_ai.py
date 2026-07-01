"""
transcript_ai.py
================
Mode 1: AI transcript analysis.

Design notes
------------
* The Gemini call is OPTIONAL and lazily imported, so the program runs even
  when google-genai is not installed or no API key is set.
* When the API is unavailable we fall back to a deterministic, keyword-based
  "offline analyzer". This doubles as the live-demo safety net (no network,
  no surprises) and keeps the explainable-AI contract: it still emits
  confidence, evidence and reasoning for every factor.
* spaCy is also optional; if present it is used only to pull noun chunks as
  richer "evidence", otherwise we use simple keyword scanning.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from constants import CONFIDENCE_THRESHOLD
from prompts import SYSTEM_PROMPT, build_analysis_prompt
from utils import safe_json_parse


@dataclass
class AnalyzerConfig:
    # Gemini model. gemini-2.5-flash is fast and has a generous free tier.
    # You can also try "gemini-2.5-pro" or a newer flash model if your key
    # has access.
    model: str = "gemini-2.5-flash"
    temperature: float = 0.2
    use_llm: bool = True


# ---------------------------------------------------------------------------
# Optional spaCy evidence extraction
# ---------------------------------------------------------------------------
NEGATION_CUES = ("no ", "not ", "nothing ", "without ", "isn't", "aren't",
                 "non-", "never ", "neither ", "nor ")


def _is_negated(text_lower: str, position: int) -> bool:
    """True if a negation cue appears in the ~40 chars before ``position``."""
    window = text_lower[max(0, position - 40):position]
    return any(cue in window for cue in NEGATION_CUES)


def _find_keyword_spans(transcript: str, keywords: list[str]) -> list[dict]:
    """
    Return source spans for non-negated keyword matches.

    Each span is suitable for UI highlighting:
        {"start": 10, "end": 21, "text": "payment API"}

    The matching is case-insensitive but preserves the original transcript text.
    """
    lowered = transcript.lower()
    spans: list[dict] = []

    for kw in keywords:
        pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
        for match in pattern.finditer(transcript):
            if _is_negated(lowered, match.start()):
                continue
            spans.append({
                "start": match.start(),
                "end": match.end(),
                "text": transcript[match.start():match.end()],
            })
            break

    return spans[:5]


def _spans_to_evidence(transcript: str, spans: list[dict]) -> list[str]:
    """Convert source spans into short evidence strings for existing displays."""
    return [transcript[s["start"]:s["end"]] for s in spans]


def _extract_evidence(transcript: str, keywords: list[str]) -> list[str]:
    """
    Return transcript phrases matching keywords, skipping negated mentions
    (so "nothing embedded or real-time" is NOT counted as evidence of an
    embedded system). spaCy is used for richer evidence if available.
    """
    found: list[str] = _spans_to_evidence(
        transcript,
        _find_keyword_spans(transcript, keywords),
    )

    # Best-effort spaCy enrichment (never fatal if unavailable).
    try:
        import spacy  # type: ignore

        nlp = spacy.blank("en")  # blank pipeline avoids model downloads
        nlp.add_pipe("sentencizer")
        for sent in nlp(transcript).sents:
            stext = sent.text.lower()
            for kw in keywords:
                pos = stext.find(kw)
                if pos != -1 and not _is_negated(stext, pos) \
                        and sent.text.strip() not in found:
                    found.append(sent.text.strip()[:120])
                    break
    except Exception:
        pass
    return found[:5]


# ---------------------------------------------------------------------------
# Offline deterministic analyzer (fallback / demo mode)
# ---------------------------------------------------------------------------
KEYWORD_MAP = {
    "complexity_high": ["real-time", "embedded", "payment gateway", "encryption",
                        "machine learning", "concurrency", "distributed"],
    "complexity_medium": ["authentication", "admin dashboard", "rest api",
                          "integration", "database", "reporting"],
    "reliability_high": ["financial", "payment", "medical", "transaction",
                         "compliance", "security"],
    "embedded": ["hardware", "firmware", "device", "real-time", "sensor"],
    "junior": ["junior", "intern", "trainee", "students"],
}


def _factor(value, confidence, reasoning, evidence, source_spans=None):
    """Build a single explainable factor dict."""
    return {
        "value": value,
        "confidence": confidence,
        "reasoning": reasoning,
        "evidence": evidence,
        "source_spans": source_spans or [],
        "needs_confirmation": confidence < CONFIDENCE_THRESHOLD,
    }


def _infer_kloc(transcript: str) -> tuple[float | None, list[str], list[dict]]:
    """
    Try to read an explicit project size from the notes.
    Recognises e.g. '45 KLOC', '45,000 lines of code', '45000 LOC'.
    Returns (kloc_or_None, evidence, source_spans).
    """
    # Direct KLOC figure.
    m = re.search(r"(\d+(?:\.\d+)?)\s*kloc", transcript, re.IGNORECASE)
    if m:
        matched = m.group(0).strip()
        return float(m.group(1)), [matched], [{
            "start": m.start(),
            "end": m.end(),
            "text": transcript[m.start():m.end()],
        }]

    # Lines of code / LOC figure -> convert to KLOC.
    m = re.search(
        r"(\d[\d,]{2,})\s*(?:lines of code|lines|loc)\b",
        transcript,
        re.IGNORECASE,
    )
    if m:
        loc = float(m.group(1).replace(",", ""))
        matched = m.group(0).strip()
        return round(loc / 1000.0, 2), [matched], [{
            "start": m.start(),
            "end": m.end(),
            "text": transcript[m.start():m.end()],
        }]

    return None, [], []


def offline_analyze(transcript: str) -> dict:
    """Deterministic heuristic analysis used when the LLM is unavailable."""
    text = transcript.lower()

    high_spans = _find_keyword_spans(transcript, KEYWORD_MAP["complexity_high"])
    med_spans = _find_keyword_spans(transcript, KEYWORD_MAP["complexity_medium"])
    high_ev = _spans_to_evidence(transcript, high_spans)
    med_ev = _spans_to_evidence(transcript, med_spans)

    if high_ev:
        complexity = _factor("High", 72,
                             "Several advanced/interacting components detected.",
                             high_ev, high_spans)
    elif med_ev:
        complexity = _factor("Medium", 70,
                             "Multiple integrated business modules detected.",
                             med_ev, med_spans)
    else:
        complexity = _factor("Low", 55,
                             "Few interacting components found in transcript.",
                             med_ev or ["(little evidence)"], med_spans)

    rely_spans = _find_keyword_spans(transcript, KEYWORD_MAP["reliability_high"])
    rely_ev = _spans_to_evidence(transcript, rely_spans)
    reliability = _factor(
        "High" if rely_ev else "Nominal",
        74 if rely_ev else 60,
        "Financial/sensitive operations imply higher reliability."
        if rely_ev else "No strong reliability drivers found.",
        rely_ev or ["(none)"],
        rely_spans,
    )

    embedded_spans = _find_keyword_spans(transcript, KEYWORD_MAP["embedded"])
    embedded_ev = _spans_to_evidence(transcript, embedded_spans)
    if embedded_ev:
        category = _factor("Embedded", 68,
                           "Hardware/real-time language suggests embedded mode.",
                           embedded_ev, embedded_spans)
    elif high_ev or med_ev:
        category = _factor("Semi-Detached", 70,
                           "Mixed experience and medium complexity business app.",
                           (high_ev + med_ev)[:4], (high_spans + med_spans)[:4])
    else:
        category = _factor("Organic", 65,
                           "Small, familiar in-house style project.",
                           med_ev or ["(default)"], med_spans)

    junior_spans = _find_keyword_spans(transcript, KEYWORD_MAP["junior"])
    junior_ev = _spans_to_evidence(transcript, junior_spans)
    prog_cap = _factor(
        "Low" if junior_ev else "Nominal",
        70 if junior_ev else 58,
        "Junior staff mentioned." if junior_ev else "Capability not specified.",
        junior_ev or ["(none)"],
        junior_spans,
    )

    # Recommend Basic vs Intermediate COCOMO: Intermediate is only worth the
    # extra rating effort when the notes actually give us signal on the cost
    # drivers (complexity, reliability, staffing, or platform constraints).
    driver_signal_ev = (high_ev + med_ev + rely_ev + junior_ev + embedded_ev)[:5]
    driver_signal_spans = (high_spans + med_spans + rely_spans + junior_spans + embedded_spans)[:5]
    if driver_signal_ev:
        project_type = _factor(
            "Intermediate", 66,
            "The notes give enough signal on complexity, reliability, staffing "
            "or platform constraints to rate the cost drivers.",
            driver_signal_ev, driver_signal_spans,
        )
    else:
        project_type = _factor(
            "Basic", 55,
            "No strong cost-driver signals were found, so a size-only estimate "
            "is recommended.",
            ["(no strong signals)"],
        )

    nominal = lambda why: _factor("Nominal", 55, why, ["(not specified)"])

    inferred_kloc, kloc_evidence, kloc_spans = _infer_kloc(transcript)
    if inferred_kloc is not None:
        kloc_block = {
            "value": inferred_kloc,
            "confidence": 82,
            "reasoning": "An explicit code-size figure was stated in the notes.",
            "evidence": kloc_evidence,
            "source_spans": kloc_spans,
            "needs_confirmation": False,
        }
    else:
        kloc_block = {
            "value": None,
            "confidence": 40,
            "reasoning": "Transcript does not quantify size; ask the user.",
            "evidence": [],
            "source_spans": [],
            "needs_confirmation": True,
        }

    return {
        "project_type": project_type,
        "category": category,
        "complexity": complexity,
        "required_reliability": reliability,
        "programmer_capability": prog_cap,
        "analyst_capability": nominal("Analyst capability not specified."),
        "platform_constraints": nominal("No platform constraints stated."),
        "memory_constraints": nominal("No memory constraints stated."),
        "storage_constraints": nominal("No storage constraints stated."),
        "schedule_constraints": nominal("No explicit schedule pressure stated."),
        "team_experience": prog_cap,
        "modern_practices": nominal("Engineering practices not described."),
        "software_tools": nominal("Tooling not described."),
        "kloc": kloc_block,
    }


# ---------------------------------------------------------------------------
# Main analyzer class
# ---------------------------------------------------------------------------
class TranscriptAnalyzer:
    """Analyses a transcript into explainable COCOMO parameters."""

    def __init__(self, config: AnalyzerConfig | None = None) -> None:
        self.config = config or AnalyzerConfig()

    def _llm_available(self) -> bool:
        if not self.config.use_llm:
            return False
        if not (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")):
            return False
        try:
            from google import genai  # noqa: F401  (lazy import)
            return True
        except ImportError:
            return False

    def llm_ready(self) -> bool:
        """Public check: is a live Gemini call possible right now?"""
        return self._llm_available()

    def analyze(self, transcript: str) -> dict:
        """Return the parsed analysis dict (LLM if possible, else offline)."""
        if not transcript.strip():
            raise ValueError("Transcript is empty.")
        if self._llm_available():
            try:
                return self._analyze_with_llm(transcript)
            except Exception as exc:  # network/parse error -> graceful fallback
                print(f"  [warn] LLM call failed ({exc}); using offline analyzer.")
        return offline_analyze(transcript)

    def _analyze_with_llm(self, transcript: str) -> dict:
        """Call the Gemini API in JSON mode and parse the result."""
        from google import genai  # lazy import
        from google.genai import types

        # The client picks up GEMINI_API_KEY (or GOOGLE_API_KEY) from the env.
        client = genai.Client()
        response = client.models.generate_content(
            model=self.config.model,
            contents=build_analysis_prompt(transcript),
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=self.config.temperature,
                response_mime_type="application/json",
            ),
        )
        parsed = safe_json_parse(response.text or "")
        if parsed is None:
            raise ValueError("LLM did not return valid JSON.")
        return parsed
