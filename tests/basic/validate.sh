#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists entware-rc.post-install
exists entware-rc.post-os-upgrade
exists entware-rc.post-upgrade
exists entware-rc.pre-deinstall
exists dist/noarch/entware-rc-0.1-r0.apk
if grep -q "builddir=" APKBUILD; then
  echo '$builddir present'
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
