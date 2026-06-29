"""
web_ui.py
=========
All HTML + CSS rendering for the website lives here, kept separate from the
Flask routes (api/index.py) and from the calculation engine (cocomo.py / fpa.py).

Design direction ("instrument panel"): a precise, engineering-document look.
Numbers are the hero, so all computed figures and the COCOMO formula are set in
a monospace "readout" face; the signature element is the live formula that
substitutes the real values, making the maths fully transparent.
"""

from __future__ import annotations

import html

from constants import (
    COCOMO_COEFFICIENTS,
    COST_DRIVERS,
    FP_TYPE_NAMES,
    HOURS_PER_PERSON_MONTH,
    PROJECT_TYPE_LABELS,
)

# Cost drivers grouped by Boehm's four categories (for the manual form).
DRIVER_GROUPS: dict[str, list[str]] = {
    "Product attributes": ["RELY", "DATA", "CPLX"],
    "Platform attributes": ["TIME", "STOR", "VIRT", "TURN"],
    "Personnel attributes": ["ACAP", "AEXP", "PCAP", "VEXP", "LEXP"],
    "Project attributes": ["MODP", "TOOL", "SCED"],
}


def esc(text: object) -> str:
    return html.escape(str(text), quote=True)


# ---------------------------------------------------------------------------
# Global stylesheet (inlined so it works on Vercel with no static routing)
# ---------------------------------------------------------------------------
STYLE = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root{
  --ink:#10151c; --ink-2:#39424f; --ink-3:#6b7480;
  --line:#e3e7ee; --paper:#eceff4; --surface:#ffffff;
  --accent:#4338ca; --accent-2:#6366f1; --accent-soft:#eef0ff;
  --good:#0f9d6b; --good-soft:#e6f6ef; --warn:#b45309; --warn-soft:#fdf1e3;
  --mono:'IBM Plex Mono',ui-monospace,SFMono-Regular,Menlo,monospace;
  --sans:'Inter',system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
  --display:'Space Grotesk',var(--sans);
  --radius:14px; --shadow:0 1px 2px rgba(16,21,28,.06),0 8px 28px rgba(16,21,28,.07);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  line-height:1.55;font-size:16px;-webkit-font-smoothing:antialiased}
a{color:var(--accent);text-decoration:none}
.wrap{max-width:1040px;margin:0 auto;padding:0 22px}

