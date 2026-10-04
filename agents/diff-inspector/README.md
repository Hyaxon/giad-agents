# Diff inspector

A model-free starter that requests `git.diff`, reports the retrieved UTF-8 byte
count and changed-file count, and propagates truncation. It provides a practical
check of the broker connection. It does not analyze defects or run tests.

Build the shared image with `make image` from the repository root, then run:

```sh
giad review 42 --repo OWNER/REPO \
  --agent-manifest agents/diff-inspector/agent.manifest.json \
  --config agents/diff-inspector/config.example.toml --json > draft.json
```

The [manifest](agent.manifest.json) requires `git.diff` and
`repository.instructions`. Guidance is declared to support repositories with
AGENTS.md but is not evaluated. The report always states that there was no defect
analysis. Failed diff retrieval, framing, or finish acceptance fails the session.

See the [catalog and setup](../../README.md) and
[implementation](../../src/giad_agents/diff_inspector.py).
