#!/usr/bin/env python3
"""Generate a self-contained HTML report for one or more eval iterations.

Per-iteration report (`iteration-N/report.html`) surfaces every failed
expectation up front with the judge's reason and evidence, and lets you
drill into the model's `output.md` and `files.json` in-page. Trend report
(`evals/workspace/trend.html`) shows pass/fail for every expectation across
iterations so regressions are obvious at a glance.

Usage:
    python evals/report.py                   # latest iteration
    python evals/report.py --iteration 42
    python evals/report.py --all             # one report per iteration
    python evals/report.py --trend           # also build trend.html
    python evals/report.py --open            # open report in the browser
"""
import argparse
import functools
import html
import json
import webbrowser
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
WORKSPACE = REPO / "evals" / "workspace"

# Cap embedded blob sizes so the HTML stays loadable even on big outputs.
OUTPUT_MD_MAX_BYTES = 200_000
FILE_BLOB_MAX_BYTES = 100_000


def all_iterations() -> list[int]:
    nums = []
    for p in WORKSPACE.glob("iteration-*"):
        suffix = p.name.split("-", 1)[1]
        if suffix.isdigit() and (p / "benchmark.json").exists():
            nums.append(int(suffix))
    return sorted(nums)


def latest_iteration() -> int | None:
    nums = all_iterations()
    return nums[-1] if nums else None


@functools.cache
def load_benchmark(iter_n: int) -> dict | None:
    p = WORKSPACE / f"iteration-{iter_n}" / "benchmark.json"
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        return None


def load_artifacts(iter_n: int, eval_id: int, eval_name: str) -> dict:
    slug = f"eval-{eval_id}-{eval_name}"
    arm = WORKSPACE / f"iteration-{iter_n}" / slug / "with_skill"
    output_md = ""
    files: dict[str, str] = {}
    p = arm / "output.md"
    if p.exists():
        try:
            text = p.read_text()
            if len(text) > OUTPUT_MD_MAX_BYTES:
                text = text[:OUTPUT_MD_MAX_BYTES] + "\n... [truncated]"
            output_md = text
        except OSError:
            pass
    p = arm / "files.json"
    if p.exists():
        try:
            raw = json.loads(p.read_text())
            if isinstance(raw, dict):
                for k, v in raw.items():
                    s = v if isinstance(v, str) else json.dumps(v, indent=2)
                    if len(s) > FILE_BLOB_MAX_BYTES:
                        s = s[:FILE_BLOB_MAX_BYTES] + "\n... [truncated]"
                    files[str(k)] = s
        except (OSError, json.JSONDecodeError):
            pass
    return {"output_md": output_md, "files": files}


def esc(s: str) -> str:
    return html.escape(s, quote=True) if s else ""


