"""slides_maker.py — build a self-contained HTML slide deck for the lake demo.

Generates a ``slides/`` folder containing one self-contained ``.html`` file per
slide (plus an ``index.html`` contents page). Each slide inlines its own CSS and
any diagram SVG, so the files work offline by simply double-clicking — no server,
no build step, no external assets.

Content is curated from the ``architecture/`` docs and the ``media/`` SVG
diagrams so the deck can be used directly for a session presentation.

Navigation:
* On-screen **Prev / Contents / Next** buttons.
* Keyboard: ``->`` / ``Space`` / ``PageDown`` = next, ``<-`` / ``PageUp`` = prev,
  ``Home`` / ``o`` = contents.
* A progress bar and "slide N / total" counter.

Usage::

    python slides_maker.py

Standard library only (matches the rest of this project).
"""

from __future__ import annotations

import html
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MEDIA_DIR = os.path.join(HERE, "media")
SLIDES_DIR = os.path.join(HERE, "slides")

DECK_TITLE = "Data Lake Simulation — Medallion, Ontology & Convergence"
MAX_SLIDES = 15
CONTACT = "George Gergues"


# ---------------------------------------------------------------------------
# Slide content (curated from architecture/*.md and media/*.svg)
# ---------------------------------------------------------------------------
# Each slide is a dict:
#   title  : big heading
#   kicker : small label above the title
#   body   : HTML for the text column (bullets, tables, etc.)
#   svg    : filename in media/ to inline as the diagram (or None)
#   note   : optional one-line speaker takeaway shown in a callout

