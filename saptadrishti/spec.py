"""The sealed method: lenses, charters, tiers, the Precedence Canon, the method hash.

Reconstructed from the SaptaDrishti pack (SD-CPK-1.2), the 2AI deck and the
run records (Run 2026-0912-C, SD-RUN-2026-0921-B). Everything in this module
feeds the method hash (invariant I7): change a word here and every later run
records a different method fingerprint.
"""

from __future__ import annotations

import hashlib
import json

SPEC_VERSION = "2.6-proto"
MAX_CYCLES = 2  # I4: at most two corrective cycles per version

# ---------------------------------------------------------------- lenses ---
# Core definitions (pack slides 10-11) and the question each lens asks
# (2AI deck slides 14-15). Order is a display order only; the audit is
# order-invariant because every lens reads the same frozen text in isolation.
LENSES: dict[str, dict] = {
    "prudence": {
        "sanskrit": "Viveka",
        "name": "Prudence",
        "question": "What could go wrong for the person relying on this?",
        "charter": (
            "What must not be said, and what must not be missed. Guard confidences, "
            "open doors and the institution's tomorrow. Flag irrecoverable language "
            "(ultimatums, closed doors). Ask whether the text would survive a front "
            "page, a courtroom, the counterparty. Surface the risk that matters most "
            "to the reader who will rely on the document."
        ),
    },
    "veracity": {
        "sanskrit": "Vāstava",
        "name": "Veracity",
        "question": "Is each claim borne out by the document itself?",
        "charter": (
            "What must be impeccable. Every fact, date, number and status must tie to "
            "the record. No compression that flatters: 'discussed' never becomes "
            "'agreed', a projection is never dressed as fact. Check arithmetic, dates "
            "and internal agreement. Contemporary public facts are verified at the "
            "freeze or reported as unverified."
        ),
    },
    "architecture": {
        "sanskrit": "Vinyāsa",
        "name": "Architecture",
        "question": "Do the parts, dates and cross-references agree?",
        "charter": (
            "Economy and sequence. Structure serves the reader's decision, not the "
            "drafter's process. Say a thing once; every annexure earns its place. One "
            "entity, one name. Check completeness of the document as supplied (pages, "
            "signatory, cropped or illegible values) and whether its parts are "
            "consistent with each other."
        ),
    },
    "positioning": {
        "sanskrit": "Vyūha",
        "name": "Positioning",
        "question": "Does the document support the standing it claims?",
        "charter": (
            "How asks and claims are placed. Every ask is an opened door, never a "
            "pressure; the ask is visible, neither buried nor brandished. Test whether "
            "the standing the document claims for itself (complete, final, senior, "
            "agreed) is supported by what it contains."
        ),
    },
    "purpose": {
        "sanskrit": "Vivakṣā",
        "name": "Purpose",
        "question": "Does it do the job its reader needs?",
        "charter": (
            "The animating reason, on its face. A stranger should know within a page "
            "why this exists. Judge fitness of the document for its stated audience "
            "and mandate: what it evidences, and what it omits that the reader needs."
        ),
    },
    "detachment": {
        "sanskrit": "Vairāgya",
        "name": "Detachment",
        "question": "Is the reading swayed by a famous or awkward name?",
        "charter": (
            "The energy of the text, and bias control on the reading itself. Resist "
            "halo and taint by association with equal force. Remove the grasping "
            "sentence, the overjustification, the inflated courtesy. Name each halo "
            "that could sway a reader and state the residue that remains without it."
        ),
    },
    "stewardship": {
        "sanskrit": "Vinaya",
        "name": "Stewardship",
        "question": "Is it fair to the person described, and careful with what it reveals?",
        "charter": (
            "Service before self. Every person named, adversaries included, is left "
            "their dignity; no sentence exists only to wound. Handle personal data, "
            "identifiers, retention and disclosure with care. Note who should hear "
            "sensitive findings, and how."
        ),
    },
}

