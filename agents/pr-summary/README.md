# PR summary

A model-free starter that summarizes the job's PR number, title, and changed-file
count. It does not inspect source, interpret guidance, run tests, or find defects.
An empty findings array represents that limited scope.

Build the shared image with `make image` from the repository root, then run:

```sh
giad review 42 --repo OWNER/REPO \
  --agent-manifest agents/pr-summary/agent.manifest.json \
  --config agents/pr-summary/config.example.toml --json > draft.json
```

The [manifest](agent.manifest.json) declares `repository.instructions` so GIAD can
launch against repositories containing AGENTS.md. This agent does not evaluate
that guidance, and its report states this limitation. No model or test profile is
declared. It waits for host acceptance and fails on rejection or broken framing.

See the [catalog and setup](../../README.md) and
[implementation](../../src/giad_agents/pr_summary.py).
