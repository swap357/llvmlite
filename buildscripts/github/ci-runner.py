#!/usr/bin/env python3
"""
ci_runner.py

A flexible wrapper around GitHub CLI (`gh`) to manage llvmlite CI flows:
 1. Trigger the llvmdev build workflow
 2. Trigger the llvmlite conda-builder workflow (optional use of a local llvmdev build artifact)
 3. Trigger wheel-builder workflows using the llvmdev_for_wheel artifact (optional use of local llvmdev)
 4. Monitor runs until completion (requires success)
 5. Download selected artifacts (only from successful runs)

Usage:
  export GH_TOKEN=<your_token>
  ./ci_runner.py --repo numba/llvmlite --branch <branch> \
                 --steps llvmdev,llvmlite_conda \
                 --reuse-run llvmdev:16662684974

Step identifiers:
  - llvmdev             : Build LLVM development packages
  - llvmlite_conda      : Build llvmlite conda packages; if no local llvmdev run exists, will use published llvmdev packages
  - llvmlite_wheels     : Build llvmlite wheels for all platforms; if no local llvmdev run exists, will use published llvmdev_for_wheel packages
  - download_conda      : Download llvmlite conda artifacts (requires llvmlite_conda success)
  - download_wheels     : Download llvmlite wheel artifacts (requires llvmlite_wheels success)
  - all                 : Execute all steps sequentially

Flags:
  --reuse-run STEP:RUN_ID   Pre-seed state with a manual run ID for a step (sets completed=false).
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

# Constants
STATE_FILE = Path(".ci_state.json")
DEFAULT_REPO = "numba/llvmlite"
DEFAULT_BRANCH = "main"
ALL_STEPS = {"llvmdev", "llvmlite_conda", "llvmlite_wheels", "download_conda", "download_wheels"}
PLATFORMS = [
    "linux-64",
    "linux-aarch64",
    "osx-64",
    "osx-arm64",
    "win-64",
]


def load_state() -> Dict[str, Dict[str, Any]]:
    """Load CI run state from disk, or return empty state."""
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {}


def save_state(state: Dict[str, Dict[str, Any]]) -> None:
    """Persist CI run state to disk."""
    STATE_FILE.write_text(json.dumps(state, indent=2))


def get_conclusion(run_id: str, repository: str) -> str:
    """Retrieve the conclusion of a completed run."""
    output = subprocess.check_output([
        "gh", "run", "view", run_id,
        "--repo", repository,
        "--json", "conclusion"
    ])
    return json.loads(output).get("conclusion", "")


def run_or_reuse(
    workflow: str,
    inputs: Dict[str, str],
    key: str,
    state: Dict[str, Dict[str, Any]],
    repo: str,
    branch: str
) -> int:
    """
    Reuse a successful or in-progress run, or dispatch a new one.
    Returns the run ID.
    """
    entry     = state.get(key, {})
    run_id    = entry.get("run_id")
    completed = entry.get("completed", False)
    conclusion= entry.get("conclusion", "")

    # 1) If we already have a successful run, keep using it.
    if run_id and completed and conclusion == "success":
        logging.info(f"Reusing successful {key} run {run_id}")
        return run_id

    # 2) If it's still in progress, just resume watching it.
    if run_id and not completed:
        logging.info(f"Resuming in-progress {key} run {run_id}")
        return run_id

    # 3) Otherwise, trigger a fresh run...
    cmd = ["gh", "workflow", "run", workflow, "--repo", repo, "--ref", branch]
    for name, value in inputs.items():
        cmd.extend(["-f", f"{name}={value}"])

    logging.info(f"Dispatching {workflow} for {key} with inputs {inputs}")
    # Capture the CLI output so we can grab the new run ID from its URL:
    dispatch_output = subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT)

    # Extract <run-id> from the URL: https://github.com/.../actions/runs/<run-id>
    match = re.search(r"/actions/runs/(\d+)", dispatch_output)
    if match:
        new_run_id = int(match.group(1))
    else:
        # Fallback: poll the run list for the most recent one on this branch
        logging.info(f"Waiting for new {key} run to register via list query…")
        new_run_id = None
        for _ in range(10):
            runs_output = subprocess.check_output([
                "gh", "run", "list",
                "--repo", repo,
                "--workflow", workflow,
                "--branch", branch,
                "--limit", "1",
                "--json", "databaseId",
            ])
            runs = json.loads(runs_output)
            if runs:
                new_run_id = int(runs[0]["databaseId"])
                break
            time.sleep(2)

        if new_run_id is None:
            logging.error(f"Timeout waiting for {key} run to appear.")
            sys.exit(1)

    # Record and persist the fresh run
    state[key] = {"run_id": new_run_id, "completed": False}
    save_state(state)
    logging.info(f"Recorded new {key} run {new_run_id}")

    return new_run_id

def wait_completion(
    key: str,
    state: Dict[str, Dict[str, Any]],
    repo: str
) -> None:
    """
    Wait for the specified run to complete successfully.
    """
    entry = state.get(key, {})
    run_id = entry.get("run_id")

    if not run_id:
        logging.warning(f"No run_id for {key}, skipping wait.")
        return

    if entry.get("completed") and entry.get("conclusion") == "success":
        logging.info(f"{key} already succeeded (run {run_id}).")
        return

    logging.info(f"Watching run {run_id} for {key}...")
    try:
        subprocess.run(["gh", "run", "watch", str(run_id), "--repo", repo], check=True)
    except KeyboardInterrupt:
        logging.info("Interrupted by user during watch; exiting gracefully.")
        sys.exit(0)

    conclusion = get_conclusion(str(run_id), repo)
    if conclusion != "success":
        logging.error(f"Run {run_id} for {key} concluded with '{conclusion}'. Aborting.")
        sys.exit(1)

    entry["completed"] = True
    entry["conclusion"] = conclusion
    save_state(state)
    logging.info(f"Run {run_id} for {key} succeeded.")

def download(
    key: str,
    state: Dict[str, Dict[str, Any]],
    repo: str,
    dest: Path
) -> None:
    """Download artifacts for a successful run."""
    entry = state.get(key, {})
    run_id = entry.get("run_id")

    if not run_id or entry.get("conclusion") != "success":
        logging.error(f"Cannot download {key}, no successful run found.")
        sys.exit(1)

    dest.mkdir(parents=True, exist_ok=True)
    logging.info(f"Downloading {key} artifacts from run {run_id} into {dest}")
    subprocess.run([
        "gh", "run", "download", str(run_id),
        "--repo", repo,
        "--dir", str(dest)
    ], check=True)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    parser = argparse.ArgumentParser(
        description="Manage llvmlite CI workflows selectively or end-to-end."
    )
    parser.add_argument(
        "--repo", default=DEFAULT_REPO,
        help="GitHub repository in 'owner/name' format."
    )
    parser.add_argument(
        "--branch", default=DEFAULT_BRANCH,
        help="Git branch or tag to run workflows on."
    )
    parser.add_argument(
        "--steps", default="all",
        help=(
            "Comma-separated steps: llvmdev, llvmlite_conda, "
            "llvmlite_wheels, download_conda, download_wheels, or all."
        )
    )
    parser.add_argument(
        "--reuse-run",
        action="append",
        help="STEP:RUN_ID to seed state manually"
    )

    args = parser.parse_args()

    if not os.getenv("GH_TOKEN"):
        logging.error("GH_TOKEN environment variable is required.")
        sys.exit(1)

    requested: Set[str] = {step.strip() for step in args.steps.split(',')}
    if "all" in requested:
        requested = ALL_STEPS.copy()

    state = load_state()

        # Apply manual run IDs if provided
    if args.reuse_run:
        for item in args.reuse_run:
            try:
                step, rid = item.split(":")
                state[step] = {"run_id": int(rid), "completed": False}
                logging.info(f"Manually seeded {step} with run ID {rid}")
            except ValueError:
                logging.error(f"Invalid --reuse-run format: {item}")
                sys.exit(1)
        # Persist manual seeds immediately
        save_state(state)
        logging.info(f"State updated with manual reuse-run entries: {args.reuse_run}")

    # Step: llvmdev build
    if "llvmdev" in requested:
        run_or_reuse(
            "llvmdev_build.yml",
            {"platform": "all", "recipe": "all"},
            "llvmdev",
            state,
            args.repo,
            args.branch
        )
        wait_completion("llvmdev", state, args.repo)

    # Step: llvmlite conda build
    if "llvmlite_conda" in requested:
        cond_inputs: Dict[str, str] = {"platform": "all"}
        llvm_entry = state.get("llvmdev", {})
        if llvm_entry.get("run_id") and llvm_entry.get("conclusion") == "success":
            cond_inputs["llvmdev_run_id"] = str(llvm_entry["run_id"])
            logging.info("Using local llvmdev run for conda builder.")
        else:
            logging.info("No successful local llvmdev run; using published llvmdev packages for conda build.")

        run_or_reuse(
            "llvmlite_conda_builder.yml",
            cond_inputs,
            "llvmlite_conda",
            state,
            args.repo,
            args.branch
        )
        wait_completion("llvmlite_conda", state, args.repo)

    # Step: llvmlite wheels build
    if "llvmlite_wheels" in requested:
        wheel_inputs: Dict[str, str] = {}
        llvm_entry = state.get("llvmdev", {})
        if llvm_entry.get("run_id") and llvm_entry.get("conclusion") == "success":
            wheel_inputs["llvmdev_run_id"] = str(llvm_entry["run_id"])
            logging.info("Using local llvmdev run for wheel builders.")
        else:
            logging.info("No successful local llvmdev run; using published llvmdev_for_wheel packages for wheels.")

        for plat in PLATFORMS:
            wf_file = f"llvmlite_{plat}_wheel_builder.yml"
            key = f"wheel_{plat}"
            run_or_reuse(
                wf_file,
                wheel_inputs,
                key,
                state,
                args.repo,
                args.branch
            )
            wait_completion(key, state, args.repo)

    # Step: download conda artifacts
    if "download_conda" in requested:
        download(
            "llvmlite_conda",
            state,
            args.repo,
            Path("artifacts/llvmlite_conda")
        )

    # Step: download wheel artifacts
    if "download_wheels" in requested:
        for key in state:
            if key.startswith("wheel_"):
                download(
                    key,
                    state,
                    args.repo,
                    Path("artifacts/llvmlite_wheels") / key
                )


if __name__ == "__main__":
    main()
