"""The runtime: a phase-gated state machine that enforces the seven invariants.

    0 Freeze -> 1 Parallel audit -> 2 Reconcile -> [Owner gate] -> 3 Rewrite/decide
      -> 4 Re-pass (cycle 2, at most) -> [Releaser gate] -> Released

I1 input integrity   - pack hashed at freeze, re-verified at every phase
I2 lens isolation    - one model call per lens; no lens sees another's findings
I3 human gates       - no release without a recorded Owner decision and a Releaser signature
I4 termination       - at most two cycles per version; a clean pass is terminal
I5 output boundary   - outputs carry run ref, spec version, method hash; nothing about the maker
I6 single register   - append-only, hash-chained register of every event
I7 method fidelity   - method hash computed at load, recorded at freeze, re-verified every phase
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict

from . import spec
from .engine import Engine, make_engine
from .freeze import FrozenDoc, freeze_file, locate, proof_candidates, render_for_reading, verify
from .register import Register
from .request import RunRequest
from .vault import Vault


class GuardRefusal(RuntimeError):
    """A conformance refusal. Hard-coded; configurable by no one (FR-11)."""


class Aborted(RuntimeError):
    pass


STATES = [
    "opened", "frozen", "auditing", "paused", "audited", "reconciled",
    "awaiting_owner", "owner_decided", "awaiting_release", "released",
    "closed_not_releasable", "stopped", "aborted", "purged",
]

DECISIONS = {
    "accept": "Owner accepts the finding; its remedy is to be applied.",
    "adjudicate": "Owner records a first-hand adjudication, which becomes the finding.",
    "residual_risk": "Owner accepts the residual risk, with reasons.",
    "reject": "Owner rejects the finding, with reasons.",
}


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def boundary_check(text: str) -> list[str]:
    return [p for p in spec.FORBIDDEN_PROVENANCE_PATTERNS if re.search(p, text or "", re.I)]


def certificate_check(text: str) -> None:
    for p in spec.FORBIDDEN_CERT_PATTERNS:
        if re.search(p, text or "", re.I):
            raise GuardRefusal(
                "REFUSED: certificate language claims compliance or certification; "
                "the protocol claims alignment only."
            )


class Run:
    """One run of one version of one pack."""

    def __init__(self, workdir: str, engine: Engine | None = None):
        self.workdir = workdir
        self.register = Register(os.path.join(workdir, "register.jsonl"))
        self.vault = Vault(os.path.join(workdir, "vault"))
        self.engine = engine
        self.state: dict = {}
        self._resume = threading.Event()
        self._resume.set()
        self._stop = threading.Event()

    # --------------------------------------------------------- persistence
    @property
    def run_id(self) -> str:
        return self.state["run_id"]

    def _save(self) -> None:
        self.vault.put(self.run_id, "state", self.state)
        idx_path = os.path.join(self.workdir, "index.json")
        idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
        idx[self.run_id] = {"status": self.state["status"], "profile": self.state["request"]["profile"],
                            "subject": self.state["request"]["subject"], "cycle": self.state["request"]["cycle"],
                            "verdict": self.state.get("verdict"), "updated": _now()}
        with open(idx_path, "w") as f:
            json.dump(idx, f, indent=1)

    @classmethod
    def load(cls, workdir: str, run_id: str, engine: Engine | None = None) -> "Run":
        r = cls(workdir, engine)
        try:
            r.state = r.vault.get(run_id, "state")
        except KeyError:
            raise GuardRefusal(f"run {run_id} has been purged; only its register events survive")
        if r.engine is None:
            req = r.state["request"]
            r.engine = make_engine(req["engine"], req["model"], req["effort"])
        return r

    def _event(self, kind: str, data: dict | None = None) -> None:
        self.register.append(self.run_id, kind, data or {})

    def _set(self, status: str) -> None:
        self.state["status"] = status
        self._event(f"state.{status}")
        self._save()

    # ------------------------------------------------------------ invariants
    def _check_invariants(self, phase: str) -> None:
        if self.state["status"] in ("purged", "aborted"):
            raise GuardRefusal(f"run is {self.state['status']}")
        if spec.method_hash() != self.state["method_hash"]:
            self._abort(f"method drift detected at {phase} (I7)")
        for d in self.state["docs"]:
            try:
                verify(FrozenDoc(**d))
            except Exception as e:
                self._abort(f"{e} (I1)")

    def _abort(self, reason: str):
        self.state["status"] = "aborted"
        self.state["abort_reason"] = reason
        self._event("run.aborted", {"reason": reason})
        self._save()
        raise Aborted(reason)

    def _docs(self) -> list[FrozenDoc]:
        return [FrozenDoc(**d) for d in self.state["docs"]]

    def _ctx(self) -> dict:
        req = self.state["request"]
        return {
            "profile_label": spec.PROFILES[req["profile"]]["label"],
            "audience": req["audience"], "as_of": req["as_of"], "subject": req["subject"],
            "purpose": req["purpose"], "requisition": req["requisition"],
            "standing_disclosures": req["standing_disclosures"],
            "external_inputs": req["external_inputs"],
            "prior_adjudications": self.state.get("prior_adjudications", []),
            "needs_signatory": req["profile"] in ("general", "clinical", "legal"),
            "tier_anchors": spec.tier_anchors(req["profile"]),
            "proof_candidates": proof_candidates(self._docs()) if self.state.get("docs") else [],
        }

    # ============================================================ Phase 0
    def open_and_freeze(self, request: RunRequest) -> str:
        if self.engine is None:
            self.engine = make_engine(request.engine, request.model, request.effort)
        method = spec.method_hash()  # computed at load
        run_id = self.register.next_run_id(request.as_of)
        self.state = {"run_id": run_id, "status": "opened", "request": request.to_dict(),
                      "method_hash": method, "spec_version": spec.SPEC_VERSION, "opened_at": _now()}
        self.register.append(run_id, "run.opened", {"profile": request.profile, "cycle": request.cycle,
                                                     "prior_run_id": request.prior_run_id})
        if request.cycle == 2:
            self._inherit_prior(request.prior_run_id)

        docs = [freeze_file(i, p, transcriber=self.engine.transcribe) for i, p in enumerate(request.pack, 1)]
        self.state["docs"] = [asdict(d) for d in docs]
        self.state["frozen_text"] = render_for_reading(docs)
        self.state["model_identity"] = self.engine.identity()
        self.state["frozen_at"] = _now()
        self._event("run.frozen", {
            "files": [{"name": d.filename, "sha256": d.sha256, "pages": d.pages, "text_layer": d.text_layer} for d in docs],
            "method_hash": method, "spec_version": spec.SPEC_VERSION,
            "model_identity": self.state["model_identity"], "as_of": request.as_of,
        })
        self._set("frozen")
        return run_id

    def verify_contemporary_facts(self) -> list[dict]:
        """Phase 0, continued: contemporary public facts verified at the freeze, or reported unverified.

        Runs only when the request allows web verification. The results are
        appended to the frozen text as freeze-record lines, so every lens
        reads the same verified context. Searches concern third-party public
        facts only, never the subject's name or personal identifiers.
        """
        req = self.state["request"]
        if self.state["status"] != "frozen":
            raise GuardRefusal("facts are verified at the freeze, before the audit")
        if not req["allow_web_verification"]:
            raise GuardRefusal("web verification is not allowed by this request")
        if self.state.get("facts_verified"):
            return self.state["verified_facts"]
        self._check_invariants("fact_verification")
        out = self.engine.verify_facts(self.state["frozen_text"], self._ctx(), req["contemporary_facts"])
        facts = []
        for f in out.get("facts", []):
            loc = locate(self._docs(), f.get("quote", "")) if f.get("quote") else None
            facts.append({**f, "location": loc or "-"})
        lines = ["=== FREEZE RECORD: CONTEMPORARY FACTS CHECKED AT FREEZE "
                 f"({dt.date.today().isoformat()}; third-party public facts only) ==="]
        for f in facts:
            src = "; ".join(f.get("sources", [])[:3]) or "no source"
            lines.append(f"[{f['location']}] {f['status'].upper()}: {f['claim']} - {f['finding']} (sources: {src})")
        if not facts:
            lines.append("No contemporary public facts required verification.")
        self.state["frozen_text"] += "\n" + "\n".join(lines)
        self.state["verified_facts"] = facts
        self.state["facts_verified"] = True
        self._event("facts.verified", {"count": len(facts),
                                       "statuses": [f["status"] for f in facts],
                                       "claims": [f["claim"][:80] for f in facts]})
        self._save()
        return facts

    def _inherit_prior(self, prior_id: str) -> None:
        prior = Run.load(self.workdir, prior_id, engine=self.engine)
        if prior.state["request"]["cycle"] >= spec.MAX_CYCLES:
            raise GuardRefusal("REFUSED: two-cycle cap reached for this version (I4)")
        if prior.state["status"] not in ("owner_decided", "awaiting_release", "closed_not_releasable"):
            raise GuardRefusal("REFUSED: cycle 2 requires a recorded Owner decision on cycle 1 (I3)")
        adj = []
        for f in prior.state["findings"]:
            d = prior.state["decisions"].get(f["id"])
            if d:
                adj.append(f"{f['id']} ({f['tier']}): {f['finding']} -> Owner: {d['decision']}"
                           + (f" - {d['note']}" if d.get("note") else ""))
        self.state["prior_adjudications"] = adj

    # ============================================================ Phase 1
    def audit(self) -> None:
        if self.state["status"] not in ("frozen", "paused"):
            raise GuardRefusal(f"audit cannot start from state {self.state['status']}")
        self._check_invariants("audit")
        if self.state["request"]["allow_web_verification"] and not self.state.get("facts_verified"):
            raise GuardRefusal("REFUSED: contemporary facts must be verified at the freeze before the audit")
        self._set("auditing")
        req = self.state["request"]
        text, ctx = self.state["frozen_text"], self._ctx()
        done = self.state.setdefault("lens_outputs", {})

        def one(lens: str):
            self._resume.wait()
            if self._stop.is_set():
                return lens, None
            charter = spec.charter_for(lens, req["profile"])
            # I2: the call carries the frozen text, the context and this lens's
            # charter only. Nothing from any other lens is passed in.
            return lens, self.engine.read_lens(lens, charter, text, ctx)

        todo = [l for l in spec.LENSES if l not in done]
        with ThreadPoolExecutor(max_workers=7) as pool:
            for lens, out in pool.map(one, todo):
                if out is None:
                    continue
                done[lens] = self._gate_citations(lens, out)
                self._event("lens.completed", {"lens": lens, "findings": len(done[lens]["findings"]),
                                               "rejected": len(done[lens]["rejected"])})
        if self._stop.is_set():
            self._set("stopped")
            return
        if len(done) < len(spec.LENSES):
            self._set("paused")
            return
        self.state["model_identity"] = self.engine.identity()
        self._set("audited")

    def _gate_citations(self, lens: str, out: dict) -> dict:
        """Citation-gated findings: a quote not found in the frozen source is rejected."""
        kept, rejected = [], []
        for i, f in enumerate(out.get("findings", []), 1):
            f = {**f, "id": f"{lens}.{i}", "lens": lens}
            if f["evidence_state"] == "present":
                loc = locate(self._docs(), f["quote"])
                if not loc:
                    rejected.append({**f, "reason": "quotation not found in the frozen source"})
                    continue
                f["location"] = loc
            else:
                f["location"] = "-"
            if boundary_check(f["finding"] + f.get("disposition", "")):
                rejected.append({**f, "reason": "output boundary (I5)"})
                continue
            kept.append(f)
        return {"reading": out.get("reading", ""), "findings": kept, "rejected": rejected}

    def pause(self) -> None:
        self._resume.clear()
        self._event("run.pause_requested")

    def resume(self) -> None:
        self._resume.set()
        self._event("run.resume_requested")

    def stop(self) -> None:
        self._stop.set()
        self._resume.set()
        self._event("run.stop_requested")

    # ============================================================ Phase 2
    def reconcile(self) -> None:
        if self.state["status"] != "audited":
            raise GuardRefusal("reconciliation requires a completed seven-lens audit")
        self._check_invariants("reconcile")
        all_f = [f for lo in self.state["lens_outputs"].values() for f in lo["findings"]]
        out = self.engine.reconcile(all_f, self.state["frozen_text"], self._ctx())
        by_id = {f["id"]: f for f in all_f}

        merged, counters = [], {t: 0 for t in spec.TIERS}
        accounted = set()
        for m in sorted(out["findings"], key=lambda x: -spec.TIERS[x["tier"]]["rank"]):
            srcs = [s for s in m["source_ids"] if s in by_id]
            if not srcs:
                continue  # reconciliation may not invent findings
            if m["evidence_state"] == "present":
                loc = locate(self._docs(), m["quote"])
                if not loc:  # fall back to the source finding's verified quote
                    src = by_id[srcs[0]]
                    m = {**m, "quote": src["quote"], "evidence_state": src["evidence_state"]}
                    loc = src.get("location", "-")
            else:
                loc = "-"
            counters[m["tier"]] += 1
            accounted.update(srcs)
            merged.append({**m, "id": f"{spec.TIERS[m['tier']]['prefix']}{counters[m['tier']]}",
                           "source_ids": srcs, "location": loc})
        log = list(out["log"])
        # Every source finding must be merged or dismissed on the log.
        logged = {s for e in log for s in e["source_ids"]}
        for fid, f in by_id.items():
            if fid not in accounted and fid not in logged:
                counters[f["tier"]] += 1
                merged.append({**{k: f[k] for k in ("tier", "finding", "quote", "evidence_state",
                                                    "remedy_class", "disposition", "probe", "location")},
                               "lenses": [f["lens"]], "source_ids": [fid],
                               "id": f"{spec.TIERS[f['tier']]['prefix']}{counters[f['tier']]}"})
                log.append({"source_ids": [fid], "conflict": "Not accounted for by reconciliation.",
                            "canon_rule": "merge", "resolution": "Carried forward unchanged."})

        self.state.update({
            "findings": merged, "reconciliation_log": log,
            "detachment_read": out["detachment_read"],
            "reconciled_summary": out["reconciled_summary"],
            "matters_reserved_to_owner": out["matters_reserved_to_owner"],
            "decisions": {}, "verdict": self._verdict(merged),
        })
        self._event("run.reconciled", {"findings": {t: c for t, c in counters.items() if c},
                                       "log_entries": len(log), "verdict": self.state["verdict"]})
        self._set("reconciled")
        self._set("awaiting_owner")

    @staticmethod
    def _verdict(findings: list[dict]) -> str:
        tiers = {f["tier"] for f in findings}
        if "blocking" in tiers:
            return "blocking"
        if tiers & {"material", "corrective"}:
            return "corrective"
        return "clean"

    # ============================================================ Owner gate
    def decide(self, owner_name: str, decisions: dict[str, dict]) -> None:
        """I3, first human moment. decisions = {finding_id: {"decision": ..., "note": ...}}."""
        if self.state["status"] != "awaiting_owner":
            raise GuardRefusal(f"no Owner decision is pending (state {self.state['status']})")
        self._check_invariants("owner_decision")
        owner = self.state["request"]["owner"]
        if owner_name.strip().lower() != owner["name"].strip().lower():
            raise GuardRefusal("REFUSED: only the named Owner may decide")
        ids = {f["id"]: f for f in self.state["findings"]}
        for fid, d in decisions.items():
            if fid not in ids:
                raise GuardRefusal(f"unknown finding {fid}")
            if d.get("decision") not in DECISIONS:
                raise GuardRefusal(f"decision for {fid} must be one of {list(DECISIONS)}")
            if ids[fid]["tier"] == "blocking" and d["decision"] in ("reject", "residual_risk"):
                raise GuardRefusal("REFUSED: a Blocking finding cannot be waived, by anyone, ever")
            if d["decision"] in ("reject", "residual_risk", "adjudicate") and not d.get("note", "").strip():
                raise GuardRefusal(f"{fid}: '{d['decision']}' requires reasons")
        missing = set(ids) - set(decisions)
        if missing:
            raise GuardRefusal(f"the Owner must decide every finding; missing {sorted(missing)}")
        self.state["decisions"] = {fid: {**d, "by": owner_name, "at": _now()} for fid, d in decisions.items()}
        self._event("owner.decided", {"owner": owner_name,
                                      "decisions": {k: v["decision"] for k, v in decisions.items()}})
        blocking = [f for f in self.state["findings"] if f["tier"] == "blocking"]
        needs_change = [f for f in self.state["findings"]
                        if decisions[f["id"]]["decision"] == "accept" and f["tier"] in ("blocking", "material", "corrective")]
        self._set("owner_decided")
        if blocking or (needs_change and self.state["request"]["profile"] == "general"):
            # The version cannot be released as it stands: the remedies must be
            # applied and the revised version re-read (cycle 2).
            if self.state["request"]["cycle"] >= spec.MAX_CYCLES:
                self._set("closed_not_releasable")
            return
        self._set("awaiting_release")

    def integrated_rewrite(self) -> dict:
        """Phase 3: one hand absorbs the accepted remedies. Nothing is applied without the Owner."""
        if self.state["status"] not in ("owner_decided", "awaiting_release"):
            raise GuardRefusal("the integrated rewrite follows the Owner decision")
        self._check_invariants("rewrite")
        accepted = [f for f in self.state["findings"] if self.state["decisions"][f["id"]]["decision"] == "accept"]
        out = self.engine.rewrite(self.state["frozen_text"], accepted, self._ctx())
        self.state["proposed_rewrite"] = out
        self._event("rewrite.proposed", {"changes": len(out["changes"])})
        self._save()
        return out

    # ========================================================= Releaser gate
    def sign(self, releaser_name: str, meaning: str = "Authorised for release") -> dict:
        """I3, second human moment. Emits the Release Certificate."""
        self._check_invariants("release")
        if self.state["status"] != "awaiting_release":
            if self.state["status"] in ("owner_decided", "closed_not_releasable"):
                raise GuardRefusal("REFUSED: this version cannot be released; its remedies must be applied "
                                   "and re-read (cycle 2), or it is closed under the two-cycle cap")
            raise GuardRefusal("REFUSED: any release without both human moments")
        if any(f["tier"] == "blocking" for f in self.state["findings"]):
            raise GuardRefusal("REFUSED: a Blocking finding stands")
        rel = self.state["request"].get("releaser") or {}
        if not rel.get("name") or releaser_name.strip().lower() != rel["name"].strip().lower():
            raise GuardRefusal("REFUSED: only the named Releaser may sign")
        owner = self.state["request"]["owner"]["name"]
        if releaser_name.strip().lower() == owner.strip().lower():
            raise GuardRefusal("REFUSED: Owner and Releaser must be different people")
        cert_text = (f"Standards passed: all seven lenses executed on the frozen version. "
                     f"Verdict {self.state['verdict']}. Aligned with, not certified under, any regime.")
        certificate_check(cert_text.replace("not certified under", ""))
        cert = {
            "run_id": self.run_id, "spec_version": self.state["spec_version"],
            "method_hash": self.state["method_hash"],
            "files": [{"name": d["filename"], "sha256": d["sha256"]} for d in self.state["docs"]],
            "verdict": self.state["verdict"], "text": cert_text,
            "owner": {"name": owner, "at": next(iter(self.state["decisions"].values()), {}).get("at")},
            "releaser": {"name": releaser_name, "at": _now(), "meaning": meaning},
            "retention_days": self.state["request"]["retention_days"],
        }
        self.state["certificate"] = cert
        self._event("release.signed", {"releaser": releaser_name, "meaning": meaning,
                                       "verdict": self.state["verdict"]})
        self._set("released")
        return cert

    # ================================================================ purge
    def purge(self, reason: str = "file does not proceed") -> None:
        rid = self.run_id
        self.register.append(rid, "run.purged", {"reason": reason})
        idx_path = os.path.join(self.workdir, "index.json")
        idx = json.load(open(idx_path)) if os.path.exists(idx_path) else {}
        if rid in idx:
            idx[rid] = {"status": "purged", "updated": _now()}
            json.dump(idx, open(idx_path, "w"), indent=1)
        self.vault.purge(rid)
        self.state = {"run_id": rid, "status": "purged"}


def list_runs(workdir: str) -> dict:
    p = os.path.join(workdir, "index.json")
    return json.load(open(p)) if os.path.exists(p) else {}