CSS = """
:root {
  --bg: #0f1419;
  --panel: #161b22;
  --panel-2: #1c232c;
  --border: #2a3340;
  --text: #d6deeb;
  --muted: #8b97a8;
  --pass: #3fb950;
  --fail: #f85149;
  --warn: #d29922;
  --link: #79c0ff;
  --code-bg: #0d1117;
}
* { box-sizing: border-box; }
body { margin: 0; font: 14px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", system-ui, sans-serif;
       background: var(--bg); color: var(--text); }
a { color: var(--link); text-decoration: none; }
a:hover { text-decoration: underline; }
.wrap { max-width: 1100px; margin: 0 auto; padding: 24px; }
header { position: sticky; top: 0; z-index: 5; background: var(--bg); padding: 16px 0;
         border-bottom: 1px solid var(--border); margin-bottom: 16px; }
h1 { font-size: 20px; margin: 0 0 6px; }
h2 { font-size: 16px; margin: 24px 0 8px; }
.muted { color: var(--muted); }
.meta { display: flex; flex-wrap: wrap; gap: 16px; font-size: 12px; color: var(--muted); }
.meta b { color: var(--text); font-weight: 600; }
.summary { display: flex; gap: 12px; margin-top: 8px; flex-wrap: wrap; }
.pill { padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 600;
        background: var(--panel-2); border: 1px solid var(--border); }
.pill.pass { color: var(--pass); }
.pill.fail { color: var(--fail); }
.pill.warn { color: var(--warn); }
input[type="search"] { width: 100%; padding: 8px 12px; border-radius: 6px;
                       background: var(--panel); border: 1px solid var(--border);
                       color: var(--text); font-size: 14px; }
.fail-panel { background: var(--panel); border: 1px solid var(--border);
              border-left: 3px solid var(--fail); border-radius: 6px;
              padding: 12px 16px; margin-bottom: 24px; }
.fail-row { padding: 10px 0; border-top: 1px solid var(--border); }
.fail-row:first-child { border-top: none; }
.fail-head { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; font-weight: 600; }
.fail-row .text { margin: 4px 0 6px; }
.fail-row .reason { color: var(--text); margin: 4px 0; }
.fail-row .evidence { font-family: ui-monospace, "SF Mono", Menlo, monospace;
                       font-size: 12px; color: var(--muted); background: var(--code-bg);
                       padding: 6px 10px; border-radius: 4px; white-space: pre-wrap;
                       word-break: break-word; }
.card { background: var(--panel); border: 1px solid var(--border); border-radius: 6px;
        margin: 12px 0; overflow: hidden; }
.card > summary { list-style: none; cursor: pointer; padding: 12px 16px;
                  display: flex; gap: 12px; align-items: center; }
.card > summary::-webkit-details-marker { display: none; }
.card > summary::before { content: "▸"; color: var(--muted); width: 12px;
                          transition: transform 0.1s; }
.card[open] > summary::before { transform: rotate(90deg); }
.card.allpass { border-left: 3px solid var(--pass); }
.card.partial { border-left: 3px solid var(--warn); }
.card.allfail { border-left: 3px solid var(--fail); }
.card .body { padding: 0 16px 16px; }
.expectation { padding: 10px 0; border-top: 1px solid var(--border); }
.expectation:first-child { border-top: none; }
.expectation .head { display: flex; gap: 8px; align-items: flex-start; }
.expectation .mark { width: 18px; flex-shrink: 0; font-weight: 700; }
.expectation.passed .mark { color: var(--pass); }
.expectation.failed .mark { color: var(--fail); }
.expectation .text { flex: 1; }
.expectation .reason { color: var(--muted); margin: 4px 0 0 26px; font-size: 13px; }
.expectation.failed .reason { color: var(--text); }
.expectation .evidence { margin: 4px 0 0 26px; font-family: ui-monospace, "SF Mono", Menlo, monospace;
                          font-size: 12px; color: var(--muted); background: var(--code-bg);
                          padding: 6px 10px; border-radius: 4px; white-space: pre-wrap;
                          word-break: break-word; }
details.drill { margin: 10px 0 0; }
details.drill > summary { cursor: pointer; padding: 6px 0; color: var(--link); font-size: 13px; }
details.drill pre { background: var(--code-bg); padding: 12px; border-radius: 4px;
                    overflow-x: auto; font-size: 12px; line-height: 1.5;
                    white-space: pre-wrap; word-break: break-word; max-height: 600px;
                    overflow-y: auto; }
details.file > summary { font-family: ui-monospace, "SF Mono", Menlo, monospace;
                         font-size: 12px; color: var(--muted); padding: 4px 0; }
.badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
         background: var(--panel-2); border: 1px solid var(--border); }
.badge.pass { color: var(--pass); }
.badge.fail { color: var(--fail); }
.badge.warn { color: var(--warn); }
.badge.skill { color: var(--link); }
.hidden { display: none !important; }
/* trend table */
table.trend { width: 100%; border-collapse: collapse; font-size: 12px; }
table.trend th, table.trend td { padding: 4px 6px; border: 1px solid var(--border);
                                  text-align: center; white-space: nowrap; }
table.trend th.exp { text-align: left; max-width: 480px; white-space: normal; }
table.trend td.exp { text-align: left; max-width: 480px; white-space: normal; font-size: 12px; }
table.trend td.pass { background: rgba(63, 185, 80, 0.15); color: var(--pass); }
table.trend td.fail { background: rgba(248, 81, 73, 0.18); color: var(--fail); }
table.trend td.miss { color: var(--muted); }
table.trend td.regress { background: rgba(248, 81, 73, 0.35); color: #fff;
                          box-shadow: inset 0 0 0 2px var(--fail); }
table.trend tr.regressed-row td.exp { color: var(--fail); }
.legend { font-size: 12px; color: var(--muted); margin: 4px 0 12px; }
.legend span { margin-right: 16px; }
"""

