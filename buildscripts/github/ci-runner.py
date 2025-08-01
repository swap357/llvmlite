#!/usr/bin/env python3
"""
ci_runner.py

A flexible wrapper around GitHub CLI (`gh`) to manage conda-only CI builds for llvmlite and numba:
 1. Trigger llvmdev build workflow on numba/llvmlite
 2. Trigger llvmlite conda-builder workflow on numba/llvmlite
 3. Trigger numba conda-builder workflows on numba/numba for all platforms
 4. Monitor each run to successful completion
 5. Download conda artifacts

Usage example:
  export GH_TOKEN=<your_token>
  ./ci_runner.py \
    --llvmlite-branch pr-1240-llvmlite \
    --numba-branch pr-1240-numba \
    --steps llvmdev,llvmlite_conda,numba_conda,download_llvmlite_conda,download_numba_conda \
    --reuse-run llvmdev:12345
"""

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Any, Set

# Repository constants
LLVMLITE_REPO = "swap357/llvmlite"
NUMBA_REPO    = "swap357/numba"
DEFAULT_BRANCH = "main"

# Supported steps
ALL_STEPS = {
    "llvmdev",
    "llvmlite_conda",
    "numba_conda",
    "download_llvmlite_conda",
    "download_numba_conda",
}
PLATFORMS = ["osx-64", "osx-arm64", "win-64", "linux-aarch64", "linux-64"]

STATE_FILE = Path(".ci_state.json")


def load_state() -> Dict[str, Dict[str, Any]]:
    """Load build state from disk, or return empty state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: Dict[str, Dict[str, Any]]) -> None:
    """Persist build state to disk."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_workflow_conclusion(workflow_run_id: str, repo: str) -> str:
    """Retrieve the conclusion of a completed GitHub Actions run."""
    output = subprocess.check_output([
        "gh", "run", "view", workflow_run_id,
        "--repo", repo,
        "--json", "conclusion"
    ])
    data = json.loads(output)
    return data.get("conclusion", "")


def dispatch_or_reuse(
    workflow_filename: str,
    workflow_inputs: Dict[str, str],
    step_key: str,
    state: Dict[str, Dict[str, Any]],
    repo: str,
    branch: str
) -> int:
    """
    Reuse an existing successful or in-progress run, or dispatch a new one.
    Returns the workflow run ID.
    """
    state_entry     = state.get(step_key, {})
    existing_run_id = state_entry.get("run_id")
    completed       = state_entry.get("completed", False)
    last_conclusion = state_entry.get("conclusion", "")

    if existing_run_id and completed and last_conclusion == "success":
        logging.info(f"Reusing successful {step_key} run {existing_run_id} on {repo}")
        return existing_run_id

    if existing_run_id and not completed:
        logging.info(f"Resuming in-progress {step_key} run {existing_run_id} on {repo}")
        return existing_run_id

    # Dispatch a new run
    cmd = ["gh", "workflow", "run", workflow_filename, "--repo", repo, "--ref", branch]
    for name, value in workflow_inputs.items():
        cmd.extend(["-f", f"{name}={value}"])
    logging.info(f"Dispatching {workflow_filename} for {step_key} on {repo} with inputs {workflow_inputs}")
    dispatch_output = subprocess.check_output(cmd, text=True)

    # Parse run ID from dispatch URL
    match_obj = re.search(r"/actions/runs/(\d+)", dispatch_output)
    if match_obj:
        new_run_id = int(match_obj.group(1))
    else:
        # Sleep for 30s then fetch latest run
        logging.info(f"Sleeping for 30 seconds to allow {step_key} run on {repo} to register...")
        time.sleep(30)
        list_output = subprocess.check_output([
            "gh", "run", "list",
            "--repo", repo,
            "--workflow", workflow_filename,
            "--branch", branch,
            "--limit", "1",
            "--json", "databaseId"
        ])
        runs = json.loads(list_output)
        if not runs:
            logging.error(f"No runs found for {step_key} on {repo} after waiting.")
            sys.exit(1)
        new_run_id = int(runs[0]["databaseId"])

    state[step_key] = {"run_id": new_run_id, "completed": False}
    save_state(state)
    logging.info(f"Recorded new {step_key} run {new_run_id} on {repo}")
    return new_run_id


def wait_for_success(
    step_key: str,
    state: Dict[str, Dict[str, Any]],
    repo: str
) -> None:
    """
    Block until the specified workflow run completes successfully.
    """
    state_entry     = state.get(step_key, {})
    workflow_run_id = state_entry.get("run_id")

    if not workflow_run_id:
        logging.warning(f"No run_id for {step_key}, skipping wait.")
        return
    if state_entry.get("completed") and state_entry.get("conclusion") == "success":
        return

    try:
        subprocess.run([
            "gh", "run", "watch", str(workflow_run_id), "--repo", repo
        ], check=True)
    except KeyboardInterrupt:
        logging.info("Interrupted by user during watch; exiting gracefully.")
        sys.exit(0)

    conclusion = get_workflow_conclusion(str(workflow_run_id), repo)
    if conclusion != "success":
        logging.error(
            f"Run {workflow_run_id} for {step_key} on {repo} ended with '{conclusion}'. Aborting."
        )
        sys.exit(1)

    state_entry["completed"]  = True
    state_entry["conclusion"] = conclusion
    save_state(state)


