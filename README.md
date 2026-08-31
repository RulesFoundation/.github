# The Axiom Foundation

**The world's rules, encoded.**

Axiom builds open, machine-readable encodings of statutes, regulations, and
policy rules. The durable surface is RuleSpec YAML plus normalized law data; the
tooling is designed for transparent review, deterministic tests, and compiler
validation.

## Core Projects

| Project | Description |
| --- | --- |
| [axiom.org](https://github.com/TheAxiomFoundation/axiom.org) | Axiom website and app for navigating encoded law. |
| [axiom-rules-engine](https://github.com/TheAxiomFoundation/axiom-rules-engine) | RuleSpec compiler and runtime. |
| [axiom-encode](https://github.com/TheAxiomFoundation/axiom-encode) | AI-assisted RuleSpec encoding and validation tooling. |
| [axiom-scrapers](https://github.com/TheAxiomFoundation/axiom-scrapers) | Ingestion tooling for collecting and normalizing legal source text. |

## Rule repositories

| Repo | Coverage |
| --- | --- |
| [rulespec-us](https://github.com/TheAxiomFoundation/rulespec-us) | United States federal rules. |
| [rulespec-us-ca](https://github.com/TheAxiomFoundation/rulespec-us-ca) | California rules. |
| [rulespec-us-ny](https://github.com/TheAxiomFoundation/rulespec-us-ny) | New York rules. |
| [rulespec-ca](https://github.com/TheAxiomFoundation/rulespec-ca) | Canada rules. |

## Shared CI

Jurisdiction rule repositories should keep a small local `validate` workflow that
calls the centralized reusable workflow in this repository:

```yaml
jobs:
  validate:
    uses: TheAxiomFoundation/.github/.github/workflows/validate-rulespec.yml@<workflow-commit-sha>
    with:
      axiom-encode-ref: <40-character-commit-sha>
      axiom-rules-engine-ref: <40-character-commit-sha>
      axiom-corpus-ref: <40-character-commit-sha>
      rulespec-us-ref: <40-character-commit-sha>
      corpus-release-base-url: <https-r2-bucket-base-url>
```

By default, the workflow validates RuleSpec YAML under `statutes/`,
`regulations/`, and `policies/`.

Pin the reusable workflow itself by commit SHA. The workflow accepts no mutable
dependency refs: each dependency input must be a full commit SHA, and the
checked-out commit must be an ancestor of that repository's remotely advertised
default branch. Format-only ref validation is not sufficient.

Rules repositories should pin their Axiom toolchain in `.axiom/toolchain.toml`:

```toml
[toolchain]
axiom_corpus_release = "us-rulespec-2026-07-10"
axiom_corpus_release_content_sha256 = "<64-character-lowercase-sha256>"
validation_waiver_set_sha256 = "<sha256-of-exact-known-validation-gaps.yaml-bytes>"
```

This table is mandatory and must contain exactly those three keys. The workflow
does not accept dependency refs, versions, selector aliases, or nested ref
tables in it. Before running the encoder, the workflow downloads the exact
signed object from
`<corpus-release-base-url>/releases/<name>/<content_sha256>.json` into the
corpus checkout's matching `releases/<name>/<content_sha256>.json` path. It
checks the content address and release name immediately; the protected
verification supervisor then verifies its Ed25519 signature and supplies all
three public trust roots without exposing signing capability.

Configure those protected roots as `AXIOM_ENCODE_APPLY_SIGNING_PUBLIC_KEY`,
`AXIOM_ENCODE_EVAL_SIGNING_PUBLIC_KEY`, and
`AXIOM_CORPUS_RELEASE_PUBLIC_KEY` organization or repository variables. They
are deliberately not workflow-call inputs, so a caller change cannot replace
its own verification roots.

`known-validation-gaps.yaml` is mandatory and its exact bytes must hash to
`validation_waiver_set_sha256`. On a pull request, the encoder's typed waiver
audit compares it with the protected base revision. One new `pending` approval
is permitted only in a pull request that changes exactly
`known-validation-gaps.yaml` and `.axiom/toolchain.toml`; both revisions must
bind their exact waiver bytes, and the digest value must be the toolchain's only
byte change. The new pending field may approve a module that has no existing
waiver entry, producing a pending-only module. A later pull request may consume
the exact, unexpired pending record into active on that same module, either
initializing a pending-only module or replacing its existing active state. That
consumption is valid only when one changed, surviving, signed v5 model manifest
authenticates the consumed module and the changed paths are exactly the waiver,
toolchain, manifest, and every changed manifest-listed applied file. The
pending state must be removed and every other module and state preserved.
Waiver/toolchain-only activation, unsigned or stale manifests, deletions,
unlisted modules, unrelated paths, batches, and composite transitions fail
closed. All other new or broadened waivers are rejected; entries may otherwise
only be removed.

This draft is pinned to reviewed core candidate
`10accbfb2a671efc6bd2beb6a23db953d259d8c2` (`axiom-encode` `0.2.1752`), stacked
after optional-inventory PR #1566. Do not merge or roll out this workflow until
that core is on the protected default branch under its final immutable SHA and
this pin has been reverified. The workflow freezes the event base and head to
commit objects, materializes the protected waiver and toolchain only from exact
bounded `100644 blob` objects, proves the checkout's head bytes match its frozen
commit, and preserves changed paths as bounded NUL-v1 bytes. The core
independently re-proves the same evidence through this exact interface (all
flags are required and unknown or missing flags fail):

```text
validation-waivers audit \
  --root <rules-repository> \
  --corpus-path <corpus-checkout> \
  --protected-base <raw-base-known-validation-gaps.yaml> \
  --protected-base-toolchain <raw-base-.axiom/toolchain.toml> \
  --changed-paths <NUL-v1-path-list> \
  --changed-paths-format nul-v1 \
  --partition-key <matrix-partition> \
  --partition-keys-json <all-matrix-partitions> \
  --axiom-rules-engine-path <rules-engine-checkout>
```

That audit enforces both exact same-module activation forms,
`{pending: metadata} -> {active: metadata}` and
`{active: old_metadata, pending: metadata} -> {active: metadata}`, along with
future expiry at evaluation time, no mixed transition, no other semantic
change, both waiver/toolchain digest bindings, the authenticated signed-manifest
generated closure, exact transition path scope, and digest-only toolchain
mutation from the raw base and head bytes. The exact authorized pre-toolchain
rulespec-us PR #911 bootstrap remains a narrowly proven migration exception and
does not enter the core transition path. Callers must repin the final encoder
commit and this workflow commit together. Before
relying on the ratchet, each caller must also migrate off
`validate-rulespec-legacy-pending-safe.yml` and configure its protected branch
to require the pull request branch to be up to date or to merge through a merge
queue; otherwise an event-time base SHA can become stale before merge. A
toolchain or caller-workflow change runs full RuleSpec validation so a release
or waiver-set change cannot hide behind changed-file selection.

Outside one exact pending creation or activation, the inline ratchet is
intentionally a decrement-only semantic guard: a waiver removal or semantic
no-op does not use the transition-only two-path and digest-splice restrictions.
It still cannot add or change any retained active or pending record, the head
waiver bytes must match the head toolchain digest, and the core audit runs on
every non-bootstrap outcome and every matrix shard. For activation, the inline
guard requires the waiver/toolchain pair, consumed module, and exactly one
encoding-manifest path; the core supplies the authoritative signature and exact
generated-closure proof. This is an accepted fail-closed design, not a
transition bypass.

The workflow rejects singular rule roots, separate parameter or test fixture
files, YAML fixtures under `tests/`, non-RuleSpec YAML outside the approved
roots, obsolete generated formula artifacts, manual RuleSpec YAML edits without
an Ed25519-signed `axiom-encode --apply` manifest, and unclassified PolicyEngine
oracle coverage. New executable outputs must either have
an exact PolicyEngine mapping or a harness-side `not_comparable` classification
with a rationale.

The guard also rejects a `backend: manual` apply manifest that introduces a
*new* rule file unless it declares `manual_exception: composition | repair |
fixtures | <issue-ref>`. Net-new statutory encoding must come from an encoder
run; hand-authoring stays legal only for composition/oracle plumbing,
validator-driven repairs, and fixtures, and only by declaring itself. Attest
encoder output committed outside the `--apply` flow with `axiom-encode
sign-applied-files` (add `--manual-exception` for new files, or `--all` to
backfill a corpus that has no manifests). `axiom-encode manifest-census`
reports each repo's encoder-generated / manual / unmanifested coverage.

Set `guard-programs-root: true` on the caller to require manifests on the
composed-pilot `programs/` root too (default `false`). Enable it per repo only
after every existing `programs/` file has a manifest or manual attestation,
otherwise the guard fails on the backlog.

Repos can opt into stricter structure checks by adding
`.axiom/repository-structure.yaml`. When present, the reusable workflow treats it
as the source of truth for allowed top-level directories, allowed top-level
files, and per-folder file extensions or sentinel filenames. This is intended
for country repos that need to keep executable oracle adapters, generated
outputs, and source dumps out of the RuleSpec corpus:

```yaml
version: 1
allowed_root_directories:
  - .axiom
  - .github
  - data
  - nz
  - tests
allowed_root_files:
  - .gitignore
  - CLAUDE.md
  - README.md
  - known-validation-gaps.yaml
  - variables.toml
path_rules:
  - patterns: [".axiom/**"]
    allow_extensions: [".toml", ".yaml"]
  - patterns: [".github/**"]
    allow_extensions: [".yml", ".yaml"]
  - patterns: ["data/**"]
    allow_extensions: [".json", ".jsonl", ".yaml", ".yml"]
  - patterns: ["nz/**"]
    allow_extensions: [".yaml"]
    allow_filenames: [".gitkeep"]
  - patterns: ["tests/**"]
    allow_extensions: [".py"]
```

## Links

- https://axiom.org
- hello@axiom.org
