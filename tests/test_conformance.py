"""Conformance harness: every refusal and invariant, checked with the offline engine."""

import json
import os
import shutil

import pytest

from saptadrishti import spec
from saptadrishti.engine import OfflineEngine
from saptadrishti.freeze import FreezeError, locate, freeze_file
from saptadrishti.protocol import Aborted, GuardRefusal, Run, certificate_check
from saptadrishti.register import Register, RegisterError
from saptadrishti.request import RequestError, RunRequest

HERE = os.path.dirname(__file__)
PACKS = os.path.join(HERE, "..", "examples", "packs")


@pytest.fixture
def pack(tmp_path):
    def make(name="land_letter.txt"):
        dst = tmp_path / name
        shutil.copy(os.path.join(PACKS, name), dst)
        return str(dst)
    return make


def req(path, **kw):
    d = {"pack": [path], "owner": {"name": "Olive Owner"}, "releaser": {"name": "Rex Releaser"},
         "as_of": "2026-09-27", "engine": "offline", **kw}
    return RunRequest.from_dict(d)


def run_to_owner(tmp_path, path, **kw):
    r = Run(str(tmp_path / "wd"), engine=OfflineEngine())
    r.open_and_freeze(req(path, **kw))
    r.audit()
    r.reconcile()
    return r


def accept_all(r, note="ok"):
    return {f["id"]: {"decision": "accept", "note": note} for f in r.state["findings"]}


# ------------------------------------------------------------ requests ---

def test_request_requires_owner(pack):
    with pytest.raises(RequestError):
        RunRequest.from_dict({"pack": [pack()], "engine": "offline"})


def test_request_rejects_unknown_fields(pack):
    with pytest.raises(RequestError):
        RunRequest.from_dict({"pack": [pack()], "owner": {"name": "x"}, "tone": "friendly"})


def test_request_cycle_cap(pack):
    with pytest.raises(RequestError):
        req(pack(), cycle=3, prior_run_id="x")


def test_default_audience_from_profile(pack):
    assert req(pack("candidate_cv.txt"), profile="cv").audience == spec.PROFILES["cv"]["default_audience"]


# ---------------------------------------------------------- I1 / I7 ------

def test_freeze_records_hash_method_and_model(tmp_path, pack):
    r = run_to_owner(tmp_path, pack())
    frozen = [e for e in r.register.events(r.run_id) if e["kind"] == "run.frozen"][0]["data"]
    assert len(frozen["files"][0]["sha256"]) == 64
    assert frozen["method_hash"] == spec.method_hash()
    assert "offline" in frozen["model_identity"]


def test_input_drift_aborts(tmp_path, pack):
    p = pack()
    r = Run(str(tmp_path / "wd"), engine=OfflineEngine())
    r.open_and_freeze(req(p))
    with open(p, "a") as f:
        f.write("one more line")
    with pytest.raises(Aborted):
        r.audit()
    assert r.state["status"] == "aborted"


def test_method_drift_aborts(tmp_path, pack, monkeypatch):
    r = Run(str(tmp_path / "wd"), engine=OfflineEngine())
    r.open_and_freeze(req(pack()))
    monkeypatch.setitem(spec.LENSES["prudence"], "charter", "a quietly edited charter")
    with pytest.raises(Aborted):
        r.audit()


def test_method_hash_changes_with_charter(monkeypatch):
    h = spec.method_hash()
    monkeypatch.setitem(spec.LENSES["veracity"], "question", "changed?")
    assert spec.method_hash() != h


# ------------------------------------------------------------- I2 --------

def test_lenses_are_isolated(tmp_path, pack):
    eng = OfflineEngine()
    r = Run(str(tmp_path / "wd"), engine=eng)
    r.open_and_freeze(req(pack()))
    r.audit()
    assert sorted(c["lens"] for c in eng.calls) == sorted(spec.LENSES)
    texts = {c["text"] for c in eng.calls}
    assert len(texts) == 1  # every lens read the identical frozen text
    for c in eng.calls:
        assert "findings" not in json.dumps(c["ctx"])  # nothing from another lens


# ------------------------------------------------------- citation gate ---

