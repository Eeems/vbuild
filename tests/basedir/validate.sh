#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/noarch/rmhacks-0.0.11_pre4-r0.apk
owner dist/noarch/rmhacks-0.0.11_pre4-r0.apk
if ! grep -q "builddir=\$srcdir'/rm-hacks-qmd-1c617914af95e2d3b8f25c7c0fd71ef11e21b461/0.0.11-pre4'" APKBUILD; then
  # shellcheck disable=SC2016
  echo '$builddir not set properly'
  exit 1
fi
if grep -qE '^pkgdir=' APKBUILD; then
  # shellcheck disable=SC2016
  echo '$pkgdir present'
  exit 1
fi
if grep -q "srcdir=" APKBUILD; then
  # shellcheck disable=SC2016
  echo '$srcdir present'
  exit 1
fi
if grep -q "startdir=" APKBUILD; then
  # shellcheck disable=SC2016
  echo '$startdir present'
  exit 1
fi
if grep -q "subpkgdir=" APKBUILD; then
  # shellcheck disable=SC2016
  echo '$subpkgdir present'
  exit 1
fi
