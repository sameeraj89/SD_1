"""Command-line surface.

  sd schema                         print the run-request JSON schema
  sd run REQUEST.json               Phase 0-2: freeze, seven-lens audit, reconcile
  sd decide RUN --owner NAME ...    Owner gate (first human moment)
  sd rewrite RUN                    Phase 3: propose the integrated rewrite
  sd sign RUN --releaser NAME       Releaser gate (second human moment)
  sd record RUN [--html]            write the Run Record
  sd artefacts RUN                  the five Artefacts as JSON
  sd purge RUN                      destroy the run key; the register keeps the fact
  sd register [--verify] [RUN]      register extract
  sd list                           runs in this workdir
  sd serve [--port 8765]            local web app
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from . import report, spec
from .protocol import Aborted, GuardRefusal, Run, list_runs
from .request import REQUEST_JSON_SCHEMA, RequestError, RunRequest


def _workdir(a) -> str:
    return os.path.abspath(a.workdir)


def _print_findings(run: Run) -> None:
    s = run.state
    print(f"\nRun {s['run_id']} · verdict {s['verdict']} · status {s['status']}")
    for f in s["findings"]:
        lenses = "·".join(spec.LENSES[l]["name"] for l in f["lenses"])
        print(f"  {f['id']:<4} {f['tier']:<10} {lenses:<24} {f['location']:<12} {f['finding']}")
    rej = sum(len(lo["rejected"]) for lo in s["lens_outputs"].values())
    if rej:
        print(f"  ({rej} lens finding(s) rejected at the citation gate)")


def cmd_run(a):
    with open(a.request) as f:
        d = json.load(f)
    base = os.path.dirname(os.path.abspath(a.request))
    d["pack"] = [p if os.path.isabs(p) else os.path.join(base, p) for p in d["pack"]]
    if a.engine:
        d["engine"] = a.engine
    req = RunRequest.from_dict(d)
    run = Run(_workdir(a))
    rid = run.open_and_freeze(req)
    print(f"Frozen as Run {rid}; method {run.state['method_hash'][:12]}; model {run.state['model_identity']}")
    run.audit()
    run.reconcile()
    _print_findings(run)
    path = _write_record(run, a)
    print(f"\nRun Record: {path}\nNext: sd decide {rid} --owner \"{req.owner.name}\" --decisions FILE.json")


def _write_record(run: Run, a) -> str:
    os.makedirs(os.path.join(_workdir(a), "records"), exist_ok=True)
    ev = run.register.events(run.run_id)
    run.register.verify_chain()
    md = report.run_record_markdown(run.state, ev)
    p = os.path.join(_workdir(a), "records", f"{run.run_id}.md")
    open(p, "w").write(md)
    if getattr(a, "html", False):
        p2 = p[:-3] + ".html"
        open(p2, "w").write(report.run_record_html(run.state, ev))
        return p2
    return p


def cmd_decide(a):
    run = Run.load(_workdir(a), a.run)
    if a.decisions:
        decisions = json.load(open(a.decisions))
    elif a.all:
        decisions = {f["id"]: {"decision": a.all, "note": a.note or ""} for f in run.state["findings"]}
    else:
        sys.exit("give --decisions FILE.json or --all accept|reject|residual_risk|adjudicate")
    run.decide(a.owner, decisions)
    print(f"Owner decision recorded; status {run.state['status']}")
    _write_record(run, a)


def cmd_rewrite(a):
    run = Run.load(_workdir(a), a.run)
    out = run.integrated_rewrite()
    p = os.path.join(_workdir(a), "records", f"{run.run_id}.rewrite.txt")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w").write(out["revised_text"])
    print("\n".join(f"- {c}" for c in out["changes"]))
    print(f"Proposed revision: {p}\nThe Owner accepts it by re-freezing it as cycle 2 (prior_run_id {run.run_id}).")


def cmd_sign(a):
    run = Run.load(_workdir(a), a.run)
    cert = run.sign(a.releaser, a.meaning)
    print(json.dumps(cert, indent=1))
    _write_record(run, a)


def cmd_record(a):
    run = Run.load(_workdir(a), a.run)
    print(_write_record(run, a))


def cmd_artefacts(a):
    run = Run.load(_workdir(a), a.run)
    print(json.dumps(report.artefacts(run.state, run.register.events(run.run_id)), indent=1, ensure_ascii=False))


def cmd_purge(a):
    run = Run.load(_workdir(a), a.run)
    run.purge(a.reason)
    print(f"Run {a.run} purged by key destruction; the register keeps the event.")


def cmd_register(a):
    from .register import Register
    r = Register(os.path.join(_workdir(a), "register.jsonl"))
    if a.verify:
        r.verify_chain()
        print("register chain verified")
    for e in r.events(a.run):
        print(f"{e['seq']:>4} {e['at']} {e['run_id']} {e['kind']} {json.dumps(e['data'], ensure_ascii=False)[:120]}")


def cmd_list(a):
    for rid, v in list_runs(_workdir(a)).items():
        print(rid, json.dumps(v))


def cmd_schema(a):
    print(json.dumps(REQUEST_JSON_SCHEMA, indent=1))


def cmd_serve(a):
    from .server import serve
    serve(_workdir(a), a.port)


def main(argv=None):
    p = argparse.ArgumentParser(prog="sd", description="SaptaDrishti review-gate prototype")
    p.add_argument("--workdir", default=os.environ.get("SD_WORKDIR", ".sd"))
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("run"); s.add_argument("request"); s.add_argument("--engine", choices=["claude", "offline"]); s.add_argument("--html", action="store_true"); s.set_defaults(fn=cmd_run)
    s = sub.add_parser("decide"); s.add_argument("run"); s.add_argument("--owner", required=True); s.add_argument("--decisions"); s.add_argument("--all", choices=["accept", "reject", "residual_risk", "adjudicate"]); s.add_argument("--note"); s.set_defaults(fn=cmd_decide)
    s = sub.add_parser("rewrite"); s.add_argument("run"); s.set_defaults(fn=cmd_rewrite)
    s = sub.add_parser("sign"); s.add_argument("run"); s.add_argument("--releaser", required=True); s.add_argument("--meaning", default="Authorised for release"); s.set_defaults(fn=cmd_sign)
    s = sub.add_parser("record"); s.add_argument("run"); s.add_argument("--html", action="store_true"); s.set_defaults(fn=cmd_record)
    s = sub.add_parser("artefacts"); s.add_argument("run"); s.set_defaults(fn=cmd_artefacts)
    s = sub.add_parser("purge"); s.add_argument("run"); s.add_argument("--reason", default="file does not proceed"); s.set_defaults(fn=cmd_purge)
    s = sub.add_parser("register"); s.add_argument("run", nargs="?"); s.add_argument("--verify", action="store_true"); s.set_defaults(fn=cmd_register)
    s = sub.add_parser("list"); s.set_defaults(fn=cmd_list)
    s = sub.add_parser("schema"); s.set_defaults(fn=cmd_schema)
    s = sub.add_parser("serve"); s.add_argument("--port", type=int, default=8765); s.set_defaults(fn=cmd_serve)
    a = p.parse_args(argv)
    try:
        a.fn(a)
    except (GuardRefusal, Aborted, RequestError) as e:
        sys.exit(f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
