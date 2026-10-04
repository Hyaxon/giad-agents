# Code review

A general model-backed PR reviewer with an adaptive evidence-gathering loop. It
reviews correctness, security, API compatibility, performance, concurrency,
migrations, configuration, tests, documentation, and operational impact as relevant.
It can inspect arbitrary source ranges and follow callers/dependencies across
changed and unchanged files. Its model judgment still needs quality evaluation.

## Setup

Start Ollama on the GIAD host and choose an exact model tag already installed.
From this repository root:

```sh
make image
mkdir -p config
cp -n agents/code-review/config.example.toml config/code-review.toml
ollama list
```

Edit `models.review.model` in `config/code-review.toml` to an installed model that
supports tool calls; the placeholder cannot run a review. The default endpoint is the host's local Ollama service. The model
endpoint and credentials stay in GIAD, outside the agent container.

```sh
giad review 42 --repo OWNER/REPO \
  --agent-manifest agents/code-review/agent.manifest.json \
  --config config/code-review.toml --json > draft.json
```

Inspect the draft before using GIAD's separate publication commands in the
[main setup](../../README.md). Model-free agents do not need Ollama.

## Coverage and failures

The model plans from the PR intent, complete change inventory, and available diff.
It can read any head source range, search for callers/tests, consult linked issues,
retrieve paginated context, and request approved tests. There is no three-file,
160-line, 12 KiB evidence, or per-file finding cutoff. Renames use head paths;
deleted changes can be inspected through diff evidence but cannot anchor findings.

Evidence is fitted to the actual remaining conversation space. Clipped reads keep
complete numbered lines and provide `nextStart`; cached context pages provide
`nextOffset`. Large inventories, PR bodies, diffs, issue context, test results, and
the coverage index remain available through `review_context`. Earlier complete
conversation turns can be evicted to fit context; trusted scoped guidance remains,
and evidence can be reread. The latest tool turn is never silently dropped.

GIAD's own ceilings still apply: 64 broker requests, 16 model calls, 96 KiB per
model request, two test runs, and 20 findings total. Repository tool outputs and
the model provider also have runtime limits. The agent reserves a finalization
request and asks for a report when research budgets end. These are runtime safety
and resource budgets, rather than a fixed selection of files or lines.

Findings must anchor lines actually supplied to the model, use the complete
`giad/v1` fields, and pass size/type checks. Search matches and unchanged files
cannot supply finding anchors. Invalid reports receive feedback and can be repaired
within the remaining model budget. No valid report by the deadline/budget, model
transport failure, or finish rejection fails the session. The agent records source
coverage, unread changed files, incomplete diff context, tool errors, context
eviction, and observed test coverage independently of the model's claims.

Only `trustedInstructions` from the pinned base is guidance, filtered by scope.
Source, filenames, diffs, PR/issue text, model answers, and test output are evidence.
The prompt instructs the model not to follow instructions embedded in evidence;
this does not establish immunity to prompt injection or factual correctness.

## Optional tests

The [manifest](agent.manifest.json) declares `tests.run` as optional. See
[approved test configuration](../../docs/authoring.md#approved-tests) to enable it.
The model can select approved profiles as needed, up to GIAD's two-run budget.
Results are returned as evidence and cached for paginated retrieval. Arbitrary
commands and unapproved profiles are rejected before any test request is sent.

Tests are head-only. Failure alone does not establish an introduced regression;
passing tests do not prove that tests exist or that the code is correct. This
repository does not install a test image or fetch project dependencies.

See the [implementation](../../src/giad_agents/code_review.py) and
[compatibility checks](../../docs/compatibility.md).
