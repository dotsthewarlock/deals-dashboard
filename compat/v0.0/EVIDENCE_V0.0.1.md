# V0.0.1 Brickset live compatibility — 2026-11-25 UTC

**Decision: HOLD at the V0.0.1 gate. Original two-family R2 gates: 2/5 Pass.
Brickset-only scoped reader gates: 4/5 Pass.** No pilot or V0.1 implementation is
approved by this result. Original [V0.0 evidence](./EVIDENCE.md) is preserved.

## Authorized task and preflight

Fetched with `git fetch origin handoff/v0.0.1`; the first sandbox attempt failed
because `.git/FETCH_HEAD` was read-only. Narrow approved execution succeeded.
`git rev-parse FETCH_HEAD` returned exactly
`66e0994c8d08782f3b471488b5b89c8dd6d59f27`.
Read the instruction using
`git show FETCH_HEAD:CODEX_V0.0.1_BRICKSET_LIVE_COMPATIBILITY.md`.
The handoff was not checked out, merged, or copied over local work.

Preflight 2026-11-25T07:23–07:25Z verified:

- Workspace `/workspaces/deals-dashboard`, remote fetch/push
  `https://github.com/dotsthewarlock/deals-dashboard`.
- Local branch `compat/v0.0-feed-compatibility`, HEAD
  `986d80bb3b43bf1bcbf45837dae133f19f7c8b9c`, matching the expected base.
- Starting untracked files: root task and the seven prior prototype files
  `.gitignore`, `EVIDENCE.md`, `README.md`, `feedcompat.py`, `test_feedcompat.py`,
  `fixtures/rss.xml`, `fixtures/atom.xml` under `compat/v0.0/`.
- `find .. -name AGENTS.md -print` returned none. Read the original task,
  prototype source/tests/fixtures/README/evidence/ignore rules. Reviewed untracked
  implementation directly; it would not appear in a normal tracked Git diff.
- The prior preview was reported as previously running, but this was rechecked:
  approved `curl` at 07:25Z returned connection failure / status 000 on loopback
  port 8765. No existing listener was replaced or killed.
- Pre-edit suite independently rerun: **41 tests, 40 passed, 1 skipped**, exit 0.
  An initial preflight invocation succeeded; its combined tool output was
  truncated. Repeated once to capture a complete baseline before any code edit:
  `Ran 41 tests in 0.560s`, `OK (skipped=1)`.

## Source evidence and interpretation

Checked official pages at 2026-11-25T07:23–07:25Z:

| Source | Finding |
|---|---|
| [RSS index](https://brickset.com/article/52663/) | Explicit RSS-reader invitation and distinct US/CA Amazon Bargain Watch links. |
| [Keeping up to date](https://brickset.com/article/57700/keeping-up-to-date) | Reaffirms RSS-reader use. |
| [About lead](https://brickset.com/article/52659/) | This exact URL returned a web cache miss on recheck; its About content was available in the earlier review, not newly verified here. |
| [Supplied About slug](https://brickset.com/article/52659/terms-of-use) | Previously resolved to About Brickset; not an RSS license. Affiliate funding was reported there. |
| [API lead](https://brickset.com/article/52666/api-version-3-documentation-terms-of-use) | Actually Brickset web services: separate keyed API, with usage limits and copycat restriction. No API was invoked or key requested. |
| [API documentation](https://brickset.com/article/52664/api-version-3-documentation) | Documentation only; searches for terms/cache did not establish an RSS-specific retention rule. |
| [Robots guidance](https://brickset.com/robots.txt) | Disallows various site areas including `/bargainwatch`, but neither `/feed/amazon/us` nor `/feed/amazon/ca` matches a listed disallow rule. No feed-specific request interval found. |
| [Slickdeals terms](https://corp-site.slickdeals.net/content-list-slickdeals-terms-of-service/) | March 05, 2026 terms still restrict automated access and external offer display without express permission. No Slickdeals service/feed request made by this prototype. |

**Evidence:** Brickset invites personal RSS consumption. **Interpretation for
this task:** one bounded request per market, attributed private metadata display,
and a minimal temporary reader cache are ordinary reader use. This is not derived
from endpoint success or robots silence. No blanket commercial/API license was
required for that narrow operation. No conflicting restriction on these feed
requests was found in the reviewed material.

**Unresolved scope:** no express RSS cache-retention duration, redistribution
right, long-term price-history right, or permanent/public dashboard license was
established. A chosen TTL does not confer rights. About/API guidance is not an
RSS license. Scope was minimized: no raw archive, summaries, table HTML, images,
price history, merchant scraping, API use, redistribution, public preview or
provider contact. F1 Pass in the Brickset-only matrix is limited to this ordinary
temporary reader interpretation, not those broader uses. Slickdeals remains
disabled in all modes; no source was substituted into the original criteria.

## Audit findings and implementation changes

Reviewed exact endpoint allowlisting, redirect rejection, public-IP DNS checking
and pinning, TLS hostname verification, time/size bounds, DTD/entity rejection,
identity, price/currency handling, atomic cache writes, process locking,
synthetic/live separation and HTML escaping.

**Demonstrated defect:** a synthetic description containing 1,200 nested tags
raised `RecursionError` during normalization. Added an explicit XML depth limit
32 and node limit 20,000, now tested to raise a controlled ValueError. Body limit
remains 1 MB. No broad parser/dependency replacement.

**Needed reader additions:**

- [feedcompat.py](./feedcompat.py): a keyword-only Brickset reader scope, without
  changing conservative default permission flags. Slickdeals remains denied even
  with the reader keyword. HTTP diagnostics now include final URL, status, byte
  count and content-encoding where supplied. A normalization hook allows the
  temporary reader to strip content before any disk write. Explicit empty/failure
  preview labels and padded link targets were added for the requested checks.
- [brickset_reader.py](./brickset_reader.py): at most one initial request per
  market, enforced by a locked persistent metadata-only request ledger; no poll,
  automatic retry or follow-up. Binds loopback before fetching, preserving any
  existing listener. Separately owned temporary live cache and preview, at most ten
  records per market, lifetime at most 30 minutes. Actual session was 180 seconds.
- [test_brickset_reader.py](./test_brickset_reader.py): nine focused regressions,
  all synthetic. Tests cover default/Slickdeals guards, deep XML, minimal metadata,
  ten-record bound, disk reload, one-request budget, expiry, preservation of user
  files, mixed-store rejection, failure budget and preview status labels.
- [README.md](./README.md): corrected current gate count, reader scope/retention
  and request-budget instructions, private preview and owner browser checklist.

Original task, original evidence, original test file, synthetic fixtures and ignore
rules were not edited. Baseline copies of three existing files (including the unchanged original test) were
made under the ignored runtime directory before editing.

## Actual live HTTP results

Command (approved execution outside network/socket sandbox):

```sh
python3 compat/v0.0/brickset_reader.py --serve --port 8765 --seconds 180
```

| Fact | US | CA |
|---|---|---|
| Exact requested/final URL | `https://brickset.com/feed/amazon/us` | `https://brickset.com/feed/amazon/ca` |
| Response checked UTC | 2026-11-25T07:28:01.854625+00:00 | 2026-11-25T07:28:02.133637+00:00 |
| Origin status | 200 | 200 |
| Redirects | None | None |
| Content-Type | `text/xml; charset=utf-8` | `text/xml; charset=utf-8` |
| Content-Length | 217838 | 177513 |
| Received bytes | 217838 | 177513 |
| Transport content-encoding | Header absent; identity requested | Header absent; identity requested |
| XML text decoding | UTF-8 decode and parse succeeded | UTF-8 decode and parse succeeded |
| XML declaration diagnostic | `not declared/other` (prefix diagnostic, not an encoding determination) | Same |
| ETag / Last-Modified | Neither supplied | Neither supplied |
| Item count / normalized in memory | 20 / 20 | 20 / 20 |
| Representative inspected / cached | 10 / 10 | 10 / 10 |
| Error category | None | None |

Exactly **one origin GET per market**; zero follow-ups. No extra request to chase
304 or TTL evidence. A live conditional/304 response was **not observed**, and
conditional support is unestablished. The old web-reader XML error was not treated
as an origin status; Codespaces obtained real XML responses directly.

## Representative field-level findings (redacted)

All ten inspected items **in each market** have a title, valid publication date
and absolute article link, with **no native GUID**. All are article aggregations,
not individual product deals. The metadata cache keeps article URL identity scoped
by source/market; no title/price-based merge, row-index identity or invented GUID.

| Sample | US table rows / direct merchant links | CA table rows / direct merchant links |
|---|---:|---:|
| 1 | 23 / 42 | 17 / 30 |
| 2 | 25 / 46 | 20 / 36 |
| 3 | 23 / 42 | 21 / 38 |
| 4 | 25 / 46 | 19 / 34 |
| 5 | 25 / 46 | 20 / 36 |
| 6 | 26 / 48 | 20 / 36 |
| 7 | 25 / 46 | 19 / 34 |
| 8 | 41 / 78 | 25 / 46 |
| 9 | 25 / 46 | 19 / 34 |
| 10 | 21 / 38 | 23 / 42 |

Counts reflect HTML structure, including header/other table rows and repeated
links; they are **not offer counts or independent price checks**. A narrow selector
for absolute Brickset `/sets/` links found zero; that does not establish absence
of set numbers or relative links. No article title, deal payload, item identifier,
affiliate query value or full content is copied into this shareable report.

Normalization coverage: **20 sampled articles, 0 offer rows extracted**. Retaining
article evidence meets this task's conservative option without building a
structured price database. The data contains multiple offer tables/links; this
does not justify assigning one price or product to an article. Set number,
merchant/seller, product price, reference price, comparison basis, currency,
discount, promotion, availability and expiry are not extracted at article level.
Market is CA/US from the confirmed endpoint. Dollar signs/rewards are not price or
discount evidence. All observed article titles are merely source-reported;
verification is `reported`, stock `unknown`, expiry null. The generic record kind
stays `article-or-offer-unknown`; separate live structural findings establish the
observed aggregate semantics without assuming future item structure.

At 07:28:37.182920Z, assertions over actual cached real metadata independently
validated ten records per market, source/market separation, URL identity,
publication dates, reported status, empty summary, null price/expiry, unknown
availability, matching recomputed hashes and revision 1. These were real-data
assertions, separate from the synthetic unittest suite.

## Real cache and retention evidence

Both live cache refreshes returned `updated`. Separate ReaderCache instances
reloaded actual disk state and matched it exactly for each market. At most 20
records total were present; no synthetic source/cards were mixed in. The private
cache contains minimal normalized metadata (title, original URLs/links, scoped
identity, source/market, dates/status, hash/revision), not raw XML or description
HTML. Original links are retained unchanged, bounded to the existing 30 unique
safe links per article. This is a link sample, not exhaustive offer extraction.

`lastAttemptAt` is separate from `lastSuccessAt`; failed refreshes do not change
the latter. The legacy cache timestamps successful observation at the request's
start, not completion, so it can precede the HTTP check by the fetch duration
(about 0.2 seconds here); it is not a precise response-completion timestamp.
Synthetic tests demonstrate unchanged/empty/304 clocks, TTL, last-good preservation,
deduplication, material revisions, reload, lock exclusion, retries and Retry-After.
These behaviors were not manufactured with repeated live requests.

The session uses a newly owned gitignored temporary directory. Normal expiry,
Ctrl+C or SIGTERM cleanup removes it; expiry-on-read also clears its owned state.
No existing user cache or earlier V0.0 runtime data is deleted. The request ledger
retains only attempt/result metadata and redacted structural counts, preventing
accidental repeat live retrieval even after the transient cache is gone.
This is a short-lived reader snapshot, not cross-session historical persistence.
SIGKILL/power loss can leave orphan files; no crash-proof or unattended purge is
claimed. No source-specific retention entitlement is inferred from a TTL.

## Private preview and browser limits

At **2026-11-25T07:28:37.182920Z**, an actual loopback HTTP client asserted:

```text
HTTP status: 200
Live metadata cards: 20
Synthetic fixture cards: 0
Both source/market labels: present
Reported/unknown labels: present
Original canonical links: present and HTML-escaped
Images/scripts: absent
Cache-Control: no-store
Browser rendering: not tested
```

The regression suite checks explicit empty/failure/stale state and safe escaping.
The default synthetic view remains separate. No public port was opened or
forwarding/account configuration changed; no private Codespaces URL is recorded.
Binding succeeded only on loopback port 8765. Subsequent access log GETs do not
establish who opened the preview or any browser/viewport result.

Current tool discovery exposed no browser/desktop tools. `command -v chromium
chromium-browser google-chrome` found none; Playwright package detection returned
False. No browser installation or heavy dependency was attempted. Desktop and
approximately 390px mobile browser rendering, horizontal overflow, readable labels,
tap targets and interactive error state are **Not tested**. CSS, meta tags and HTTP
200 were not counted as rendering evidence; no physical Android claim.

The owner can reproduce the synthetic view with README commands, use the VS Code
Ports panel to open port 8765 with **Visibility: Private**, and follow the supplied
desktop/390px checklist. Real-card browser evidence needs another owner-approved
bounded session after a permitted interval; the completed initial budget is not
silently reset. The actual temporary server stops automatically after 180 seconds.

## Acceptance matrices

Original R2 criteria remain two source families; no implicit gate revision:

| Gate | V0.0 reported | Corrected entering grade | V0.0.1 grade | Basis |
|---|---|---|---|---|
| F1 endpoints / permission scope | Partial | Partial | Partial | Brickset narrow personal-reader scope supported; Slickdeals retrieval/display still blocked. Broader retention/public use unresolved. |
| F2 representative live records, both families | Blocked | Blocked | Partial | Ten real US + ten real CA article samples; zero Slickdeals samples. |
| F3 safe parsing / correct real + synthetic normalization | Partial | Partial | Pass | Actual real article metadata assertions and synthetic RSS/Atom/security tests; no unsupported product/price inference. |
| F4 live disk reload / cache behaviors | Pass | Partial | Pass | Prior synthetic-only Pass corrected. Now both real market snapshots persisted/reloaded in temporary storage; fast cache behaviors simulated; live validators absent, no unnecessary second request. |
| F5 runtime / real browser mobile view | Partial | Partial | Partial | Actual fetch/parse/cache/preview succeeds; desktop/mobile browser check unavailable. |

**Original gates: 2/5 Pass → HOLD.** The historical 1/5 report is retained as
history; its F4 conclusion was overstated at that time. This review does not count
Partial as Pass or treat restricted-source fixtures as live evidence.

Separate **Brickset-only, scoped temporary personal reader** assessment:

| Gate | Grade | CA evidence | US evidence |
|---|---|---|---|
| F1 | Pass (limited scope) | Official indexed endpoint, one bounded private reader request, attributed minimal transient cache | Same, independently requested |
| F2 | Pass | 10 of 20 real articles inspected | 10 of 20 real articles inspected |
| F3 | Pass | Article URL identity, CA, dates/links, unknown product/price fields, safe preview assertions | Article URL identity, US, same checks |
| F4 | Pass | Real temporary disk reload matched; TTL/failure/empty/dedupe simulations pass | Same independent cache source |
| F5 | Partial | Live runtime/HTTP pass; no actual mobile/desktop browser result | Same |

**Brickset-only scoped gates: 4/5 Pass → HOLD pending browser evidence and owner
decision.** A permanent deal/price application, longer retention and public
distribution are outside this scoped assessment.

Smallest next action: owner reviews the narrowed article-reader scope and obtains
actual desktop/390px browser evidence during a separately approved, appropriately
spaced short live session. Then explicitly decide whether to approve a reduced
single-source pilot or revise the release gate. Slickdeals remains a separate
permission blocker for the original two-family objective. No V0.1 work started.

## Exact commands, tests and final state

Relevant commands run from the repository root (approved execution used where
Git writes/network/loopback sockets were sandbox-restricted):

```sh
git status --short --untracked-files=all
git branch --show-current
git rev-parse HEAD
git remote -v
git fetch origin handoff/v0.0.1
git rev-parse FETCH_HEAD
git show --no-patch --format=fuller FETCH_HEAD
git show FETCH_HEAD:CODEX_V0.0.1_BRICKSET_LIVE_COMPATIBILITY.md
find .. -name AGENTS.md -print
cat CODEX_V0.0_FEED_COMPATIBILITY.md compat/v0.0/README.md compat/v0.0/EVIDENCE.md compat/v0.0/.gitignore compat/v0.0/fixtures/rss.xml compat/v0.0/fixtures/atom.xml
cat compat/v0.0/feedcompat.py compat/v0.0/test_feedcompat.py
python3 -m unittest discover -s compat/v0.0 -v
python3 -m unittest discover -s compat/v0.0 -v > compat/v0.0/runtime/baseline-v001.txt 2>&1
curl --max-time 5 --silent --show-error --output /dev/null --write-out 'preview_status=%{http_code}\n' http://127.0.0.1:8765/
mkdir -p compat/v0.0/runtime/v001-baseline
cp compat/v0.0/feedcompat.py compat/v0.0/test_feedcompat.py compat/v0.0/README.md compat/v0.0/runtime/v001-baseline/
python3 -m unittest discover -s compat/v0.0 -v > compat/v0.0/runtime/prelive-v001.txt 2>&1
python3 compat/v0.0/brickset_reader.py --serve --port 8765 --seconds 180
python3 compat/v0.0/runtime/check_v001.py > compat/v0.0/runtime/live-validation-v001.txt
command -v chromium chromium-browser google-chrome
python3 -c "import importlib.util; print('playwright installed:',bool(importlib.util.find_spec('playwright')))"
python3 -m py_compile compat/v0.0/feedcompat.py compat/v0.0/brickset_reader.py compat/v0.0/test_feedcompat.py compat/v0.0/test_brickset_reader.py
diff -u compat/v0.0/runtime/v001-baseline/feedcompat.py compat/v0.0/feedcompat.py
git diff --check
git diff --no-index --check /dev/null compat/v0.0/brickset_reader.py
git diff --no-index --check /dev/null compat/v0.0/test_brickset_reader.py
git check-ignore compat/v0.0/runtime/v001-request-budget/cache.json compat/v0.0/runtime/v001-reader-example/cache.json compat/v0.0/runtime/live-validation-v001.txt
sha256sum CODEX_V0.0_FEED_COMPATIBILITY.md compat/v0.0/EVIDENCE.md compat/v0.0/fixtures/rss.xml compat/v0.0/fixtures/atom.xml
date -u +%FT%TZ
```

Auxiliary reads used `sed`, `head`, `tail`, `find`, `grep` and Git tree inspection;
source edits used the patch tool. The ignored local assertion script read actual
temporary cache data and live loopback HTML in memory, printing only the redacted
validation above. It did not write a live HTML capture. No environment variables,
credentials or live payloads were intentionally printed or added to deliverables.

The final suite command was run before live fetch, after all source changes; only
documentation/evidence changed afterward. **50 discovered, 49 passed, 1 skipped,
0 failures/errors, exit 0; 0.575s.** The skipped general default live test remains
permission-disabled; actual live compatibility was independently tested through
the dedicated reader command and real-cache/HTTP assertions, not credited to that
skip or any fixture. Syntax compilation exited 0. Whitespace checks include
untracked deliverables; final verification follows.


### Captured baseline output (summary)

```text

----------------------------------------------------------------------
Ran 41 tests in 0.560s

OK (skipped=1)
```

### Captured expanded suite output (complete)

```text
test_cache_expires_without_deleting_other_user_files (test_brickset_reader.Reader.test_cache_expires_without_deleting_other_user_files) ... ok
test_default_transport_still_blocked_and_slickdeals_never_enabled (test_brickset_reader.Reader.test_default_transport_still_blocked_and_slickdeals_never_enabled) ... ok
test_failure_is_logged_without_content_and_not_retried (test_brickset_reader.Reader.test_failure_is_logged_without_content_and_not_retried) ... ok
test_metadata_bound_ten (test_brickset_reader.Reader.test_metadata_bound_ten) ... ok
test_mixed_data_rejected (test_brickset_reader.Reader.test_mixed_data_rejected) ... ok
test_preview_status_empty_failure_stale_and_links (test_brickset_reader.Reader.test_preview_status_empty_failure_stale_and_links) ... ok
test_session_persistence_and_one_request_budget (test_brickset_reader.Reader.test_session_persistence_and_one_request_budget) ... ok
test_structure_and_minimum_metadata (test_brickset_reader.Reader.test_structure_and_minimum_metadata) ... ok
test_xml_depth_bound (test_brickset_reader.Reader.test_xml_depth_bound) ... ok
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
test_real_local_http_preview (test_feedcompat.Preview.test_real_local_http_preview) ... 127.0.0.1 - - [25/Nov/2026 07:27:50] "GET / HTTP/1.1" 200 -
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
Ran 50 tests in 0.575s

OK (skipped=1)
```

### Final independent state checks

At 2026-11-25T07:32:40Z the reader command had exited **0**.
`find compat/v0.0/runtime -maxdepth 1 -type d -name 'v001-reader-*' -print` returned no directories: the live session cache was removed. No prior user cache was deleted.

```text
git branch --show-current
compat/v0.0-feed-compatibility
```

```text
git rev-parse HEAD
986d80bb3b43bf1bcbf45837dae133f19f7c8b9c
```

```text
git rev-parse FETCH_HEAD
66e0994c8d08782f3b471488b5b89c8dd6d59f27
```

```text
git status --short --untracked-files=all
?? CODEX_V0.0_FEED_COMPATIBILITY.md
?? compat/v0.0/.gitignore
?? compat/v0.0/EVIDENCE.md
?? compat/v0.0/EVIDENCE_V0.0.1.md
?? compat/v0.0/README.md
?? compat/v0.0/brickset_reader.py
?? compat/v0.0/feedcompat.py
?? compat/v0.0/fixtures/atom.xml
?? compat/v0.0/fixtures/rss.xml
?? compat/v0.0/test_brickset_reader.py
?? compat/v0.0/test_feedcompat.py
```

Current-task changes: modified source and README; added reader module, focused test file and this report. Existing uncommitted files remain untracked; no staging, checkout/switch, reset, clean, merge, commit, push, deployment or cloud/account changes. Fetch only added FETCH_HEAD and the remote-tracking ref.

Preserved original evidence SHA-256: `7a0a21f7543d4e03935519e4b25ed49b30aa1c6498e0f26e644107da61af792d`. Original task SHA-256 remains `4ff074f101d1b56722ce7a2e33761be58f46e5bdd2946a9b554960cb85b97172`. Both fixtures also matched pre-edit checksums; original test matches its baseline copy byte-for-byte.

Final shareable-file review at 2026-11-25T07:33Z covered all 11 untracked files. No prototype whitespace errors or matching credential/private-key signatures found. The read-only original task has pre-existing Markdown trailing spaces and was preserved. Initial review scripting treated the expected no-index difference exit 1 as an error; corrected validation distinguishes it from whitespace diagnostics (exit 3 with output). No source/test change was needed. This pattern scan is not a proof that arbitrary secrets cannot exist. No live payload/title fixtures, raw XML archive, live HTML capture, private preview URL or credentials were added to shareable files. All new runtime paths match the existing ignore rule. The original test matches its baseline copy and zero owned live session directories remain.

The editor diagnostics tool again returned `No client available to run problems`;
this is unavailable tooling, not an editor diagnostic pass. Python compilation
and actual automated/runtime assertions are the validation evidence used here.
