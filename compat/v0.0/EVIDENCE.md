# V0.0 evidence and decision

**HOLD — 1/5 gates Pass.** Partial is not Pass. No V0.1 work is authorized by this
result. All independently achievable implementation, synthetic tests and local
HTTP checks are complete. Live compatibility and mobile browser rendering remain
unproven. No commits, pushes, merges, deployment, schedules or cloud changes.

## Repository verification

Start: 2026-11-25T07:05–07:06Z (UTC).

- Remote fetch/push: `https://github.com/dotsthewarlock/deals-dashboard`.
- Branch: `main`; HEAD: `986d80bb3b43bf1bcbf45837dae133f19f7c8b9c`, matching expected base.
- Existing tracked file: root README, containing `# deals-dashboard`.
- Starting status: `?? CODEX_V0.0_FEED_COMPATIBILITY.md` (user-provided task).
- `find .. -name AGENTS.md -print` and `find /workspaces -maxdepth 2 -name AGENTS.md -print`
  found no instructions. `.agents` and `.codex` directories were empty.
- `rg` was unavailable. Subsequent discovery used `find`, `grep`, `ls`, `cat`.
- Created local feature branch `compat/v0.0-feed-compatibility`; sandbox initially
  denied writing Git refs, then the escalated branch command succeeded.
- Task snapshot and root README were not edited. Changes are isolated below this
  directory; runtime data is ignored.

## Source review

Reviewed independently via web opens/searches during 2026-11-25T07:05–07:07Z.
These are source-specific findings, not a general legal determination. No accounts
were contacted and no tokens or paid access were requested.

### Brickset

