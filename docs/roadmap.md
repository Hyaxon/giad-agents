# Agent roadmap

This document describes potential official agent packages and collection work,
not available agents or a release schedule. The
[current catalog](../README.md#catalog) contains only the implemented
`pr-summary`, `diff-inspector`, `test-summary`, and `code-review` starters.
The existing general reviewer remains useful independently of the proposals below.

Runtime features such as local/range reviews, scheduling, web access, MCP,
installation, and distributed workers belong in the
[GIAD runtime roadmap](https://github.com/Hyaxon/giad/blob/main/docs/roadmap.md).
Official agents use the same public protocol and permission system as third-party
agents, with no privileged access. Proposed capabilities must be implemented and
explicitly granted by GIAD before an agent can use them.

## MAGI composite reviewer

Explore complementary review passes rather than a replacement runtime:

- **MELCHIOR:** correctness, logic, error handling, and behavioral regressions.
- **BALTHASAR:** requirements, linked issue intent, integration, and compatibility.
- **CASPER:** adversarial cases, security boundaries, and performance risks.

Evaluate how to combine evidence, disagreements, confidence, and duplicate findings
into one actionable report. Define whether passes run inside one composite package
or use future multi-agent orchestration. Sequential operation should suit smaller
machines; concurrent passes would depend on GIAD's resource-aware scheduling.
Logical model profiles can let passes use different host-configured models.
No pass should require a finding quota or hide incomplete coverage.

## Test Writer

Inspect behavioral changes and repository testing conventions to suggest or
generate focused tests. Explain the behavior each test checks and distinguish
proposed tests from tests that were actually executed.

Optional validation would apply generated patches only in a temporary test
workspace through a future approved runtime mechanism, then use sandboxed test
profiles. Current `tests.run` runs existing head tests; it cannot accept generated
patches or arbitrary commands. The existing `test-summary` reports observed runs
and does not generate tests. Include base/head comparisons when GIAD supports them.

## Wacht / CVE reviewer

Review dependency manifest and lockfile changes against current vulnerability
data. Match the ecosystem, resolved version, affected range, and relevant usage;
cite advisory sources and distinguish newly introduced vulnerabilities from
existing debt. Report unavailable or stale data as a coverage limitation.

Prefer a future curated `vulnerabilities.lookup` capability over broad web access.
Any necessary external research must use host-granted broker tools; agents receive
neither direct network access nor credentials. Runtime path filters could select
this agent when dependency files change. The package name and supported ecosystems
remain proposals, and neither lookup capability nor reviewer ships today.

## Other software-engineering agents

Potential packages include deterministic/static-analysis or hybrid reviewers,
security audits beyond dependency CVEs, API compatibility checks, documentation
review, repository audits, and onboarding/developer-experience analysis.
Define concrete evidence requirements, actionable outputs, and evaluations for
each package. Work outside PR review depends on GIAD supporting the appropriate
job context and report types; agents do not implement their own execution host.

## Collection quality and distribution

- **Evaluation:** defect and false-positive fixtures, coverage measurements, and
  published limitations for model-based and deterministic reviewers. Protocol
  integration tests alone do not establish review quality.
- **Catalog growth:** add packages only once implementations, manifests, granted
  capability examples, compatibility baselines, documentation, and maintainer/
  support information exist. Keep proposed agents out of `catalog.json`.
- **Releases:** published, versioned images and repeatable release checks before
  claiming registry availability. Catalog metadata can support a future GIAD
  installer; installation and trust policy remain runtime responsibilities.