# ------------------------------------------------------- editions/profiles ---
# The freeze record carries an "Edition · Profile" row. Observed values:
#   "SD Talent edition"                              (Run 2026-0912-C, CV)
#   "core edition, clinical case-history format"     (SD-RUN-2026-0921-B)
# The films add credit files and legal instruments.
PROFILES: dict[str, dict] = {
    "general": {
        "edition": "core",
        "label": "Core edition · general document",
        "default_audience": "the named recipient of the document",
        "tuning": {},
    },
    "cv": {
        "edition": "talent",
        "label": "SD Talent edition · candidate pack",
        "default_audience": "a hiring panel or nomination committee",
        "tuning": {
            # pack slide 24
            "prudence": "Risk and diligence signals: tenures, gaps, associations, and claims that would matter in a governance-sensitive appointment.",
            "veracity": "Internal consistency and verifiability: dates, arithmetic, undated roles, unverifiable superlatives, tense drift, currency of the document against the as-of date.",
            "architecture": "The document as a construction: structure and finish, and what its craft says relative to its claims. Proofread line by line as rendered: a missing space after a full stop or around a parenthesis, a hyphen standing in for a dash, number or agreement slips, repeated words, stray spaces before punctuation, inconsistent date formats. Proof candidates flagged mechanically at freeze are listed for you; check each against the line and report only the genuine ones. Name every genuine defect; one finding may list several, quoting the first. Spacing quarantined as an extraction artifact at freeze is not a defect.",
            "positioning": "The career as strategy: trajectory, transitions, timing, and what the profile is built toward. If a requisition is given, read against it. Read the tenure pattern (how long each role lasted, and whether it stabilises) and the staff-versus-line character of the roles against the self-description. Read timing: when the document was authored (freeze-record metadata) relative to the start of the current role, and what that implies about present motivation; frame it as a probe, never as an inference about the person.",
            "purpose": "Fitness of the instrument for its audience and mandate: what it evidences, and what it omits.",
            "detachment": "Bias control on the reading itself: halo and taint by association resisted with equal force. Apply the familiarity-bias guard for any standing disclosure.",
            "stewardship": "Handling of the person behind the paper: identifiers, protected data (photo, DOB, sex, family), retention, purge, dignity. Also buried strengths the reader should not miss.",
        },
        "probes": True,
        "tier_anchors": [
            "material: a current or 'Present' role, or the document as a whole, more than 12 months past the document's authored date at the as-of date, so the record cannot show the candidate's present position",
            "material: a cluster of outcome claims inside a standing disclosure, which must be adjudicated first-hand by the Owner before anyone relies on it",
            "material: an adverse event attributed to a firm during or around the candidate's tenure there (regulatory charges, sanctions, fraud, a collapse the candidate is not credited with resolving) that would decide a governance-sensitive appointment",
            "not adverse in itself: a restructuring, turnaround or rescue the candidate is credited with helping resolve; read it as an outcome claim (and, inside a standing disclosure, reserve it to the Owner with the rest of that cluster)",
            "corrective: a true fact imported beyond its scope, such as a later corporate outcome presented inside an earlier role, or an aggregate that conflates funds stewarded with capital raised",
            "corrective: a scale claim extraordinary for the stated title or tenure, needing referee verification",
            "corrective: a senior role missing a start or end date, or tense drift that leaves a role's status unclear",
            "corrective: genuine surface defects in the rendered text; never spacing already quarantined as extraction artifacts at freeze",
            "moderate: an unexplained gap; a tenure-pattern or positioning observation; round, unverifiable programme figures; a timing signal on present motivation",
            "advisory: presentation or context only",
        ],
    },
    "clinical": {
        "edition": "core",
        "label": "Core edition · clinical case-history format",
        "default_audience": "the next treating clinician",
        "tuning": {
            "prudence": "A consequential finding carried in the investigations and then dropped from diagnosis, references, advice or follow-up.",
            "veracity": "Stated causes and labels tested against values printed in the same document; improbable values; labels contradicted by the record.",
            "architecture": "Monitoring timed to the wrong risk; medication lists reconciled (hospital vs discharge, printed vs handwritten); completeness (pages, signatory, cropped digits).",
            "positioning": "A summary that claims completeness or a normal status the contents do not support.",
            "purpose": "Does the document lead the next clinician to the right door?",
            "detachment": "The standing of the institution lends no weight; gaps lend no presumption of poor care.",
            "stewardship": "Whether the patient may not have been told; disclosure is for clinicians, in person. Output is suggestions to clinicians, never advice to the patient.",
        },
        "disclaimer": "Compiled with AI assistance from the reports supplied. Not issued by any hospital and not a medical opinion. Points are suggestions to clinicians, not advice to the patient.",
    },
    "credit": {
        "edition": "core",
        "label": "Core edition · credit file",
        "default_audience": "a lender pricing the borrower",
        "tuning": {
            "veracity": "Balances, statuses and dates that do not reconcile account by account.",
            "architecture": "One borrower, one identity: names, addresses and identifiers consistent across accounts; data gaps on the largest exposures.",
            "stewardship": "An honest borrower is not marked down for errors that are not theirs.",
        },
        "disclaimer": "Findings are offered to the lender and are not a credit decision.",
    },
    "legal": {
        "edition": "core",
        "label": "Core edition · legal instrument",
        "default_audience": "the party about to sign or rely on the instrument",
        "tuning": {
            "prudence": "Protections absent (warranties, indemnities, conditions precedent); terms referenced but not seen.",
            "veracity": "Figures stated (price, number of shares) against what they imply (stake percentage, ranking) where the instrument is silent.",
            "positioning": "Where the instrument places each party: ranking, options held by others, what binds and when.",
        },
        "disclaimer": "The reading examines the document and is not legal advice.",
    },
}