SLIDES: list[dict] = [
    {
        "kicker": "Session deck",
        "title": "From Raw Files to Trustworthy Data",
        "body": """
<p class="lead">A tiny, fully runnable data-lake simulation that teaches the
<strong>medallion architecture</strong> — bronze → silver → gold — using nothing
but the Python standard library.</p>
<ul>
  <li>Two real source systems: <strong>Orders (CSV)</strong> and
      <strong>Invoicing (SOAP/XML)</strong>.</li>
  <li>They converge into <strong>one clean table</strong> at the silver layer.</li>
  <li>No Spark, no cloud, no installs — focus on the <em>concepts</em>.</li>
</ul>
<p class="run"><code>python run.py --stage all --reset</code></p>
""",
        "svg": "01-overview-medallion-flow.svg",
        "note": "Headline lesson: bronze/silver/gold does not care about file format.",
    },
    {
        "kicker": "The problem",
        "title": "Why Layers at All?",
        "body": """
<p>Raw operational data is messy, duplicated, and arrives in many shapes. We
refine it in stages, and data only ever flows <strong>downstream</strong>.</p>
<ul>
  <li><strong>Reproducibility</strong> — cleaning logic changed? Rebuild silver &
      gold from the untouched bronze copy.</li>
  <li><strong>Debuggability</strong> — trace a wrong number back, layer by layer,
      to the exact raw record.</li>
  <li><strong>Separation of concerns</strong> — ingestion, quality, and business
      logic live in different places.</li>
</ul>
""",
        "svg": None,
        "note": "Each layer has one job; never lose the original.",
    },
    {
        "kicker": "The pattern",
        "title": "The Medallion Architecture",
        "body": """
<table class="mini">
  <thead><tr><th>Layer</th><th>Job</th><th>Quality</th></tr></thead>
  <tbody>
    <tr><td><span class="pill bronze">Bronze</span></td>
        <td>Store source data <em>exactly</em> as received + ingestion metadata.</td>
        <td>Low (messy)</td></tr>
    <tr><td><span class="pill silver">Silver</span></td>
        <td>Clean, type, dedupe, validate — one schema everyone trusts.</td>
        <td>Medium / High</td></tr>
    <tr><td><span class="pill gold">Gold</span></td>
        <td>Aggregate & model for a specific business question.</td>
        <td>High (ready)</td></tr>
  </tbody>
</table>
<p>The pattern is <strong>format-agnostic</strong> and supports
<strong>many sources at once</strong> — each keeps its native format in bronze
and converges at silver.</p>
""",
        "svg": "01-overview-medallion-flow.svg",
        "note": "Raw → refined, one direction only.",
    },
    {
        "kicker": "The twist",
        "title": "Two Sources, On Purpose",
        "body": """
<p>Real platforms integrate many systems. This demo ships two very different ones:</p>
<ul>
  <li><span class="pill csv">Orders</span> — an e-commerce system emitting
      <strong>CSV</strong> rows (one row = one sale).</li>
  <li><span class="pill xml">Invoicing</span> — a SOAP middleware emitting
      <strong>XML</strong> envelopes (one document = many line items).</li>
</ul>
<p>Different formats, different shapes, different quirks — yet they describe the
<strong>same business event</strong>: a sale.</p>
""",
        "svg": None,
        "note": "Seeing a CSV feed and an XML feed land in the same clean table is the point.",
    },
    {
        "kicker": "How it runs",
        "title": "The Pipeline & the Modules",
        "body": """
<p>One orchestrator, four stages:</p>
<table class="mini">
  <tbody>
    <tr><td><code>--stage generate</code></td><td>Create messy raw data in <code>data/landing/</code></td></tr>
    <tr><td><code>--stage bronze</code></td><td>Ingest landing → <code>data/bronze/</code> (append-only)</td></tr>
    <tr><td><code>--stage silver</code></td><td>Shred + clean + conform + <strong>merge both sources</strong></td></tr>
    <tr><td><code>--stage gold</code></td><td>Build business aggregates → <code>data/gold/</code></td></tr>
  </tbody>
</table>
<p><code>silver</code> and <code>gold</code> are cross-source by nature — they
consume whatever is present in bronze.</p>
""",
        "svg": "02-architecture-data-flow.svg",
        "note": "run.py wires generators, bronze ingesters, silver, and gold together.",
    },
    {
        "kicker": "Layer 1",
        "title": "Bronze — The System of Record",
        "body": """
<ul>
  <li>Stores each source <strong>verbatim</strong> — CSV stays CSV, XML stays XML.</li>
  <li><strong>Append-only</strong> and <strong>per-source</strong> — adding a
      source never risks the others.</li>
  <li>Adds ingestion metadata: <code>_ingested_at</code>, <code>_batch_id</code>,
      <code>_source_file</code>.</li>
  <li>Invoices also get a <code>manifest.csv</code> — one catalog row per XML file.</li>
</ul>
<p class="callout">"Bronze is useless because it's dirty" — no: it's your safety
net for reprocessing and your audit trail.</p>
""",
        "svg": None,
        "note": "Never lose the original. Bronze is the source of truth for replays.",
    },
    {
        "kicker": "Layer 2",
        "title": "Silver — Where the Sources Converge",
        "body": """
<p>Silver reads <strong>both</strong> bronze sources and maps them into one
conformed <code>sales</code> schema (schema-on-read):</p>
<ul>
  <li>CSV rows mapped field-by-field.</li>
  <li>XML <em>shredded</em> into one record per line item.</li>
  <li>Then <strong>identical</strong> cleaning, dedupe (by
      <code>source_system</code> + <code>source_id</code>), and validation.</li>
</ul>
<p>Integration happens <strong>here</strong> — not in landing, not in bronze.
This is <em>late integration</em>: keep sources native until meaning is applied.</p>
""",
        "svg": "ontology-convergence.svg",
        "note": "One shared vocabulary; two source adapters feed it.",
    },
    {
        "kicker": "Layer 3",
        "title": "Gold — Business-Ready Aggregates",
        "body": """
<p>Gold answers specific questions by aggregating clean silver detail. Four marts:</p>
<ul>
  <li><code>daily_revenue.csv</code> — revenue per day.</li>
  <li><code>revenue_by_category.csv</code> — revenue per product category.</li>
  <li><code>top_customers.csv</code> — highest-spending customers.</li>
  <li><code>revenue_by_source.csv</code> — revenue split by originating system.</li>
</ul>
<p>Gold is <strong>idempotent</strong> — rebuilding produces identical files, and
every total ties back to silver.</p>
""",
        "svg": None,
        "note": "Silver = clean detail; Gold = aggregated for a purpose.",
    },
    {
        "kicker": "The shared schema",
        "title": "One Data Model, Two Origins",
        "body": """
<p>Both sources land in the same conformed <code>sales</code> row:</p>
<ul>
  <li><code>source_system</code>, <code>source_id</code> — provenance & natural key.</li>
  <li><code>txn_date</code>, <code>customer_id</code>, <code>customer_name</code>.</li>
  <li><code>product</code>, <code>category</code>, <code>quantity</code>, <code>unit_price</code>.</li>
  <li><code>revenue</code> — <em>derived</em> as <code>quantity × unit_price</code>.</li>
</ul>
<p><code>revenue</code> is stored by neither source — it is <strong>entailed</strong>
by a rule. A first taste of inference.</p>
""",
        "svg": "03-data-model-erd.svg",
        "note": "The ERD shows Orders & Invoices meeting as one Sale.",
    },
    {
        "kicker": "Data quality",
        "title": "Validate & Quarantine — Never Drop",
        "body": """
<p>Invalid records from <em>either</em> source are moved aside with a reason,
never silently discarded:</p>
<table class="mini">
  <tbody>
    <tr><td>missing <code>source_id</code></td><td>no natural key</td></tr>
    <tr><td>unparseable date</td><td>multi-format parser failed</td></tr>
    <tr><td>quantity not a positive integer</td><td><code>qty &le; 0</code></td></tr>
    <tr><td>unit_price not valid / non-negative</td><td>bad or missing price</td></tr>
  </tbody>
</table>
<p class="callout">Quarantine = "known instances that fail the rules" — countable,
inspectable, fixable.</p>
""",
        "svg": None,
        "note": "Dropping bad rows hides data-quality problems; quarantining keeps them visible.",
    },
    {
        "kicker": "Meaning layer",
        "title": "Schema vs. Ontology",
        "body": """
<p>A <strong>schema</strong> is the shape of storage. An <strong>ontology</strong>
is the shape of <em>meaning</em>:</p>
<ul>
  <li><strong>Classes</strong> (nouns): Party, Customer, Product, Category, Sale,
      Order, Invoice, LineItem.</li>
  <li><strong>Relationships</strong> (verbs): <code>placedBy</code>,
      <code>hasLineItem</code>, <code>refersToProduct</code>.</li>
  <li><strong>Axioms</strong>: the validation rules, restated as truths a valid
      instance must satisfy.</li>
</ul>
<p>Key axiom: <code>Order &sqsubseteq; Sale</code> and
<code>Invoice &sqsubseteq; Sale</code> — both <em>are</em> Sales.</p>
""",
        "svg": "06-ontology-medallion-meaning.svg",
        "note": "Data quality is just conformance to the ontology's axioms.",
    },
    {
        "kicker": "The realization",
        "title": "Silver Is an Ontology in Disguise",
        "body": """
<p>The silver adapters already do ontology work:</p>
<ul>
  <li>Two source <em>schemas</em> map to the <strong>same concepts</strong>
      (one property, two source expressions).</li>
  <li>The conformed schema <em>is</em> the shared vocabulary.</li>
  <li>Quarantine <em>is</em> "instances that violate the axioms".</li>
</ul>
<p>You were building a semantic layer all along — the medallion just made it
practical.</p>
""",
        "svg": "ontology-class-diagram.svg",
        "note": "One concept, two source expressions — that is the heart of integration.",
    },
    {
        "kicker": "Platform theory",
        "title": "Lakehouse vs. Ontology Store",
        "body": """
<table class="mini">
  <thead><tr><th></th><th>Lakehouse</th><th>Ontology store</th></tr></thead>
  <tbody>
    <tr><td>Question</td><td>"What happened?"</td><td>"What does it mean?"</td></tr>
    <tr><td>Integrates at</td><td>data / instance level</td><td>schema / concept level</td></tr>
    <tr><td>Scales on</td><td>volume</td><td>complexity</td></tr>
    <tr><td>Holds</td><td>bronze/silver/gold rows</td><td>concepts, relationships, axioms</td></tr>
  </tbody>
</table>
<p>Keep them <strong>separate</strong> — different change rates, different scaling
axes — and let them <strong>meet at silver</strong>.</p>
""",
        "svg": "07-lakehouse-and-ontology-store.svg",
        "note": "The lakehouse is the memory; the ontology store is the understanding.",
    },
    {
        "kicker": "Live exercise",
        "title": "Add a Third Source (JSON)",
        "body": """
<p>Bring in a POS system that emits JSON. What changes?</p>
<ul>
  <li><strong>Ontology</strong>: +1 mapping column, +1 axiom
      (<code>PosSale &sqsubseteq; Sale</code>).</li>
  <li><strong>Plumbing</strong>: new per-source generator + bronze reader.</li>
  <li><strong>Silver</strong>: +1 adapter <code>_pos_raw()</code>, +1 line in
      <code>build()</code>.</li>
  <li><strong>Gold</strong>: <span class="pill gold">no change</span> — it only
      knows <code>Sale</code>, so POS is counted for free.</li>
</ul>
<p class="callout">New source ⇒ new <em>mapping</em>, not new <em>math</em>.</p>
""",
        "svg": "08-add-a-json-source.svg",
        "note": "This is exactly why the lakehouse and ontology store are worth separating.",
    },
    {
        "kicker": "Wrap-up",
        "title": "Key Takeaways",
        "body": """
<ul>
  <li><strong>Medallion</strong>: raw → clean → curated, one direction, each layer
      one job.</li>
  <li><strong>Bronze</strong> is the safety net; <strong>silver</strong> is where
      meaning and integration happen; <strong>gold</strong> serves the business.</li>
  <li><strong>Format doesn't matter</strong> — CSV and XML converge into one table.</li>
  <li><strong>Quality = conformance</strong> to the ontology's axioms; quarantine,
      don't drop.</li>
  <li><strong>Separate meaning from storage</strong> — they meet at silver.</li>
</ul>
<p class="run">Run it yourself: <code>python run.py --stage all --reset</code></p>
""",
        "svg": None,
        "note": "Thank you — questions welcome.",
    },
]


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

