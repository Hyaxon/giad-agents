"""Check or update GIAD's bundled mirror of the official general reviewer."""

import argparse
import json
from pathlib import Path
import shutil
import tomllib

FILES = ("__init__.py", "peer.py", "code_review.py")
METADATA = ("apiVersion", "name", "version", "capabilities", "modelProfiles")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", required=True, type=Path)
    parser.add_argument("--write", action="store_true", help="Copy official source and matching manifest metadata")
    args = parser.parse_args()
    runtime = args.runtime.resolve()
    root = Path(__file__).resolve().parents[1]
    target = runtime / "example/code-review"
    if not (runtime / "internal/agents/session.go").is_file() or not (target / "agent.manifest.json").is_file():
        parser.error("--runtime must point to a GIAD source checkout containing the code-review example")
    manifest = json.loads((root / "agents/code-review/agent.manifest.json").read_text())
    example = json.loads((target / "agent.manifest.json").read_text())
    differences = []
    for name in FILES:
        source, destination = root / "src/giad_agents" / name, target / "giad_agents" / name
        if args.write:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        if not destination.is_file() or destination.read_bytes() != source.read_bytes():
            differences.append("source: " + name)
    if args.write:
        for key in METADATA:
            example[key] = manifest[key]
        (target / "agent.manifest.json").write_text(json.dumps(example, indent=2) + "\n")
    for key in METADATA:
        if example[key] != manifest[key]:
            differences.append("manifest: " + key)
    config = tomllib.loads((target / "config.toml").read_text())
    policy = set(config["agents"]["code-review"]["capabilities"])
    for capability in manifest["capabilities"]["required"]:
        if capability not in policy:
            differences.append("example policy missing required grant: " + capability)
    for profile in manifest["modelProfiles"]:
        if profile not in config.get("models", {}):
            differences.append("example policy missing model profile: " + profile)
    if differences:
        print("Reviewer mirror differs:\n" + "\n".join(differences))
        return 1
    print("GIAD example matches official reviewer source, manifest metadata, and required policy grants.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
