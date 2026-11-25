# V0.0 feed compatibility prototype

Standard-library Python 3.11+ prototype. Tested with Python 3.14.2 on Linux.
No dependencies, accounts, scheduler, cloud configuration or production PWA.
Current V0.0.2 decision: **HOLD, 2/5 original gates passed**. See
[EVIDENCE_V0.0.2.md](./EVIDENCE_V0.0.2.md). The historical
[V0.0 report](./EVIDENCE.md) is preserved; its synthetic-only F4 Pass was overstated.

## Independent review snapshot

This public snapshot contains only prototype source, synthetic fixtures, tests,
this setup guide, ignore rules and the three historical evidence reports:
[V0.0](./EVIDENCE.md), [V0.0.1](./EVIDENCE_V0.0.1.md), and
[V0.0.2](./EVIDENCE_V0.0.2.md). Their UTC timestamps, failed/skipped checks and
scope qualifications are historical observations, not promises of current source
permission or a completed browser test. Their original uncommitted Git status
and no-publication statements describe those runs; the owner subsequently
authorized this review publication.

Publication validation on 2026-11-25 at approximately **07:42:37 UTC**:

```text
python3 -m unittest discover -s compat/v0.0 -v
Ran 50 tests in 0.081s
OK (skipped=1)
```

**49 passed, one live test skipped, zero failures/errors**. Python compilation
also passed. This rerun made no live source requests and did not add browser
evidence. Read the matrices in V0.0.2: F1/F2/F5 remain Partial for the original
two-family objective; scoped Brickset-only remains 4/5, with F5 Partial.

For review, use the fixture test/demo commands below. No raw feed, real item
title/URL dataset, runtime cache, request ledger, credential, private preview URL,
personal preference or root instruction snapshot is included. The evidence keeps
redacted structural counts and HTTP metadata rather than live payloads. The
placeholder private-preview URL format was omitted from this guide; use the
Codespaces Ports panel's actual private URL locally.

The disposable V0.0.2 smoke harness and earlier one-off real-data assertion script
were runtime files and are deliberately excluded. Commands mentioning them in
historical reports cannot be replayed from this snapshot. The existing default
fixture preview remains reproducible; synthetic empty/failure state assertions
are in [test_brickset_reader.py](./test_brickset_reader.py). No desktop/mobile
rendering result or complete replay of the earlier live observations is claimed.

**Do not run the dedicated live reader merely to review the code.** Its request
budget is enforced by a local ignored ledger, not a global/source-side lock.
A fresh checkout has no consumed ledger and can make new requests if that reader
is explicitly invoked. Reassess the permitted scope, timing and authorization
before any new live run; never copy private caches or erase an existing ledger
to bypass the budget. Default `live` remains blocked. Prototype behavior is
unchanged in this publication task; known limits include request-start success
timestamps, OS-bounded DNS timing, content-based identity fallback, and possible
temporary-cache remnants after a hard crash, as described below and in evidence.

## Fixture setup

From the repository root:

```sh
python3 -m unittest discover -s compat/v0.0 -v
python3 compat/v0.0/feedcompat.py demo
python3 compat/v0.0/feedcompat.py serve
```

Open `http://127.0.0.1:8765/` in a browser running in the same environment.
For browser-accessible Codespaces use VS Code's **Ports** panel, add port **8765**,
verify **Port Visibility: Private**, then choose **Open in Browser** while signed
in to the owning GitHub account. Use the URL provided by the Ports panel and do
not change visibility to public. V0.0.2 verified port visibility as Private, but
did not verify an authenticated browser opening. Server binding remains
loopback only. Use `--port 8766` if needed. Stop with Ctrl+C.

The default preview shows only the synthetic cache, clearly labels fixtures and permission
blocks, and makes no browser-side API requests. It includes market, source,
timestamps, verification, availability and source freshness. Long links wrap and
spacing adjusts below 480px. Actual mobile browser rendering was not tested here.

`demo` seeds five synthetic records across three adapters (2 US, 2 CA, 1
Slickdeals fixture). Repeated demo calls respect the 30-minute TTL.

```sh
python3 compat/v0.0/feedcompat.py live
```

Currently exits **2**: all source policies block live retrieval before DNS or HTTP.
Blocked-attempt metadata is persisted separately from synthetic data. This command
does not fetch Slickdeals or Brickset payloads. There is no permission override
flag. Enabling a source requires documented permission evidence and a reviewed
policy change. V0.0.1 separately adds the narrowly scoped reader mode below; the default
command still cannot enable a source. The general live test is
explicitly skipped while no sources are permitted. Do not count fixtures as live
compatibility. The preview deliberately has no fetch button or arbitrary URL input.

## Implementation boundaries

- [feedcompat.py](./feedcompat.py) parses RSS 2.0 / Atom 1.0 and normalizes contract
  v1. Titles and summaries are bounded plain text, links retain affiliate queries,
  executable markup is never rendered. Unsupported encodings, DTD/entities, bad
  XML, oversized bodies/items and oversized identifiers fail closed.