def _read_svg(name: str | None) -> str:
    """Return inline-ready SVG markup for a media file, or '' if unavailable."""
    if not name:
        return ""
    path = os.path.join(MEDIA_DIR, name)
    if not os.path.isfile(path):
        print(f"  ! diagram not found, skipping: {name}")
        return ""
    with open(path, "r", encoding="utf-8") as fh:
        svg = fh.read()
    # Strip any XML/doctype prologue so the SVG inlines cleanly inside HTML.
    idx = svg.find("<svg")
    return svg[idx:] if idx != -1 else svg


CSS = """
:root{
  --bg:#0f172a; --panel:#ffffff; --ink:#1e293b; --muted:#64748b;
  --bronze:#c2703d; --silver:#6b7280; --gold:#ca8a04;
  --csv:#0284c7; --xml:#7c3aed; --accent:#0f766e; --line:#e2e8f0;
}
*{box-sizing:border-box}
html,body{margin:0;height:100%}
body{
  font-family:"Segoe UI",Arial,sans-serif;color:var(--ink);
  background:linear-gradient(135deg,#0f172a 0%,#1e293b 100%);
  display:flex;align-items:center;justify-content:center;min-height:100vh;padding:24px;
}
.deck{
  width:min(1100px,96vw);background:var(--panel);border-radius:18px;
  box-shadow:0 24px 60px rgba(0,0,0,.45);overflow:hidden;display:flex;flex-direction:column;
  min-height:min(680px,92vh);
}
.progress{height:6px;background:var(--line)}
.progress > span{display:block;height:100%;background:linear-gradient(90deg,var(--csv),var(--accent));}
.topbar{display:flex;justify-content:space-between;align-items:center;padding:14px 30px 0;
  color:var(--muted);font-size:13px;font-weight:600}
.topbar .deck-title{letter-spacing:.02em}
.content{flex:1;display:flex;gap:28px;padding:14px 40px 24px;align-items:center}
.content.solo{justify-content:center}
.text{flex:1;min-width:0}
.diagram{flex:1.1;min-width:0;display:flex;align-items:center;justify-content:center}
.diagram svg{width:100%;height:auto;max-height:60vh}
.kicker{display:inline-block;text-transform:uppercase;letter-spacing:.12em;font-size:12px;
  font-weight:700;color:var(--accent);background:#ecfdf5;padding:4px 10px;border-radius:999px;margin-bottom:12px}
h1{font-size:34px;line-height:1.15;margin:0 0 14px;color:var(--ink)}
.text p{font-size:17px;line-height:1.5;margin:0 0 12px}
.text .lead{font-size:19px}
.text ul{margin:0 0 12px;padding-left:22px}
.text li{font-size:16.5px;line-height:1.5;margin:6px 0}
code{background:#f1f5f9;border:1px solid var(--line);border-radius:6px;padding:1px 6px;
  font-family:Consolas,"Courier New",monospace;font-size:.92em;color:#0f172a}
.run code{background:#0f172a;color:#e2e8f0;border-color:#0f172a;padding:6px 12px;display:inline-block}
.callout{background:#fffbeb;border-left:4px solid var(--gold);padding:10px 14px;border-radius:8px;
  font-size:15.5px;color:#713f12}
table.mini{width:100%;border-collapse:collapse;margin:0 0 12px;font-size:15px}
table.mini th,table.mini td{border:1px solid var(--line);padding:7px 10px;text-align:left;vertical-align:top}
table.mini th{background:#f8fafc;color:var(--muted);font-size:13px;text-transform:uppercase;letter-spacing:.04em}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:13px;font-weight:700;color:#fff}
.pill.bronze{background:var(--bronze)} .pill.silver{background:var(--silver)}
.pill.gold{background:var(--gold)} .pill.csv{background:var(--csv)} .pill.xml{background:var(--xml)}
.note{background:#f0f9ff;border-top:1px solid var(--line);color:#0c4a6e;font-size:14px;
  padding:10px 40px;font-style:italic}
.note strong{font-style:normal}
.nav{display:flex;justify-content:space-between;align-items:center;padding:14px 30px;
  border-top:1px solid var(--line);background:#f8fafc}
.nav a,.nav span.disabled{
  text-decoration:none;font-weight:600;font-size:14px;padding:9px 16px;border-radius:9px;
  color:#fff;background:#0f766e;transition:opacity .15s}
.nav a:hover{opacity:.85}
.nav .home{background:#334155}
.nav span.disabled{background:#cbd5e1;color:#f8fafc;cursor:not-allowed}
.counter{color:var(--muted);font-weight:700;font-size:14px}
.footer{display:flex;justify-content:center;align-items:center;gap:8px;
  padding:9px 30px;background:#0f172a;color:#cbd5e1;font-size:12.5px;letter-spacing:.03em}
.footer strong{color:#fff;font-weight:600}
@media (max-width:820px){
  .content{flex-direction:column;padding:12px 22px 18px}
  h1{font-size:26px}.diagram svg{max-height:38vh}
}
"""

