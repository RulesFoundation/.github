# The Axiom Foundation

**The world's rules, encoded.**

Axiom builds open, machine-readable encodings of statutes, regulations, and
policy rules. The durable surface is RuleSpec YAML plus normalized law data; the
tooling is designed for transparent review, deterministic tests, and compiler
validation.

## Core Projects

| Project | Description |
| --- | --- |
| [axiom-foundation.org](https://github.com/TheAxiomFoundation/axiom-foundation.org) | Axiom website and app for navigating encoded law. |
| [axiom-rules-engine](https://github.com/TheAxiomFoundation/axiom-rules-engine) | RuleSpec compiler and runtime. |
| [axiom-encode](https://github.com/TheAxiomFoundation/axiom-encode) | AI-assisted RuleSpec encoding and validation tooling. |
| [axiom-scrapers](https://github.com/TheAxiomFoundation/axiom-scrapers) | Ingestion tooling for collecting and normalizing legal source text. |

## Rule Repositories

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
    uses: TheAxiomFoundation/.github/.github/workflows/validate-rulespec.yml@<published-validation-tag>
    secrets: inherit
```

By default, the workflow validates RuleSpec YAML under `statutes/`,
`regulations/`, and `policies/`.

Use a published validation workflow tag, not `main`; the first release tag for
this rollout is expected to be `rulespec-validate-v1` after the workflow release
PR merges.

Rules repositories should pin their Axiom toolchain in `.axiom/toolchain.toml`:

```toml
[toolchain]
axiom_encode_version = "0.1.0"
axiom_encode_ref = "v0.1.0"
axiom_rules_engine_ref = "v0.1.0"
axiom_corpus_ref = "v0.1.0"
rulespec_us_ref = "v0.1.0"
```

When this file exists, the reusable workflow rejects branch refs such as `main`
and verifies that `axiom_encode_version` matches the checked-out
`axiom-encode` package. Pull requests that change `.axiom/toolchain.toml` or the
caller workflow run full RuleSpec validation rather than changed-file-only
validation, so toolchain bumps expose every file that needs re-encoding.

The workflow rejects singular rule roots, separate parameter or test fixture
files, YAML fixtures under `tests/`, non-RuleSpec YAML outside the approved
roots, obsolete generated formula artifacts, manual RuleSpec YAML edits without
a signed `axiom-encode --apply` manifest, and unclassified PolicyEngine oracle
coverage. Rules repos using this workflow need the
`AXIOM_ENCODE_APPLY_SIGNING_KEY` secret. New executable outputs must either have
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

- https://axiom-foundation.org
- hello@axiom-foundation.org
