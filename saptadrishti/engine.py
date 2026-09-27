"""Models beneath the method.

Two engines share one interface:

* ClaudeEngine  - each lens is a separate, context-isolated Claude call (I2).
* OfflineEngine - deterministic heuristics, no network. It exists so the
  protocol mechanics (freeze, gates, register, purge, guard) can be run and
  tested without an API key. It is not a substitute for the reading.
"""

from __future__ import annotations

import base64
import json
import re
from typing import Protocol

from . import spec

# ------------------------------------------------------------- schemas ---

_FINDING_PROPS = {
    "tier": {"type": "string", "enum": list(spec.TIERS)},
    "finding": {"type": "string"},
    "quote": {"type": "string"},
    "evidence_state": {"type": "string", "enum": spec.EVIDENCE_STATES},
    "remedy_class": {"type": "string", "enum": spec.REMEDY_CLASSES},
    "disposition": {"type": "string"},
    "probe": {"type": "string"},
}

LENS_SCHEMA = {
    "type": "object",
    "properties": {
        "reading": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _FINDING_PROPS,
                "required": list(_FINDING_PROPS),
                "additionalProperties": False,
            },
        },
    },
    "required": ["reading", "findings"],
    "additionalProperties": False,
}

_RECON_FINDING_PROPS = {
    "source_ids": {"type": "array", "items": {"type": "string"}},
    "lenses": {"type": "array", "items": {"type": "string", "enum": list(spec.LENSES)}},
    **_FINDING_PROPS,
}

RECONCILE_SCHEMA = {
    "type": "object",
    "properties": {
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": _RECON_FINDING_PROPS,
                "required": list(_RECON_FINDING_PROPS),
                "additionalProperties": False,
            },
        },
        "log": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "source_ids": {"type": "array", "items": {"type": "string"}},
                    "conflict": {"type": "string"},
                    "canon_rule": {"type": "string", "enum": ["I", "II", "III", "IV", "merge"]},
                    "resolution": {"type": "string"},
                },
                "required": ["source_ids", "conflict", "canon_rule", "resolution"],
                "additionalProperties": False,
            },
        },
        "detachment_read": {"type": "string"},
        "reconciled_summary": {"type": "string"},
        "matters_reserved_to_owner": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["findings", "log", "detachment_read", "reconciled_summary", "matters_reserved_to_owner"],
    "additionalProperties": False,
}

REWRITE_SCHEMA = {
    "type": "object",
    "properties": {"revised_text": {"type": "string"}, "changes": {"type": "array", "items": {"type": "string"}}},
    "required": ["revised_text", "changes"],
    "additionalProperties": False,
}

# ------------------------------------------------------------- prompts ---

PROTOCOL_SYSTEM = """You are executing one lens of the SaptaDrishti review protocol.

The document you are given has been frozen: it will not change during this run. You read it through exactly one lens, whose charter follows the document. You have not seen, and must not guess at, what any other lens found.

Rules of the method:
- Findings only. You do not rewrite the document and you do not make the decision; a named person does.
- Every finding with evidence_state "present" must quote, verbatim, the line of the frozen text it rests on (copy the words exactly, without the [D p L] address). A finding whose quote is not found in the frozen text is rejected.
- Absent data is reported as absent: evidence_state "absent", quote empty, and the text "no result in the document supplied". Never fill a gap by inference. Illegible or cropped values are "unreadable".
- Tiers: blocking (release impossible: e.g. a false statement of fact, a breach of confidence), material (decides the reader's decision), corrective (defect to correct or clarify), moderate (an observation to weigh), advisory (presentation/context only).
- Conservative severity: when in doubt, rank lower. False alarms cost scarce attention.
- Judge currency against the as-of date given; do not assume facts after it.
- Where a standing disclosure places the Owner close to the subject, refer those claims to the Owner (remedy_class "reserved_to_owner"); neither discount nor premium attaches to acquaintance.
- Infer nothing the document does not state: no protected attributes, no psychology.
- Speak only of the document. Never mention the protocol's maker, dedication or trademark.
- "probe" is a precise question a person could ask to resolve the finding (empty if none).
- "reading" is a short paragraph: what this lens sees in the document as a whole, in plain, measured prose.
- Return at most 8 findings; if the lens finds nothing, return an empty list and say so in the reading."""

