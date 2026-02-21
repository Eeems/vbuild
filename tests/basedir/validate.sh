#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/noarch/rmhacks-0.0.11_pre4-r0.apk
if ! grep -q "builddir='x/'\$srcdir'/rm-hacks-qmd-1c617914af95e2d3b8f25c7c0fd71ef11e21b461/0.0.11-pre4'" APKBUILD; then
  echo '$builddir not set properly'
  exit 1
fi
if grep -qE '^pkgdir=' APKBUILD; then
  echo '$pkgdir present'
  exit 1
fi
if grep -q "srcdir=" APKBUILD; then
  echo '$srcdir present'
  exit 1
fi
if grep -q "startdir=" APKBUILD; then
  echo '$startdir present'
  exit 1
fi
if grep -q "subpkgdir=" APKBUILD; then
  echo '$subpkgdir present'
  exit 1
fi
