"""The run request: the input parameters a SaptaDrishti run takes.

Each field is traced to where it shows up in the source material; see
docs/INPUT_PARAMETERS.md for the full evidence table.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import asdict, dataclass, field
from typing import Optional

from . import spec


class RequestError(ValueError):
    pass


@dataclass
class Person:
    name: str
    role: str = ""


@dataclass
class Disclosure:
    """A standing relationship between the Owner and the subject (Run 2026-0912-C §C)."""
    relationship: str
    claims_affected: list[str] = field(default_factory=list)


@dataclass
class RunRequest:
    # --- the pack -----------------------------------------------------------
    pack: list[str]                               # file paths; frozen as received
    profile: str = "general"                      # general | cv | clinical | credit | legal
    subject: str = ""                             # "Curriculum Vitae - <name> (pack of 10 August 2025)"

    # --- the two human moments ------------------------------------------------
    owner: Optional[Person] = None                # accepts findings / integrated rewrite
    releaser: Optional[Person] = None             # signs release

    # --- the reading context --------------------------------------------------
    audience: str = ""                            # who will rely on the page
    purpose: str = ""                             # why the document exists / the mandate
    requisition: str = ""                         # talent: the role; absent -> general terms
    as_of: str = ""                               # freeze date; currency is judged against it
    standing_disclosures: list[Disclosure] = field(default_factory=list)
    external_inputs: list[str] = field(default_factory=list)
    contemporary_facts: list[str] = field(default_factory=list)  # to verify at freeze
    allow_web_verification: bool = False          # "No web sources were needed or used"

    # --- data handling --------------------------------------------------------
    contains_personal_data: bool = True
    purge_if_not_proceeding: bool = True
    retention_days: int = 3650                    # "A 10-year floor"
    distribution: str = ""                        # who may receive the record; profile default if blank
    route: str = ""                               # how it travels; profile default if blank
    contact: str = ""                             # who to ask about a reading (compiler / Owner's office)

    # --- run control ----------------------------------------------------------
    cycle: int = 1
    prior_run_id: str = ""                        # cycle 2: honour adjudications, review deltas
    model: str = "claude-opus-5"
    engine: str = "claude"                        # claude | offline
    effort: str = "high"

    @classmethod
    def from_dict(cls, d: dict) -> "RunRequest":
        d = dict(d)
        if d.get("owner") and isinstance(d["owner"], dict):
            d["owner"] = Person(**d["owner"])
        if d.get("releaser") and isinstance(d["releaser"], dict):
            d["releaser"] = Person(**d["releaser"])
        d["standing_disclosures"] = [
            x if isinstance(x, Disclosure) else Disclosure(**x)
            for x in d.get("standing_disclosures", [])
        ]
        known = set(cls.__dataclass_fields__)
        unknown = set(d) - known
        if unknown:
            raise RequestError(f"unknown request fields: {sorted(unknown)}")
        req = cls(**d)
        req.validate()
        return req

    def validate(self) -> None:
        if not self.pack:
            raise RequestError("pack must contain at least one document")
        if self.profile not in spec.PROFILES:
            raise RequestError(f"profile must be one of {sorted(spec.PROFILES)}")
        if not self.owner or not self.owner.name:
            raise RequestError("an Owner must be named: the first human moment is constitutive")
        if self.cycle not in range(1, spec.MAX_CYCLES + 1):
            raise RequestError(f"cycle must be 1..{spec.MAX_CYCLES} (two-cycle cap, I4)")
        if self.cycle > 1 and not self.prior_run_id:
            raise RequestError("cycle 2 requires prior_run_id")
        if self.engine not in ("claude", "offline", "replay"):
            raise RequestError("engine must be claude, offline or replay")
        if not self.as_of:
            self.as_of = dt.date.today().isoformat()
        if not self.audience:
            self.audience = spec.PROFILES[self.profile]["default_audience"]

    @property
    def edition(self) -> str:
        return spec.PROFILES[self.profile]["edition"]

    def to_dict(self) -> dict:
        return asdict(self)


REQUEST_JSON_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "SaptaDrishti run request",
    "type": "object",
    "required": ["pack", "owner"],
    "properties": {
        "pack": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "profile": {"enum": sorted(spec.PROFILES)},
        "subject": {"type": "string"},
        "owner": {"type": "object", "required": ["name"],
                  "properties": {"name": {"type": "string"}, "role": {"type": "string"}}},
        "releaser": {"type": "object",
                     "properties": {"name": {"type": "string"}, "role": {"type": "string"}}},
        "audience": {"type": "string"},
        "purpose": {"type": "string"},
        "requisition": {"type": "string"},
        "as_of": {"type": "string", "format": "date"},
        "standing_disclosures": {"type": "array", "items": {
            "type": "object", "required": ["relationship"],
            "properties": {"relationship": {"type": "string"},
                           "claims_affected": {"type": "array", "items": {"type": "string"}}}}},
        "external_inputs": {"type": "array", "items": {"type": "string"}},
        "contemporary_facts": {"type": "array", "items": {"type": "string"}},
        "allow_web_verification": {"type": "boolean"},
        "contains_personal_data": {"type": "boolean"},
        "purge_if_not_proceeding": {"type": "boolean"},
        "retention_days": {"type": "integer", "minimum": 1},
        "distribution": {"type": "string"},
        "route": {"type": "string"},
        "contact": {"type": "string"},
        "cycle": {"type": "integer", "minimum": 1, "maximum": spec.MAX_CYCLES},
        "prior_run_id": {"type": "string"},
        "model": {"type": "string"},
        "engine": {"enum": ["claude", "offline", "replay"]},
        "effort": {"enum": ["low", "medium", "high", "xhigh", "max"]},
    },
    "additionalProperties": False,
}