FILTER_JS = """
(function() {
  const input = document.getElementById('filter');
  if (!input) return;
  input.addEventListener('input', () => {
    const q = input.value.trim().toLowerCase();
    document.querySelectorAll('.card').forEach(card => {
      const hay = card.dataset.search || '';
      card.classList.toggle('hidden', q !== '' && !hay.includes(q));
    });
    document.querySelectorAll('.fail-row').forEach(row => {
      const hay = row.dataset.search || '';
      row.classList.toggle('hidden', q !== '' && !hay.includes(q));
    });
  });
})();
"""


def card_class(passed: int, total: int) -> str:
    if total == 0:
        return ""
    if passed == total:
        return "allpass"
    if passed == 0:
        return "allfail"
    return "partial"


def status_class(passed: int, total: int) -> str:
    """CSS class for pass/fail/warn pills and badges."""
    if total and passed == total:
        return "pass"
    if passed == 0:
        return "fail"
    return "warn"


def haystack(*parts: str) -> str:
    return esc(" ".join(parts).lower())


def render_expectation(i: int, e: dict) -> str:
    passed = bool(e.get("passed"))
    status_class = "passed" if passed else "failed"
    mark = "✓" if passed else "✗"
    text = esc(e.get("text", ""))
    reason = esc(e.get("reason", ""))
    evidence = esc(e.get("evidence", ""))
    parts = [
        f'<div class="expectation {status_class}">',
        f'  <div class="head"><div class="mark">{mark}</div>',
        f'    <div class="text"><b>{i + 1}.</b> {text}</div></div>',
    ]
    if reason:
        parts.append(f'  <div class="reason">{reason}</div>')
    if evidence:
        parts.append(f'  <div class="evidence">{evidence}</div>')
    parts.append("</div>")
    return "\n".join(parts)


def render_drill(label: str, body: str) -> str:
    if not body:
        return ""
    return (
        f'<details class="drill"><summary>{esc(label)}</summary>'
        f'<pre>{esc(body)}</pre></details>'
    )


def render_files(files: dict[str, str]) -> str:
    if not files:
        return ""
    chunks = ['<details class="drill"><summary>'
              f'Files written ({len(files)})</summary>']
    for path, content in files.items():
        chunks.append(
            f'<details class="file"><summary>{esc(path)}</summary>'
            f'<pre>{esc(content)}</pre></details>'
        )
    chunks.append("</details>")
    return "".join(chunks)


def render_run_card(iter_n: int, run: dict) -> str:
    eval_id = run["eval_id"]
    eval_name = run["eval_name"]
    res = run.get("result", {})
    passed, total = res.get("passed", 0), res.get("total", 0)
    triggered = run.get("skill_triggered")

    artifacts = load_artifacts(iter_n, eval_id, eval_name)

    expectations = run.get("expectations", [])
    trigger_badge = ""
    if triggered is True:
        trigger_badge = '<span class="badge skill">skill triggered</span>'
    elif triggered is False:
        trigger_badge = '<span class="badge fail">no skill</span>'

    expectations_html = "\n".join(render_expectation(i, e) for i, e in enumerate(expectations))
    open_attr = " open" if any(not e.get("passed") for e in expectations) else ""
    search = haystack(
        eval_name,
        *(e.get("text", "") for e in expectations),
        *(e.get("reason", "") for e in expectations),
        *(e.get("evidence", "") for e in expectations),
    )

    return f"""
<details class="card {card_class(passed, total)}" id="eval-{eval_id}" data-search="{search}"{open_attr}>
  <summary>
    <span class="badge {status_class(passed, total)}">{passed}/{total}</span>
    <b>eval {eval_id}</b>
    <span>{esc(eval_name)}</span>
    {trigger_badge}
  </summary>
  <div class="body">
    {expectations_html}
    {render_drill("Model response (output.md)", artifacts["output_md"])}
    {render_files(artifacts["files"])}
  </div>
</details>
"""


