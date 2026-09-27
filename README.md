# SaptaDrishti review gate: working prototype

A prototype of the SaptaDrishti protocol: a document is frozen, read
through seven isolated lenses, and reconciled under the Precedence Canon.
It then passes two human gates (the Owner accepts, the Releaser signs). Every
step is written to an append-only register.

- **Reverse-engineered input parameters:** [`docs/INPUT_PARAMETERS.md`](docs/INPUT_PARAMETERS.md)
- **Comparables and monetization research:** [`docs/MARKET_RESEARCH.md`](docs/MARKET_RESEARCH.md)

## Quick start

```bash
pip install -e .                      # anthropic, pypdf, cryptography
export ANTHROPIC_API_KEY=...          # or `ant auth login`

# Web app (Start / Pause / Resume / Stop, then Accept and Sign)
sd serve                              # http://127.0.0.1:8765

# Or from the command line
sd schema                             # the run-request JSON schema
sd run examples/requests/candidate_cv.json
sd decide 2026-0927-A --owner "Search Partner" --all accept --note "agreed"
sd sign   2026-0927-A --releaser "Managing Partner"
sd record 2026-0927-A --html          # the Run Record
sd artefacts 2026-0927-A              # the five Artefacts as JSON
sd register --verify                  # hash-chain check
sd purge 2026-0927-A                  # destroy the run key; the event survives
```

Without an API key, add `--engine offline` (or pick "Offline heuristics" in
the web app). This runs the protocol mechanics on deterministic pattern
checks. It demonstrates freezing, gating, the register and purge; it does
**not** demonstrate reading quality.

## A run request

```json
{
  "pack": ["../packs/candidate_cv.txt"],
  "profile": "cv",
  "subject": "Curriculum vitae of a senior clinician",
  "owner": {"name": "Search Partner"},
  "releaser": {"name": "Managing Partner"},
  "audience": "the nomination committee",
  "requisition": "Chief Medical Officer, 400-bed tertiary hospital",
  "as_of": "2026-09-27",
  "standing_disclosures": [{"relationship": "The Owner worked with the candidate 2019-2021",
                            "claims_affected": ["City Heart Institute"]}],
  "contains_personal_data": true
}
```

Profiles: `general`, `cv` (Talent edition), `clinical`, `credit`, `legal`.
The full parameter list, with the evidence behind each field, is in
[`docs/INPUT_PARAMETERS.md`](docs/INPUT_PARAMETERS.md).

## How it maps to the protocol

| Protocol | Code |
|---|---|
| Phase 0 Freeze: SHA-256, version record, model identity, method hash | `freeze.py`, `Run.open_and_freeze` |
| Phase 1 Parallel audit: 7 isolated calls, citation-gated findings | `engine.py`, `Run.audit`, `Run._gate_citations` |
| Phase 2 Reconciliation under the Canon, every lens finding accounted for | `Run.reconcile` |
| Owner gate: every finding decided; Blocking findings can't be waived | `Run.decide` |
| Phase 3 Integrated rewrite (proposed; applied only by re-freezing) | `Run.integrated_rewrite` |
| Phase 4 Re-pass: cycle 2 honours prior adjudications; two-cycle cap | `prior_run_id`, `Run._inherit_prior` |
| Releaser gate and Release Certificate (alignment language only) | `Run.sign`, `certificate_check` |
| I6 register: append-only, hash-chained | `register.py` |
| Purge by key destruction (per-run encryption at rest) | `vault.py`, `Run.purge` |
| Sealed method: charters, tiers, Canon, method hash | `spec.py` |

With the `claude` engine, each lens is a separate Claude API call (`claude-opus-5`,
adaptive thinking, JSON-schema output, server-side refusal fallback). The
frozen text sits in a cached prefix shared by all seven calls, so the document
is billed at full price once and read seven times. Scanned PDFs are transcribed
once at freeze, and that transcript is what gets frozen and cited.

## Tests

```bash
pytest -q        # 32 checks: refusals, invariants, citation gate, register, purge, engine request shape
```

## Limits of this prototype

- The charters are reconstructed from published descriptions, not the sealed
  originals, so the method hash does not match `13a400f4a409`.
- Lenses share one model, so their errors may correlate. They are isolated, not independent.
- The web app is single-user and binds to localhost only. There is no auth, SSO or tenancy.
- Regeneration is not bit-identical. The register, not a re-run, is the record.