NAV_SCRIPT = """
<script>
(function(){{
  var prev={prev}, next={next}, home="index.html";
  function go(u){{ if(u) window.location.href=u; }}
  document.addEventListener("keydown",function(e){{
    switch(e.key){{
      case "ArrowRight": case " ": case "PageDown": go(next); break;
      case "ArrowLeft": case "PageUp": go(prev); break;
      case "Home": go(home); break;
      case "o": case "O": go(home); break;
    }}
  }});
}})();
</script>
"""


def _slide_filename(index: int) -> str:
    return f"slide-{index + 1:02d}.html"


def _render_slide(index: int, slide: dict, total: int) -> str:
    svg = _read_svg(slide.get("svg"))
    has_svg = bool(svg)
    kicker = slide.get("kicker", "")
    note = slide.get("note", "")

    text_block = f"""
        <div class="text">
          {'<span class="kicker">' + html.escape(kicker) + '</span>' if kicker else ''}
          <h1>{html.escape(slide['title'])}</h1>
          {slide['body']}
        </div>"""
    diagram_block = f'<div class="diagram">{svg}</div>' if has_svg else ""
    content_class = "content" if has_svg else "content solo"

    prev_file = _slide_filename(index - 1) if index > 0 else ""
    next_file = _slide_filename(index + 1) if index < total - 1 else ""

    prev_btn = (f'<a class="prev" href="{prev_file}">&larr; Prev</a>'
                if prev_file else '<span class="disabled">&larr; Prev</span>')
    next_btn = (f'<a class="next" href="{next_file}">Next &rarr;</a>'
                if next_file else '<span class="disabled">Next &rarr;</span>')

    pct = round((index + 1) / total * 100)
    note_block = f'<div class="note"><strong>Takeaway:</strong> {html.escape(note)}</div>' if note else ""
    nav_script = NAV_SCRIPT.format(
        prev=json.dumps(prev_file or None),
        next=json.dumps(next_file or None),
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(slide['title'])} — {html.escape(DECK_TITLE)}</title>
<style>{CSS}</style>
</head>
<body>
  <div class="deck">
    <div class="progress"><span style="width:{pct}%"></span></div>
    <div class="topbar">
      <span class="deck-title">{html.escape(DECK_TITLE)}</span>
      <span class="counter">Slide {index + 1} / {total}</span>
    </div>
    <div class="{content_class}">
      {text_block}
      {diagram_block}
    </div>
    {note_block}
    <div class="nav">
      {prev_btn}
      <a class="home" href="index.html">Contents</a>
      <span class="counter">{index + 1} / {total}</span>
      {next_btn}
    </div>
    <div class="footer">Contact: <strong>{html.escape(CONTACT)}</strong></div>
  </div>
  {nav_script}
