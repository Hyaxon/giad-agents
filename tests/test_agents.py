import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from giad_agents.peer import VERSION

ROOT = Path(__file__).resolve().parents[1]


def job(**updates):
    value = {
        "number": 42, "title": "Fix addition", "changedFiles": [],
        "allowedCapabilities": [], "trustedInstructions": [], "testProfiles": [],
    }
    value.update(updates)
    return value


def run_agent(name, start, replies):
    frames = [{"apiVersion": VERSION, "method": "review.start", "params": start}]
    frames += [{"apiVersion": VERSION, "id": str(i), **reply} for i, reply in enumerate(replies, 1)]
    result = subprocess.run(
        [sys.executable, "-m", "giad_agents." + name.replace("-", "_")],
        input="".join(json.dumps(frame) + "\n" for frame in frames),
        capture_output=True, text=True, timeout=10,
        env=dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1"),
    )
    requests = [json.loads(line) for line in result.stdout.split("\n") if line]
    return result, requests


def test_result(profile, exit_code, **updates):
    result = {"profile": profile, "exitCode": exit_code, "output": "observed output", "durationMs": 25,
              "timedOut": False, "truncated": False, "oomKilled": False}
    result.update(updates)
    return result


class AgentTests(unittest.TestCase):
    def test_metadata_needs_only_finish_and_acceptance(self):
        result, requests = run_agent("pr-summary", job(), [{"result": {"accepted": True}}])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["method"] for r in requests], ["review.finish"])
        self.assertEqual(requests[0]["params"]["findings"], [])
        self.assertIn("Metadata only", requests[0]["params"]["limitations"])

    def test_finish_rejection_fails(self):
        for reply in ({"error": "rejected"}, {"result": {"accepted": False}}):
            with self.subTest(reply=reply):
                result, _ = run_agent("pr-summary", job(), [reply])
                self.assertNotEqual(result.returncode, 0)

    def test_diff_reports_utf8_bytes_and_truncation(self):
        result, requests = run_agent("diff-inspector", job(), [
            {"result": {"Text": "é\n", "Truncated": True, "SkippedFiles": 0}},
            {"result": {"accepted": True}},
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("3 bytes", requests[-1]["params"]["summary"])
        self.assertIn("truncated", requests[-1]["params"]["limitations"])

    def test_failed_diff_does_not_finish(self):
        result, requests = run_agent("diff-inspector", job(), [{"error": "unavailable"}])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([r["method"] for r in requests], ["git.diff"])

    def test_test_summary_reports_pass_fail_and_unrun_profiles(self):
        start = job(allowedCapabilities=["tests.run"], testProfiles=["unit", "unit", "integration", "extra"])
        results = [test_result("unit", 0), test_result("integration", 1, truncated=True)]
        result, requests = run_agent("test-summary", start, [
            *[{"result": r} for r in results], {"result": {"accepted": True}},
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([r["params"]["profile"] for r in requests[:-1]], ["unit", "integration"])
        report = requests[-1]["params"]
        self.assertIn("unit: PASSED", report["summary"])
        self.assertIn("integration: FAILED", report["summary"])
        self.assertIn("1 additional approved profiles were not run", report["limitations"])
        self.assertIn("truncated", report["limitations"])
        self.assertEqual(report["findings"], [])

    def test_test_summary_reports_timeout_and_memory_exhaustion(self):
        result, requests = run_agent("test-summary", job(allowedCapabilities=["tests.run"], testProfiles=["slow", "large"]), [
            {"result": test_result("slow", None, timedOut=True)},
            {"result": test_result("large", 137, oomKilled=True)},
            {"result": {"accepted": True}},
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("TIMED OUT", requests[-1]["params"]["summary"])
        self.assertIn("OUT OF MEMORY", requests[-1]["params"]["summary"])

    def test_test_summary_cannot_report_success_without_approved_tests(self):
        for start in (job(), job(allowedCapabilities=["tests.run"]), job(testProfiles=["unit"])):
            with self.subTest(start=start):
                result, requests = run_agent("test-summary", start, [])
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(requests, [])

    def test_test_summary_transport_failure_does_not_finish(self):
        result, requests = run_agent("test-summary", job(allowedCapabilities=["tests.run"], testProfiles=["unit"]), [
            {"error": "test runner unavailable"},
        ])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual([r["method"] for r in requests], ["tests.run"])


if __name__ == "__main__":
    unittest.main()
