# CODEX task: V0.0.1 Brickset live compatibility

Project: PWA Deal Dashboard (R2)
Repository: dotsthewarlock/deals-dashboard
Expected local branch: compat/v0.0-feed-compatibility
Expected base HEAD: 986d80bb3b43bf1bcbf45837dae133f19f7c8b9c
Workspace: /workspaces/deals-dashboard
Date: 2026-11-25
Decision entering task: HOLD at original V0.0 five-gate review.

## 1. Authorization and stop condition

This is an authorized local compatibility follow-up, not V0.1. Reuse the existing uncommitted implementation in compat/v0.0/. Do not create a new repository, reset, clean, overwrite unrelated work, commit, push, merge, deploy, change account settings, expose public ports, use paid services, or schedule work. No GiftCash, GPT runtime, new source families, JSON adapter, production app, authentication service or external merchant scraping. Do not contact providers or send messages on the owner's behalf. Stop at a documented GO/HOLD recommendation; the owner must separately approve any single-source pilot or revised release gate.

The remote was previously observed to be public. Keep live payloads, caches, private preview links, credentials and personal data out of tracked files and public outputs. Use synthetic fixtures in any eventual shareable code. Do not print environment variables or secrets. Use approved execution permissions only; do not bypass sandbox or network restrictions. If an essential operation requires approval, request only that narrow operation.

## 2. Preflight and baseline audit

Read this file as the implementation instruction, not as passive context. Read repository AGENTS.md files if present, original CODEX_V0.0_FEED_COMPATIBILITY.md, compat/v0.0/README.md, EVIDENCE.md, feedcompat.py, test_feedcompat.py, fixtures and .gitignore. Use find/grep if rg is unavailable. Inspect git remote, branch, HEAD, status including untracked files, and any running preview. Verify expected workspace identity; stop if wrong repository or conflicting changes prevent safe continuation. Preserve all existing files and the original evidence; append a dated review or create EVIDENCE_V0.0.1.md rather than rewriting history.

Prior Codex report: 40 passed, 1 skipped live test, zero failures; seven added files, 1184 added lines; local HTTP preview on port 8765 returned 200; no actual mobile browser test; no live records. These are reported baseline facts, not a new independently executed test. Rerun python3 -m unittest discover -s compat/v0.0 -v before editing. If loopback socket tests fail because of sandbox, use supported narrowly approved execution or report blocked. Record command, exit status, tests and skips. Review code for allowlisting/redirect safety, bounded XML parsing, source-specific identity, currency/price handling, cache atomicity and concurrency, live/synthetic isolation, status semantics, and preview escaping. Correct only demonstrated V0.0 defects needed for this task; avoid broad refactors or dependencies. Report issues and changes separately.

## 3. Source permission and retrieval scope

Official source documentation to inspect and timestamp:
- https://brickset.com/article/52663/ (RSS index, expressly intended for RSS readers; CA and US Amazon Bargain Watch)
- https://brickset.com/article/57700/keeping-up-to-date (RSS reader use)
- https://brickset.com/article/52659/ (About page, not an RSS license; affiliate model)
- https://brickset.com/article/52666/api-version-3-documentation-terms-of-use (separate API, do not invoke)
- https://corp-site.slickdeals.net/content-list-slickdeals-terms-of-service/ (effective March 5, 2026, automated access and external display restrictions)

The official Brickset index links to:
- US: https://brickset.com/feed/amazon/us
- CA: https://brickset.com/feed/amazon/ca

The review browser returned unsupported text/xml for these links; this is not a live HTTP payload verification. Verify the exact endpoint and response in Codespaces. Slickdeals remains disabled: no automated requests to its services and no real content fixtures. Do not infer authorization from an endpoint working or from absence of a prohibition.

The official RSS invitation supports ordinary personal reader consumption, not an unrestricted license for permanent structured price databases, redistribution, public previews or republishing full articles. Independently check applicable current terms, robots guidance and source-specific limits. If a conflicting restriction is found, stop that operation and explain it. Do not require a blanket commercial/API license simply to make a normal bounded private RSS reader request where the published invitation supports that request. Use the minimum needed for this compatibility check: read and parse in memory, private display of limited attributed feed metadata, preserve source and affiliate links, no images or full-content archives. Separate ordinary reader use from persistent cache/display permission; explicitly document evidence, interpretation and unresolved scope. Where normal transient reader cache is defensible under the applicable rules, test a short-lived, bounded, gitignored cache of minimal normalized metadata and reload; do not assert that a chosen TTL grants rights. If persistence is not supported by the evidence, use memory only for real data, demonstrate persistent behavior with synthetic fixtures, leave F4 partial, and propose an owner-approved clarification. No long-term price history or raw feed archive. Do not make repeated requests just to chase a passing test.

## 4. Live retrieval and normalization

Use existing Python standard-library implementation where possible. Inspect its actual CLI and permission flags first; do not blindly disable permission guards. Add a narrowly scoped Brickset reader mode only if necessary, with the restrictions above. Default remains conservative. Enforce HTTPS allowlist, bounded time/size, XML DTD/entity rejection, safe redirect validation and no private/link-local/metadata network destinations. Honor 429/Retry-After and stop on denial, no proxies, spoofed access or circumvention. Make at most one initial fetch per market, plus at most one justified follow-up per market after permitted interval (or documented permitted conditional request); never poll in a loop. Record UTC time, status, final URL, content type, encoding, byte size, validators, item count and error category; redact sensitive details. Do not confuse web reader tool's content-type error with origin response status. If empty, note valid empty vs unexpected malformed/truncated; do not claim no market deals.