/* header */
.site-head{background:var(--ink);color:#fff;border-bottom:1px solid #000}
.site-head .wrap{display:flex;align-items:center;justify-content:space-between;height:64px}
.brand{font-family:var(--display);font-weight:700;font-size:1.12rem;letter-spacing:-.01em;color:#fff;display:flex;gap:.55rem;align-items:center}
.brand .dot{width:11px;height:11px;border-radius:3px;background:var(--accent-2);box-shadow:0 0 0 4px rgba(99,102,241,.25)}
.nav{display:flex;gap:4px}
.nav a{color:#c4cad6;font-weight:500;font-size:.92rem;padding:.45rem .8rem;border-radius:8px}
.nav a:hover{color:#fff;background:#ffffff14}
.nav a.active{color:#fff;background:#ffffff1f}

/* hero */
.hero{padding:64px 0 30px}
.eyebrow{font-family:var(--mono);font-size:.78rem;letter-spacing:.16em;text-transform:uppercase;color:var(--accent)}
h1{font-family:var(--display);font-weight:700;font-size:2.5rem;line-height:1.08;letter-spacing:-.02em;margin:.5rem 0 .6rem}
.lede{font-size:1.12rem;color:var(--ink-2);max-width:60ch}
.formula-motif{margin-top:26px;font-family:var(--mono);color:var(--ink-2);background:var(--surface);
  border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow);overflow:auto}
.formula-motif b{color:var(--accent)}

/* mode cards */
.modes{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:34px 0 70px}
.mode{display:block;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);
  padding:26px;box-shadow:var(--shadow);transition:transform .15s ease,border-color .15s ease}
.mode:hover{transform:translateY(-3px);border-color:var(--accent-2)}
.mode .num{font-family:var(--mono);color:var(--accent);font-weight:600;font-size:.85rem}
.mode h3{font-family:var(--display);margin:.4rem 0 .35rem;font-size:1.25rem;color:var(--ink)}
.mode p{margin:0;color:var(--ink-2);font-size:.96rem}
.mode .go{margin-top:16px;display:inline-block;font-weight:600;color:var(--accent)}

/* generic section + cards */
.section{padding:40px 0 70px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius);padding:24px;box-shadow:var(--shadow);margin-bottom:20px}
.card h2{font-family:var(--display);font-size:1.25rem;margin:0 0 14px}
.card h3{font-family:var(--display);font-size:1.02rem;margin:0 0 10px}
.muted{color:var(--ink-2)}

/* forms */
label.field{display:block;font-weight:600;margin:16px 0 6px;font-size:.95rem}
.hint{font-weight:400;color:var(--ink-2);font-size:.85rem}
textarea,input[type=number],select{width:100%;padding:.7rem .8rem;border:1px solid var(--line);
  border-radius:10px;font-size:1rem;font-family:var(--sans);background:#fff;color:var(--ink)}
textarea{min-height:210px;font-family:var(--mono);font-size:.92rem;line-height:1.5;resize:vertical}
select{appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='12' height='12'><path d='M2 4l4 4 4-4' stroke='%2339424f' fill='none' stroke-width='1.5'/></svg>");
  background-repeat:no-repeat;background-position:right .8rem center;padding-right:2rem}
:focus-visible{outline:3px solid var(--accent-soft);outline-offset:1px;border-color:var(--accent)}
.row{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.check{display:flex;align-items:center;gap:.6rem;margin-top:18px;font-weight:600}
.check input{width:18px;height:18px;accent-color:var(--accent)}
.btn{margin-top:22px;display:inline-flex;align-items:center;gap:.5rem;background:var(--accent);color:#fff;
  border:0;border-radius:10px;padding:.8rem 1.4rem;font-size:1rem;font-weight:600;cursor:pointer;font-family:var(--sans)}
.btn:hover{background:var(--accent-2)}
.btn.ghost{background:#fff;color:var(--accent);border:1px solid var(--line)}
.linkbtn{background:none;border:0;color:var(--accent);font-weight:600;cursor:pointer;padding:0;font-size:.92rem}

/* driver group grid in manual form */
.group{margin-top:8px}
.group .glabel{font-family:var(--mono);font-size:.74rem;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin:22px 0 4px}
.driver-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px 18px}
.driver-grid .field{margin-top:6px}

/* readout (the hero result) */
.readout{background:var(--ink);color:#fff;border-radius:var(--radius);padding:26px 28px;box-shadow:var(--shadow);margin-bottom:20px}
.readout .topline{font-family:var(--mono);font-size:.78rem;letter-spacing:.14em;text-transform:uppercase;color:#9aa3b2}
.readout .cost{font-family:var(--mono);font-weight:600;font-size:3rem;line-height:1.05;margin:.2rem 0 .1rem;letter-spacing:-.02em}
.readout .costsub{color:#aeb6c4;font-size:.92rem}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;background:#ffffff1a;border-radius:10px;overflow:hidden;margin-top:22px}
.stat{background:var(--ink);padding:14px 16px}
.stat .k{font-size:.74rem;letter-spacing:.1em;text-transform:uppercase;color:#9aa3b2}
.stat .v{font-family:var(--mono);font-size:1.3rem;font-weight:600;margin-top:3px}
@media(max-width:720px){.stats{grid-template-columns:1fr 1fr}}

/* substituted formula block (signature) */
.formula{font-family:var(--mono);font-size:.95rem;background:#0c1117;color:#e6e9ef;border-radius:12px;padding:18px 20px;overflow:auto;line-height:1.9}
.formula .lbl{color:#7c8aa5}
.formula .res{color:#8ee6b8;font-weight:600}
.formula .op{color:#c4b5fd}

/* factor cards */
.factors{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.factor{border:1px solid var(--line);border-radius:12px;padding:16px}
.factor .ftop{display:flex;justify-content:space-between;align-items:baseline;gap:8px}
.factor .fname{font-weight:600}
.factor .fval{font-family:var(--mono);font-weight:600;color:var(--accent)}
.bar{height:7px;border-radius:99px;background:var(--paper);margin:10px 0 6px;overflow:hidden}
.bar > span{display:block;height:100%;border-radius:99px}
.conf{font-family:var(--mono);font-size:.78rem;color:var(--ink-2)}
.tag{display:inline-block;font-size:.72rem;font-weight:600;padding:.15rem .5rem;border-radius:99px;margin-left:6px}
.tag.ok{background:var(--good-soft);color:var(--good)}
.tag.warn{background:var(--warn-soft);color:var(--warn)}
.chips{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
.chip{font-family:var(--mono);font-size:.74rem;background:var(--accent-soft);color:var(--accent);padding:.2rem .55rem;border-radius:7px}
.reason{margin-top:10px;color:var(--ink-2);font-size:.9rem}

/* tables */
table{width:100%;border-collapse:collapse;font-size:.92rem}
th,td{text-align:left;padding:.6rem .7rem;border-bottom:1px solid var(--line)}
th{font-size:.74rem;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-2);font-weight:600}
td.num,th.num{text-align:right;font-family:var(--mono)}

/* notice */
.notice{border-radius:10px;padding:12px 16px;margin-bottom:18px;font-size:.92rem;font-weight:500;border:1px solid}
.notice.live{background:var(--good-soft);border-color:#bfe9d4;color:#0a6b49}
.notice.demo{background:var(--accent-soft);border-color:#d7d9ff;color:var(--accent)}
.notice.warn{background:var(--warn-soft);border-color:#f4d9b4;color:var(--warn)}

footer{padding:30px 0 50px;color:var(--ink-2);font-size:.85rem}
@media(max-width:720px){.modes,.row,.factors,.driver-grid{grid-template-columns:1fr}h1{font-size:2rem}.readout .cost{font-size:2.3rem}}
@media(prefers-reduced-motion:reduce){*{transition:none!important;scroll-behavior:auto}}
</style>
"""
# CSS is defined above as the STYLE constant.


def _nav(active: str) -> str:
    def link(href, key, text):
        cls = "active" if active == key else ""
        return f'<a class="{cls}" href="{href}">{text}</a>'
    return (
        '<header class="site-head"><div class="wrap">'
        '<a class="brand" href="/"><span class="dot"></span>COCOMO&nbsp;·&nbsp;FPA Estimator</a>'
        '<nav class="nav">'
        + link("/", "home", "Home")
        + link("/analyze", "analyze", "AI Analysis")
        + link("/manual", "manual", "Manual Calculator")
        + "</nav></div></header>"
    )


def render_page(title: str, body: str, active: str = "") -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)}</title>{STYLE}</head><body>"
        f"{_nav(active)}<main>{body}</main>"
        "<footer class='wrap'>Estimates are indicative. COCOMO (Boehm, 1981) · "
        "Function Point Analysis (Albrecht, 1979 / ISO&nbsp;20926).</footer>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def render_landing() -> str:
    body = (
        "<section class='hero wrap'>"
        "<div class='eyebrow'>Software cost estimation</div>"
        "<h1>Turn meeting notes into a defensible cost estimate.</h1>"
        "<p class='lede'>Paste a requirements meeting transcript and let the model infer the "
        "COCOMO parameters and Function Point size — or fill in the figures yourself. "
        "Every number is shown with the maths behind it.</p>"
        "<div class='formula-motif'>Effort = <b>a</b> × KLOC<sup>b</sup> × EAF &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Schedule = <b>c</b> × Effort<sup>d</sup> &nbsp;&nbsp;|&nbsp;&nbsp; "
        "AFP = UFP × (0.65 + 0.01·ΣGSC)</div>"
        "<div class='modes'>"
        "<a class='mode' href='/analyze'><div class='num'>MODE 01</div>"
        "<h3>AI Analysis</h3><p>The LLM reads your meeting notes, infers every COCOMO factor "
        "with evidence and confidence, sizes the system via Function Points, and produces the full report.</p>"
        "<span class='go'>Analyse notes →</span></a>"
        "<a class='mode' href='/manual'><div class='num'>MODE 02</div>"
        "<h3>Manual Calculator</h3><p>Choose the project type, enter KLOC, and rate every cost driver "
        "yourself. The app computes EAF, effort, schedule, team size and cost.</p>"
        "<span class='go'>Open calculator →</span></a>"
        "</div></section>"
    )
    return render_page("COCOMO + FPA Estimator", body, "home")


SAMPLE_HINT = (
    "Project kick-off for an online grocery platform. Customers browse products, "
    "add to basket and pay online via a payment gateway (real financial "
    "transactions, must be reliable). Needs user authentication, a product "
    "catalogue with a database, an order service, and an admin dashboard with "
    "reports. Integrates a delivery-tracking API and email notifications. "
    "Standard business web app, not embedded or real-time. Team knows the domain "
    "but two developers are junior. Modern practices and good tooling. Mild "
    "schedule pressure for a holiday launch. Roughly 45,000 lines of code."
)


def render_analyze_form(prefill: str = "", monthly: float = 8000.0,
                        demo_default: bool = True) -> str:
    checked = "checked" if demo_default else ""
    body = (
        "<section class='section wrap'>"
        "<div class='eyebrow'>Mode 01</div><h1 style='font-size:1.9rem'>AI Analysis</h1>"
        "<p class='lede'>Paste your meeting notes. The model infers each factor, shows its "
        "evidence and confidence, and computes the estimate.</p>"
        "<form method='post' action='/analyze' class='card' style='margin-top:22px'>"
        "<label class='field' for='transcript'>Meeting notes / transcript</label>"
        f"<textarea id='transcript' name='transcript' placeholder='Paste the meeting notes here…'>{esc(prefill)}</textarea>"
        "<button type='button' class='linkbtn' onclick=\"document.getElementById('transcript').value=SAMPLE\">"
        "Insert sample notes</button>"
        "<div class='row'>"
        "<div><label class='field' for='monthly'>Cost per developer / month "
        "<span class='hint'>(£)</span></label>"
        f"<input type='number' step='100' id='monthly' name='monthly' value='{int(monthly)}'></div>"
        "<div><label class='field' for='kloc'>KLOC override <span class='hint'>(optional)</span></label>"
        "<input type='number' step='0.1' id='kloc' name='kloc' placeholder='auto (from Function Points)'></div>"
        "</div>"
        f"<label class='check'><input type='checkbox' name='demo' {checked}> "
        "Demo mode <span class='hint'>(offline analyzer — no API key needed)</span></label>"
        "<button class='btn' type='submit'>Generate estimate →</button>"
        "</form></section>"
        f"<script>const SAMPLE={_js_str(SAMPLE_HINT)};</script>"
    )
    return render_page("AI Analysis · COCOMO + FPA", body, "analyze")


def render_manual_form() -> str:
    # Project type options
    pt_opts = "".join(
        f"<option value='{k}'>{v}</option>" for k, v in PROJECT_TYPE_LABELS.items()
    )
    # Driver groups
    groups_html = ""
    for group_name, codes in DRIVER_GROUPS.items():
        fields = ""
        for code in codes:
            d = COST_DRIVERS[code]
            opts = "".join(
                f"<option value='{esc(r)}'{' selected' if r=='Nominal' else ''}>"
                f"{esc(r)} (×{m:.2f})</option>"
                for r, m in d["ratings"].items()
            )
            fields += (
                "<div class='field'>"
                f"<label class='field' for='{code}'>{esc(d['name'])} "
                f"<span class='hint'>{code}</span></label>"
                f"<select id='{code}' name='{code}'>{opts}</select></div>"
            )
        groups_html += (
            f"<div class='group'><div class='glabel'>{esc(group_name)}</div>"
            f"<div class='driver-grid'>{fields}</div></div>"
        )

    body = (
        "<section class='section wrap'>"
        "<div class='eyebrow'>Mode 02</div><h1 style='font-size:1.9rem'>Manual COCOMO Calculator</h1>"
        "<p class='lede'>Select the project type, enter the size, and rate every effort multiplier. "
        "The app computes the EAF, effort, schedule, average staff and cost.</p>"
        "<form method='post' action='/manual' class='card' style='margin-top:22px'>"
        "<div class='row'>"
        f"<div><label class='field' for='ptype'>Project type</label><select id='ptype' name='ptype'>{pt_opts}</select></div>"
        "<div><label class='field' for='kloc'>Size in KLOC <span class='hint'>(thousands of lines)</span></label>"
        "<input type='number' step='0.1' min='0.1' id='kloc' name='kloc' value='45' required></div>"
        "</div>"
        "<label class='field' for='monthly'>Cost per developer / month <span class='hint'>(£)</span></label>"
        "<input type='number' step='100' id='monthly' name='monthly' value='8000'>"
        "<h3 style='margin-top:26px;font-family:var(--display)'>Effort multipliers (cost drivers)</h3>"
        f"{groups_html}"
        "<button class='btn' type='submit'>Compute estimate →</button>"
        "</form></section>"
    )
    return render_page("Manual Calculator · COCOMO", body, "manual")


# ---------------------------------------------------------------------------
# Results rendering (shared by AI + manual)
# ---------------------------------------------------------------------------
def _readout(result) -> str:
    c = result.currency
    return (
        "<div class='readout'>"
        "<div class='topline'>Estimated total cost</div>"
        f"<div class='cost'>{c}{result.cost:,.0f}</div>"
        f"<div class='costsub'>{PROJECT_TYPE_LABELS.get(result.project_type, result.project_type)} project · "
        f"{result.kloc:.1f} KLOC · EAF {result.eaf:.3f}</div>"
        "<div class='stats'>"
        f"<div class='stat'><div class='k'>Effort</div><div class='v'>{result.effort_pm:.1f}<span style='font-size:.7rem;color:#9aa3b2'> PM</span></div></div>"
        f"<div class='stat'><div class='k'>Schedule</div><div class='v'>{result.schedule_months:.1f}<span style='font-size:.7rem;color:#9aa3b2'> mo</span></div></div>"
        f"<div class='stat'><div class='k'>Avg team</div><div class='v'>{result.average_staff:.1f}<span style='font-size:.7rem;color:#9aa3b2'> dev</span></div></div>"
        f"<div class='stat'><div class='k'>Effort hours</div><div class='v'>{result.effort_hours:,.0f}</div></div>"
        "</div></div>"
    )


def _formula(result) -> str:
    co = COCOMO_COEFFICIENTS[result.project_type]
    a, b, cc, d = co["a"], co["b"], co["c"], co["d"]
    return (
        "<div class='card'><h2>How this was calculated</h2>"
        "<div class='formula'>"
        f"<span class='lbl'>EAF</span>   <span class='op'>=</span> ∏(multipliers) <span class='op'>=</span> <span class='res'>{result.eaf:.3f}</span><br>"
        f"<span class='lbl'>Effort</span> <span class='op'>=</span> a·KLOC^b·EAF "
        f"<span class='op'>=</span> {a}·{result.kloc:.1f}^{b}·{result.eaf:.3f} "
        f"<span class='op'>=</span> <span class='res'>{result.effort_pm:.2f} PM</span><br>"
        f"<span class='lbl'>Time</span>   <span class='op'>=</span> c·Effort^d "
        f"<span class='op'>=</span> {cc}·{result.effort_pm:.1f}^{d} "
        f"<span class='op'>=</span> <span class='res'>{result.schedule_months:.2f} months</span><br>"
        f"<span class='lbl'>Staff</span>  <span class='op'>=</span> Effort÷Time "
        f"<span class='op'>=</span> {result.effort_pm:.1f}÷{result.schedule_months:.1f} "
        f"<span class='op'>=</span> <span class='res'>{result.average_staff:.1f} developers</span><br>"
        f"<span class='lbl'>Hours</span>  <span class='op'>=</span> Effort×{HOURS_PER_PERSON_MONTH} "
        f"<span class='op'>=</span> <span class='res'>{result.effort_hours:,.0f} h</span>"
        "</div></div>"
    )


def _driver_table(result) -> str:
    if not result.driver_ratings:
        return ""
    rows = ""
    for code, rating in result.driver_ratings.items():
        d = COST_DRIVERS.get(code, {})
        mult = d.get("ratings", {}).get(rating, 1.0)
        rows += (f"<tr><td>{esc(d.get('name', code))}</td><td>{esc(rating)}</td>"
                 f"<td class='num'>×{mult:.2f}</td></tr>")
    return ("<div class='card'><h2>Cost drivers</h2><table>"
            "<tr><th>Driver</th><th>Rating</th><th class='num'>Multiplier</th></tr>"
            f"{rows}</table></div>")


def _factor_grid(analysis: dict) -> str:
    labels = {
        "project_type": "Project type", "complexity": "Complexity",
        "required_reliability": "Required reliability",
        "programmer_capability": "Programmer capability",
        "analyst_capability": "Analyst capability",
        "platform_constraints": "Platform constraints",
        "memory_constraints": "Memory constraints",
        "storage_constraints": "Storage constraints",
        "schedule_constraints": "Schedule constraints",
        "team_experience": "Team experience",
        "modern_practices": "Modern practices",
        "software_tools": "Software tools",
    }
    cards = ""
    for key, label in labels.items():
        f = analysis.get(key)
        if not f:
            continue
        conf = int(f.get("confidence", 0) or 0)
        ok = conf >= 80
        color = "var(--good)" if ok else "var(--warn)"
        tag = ("<span class='tag ok'>confident</span>" if ok
               else "<span class='tag warn'>confirm</span>")
        chips = "".join(f"<span class='chip'>{esc(e)}</span>"
                        for e in (f.get("evidence") or [])[:5])
        cards += (
            "<div class='factor'>"
            f"<div class='ftop'><span class='fname'>{esc(label)}{tag}</span>"
            f"<span class='fval'>{esc(f.get('value'))}</span></div>"
            f"<div class='bar'><span style='width:{conf}%;background:{color}'></span></div>"
            f"<div class='conf'>{conf}% confidence</div>"
            f"<div class='chips'>{chips}</div>"
            f"<div class='reason'>{esc(f.get('reasoning',''))}</div>"
            "</div>"
        )
    return ("<div class='card'><h2>What the model inferred</h2>"
            "<p class='muted' style='margin-top:-6px'>Each factor shows the evidence found in your notes "
            "and a confidence score. Amber factors fell below 80% and would normally be confirmed.</p>"
            f"<div class='factors'>{cards}</div></div>")


def _fpa_block(fpa_result, kloc_note: str) -> str:
    rows = ""
    for ftype, name in FP_TYPE_NAMES.items():
        band = fpa_result.counts.get(ftype, {})
        rows += (f"<tr><td>{esc(name)} <span class='muted'>({ftype})</span></td>"
                 f"<td class='num'>{band.get('low',0)}</td>"
                 f"<td class='num'>{band.get('average',0)}</td>"
                 f"<td class='num'>{band.get('high',0)}</td></tr>")
    return (
        "<div class='card'><h2>Function Point Analysis</h2>"
        f"<p class='muted' style='margin-top:-6px'>{esc(kloc_note)}</p>"
        "<table><tr><th>Function type</th><th class='num'>Low</th><th class='num'>Avg</th><th class='num'>High</th></tr>"
        f"{rows}</table>"
        "<table style='margin-top:14px'>"
        f"<tr><td>Unadjusted FP (UFP)</td><td class='num'>{fpa_result.ufp}</td></tr>"
        f"<tr><td>Value Adjustment Factor (VAF)</td><td class='num'>{fpa_result.vaf:.2f}</td></tr>"
        f"<tr><td>Adjusted FP (AFP)</td><td class='num'>{fpa_result.afp:.1f}</td></tr>"
        f"<tr><td>Backfiring ({esc(fpa_result.language)})</td><td class='num'>{fpa_result.loc_per_fp} LOC/FP</td></tr>"
        f"<tr><td>Estimated size</td><td class='num'>{fpa_result.kloc:.2f} KLOC</td></tr>"
        "</table></div>"
    )


def render_results(result, *, mode: str, notice: tuple[str, str] | None = None,
                   analysis: dict | None = None, fpa_result=None,
                   kloc_note: str = "", back_href: str = "/analyze") -> str:
    parts = ["<section class='section wrap'>",
             "<div class='eyebrow'>Result</div>",
             f"<h1 style='font-size:1.9rem'>{esc(mode)} estimate</h1>"]
    if notice:
        kind, msg = notice
        parts.append(f"<div class='notice {kind}'>{esc(msg)}</div>")
    parts.append(_readout(result))
    parts.append(_formula(result))
    if analysis:
        parts.append(_factor_grid(analysis))
    if fpa_result is not None:
        parts.append(_fpa_block(fpa_result, kloc_note))
    parts.append(_driver_table(result))
    parts.append(
        f"<a class='btn ghost' href='{back_href}'>← Run another estimate</a></section>"
    )
    return render_page(f"{mode} estimate · COCOMO + FPA", "".join(parts))


def render_error(message: str, back_href: str = "/") -> str:
    body = (
        "<section class='section wrap'><h1 style='font-size:1.7rem'>Something needs fixing</h1>"
        f"<div class='notice warn'>{esc(message)}</div>"
        f"<a class='btn ghost' href='{back_href}'>← Go back</a></section>"
    )
    return render_page("Error", body)


def _js_str(text: str) -> str:
    """Safely embed a Python string as a JS string literal."""
    import json
    return json.dumps(text)
