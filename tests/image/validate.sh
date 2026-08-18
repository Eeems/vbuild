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
owner dist/noarch/entware-rc-0.1-r0.apk
# shellcheck disable=SC2016
if ! grep -Fq 'install -Dm755 "$startdir"/"$pkgname".post-os-upgrade "$pkgdir"/home/root/.vellum/hooks/post-os-upgrade/"$pkgname";' APKBUILD; then
  echo "post-os-upgrade install line missing"
  exit 1
fi
if ! grep -Fq 'postinstall() {' entware-rc.post-upgrade; then
  echo "postinstall() method missing from entware-rc.post-upgrade"
  exit 1
fi

exists entware-rc.build
# shellcheck disable=SC2016
if ! grep -Fq 'sh $(pwd)/$pkgname.build' APKBUILD; then
  echo "pkgname.build invocation missing from APKBUILD"
  exit 1
fi
if ! grep -Fq '#!/bin/sh' entware-rc.build; then
  echo "shebang missing from entware-rc.build"
  exit 1
fi