def test_fabricated_quote_is_rejected(tmp_path, pack):
    class Liar(OfflineEngine):
        def read_lens(self, lens, charter, text, ctx):
            return {"reading": "x", "findings": [{
                "tier": "material", "finding": "invented", "quote": "a sentence that is not in the letter",
                "evidence_state": "present", "remedy_class": "restate", "disposition": "", "probe": ""}]}
    r = Run(str(tmp_path / "wd"), engine=Liar())
    r.open_and_freeze(req(pack()))
    r.audit()
    assert all(not lo["findings"] and lo["rejected"] for lo in r.state["lens_outputs"].values())


def test_locate_handles_typography_and_line_breaks(pack, tmp_path):
    p = tmp_path / "t.txt"
    p.write_text("The centre will\ntreat 30,000 patients — in year one.\n")
    d = freeze_file(1, str(p))
    assert locate([d], "will treat 30,000 patients - in year one") == "D1 p1 L1"
    assert locate([d], "treat 30,000") == "D1 p1 L2"
    assert locate([d], "cure everyone") is None


def test_absent_data_needs_no_quote(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="general")
    absent = [f for f in r.state["findings"] if f["evidence_state"] == "absent"]
    assert absent and absent[0]["location"] == "-"


def test_output_boundary(tmp_path, pack):
    class Boaster(OfflineEngine):
        def read_lens(self, lens, charter, text, ctx):
            return {"reading": "x", "findings": [{
                "tier": "advisory", "finding": "This protocol is dedicated to a foundation.",
                "quote": "Yours faithfully", "evidence_state": "present", "remedy_class": "none",
                "disposition": "", "probe": ""}]}
    r = Run(str(tmp_path / "wd"), engine=Boaster())
    r.open_and_freeze(req(pack()))
    r.audit()
    assert all(lo["rejected"][0]["reason"].startswith("output boundary") for lo in r.state["lens_outputs"].values())


# ------------------------------------------------------- reconciliation --

def test_every_lens_finding_is_accounted_for(tmp_path, pack):
    r = run_to_owner(tmp_path, pack())
    src = {f["id"] for lo in r.state["lens_outputs"].values() for f in lo["findings"]}
    got = {s for f in r.state["findings"] for s in f["source_ids"]}
    logged = {s for e in r.state["reconciliation_log"] for s in e["source_ids"]}
    assert src <= got | logged


def test_reconciliation_cannot_invent_findings(tmp_path, pack):
    class Inventor(OfflineEngine):
        def reconcile(self, findings, text, ctx):
            out = super().reconcile(findings, text, ctx)
            out["findings"].append({**out["findings"][0], "source_ids": ["ghost.1"], "finding": "invented"})
            return out
    r = Run(str(tmp_path / "wd"), engine=Inventor())
    r.open_and_freeze(req(pack()))
    r.audit()
    r.reconcile()
    assert not any(f["finding"] == "invented" for f in r.state["findings"])


def test_ids_follow_tier_prefixes(tmp_path, pack):
    r = run_to_owner(tmp_path, pack())
    for f in r.state["findings"]:
        assert f["id"][0] == spec.TIERS[f["tier"]]["prefix"]


# ------------------------------------------------------------- I3 --------

def test_blocking_cannot_be_waived(tmp_path, pack):
    r = run_to_owner(tmp_path, pack())
    assert r.state["verdict"] == "blocking"
    d = accept_all(r)
    b = next(f["id"] for f in r.state["findings"] if f["tier"] == "blocking")
    for waiver in ("reject", "residual_risk"):
        d[b] = {"decision": waiver, "note": "we would rather keep it"}
        with pytest.raises(GuardRefusal, match="cannot be waived"):
            r.decide("Olive Owner", d)


def test_only_named_owner_decides(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="cv")
    with pytest.raises(GuardRefusal, match="named Owner"):
        r.decide("Somebody Else", accept_all(r))


def test_owner_must_decide_every_finding(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="cv")
    d = accept_all(r)
    d.pop(next(iter(d)))
    with pytest.raises(GuardRefusal, match="every finding"):
        r.decide("Olive Owner", d)


def test_rejection_needs_reasons(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="cv")
    d = {k: {"decision": "reject", "note": ""} for k in accept_all(r)}
    with pytest.raises(GuardRefusal, match="reasons"):
        r.decide("Olive Owner", d)