Inspect up to 10 representative real records per market (all if fewer). Determine whether items are individual offers or articles containing multiple offers. Keep article identity and provenance; only split reliably structured individual rows if needed for matching and evidence is unambiguous. Minimal source-specific normalization extension if justified, otherwise retain article-level records and document coverage. Preserve actual source/affiliate URLs without executing markup. For each reliable offer retain set number, title, reported merchant/seller where known, market, native price/reference price in integer minor units, currency, discount basis, dates and evidence when supported. Market derives from confirmed feed scope, not a dollar symbol; CAD/USD only with supporting market/currency semantics. Do not infer current stock, expiration, MSRP, seller, checkout price or availability. Distinguish advertised comparison from documented MSRP; calculated discounts only from comparable known prices. No independent price verification or retailer requests. Record unknowns, extraction coverage, rejected/ambiguous rows and representative redacted field-level findings. Use stable per-source ID; if multiple offers in one article, stable source/article/product/offer identity with market separation, not row index or title alone. Keep source evidence distinct from normalized interpretation. Synthetic offer-level tests may use invented set IDs and prices explicitly labeled fixtures.

## 5. Cache and refresh validation

Retain existing 30-minute provisional source TTL only if consistent with documented limits; do not force repeated live checks to demonstrate it. Use simulated time and mock transport for fast tests. Verify lastAttemptAt vs lastSuccessAt; valid empty/unchanged/304 may advance successful freshness, failure cannot. Preserve last-good records on failure; disappearance from feed is not expiry. Test reload from disk with permitted real minimal data if supported, otherwise synthetic only and mark real persistence blocked. Record observed validators and whether a real conditional response was observed; synthetic 304 is not live 304. Verify idempotency, no overlapping duplicate refresh, material change versioning, safe cache boundaries and separate live/fixture stores. Use existing gitignore and verify it covers all new runtime files. Record actual retention behavior and outstanding rights separately; don't delete existing user data. No periodic unattended refresh.

## 6. Private preview

Reuse the existing local preview, not a production PWA. Check whether port 8765 is already running and avoid duplicate listeners. Verify HTTP response, safe rendering, source/market attribution, original links, reported/unknown/stale labels, empty/failure status, and clear fixture versus live separation. Keep loopback/private Codespaces preview; no public forwarding or production hosting. If an already authorized private port is available, use it; otherwise provide exact browser-only instructions for owner to open the preview with visibility Private (do not change port visibility or account configuration without approval). If preview cannot be exposed privately, stop there. Actual mobile viewport test at approximately 390px plus desktop: no horizontal overflow, readable labels, tap targets, links and error state. Use existing supported browser tooling if available; if not, provide owner smoke-test checklist and mark mobile browser validation not tested. HTTP 200, CSS inspection or viewport meta tag alone does not establish rendering. No browser installs or new heavy dependencies merely to pass this gate; no physical Android claim unless actually tested. Stop any new temporary server when practical or document how owner can stop it; preserve any pre-existing unrelated process.

## 7. Evidence and acceptance

Run existing suite plus focused regression tests for any code changes, py_compile and git diff --check; include untracked files in review, check ignore patterns and secret/live-content leakage. Record actual output, test totals, skipped reasons and environment. Do not commit or push. Keep existing branch. Create compat/v0.0/EVIDENCE_V0.0.1.md and update README only as necessary for reproducible setup. Include exact commands, checked UTC times, source URLs, scope/permission reasoning, live HTTP and normalization observations (minimal redacted metadata only), actual cache behavior, preview checks, original vs current gate grades, changed file list, git status, known flaws and fallback. If live permission or access is blocked, finish independently achievable audit/tests without expanding scope.

Original R2 gates (equally weighted; all must pass for full V0.0 GO):
- F1 exact live endpoints and permitted personal retrieval/cache/display/attribution for both source families; current Partial.
- F2 representative live records for both required families; current Blocked.
- F3 correct normalization of live records and safe synthetic edge cases; current Partial.
- F4 live records persisted and reloaded, repeat retrieval/conditional where supported, TTL, valid empty/unchanged, failure preservation, dedupe and retries; current Partial (prior Codex Pass was overstated because only synthetic persistence demonstrated).
- F5 actual isolated fetch/parse/cache runtime, mobile-compatible view with real browser evidence and reproducible browser setup; current Partial.

Grade Pass/Partial/Fail/Blocked/Not tested for each; no partial counts as pass. Report separate Brickset-only matrix with CA and US evidence so the owner can decide whether to approve a reduced-source pilot. Slickdeals remains out of live testing, not silently removed from original acceptance criteria. Full original V0.0 remains HOLD if any material gate is incomplete. A conditional recommendation for a Brickset-only V0.1 pilot is not authorization to build or deploy it. No fixtures credited as live evidence. If any review result cannot be independently checked, label reported/unverified.

Return concise decision, changes, evidence and gaps, exact local report paths, tests, Git branch/HEAD/status, private preview instructions if applicable, and smallest next action. Stop at the V0.0.1 decision gate; no publication, paid usage, deployment or V0.1 implementation.
