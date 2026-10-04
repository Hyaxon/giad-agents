# Test summary

A model-free agent that runs host-approved test profiles and summarizes observed
exit status, duration, timeout, truncation, and memory exhaustion. It reports empty
findings because test failures alone do not establish introduced code defects.
GIAD retains the bounded merged output in the draft's `testRuns`.

## Setup

Prepare a trusted project-specific test image containing GIAD's `/giad-test`
helper, the interpreter/toolchain, and all dependencies before review. Follow
[approved test configuration](../../docs/authoring.md#approved-tests).
The shared agent image is separate from that test runner image.

From this repository root:

```sh
make image
mkdir -p config
cp -n agents/test-summary/config.example.toml config/test-summary.toml
```

Edit the test image, command, arguments, and approved `test_profiles` in the local
policy. The placeholder image cannot run tests. No Ollama/model setup is needed.

```sh
giad review 42 --repo OWNER/REPO \
  --agent-manifest agents/test-summary/agent.manifest.json \
  --config config/test-summary.toml --json > draft-tests.json
```

## Coverage and failures

Profiles run in their configured order with duplicate names removed. GIAD permits
at most two test runs per session; additional approved profiles are counted as
unrun. Missing grants/profiles, runner/transport failures, or finish rejection fail
the session. Nonzero exits, timeouts, and memory exhaustion are observed outcomes
that produce an accepted summary describing the failure.

All runs are head-only. A passing profile does not establish that tests existed or
that the code is correct. A failing profile does not establish an introduced
regression. Repository/test text is never executed as instructions by this agent;
only fixed approved profiles run in GIAD's separate sandbox.

See the [manifest](agent.manifest.json), [policy](config.example.toml), and
[implementation](../../src/giad_agents/test_summary.py).

`make sandbox-smoke` verifies this agent against real isolated failing unit tests
and a passing smoke command using the trusted fixture runner. That fixture image
is for repository checks; prepare your own image and policy for real projects.
