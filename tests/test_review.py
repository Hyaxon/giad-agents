import copy
import unittest

from giad_agents.code_review import Reviewer
from giad_agents.peer import MAX_MODEL_CALLS, MAX_MODEL_PARAMS, MAX_REQUESTS, ToolError, encode
from test_agents import job, test_result
from test_peer import valid_report


def call(name, **args):
    return {"function": {"name": name, "arguments": args}}


def assistant(*calls):
    return {"role": "assistant", "content": "", "tool_calls": list(calls)}


def finish(findings=None):
    return {"role": "assistant", "content": encode({"summary": "Inspected PR behavior and dependencies.",
             "limitations": "Scripted model fixture.", "findings": findings or []})}


def finding(path="a.py", line=2):
    result = valid_report()["findings"][0]
    result.update(file=path, line=line)
    return result


class ScriptedHost:
    def __init__(self, answers, sources=None, diff="diff", errors=None):
        self.answers, self.sources, self.diff = answers, sources or {"a.py": "def add(a, b):\n    return a - b\n"}, diff
        self.calls, self.requests, self.errors = 0, [], errors or {}
        self.report = None

    def call(self, method, params):
        self.calls += 1
        self.requests.append((method, copy.deepcopy(params)))
        if method in self.errors:
            raise ToolError(self.errors[method])
        if method == "git.diff":
            return {"Text": self.diff, "Truncated": False, "SkippedFiles": 0}
        if method == "model.chat":
            if not self.answers:
                raise ToolError("scripted model unavailable")
            return copy.deepcopy(self.answers.pop(0))
        if method == "repository.read":
            path = params["path"]
            if path not in self.sources:
                raise ToolError(f"Could not read {path}")
            lines = self.sources[path].rstrip("\n").split("\n")
            end = params["end"] or len(lines)
            return {"Text": "".join(f"{i}: {lines[i-1]}\n" for i in range(params["start"], min(end, len(lines)) + 1)),
                    "Truncated": False, "SkippedFiles": 0}
        if method == "repository.search":
            return {"Text": "helper.py:1: add(a, b)\n", "Truncated": False, "SkippedFiles": 0}
        if method == "github.linked_issues":
            return [{"number": 7, "title": "Addition contract", "body": "Return the sum"}]
        if method == "tests.run":
            return test_result(params["profile"], 1)
        raise AssertionError(method)

    def finish(self, report, observed):
        self.calls += 1
        self.report = copy.deepcopy(report)


def review_job(paths=("a.py",), **updates):
    return job(changedFiles=[{"path": p, "status": "modified"} for p in paths],
               allowedCapabilities=["git.diff", "repository.read", "repository.search", "repository.instructions",
                                    "model.chat", "tests.run", "github.linked_issues"], **updates)


