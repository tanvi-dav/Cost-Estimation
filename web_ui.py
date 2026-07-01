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
    COST_DRIVERS,
    DEFAULT_PROJECT_CATEGORY,
    HOURS_PER_PERSON_MONTH,
    PROJECT_CATEGORIES,
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

/* cost-driver rating grid (table of radio buttons, like Boehm's table) */
.driver-table-wrap{overflow:auto;margin-top:10px;border:1px solid var(--line);border-radius:var(--radius)}
table.driver-table{width:100%;border-collapse:collapse;font-size:.86rem}
table.driver-table th,table.driver-table td{padding:.5rem .6rem;border-bottom:1px solid var(--line);text-align:center}
table.driver-table thead th{background:var(--paper);font-size:.7rem;letter-spacing:.06em;text-transform:uppercase;color:var(--ink-2)}
table.driver-table td.dname{text-align:left;font-weight:600;white-space:nowrap}
table.driver-table td.dname .hint{display:block;font-weight:400;font-family:var(--mono);font-size:.72rem;color:var(--ink-3)}
table.driver-table tbody tr.gsub td{background:var(--paper);font-family:var(--mono);font-size:.7rem;letter-spacing:.1em;text-transform:uppercase;color:var(--accent);text-align:left;font-weight:700}
table.driver-table td.cell{cursor:pointer}
table.driver-table td.cell.empty{cursor:default;color:var(--line)}
table.driver-table td.cell input{accent-color:var(--accent);width:16px;height:16px}
table.driver-table td.cell .mult{display:block;font-family:var(--mono);font-size:.68rem;color:var(--ink-3);margin-top:2px}

