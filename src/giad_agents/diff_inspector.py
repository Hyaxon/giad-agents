"""Model-free broker check; fetching a diff does not establish correctness."""

from .peer import Host, run, start_job


def main():
    job = start_job()
    host = Host()
    diff = host.call("git.diff", {})
    limitations = "Diff retrieval only; no defect analysis, guidance evaluation, or tests."
    if diff["Truncated"]:
        limitations += " Diff coverage was truncated."
    host.finish({
        "summary": f"Retrieved {len(diff['Text'].encode('utf-8'))} bytes of diff for {len(job['changedFiles'])} changed files.",
        "limitations": limitations,
        "findings": [],
    })


if __name__ == "__main__":
    run(main, "diff-inspector")