The official [RSS index](https://brickset.com/article/52663/) explicitly offers RSS
reader use and links to [US](https://brickset.com/feed/amazon/us) and
[CA](https://brickset.com/feed/amazon/ca) separately. Those exact endpoints are
independently confirmed. Its invitation supports personal RSS reading; it does not
specify custom-dashboard display rights, retention duration, cache limits or a
required attribution format for this use. These boundaries remain unresolved.

The supplied [terms-of-use lead](https://brickset.com/article/52659/terms-of-use)
actually returned **About Brickset**, not terms of use. It discusses affiliate
funding and some image permissions, without settling this prototype's retention
and display scope. No image is copied or displayed. Source attribution and original
article/affiliate links are preserved by the implementation, but this does not
establish permission by itself.

The official [Amazon alerts explanation](https://brickset.com/article/24525/how-to-ensure-you-never-miss-a-bargain-at-amazon)
describes article text containing multiple reductions. This supports an
**article-aggregation hypothesis**, not a current live-sample finding. The adapter
preserves article-level observations without extracting product deals.

Following both official feed links in the web reader returned tool errors:
`(400) Unsupported content-type: text/xml`. This is a **web-reader limitation**,
not evidence of an origin HTTP 400, a valid parse or current real-record contents.
No feed body, record or origin response header was exposed to the implementation.
Per the task's unresolved-permission fallback, neither endpoint was subsequently
retrieved/cached/displayed by the prototype. Both policies remain blocked.

### Slickdeals

The official [terms](https://corp-site.slickdeals.net/content-list-slickdeals-terms-of-service/)
show effective date March 05, 2026. The proprietary-rights section requires express
permission for automated access and copying/displaying offers in another app.
The official [API resources](https://corp-site.slickdeals.net/api-resources/)
describe content-feed access via a token obtained from the team; they do not
provide an RSS exception to those restrictions. Targeted official-domain searches
did not establish specific RSS authorization. This is not a claim that no such
authorization could exist.

`https://slickdeals.net/rss.php` remains an **unverified candidate**, not a
validated endpoint. No automated request was made to it. No token, permission,
account setting, alternate endpoint or bypass was attempted. Source **Blocked**;
adapter exercised with synthetic Atom data only.

### Live observation ledger

| Endpoint | Permission result | Current records examined | Origin HTTP metadata | Current semantics |
|---|---|---:|---|---|
| Brickset `/feed/amazon/us` | RSS reading supported; cache/custom display unresolved | 0 of target up to 10 | Not available; web-reader XML limitation | Not established from live records |
| Brickset `/feed/amazon/ca` | Assessed independently, same unresolved boundaries | 0 of target up to 10 | Not available; web-reader XML limitation | Not established from live records |
| Slickdeals `/rss.php` | Express permission unresolved; candidate unverified | 0 of target up to 10 | Not requested | Not established |

No real sample has been relabeled as synthetic or vice versa. There are no live
payloads, real offer excerpts or personal preferences in these deliverables.
Redacted live sample findings: **none available**, rather than invented samples.

## Implementation evidence

[Source](./feedcompat.py), [synthetic RSS](./fixtures/rss.xml),
[synthetic Atom](./fixtures/atom.xml), [tests](./test_feedcompat.py),
[setup and limits](./README.md), [ignore rules](./.gitignore).

Five fixture records seeded at 2026-11-25T07:11:32Z: Brickset-US 2, Brickset-CA 2,
Slickdeals-US 1. All have `provenance.synthetic=true`. Same native article IDs in
CA and US stay separate; unknown currency/price/stock/expiry stay unknown.
Reward percentages do not become unconditional discounts. Native identifiers
and affiliate URLs remain intact. Stable native IDs support hash-based revisions;
identity-less fallback has the limits documented in the README.

Live command at 2026-11-25T07:11:32Z returned `failed` for all three sources, before
network access. Their cache states contain zero records, null `lastSuccessAt`,
separate UTC `lastAttemptAt`, explicit permission errors and a retry backoff.
These are **blocked attempts, not HTTP failures or live retrieval evidence**.

Cache tests demonstrate process-level locking, atomic persistence/reload,
30-minute TTL, conditional headers, synthetic 304 handling, empty/unchanged
responses, material revisions, deduplication, failure preservation and Retry-After.
Network safety tests cover private/mixed DNS, exact allowlisting, TLS hostname/IP
pinning, unsafe redirects, size, truncation, compression, MIME and elapsed deadline.
HTTP transport is mocked in those tests; it does not establish live endpoint support.

## Actual automated output

Command: `python3 -m unittest discover -s compat/v0.0 -v`.
Final run: 2026-11-25T07:14:25Z, Linux / Python 3.14.2.
**41 discovered, 40 passed, 1 skipped, 0 failures, 0 errors.**
Exact final output below (local HTTP access log included):

```text
test_atom (test_feedcompat.Parsing.test_atom) ... ok
test_bounded_text_and_payload (test_feedcompat.Parsing.test_bounded_text_and_payload) ... ok
test_dates_do_not_invent_timezone (test_feedcompat.Parsing.test_dates_do_not_invent_timezone) ... ok
test_dtd_and_entities (test_feedcompat.Parsing.test_dtd_and_entities) ... ok
test_duplicate_native_ids (test_feedcompat.Parsing.test_duplicate_native_ids) ... ok
test_invalid_prices_and_rewards_are_not_discount (test_feedcompat.Parsing.test_invalid_prices_and_rewards_are_not_discount) ... ok
test_links_and_affiliates_preserved (test_feedcompat.Parsing.test_links_and_affiliates_preserved) ... ok
test_malformed_truncated_and_wrong_root (test_feedcompat.Parsing.test_malformed_truncated_and_wrong_root) ... ok
test_markets_separate_same_native_id (test_feedcompat.Parsing.test_markets_separate_same_native_id) ... ok
test_missing_id_stable_fallback (test_feedcompat.Parsing.test_missing_id_stable_fallback) ... ok
test_native_identifier_not_silently_truncated (test_feedcompat.Parsing.test_native_identifier_not_silently_truncated) ... ok
test_rss_and_contract (test_feedcompat.Parsing.test_rss_and_contract) ... ok
test_unknown_market (test_feedcompat.Parsing.test_unknown_market) ... ok
test_unsafe_links (test_feedcompat.Parsing.test_unsafe_links) ... ok
test_unsafe_markup_removed (test_feedcompat.Parsing.test_unsafe_markup_removed) ... ok
test_url_fallback (test_feedcompat.Parsing.test_url_fallback) ... ok
test_conditional_304 (test_feedcompat.Persistence.test_conditional_304) ... ok
test_corrupt_cache_not_overwritten (test_feedcompat.Persistence.test_corrupt_cache_not_overwritten) ... ok
test_cross_market_persistence (test_feedcompat.Persistence.test_cross_market_persistence) ... ok
test_empty_and_disappearance_preserve_inventory_unknown (test_feedcompat.Persistence.test_empty_and_disappearance_preserve_inventory_unknown) ... ok
test_failure_preservation_and_backoff (test_feedcompat.Persistence.test_failure_preservation_and_backoff) ... ok
test_material_change_same_id (test_feedcompat.Persistence.test_material_change_same_id) ... ok
test_overlapping_retrieval_rejected (test_feedcompat.Persistence.test_overlapping_retrieval_rejected) ... ok
test_parse_failure_preserves (test_feedcompat.Persistence.test_parse_failure_preserves) ... ok
test_reload (test_feedcompat.Persistence.test_reload) ... ok
test_retry_after_source_limit (test_feedcompat.Persistence.test_retry_after_source_limit) ... ok
test_ttl (test_feedcompat.Persistence.test_ttl) ... ok
test_unchanged_dedup_and_revision (test_feedcompat.Persistence.test_unchanged_dedup_and_revision) ... ok
test_unsolicited_304 (test_feedcompat.Persistence.test_unsolicited_304) ... ok
test_valid_empty_initial (test_feedcompat.Persistence.test_valid_empty_initial) ... ok
test_output_escaped (test_feedcompat.Preview.test_output_escaped) ... ok
test_real_local_http_preview (test_feedcompat.Preview.test_real_local_http_preview) ... 127.0.0.1 - - [25/Nov/2026 07:14:25] "GET / HTTP/1.1" 200 -
ok
test_arbitrary_endpoint_rejected_before_dns (test_feedcompat.Transport.test_arbitrary_endpoint_rejected_before_dns) ... ok
test_http_200_and_304 (test_feedcompat.Transport.test_http_200_and_304) ... ok
test_http_failure_truncation_size_compression_and_redirect (test_feedcompat.Transport.test_http_failure_truncation_size_compression_and_redirect) ... ok
test_live_permitted_retrieval (test_feedcompat.Transport.test_live_permitted_retrieval) ... skipped 'Live permissions unresolved; no fixture counts as live retrieval'
test_permission_before_dns_or_http (test_feedcompat.Transport.test_permission_before_dns_or_http) ... ok
test_pinned_tls_identity (test_feedcompat.Transport.test_pinned_tls_identity) ... ok
test_private_dns_and_mixed_dns_rejected (test_feedcompat.Transport.test_private_dns_and_mixed_dns_rejected) ... ok
test_stream_size_without_content_length (test_feedcompat.Transport.test_stream_size_without_content_length) ... ok
test_total_deadline (test_feedcompat.Transport.test_total_deadline) ... ok

----------------------------------------------------------------------
Ran 41 tests in 0.629s

OK (skipped=1)
```

Initial run discovered 37 tests and had 3 errors: two malformed-XML assertions
expected ValueError rather than ElementTree's ParseError; the parser now exposes
a consistent ValueError. The third was sandbox denial of socket creation. The
approved run outside the sandbox then passed 36 tests with 1 live skip. Four added
boundary/backoff tests produced the final count above. No result was hidden by
silently skipping the local HTTP test. Editor `problems` returned
`No client available to run problems`; this was not counted as a diagnostic pass.

## Runtime and mobile limitations

`demo` printed `updated` for all three synthetic adapters. `live` printed `failed`
for each blocked policy. `serve` initially failed inside the sandbox with
`PermissionError: [Errno 1] Operation not permitted`. Approved execution outside
the sandbox started `Local synthetic preview: http://127.0.0.1:8765`.

A separate curl request initially could not connect from inside the sandbox; its
approved execution outside the sandbox succeeded and captured headers/HTML only
under the ignored runtime directory. The test suite also actually served and
requested the preview on an ephemeral loopback port, asserting HTTP 200, viewport,
responsive CSS, CA/unverified/fixture labels, escaping, CSP and no-store headers.
Neither check is a mobile browser rendering test.

No Chromium/Chrome executable, Playwright package, desktop/browser tools or cloud
browser runtime were available. Browser rendering at a mobile viewport is **Not
tested**. No screenshot, accessibility, horizontal-overflow or touch-target pass
is claimed. No dependencies were installed to conceal this limitation. The
cloud-desktop skill was consulted for environment checks; it did not require an
approval or block independent implementation.

## Five-gate acceptance matrix

| Gate | Grade | Evidence and missing requirement |
|---|---|---|
| F1: exact endpoints and permitted retrieval/cache/display | Partial | Brickset endpoint links and RSS-reader use confirmed. Custom-display/retention scope unresolved. Slickdeals candidate and RSS permission unverified. |
| F2: representative real records from both families | Blocked | US 0, CA 0, Slickdeals 0. Source permission fallback enforced. No synthetic record counts here. |
| F3: safe parsing and normalization of real and synthetic records | Partial | Synthetic RSS/Atom/security/unknown-fields tests pass. No real-record parsing or field accuracy evidence. |
| F4: persistent cache, freshness, deduplication and failure behavior | Pass | Actual disk/reload/lock/TTL/revision/failure tests pass; HTTP variants are synthetic, clearly labeled. |
| F5: runtime feasibility and mobile-compatible preview | Partial | Actual local HTTP 200, responsive markup and fixtures demonstrated. Mobile rendering and private forwarded browser access not tested. |

**Passed: 1/5. Decision: HOLD.**

Fallback recommendation: use the synthetic local preview for compatibility work.
A **Brickset-only personal RSS-reader pilot is a conditional candidate**, because
it publishes RSS feeds, but is not validated or approved here: resolve cache,
retention and custom-display scope, then independently inspect up to ten current
records per market and test mobile rendering. Do not claim a two-family milestone
or quietly replace Slickdeals. Slickdeals requires explicit applicable permission
or documented RSS authorization before retrieval. These are future decision
inputs, not actions taken or V0.1 work.

## Commands and ending state

All shell commands were run from `/workspaces/deals-dashboard` unless otherwise
noted. Relevant exact commands (including unsuccessful attempts):

```sh
pwd && rg --files -g 'AGENTS.md' -g 'package.json' -g '*FEED*' -g 'README*'
find . -name AGENTS.md -o -name '*FEED*' -o -name package.json -o -name README.md
cat CODEX_V0.0_FEED_COMPATIBILITY.md
find .. -name AGENTS.md -print
git status --short
ls -la
git remote -v
git branch --show-current
git rev-parse HEAD
git log -1 --format=fuller
cat README.md
find .agents .codex -maxdepth 3 -type f -print
python3 --version
which node chromium chromium-browser google-chrome
git switch -c compat/v0.0-feed-compatibility
date -u +%FT%TZ
find /workspaces -maxdepth 2 -name AGENTS.md -print
ls -la .agents .codex
python3 -c "import importlib.util; print('playwright:', bool(importlib.util.find_spec('playwright')))"
mkdir -p compat/v0.0/fixtures
find /usr /opt /tmp -maxdepth 4 -iname '*playwright*' -o -iname '*chromium*' 2>/dev/null
printenv | grep -E 'CODESPACE_NAME|GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN'
ls -Ld /usr/local/bin/cloud-agent-browser-runtime /opt/codex/marketplaces/openai-bundled/plugins/unified-computer-use/.codex-plugin/plugin.json
find /usr/local/lib /opt /home/codespace -maxdepth 4 -iname '*playwright*' -o -iname '*chrome*' 2>/dev/null
python3 -m unittest discover -s compat/v0.0 -v
python3 compat/v0.0/feedcompat.py demo
python3 compat/v0.0/feedcompat.py live
git check-ignore compat/v0.0/runtime/synthetic/cache.json compat/v0.0/runtime/live/cache.json
git status --short --untracked-files=all
python3 compat/v0.0/feedcompat.py serve
curl --max-time 5 --silent --show-error --dump-header compat/v0.0/runtime/preview-headers.txt --output compat/v0.0/runtime/preview.html http://127.0.0.1:8765/
git diff --check
git status --porcelain=v1 --untracked-files=all
```

Web operations opened the four task documentation leads, followed the two RSS
index links, searched official domains for RSS permissions/terms and opened the
official Amazon explanation. Those are documentation research, not successful
feed retrieval. File creation/edits used the patch tool. Auxiliary read-only cache
inspection printed source record counts, lastAttemptAt, lastSuccessAt and errors.

Ending branch remains `compat/v0.0-feed-compatibility`; HEAD remains the expected
base; tracked diff empty. New deliverables: `.gitignore`, `feedcompat.py`,
`test_feedcompat.py`, `fixtures/rss.xml`, `fixtures/atom.xml`, `README.md`,
`EVIDENCE.md` under `compat/v0.0/`. User task remains untracked and unchanged.
Runtime cache, lock files, HTML/headers and bytecode are ignored. No tracked file
was modified. A local-only preview process was left available on port 8765; no
forwarding visibility was changed. Final verification details follow below.

Final checks at **2026-11-25T07:17:02Z**:

```text
GET http://127.0.0.1:8765/ (curl): HTTP/1.0 200 OK
Date: Wed, 25 Nov 2026 07:14:52 GMT
Server: BaseHTTP/0.6 Python/3.14.2
Content-Type: text/html; charset=utf-8
Content-Length: 3550
Cache-Control: no-store
Content-Security-Policy: default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'; form-action 'none'
X-Content-Type-Options: nosniff

Captured HTML: 5 article elements, 5 SYNTHETIC FIXTURE labels;
viewport and max-width:480px rules present. This is static inspection, not browser rendering.

python3 -m py_compile compat/v0.0/feedcompat.py compat/v0.0/test_feedcompat.py
Exit 0, no output.

git diff --check
Exit 0, no output (tracked changes only; deliverables are untracked).

git diff --name-only
No output.

git branch --show-current
compat/v0.0-feed-compatibility

git rev-parse HEAD
986d80bb3b43bf1bcbf45837dae133f19f7c8b9c

git status --porcelain=v1 --untracked-files=all
?? CODEX_V0.0_FEED_COMPATIBILITY.md
?? compat/v0.0/.gitignore
?? compat/v0.0/EVIDENCE.md
?? compat/v0.0/README.md
?? compat/v0.0/feedcompat.py
?? compat/v0.0/fixtures/atom.xml
?? compat/v0.0/fixtures/rss.xml
?? compat/v0.0/test_feedcompat.py

git check-ignore compat/v0.0/runtime/preview.html compat/v0.0/runtime/preview-headers.txt compat/v0.0/runtime/synthetic/cache.json compat/v0.0/runtime/live/cache.json
compat/v0.0/runtime/preview.html
compat/v0.0/runtime/preview-headers.txt
compat/v0.0/runtime/synthetic/cache.json
compat/v0.0/runtime/live/cache.json

sha256sum CODEX_V0.0_FEED_COMPATIBILITY.md
4ff074f101d1b56722ce7a2e33761be58f46e5bdd2946a9b554960cb85b97172  CODEX_V0.0_FEED_COMPATIBILITY.md
```

Ending checksum identifies the task snapshot; no starting checksum was taken, so
it is not represented as a before/after checksum comparison. The task was only read.
