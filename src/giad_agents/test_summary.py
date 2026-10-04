"""Summarize observed approved test runs without a model or defect inference."""

from .peer import Host, MAX_TEST_RUNS, run, start_job


def main():
    job = start_job()
    profiles = list(dict.fromkeys(job.get("testProfiles") or []))
    if "tests.run" not in job["allowedCapabilities"] or not profiles:
        raise ValueError("test-summary requires tests.run and at least one approved test profile")
    host = Host()
    results = [host.call("tests.run", {"profile": profile}) for profile in profiles[:MAX_TEST_RUNS]]
    summary = [f"Ran {len(results)} approved test profile(s) on the PR head."]
    limitations = ["Head-only execution; no base comparison. A failing profile does not establish an introduced regression, and a passing profile does not establish that tests existed or that the code is correct.",
                   "This agent summarizes observed results and performs no defect analysis. Bounded merged output is retained in GIAD's draft testRuns."]
    for result in results:
        if result["timedOut"]:
            status = "TIMED OUT"
        elif result["oomKilled"]:
            status = "OUT OF MEMORY"
        elif result["exitCode"] is None:
            status = "NO EXIT STATUS"
        else:
            status = "PASSED" if result["exitCode"] == 0 else "FAILED"
        summary.append(f"{result['profile']}: {status}; exitCode={result['exitCode']}; duration={result['durationMs']} ms.")
        if result["truncated"]:
            limitations.append(f"Output for profile {result['profile']} was truncated by GIAD.")
        if result["oomKilled"]:
            limitations.append(f"Profile {result['profile']} exceeded its container memory limit.")
    if len(profiles) > MAX_TEST_RUNS:
        limitations.append(f"GIAD permits {MAX_TEST_RUNS} runs per session; {len(profiles) - MAX_TEST_RUNS} additional approved profiles were not run.")
    host.finish({"summary": "\n".join(summary), "limitations": "\n".join(limitations), "findings": []})


if __name__ == "__main__":
    run(main, "test-summary")
