"""Render the five Artefacts and the Run Record.

The layout follows the observed run records (Run 2026-0912-C,
SD-RUN-2026-0921-B): A Purpose and boundary, B Freeze record, C Standing
disclosure, D Findings, E Detachment read, F Verdict and matters reserved,
G Register.
"""

from __future__ import annotations

import html

from . import spec

TIER_ORDER = list(spec.TIERS)


def _lens_names(f: dict) -> str:
    return " · ".join(spec.LENSES[l]["name"] for l in f.get("lenses", [f.get("lens")]) if l in spec.LENSES)


def artefacts(state: dict, register_events: list[dict]) -> dict:
    """The five Artefacts (pack slide 14) as structured data."""
    req = state["request"]
    return {
        "version_record": {
            "run_id": state["run_id"], "spec_version": state["spec_version"],
            "method_hash": state["method_hash"], "frozen_at": state.get("frozen_at"),
            "owner": req["owner"], "audience": req["audience"],
            "external_inputs": req["external_inputs"], "model_identity": state.get("model_identity"),
            "files": [{k: d[k] for k in ("filename", "sha256", "pages", "media_type", "metadata", "text_layer")}
                      for d in state.get("docs", [])],
        },
        "findings_ledger": state.get("findings", []),
        "reconciliation_log": state.get("reconciliation_log", []),
        "decision_record": state.get("decisions", {}),
        "release_certificate": state.get("certificate"),
        "register_extract": register_events,
    }