- No price extractor: article/offer kind remains unknown; price, currency,
  comparison basis, discount, promotion, merchant, product ID, restrictions and
  expiry remain null. Verification is unverified; stock is unknown. Percentages,
  rewards and ambiguous dollar amounts never become invented discounts.
- Identity is scoped by source, then native ID, then source URL, then a deterministic
  title/date/summary hash. Identical native IDs are deduplicated within a feed;
  the last occurrence wins. CA and US never merge. Content-only fallback identity
  cannot reliably track revisions when all stable identity evidence is absent.
- Atomic persistent cache with a process-level advisory lock; overlapping refresh
  fails before fetching. TTL is 30 minutes. ETag/Last-Modified validators are used
  when present. Valid empty, unchanged and supported 304 responses refresh the
  source clock. Errors preserve records and the successful clock. Retries back off
  from 30 minutes to 24 hours; longer valid Retry-After instructions are honored.
- Disappeared records remain available as historical observations with their old
  observedAt. Source freshness does not verify a historical offer or its stock.
  No inferred expiry, automatic purge, retention entitlement or archival license.
  Cache capacity is bounded; exceeding it fails without replacing last-good data.
- Retrieval is exact-endpoint allowlisted and permission gated, ignores environment
  proxies, rejects non-global DNS answers, pins the vetted IP while checking TLS
  against the hostname, rejects unapproved redirects (including cross-market),
  and requests uncompressed XML. Body limit 1 MB, socket timeout 10 seconds,
  elapsed deadline checked at 20 seconds. An in-progress socket/DNS operation can
  finish after that deadline; DNS has the OS resolver's timeout. No promise of a
  strict wall-clock bound is made. Four redirect attempts maximum; no automatic retry.
- All runtime caches, HTTP captures and bytecode are [gitignored](./.gitignore).
  Live payloads are never written separately. Synthetic and live cache directories
  are separate. Only synthetic fixtures belong in version control.

The test suite includes mocked HTTP responses and actual local HTTP serving, with
no requests to real source endpoints. Mocked 304 support is not evidence that a
live endpoint offers conditional retrieval. Browser tooling and editor diagnostics
were unavailable; see the evidence for those limits.

## V0.0.1 Brickset reader check

[brickset_reader.py](./brickset_reader.py) implements the handoff's ordinary personal
RSS-reader scope. It does not enable the default policies or Slickdeals. The exact
command used was:

```sh
python3 compat/v0.0/brickset_reader.py --serve --port 8765 --seconds 180
```

This already consumed the handoff's one initial request per market. A persistent
gitignored request-budget ledger prevents accidental reruns, including across
processes. Do not delete it merely to get another fetch. No follow-up was made:
both initial responses succeeded and provided no conditional validators. Further
live checks need a separately agreed request budget and an appropriate interval.

The reader fetches both feeds once, validates/parses XML in memory, inspects at most
ten articles per market, and stores at most ten minimal metadata records per market
in a fresh, private, gitignored temporary session directory. Summaries, table HTML,
images and raw XML are not stored. Titles, original article/affiliate links, scoped
identity, source/market and timestamps remain; price, currency, stock and expiry
remain unknown. Real article observations carry `reported`, not independently
verified offer status. The console and persistent request ledger contain only
redacted field-presence/structure counts and HTTP metadata.

Temporary cache retention is the process lifetime, at most 30 minutes (180 seconds
in the actual run). The preview performs no additional source requests and stops
automatically, deleting its owned temporary directory. Normal interruption also
cleans up. SIGKILL, host crash or power loss can leave an orphan directory: there
is no unattended cleanup service, and expiry-on-read does not erase a file that
is never read again. Existing user caches are never deleted. This is a bounded
personal-reader interpretation of the RSS invitation, not an express archival or
redistribution license. No long-term price history or raw archives are permitted.

The reader binds loopback before fetching; an occupied port causes it to stop
without another request or interference with the existing listener. Only the
reader session is displayed, with no synthetic cards mixed in. Use the Private
Codespaces instructions above during an authorized live session. The completed
180-second session is stopped; the default synthetic preview remains reproducible
without more source requests.

Owner browser checklist (not completed here):

1. Start the synthetic preview with the commands above, open only a Private port,
   and test at desktop width and approximately **390px** mobile width.
2. Confirm no horizontal scrolling, readable source/market/date/status labels,
   comfortable link targets and intact original destinations; do not navigate to
   merchants as part of the compatibility check.
3. Check empty/failure/stale rendering against the regression tests. Do not induce
   additional real feed requests to manufacture an error state.
4. Real-card rendering needs a separately authorized bounded live session; fixture
   rendering alone must not be credited as real-data browser evidence. No physical
   Android claim is made.
