#!/bin/bash

set -v -e

# values borrowed from:
# https://github.com/numba/numba/blob/main/buildscripts/incremental/setup_conda_environment.sh
conda config --describe
conda config --set remote_connect_timeout_secs 30.15
conda config --set remote_max_retries 10
conda config --set remote_read_timeout_secs 120.2
conda config --set show_channel_urls true
conda info
conda config --show