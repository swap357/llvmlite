#!/usr/bin/env python

import json
import os
from pathlib import Path


event = os.environ.get("GITHUB_EVENT_NAME")
label = os.environ.get("GITHUB_LABEL_NAME")
inputs = os.environ.get("GITHUB_WORKFLOW_INPUT", "{}")

runner_mapping = {
    "linux-64": "ubuntu-24.04",
    "linux-arm64": "ubuntu-24.04-arm",
    "osx-64": "macos-13",
    "osx-arm64": "macos-14",
    "win-64": "windows-2019",
}

python_versions = ["3.10", "3.11", "3.12", "3.13"]

def generate_matrix(platforms, python_versions):
    """Generate matrix with all combinations of platforms and Python versions"""
    include = []
    for platform in platforms:
        for python_version in python_versions:
            include.append({
                "runner": runner_mapping[platform],
                "platform": platform,
                "python-version": python_version,
            })
    return include

# Default platforms for PR and label builds
default_platforms = ["linux-64", "linux-arm64", "win-64", "osx-64", "osx-arm64"]

print(
    "Deciding what to do based on event: "
    f"'{event}', label: '{label}', inputs: '{inputs}'"
)

if event == "pull_request":
    print("pull_request detected")
    include = generate_matrix(default_platforms, python_versions)
elif event == "label" and label == "build_llvmlite_on_gha":
    print("build label detected")
    include = generate_matrix(default_platforms, python_versions)
elif event == "workflow_dispatch":
    print("workflow_dispatch detected")
    params = json.loads(inputs)
    platform = params.get("platform", "linux-64")
    python_version = params.get("python-version", "3.12")
    include = generate_matrix([platform], [python_version])
else:
    include = []

matrix = {"include": include}
print(f"Emitting matrix:\n {json.dumps(matrix, indent=4)}")

Path(os.environ["GITHUB_OUTPUT"]).write_text(f"matrix={json.dumps(matrix)}")
