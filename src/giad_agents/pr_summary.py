"""Metadata-only starter; it does not analyze code or ask a model."""

from .peer import Host, run, start_job


def main():
    job = start_job()
    Host().finish({
        "summary": f"PR #{job['number']}: {job['title']} ({len(job['changedFiles'])} changed files).",
        "limitations": "Metadata only; code, repository guidance, and tests were not evaluated.",
        "findings": [],
    })


if __name__ == "__main__":
    run(main, "pr-summary")
