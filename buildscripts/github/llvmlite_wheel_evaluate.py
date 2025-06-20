#!/usr/bin/env python

import json
import os
from pathlib import Path


def get_platform_config():
    """Get platform-specific configurations for wheel building"""
    return {
        "linux-64": {
            "runner": "ubuntu-latest",
            "manylinux_image": "manylinux2014_x86_64",
            "conda_channel": "numba/label/manylinux2014_x86_64",
            "miniconda_file": "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh",
        },
        "linux-arm64": {
            "runner": "ubuntu-24.04-arm",
            "manylinux_image": "manylinux_2_28_aarch64",
            "conda_channel": "numba/label/manylinux2014_aarch64",
            "miniconda_file": "https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-aarch64.sh",
        },
        "osx-64": {
            "runner": "macos-13",
            "conda_channel": "numba/label/osx_wheel",
            "macosx_deployment_target": "10.15",
        },
        "osx-arm64": {
            "runner": "macos-14",
            "conda_channel": "numba/label/osx_wheel",
            "macosx_deployment_target": "11.1",
        },
        "win-64": {
            "runner": "windows-2019",
            "conda_channel": "numba/label/win64_wheel",
        },
    }


def generate_wheel_matrix(platforms, python_versions):
    """Generate matrix with platform configs and Python versions"""
    platform_configs = get_platform_config()
    include = []

    for platform in platforms:
        for python_version in python_versions:
            config = {
                "platform": platform,
                "python-version": python_version,
                "runner": platform_configs[platform]["runner"],
            }

            # Add platform-specific configurations
            platform_config = platform_configs[platform]
            for key, value in platform_config.items():
                if key != "runner":  # runner is already added
                    config[key] = value

            include.append(config)

    return include


event = os.environ.get("GITHUB_EVENT_NAME")
label = os.environ.get("GITHUB_LABEL_NAME")
inputs = os.environ.get("GITHUB_WORKFLOW_INPUT", "{}")

python_versions = ["3.10", "3.11", "3.12", "3.13"]
default_platforms = ["linux-64", "linux-arm64", "osx-64", "osx-arm64", "win-64"]

print(
    "Deciding what to do based on event: "
    f"'{event}', label: '{label}', inputs: '{inputs}'"
)

if event == "pull_request":
    print("pull_request detected")
    include = generate_wheel_matrix(default_platforms, python_versions)
elif event == "label" and label == "build_wheels_on_gha":
    print("build wheels label detected")
    include = generate_wheel_matrix(default_platforms, python_versions)
elif event == "workflow_dispatch":
    print("workflow_dispatch detected")
    params = json.loads(inputs)
    platform = params.get("platform", "linux-64")
    python_version = params.get("python-version", "3.12")
    include = generate_wheel_matrix([platform], [python_version])
else:
    include = []

matrix = {"include": include}
print(f"Emitting matrix:\n {json.dumps(matrix, indent=4)}")

Path(os.environ["GITHUB_OUTPUT"]).write_text(f"matrix={json.dumps(matrix)}")