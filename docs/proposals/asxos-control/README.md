# asxos-control — staged control-plane files (2026-09-06)

Files destined for the `asxos-control` repository, which does not exist yet.
Staged here so they are reviewable now; James moves them when the repo is created.

Nothing here is applied, and none of it can run from this directory.

| File | Destination |
|---|---|
| `workflows/verify.yml` | `asxos-control/.github/workflows/verify.yml` |
| `product-repo/verify-caller.yml` | `asxos/.github/workflows/verify.yml` |

## Why the verifier is not in this repo

The product checkout is untrusted code. A verifier living in the repo it verifies
can be edited by the same pull request it is verifying, at the PR head — which is
not a verifier. Only control code a product PR cannot reach can produce a
trustworthy status.

This is also why no unfence was needed to do this work: the artifact belongs in
another repo, and the thin caller is a file James applies, which D7 already permits.

## What the pair provides (ACP §5.4)

- `docker run --network none`; non-root; read-only root filesystem; `--cap-drop ALL`;
  `no-new-privileges`; no Docker socket mounted.
- Dependency image identified by **digest**, and the ref refused unless it is a
  40-hex SHA — a branch or tag can move between review and verification, so the
  result would attest to something other than what was read.
- **No secrets.** The reusable workflow declares no `secrets:` block at all, so it
  cannot be passed one and `secrets: inherit` at a call site is inert against it.
- Postgres runs **inside** the test container on loopback when DB tests are enabled.
  A service sidecar would be unreachable under `--network none` — and reaching one
  would mean egress existed.

## The egress negative test

`--network none` is asserted throughout; one step proves it. Before the suite runs,
inside the container: DNS resolution must fail, **and** a raw TCP connect to a
routable literal IP must fail (no DNS involved, so a stubbed resolver cannot fake a
pass). If either succeeds the job fails immediately — an unsandboxed run makes every
result from it untrustworthy, and that failure is otherwise silent.

This complements the in-process guard on `main` (PR #209): that one catches a test
*reaching* for the network; this one catches the sandbox not being a sandbox.

## Before moving them

- Replace `@REPLACE_WITH_COMMIT_SHA` in the caller with the pinned `asxos-control`
  commit. `@main` would let a change there silently alter what this repo's required
  status means.
- Replace `sha256:REPLACE_WITH_IMAGE_DIGEST` with the built image digest.
- The image must contain the `[dev]` extras, `bash`, and — if `run-db-tests: true` —
  a Postgres 16 cluster.
