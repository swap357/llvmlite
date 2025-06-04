#!/usr/bin/env python

import os
from pathlib import Path

event = os.environ.get("GITHUB_EVENT_NAME")
label = os.environ.get("GITHUB_LABEL_NAME")

print(f"Evaluating trigger: event='{event}', label='{label}'")

# Determine if workflow should run
if event == "pull_request":
    print("pull_request detected - running workflow")
    matrix = True
elif event == "label" and label == "gha_build_and_test":
    print("Build label detected - running workflow")
    matrix = True
elif event == "workflow_dispatch":
    print("workflow_dispatch detected - running workflow")
    matrix = True
else:
    print("No matching trigger found - skipping workflow")
    matrix = False

Path(os.environ["GITHUB_OUTPUT"]).write_text(f"matrix={str(matrix).lower()}")
