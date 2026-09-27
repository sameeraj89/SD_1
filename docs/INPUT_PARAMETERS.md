# SaptaDrishti: the reverse-engineered input contract

Worked backwards from the materials: the pack deck (SD-CPK-1.2), the 2AI
deck, two run records (Run 2026-0912-C, a CV under the Talent edition, and
SD-RUN-2026-0921-B, a clinical discharge summary under the core edition) and
the three short films (a CV, a credit file, a medical record, a legal
instrument).

Each parameter below is something a run record *prints* or a guard *refuses
on*. If a record shows it, the run had to be given it or had to compute it.

## 1. What the run is given (inputs)

| Parameter | Type / values | Required | Where the evidence is |
|---|---|---|---|
| `pack` | one or more files (PDF, DOCX, TXT; scanned PDFs are transcribed at freeze) | yes | Freeze record: *"<candidate>_CV_.pdf — 3 pages, A4, Microsoft Word origin"*; *"Adobe_Scan_…pdf; six scanned pages … Read as rendered images"* |
| `profile` | `general` · `cv` · `clinical` · `credit` · `legal` | yes (default `general`) | Freeze row *"Edition · Profile"*: *"SD Talent edition"* / *"core edition, clinical case-history format"*; films add credit files and legal instruments |
| `subject` | text | no | Record header: *"Subject: Curriculum Vitae — <candidate> (pack of <date>)"* |
| `owner` | `{name, role}` | **yes** | "The two human moments are constitutive"; *"Reserved to Owner; first-hand adjudication becomes the finding"* |
| `releaser` | `{name, role}` (must differ from the Owner) | needed to release | Phase 4: *"on a clean pass the Releaser signs"*; Release Certificate carries *"the two bound signatures"* |
| `audience` | text; profile default if blank | no | Version Record lists *"owner, audience"*; Purpose lens: *"Fitness … for its audience"*; clinical: *"the next clinician"* |
| `purpose` | text | no | Vivakṣā: *"A stranger should know within a page why this exists"* |
| `requisition` | text (the role or mandate) | no | *"No requisition was stated for this run. If the record is to serve a specific role, the Positioning lens re-runs against that context"* |
| `as_of` | date | defaults to today | Currency findings are measured against it: *"File authored 10 August 2025; 'Sep-24 – Present' is evidenced only to that date … thirteen months since authoring are unevidenced"* |
| `standing_disclosures[]` | `{relationship, claims_affected[]}` | no | Section C *"Standing disclosure … positions proximate to the Owner … the run refers those claims to the Owner … familiarity-bias guard applies in both directions"* |
| `external_inputs[]` | text | no | Version Record: *"record owner, audience and inputs"* |
| `contemporary_facts[]` + `allow_web_verification` | list + bool | no | *"<named> transaction verified against public record at freeze (Clause 4.3)"*; *"No web sources were needed or used"* |
| `contains_personal_data` | bool | default true | *"Internal record — contains candidate personal data; anonymise before any circulation"* |
| `purge_if_not_proceeding`, `retention_days` | bool, int (default 3650) | no | *"purged if the file does not proceed"*; *"A 10-year floor"* |
| `distribution`, `route`, `contact` | text; profile defaults if blank | no | Added after the case-history run found a record about possibly undisclosed findings with *"no recipient or handling line, no route, no retention note, and no named compiler"*; printed in the record's release section |
| `cycle` | 1 or 2 | default 1 | *"Cycle 1 verdict: corrective … Cycle 2 is reserved"*; *"At most two corrective cycles per version"* |
| `prior_run_id` | run id | when cycle = 2 | *"Cycle 2 … honouring the adjudications recorded here and reviewing deltas only"* |
| `model`, `engine`, `effort` | model id; `claude` or `offline` | defaults | *"model identity: Claude (Anthropic)"*; *"Mode: Chat-emulated run"* vs *"on the server"*; models are *"substitutable beneath the orchestration layer"* |

## 2. What the run computes at freeze (Version Record)

| Field | How |
|---|---|
| `run_id` | `YYYY-MMDD-<letter>`, one letter per run that day (as in `2026-0912-C`) |
| per-file `sha256`, pages, media type, document metadata (author, created/modified) | at freeze; re-verified before every phase (I1) |
| `text_layer` + transcription note | scanned pages are read as images once, and that transcript is what gets frozen |
| `method_hash` | SHA-256 over spec version, lens charters, profiles, tiers, Canon (I7). The record prints *"sealed Method Hash 13a400f4a409"* |
| `spec_version` | `v2.3`, `v2.4` in the records; `2.4-proto` here |
| `model_identity` | requested model and the model that actually served (I7) |

## 3. What the run returns (outputs)

**Each finding** (Exhibit 2/3 and B-1 in the records) has:

| Field | Values |
|---|---|
| `id` | tier prefix plus number: `B1`, `M1`, `C1`, `O1` (moderate observation), `A1` |
| `tier` | `blocking` · `material` · `corrective` · `moderate` · `advisory` |
| `lenses` | one or more, e.g. *"Prudence · Veracity"* |
| `finding` | the defect, stated plainly |
| `quote` + `location` | the verbatim line it rests on (`D1 p2 L14`). If the quote isn't in the frozen text, the finding is rejected |
| `evidence_state` | `present` · `absent` (*"No result in the reports supplied"*) · `unreadable` (*"[1]28\*"* cropped digit) |
| `remedy_class` + `disposition` | e.g. refresh_required, reserved_to_owner, seek_clarification, referee_verify, probe, restate, omit, add, cosmetic, clinician_consider |
| `probe` | the question a person can ask to resolve it (*"Probe 1 — decides the file"*) |

**Whole-run outputs:** a reading for each lens; the Reconciliation Log (each
conflict and the Canon rule applied); the Detachment read (*"Strip the three
halos … a genuine residue remains"*); the verdict (`clean` · `corrective` ·
`blocking`); the matters reserved to the Owner; the Decision Record; the
Release Certificate; and the register extract.

## 4. Fixed method constants (the sealed asset)

- **Seven lenses:** Prudence (Viveka), Veracity (Vāstava), Architecture (Vinyāsa),
  Positioning (Vyūha), Purpose (Vivakṣā), Detachment (Vairāgya), Stewardship
  (Vinaya). Each has a core charter plus a tuning for each profile. The Talent
  tunings come from pack slide 24; the clinical ones from the 2AI deck, slides 14–15.
- **Precedence Canon:** I Truth is absolute › II Prudence governs disclosure
  (by omission, never distortion) › III Stewardship arbitrates the spirit ›
  IV Craft serves.
- **Two-cycle cap. Two human gates.** No waiver of a Blocking finding.
  Certificates may claim alignment only, never compliance or certification.
  Run output says nothing about the protocol's maker.

## 5. What the materials do not settle (assumptions made here)

- **Tier vocabulary.** The pack uses Blocking/Material/Minor. The records use
  Material/Corrective/Moderate/Advisory. They are unified here as five tiers.
- **When a cycle 2 is required.** Here it is required for (a) any Blocking
  finding, and (b) a `general` document with accepted substantive remedies.
  For `cv`/`clinical`/`credit`/`legal`, the *record* is what gets released,
  so a corrective verdict can be released once every finding is decided.
- **Sealed charters.** The real charter text is sealed server-side. The
  charters here are reconstructed from the published descriptions, so they
  will not reproduce method hash `13a400f4a409`.
- **Clause numbers** (4.3, 4.13–4.14, 4.18) point to a specification document
  that wasn't supplied.
