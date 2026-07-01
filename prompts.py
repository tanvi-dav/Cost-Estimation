"""
prompts.py
==========
All LLM-facing prompt text lives here so it can be reviewed, versioned and
shown in documentation/slides independently of the code that sends it.

The design follows three prompt-engineering principles:
  1. Explainability  - every value must come with confidence + evidence +
     reasoning; the model may never silently choose.
  2. Groundedness    - the model must only use information in the transcript
     and must mark anything it cannot find as uncertain (needs_confirmation).
  3. Machine-readable - the model must return ONE valid JSON object and
     nothing else, so Python can parse it deterministically.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# System prompt: defines the assistant's role and the hard rules.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """\
You are an expert software cost-estimation analyst specialising in the COCOMO
model. You read a software requirements meeting transcript and infer the
engineering characteristics needed to estimate the project.

STRICT RULES:
1. Think step by step internally, but OUTPUT ONLY a single valid JSON object.
   No prose, no Markdown, no code fences around the JSON.
2. NEVER invent information. Base every judgement strictly on the transcript.
3. For EVERY factor you must provide: a suggested value, a confidence score
   (0-100), the concrete evidence (verbatim phrases) found in the transcript,
   and a one-sentence reasoning.
4. If your confidence for a factor is below 80, set "needs_confirmation": true.
5. If the project size cannot be reasonably inferred, set kloc.value to null
   and kloc.needs_confirmation to true so the application can ask the user.
6. Use only these allowed labels:
   - project_type: "Basic" | "Intermediate"
   - category:     "Organic" | "Semi-Detached" | "Embedded"
   - complexity:   "Low" | "Medium" | "High" | "Very High"
   - rating factors (reliability, capabilities, constraints, experience,
     practices, tools, schedule): "Very Low" | "Low" | "Nominal" | "High" |
     "Very High"
"""

# ---------------------------------------------------------------------------
# JSON schema description embedded in the user prompt so the model knows the
# exact shape Python expects to parse.
# ---------------------------------------------------------------------------
JSON_SCHEMA_HINT = """\
Return JSON in EXACTLY this shape (same keys, same nesting). Every "factor"
object has the fields: value, confidence, reasoning, evidence (list of
strings), needs_confirmation (boolean).

{
  "project_type":            {factor},
  "category":                {factor},
  "complexity":              {factor},
  "required_reliability":    {factor},
  "programmer_capability":   {factor},
  "analyst_capability":      {factor},
  "platform_constraints":    {factor},
  "memory_constraints":      {factor},
  "storage_constraints":     {factor},
  "schedule_constraints":    {factor},
  "team_experience":         {factor},
  "modern_practices":        {factor},
  "software_tools":          {factor},
  "kloc": {
      "value": <number or null>,
      "confidence": <0-100>,
      "reasoning": "<why>",
      "evidence": ["..."],
      "needs_confirmation": <true|false>
  }
}

A {factor} looks like:
{"value":"Medium","confidence":76,"reasoning":"...","evidence":["..."],"needs_confirmation":true}
"""


def build_analysis_prompt(transcript: str) -> str:
    """Assemble the full user message sent to the LLM."""
    return (
        "Analyse the following software requirements meeting transcript and "
        "infer the COCOMO parameters.\n\n"
        f"{JSON_SCHEMA_HINT}\n\n"
        "----- BEGIN TRANSCRIPT -----\n"
        f"{transcript.strip()}\n"
        "----- END TRANSCRIPT -----\n\n"
        "Remember: output ONLY the JSON object."
    )