"""Local web app: four verbs (Start, Pause, Resume, Stop), two moments (Accept, Sign).

Standard library only. Runs inside the user's own environment; pack files
never leave it except for the model calls the chosen engine makes.
"""

from __future__ import annotations

import base64
import json
import os
import re
import threading
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import report, spec
from .protocol import Aborted, GuardRefusal, Run, list_runs
from .request import REQUEST_JSON_SCHEMA, RequestError, RunRequest

STATIC = os.path.join(os.path.dirname(__file__), "static")


class App:
    def __init__(self, workdir: str):
        self.workdir = os.path.abspath(workdir)
        self.live: dict[str, Run] = {}
        self.errors: dict[str, str] = {}
        os.makedirs(os.path.join(self.workdir, "uploads"), exist_ok=True)

    def run(self, rid: str) -> Run:
        return self.live.get(rid) or Run.load(self.workdir, rid)

    def start(self, body: dict) -> dict:
        files = body.pop("files", [])
        if not files:
            raise RequestError("upload at least one document")
        paths = []
        for f in files:
            name = re.sub(r"[^\w.\-]+", "_", os.path.basename(f["name"]))[:120]
            data = base64.b64decode(f["data"])
            p = os.path.join(self.workdir, "uploads", f"{os.urandom(4).hex()}_{name}")
            with open(p, "wb") as out:
                out.write(data)
            paths.append(p)
        body["pack"] = paths
        req = RunRequest.from_dict(body)
        run = Run(self.workdir)
        rid = run.open_and_freeze(req)
        run.state["uploads"] = paths
        run._save()
        self.live[rid] = run

        def work():
            try:
                run.audit()
                if run.state["status"] == "audited":
                    run.reconcile()
            except Exception as e:  # surfaced to the UI
                self.errors[rid] = f"{type(e).__name__}: {e}"
                traceback.print_exc()

        threading.Thread(target=work, daemon=True).start()
        return {"run_id": rid}

    def view(self, rid: str) -> dict:
        run = self.run(rid)
        s = run.state
        ev = run.register.events(rid)
        out = {k: v for k, v in s.items() if k not in ("frozen_text",)}
        out["error"] = self.errors.get(rid)
        out["lenses_done"] = sorted(s.get("lens_outputs", {}))
        if s.get("verdict"):
            out["verdict_line"] = report.verdict_line(s)
        if s.get("status") not in ("purged", "opened", "frozen", "auditing"):
            out["record_md"] = report.run_record_markdown(s, ev)
        out["register"] = ev
        return out

    def purge(self, rid: str) -> dict:
        run = self.run(rid)
        for p in run.state.get("uploads", []):
            if os.path.exists(p):
                os.remove(p)
        run.purge()
        self.live.pop(rid, None)
        return {"status": "purged"}


def make_handler(app: App):
    class H(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def _send(self, code: int, obj, ctype="application/json"):
            data = obj.encode() if isinstance(obj, str) else json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype + "; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}")

        def do_GET(self):
            try:
                p = self.path.split("?")[0]
                if p in ("/", "/index.html"):
                    return self._send(200, open(os.path.join(STATIC, "index.html"), encoding="utf-8").read(), "text/html")
                if p == "/api/meta":
                    return self._send(200, {
                        "spec_version": spec.SPEC_VERSION, "method_hash": spec.method_hash(),
                        "profiles": {k: {"label": v["label"], "default_audience": v["default_audience"]}
                                     for k, v in spec.PROFILES.items()},
                        "lenses": {k: {"name": v["name"], "sanskrit": v["sanskrit"], "question": v["question"]}
                                   for k, v in spec.LENSES.items()},
                        "tiers": spec.TIERS, "canon": spec.CANON, "schema": REQUEST_JSON_SCHEMA,
                        "api_key_present": bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN")),
                    })
                if p == "/api/runs":
                    return self._send(200, list_runs(app.workdir))
                m = re.fullmatch(r"/api/runs/([\w-]+)(/record\.html)?", p)
                if m:
                    if m.group(2):
                        run = app.run(m.group(1))
                        return self._send(200, report.run_record_html(run.state, run.register.events(run.run_id)), "text/html")
                    return self._send(200, app.view(m.group(1)))
                self._send(404, {"error": "not found"})
            except (GuardRefusal, Aborted, RequestError) as e:
                self._send(409, {"error": str(e)})
            except Exception as e:
                traceback.print_exc()
                self._send(500, {"error": f"{type(e).__name__}: {e}"})

        def do_POST(self):
            try:
                p = self.path.split("?")[0]
                if p == "/api/runs":
                    return self._send(200, app.start(self._body()))
                m = re.fullmatch(r"/api/runs/([\w-]+)/(\w+)", p)
                if not m:
                    return self._send(404, {"error": "not found"})
                rid, verb = m.groups()
                b = self._body()
                if verb in ("pause", "resume", "stop"):
                    run = app.live.get(rid)
                    if not run:
                        raise GuardRefusal("run is not active in this session")
                    getattr(run, verb)()
                    if verb == "resume" and run.state["status"] == "paused":
                        threading.Thread(target=lambda: (run.audit(), run.state["status"] == "audited" and run.reconcile()),
                                         daemon=True).start()
                    return self._send(200, {"ok": True})
                run = app.run(rid)
                if verb == "decide":
                    run.decide(b.get("owner", ""), b.get("decisions", {}))
                    return self._send(200, {"status": run.state["status"]})
                if verb == "rewrite":
                    return self._send(200, run.integrated_rewrite())
                if verb == "sign":
                    return self._send(200, run.sign(b.get("releaser", ""), b.get("meaning") or "Authorised for release"))
                if verb == "purge":
                    return self._send(200, app.purge(rid))
                self._send(404, {"error": "unknown verb"})
            except (GuardRefusal, Aborted, RequestError) as e:
                self._send(409, {"error": str(e)})
            except Exception as e:
                traceback.print_exc()
                self._send(500, {"error": f"{type(e).__name__}: {e}"})

    return H


def serve(workdir: str, port: int = 8765) -> None:
    app = App(workdir)
    srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(app))
    print(f"SaptaDrishti prototype on http://127.0.0.1:{port}  (workdir {app.workdir})")
    srv.serve_forever()
