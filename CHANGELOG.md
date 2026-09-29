# Veto Changelog

Plain-English notes on what changed in Veto, most recent first.

## v1.0.0 — 2026-09-29

Initial public release of Veto MCP.

Listing fetches, robots.txt checks, apply-page hops, and webhook delivery refuse private and metadata destinations. Each outbound connect uses an address that already passed that check, so the hostname cannot change between the check and the request. Application CSV exports and saved HTML files stay inside the workspace. Webhook delivery requires an explicit https host list and does not follow a redirect until the next URL passes the same rules. Python packages are pinned to exact versions.