def render_failures_panel(runs: list[dict]) -> str:
    rows = []
    for r in runs:
        for i, e in enumerate(r.get("expectations", [])):
            if e.get("passed"):
                continue
            text = esc(e.get("text", ""))
            reason = esc(e.get("reason", ""))
            evidence = esc(e.get("evidence", ""))
            search = haystack(
                r["eval_name"], e.get("text", ""), e.get("reason", ""), e.get("evidence", ""),
            )
            rows.append(f"""
<div class="fail-row" data-search="{search}">
  <div class="fail-head">
    <span class="badge fail">FAIL</span>
    <a href="#eval-{r['eval_id']}">eval {r['eval_id']} · {esc(r['eval_name'])}</a>
    <span class="muted">expectation #{i + 1}</span>
  </div>
  <div class="text">{text}</div>
  <div class="reason"><b>reason:</b> {reason}</div>
  {f'<div class="evidence">{evidence}</div>' if evidence else ''}
</div>
""")
    if not rows:
        return ""
    return f"""
<div class="fail-panel">
  <h2 style="margin-top:0">Failures ({len(rows)})</h2>
  {''.join(rows)}
</div>
"""


def render_iteration(iter_n: int) -> str | None:
    bench = load_benchmark(iter_n)
    if bench is None:
        return None
    meta = bench.get("metadata", {})
    runs = bench.get("runs", [])
    summary = bench.get("run_summary", {}).get("with_skill", {}) or {}

    total_passed = summary.get("total_passed", 0)
    total = summary.get("total", 0)
    pass_rate = summary.get("pass_rate", 0)
    skill_triggered = summary.get("skill_triggered")
    skill_total = summary.get("skill_trigger_total")
    skill_rate = summary.get("skill_trigger_rate")

    failures_html = render_failures_panel(runs)
    cards_html = "\n".join(render_run_card(iter_n, r) for r in runs)

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>Eval report — iteration {iter_n}</title>
<style>{CSS}</style>
</head><body>
<div class="wrap">
  <header>
    <h1>Eval report — iteration {iter_n}</h1>
    <div class="meta">
      <span><b>timestamp:</b> {esc(meta.get('timestamp', '—'))}</span>
      <span><b>executor:</b> {esc(meta.get('executor_model', '—'))}</span>
      <span><b>judge:</b> {esc(meta.get('analyzer_model', '—'))}</span>
      <span><b>evals run:</b> {len(runs)}</span>
    </div>
    <div class="summary">
      <span class="pill {status_class(total_passed, total)}">{total_passed}/{total} expectations passed (rate {pass_rate})</span>
      {f'<span class="pill">{skill_triggered}/{skill_total} skill-triggered (rate {skill_rate})</span>'
       if skill_total else ''}
    </div>
    <div style="margin-top:12px">
      <input id="filter" type="search" placeholder="filter by eval name, expectation text, or judge reason…">
    </div>
  </header>
  {failures_html}
  <h2>All evals</h2>
  {cards_html}
