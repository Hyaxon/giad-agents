import importlib.util
import json
from pathlib import Path
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CatalogTests(unittest.TestCase):
    def test_ci_uses_recorded_runtime_baseline(self):
        baseline = json.loads((ROOT / "compatibility.json").read_text())
        workflow = (ROOT / ".github/workflows/ci.yml").read_text()
        self.assertEqual(baseline["protocol"], "giad/v1")
        self.assertRegex(baseline["revision"], r"^[a-f0-9]{40}$")
        repository = baseline["repository"].removeprefix("git@github.com:").removesuffix(".git")
        self.assertIn("repository: " + repository, workflow)
        self.assertIn("ref: " + baseline["revision"], workflow)

    def test_packages_match_catalog_manifest_and_host_policy(self):
        catalog = json.loads((ROOT / "catalog.json").read_text())
        self.assertEqual(catalog["schemaVersion"], 1)
        version = (ROOT / "VERSION").read_text().strip()
        names = [entry["name"] for entry in catalog["agents"]]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(set(names), {p.name for p in (ROOT / "agents").iterdir() if p.is_dir()})
        for entry in catalog["agents"]:
            with self.subTest(agent=entry["name"]):
                manifest = json.loads((ROOT / entry["manifest"]).read_text())
                config = tomllib.loads((ROOT / entry["configuration"]).read_text())
                policy = config["agents"][entry["name"]]
                self.assertTrue((ROOT / entry["documentation"]).is_file())
                self.assertEqual(manifest["name"], entry["name"])
                self.assertEqual(manifest["version"], version)
                self.assertEqual(entry["version"], version)
                self.assertEqual(manifest["apiVersion"], entry["protocol"])
                self.assertEqual(entry["protocol"], "giad/v1")
                self.assertEqual(policy["sandbox_image"], entry["image"])
                self.assertEqual(entry["image"], "giad-agents:" + version)
                self.assertTrue(set(manifest["capabilities"]["required"]) <= set(policy["capabilities"]))
                self.assertTrue(set(policy["capabilities"]) <= set(manifest["capabilities"]["required"] + manifest["capabilities"]["optional"]))
                self.assertEqual(set(config.get("models", {})), set(manifest["modelProfiles"]))
                self.assertEqual(manifest["entrypoint"]["command"], "/usr/local/bin/python3")
                self.assertEqual(manifest["entrypoint"]["args"][0], "-m")
                self.assertIsNotNone(importlib.util.find_spec(manifest["entrypoint"]["args"][1]))

    def test_local_markdown_links_exist(self):
        paths = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "AGENTS.md"]
        paths += list((ROOT / "agents").rglob("*.md")) + list((ROOT / "docs").rglob("*.md"))
        for path in paths:
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text()):
                if "://" in target or target.startswith("#"):
                    continue
                target = target.split("#", 1)[0]
                with self.subTest(path=path.relative_to(ROOT), target=target):
                    self.assertTrue((path.parent / target).is_file(), "broken local Markdown link")


if __name__ == "__main__":
    unittest.main()