class ReviewTests(unittest.TestCase):
    def test_whole_pr_more_than_three_files_later_lines_and_more_than_three_findings(self):
        sources = {f"file{i}.py": "x = 1\n" * 250 for i in range(5)}
        sources["helper.py"] = "add(a, b)\n"
        calls = [call("repository_read", path=p, start=200, end=0) for p in sources if p != "helper.py"]
        calls.append(call("repository_read", path="helper.py", start=1, end=0))
        calls += [call("repository_search", query="add("), call("linked_issues"),
                  call("tests_run", profile="unit"), call("tests_run", profile="integration")]
        findings = [finding("file4.py", line) for line in range(200, 205)]
        host = ScriptedHost([assistant(*calls), finish(findings)], sources)
        reviewer = Reviewer(review_job(tuple(p for p in sources if p != "helper.py"), testProfiles=["unit", "integration"]), host)
        reviewer.review()
        self.assertEqual(len(host.report["findings"]), 5)
        self.assertIn("5 of 5", host.report["limitations"])
        self.assertIn("helper.py", reviewer.observed)
        self.assertEqual([r["profile"] for r in reviewer.test_results], ["unit", "integration"])
        self.assertNotIn("No tests ran", host.report["limitations"])

    def test_search_hits_and_unchanged_source_cannot_supply_finding_anchors(self):
        host = ScriptedHost([
            assistant(call("repository_search", query="add("), call("repository_read", path="helper.py", start=1, end=0)),
            finish([finding("a.py", 2)]),
            assistant(call("repository_read", path="a.py", start=1, end=0)),
            finish([finding("a.py", 2)]),
        ], {"helper.py": "return a - b\n", "a.py": "def add(a,b):\n    return a - b\n"})
        Reviewer(review_job(), host).review()
        chats = [p for m, p in host.requests if m == "model.chat"]
        self.assertIn("uninspected source", encode(chats[2]))
        self.assertEqual(host.report["findings"][0]["file"], "a.py")

    def test_missing_source_is_visible_and_does_not_omit_other_changed_files(self):
        host = ScriptedHost([assistant(call("repository_read", path="missing.py", start=1, end=0),
                                       call("repository_read", path="a.py", start=1, end=0)), finish()])
        Reviewer(review_job(("missing.py", "a.py")), host).review()
        self.assertIn("1 of 2", host.report["limitations"])
        self.assertIn("missing.py", host.report["limitations"])
        self.assertIn("Could not read", host.report["limitations"])

    def test_model_failure_never_finishes(self):
        host = ScriptedHost([], errors={"model.chat": "model unavailable"})
        with self.assertRaises(ToolError):
            Reviewer(review_job(), host).review()
        self.assertIsNone(host.report)

    def test_model_must_inspect_source_before_empty_report(self):
        host = ScriptedHost([finish(), assistant(call("repository_read", path="a.py", start=1, end=0)), finish()])
        Reviewer(review_job(), host).review()
        chats = [p for m, p in host.requests if m == "model.chat"]
        self.assertIn("inspect changed head source", encode(chats[1]))

    def test_unapproved_tests_and_unknown_methods_are_not_executed(self):
        host = ScriptedHost([assistant(call("tests_run", profile="arbitrary"), call("shell", command="echo unsafe"),
                                       call("repository_read", path="a.py", start=1, end=0)), finish()])
        Reviewer(review_job(testProfiles=["unit"]), host).review()
        self.assertNotIn("tests.run", [m for m, _ in host.requests])
        self.assertIn("test profile is not approved", host.report["limitations"])

    def test_context_pagination_recovers_large_diff_without_twelve_kib_cutoff(self):
        host = ScriptedHost([], diff="x" * 64000)
        reviewer = Reviewer(review_job(), host)
        self.assertNotIn("diff", reviewer.brief)
        args = {"section": "diff", "offset": 0, "length": 0}
        first = reviewer.context(args, 20000)
        self.assertGreater(len(first["Text"]), 12000)
        self.assertTrue(first["Truncated"])
        text = first["Text"]
        while first["Truncated"]:
            args["offset"] = first["nextOffset"]
            first = reviewer.context(args, 20000)
            text += first["Text"]
        self.assertEqual(text, host.diff)

    def test_context_eviction_keeps_complete_tool_turns_and_trusted_guidance(self):
        host = ScriptedHost([*[assistant(call("repository_read", path="a.py", start=1, end=0)) for _ in range(8)], finish()],
                            {"a.py": "x" * 250 + "\n" + "y" * 250 + "\n" + "z" * 18000 + "\n"})
        reviewer = Reviewer(review_job(trustedInstructions=[{"scope": ".", "content": "trusted root marker"}]), host)
        reviewer.review()
        for method, params in host.requests:
            if method != "model.chat":
                continue
            self.assertLessEqual(len(encode(params).encode("utf-8")), MAX_MODEL_PARAMS)
            self.assertIn("trusted root marker", params["messages"][0]["content"])
            seen = False
            for message in params["messages"]:
                if message["role"] == "assistant":
                    seen = bool(message.get("tool_calls"))
                if message["role"] == "tool":
                    self.assertTrue(seen, "orphaned tool response")
        self.assertIn("evicted", host.report["limitations"])

    def test_guidance_scopes_and_unicode_source(self):
        host = ScriptedHost([assistant(call("repository_read", path="src/new.py", start=1, end=0)), finish([finding("src/new.py", 2)])],
                            {"src/new.py": "value = '\u2028'\nreturn 0\n"})
        start = review_job(("src/new.py",), trustedInstructions=[
            {"scope": ".", "content": "root"}, {"scope": "src", "content": "applicable"},
            {"scope": "other", "content": "unrelated"}])
        start["changedFiles"][0].update(status="renamed", previousPath="old.py")
        Reviewer(start, host).review()
        chats = [p for m, p in host.requests if m == "model.chat"]
        self.assertIn("applicable", chats[1]["messages"][0]["content"])
        self.assertNotIn("unrelated", chats[1]["messages"][0]["content"])

    def test_budget_end_requests_a_report_instead_of_more_research(self):
        answers = [assistant(call("repository_read", path="a.py", start=1, end=0)) for _ in range(MAX_MODEL_CALLS - 1)]
        host = ScriptedHost(answers + [finish()])
        Reviewer(review_job(), host).review()
        chats = [p for m, p in host.requests if m == "model.chat"]
        self.assertEqual(len(chats), MAX_MODEL_CALLS)
        self.assertEqual(chats[-1]["tools"], [])
        self.assertIsNotNone(host.report)

    def test_no_valid_report_before_budget_is_failure(self):
        host = ScriptedHost([{"role": "assistant", "content": "not JSON"} for _ in range(MAX_MODEL_CALLS)])
        with self.assertRaisesRegex(ValueError, "no valid report"):
            Reviewer(review_job(), host).review()
        self.assertIsNone(host.report)

    def test_host_budget_reserves_final_model_call_and_finish(self):
        host = ScriptedHost([assistant(*[call("repository_read", path="a.py", start=1, end=0) for _ in range(100)]), finish()])
        Reviewer(review_job(), host).review()
        self.assertEqual(host.calls, MAX_REQUESTS)
        chats = [p for m, p in host.requests if m == "model.chat"]
        self.assertEqual(chats[-1]["tools"], [])
        self.assertIn("host request budget reserved", host.report["limitations"])

    def test_only_two_approved_test_runs_are_executed(self):
        host = ScriptedHost([assistant(call("repository_read", path="a.py", start=1, end=0),
                                       *[call("tests_run", profile=p) for p in ("unit", "integration", "extra")]), finish()])
        Reviewer(review_job(testProfiles=["unit", "integration", "extra"]), host).review()
        self.assertEqual([p["profile"] for m, p in host.requests if m == "tests.run"], ["unit", "integration"])
        self.assertIn("test-run budget exhausted", host.report["limitations"])

    def test_latest_oversized_turn_is_not_dropped_and_claimed_as_observed(self):
        host = ScriptedHost([])
        reviewer = Reviewer(review_job(), host)
        reviewer.turns = [[{"role": "assistant", "content": "x" * MAX_MODEL_PARAMS}]]
        with self.assertRaisesRegex(ValueError, "latest tool turn"):
            reviewer.messages(reviewer.tools)
        self.assertEqual(len(reviewer.turns), 1)


if __name__ == "__main__":
    unittest.main()