</div>
<script>{FILTER_JS}</script>
</body></html>
"""


def write_iteration_report(iter_n: int) -> Path | None:
    rendered = render_iteration(iter_n)
    if rendered is None:
        return None
    out = WORKSPACE / f"iteration-{iter_n}" / "report.html"
    out.write_text(rendered)
    return out


# ---------- Trend ----------

def render_trend() -> str | None:
    iters = all_iterations()
    if not iters:
        return None
    cols = iters[-30:]

    # Key by (eval_id, expectation_index) so minor edits to expectation text
    # don't fragment the row history. The text itself is shown as the label.
    rows: dict[tuple[int, int], dict[int, bool]] = {}
    eval_names: dict[int, str] = {}
    expectation_text: dict[tuple[int, int], str] = {}
    order: list[tuple[int, int]] = []

    for n in iters:
        bench = load_benchmark(n)
        if not bench:
            continue
        for r in bench.get("runs", []):
            eid = r["eval_id"]
            eval_names[eid] = r["eval_name"]
            for idx, e in enumerate(r.get("expectations", [])):
                key = (eid, idx)
                if key not in rows:
                    rows[key] = {}
                    order.append(key)
                rows[key][n] = bool(e.get("passed"))
                expectation_text[key] = e.get("text", "")

    header_cells = "".join(f'<th>{n}</th>' for n in cols)
    body_rows = []
    regression_count = 0
    for key in order:
        eid, idx = key
        cells = []
        prev_pass: bool | None = None
        row_regressed = False
        for n in cols:
            if n not in rows[key]:
                cells.append('<td class="miss">—</td>')
                continue
            passed = rows[key][n]
            cls = "pass" if passed else "fail"
            mark = "✓" if passed else "✗"
            if prev_pass is True and passed is False:
                cls = "regress"
                row_regressed = True
            cells.append(f'<td class="{cls}">{mark}</td>')
            prev_pass = passed
        if row_regressed:
            regression_count += 1
        row_class = "regressed-row" if row_regressed else ""
        label = (
            f'eval {eid} ({esc(eval_names.get(eid, ""))}) '
            f'#{idx + 1}: {esc(expectation_text.get(key, ""))}'
        )
        body_rows.append(
            f'<tr class="{row_class}"><td class="exp">{label}</td>{"".join(cells)}</tr>'
        )

    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>Eval trend</title>
<style>{CSS}</style>
</head><body>
<div class="wrap">
  <header>
    <h1>Eval trend across iterations</h1>
    <div class="meta">
      <span><b>iterations shown:</b> {len(cols)} (of {len(iters)})</span>
      <span><b>expectations tracked:</b> {len(order)}</span>
      <span><b>rows with regressions:</b> {regression_count}</span>
    </div>
    <div class="legend">
      <span><span class="badge pass">✓</span> passed</span>
      <span><span class="badge fail">✗</span> failed</span>
      <span><span class="badge warn">box</span> regression (pass → fail)</span>
      <span>— = expectation not present in that iteration</span>
    </div>
  </header>
  <table class="trend">
    <thead><tr><th class="exp">Expectation</th>{header_cells}</tr></thead>
    <tbody>{''.join(body_rows)}</tbody>
  </table>
</div>
</body></html>
"""


def write_trend_report() -> Path | None:
    rendered = render_trend()
    if rendered is None:
        return None
    out = WORKSPACE / "trend.html"
    out.write_text(rendered)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--iteration", type=int, help="iteration to render; default latest")
    ap.add_argument("--all", action="store_true", help="render every iteration")
    ap.add_argument("--trend", action="store_true", help="also build trend.html")
    ap.add_argument("--open", dest="open_browser", action="store_true",
                    help="open the produced report in the browser")
    args = ap.parse_args()

    written: list[Path] = []
    if args.all:
        nums = all_iterations()
        for n in nums:
            out = write_iteration_report(n)
            if out is None:
                print(f"  • iteration {n}: no benchmark.json, skipping")
                continue
            written.append(out)
            print(f"  ✓ iteration {n}: {out}")
        if not nums:
            print("no iterations with benchmark.json found; nothing to render")
    else:
        n = args.iteration if args.iteration is not None else latest_iteration()
        if n is None:
            print("no iterations with benchmark.json found; nothing to render")
        else:
            out = write_iteration_report(n)
            if out is None:
                print(f"no benchmark.json for iteration {n}; skipping")
            else:
                written.append(out)
                print(f"✓ wrote {out}")

    if args.trend:
        trend = write_trend_report()
        if trend is None:
            print("no iterations to build trend.html from; skipping")
        else:
            written.append(trend)
            print(f"✓ wrote {trend}")

    if args.open_browser and written:
        webbrowser.open(written[-1].as_uri())


if __name__ == "__main__":
    main()
