# Comparables and monetization (research as of 2026-09-27)

Most enterprise vendors don't publish prices. **(3P est.)** marks a figure
from a third-party aggregator or review site rather than the vendor.
**Unverified** marks anything that couldn't be confirmed. The pricing
hypotheses in §3 are untested.

## 1. Comparables

| Company | Category | Similarity to SaptaDrishti | How it makes money | Price / revenue signals | Source |
|---|---|---|---|---|---|
| Cleanlab TLM | Output verification | Flags unsupported claims by scoring model output. SD instead reviews a frozen document through seven lenses with human gates | Free tokens, then per-token; enterprise private deployment | Rates not public | https://help.cleanlab.ai/tlm/faq/ |
| Patronus AI (Lynx) | Output verification | Close to the Veracity lens alone; no Canon, gates or certificate | Pay-per-call plus enterprise | $10 / $20 per 1,000 calls; $17M Series A | https://venturebeat.com/ai/patronus-ai-launches-worlds-first-self-serve-api-to-stop-ai-hallucinations |
| Galileo | Eval / observability | Groundedness metrics, built for developers | Freemium → Pro → Enterprise | Pro ≈ $100/mo (annual) | https://galileo.ai/pricing |
| Vectara HHEM | Hallucination model | An open model draws users in; a commercial model is sold through the API | Platform subscription | Not public | https://www.vectara.com/blog/hallucination-detection-commercial-vs-open-source-a-deep-dive |
| Guardrails AI | Output validation | Validator pipeline is shaped like the lenses | Open-core; Pro sold via AWS Marketplace | Example listing $50k/12 mo (3P est.) | https://markaicode.com/pricing/guardrails-ai-pricing/ |
| Credo AI | AI governance | Same "aligned with EU AI Act / NIST / ISO" story, but governs AI systems rather than single documents | Enterprise annual licence | $30k–400k/yr (3P est.); ~$42M raised | https://co-aims.com/blog/credo-ai-review-2026-compliance-officers |
| IBM watsonx.governance | AI governance | Lineage and audit trail, like the register | Metered resource units or per-VPC licence | Essentials ≈ $0.60/RU | https://www.ibm.com/products/watsonx-governance/pricing |
| Harvey | Legal AI | Legal vertical; Harvey drafts, SD attests | Per-seat enterprise | ARR > $400M (press) | https://www.cnbc.com/2026/03/25/legal-ai-startup-harvey-raises-200-million-at-11-billion-valuation.html |
| Spellbook | Contract review in Word | Mirrors SD's Microsoft 365 delivery route | Per-seat, annual | ≈ $500/user/mo (3P est.); $50M Series B | https://www.businesswire.com/news/home/20251009110230/en/Spellbook-Raises-$50M-Series-B-to-Expand-AI-Contract-Review-Platform |
| Luminance | Contract review | Human-in-the-loop document review | Enterprise licence | Not public; 700+ orgs | https://sacra.com/c/luminance/ |
| HireVue | Hiring assessment | Bias control and audit; dropped facial analysis in 2021 | Enterprise subscription (unverified) | Published an external audit | https://fortune.com/2021/01/19/hirevue-drops-facial-monitoring-amid-a-i-algorithm-audit/ |
| Metaview | Interview notes | Evidence-grounded summaries of candidates | SaaS | $35M Series B | https://www.unleash.ai/hr-technology/news/google-ventures-leads-35-million-series-b-funding-in-metaview |
| Checkr | Background checks | Candidate-pack verification; SD Talent's natural partner or competitor | **Per report** | $29.99 / $54.99 / $89.99 per report | https://checkr.com/pricing |
| Eightfold AI | Talent intelligence | A warning case (FCRA suit, Jan 2026) | Enterprise SaaS | — | https://ogletree.com/insights-resources/blog-posts/groundbreaking-lawsuit-tests-whether-ai-hiring-tools-trigger-fcra-compliance/ |
| Iodine Software | Clinical documentation integrity | Finds clinical documentation gaps, aimed at revenue rather than integrity | Enterprise and outcome-based | Claims $1.5B/yr reimbursement uplift for clients | https://iodinesoftware.com/newsroom/iodine-software-unveils-awarecdi/ |
| Abridge | Ambient scribe | Writes the notes that SD would review | Per clinician | ≈ $2.5k/clinician/yr (3P est.) | https://sacra.com/c/abridge/ |
| Regard | Clinical decision support | The decision-support layer SD would sit beneath | Enterprise, justified by revenue uplift | $61M Series B | https://www.fiercehealthcare.com/ai-and-machine-learning/regard-picks-61m-build-out-ai-powered-clinical-insights-research-llms |
| Ocrolus | Lending documents | Credit-file integrity | Metered by page or statement | ≈ $0.50–2 per statement (3P est.) | https://addy.com/blog/ocrolus-pricing |
| Inscribe | Loan-document fraud | Like the Veracity lens applied to credit files | Per document (not public) | ~$39M raised | https://www.inscribe.ai/industries/lenders |
| Heron Data | SMB underwriting intake | Structured data lenders can act on | Not public | $16M Series A | https://www.herondata.io/blog/series-a-announcement |
| DocuSign Part 11 module | Regulated e-sign | Signatures bound to a version, with a stated reason | Add-on per seat or per envelope | $4.99/envelope (reseller) | https://www.cdw.com/product/docusign-esignature-life-sciences-fda-part-11-module-license-1-envelope/7286495 |
| MasterControl | QMS document control | Controlled release with an audit trail | Named-user, per module | ≈ $300/user/mo (3P est.) | https://www.itqlick.com/mastercontrol-quality-management-system-qms-software/pricing |
| **FICO Scores** | Method licensing | **Closest parallel to "the method is the asset"**: the bureaus compute the score and FICO takes a royalty | Royalty per score via distributors | $4.95 → ~$10 per mortgage score; Scores revenue $1.17B | https://www.sec.gov/Archives/edgar/data/814547/000081454725000026/exhibit991erq42025.htm |
| B Lab | Certification | Annual fee against its own standard | Fee tiered by client revenue | From $2,100/yr | https://usca.bcorporation.net/fees/ |
| ISO 42001 bodies | Certification | They certify; SD only aligns | Audit plus annual surveillance | $5k–25k initial (3P est.) | https://www.vanta.com/collection/iso-42001/iso-42001-certification-cost |
| Wikimedia Enterprise | Mission-owned | Paid tier run by a nonprofit | Usage-based API | FY25 $8.3M revenue | https://diff.wikimedia.org/2025/11/24/wikimedia-enterprise-financial-report-fiscal-year-2024-2025/ |
| Mozilla Corporation | Mission-owned | For-profit subsidiary of a foundation | Search royalties | $680M revenue (2024) | https://stateof.mozilla.org/pdf/Mozilla%20Fdn%202024%20-%20AuditedFinancials.pdf |
| Patagonia / Holdfast | Mission-owned | Economic interest dedicated to a cause | Commercial pricing; surplus paid as a dividend | ~$100M/yr projected | https://www.patagoniaworks.com/press/2022/9/14/patagonias-next-chapter-earth-is-now-our-only-shareholder |
| Newman's Own | Mission-owned | Foundation owns 100% of the company | Product sales and royalties | $600M+ given | https://newmansown.org/faq/ |
| AuthBridge (India) | Background verification | Indian candidate verification | Per check | FY25 ≈ ₹144–148 Cr | https://inc42.com/company/authbridge/ |
| IDfy (India) | KYC / verification | Candidate and credit checks | Per verification (unverified) | FY25 ₹188.5 Cr, profitable | https://entrackr.com/exclusive/exclusive-idfy-posts-rs-188-cr-revenue-in-fy25-while-maintaining-profitability-9512349 |
| Qure.ai (India) | Radiology AI | Indian clinical AI with grant channels | Not public | $65M Series D | https://www.mobihealthnews.com/news/asia/qureai-pursuing-large-ai-65m-series-d-funding-and-more-briefs |

