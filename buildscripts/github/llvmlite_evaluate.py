#!/usr/bin/env python

import json
import os
from pathlib import Path


event = os.environ.get("GITHUB_EVENT_NAME")
pr_labels_json = os.environ.get("GITHUB_PR_LABELS", "[]")
inputs = os.environ.get("GITHUB_WORKFLOW_INPUT", "{}")

# Parse PR labels
try:
    pr_labels = json.loads(pr_labels_json) if pr_labels_json else []
except json.JSONDecodeError:
    pr_labels = []

runner_mapping = {
    "linux-64": "ubuntu-24.04",
    "linux-aarch64": "ubuntu-24.04-arm",
    "osx-arm64": "macos-14",
    "win-64": "windows-2025",
}

default_include = [
    # linux-64
    {"runner": runner_mapping["linux-64"], "platform": "linux-64", "python-version": "3.10"},
    {"runner": runner_mapping["linux-64"], "platform": "linux-64", "python-version": "3.11"},
    {"runner": runner_mapping["linux-64"], "platform": "linux-64", "python-version": "3.12"},
    {"runner": runner_mapping["linux-64"], "platform": "linux-64", "python-version": "3.13"},
    {"runner": runner_mapping["linux-64"], "platform": "linux-64", "python-version": "3.14"},

    # linux-aarch64
    {"runner": runner_mapping["linux-aarch64"], "platform": "linux-aarch64", "python-version": "3.10"},
    {"runner": runner_mapping["linux-aarch64"], "platform": "linux-aarch64", "python-version": "3.11"},
    {"runner": runner_mapping["linux-aarch64"], "platform": "linux-aarch64", "python-version": "3.12"},
    {"runner": runner_mapping["linux-aarch64"], "platform": "linux-aarch64", "python-version": "3.13"},
    {"runner": runner_mapping["linux-aarch64"], "platform": "linux-aarch64", "python-version": "3.14"},

    # osx-arm64
    {"runner": runner_mapping["osx-arm64"], "platform": "osx-arm64", "python-version": "3.10"},
    {"runner": runner_mapping["osx-arm64"], "platform": "osx-arm64", "python-version": "3.11"},
    {"runner": runner_mapping["osx-arm64"], "platform": "osx-arm64", "python-version": "3.12"},
    {"runner": runner_mapping["osx-arm64"], "platform": "osx-arm64", "python-version": "3.13"},
    {"runner": runner_mapping["osx-arm64"], "platform": "osx-arm64", "python-version": "3.14"},

    # win-64
    {"runner": runner_mapping["win-64"], "platform": "win-64", "python-version": "3.10"},
    {"runner": runner_mapping["win-64"], "platform": "win-64", "python-version": "3.11"},
    {"runner": runner_mapping["win-64"], "platform": "win-64", "python-version": "3.12"},
    {"runner": runner_mapping["win-64"], "platform": "win-64", "python-version": "3.13"},
    {"runner": runner_mapping["win-64"], "platform": "win-64", "python-version": "3.14"},
]

print(
    "Deciding what to do based on event: "
    f"'{event}', labels: '{pr_labels}', inputs: '{inputs}'"
)
if event == "push":
    # Push events to main branch
    print(f"{event} detected, running full build matrix.")
    include = default_include
elif event == "pull_request":
    # Check if both 'conda' and 'gha' labels are present
    has_conda_and_gha = "conda" in pr_labels and "gha" in pr_labels

    if has_conda_and_gha:
        # Both labels present - run build
        print(f"pull_request with both 'conda' and 'gha' labels detected.")

        # Check for platform-specific labels
        platform_labels = {"linux-64", "linux-aarch64", "osx-arm64", "win-64"}
        platform_filter = platform_labels.intersection(pr_labels)

        if platform_filter:
            # Filter matrix by specified platforms
            print(f"Filtering by platforms: {platform_filter}")
            include = [
                item for item in default_include
                if item["platform"] in platform_filter
            ]
        else:
            # No platform filter - run all platforms
            print("Running full build matrix for all platforms.")
            include = default_include
    elif "conda" in pr_labels or "gha" in pr_labels:
        # Only one label present - skip
        print(f"pull_request has labels {pr_labels} but requires BOTH 'conda' AND 'gha'. Skipping.")
        include = []
    else:
        # No build labels - triggered by path changes
        print("pull_request triggered by path changes, running full build matrix.")
        include = default_include
elif event == "workflow_dispatch":
    print("workflow_dispatch detected")
    params = json.loads(inputs)
    platform = params.get("platform", "all")

    # Start with the full matrix
    filtered_matrix = default_include

    # Filter by platform if a specific one is chosen
    if platform != "all":
        filtered_matrix = [
            item for item in filtered_matrix if item["platform"] == platform
        ]

    include = filtered_matrix
else:
    # For any other events, produce an empty matrix.
    include = []

matrix = {"include": include}
print(f"Emitting matrix:\n {json.dumps(matrix, indent=4)}")

Path(os.environ["GITHUB_OUTPUT"]).write_text(f"matrix={json.dumps(matrix)}")