</body>
</html>
"""


def _render_index(total: int) -> str:
    items = []
    for i, slide in enumerate(SLIDES[:total]):
        items.append(
            f'<li><a href="{_slide_filename(i)}">'
            f'<span class="num">{i + 1:02d}</span>'
            f'<span class="ttl">{html.escape(slide["title"])}</span>'
            f'<span class="kick">{html.escape(slide.get("kicker", ""))}</span>'
            f'</a></li>'
        )
    items_html = "\n".join(items)
    index_css = CSS + """
.toc{width:min(900px,96vw)}
.toc .deck{padding-bottom:10px}
.toc h1{padding:24px 40px 4px;font-size:30px}
.toc p.sub{padding:0 40px 6px;color:var(--muted);font-size:16px}
ul.toc-list{list-style:none;margin:0;padding:8px 24px 24px;
  display:grid;grid-template-columns:1fr 1fr;gap:10px}
ul.toc-list a{display:flex;align-items:center;gap:12px;text-decoration:none;color:var(--ink);
  border:1px solid var(--line);border-radius:12px;padding:12px 14px;transition:.15s}
ul.toc-list a:hover{border-color:var(--accent);box-shadow:0 6px 16px rgba(15,118,110,.15);transform:translateY(-1px)}
ul.toc-list .num{font-weight:800;color:var(--accent);font-size:15px;min-width:26px}
ul.toc-list .ttl{font-weight:600;font-size:15px;flex:1}
ul.toc-list .kick{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--muted)}
.start{margin:0 40px 22px;display:inline-block;background:#0f766e;color:#fff;text-decoration:none;
  font-weight:700;padding:12px 22px;border-radius:10px}
