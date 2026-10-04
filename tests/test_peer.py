import copy
import io
import unittest
from unittest.mock import patch

from giad_agents.code_review import fit_text_result, model_report
from giad_agents.peer import Host, MAX_FRAME, VERSION, receive, validate_report


def valid_report():
    return {"summary": "Inspected addition", "limitations": "No callers inspected.", "findings": [{
        "source": "code-review", "category": "correctness", "file": "a.py", "line": 2,
        "severity": "high", "confidence": 0.9, "title": "Wrong return value",
        "explanation": "Addition subtracts.", "evidence": "return a - b",
        "failure_scenario": "add(2, 3) returns -1.", "suggested_fix": "Return a + b.",
    }]}


class PeerTests(unittest.TestCase):
    def test_invalid_frames(self):
        for wire in (b"", b"{}", b"not JSON\n", b"[]\n", b'{"apiVersion":"old"}\n',
                     b'{"apiVersion":"giad/v1","result":NaN}\n', b"\xff\n", b"x" * MAX_FRAME + b"\n"):
            with self.subTest(wire=wire[:60]), patch("sys.stdin", io.TextIOWrapper(io.BytesIO(wire))):
                with self.assertRaises(ValueError):
                    receive()

    def test_reply_id_must_match(self):
        with patch("giad_agents.peer.receive", return_value={"apiVersion": VERSION, "id": "wrong", "result": {}}), patch("sys.stdout", io.StringIO()):
            with self.assertRaisesRegex(ValueError, "unexpected host response"):
                Host().call("git.diff", {})

    def test_model_budget_fails_before_writing(self):
        with patch("sys.stdout", io.StringIO()) as output:
            with self.assertRaisesRegex(ValueError, "96 KiB"):
                Host().call("model.chat", {"messages": [{"content": "x" * (96 * 1024)}]})
            self.assertEqual(output.getvalue(), "")

    def test_report_requires_inspected_anchors_and_strict_fields(self):
        report = valid_report()
        validate_report(report, {"a.py": {2}})
        for key, value in (
            ("line", 999), ("line", True), ("severity", "critical"),
            ("confidence", True), ("confidence", float("nan")), ("confidence", float("inf")),
            ("confidence", 1.1), ("confidence", 10 ** 400), ("title", ""), ("evidence", "é" * 4097),
            ("file", "unread.py"), ("extra", "unsupported"),
        ):
            bad = copy.deepcopy(report)
            bad["findings"][0][key] = value
            with self.subTest(key=key, value=str(value)[:40]), self.assertRaises(ValueError):
                validate_report(bad, {"a.py": {2}})

    def test_model_json_prose_and_nonfinite_numbers_rejected(self):
        for content in ("looks fine", "", '{"summary": NaN}'):
            with self.subTest(content=content), self.assertRaises(ValueError):
                model_report(content)

    def test_bounded_source_preserves_complete_utf8_lines(self):
        result = fit_text_result({"Text": "1: hello\n2: " + "é" * 7000 + "\n", "Truncated": False}, 250, complete_lines=True)
        self.assertTrue(result["Truncated"])
        self.assertEqual(result["Text"], "1: hello\n")
        self.assertEqual(result["nextStart"], 2)


if __name__ == "__main__":
    unittest.main()