/* category cards (Organic / Semi-Detached / Embedded) */
.cat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:8px}
.cat-card{position:relative;border:1px solid var(--line);border-radius:12px;padding:14px 14px 12px;cursor:pointer;background:#fff}
.cat-card input{position:absolute;top:12px;right:12px;width:16px;height:16px;accent-color:var(--accent)}
.cat-card .cname{font-weight:700;font-family:var(--display)}
.cat-card .cdesc{font-size:.8rem;color:var(--ink-2);margin-top:4px}
.cat-card .ccoef{font-family:var(--mono);font-size:.72rem;color:var(--accent);margin-top:8px}
.cat-card:has(input:checked){border-color:var(--accent);box-shadow:0 0 0 2px var(--accent-soft)}
@media(max-width:720px){.cat-grid{grid-template-columns:1fr}}

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
.source-link{display:inline-block;margin-top:10px;font-size:.82rem;font-weight:600;color:var(--accent)}
.transcript-source{white-space:pre-wrap;font-family:var(--mono);font-size:.9rem;line-height:1.75;
  background:#fbfcff;border:1px solid var(--line);border-radius:12px;padding:18px;max-height:430px;overflow:auto}
.src-mark{border-radius:4px;padding:.08rem .18rem;color:#10151c;font-weight:600}
.legend{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 16px}
.legend-item{font-size:.78rem;font-weight:600;border-radius:999px;padding:.18rem .55rem;color:#10151c}

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
            '<a class="brand" href="/"><span class="dot"></span>COCOMO&nbsp;Estimator&nbsp;</a>'
            '<nav class="nav">'
            + link("/", "home", "Home")
            + link("/analyze", "analyze", "Analyse Notes")
            + link("/manual", "manual", "Manual Calculator")
            + "</nav></div></header>"
    )


def render_page(title: str, body: str, active: str = "") -> str:
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>{esc(title)}</title>{STYLE}</head><body>"
        f"{_nav(active)}<main>{body}</main>"
        "<footer class='wrap'>Estimates are indicative. COCOMO (Boehm, 1981).</footer>"
        "</body></html>"
    )


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def render_landing() -> str:
    body = (
        "<section class='hero wrap'>"
        "<div class='eyebrow'>Software cost estimation </div>"
        "<h1>Turn meeting notes into a cost estimate, or build one by hand.</h1>"
        "<p class='lede'>Paste a requirements meeting transcript and a keyword-based demo "
        "analyser infers the COCOMO factors with evidence and confidence — or fill in the "
        "figures yourself with the Basic / Intermediate calculator. Every number is shown "
        "with the maths behind it.</p>"
        "<div class='formula-motif'>Effort = <b>a</b> × KLOC<sup>b</sup> × EAF &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Schedule = <b>c</b> × Effort<sup>d</sup> &nbsp;&nbsp;|&nbsp;&nbsp; "
        "Cost = Effort × Avg. Salary</div>"
        "<div class='modes'>"
        "<a class='mode' href='/analyze'><div class='num'>MODE 01</div>"
        "<h3>Analyse Notes </h3><p>A deterministic keyword analyser scans your notes "
        "and suggests each factor with evidence and a confidence score — no live AI call, "
        "fully offline and reproducible.</p>"
        "<span class='go'>Analyse notes →</span></a>"
        "<a class='mode' href='/manual'><div class='num'>MODE 02</div>"
        "<h3>Manual Calculator</h3><p>Choose Basic (size only) or Intermediate (size + cost "
        "drivers) and enter the figures yourself.</p>"
        "<span class='go'>Open calculator →</span></a>"
        "</div></section>"
    )
    return render_page("COCOMO Estimator (Demo)", body, "home")


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


def render_analyze_form(prefill: str = "", monthly: float = 8000.0) -> str:
    body = (
        "<section class='section wrap'>"
        "<div class='eyebrow'>Mode 01</div><h1 style='font-size:1.9rem'>Analyse Meeting Notes</h1>"
        "<p class='lede'>Paste your meeting notes. A deterministic, keyword-based demo "
        "analyser infers each factor, shows its evidence and confidence, and computes "
        "the estimate — no live AI call is made.</p>"
        "<form method='post' action='/analyze' class='card' style='margin-top:22px'>"
        "<label class='field' for='transcript'>Meeting notes / transcript</label>"
        f"<textarea id='transcript' name='transcript' placeholder='Paste the meeting notes here…'>{esc(prefill)}</textarea>"
        "<button type='button' class='linkbtn' onclick=\"document.getElementById('transcript').value=SAMPLE\">"
        "Insert sample notes</button>"
        "<div class='row'>"
        "<div><label class='field' for='monthly'>Average developer salary / month "
        "<span class='hint'>(£)</span></label>"
        f"<input type='number' step='100' id='monthly' name='monthly' value='{int(monthly)}'></div>"
        "<div><label class='field' for='kloc'>KLOC override <span class='hint'>(optional)</span></label>"
        "<input type='number' step='0.1' id='kloc' name='kloc' placeholder='auto (from notes)'></div>"
        "</div>"
        "<button class='btn' type='submit'>Generate estimate →</button>"
        "</form></section>"
        f"<script>const SAMPLE={_js_str(SAMPLE_HINT)};</script>"
    )
    return render_page("Analyse Notes · COCOMO", body, "analyze")


def _category_cards_html(selected: str = DEFAULT_PROJECT_CATEGORY) -> str:
    cards = ""
    for key, cat in PROJECT_CATEGORIES.items():
        checked = " checked" if key == selected else ""
        cards += (
            f"<label class='cat-card'><input type='radio' name='category' value='{key}'{checked}>"
            f"<div class='cname'>{esc(cat['label'])}</div>"
            f"<div class='cdesc'>{esc(cat['description'])}</div>"
            f"<div class='ccoef'>a={cat['a_basic']} (Basic) / {cat['a_intermediate']} (Interm.)"
            f" &nbsp;b={cat['b']} c={cat['c']} d={cat['d']}</div>"
            "</label>"
        )
    return f"<div class='cat-grid'>{cards}</div>"


# All distinct rating labels across every driver, in Boehm's canonical order
# (used as the column headers of the cost-driver grid).
ALL_RATING_LABELS = ["Very Low", "Low", "Nominal", "High", "Very High", "Extra High"]


def _driver_grid_table_html() -> str:
    """Render every cost driver as one row of a single grid/table, grouped by
    attribute category, with a radio button per valid rating column (mirrors
    the Boehm cost-driver table)."""
    header = "".join(f"<th>{esc(r)}</th>" for r in ALL_RATING_LABELS)
    rows = ""
    for group_name, codes in DRIVER_GROUPS.items():
        rows += f"<tr class='gsub'><td colspan='{len(ALL_RATING_LABELS) + 1}'>{esc(group_name)}</td></tr>"
        for code in codes:
            d = COST_DRIVERS[code]
            cells = ""
            for label in ALL_RATING_LABELS:
                if label in d["ratings"]:
                    checked = " checked" if label == "Nominal" else ""
                    mult = d["ratings"][label]
                    cells += (
                        f"<td class='cell'><label>"
                        f"<input type='radio' name='{code}' value='{esc(label)}'{checked}>"
                        f"<span class='mult'>×{mult:.2f}</span></label></td>"
                    )
                else:
                    cells += "<td class='cell empty'>—</td>"
            rows += (
                "<tr><td class='dname'>"
                f"{esc(d['name'])}<span class='hint'>{code}</span></td>{cells}</tr>"
            )
    return (
        "<div class='driver-table-wrap'><table class='driver-table'>"
        f"<thead><tr><th></th>{header}</tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
    )


def render_manual_form() -> str:
    # Project type options
    pt_opts = "".join(
        f"<option value='{k}'>{v}</option>" for k, v in PROJECT_TYPE_LABELS.items()
    )

    body = (
        "<section class='section wrap'>"
        "<div class='eyebrow'>Demo</div><h1 style='font-size:1.9rem'>Manual COCOMO Calculator</h1>"
        "<p class='lede'>Choose Basic or Intermediate, pick the project category (sets a/b/c/d), "
        "enter the size, and (for Intermediate) rate every effort multiplier on the grid below. "
        "The app computes the EAF, effort, schedule, average staff and cost.</p>"
        "<form method='post' action='/manual' class='card' style='margin-top:22px'>"
        "<div class='row'>"
        "<div><label class='field' for='ptype'>Option</label>"
        f"<select id='ptype' name='ptype' onchange=\"document.getElementById('drivers').style.display="
        "this.value==='intermediate'?'block':'none'\">"
        f"{pt_opts}</select></div>"
        "<div><label class='field' for='kloc'>Size in KLOC <span class='hint'>(thousands of lines)</span></label>"
        "<input type='number' step='0.1' min='0.1' id='kloc' name='kloc' value='45' required></div>"
        "</div>"
        "<label class='field'>Project category <span class='hint'>(sets a, b, c, d)</span></label>"
        f"{_category_cards_html()}"
        "<label class='field' for='monthly'>Average developer salary / month <span class='hint'>(£)</span></label>"
        "<input type='number' step='100' id='monthly' name='monthly' value='8000'>"
        "<div id='drivers' style='display:none'>"
        "<h3 style='margin-top:26px;font-family:var(--display)'>Effort multipliers (cost drivers)</h3>"
        "<p class='muted' style='margin-top:-6px'>Pick one rating per row.</p>"
        f"{_driver_grid_table_html()}"
        "</div>"
        "<button class='btn' type='submit'>Compute estimate →</button>"
        "</form></section>"
    )
    return render_page("Manual Calculator · COCOMO", body, "manual")


# ---------------------------------------------------------------------------
# Results rendering
# ---------------------------------------------------------------------------
def _readout(result) -> str:
    c = result.currency
    return (
        "<div class='readout'>"
        "<div class='topline'>Estimated total cost</div>"
        f"<div class='cost'>{c}{result.cost:,.0f}</div>"
        f"<div class='costsub'>{PROJECT_TYPE_LABELS.get(result.project_type, result.project_type)} · "
        f"{PROJECT_CATEGORIES.get(result.category, {}).get('label', result.category)} · "
        f"{result.kloc:.1f} KLOC · EAF {result.eaf:.3f}</div>"
        "<div class='stats'>"
        f"<div class='stat'><div class='k'>Effort</div><div class='v'>{result.effort_pm:.1f}<span style='font-size:.7rem;color:#9aa3b2'> PM</span></div></div>"
        f"<div class='stat'><div class='k'>Schedule</div><div class='v'>{result.schedule_months:.1f}<span style='font-size:.7rem;color:#9aa3b2'> mo</span></div></div>"
        f"<div class='stat'><div class='k'>Avg team</div><div class='v'>{result.average_staff:.1f}<span style='font-size:.7rem;color:#9aa3b2'> dev</span></div></div>"
        f"<div class='stat'><div class='k'>Effort hours</div><div class='v'>{result.effort_hours:,.0f}</div></div>"
        "</div></div>"
    )


def _formula(result) -> str:
    co = PROJECT_CATEGORIES.get(result.category, PROJECT_CATEGORIES[DEFAULT_PROJECT_CATEGORY])
    a_key = "a_intermediate" if result.project_type == "intermediate" else "a_basic"
    a, b, cc, d = co[a_key], co["b"], co["c"], co["d"]
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
        driver = COST_DRIVERS.get(code, {})
        multiplier = driver.get("ratings", {}).get(rating, 1.0)
        rows += (
            f"<tr><td>{esc(driver.get('name', code))}</td>"
            f"<td>{esc(rating)}</td>"
            f"<td class='num'>×{multiplier:.2f}</td></tr>"
        )

    return (
        "<div class='card'><h2>Cost drivers</h2><table>"
        "<tr><th>Driver</th><th>Rating</th><th class='num'>Multiplier</th></tr>"
        f"{rows}</table></div>"
    )


SOURCE_COLOURS = [
    "#fde68a", "#bfdbfe", "#bbf7d0", "#fecaca", "#ddd6fe", "#fed7aa",
    "#bae6fd", "#fbcfe8", "#ccfbf1", "#e9d5ff", "#d9f99d", "#c7d2fe",
]


def _analysis_labels() -> dict[str, str]:
    """Factor labels for the demo analyser dashboard.

    These are pulled straight from ``COST_DRIVERS`` (the same source the
    Manual Intermediate cost-driver table uses) so the two pages always
    show identical names for the same factor.
    """
    return {
        "project_type": "Project type",
        "category": "Category",
        "complexity": COST_DRIVERS["CPLX"]["name"],
        "required_reliability": COST_DRIVERS["RELY"]["name"],
        "programmer_capability": COST_DRIVERS["PCAP"]["name"],
        "analyst_capability": COST_DRIVERS["ACAP"]["name"],
        "platform_constraints": COST_DRIVERS["TIME"]["name"],
        "memory_constraints": COST_DRIVERS["STOR"]["name"],
        "storage_constraints": COST_DRIVERS["DATA"]["name"],
        "schedule_constraints": COST_DRIVERS["SCED"]["name"],
        "team_experience": COST_DRIVERS["AEXP"]["name"],
        "modern_practices": COST_DRIVERS["MODP"]["name"],
        "software_tools": COST_DRIVERS["TOOL"]["name"],
        "kloc": "KLOC",
    }


def _source_colour(index: int) -> str:
    return SOURCE_COLOURS[index % len(SOURCE_COLOURS)]


def _factor_grid(analysis: dict) -> str:
    labels = _analysis_labels()
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
        source_link = ""
        if f.get("source_spans"):
            source_link = f"<a class='source-link' href='#src-{esc(key)}'>View highlighted source ↓</a>"
        cards += (
            "<div class='factor'>"
            f"<div class='ftop'><span class='fname'>{esc(label)}{tag}</span>"
            f"<span class='fval'>{esc(f.get('value'))}</span></div>"
            f"<div class='bar'><span style='width:{conf}%;background:{color}'></span></div>"
            f"<div class='conf'>{conf}% confidence</div>"
            f"<div class='chips'>{chips}</div>"
            f"<div class='reason'>{esc(f.get('reasoning',''))}</div>"
            f"{source_link}"
            "</div>"
        )
    return ("<div class='card'><h2>What the analyser inferred</h2>"
            "<p class='muted' style='margin-top:-6px'>Each factor shows the evidence found in your notes "
            "and a confidence score. Amber factors fell below 80% and would normally be confirmed.</p>"
            f"<div class='factors'>{cards}</div></div>")


def _highlighted_transcript(transcript: str, analysis: dict) -> str:
    """Render the original transcript with colour-coded source spans."""
    if not transcript:
        return ""

    labels = _analysis_labels()
    spans: list[dict] = []

    for idx, (key, label) in enumerate(labels.items()):
        factor = analysis.get(key) or {}
        for span in factor.get("source_spans") or []:
            try:
                start = int(span["start"])
                end = int(span["end"])
            except (KeyError, TypeError, ValueError):
                continue

            if start < 0 or end <= start or end > len(transcript):
                continue

            spans.append({
                "start": start,
                "end": end,
                "key": key,
                "label": label,
                "colour": _source_colour(idx),
            })

    if not spans:
        return (
            "<div class='card'><h2>Source transcript</h2>"
            "<p class='muted'>No exact source spans were returned for this analysis.</p>"
            f"<div class='transcript-source'>{esc(transcript)}</div></div>"
        )

    spans.sort(key=lambda s: (s["start"], -(s["end"] - s["start"])))
    filtered: list[dict] = []
    last_end = -1
    for span in spans:
        if span["start"] >= last_end:
            filtered.append(span)
            last_end = span["end"]

    legend = ""
    seen: set[str] = set()
    for span in filtered:
        if span["key"] in seen:
            continue
        seen.add(span["key"])
        legend += (
            f"<span class='legend-item' style='background:{span['colour']}'>"
            f"{esc(span['label'])}</span>"
        )

    html_parts: list[str] = []
    cursor = 0
    used_ids: set[str] = set()
    for span in filtered:
        html_parts.append(esc(transcript[cursor:span["start"]]))
        marked = esc(transcript[span["start"]:span["end"]])
        mark_id = f"src-{span['key']}" if span["key"] not in used_ids else ""
        used_ids.add(span["key"])
        id_attr = f" id='{esc(mark_id)}'" if mark_id else ""
        html_parts.append(
            f"<mark{id_attr} class='src-mark' "
            f"style='background:{span['colour']}' "
            f"title='{esc(span['label'])}'>{marked}</mark>"
        )
        cursor = span["end"]
    html_parts.append(esc(transcript[cursor:]))

    return (
        "<div class='card'><h2>Source transcript</h2>"
        "<p class='muted' style='margin-top:-6px'>Highlighted text shows the exact transcript phrases "
        "used to infer each automated parameter.</p>"
        f"<div class='legend'>{legend}</div>"
        f"<div class='transcript-source'>{''.join(html_parts)}</div></div>"
    )

def render_results(result, *, mode: str, notice: tuple[str, str] | None = None,
                   analysis: dict | None = None, transcript: str = "",
                   kloc_note: str = "",
                   back_href: str = "/analyze") -> str:
    parts = ["<section class='section wrap'>",
             "<div class='eyebrow'>Result</div>",
             f"<h1 style='font-size:1.9rem'>{esc(mode)} estimate</h1>"]
    if notice:
        kind, msg = notice
        parts.append(f"<div class='notice {kind}'>{esc(msg)}</div>")
    if kloc_note:
        parts.append(f"<p class='muted'>{esc(kloc_note)}</p>")
    parts.append(_readout(result))
    parts.append(_formula(result))
    if analysis:
        parts.append(_factor_grid(analysis))
        parts.append(_highlighted_transcript(transcript, analysis))
    parts.append(_driver_table(result))
    parts.append(
        f"<a class='btn ghost' href='{back_href}'>← Run another estimate</a></section>"
    )
    return render_page(f"{mode} estimate · COCOMO", "".join(parts))


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