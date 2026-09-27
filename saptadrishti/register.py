"""I6 - Single source of record: an append-only, hash-chained register.

Every run, finding, decision, release and purge is an event. Each event
carries the hash of the previous one, so any edit or deletion of history is
detectable by `verify_chain()`.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import threading

GENESIS = "0" * 64


class RegisterError(RuntimeError):
    pass


class Register:
    def __init__(self, path: str):
        self.path = path
        self._lock = threading.Lock()
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        if not os.path.exists(path):
            open(path, "a").close()

    def _events(self) -> list[dict]:
        with open(self.path, encoding="utf-8") as f:
            return [json.loads(line) for line in f if line.strip()]

    def events(self, run_id: str | None = None) -> list[dict]:
        ev = self._events()
        return [e for e in ev if run_id is None or e.get("run_id") == run_id]

    def append(self, run_id: str, kind: str, data: dict) -> dict:
        with self._lock:
            ev = self._events()
            prev = ev[-1]["hash"] if ev else GENESIS
            body = {
                "seq": len(ev) + 1,
                "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "run_id": run_id,
                "kind": kind,
                "data": data,
                "prev": prev,
            }
            body["hash"] = hashlib.sha256(
                json.dumps(body, sort_keys=True, ensure_ascii=False).encode()
            ).hexdigest()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(body, ensure_ascii=False) + "\n")
            return body

    def verify_chain(self) -> bool:
        prev = GENESIS
        for i, e in enumerate(self._events(), 1):
            h = e.get("hash")
            body = {k: v for k, v in e.items() if k != "hash"}
            if e.get("seq") != i or e.get("prev") != prev:
                raise RegisterError(f"register broken at seq {i}")
            if hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False).encode()).hexdigest() != h:
                raise RegisterError(f"register tampered at seq {i}")
            prev = h
        return True

    def next_run_id(self, as_of: str) -> str:
        """Run IDs as seen in the records: 2026-0912-C (date + letter of the day)."""
        y, m, d = as_of[:10].split("-")
        stem = f"{y}-{m}{d}-"
        n = sum(1 for e in self._events() if e["kind"] == "run.opened" and e["run_id"].startswith(stem))
        return stem + chr(ord("A") + n % 26) + ("" if n < 26 else str(n // 26))
