#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
if ! grep -q "sha512sums=" APKBUILD; then
  echo 'sha512sums missing from APKBUILD'
  exit 1
fi
if ! grep -q "sha512sums=" VELBUILD; then
  echo 'sha512sums missing from VELBUILD'
  exit 1
fi
