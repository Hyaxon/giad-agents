"""Overlay integration tests into a GIAD checkout without modifying its files."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--docker-image")
    parser.add_argument("--test-image")
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    root = Path(__file__).resolve().parents[1]
    if not (runtime / "internal/agents/session.go").is_file():
        parser.error("--runtime must point to a GIAD source checkout")
    env = dict(os.environ, GIAD_OFFICIAL_AGENTS_ROOT=str(root), GIAD_OFFICIAL_PYTHON=sys.executable)
    if args.docker_image:
        env["GIAD_OFFICIAL_IMAGE"] = args.docker_image
    else:
        env.pop("GIAD_OFFICIAL_IMAGE", None)
    if args.test_image:
        env["GIAD_OFFICIAL_TEST_IMAGE"] = args.test_image
    else:
        env.pop("GIAD_OFFICIAL_TEST_IMAGE", None)
    with tempfile.TemporaryDirectory(prefix="giad-agents-smoke-") as scratch:
        overlay = Path(scratch) / "overlay.json"
        overlay.write_text(json.dumps({"Replace": {
            str(runtime / "internal/agents/official_agents_test.go"):
            str(root / "tests/integration/official_agents_test.go"),
        }}))
        result = subprocess.run([
            "go", "test", "-race", "-count=1", "-overlay=" + str(overlay),
            "./internal/agents", "-run", "^TestOfficialAgents", "-v",
        ], cwd=runtime, env=env, check=False)
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
