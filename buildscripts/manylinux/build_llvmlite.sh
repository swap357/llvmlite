#!/bin/bash
set -ex

cd $(dirname $0)
source ./prepare_miniconda.sh $1


# Move to source root
cd ../..
sourceroot=$(pwd)

# Make conda environmant for llvmdev
pyver=$2
envname="llvmbase"
outputdir="/root/llvmlite/docker_output"
LLVMDEV_PKG_PATH=${3:-""}

ls -l /opt/python/$pyver/bin

conda create -y -n $envname
conda activate $envname
# Install llvmdev

if [ -n "$LLVMDEV_PKG_PATH" ] && [ -d "$LLVMDEV_PKG_PATH" ]; then
    echo "=== Verifying llvmdev packages (container) ==="
    echo "LLVMDEV_PKG_PATH: $LLVMDEV_PKG_PATH"
    echo "Directory exists: $(test -d "$LLVMDEV_PKG_PATH" && echo "YES" || echo "NO")"
    echo "Contents:"
    ls -la "$LLVMDEV_PKG_PATH"
    echo "Package files:"
    find "$LLVMDEV_PKG_PATH" -name "*.conda" -o -name "*.tar.bz2" | head -10

    # Find and install the llvmdev package directly
    LLVMDEV_PKG=$(find "$LLVMDEV_PKG_PATH" -name "llvmdev*.conda" -o -name "llvmdev*.tar.bz2" | head -1)
    if [ -n "$LLVMDEV_PKG" ]; then
        echo "Installing package: $LLVMDEV_PKG"
        conda install -y "$LLVMDEV_PKG" --no-deps
    else
        echo "ERROR: No llvmdev package found in $LLVMDEV_PKG_PATH"
        exit 1
    fi
else
    if [[ $(uname -m) == "aarch64" ]] ; then
        conda install -y numba/label/manylinux_2_28::llvmdev --no-deps
    elif [[ $(uname -m) == "x86_64" ]] ; then
        conda install -y numba/label/manylinux_2_17::llvmdev --no-deps
    else
        echo "Error: Unsupported architecture: $(uname -m)"
        exit 1
    fi
fi

# Prepend builtin Python Path
export PATH=/opt/python/$pyver/bin:$PATH

echo "Using python: $(which python)"

# Python 3.12+ won't have setuptools pre-installed
pip install setuptools

# Clean up
python setup.py clean

# Build wheel
distdir=$outputdir/dist_$(uname -m)_$pyver
rm -rf $distdir
python setup.py bdist_wheel -d $distdir

# Audit wheel
cd $distdir
auditwheel --verbose repair *.whl

cd wheelhouse
ls