def download_artifacts(
    step_key: str,
    state: Dict[str, Dict[str, Any]],
    repo: str,
    destination: Path
) -> None:
    """
    Download artifacts from a successful workflow run.
    """
    state_entry     = state.get(step_key, {})
    workflow_run_id = state_entry.get("run_id")

    if not workflow_run_id or state_entry.get("conclusion") != "success":
        logging.error(f"Cannot download {step_key}: no successful run on {repo}.")
        sys.exit(1)

    destination.mkdir(parents=True, exist_ok=True)
    logging.info(
        f"Downloading {step_key} artifacts from run {workflow_run_id} on {repo} to {destination}"
    )
    subprocess.run([
        "gh", "run", "download", str(workflow_run_id),
        "--repo", repo,
        "--dir", str(destination)
    ], check=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser(
        description="Manage conda-only CI workflows for llvmlite & numba"
    )
    parser.add_argument(
        "--llvmlite-branch", default=DEFAULT_BRANCH,
        help="Git branch or tag for llvmlite workflows"
    )
    parser.add_argument(
        "--numba-branch", default=DEFAULT_BRANCH,
        help="Git branch or tag for numba workflows"
    )
    parser.add_argument(
        "--steps", default="all",
        help=",".join(sorted(ALL_STEPS)) + ",all"
    )
    parser.add_argument(
        "--reuse-run", action="append",
        help="STEP:RUN_ID to seed the state manually"
    )
    args = parser.parse_args()

    if not os.getenv("GH_TOKEN"):
        logging.error("GH_TOKEN environment variable is required.")
        sys.exit(1)

    requested_steps: Set[str] = {s.strip() for s in args.steps.split(',')}
    if "all" in requested_steps:
        requested_steps = ALL_STEPS.copy()

    state = load_state()

    # Seed manual runs
    if args.reuse_run:
        for seed in args.reuse_run:
            try:
                seed_step, seed_id = seed.split(":")
                state[seed_step] = {"run_id": int(seed_id), "completed": False}
                logging.info(f"Seeded {seed_step} with run {seed_id}")
            except ValueError:
                logging.error(f"Invalid --reuse-run format: {seed}")
                sys.exit(1)
        save_state(state)

    # Step: llvmdev on LLVMLITE_REPO
    if "llvmdev" in requested_steps:
        dispatch_or_reuse(
            "llvmdev_build.yml",
            {"platform": "all", "recipe": "all"},
            "llvmdev",
            state,
            LLVMLITE_REPO,
            args.llvmlite_branch
        )
        wait_for_success("llvmdev", state, LLVMLITE_REPO)

    # Step: llvmlite_conda on LLVMLITE_REPO
    if "llvmlite_conda" in requested_steps:
        ll_inputs: Dict[str, str] = {"platform": "all"}
        llvm_entry = state.get("llvmdev", {})
        if llvm_entry.get("run_id") and llvm_entry.get("conclusion") == "success":
            ll_inputs["llvmdev_run_id"] = str(llvm_entry["run_id"])
            logging.info("Using local llvmdev run for llvmlite_conda")
        dispatch_or_reuse(
            "llvmlite_conda_builder.yml",
            ll_inputs,
            "llvmlite_conda",
            state,
            LLVMLITE_REPO,
            args.llvmlite_branch
        )
        wait_for_success("llvmlite_conda", state, LLVMLITE_REPO)

            # Step: numba_conda on NUMBA_REPO
    if "numba_conda" in requested_steps:
        # Prepare inputs using the llvmlite_conda run
        numba_inputs: Dict[str, str] = {}
        llconda_entry = state.get("llvmlite_conda", {})
        if llconda_entry.get("run_id") and llconda_entry.get("conclusion") == "success":
            numba_inputs["llvmlite_run_id"] = str(llconda_entry["run_id"])
            logging.info("Using llvmlite_conda run for numba_conda: %s", llconda_entry["run_id"])

        # Dispatch all platform-specific numba conda workflows
        dispatched_steps: List[str] = []
        for platform_name in PLATFORMS:
            # Map linux-aarch64 to linux-arm64
            workflow_platform = "linux-arm64" if platform_name == "linux-aarch64" else platform_name
            # Windows builder vs other platforms
            if platform_name == "win-64":
                workflow_file = f"numba_{workflow_platform}_builder.yml"
            else:
                workflow_file = f"numba_{workflow_platform}_conda_builder.yml"
            step_key = f"numba_conda_{platform_name}"
            dispatch_or_reuse(
                workflow_file,
                numba_inputs,
                step_key,
                state,
                NUMBA_REPO,
                args.numba_branch
            )
            dispatched_steps.append(step_key)

        # After triggering all, monitor each to completion
        for step_key in dispatched_steps:
            wait_for_success(step_key, state, NUMBA_REPO)

    # Step: download llvmlite conda artifacts
    if "download_llvmlite_conda" in requested_steps:
        download_artifacts(
            "llvmlite_conda",
            state,
            LLVMLITE_REPO,
            Path("artifacts/llvmlite_conda")
        )

    # Step: download numba conda artifacts
    if "download_numba_conda" in requested_steps:
        for step_key in state:
            if step_key.startswith("numba_conda_"):
                download_artifacts(
                    step_key,
                    state,
                    NUMBA_REPO,
                    Path("artifacts/numba_conda") / step_key
                )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Interrupted by user; exiting.")
        sys.exit(0)
