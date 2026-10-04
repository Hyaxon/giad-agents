# Compatibility

The initial packages target GIAD `1.0.0` and the public `giad/v1` contract.
The tested source baseline is recorded in [compatibility.json](../compatibility.json):

- Repository: `git@github.com:Hyaxon/giad.git`.
- Revision: `71a66e8849ed83a7945c23973b35dbd6131eb3a3`.
- Source checkout: the GIAD repository whose module is `github.com/hyaxon/giad`.

This collection is maintained separately at `Hyaxon/giad-agents`.
Old `agentic-review/v1` frames and manifests are incompatible.

## Checks

`make smoke GIAD_DIR=/path/to/giad` overlays the
[integration suite](../tests/integration/official_agents_test.go) into the runtime
package. This exercises real manifest loading, grants, repository reads, finding
validation, model lifecycle, and completion using trusted test processes and
scripted model answers. It neither modifies the checkout nor contacts GitHub
or Ollama.

`make sandbox-smoke` uses the same suite through GIAD's real Docker launcher and
the installed shared agent image. It exercises non-root, network-free, read-only
agent execution and cleanup. Reviewer judgments and most test evidence are
scripted. An additional test-summary integration uses real separate test
containers and verifies one failed unit-test profile and one passing smoke profile.
`make sandbox-smoke` builds the trusted Python fixture test image for this check;
project-specific test images still require their own validation.

The Python checks cover framing failures, evidence clipping, report validation,
coverage limits, and catalog/package consistency. These checks establish runtime
compatibility and failure behavior, not the quality of a real model's judgment.

CI uses the pinned runtime revision above. Recheck and update this baseline
explicitly when adopting runtime changes; incompatible wire changes require
new agent compatibility metadata and a new protocol version in GIAD.
