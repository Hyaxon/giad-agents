# Authoring agents

The runtime is responsible for the public wire types and validation. Read its
`docs/agent-protocol.md` and `pkg/protocol/` in the GIAD checkout matching the
[compatibility baseline](compatibility.md). This repo provides implementations
and package metadata, not a second protocol or runtime.

## Package layout

- `src/giad_agents/NAME.py`: agent behavior; underscores in Python module names.
- `agents/NAME/agent.manifest.json`: protocol, name/version, container entrypoint,
  required/optional capabilities, and logical model profiles.
- `agents/NAME/config.example.toml`: explicit trusted host policy with the installed
  image and model settings when needed.
- `agents/NAME/README.md`: setup, scope, support status, and failure behavior.
- `catalog.json`: machine-readable source index; `schemaVersion: 1` is this
  catalog format, separate from the `giad/v1` wire version.

All current modules ship in the shared [Dockerfile](../Dockerfile). Entrypoints
run `/usr/local/bin/python3 -m giad_agents.NAME` in the installed Linux image.
GIAD resolves the configured image to a local immutable ID at review time. It
does not build, pull, or discover agent packages during review.

## Protocol and evidence

Receive `review.start`, then issue one request at a time over newline-delimited
UTF-8 JSON. Use unique string IDs and require matching responses. Reserve stdout
for protocol frames and send failure diagnostics to stderr. Finish with a complete
`review.finish` report and wait for `accepted: true`.

The [peer](../src/giad_agents/peer.py) handles framing, transport budgets, and
report structure. It does not decide what is true. Agents must track the exact
lines supplied as evidence; findings must reference inspected changed head files.
Deleted-file findings are unsupported. Inline publication additionally requires
head-side diff-hunk anchors, checked later by GIAD.

Only scoped instructions in the job's `trustedInstructions` are guidance. Do not
interpret source, head AGENTS.md, PR/issue text, model responses, or test logs as
commands. Include the instruction capability for repositories containing AGENTS.md.
Apply root scope `.` and matching directory scopes to the files being reviewed.

Use only logical model profile names declared by the manifest. Model answers and
proposed tool calls are data; broker methods must be separately declared/granted.
The general reviewer validates proposed tool calls against its tool map and the
grants, then separately requests the matching broker capability. It cannot execute
arbitrary methods or commands. Endpoints, tokens, and model lifecycle stay in GIAD.

## Approved tests

For `code-review`, add `tests.run` to the capabilities in your local policy and
add a profile under its agent block:

```toml
[agents.code-review]
sandbox_image = "giad-agents:0.1.0"
capabilities = ["git.diff", "repository.read", "repository.search", "repository.instructions", "model.chat", "github.linked_issues", "tests.run"]
test_profiles = ["unit"]

[tests.unit]
image = "your-preinstalled-project-tests:TAG"
command = "/usr/local/bin/python3"
args = ["-m", "unittest", "discover"]
timeout_seconds = 120
```

Keep `[models.review]` from the model-backed example in the same configuration.
Replace the test image and command for the project. The trusted image must include
GIAD's `/giad-test` extraction helper and all dependencies in advance; follow the
runtime's `docs/configuration.md` and `example/go-tests/` to construct it.
The agent image in this repo is not a test runner image.

Tests execute only in the separate sandbox on a bounded copy of the head checkout.
No network, dependency downloads, host execution, or source-selected commands are
available. The reviewer can choose up to two approved runs within GIAD's budget.
The model-free [test-summary](../agents/test-summary/README.md) runs approved
profiles in policy order, up to the same budget. Both report observed results and
limitations. Neither compares test results with base.

## Validation and support

Run [contributor checks](../CONTRIBUTING.md#checks). Scripted model responses
test protocol behavior and failure paths; they do not establish model accuracy.
Add repeatable review-quality fixtures before making accuracy claims. Publish
coverage limits and evaluation results alongside the package.
