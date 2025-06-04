#!/usr/bin/env python

import os
from pathlib import Path


def should_run_workflow():
    """
    Determine if the llvmlite workflow should run based on the trigger event.
    Returns True if workflow should run, False otherwise.
    """
    event = os.environ.get("GITHUB_EVENT_NAME")
    label = os.environ.get("GITHUB_LABEL_NAME")

    print(f"Evaluating trigger: event='{event}', label='{label}'")

    # Always run on pull_request with path changes
    if event == "pull_request":
        print("pull_request detected - running workflow")
        return True

    # Run when specific label is applied
    elif event == "label" and label == "gha_build_and_test":
        print("Build label detected - running workflow")
        return True

    # Always run on manual dispatch
    elif event == "workflow_dispatch":
        print("workflow_dispatch detected - running workflow")
        return True

    else:
        print("No matching trigger found - skipping workflow")
        return False


if __name__ == "__main__":
    should_run = should_run_workflow()

    # Output for GitHub Actions
    if "GITHUB_OUTPUT" in os.environ:
        output_text = f"should_run={str(should_run).lower()}"
        Path(os.environ["GITHUB_OUTPUT"]).write_text(output_text)

    # Exit with appropriate code for shell usage
    exit(0 if should_run else 1)
