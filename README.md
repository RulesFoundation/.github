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
| [axiom-rules](https://github.com/TheAxiomFoundation/axiom-rules) | RuleSpec compiler and runtime. |
| [axiom-encode](https://github.com/TheAxiomFoundation/axiom-encode) | AI-assisted RuleSpec encoding and validation tooling. |
| [axiom-scrapers](https://github.com/TheAxiomFoundation/axiom-scrapers) | Ingestion tooling for collecting and normalizing legal source text. |

## Rule Repositories

| Repo | Coverage |
| --- | --- |
| [rules-us](https://github.com/TheAxiomFoundation/rules-us) | United States federal rules. |
| [rules-us-ca](https://github.com/TheAxiomFoundation/rules-us-ca) | California rules. |
| [rules-us-ny](https://github.com/TheAxiomFoundation/rules-us-ny) | New York rules. |
| [rules-ca](https://github.com/TheAxiomFoundation/rules-ca) | Canada rules. |

## Shared CI

Jurisdiction rule repositories should keep a small local `validate` workflow that
calls the centralized reusable workflow in this repository:

```yaml
jobs:
  validate:
    uses: TheAxiomFoundation/.github/.github/workflows/validate-rulespec.yml@main
```

By default, the workflow validates RuleSpec YAML under `statutes/`,
`regulations/`, and `policies/`.

The workflow rejects legacy `statute/`, `regulation/`, and `policy/` roots,
old `parameters.yaml` / `tests.yaml` artifacts, YAML fixtures under `tests/`,
and obsolete generated `.rac` artifacts.

## Links

- https://axiom-foundation.org
- hello@axiom-foundation.org