RECONCILE_SYSTEM = """You are the reconciliation phase of the SaptaDrishti review protocol.

You receive the findings of seven isolated lenses on one frozen document. Merge findings that describe the same defect (list every source id and every lens), and resolve conflicts solely by the Precedence Canon, applied in strict order:
I   Truth is absolute - nothing false or overstated is ever written; no Standard may license a distortion.
II  Prudence governs disclosure - what is true may be withheld; what is said must be true. Truth-vs-prudence resolves by omission, never distortion.
III Stewardship arbitrates the spirit - where Purpose and Detachment pull against each other or against craft.
IV  Craft serves - Architecture and Positioning adapt to Rules I-III, never the reverse.

Rules:
- Every source finding must appear in exactly one merged finding, or in a log entry explaining why it was dismissed and under which rule.
- Log every merge (canon_rule "merge") and every conflict resolution (the rule applied).
- Keep quotes verbatim from the source findings; do not invent new ones.
- When merged findings disagree on tier, take the tier the evidence supports; when in doubt, the lower.
- detachment_read: strip the halos named by the Detachment lens and state the genuine residue that remains.
- reconciled_summary: one paragraph, the picture the lenses return when read together. Findings, not a verdict on the person.
- matters_reserved_to_owner: the acts that must happen before the reader can rely on the document.
- Never mention the protocol's maker, dedication or trademark."""

REWRITE_SYSTEM = """You are the integrated rewrite of the SaptaDrishti review protocol. One hand absorbs the accepted remedies into a single revision. Change only what the accepted findings require. Never introduce a fact that is not in the frozen text; where a remedy needs a fact the text lacks, insert a bracketed placeholder such as [date to be supplied]. List each change you made."""


def _context_block(ctx: dict) -> str:
    lines = [
        f"Profile: {ctx['profile_label']}",
        f"Audience (who will rely on the page): {ctx['audience']}",
        f"As-of date (freeze): {ctx['as_of']}",
    ]
    if ctx.get("subject"):
        lines.append(f"Subject: {ctx['subject']}")
    if ctx.get("purpose"):
        lines.append(f"Purpose / mandate: {ctx['purpose']}")
    lines.append(
        f"Requisition: {ctx['requisition']}" if ctx.get("requisition")
        else "Requisition: none stated; adjudicate the document in general terms."
    )
    for d in ctx.get("standing_disclosures", []):
        lines.append(f"Standing disclosure: {d['relationship']} (claims affected: {', '.join(d['claims_affected']) or 'unspecified'})")
    for x in ctx.get("external_inputs", []):
        lines.append(f"External input on record: {x}")
    if ctx.get("prior_adjudications"):
        lines.append("Cycle 2: honour these recorded adjudications and review deltas only:")
        lines.extend(f"  - {a}" for a in ctx["prior_adjudications"])
    return "\n".join(lines)


class Engine(Protocol):
    def identity(self) -> str: ...
    def transcribe(self, pdf_path: str, pages: int) -> list[str]: ...
    def read_lens(self, lens: str, charter: str, frozen_text: str, ctx: dict) -> dict: ...
    def reconcile(self, findings: list[dict], frozen_text: str, ctx: dict) -> dict: ...
    def rewrite(self, frozen_text: str, accepted: list[dict], ctx: dict) -> dict: ...


# ======================================================== Claude engine ===

class RefusalError(RuntimeError):
    pass


