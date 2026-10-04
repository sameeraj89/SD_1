"""Build web/ingest.html: the in-browser ingestion window.

The page runs the protocol on the viewer's own Claude plan (the artifact
`sample` capability), so it carries the sealed method as data. This script
injects that data from the Python package, so the browser edition and the
CLI read from one specification.

    python web/build_ingest.py
"""

from __future__ import annotations

import json
from pathlib import Path

from saptadrishti import engine, spec

HERE = Path(__file__).parent


def method() -> dict:
    return {
        **spec.method_payload(),
        "spec_version": spec.SPEC_VERSION + "-web",
        "default_handling": spec.DEFAULT_HANDLING,
        "forbidden_cert": spec.FORBIDDEN_CERT_PATTERNS,
        "forbidden_provenance": spec.FORBIDDEN_PROVENANCE_PATTERNS,
        "prompts": {
            "protocol": engine.PROTOCOL_SYSTEM,
            "reconcile": engine.RECONCILE_SYSTEM,
            "rewrite": engine.REWRITE_SYSTEM,
        },
    }


def build() -> Path:
    tpl = (HERE / "ingest.template.html").read_text()
    blob = json.dumps(method(), ensure_ascii=False).replace("</", "<\\/")
    out = HERE / "ingest.html"
    out.write_text(tpl.replace("/*@METHOD@*/null", blob))
    return out


if __name__ == "__main__":
    print(build())
