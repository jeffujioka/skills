---
source:
area: []
project:
related: []
tags:
  - subject/vault/troubleshooting
  - subject/rust/cargo
created: 2026-03-26
---

# error: failed to download from `https://index.crates.io/config.json` (SSL certificate problem)

Seen with: cargo 1.80.0 (checked 2026-03-26)

## Symptom

`cargo install tealdeer` prints `SSL certificate problem: unable to get local issuer certificate`.

## Cause

The corporate proxy re-signs TLS traffic with a CA that cargo does not trust.

## Fix

- Set `CARGO_HTTP_CAINFO` to the bundle that contains the proxy CA.

## Verification

`cargo install tealdeer` finishes without the SSL error.

## Ruled out

- Stale registry index: `cargo update` changed nothing.
