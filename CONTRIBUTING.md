# Contributing

This repository maintains official GIAD agent packages and their source catalog.
Keep runtime/authentication/sandbox/publication changes in GIAD. Agent prompts,
review strategies, and package-specific evaluation belong here.

## Add or change an agent

1. Follow [authoring](docs/authoring.md) and the tested `giad/v1` contract.
2. Add an implementation, explicit manifest, example policy, and agent README.
3. Add the package to [catalog.json](catalog.json) and the main README table.
4. Describe capabilities, model profiles, actual coverage, failure behavior,
   maintainer, and support status. Label experimental judgment honestly.
5. Add tests for meaningful behavior and protocol failures. For review-quality
   claims, supply repeatable defect/false-positive fixtures and evaluation results.

All packages currently share one image and the version in [VERSION](VERSION).
Update catalog entries, manifests, configs, and documented tags together when
releasing. Do not claim a registry image exists before it has been published.
An automated publishing or installation workflow is outside this initial setup.

## Checks

Use Python 3.11+, Node.js for Markdown lint, and GIAD's Go toolchain for integration:

```sh
make check
make lint
make smoke GIAD_DIR=../giad
make image
make sandbox-smoke GIAD_DIR=../giad
```

Container or packaged-agent changes require real Docker integration. State which
checks ran and explain unavailable checks. Keep generated drafts, keys, identity
files, and personal configuration out of commits. A failed model/session must not
be reported as a successful clean review.