def test_no_release_without_owner_decision(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="cv")
    with pytest.raises(GuardRefusal, match="both human moments"):
        r.sign("Rex Releaser")


def test_release_needs_named_distinct_releaser(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="cv")
    r.decide("Olive Owner", accept_all(r))
    with pytest.raises(GuardRefusal):
        r.sign("Olive Owner")
    cert = r.sign("Rex Releaser")
    assert cert["files"][0]["sha256"] == r.state["docs"][0]["sha256"]
    assert r.state["status"] == "released"


def test_blocking_version_is_not_releasable(tmp_path, pack):
    r = run_to_owner(tmp_path, pack())
    r.decide("Olive Owner", accept_all(r))
    assert r.state["status"] == "owner_decided"
    with pytest.raises(GuardRefusal, match="cannot be released"):
        r.sign("Rex Releaser")


# ------------------------------------------------------------- I4 --------

def test_cycle_two_honours_adjudications_and_cap(tmp_path, pack):
    wd = str(tmp_path / "wd")
    r1 = run_to_owner(tmp_path, pack())
    r1.decide("Olive Owner", accept_all(r1, "agreed"))
    revised = tmp_path / "revised.txt"
    revised.write_text("To the Department\nWe request your consideration of a land allotment.\n"
                       "The centre is projected to serve about 30,000 patients a year.\nYours faithfully,\nDirector\n")
    r2 = Run(wd, engine=OfflineEngine())
    r2.open_and_freeze(req(str(revised), cycle=2, prior_run_id=r1.run_id))
    assert r2.state["prior_adjudications"]
    r2.audit()
    r2.reconcile()
    assert r2.state["verdict"] != "blocking"
    r2.decide("Olive Owner", accept_all(r2))
    r2.sign("Rex Releaser")
    r3 = Run(wd, engine=OfflineEngine())
    with pytest.raises(GuardRefusal, match="two-cycle cap"):
        r3.open_and_freeze(req(str(revised), cycle=2, prior_run_id=r2.run_id))


# ------------------------------------------------------- I6 / purge ------

def test_register_is_hash_chained(tmp_path, pack):
    r = run_to_owner(tmp_path, pack())
    assert r.register.verify_chain()
    lines = open(r.register.path).read().splitlines()
    ev = json.loads(lines[2])
    ev["data"] = {"tampered": True}
    lines[2] = json.dumps(ev)
    open(r.register.path, "w").write("\n".join(lines) + "\n")
    with pytest.raises(RegisterError):
        r.register.verify_chain()


def test_purge_destroys_content_keeps_event(tmp_path, pack):
    r = run_to_owner(tmp_path, pack("candidate_cv.txt"), profile="cv")
    rid, wd = r.run_id, r.workdir
    r.purge()
    with pytest.raises(GuardRefusal, match="purged"):
        Run.load(wd, rid)
    assert Register(os.path.join(wd, "register.jsonl")).events(rid)[-1]["kind"] == "run.purged"


def test_run_ids_follow_date_letter_convention(tmp_path, pack):
    wd = str(tmp_path / "wd")
    ids = []
    for _ in range(2):
        r = Run(wd, engine=OfflineEngine())
        ids.append(r.open_and_freeze(req(pack())))
    assert ids == ["2026-0927-A", "2026-0927-B"]


# ----------------------------------------------------- certificate text --

def test_certificate_refuses_compliance_language():
    with pytest.raises(GuardRefusal):
        certificate_check("This document is compliant with 21 CFR Part 11.")
    certificate_check("Aligned with ISO/IEC 42001 practices.")


def test_scanned_pdf_needs_transcriber(tmp_path):
    from pypdf import PdfWriter
    p = tmp_path / "scan.pdf"
    w = PdfWriter()
    w.add_blank_page(width=200, height=200)
    w.write(str(p))
    with pytest.raises(FreezeError, match="no text layer"):
        freeze_file(1, str(p))
    d = freeze_file(1, str(p), transcriber=lambda path, n: ["Transcribed line one\nLine two"])
    assert not d.text_layer and d.lines[0]["text"] == "Transcribed line one"
