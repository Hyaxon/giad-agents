# GIAD Agents

The official starter agent collection and source catalog for GIAD, the
self-hosted runtime for programmable code-review agents. Build custom agents to
audit, review, and engage with GitHub PRs, with models or deterministic logic.
Agents supply review judgment over `giad/v1`; GIAD owns GitHub access, repository
tools, models, sandboxed tests, and separately confirmed publication.

This initial collection is version `0.1.0`. Packages are maintained here, built
locally into one trusted Linux image, and selected with explicit manifests and
host policy. The catalog is a source index; GIAD does not discover or install it
automatically. No container registry release is published yet.
Official status grants no extra access: these agents use the same public protocol
and explicit host capability policy as third-party packages.

## Catalog

| Agent | Model | Purpose | Status |
| --- | --- | --- | --- |
| [pr-summary](agents/pr-summary/README.md) | None | Summarize PR metadata; no defect analysis | Starter |
| [diff-inspector](agents/diff-inspector/README.md) | None | Verify diff retrieval and report coverage; no defect analysis | Starter |
| [test-summary](agents/test-summary/README.md) | None | Run approved test profiles and summarize observed results | Starter |
| [code-review](agents/code-review/README.md) | Ollama | General PR review with adaptive evidence gathering | Model judgment needs evaluation |

[catalog.json](catalog.json) records package paths, versions, compatibility,
maintainer, and image. All four packages use `giad-agents:0.1.0`.
The [compatibility reference](docs/compatibility.md) records the tested GIAD baseline.

## First draft

Prerequisites: a built GIAD CLI, GitHub authentication configured in GIAD, and a
running Linux Docker engine. GIAD v1 supports Linux amd64 and macOS Apple Silicon;
follow the runtime's own setup guide for host requirements. Python 3.11+ is needed
only for development checks; Python is included in the image.

Clone over SSH and build the installed agent image:

```sh
git clone git@github.com:Hyaxon/giad-agents.git
cd giad-agents
make image
```

From this repository root, with the GIAD CLI on `PATH`:

```sh
giad auth status
giad review 42 --repo OWNER/REPO \
  --agent-manifest agents/diff-inspector/agent.manifest.json \
  --config agents/diff-inspector/config.example.toml --json > draft.json
```

Replace `42` and `OWNER/REPO`. The diff inspector returns a draft with empty
findings and explicit limitations. It verifies the broker connection and does
not analyze defects. `review` does not publish anything.

For the model-backed reviewer, follow its
[model setup](agents/code-review/README.md). To use GitHub App authentication,
pass your trusted `--identity /absolute/path/identity.toml` to each GIAD command.

For a model-free summary of observed tests, configure a trusted project-specific
test image and follow [test-summary setup](agents/test-summary/README.md).

Inspect a draft and publication preview before using the confirmation hash:

```sh
giad publish draft.json
giad publish draft.json --confirm HASH
```

These commands publish a `COMMENT` review. Use `--inline` in both commands only
when findings anchor head-side diff lines; use `--event REQUEST_CHANGES` in both
when requesting changes. GIAD checks revisions, anchors, and confirmation.
Agents have no publication capability.

## Development

```sh
make check                         # Offline tests and catalog/link checks.
make lint                          # Markdown lint; requires Node.js.
make smoke GIAD_DIR=../giad         # Real GIAD broker, scripted model, no GitHub.
make image                         # Trusted image, explicit build step.
make sandbox-smoke GIAD_DIR=../giad # Real broker, agent containers, and fixture tests.
```

The integration checks require a GIAD source checkout and its Go toolchain.
They overlay tests into that checkout without changing its files. Host execution
is used only by offline tests. CLI reviews always use GIAD's Docker isolation.
CI runs the same checks against the pinned compatibility baseline.

See [authoring](docs/authoring.md), [contributing](CONTRIBUTING.md), and
[repository instructions](AGENTS.md). Changes to the runtime belong in GIAD;
specialist prompts and review behavior belong here.

## Planned features

See the [agent roadmap](docs/roadmap.md) for templates, evaluation, and planned
reviewers. Setup, tools, and automation belong in
[GIAD's roadmap](https://github.com/Hyaxon/giad/blob/main/docs/roadmap.md).

## License

[Apache License 2.0](LICENSE). Starter implementations are adapted from GIAD's
protocol examples; see [NOTICE](NOTICE).