class ClaudeEngine:
    def __init__(self, model: str = "claude-opus-5", effort: str = "high", client=None):
        import anthropic

        self.model = model
        self.effort = effort
        self.client = client or anthropic.Anthropic()
        self.served_models: set[str] = set()

    def identity(self) -> str:
        served = ", ".join(sorted(self.served_models)) or "not yet served"
        return f"Claude (Anthropic) · requested {self.model} · served {served}"

    def _call(self, system: str, content: list[dict], schema: dict, max_tokens: int = 16000) -> dict:
        resp = self.client.beta.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            thinking={"type": "adaptive"},
            output_config={"effort": self.effort, "format": {"type": "json_schema", "schema": schema}},
            betas=["server-side-fallback-2026-06-01"],
            fallbacks=[{"model": "claude-opus-4-8"}],
            messages=[{"role": "user", "content": content}],
        )
        self.served_models.add(resp.model)
        if resp.stop_reason == "refusal":
            raise RefusalError(f"model declined this call ({getattr(resp, 'stop_details', None)})")
        if resp.stop_reason == "max_tokens":
            raise RuntimeError("lens output truncated at max_tokens")
        text = next(b.text for b in resp.content if b.type == "text")
        return json.loads(text)

    def _doc_blocks(self, frozen_text: str, ctx: dict) -> list[dict]:
        # Identical prefix for every lens, so the frozen text is cached once
        # and read seven times. Isolation is about findings, not the input.
        return [
            {"type": "text", "text": f"<context>\n{_context_block(ctx)}\n</context>\n\n"
                                     f"<frozen_document>\n{frozen_text}\n</frozen_document>",
             "cache_control": {"type": "ephemeral"}},
        ]

    def transcribe(self, pdf_path: str, pages: int) -> list[str]:
        with open(pdf_path, "rb") as f:
            data = base64.standard_b64encode(f.read()).decode()
        schema = {
            "type": "object",
            "properties": {"pages": {"type": "array", "items": {"type": "string"}}},
            "required": ["pages"], "additionalProperties": False,
        }
        out = self._call(
            "Transcribe the document verbatim, page by page, as rendered. Preserve line breaks, "
            "tables as pipe-separated rows, and handwriting as [handwritten: ...]. Mark any "
            "illegible or cropped character as [?]. Add nothing, correct nothing.",
            [{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
             {"type": "text", "text": f"The document has {pages} pages. Return one string per page."}],
            schema, max_tokens=32000,
        )
        return out["pages"]

    def read_lens(self, lens: str, charter: str, frozen_text: str, ctx: dict) -> dict:
        L = spec.LENSES[lens]
        instruction = (
            f"<lens>\n{L['name']} ({L['sanskrit']})\nThe question it asks: {L['question']}\n\n"
            f"Charter:\n{charter}\n</lens>\n\nRead the frozen document through this lens only."
        )
        return self._call(PROTOCOL_SYSTEM, self._doc_blocks(frozen_text, ctx) +
                          [{"type": "text", "text": instruction}], LENS_SCHEMA)

    def reconcile(self, findings: list[dict], frozen_text: str, ctx: dict) -> dict:
        return self._call(RECONCILE_SYSTEM, self._doc_blocks(frozen_text, ctx) + [
            {"type": "text", "text": "<lens_findings>\n" + json.dumps(findings, ensure_ascii=False, indent=1)
                                     + "\n</lens_findings>"}], RECONCILE_SCHEMA)

    def rewrite(self, frozen_text: str, accepted: list[dict], ctx: dict) -> dict:
        return self._call(REWRITE_SYSTEM, self._doc_blocks(frozen_text, ctx) + [
            {"type": "text", "text": "<accepted_findings>\n" + json.dumps(accepted, ensure_ascii=False, indent=1)
                                     + "\n</accepted_findings>"}], REWRITE_SCHEMA, max_tokens=32000)


# ======================================================= Offline engine ===

_LINE = re.compile(r"^\[D(\d+) p(\d+) L(\d+)\] (.*)$")


def _lines(frozen_text: str) -> list[str]:
    return [m.group(4) for m in map(_LINE.match, frozen_text.splitlines()) if m]


def _f(tier, finding, quote, remedy="seek_clarification", probe="", state="present", disp=""):
    return {"tier": tier, "finding": finding, "quote": quote, "evidence_state": state,
            "remedy_class": remedy, "disposition": disp or remedy.replace("_", " "), "probe": probe}


class OfflineEngine:
    """Deterministic pattern checks. Demonstrates mechanics, not judgement."""

    def __init__(self):
        self.calls: list[dict] = []  # recorded for the lens-isolation test

    def identity(self) -> str:
        return "offline-heuristic-engine (no model)"

    def transcribe(self, pdf_path: str, pages: int) -> list[str]:
        raise RuntimeError("the offline engine cannot read scanned pages; use engine 'claude'")

    def read_lens(self, lens: str, charter: str, frozen_text: str, ctx: dict) -> dict:
        self.calls.append({"lens": lens, "charter": charter, "text": frozen_text, "ctx": dict(ctx)})
        lines = _lines(frozen_text)
        fn = getattr(self, f"_{lens}")
        found = [x for x in fn(lines, ctx) if x][:8]
        name = spec.LENSES[lens]["name"]
        reading = (f"{name}: {len(found)} matter(s) raised by pattern checks." if found
                   else f"{name}: the pattern checks raise nothing on this document.")
        return {"reading": reading, "findings": found}

    # --- lens heuristics -------------------------------------------------
    def _prudence(self, lines, ctx):
        out = []
        for ln in lines:
            if re.search(r"\b(fraud|litigation|convicted|charged|investigation|insolvency|default(ed)?)\b", ln, re.I):
                out.append(_f("material", "A risk signal appears that the reader must examine directly rather than infer.",
                              ln, "probe", probe="What were the circumstances, and is there any appearance in proceedings?"))
            if re.search(r"\b(final offer|non-negotiable|last chance|or else|we will be forced)\b", ln, re.I):
                out.append(_f("material", "Irrecoverable language: an ultimatum closes a door that may be needed later.", ln, "restate"))
            if re.search(r"\b(privately|off the record|in confidence|told me)\b", ln, re.I):
                out.append(_f("blocking", "A private remark is recited as support; it breaches a confidence.", ln, "omit"))
        return out

    def _veracity(self, lines, ctx):
        out = []
        for ln in lines:
            if re.search(r"\bwill (treat|reach|serve|deliver|achieve)\b", ln, re.I):
                out.append(_f("material", "A projection is stated as fact; it should be stated as a projection, with its basis.", ln, "restate"))
            if re.search(r"\b(approved|granted) patents?\b", ln, re.I):
                out.append(_f("corrective", "Patent status is asserted; applications filed are not patents granted.", ln,
                              probe="Which of these are granted, and under which numbers?"))
            if re.search(r"[-–]\s*(present|current|date)\b", ln, re.I):
                out.append(_f("moderate", f"An open-ended role ('present') is evidenced only to the document's own date; judge currency against {ctx['as_of']}.", ln,
                              "refresh_required"))
            if re.search(r"\b(world[- ]class|best[- ]in[- ]class|unparalleled|leading|renowned|\d+\+)\b", ln, re.I):
                out.append(_f("advisory", "An unverifiable superlative or rounded figure; none contradicted, none verifiable from the document.", ln, "none"))
        return out

    def _architecture(self, lines, ctx):
        out, seen = [], {}
        for ln in lines:
            key = re.sub(r"\W+", " ", ln.lower()).strip()
            if len(key) > 25 and key in seen:
                out.append(_f("advisory", "Said twice: the same line recurs; say a thing once.", ln, "cosmetic"))
            seen[key] = True
            if re.search(r"\w\(|\.\w{2,}\s|\s[,;]", ln):
                out.append(_f("advisory", "Surface defect in spacing or punctuation.", ln, "cosmetic"))
            if "[?]" in ln:
                out.append(_f("corrective", "A value is illegible or cropped in the source; it is marked, not inferred.", ln,
                              state="unreadable", remedy="seek_clarification"))
        if ctx.get("needs_signatory") and not any(
                re.search(r"\b(sign(ed|ature)|signatory|yours (sincerely|faithfully))\b", ln, re.I) for ln in lines):
            out.append(_f("corrective", "No signatory: no result in the document supplied.", "", state="absent"))
        return out

    def _positioning(self, lines, ctx):
        out = []
        for ln in lines:
            if re.search(r"\b(expect(s)? (early )?(orders|approval)|at the earliest|immediately|without delay|by return)\b", ln, re.I):
                out.append(_f("material", "The ask is placed as a pressure, not an opened door.", ln, "restate"))
        return out

    def _purpose(self, lines, ctx):
        if not lines:
            return []
        first = " ".join(lines[:6]).lower()
        if not re.search(r"\b(request|seek|propos|summary|purpose|write to|apply|applying|objective|profile)\b", first):
            return [_f("moderate", "A stranger would not learn within the first lines why this document exists.", lines[0], "restate")]
        return []

    def _detachment(self, lines, ctx):
        out = []
        for ln in lines:
            if re.search(r"\b(oxford|harvard|stanford|cambridge|iit|iim|mckinsey|goldman|tata|reliance|fortune 500)\b", ln, re.I):
                out.append(_f("advisory", "A halo by association; it should decide nothing on its own.", ln, "none"))
        return out[:3]

    def _stewardship(self, lines, ctx):
        out = []
        for ln in lines:
            if re.search(r"\b(date of birth|dob|marital status|religion|caste|sex|gender|father'?s name|passport no)\b", ln, re.I):
                out.append(_f("corrective", "Protected personal data on the page; held for the run only and purged if the file does not proceed.",
                              ln, "none"))
        return out

    # --- reconciliation --------------------------------------------------
    def reconcile(self, findings: list[dict], frozen_text: str, ctx: dict) -> dict:
        groups: dict[str, list[dict]] = {}
        for f in findings:
            key = f"{f['quote'].strip().lower() or 'absent:' + f['id']}|{f['remedy_class']}"
            groups.setdefault(key, []).append(f)
        merged, log = [], []
        for g in groups.values():
            g.sort(key=lambda x: -spec.TIERS[x["tier"]]["rank"])
            top = g[0]
            merged.append({**{k: top[k] for k in _FINDING_PROPS},
                           "source_ids": [x["id"] for x in g],
                           "lenses": sorted({x["lens"] for x in g}, key=list(spec.LENSES).index)})
            if len(g) > 1:
                log.append({"source_ids": [x["id"] for x in g], "conflict": "Same line raised by several lenses.",
                            "canon_rule": "merge", "resolution": f"Merged at tier {top['tier']}."})
        reserved = [f"{m['finding']}" for m in merged if spec.TIERS[m["tier"]]["rank"] >= 4]
        return {
            "findings": merged, "log": log,
            "detachment_read": "Offline engine: halos are listed as findings; no residue is composed.",
            "reconciled_summary": f"{len(merged)} reconciled finding(s) from {len(findings)} lens finding(s).",
            "matters_reserved_to_owner": reserved,
        }

    def rewrite(self, frozen_text: str, accepted: list[dict], ctx: dict) -> dict:
        text = "\n".join(_lines(frozen_text))
        changes = []
        for f in accepted:
            if f["remedy_class"] == "omit" and f["quote"]:
                text = text.replace(f["quote"], "")
                changes.append(f"Omitted: {f['quote'][:60]}")
            elif f["quote"]:
                text = text.replace(f["quote"], f"{f['quote']} [revise: {f['finding'][:60]}]")
                changes.append(f"Marked for revision: {f['quote'][:60]}")
        return {"revised_text": text, "changes": changes}


def make_engine(kind: str, model: str = "claude-opus-5", effort: str = "high") -> Engine:
    if kind == "offline":
        return OfflineEngine()
    return ClaudeEngine(model=model, effort=effort)
