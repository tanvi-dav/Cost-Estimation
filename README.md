# COCOMO + Function Point Estimator (Web App)

A **website** that estimates software development effort, schedule, team size
and cost. It has two modes:

1. **AI Analysis** — paste a requirements meeting transcript; an LLM infers
   every COCOMO factor (with evidence + confidence) and produces the full
   report.
2. **Manual Calculator** — choose the project type, enter KLOC, and rate every
   COCOMO cost driver yourself; the app computes EAF, Effort, Schedule, Average
   Staff and Cost.

It is built in **Python (Flask)** — no TypeScript needed — and deploys to
**Vercel**. The same calculation engine also has a CLI (`app.py`) and can be
imported as a library.

---

## Quick start (run the website locally)

```bash
# 1. (optional) virtual environment
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate

# 2. install dependencies
pip install -r requirements.txt

# 3. (optional) enable the real LLM
export GEMINI_API_KEY="AIza..."      # Windows: set GEMINI_API_KEY=AIza...

# 4. run it
python api/index.py
```

Then open **http://localhost:5000**.

- Without an API key, leave **Demo mode** ticked on the AI page — it uses a
  built-in offline analyzer, so the site works with zero setup.
- With a key, untick Demo mode to use the live LLM (`gemini-2.5-flash`).

---

## Deploy to Vercel

```bash
npm i -g vercel
vercel
```

`vercel.json` routes all traffic to `api/index.py`. In the Vercel dashboard,
add an `GEMINI_API_KEY` environment variable to enable live mode (otherwise the
site runs in demo mode).

---

## Pages

| Route        | What it does                                              |
|--------------|----------------------------------------------------------|
| `/`          | Landing page — pick a mode                                |
| `/analyze`   | Paste meeting notes → LLM/offline analysis → dashboard    |
| `/manual`    | Rate every cost driver → COCOMO report                    |

The AI dashboard shows, for every inferred factor, the **value**, a
**confidence bar**, the **evidence** found in your notes, and the **reasoning**
— plus a live, value-substituted view of the COCOMO formula.

---

## Optional: command-line version

The same engine also runs as a CLI if you prefer:

```bash
python app.py
```

---

## How the estimate is calculated

**COCOMO (Intermediate)**
```
EAF      = product of chosen effort multipliers
Effort   = a * (KLOC ^ b) * EAF      [person-months]
Schedule = c * (Effort ^ d)          [calendar months]
Staff    = Effort / Schedule
Cost     = Effort * monthly_cost_per_person
```

**Function Point Analysis**
```
UFP  = Σ (count * weight)            (per function type & complexity band)
VAF  = 0.65 + 0.01 * Σ(14 GSC ratings)
AFP  = UFP * VAF
KLOC = (AFP * LOC_per_FP) / 1000     (bridge into COCOMO)
```

---

## Architecture

```
cocomo_estimator/
├── api/index.py      Flask routes (the website) — reuses the engine below
├── web_ui.py         all HTML + CSS rendering (landing, forms, dashboard)
├── cocomo.py         COCOMO engine (functions + OO + report)   — pure maths
├── fpa.py            Function Point Analysis engine            — pure maths
├── transcript_ai.py  LLM analysis + offline/demo analyzer (+ optional spaCy)
├── prompts.py        LLM system/user prompt templates
├── constants.py      Coefficients, 15 cost drivers, FPA weights, 14 GSCs
├── utils.py          JSON parsing, formatting, CLI input helpers
├── app.py            optional command-line interface
├── manual.py         CLI manual mode + interactive FPA
├── vercel.json       Vercel routing
├── requirements.txt
├── sample_transcript.txt
└── README.md
```
The UI layers (web and CLI) never do arithmetic — all numbers come from
`cocomo.py` and `fpa.py`, so every interface gives identical results.

---

## References

- Boehm, B. W. (1981). *Software Engineering Economics*. Prentice-Hall.
  (COCOMO model, coefficients and the 15 intermediate effort multipliers.)
- Albrecht, A. J. (1979). "Measuring Application Development Productivity."
  *Proc. IBM Applications Development Symposium*. (Function Points.)
- ISO/IEC 20926:2009. *Software and systems engineering — Software measurement
  — IFPUG functional size measurement method.* (FPA weights, 14 GSCs, VAF.)
- International Function Point Users Group (IFPUG). *Counting Practices Manual.*
- Jones, C. (2008). *Applied Software Measurement* (3rd ed.). McGraw-Hill.
  (Backfiring / LOC-per-function-point ratios — approximate, language dependent.)
- Project Management Institute (2021). *A Guide to the Project Management Body
  of Knowledge (PMBOK Guide)* (7th ed.). PMI. (Estimating under uncertainty;
  contingency vs. management reserve.)

> Estimation models give *indicative* figures, not guarantees. Always sanity-
> check COCOMO/FPA outputs against expert judgement and historical data.