def _diff_window(a: str, b: str, pad: int = 24) -> tuple[str, str]:
    """The stretch around the first difference, so a long line shows what changed."""
    i = next((k for k, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
    lo = max(0, i - pad)
    cut = lambda s: ("…" if lo else "") + s[lo:i + pad] + ("…" if len(s) > i + pad else "")
    return cut(a), cut(b)


def run_record_markdown(state: dict, register_events: list[dict]) -> str:
    req = state["request"]
    prof = spec.PROFILES[req["profile"]]
    rid = state["run_id"]
    subj = req["subject"] or ", ".join(d["filename"] for d in state["docs"])
    out = [
        "*Private and Confidential*", "",
        "# SaptaDrishti Run Record", "",
        f"**Run {rid} · {prof['label']} · Specification v{state['spec_version']} · Cycle {req['cycle']}**  ",
        f"Subject: {subj}  ",
    ]
    if req["contains_personal_data"]:
        out.append("*Internal record: contains personal data; anonymise before any circulation.*")
    out += [
        "", "## A. Purpose and boundary", "",
        f"1. This record sets out Run {rid}, conducted under the {prof['label']}, Specification "
        f"v{state['spec_version']}, at Cycle {req['cycle']}. The seven lenses were applied in parallel "
        "to the frozen pack, each in isolation, reconciled under the Precedence Canon, and the findings tiered below.",
        "2. This record certifies document integrity and decision-sufficiency of the record as frozen. "
        "It is not a decision, an endorsement, or an assessment of any person; adjudications reserved to "
        "the Owner remain open until taken.",
    ]
    if prof.get("disclaimer"):
        out.append(f"3. {prof['disclaimer']}")

    out += ["", "## B. Freeze record", "", "| Field | Entry |", "|---|---|"]
    for d in state["docs"]:
        meta = "; ".join(f"{k} “{v}”" for k, v in d["metadata"].items()) or "no document metadata"
        out.append(f"| Pack | {d['filename']} — {d['pages']} page(s), {d['media_type']}; {meta} |")
        out.append(f"| SHA-256 | `{d['sha256']}` |")
        out.append("| Rendered verification | " + (" ".join(d.get("notes", [])) or "Text layer present; extracted and frozen.") + " |")
        for a in d.get("artifacts", [])[:40]:
            e, r = _diff_window(a["extracted"], a["rendered"])
            out.append(f"| Quarantined artifact | p{a['page']} L{a['line']}: extracted “{e}” → rendered “{r}” |")
    out += [
        f"| As-of date | {req['as_of']} |",
        f"| Audience | {req['audience']} |",
        f"| Requisition | {req['requisition'] or 'None stated; the record adjudicates the document in general terms.'} |",
        f"| Contemporary facts | {'; '.join(req['contemporary_facts']) or 'None declared.'}"
        f"{' Web verification permitted.' if req['allow_web_verification'] else ' No web sources used.'} |",
    ]
    for f in state.get("verified_facts", []):
        out.append(f"| Fact checked at freeze · {f.get('id', '')} | {f['status'].title()}: {f['claim']} — {f['finding']} "
                   f"({'; '.join(f.get('sources', [])[:2]) or 'no source'}) |")
    out += [
        f"| Edition · Profile | {prof['label']} |",
        f"| Specification | v{state['spec_version']} · Cycle {req['cycle']} |",
        f"| Method hash | `{state['method_hash'][:16]}…` (sealed charters) |",
        f"| Model identity | {state.get('model_identity')} |",
        f"| Owner · Releaser | {req['owner']['name']} · {(req.get('releaser') or {}).get('name', 'not yet named')} |",
    ]

    if req["standing_disclosures"]:
        out += ["", "## C. Standing disclosure", ""]
        for d in req["standing_disclosures"]:
            out.append(f"- {d['relationship']}. Claims affected: {', '.join(d['claims_affected']) or 'unspecified'}. "
                       "Those claims are referred to the Owner rather than to external sources. The familiarity-bias "
                       "guard applies in both directions: neither discount nor premium attaches to acquaintance.")
    if state.get("prior_adjudications"):
        out += ["", "### Adjudications honoured from the prior cycle", ""]
        out += [f"- {a}" for a in state["prior_adjudications"]]

    findings = state.get("findings", [])
    decisions = state.get("decisions", {})
    out += ["", "## D. Findings", ""]
    for group, tiers in (("Material and Corrective Findings", ["blocking", "material", "corrective"]),
                         ("Moderate Observations and Advisories", ["moderate", "advisory"])):
        rows = [f for f in findings if f["tier"] in tiers]
        if not rows:
            continue
        out += [f"### {group}", "", "| No. | Tier | Lens | Finding | Line | Disposition | Owner |", "|---|---|---|---|---|---|---|"]
        for f in rows:
            q = f" — “{f['quote']}”" if f.get("quote") else ""
            if f.get("fact_refs"):
                q += f" [facts: {', '.join(f['fact_refs'])}]"
            d = decisions.get(f["id"])
            dec = f"{d['decision']}" + (f": {d['note']}" if d.get("note") else "") if d else "pending"
            out.append(f"| {f['id']} | {f['tier'].title()} | {_lens_names(f)} | {f['finding']}{q} | "
                       f"{f['location']} | {f['disposition']} | {dec} |")
        out.append("")
    probes = [f for f in findings if f.get("probe")]
    if probes:
        out += ["### Probes", ""] + [f"- **{f['id']}** {f['probe']}" for f in probes] + [""]

    out += ["### The seven readings", ""]
    for lens, lo in state.get("lens_outputs", {}).items():
        out.append(f"**{spec.LENSES[lens]['name']}.** {lo['reading']}"
                   + (f" *({len(lo['rejected'])} finding(s) rejected at the citation gate.)*" if lo["rejected"] else ""))
        out.append("")

    out += ["## E. Detachment read", "", state.get("detachment_read", ""), "",
            "**Reconciled.** " + state.get("reconciled_summary", ""), ""]
    if state.get("reconciliation_log"):
        out += ["### Reconciliation log", "", "| Sources | Conflict | Canon rule | Resolution |", "|---|---|---|---|"]
        out += [f"| {', '.join(e['source_ids'])} | {e['conflict']} | {e['canon_rule']} | {e['resolution']} |"
                for e in state["reconciliation_log"]]
        out.append("")

    counts = {t: sum(1 for f in findings if f["tier"] == t) for t in TIER_ORDER}
    tally = ", ".join(f"{n} {t.title()}" for t, n in counts.items() if n) or "no findings"
    out += ["## F. Verdict and matters reserved to the Owner", "",
            f"Cycle {req['cycle']} verdict: **{state.get('verdict', 'pending')}** ({tally})."]
    if state.get("matters_reserved_to_owner"):
        out += ["", "Decision-insufficient pending:"] + [f"- {m}" for m in state["matters_reserved_to_owner"]]
    if req["cycle"] < spec.MAX_CYCLES and state.get("verdict") != "clean":
        out.append(f"\nCycle 2 is reserved for the refreshed pack, honouring the adjudications recorded here and reviewing deltas only.")
    if not req["requisition"] and req["profile"] == "cv":
        out.append("\nNo requisition was stated for this run. If the record is to serve a specific role, "
                   "the Positioning lens re-runs against that context on request.")
    if state.get("certificate"):
        c = state["certificate"]
        out += ["", "### Release Certificate", "",
                f"{c['text']}  ", f"Owner: {c['owner']['name']} ({c['owner']['at']})  ",
                f"Releaser: {c['releaser']['name']} — {c['releaser']['meaning']} ({c['releaser']['at']})  ",
                f"Retention: {c['retention_days']} days."]

    out += ["", "## G. Register", "",
            f"This run is recorded to the register as Run {rid}, Specification v{state['spec_version']}, "
            f"{prof['label']}, Cycle {req['cycle']} {state.get('verdict', '')}; status {state['status']}. "
            f"{len(register_events)} event(s); chain verified.", "",
            f"*Run {rid} · Specification v{state['spec_version']} · method {state['method_hash'][:12]}*"]
    return "\n".join(out)


def run_record_html(state: dict, register_events: list[dict]) -> str:
    """Minimal, print-friendly HTML rendering of the Markdown record."""
    md = run_record_markdown(state, register_events)
    body, in_table = [], False
    for line in md.splitlines():
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if all(set(c) <= set("-") for c in cells):
                continue
            if not in_table:
                body.append("<table>")
                in_table = True
                body.append("<tr>" + "".join(f"<th>{_inline(c)}</th>" for c in cells) + "</tr>")
            else:
                body.append("<tr>" + "".join(f"<td>{_inline(c)}</td>" for c in cells) + "</tr>")
            continue
        if in_table:
            body.append("</table>")
            in_table = False
        if line.startswith("### "):
            body.append(f"<h3>{_inline(line[4:])}</h3>")
        elif line.startswith("## "):
            body.append(f"<h2>{_inline(line[3:])}</h2>")
        elif line.startswith("# "):
            body.append(f"<h1>{_inline(line[2:])}</h1>")
        elif line.startswith("- "):
            body.append(f"<li>{_inline(line[2:])}</li>")
        elif line.strip():
            body.append(f"<p>{_inline(line)}</p>")
    if in_table:
        body.append("</table>")
    return ("<!doctype html><html><head><meta charset='utf-8'><title>Run " + html.escape(state["run_id"]) +
            "</title><style>body{font:15px/1.5 Arial,Helvetica,sans-serif;max-width:900px;margin:32px auto;"
            "padding:0 16px;color:#111}table{border-collapse:collapse;width:100%;margin:8px 0}"
            "td,th{border:1px solid #bbb;padding:6px;vertical-align:top;font-size:13px;text-align:left}"
            "th{background:#f3f3f3}h1{text-align:center}code{font-size:12px}</style></head><body>"
            + "\n".join(body) + "</body></html>")


def _inline(s: str) -> str:
    import re
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\*(.+?)\*", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s
