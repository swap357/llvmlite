#!/bin/bash

set -x

if [[ $(uname) == Darwin ]]; then
  # The following is suggested in https://docs.conda.io/projects/conda-build/en/latest/resources/compiler-tools.html?highlight=SDK#macos-sdk
  wget -q https://github.com/phracker/MacOSX-SDKs/releases/download/11.3/MacOSX10.10.sdk.tar.xz
  shasum -c ./buildscripts/incremental/MacOSX10.10.sdk.checksum
  tar -xf ./MacOSX10.10.sdk.tar.xz
  
  # Define SDK paths and version once
  SDK_DIR=`pwd`/MacOSX10.10.sdk
  export SDKROOT=${SDK_DIR}
  export CONDA_BUILD_SYSROOT=${SDK_DIR}
  export macos_min_version=10.10
  SYSROOT_DIR=${CONDA_BUILD_SYSROOT}
  CFLAG_SYSROOT="--sysroot ${SYSROOT_DIR}"
  export MACOSX_DEPLOYMENT_TARGET=10.10

  if [[ $build_platform == osx-arm64 ]]; then
      CLANG_PKG_SELECTOR=clangxx_osx-arm64=14
  else
      CLANG_PKG_SELECTOR=clangxx_osx-64=14
  fi

  ${SYS_PREFIX}/bin/conda create -y -p ${SRC_DIR}/bootstrap ${CLANG_PKG_SELECTOR}
  export PATH=${SRC_DIR}/bootstrap/bin:${PATH}
  CONDA_PREFIX=${SRC_DIR}/bootstrap \
    . ${SRC_DIR}/bootstrap/etc/conda/activate.d/*

  # Set compiler flags using the defined SDK
  export CXXFLAGS=${CFLAGS}" -mmacosx-version-min=${MACOSX_DEPLOYMENT_TARGET}"
  export CFLAGS=${CFLAGS}" -mmacosx-version-min=${MACOSX_DEPLOYMENT_TARGET}"

  # export LLVM_CONFIG explicitly as the one installed from llvmdev
  # in the build root env, the one in the bootstrap location needs to be ignored.
  export LLVM_CONFIG="${PREFIX}/bin/llvm-config"
  ${LLVM_CONFIG} --version
fi

if [ -n "$MACOSX_DEPLOYMENT_TARGET" ]; then
    export MACOSX_DEPLOYMENT_TARGET=10.10
fi


# This is the clang compiler prefix
if [[ $build_platform == osx-arm64 ]]; then
    DARWIN_TARGET=arm64-apple-darwin20.0.0
else
    DARWIN_TARGET=x86_64-apple-darwin13.4.0
fi

export PYTHONNOUSERSITE=1
# Enables static linking of stdlibc++
export LLVMLITE_CXX_STATIC_LINK=1

$PYTHON setup.py build --force
$PYTHON setup.py install