Not researched: Holistic AI, Fairly, ValidMind, OneTrust, Kira/Litera, Ironclad,
Evisort, Harver, Sterling, HireRight, Solventum, Nuance DAX, Suki, Nabla,
Veeva Vault, 5C Network.

## 2. Monetization patterns that fit SaptaDrishti

1. **Per run.** Checkr ($30–90 per report), DocuSign Part 11 ($4.99 per envelope), Ocrolus, Patronus. Each run record is one natural billable unit; plausible range **$5–75 per run**, depending on vertical.
2. **Per signer seat.** Harvey, Spellbook, MasterControl. Charge the Owner and Releaser roles and leave submitters free.
3. **Platform fee plus usage.** Galileo, Cleanlab, IBM. Health buyers prefer a base fee plus units defined in clinically meaningful terms. The best default for SD.
4. **Enterprise licence.** Credo AI, Luminance, Iodine. The register and method hash justify it to risk and compliance teams.
5. **OEM / royalty (the FICO model).** An ATS, EHR vendor or credit bureau embeds SD and pays per run. This is the "method is the asset" model.
6. **Method licence plus accreditation.** FICO, B Lab, ISO bodies. It must stay framed as "aligned with", never "certified by".
7. **Open-core funnel.** Vectara, Guardrails, Patronus Lynx. Publish the method specification; charge for the hosted, hashed, registered run.
8. **Outcome-based.** Iodine, Regard. Harder for SD because it produces integrity, not revenue. Possible forms: cost per defect caught, or a share of avoided write-offs in credit.
9. **Marketplace billing.** The Microsoft Marketplace supports per-user, flat-rate or usage-based offers for M365 Copilot agents (https://learn.microsoft.com/en-us/startups/build/ai/agents/monetizing-agents); AWS Marketplace is another route. MCP directories are for discovery only; none has billing today (unverified).
10. **Paid pilot credited to the contract.** The norm across these enterprises. It matches the pack's 60-day retrospective pilot and the 2AI pilot.

## 3. Pricing hypotheses (untested)

| Vertical | Hypothesis | Anchor |
|---|---|---|
| **SD Talent** | $25–60 (₹1,500–4,000) per candidate pack, or $500–1,500/mo for ~50 packs plus ~$15 per extra pack | Checkr per report; search fees are placement-linked, so a per-shortlist charge passes through to clients |
| **Clinical** | Platform fee ₹3–10 lakh/yr (India) or $25k–100k (US/EU), plus ₹20–100 / $1–5 per summary; grant or pilot funding for 2AI and public hospitals | Health-AI buyers prefer base plus units; far cheaper than a scribe seat |
| **Credit** | $0.50–3 per file (₹10–50) at volume; long-term, an OEM royalty per bureau | Ocrolus per statement; FICO distribution |
| **Legal** | $50–250 per instrument, or $200–500 per signer per month | Below drafting tools such as Spellbook |
| **Institutional** | $20–50 per user/month via the Copilot agent; $25k+/yr for an enterprise tier with the register | Galileo Pro; Copilot marketplace |
| **Cross-vertical** | Method licence $10k–50k/yr for white-label partners, plus a per-run royalty; a free open-method tier | FICO; Vectara / Guardrails open-core |

**Charity structure.** Price commercially, then route surplus to the
foundation through a Holdfast- or Newman's Own-style ownership or dividend
structure. Wikimedia Enterprise and Mozilla show buyers don't discount a
product because a nonprofit benefits.

## 4. Lessons and risks from comparables

1. **HireVue** dropped facial analysis in 2021 under pressure. Publish exactly what is evaluated, and never let Detachment become a hidden way of scoring people.
2. **NYC Local Law 144.** The state Comptroller called enforcement ineffective, and tougher enforcement is coming. If SD Talent output influences screening, clients may need a bias audit. https://www.osc.ny.gov/state-agencies/audits/2025/12/02/enforcement-local-law-144-automated-employment-decision-tools
3. **Mobley v. Workday.** A collective action was certified in 2025, so vendors can share liability for screening outcomes. SD's "no ranking, a human decides" design is a legal asset: keep it. https://www.hklaw.com/en/insights/publications/2025/05/federal-court-allows-collective-action-lawsuit-over-alleged
4. **Eightfold FCRA suit.** The claim is that AI candidate dossiers can count as consumer reports. If SD Talent checks third-party facts, consent, notice and dispute duties may apply.
5. **EU AI Act.** The Digital Omnibus moved Annex III high-risk duties (employment, credit) to 2 Dec 2027. That leaves about 14 months to sell *readiness*, never conformity. https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/
6. **Liability for AI errors.** Mata v. Avianca supports citation-gating. It also means SD's own wrong findings carry liability: allocate responsibility in contracts and carry professional-indemnity cover.
7. **The word "certificate".** Certification is a guarded role. Consider "Release Attestation" in place of "Release Certificate".
8. **Price backlash.** FICO's price rise drew Senate scrutiny. A charity-linked method licence should publish stable, transparent rates.
9. **Clinical ROI and scope.** An integrity-only pitch has no built-in ROI, so measured defect-catch rates are needed (the 2AI pilot's P1–P6 measures). Drifting into diagnostic suggestions risks regulation as software as a medical device.
10. **Channel concentration.** Mozilla's reliance on Google is the cautionary case. Don't depend on a single marketplace or bureau.