@media (max-width:720px){ul.toc-list{grid-template-columns:1fr}}
"""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(DECK_TITLE)}</title>
<style>{index_css}</style>
</head>
<body>
  <div class="deck toc">
    <div class="progress"><span style="width:100%"></span></div>
    <h1>{html.escape(DECK_TITLE)}</h1>
    <p class="sub">A {total}-slide session deck built from the project docs and diagrams.
       Use the arrow keys to navigate once inside.</p>
    <a class="start" href="{_slide_filename(0)}">Start presentation &rarr;</a>
    <ul class="toc-list">
      {items_html}
    </ul>
    <div class="footer">Contact: <strong>{html.escape(CONTACT)}</strong></div>
  </div>
  <script>
    document.addEventListener("keydown",function(e){{
      if(e.key==="ArrowRight"||e.key===" "||e.key==="Enter"){{
        window.location.href="{_slide_filename(0)}";
      }}
    }});
  </script>
</body>
</html>
"""


def build() -> None:
    slides = SLIDES[:MAX_SLIDES]
    total = len(slides)

    os.makedirs(SLIDES_DIR, exist_ok=True)
    print(f"Building {total} slide(s) into: {SLIDES_DIR}")

    for i, slide in enumerate(slides):
        fname = _slide_filename(i)
        with open(os.path.join(SLIDES_DIR, fname), "w", encoding="utf-8") as fh:
            fh.write(_render_slide(i, slide, total))
        print(f"  + {fname}  {slide['title']}")

    with open(os.path.join(SLIDES_DIR, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(_render_index(total))
    print("  + index.html  (contents / launcher)")

    print(f"\nDone. Open: {os.path.join(SLIDES_DIR, 'index.html')}")


if __name__ == "__main__":
    build()
