#!/usr/bin/env python
"""
Workflow utilities for LLVMLite build orchestration.
Combines platform mappings, build matrix generation, and workflow filename lookup.

Usage:
  python workflow_utils.py get-build-matrix <platform_group> <python_versions>
  python workflow_utils.py get-workflow-filename <platform> <build_type>
"""

import sys
import json

# Platform configuration embedded directly in the script
# This replaces the need for the external platform_mappings.yml file
CONFIG = {
    # Workflow mappings for conda builds
    "conda_workflows": {
        "linux-64": "llvmlite_linux-64_conda_builder.yml",
        "linux-arm64": "llvmlite_linux-arm64_conda_builder.yml",
        "osx-64": "llvmlite_osx-64_conda_builder.yml",
        "osx-arm64": "llvmlite_osx-arm64_conda_builder.yml",
        "win-64": "llvmlite_win-64_conda_builder.yml"
    },

    # Workflow mappings for wheel builds
    "wheel_workflows": {
        "linux-64": "llvmlite_linux-64_wheel_builder.yml",
        "linux-arm64": "llvmlite_linux-arm64_wheel_builder.yml",
        "osx-64": "llvmlite_osx-64_wheel_builder.yml",
        "osx-arm64": "llvmlite_osx-arm64_wheel_builder.yml",
        "win-64": "llvmlite_win-64_wheel_builder.yml"
    },

    # Platform groupings for easier selection
    "platform_groups": {
        "all": ["linux-64", "linux-aarch64", "osx-64", "osx-arm64", "win-64"],
        "linux": ["linux-64", "linux-aarch64"],
        "osx": ["osx-64", "osx-arm64"],
        "win": ["win-64"],
        "arm": ["linux-aarch64", "osx-arm64"]
    },

    # Default Python versions to build
    "python_versions": ["3.10", "3.11", "3.12", "3.13"]
}


def get_build_matrix(platform_group, python_versions_input):
    """
    Generate the build matrix based on platform group and Python versions

    Args:
        platform_group: Platform group to build (all, linux, osx, win, arm)
        python_versions_input: 'all' or comma-separated list of Python versions

    Returns:
        Dictionary with platforms and python_versions arrays
    """
    # Get platform list based on input
    platforms = CONFIG["platform_groups"].get(platform_group, [])

    if not platforms:
        raise ValueError(f"Invalid platform group: {platform_group}")

    # Handle Python versions
    if python_versions_input == 'all':
        # Use default Python versions from config
        py_versions = CONFIG["python_versions"]
    else:
        # Parse comma-separated list
        py_versions = python_versions_input.split(',')

    return {
        'platforms': platforms,
        'python_versions': py_versions
    }


def get_workflow_filename(platform, build_type):
    """
    Get the workflow filename for a specific platform and build type

    Args:
        platform: Platform identifier (e.g., linux-64, osx-arm64)
        build_type: Type of package build (conda or wheel)

    Returns:
        Workflow filename

    Raises:
        KeyError: If no mapping is found for the platform
        ValueError: If build_type is not 'conda' or 'wheel'
    """
    # Get the mapping key based on build type
    if build_type == 'conda':
        mapping_key = 'conda_workflows'
    elif build_type == 'wheel':
        mapping_key = 'wheel_workflows'
    else:
        raise ValueError(f"Invalid build type: {build_type}. Must be 'conda' or 'wheel'.")

    # Get workflow filename for the platform
    try:
        workflow = CONFIG[mapping_key][platform]
        return workflow
    except KeyError:
        raise KeyError(f"No workflow mapping found for platform: {platform}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: python {sys.argv[0]} [command] [arguments...]")
        print(f"Commands: get-build-matrix, get-workflow-filename")
        sys.exit(1)

    command = sys.argv[1]

    if command == "get-build-matrix":
        if len(sys.argv) != 4:
            print(f"Usage: python {sys.argv[0]} get-build-matrix <platform_group> <python_versions>")
            sys.exit(1)

        platform_group = sys.argv[2]
        python_versions_input = sys.argv[3]

        try:
            matrix = get_build_matrix(platform_group, python_versions_input)
            # Output the matrix as JSON for GitHub Actions
            print(json.dumps(matrix))
        except Exception as e:
            print(f"ERROR: {str(e)}", file=sys.stderr)
            sys.exit(1)

    elif command == "get-workflow-filename":
        if len(sys.argv) != 4:
            print(f"Usage: python {sys.argv[0]} get-workflow-filename <platform> <build_type>")
            sys.exit(1)

        platform = sys.argv[2]
        build_type = sys.argv[3]

        try:
            workflow_file = get_workflow_filename(platform, build_type)
            print(workflow_file)
        except Exception as e:
            print(f"ERROR: {str(e)}", file=sys.stderr)
            sys.exit(1)

    else:
        print(f"Unknown command: {command}")
        print(f"Available commands: get-build-matrix, get-workflow-filename")
        sys.exit(1)