# ----------------------------------------------------------------- tiers ---
# Pack slide 15 uses Blocking / Material / Minor; the run records use
# Material / Corrective / Moderate (observations) / Advisory. Unified here.
TIERS: dict[str, dict] = {
    "blocking": {"prefix": "B", "rank": 5, "waivable": False,
                 "meaning": "Release impossible until removed. Cannot be waived by anyone."},
    "material": {"prefix": "M", "rank": 4, "waivable": True,
                 "meaning": "Decides the file or the reader's decision; must be adjudicated."},
    "corrective": {"prefix": "C", "rank": 3, "waivable": True,
                   "meaning": "A defect to correct or clarify before reliance."},
    "moderate": {"prefix": "O", "rank": 2, "waivable": True,
                 "meaning": "An observation the reader should weigh."},
    "advisory": {"prefix": "A", "rank": 1, "waivable": True,
                 "meaning": "Presentation or context only."},
}

EVIDENCE_STATES = ["present", "absent", "unreadable"]

# Remedy classes seen in the dispositions column of the run records.
REMEDY_CLASSES = [
    "refresh_required",      # "Refreshed CV ... before candidate adjudication"
    "reserved_to_owner",     # "Reserved to Owner; first-hand adjudication becomes the finding"
    "seek_clarification",    # "Seek clarification" / "Dates ... to be supplied"
    "referee_verify",        # "Referee-verify the management scope"
    "probe",                 # "Probe 1 - decides the file"
    "restate",               # "Read as context, not achievement" / projection stated as projection
    "omit",                  # Canon II: truth-vs-prudence resolves by omission
    "add",                   # "One sentence added, commending interim service continuity"
    "cosmetic",              # "Cosmetic; note for any onward copy"
    "clinician_consider",    # clinical: "suggestion to clinicians"
    "none",
]

# ------------------------------------------------------ Precedence Canon ---
CANON: list[dict] = [
    {"rule": "I", "name": "Truth is absolute",
     "text": "Nothing false or overstated is ever written; no Standard may license a distortion."},
    {"rule": "II", "name": "Prudence governs disclosure",
     "text": "What is true may be withheld; what is said must be true. Truth-vs-prudence resolves by omission, never distortion."},
    {"rule": "III", "name": "Stewardship arbitrates the spirit",
     "text": "Where Purpose and Detachment pull against each other or against craft, Stewardship decides."},
    {"rule": "IV", "name": "Craft serves",
     "text": "Architecture and Positioning adapt to Rules I-III, never the reverse."},
]

# ------------------------------------------------ conformance guard text ---
# Certificate language that claims compliance rather than alignment (FR-11).
FORBIDDEN_CERT_PATTERNS = [
    r"\bcompliant with\b", r"\bcertif(?:y|ies|ied) (?:that )?.*compl", r"\bin compliance with\b",
    r"\bcertified under\b", r"\bconfers? compliance\b",
]
# Output boundary (I5): no run output speaks of the maker, dedication or mark.
FORBIDDEN_PROVENANCE_PATTERNS = [
    r"\bNAMO\b", r"\bdedicat(?:ed|ion)\b", r"\bfounders?'? (?:economic )?interest\b",
]


GENERAL_TIER_ANCHORS = [
    "blocking: a false statement of fact, or a breach of confidence, in text about to be released",
    "material: an omission or contradiction that would change the reader's decision",
]


def tier_anchors(profile: str) -> list[str]:
    return GENERAL_TIER_ANCHORS + PROFILES[profile].get("tier_anchors", [])


def charter_for(lens: str, profile: str) -> str:
    base = LENSES[lens]["charter"]
    tuned = PROFILES[profile]["tuning"].get(lens)
    return base if not tuned else f"{base}\n\nFor this profile: {tuned}"


def method_payload() -> dict:
    return {
        "spec_version": SPEC_VERSION,
        "max_cycles": MAX_CYCLES,
        "lenses": LENSES,
        "profiles": PROFILES,
        "tiers": TIERS,
        "canon": CANON,
        "general_tier_anchors": GENERAL_TIER_ANCHORS,
        "remedy_classes": REMEDY_CLASSES,
        "evidence_states": EVIDENCE_STATES,
    }


def method_hash() -> str:
    """I7: fingerprint of specification, editions and sealed charters."""
    blob = json.dumps(method_payload(), sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(blob).hexdigest()
