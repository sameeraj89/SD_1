"""Per-run encryption at rest; purge by key destruction (pack slide 27).

Run content (frozen text, lens outputs) is stored encrypted under a key that
belongs to that run alone. Purging destroys the key: the register keeps the
fact of the purge, the content becomes unrecoverable.
"""

from __future__ import annotations

import json
import os

from cryptography.fernet import Fernet


class Vault:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(os.path.join(root, "keys"), exist_ok=True)
        os.makedirs(os.path.join(root, "content"), exist_ok=True)

    def _key_path(self, run_id: str) -> str:
        return os.path.join(self.root, "keys", f"{run_id}.key")

    def _content_path(self, run_id: str, name: str) -> str:
        return os.path.join(self.root, "content", f"{run_id}.{name}.enc")

    def _fernet(self, run_id: str, create: bool = False) -> Fernet:
        p = self._key_path(run_id)
        if not os.path.exists(p):
            if not create:
                raise KeyError(f"no key for run {run_id} (purged or never opened)")
            with open(p, "wb") as f:
                f.write(Fernet.generate_key())
            os.chmod(p, 0o600)
        with open(p, "rb") as f:
            return Fernet(f.read())

    def put(self, run_id: str, name: str, obj) -> None:
        token = self._fernet(run_id, create=True).encrypt(json.dumps(obj, ensure_ascii=False).encode())
        with open(self._content_path(run_id, name), "wb") as f:
            f.write(token)

    def get(self, run_id: str, name: str):
        with open(self._content_path(run_id, name), "rb") as f:
            return json.loads(self._fernet(run_id).decrypt(f.read()))

    def has_key(self, run_id: str) -> bool:
        return os.path.exists(self._key_path(run_id))

    def purge(self, run_id: str) -> None:
        p = self._key_path(run_id)
        if os.path.exists(p):
            size = os.path.getsize(p)
            with open(p, "r+b") as f:
                f.write(os.urandom(size))
            os.remove(p)
