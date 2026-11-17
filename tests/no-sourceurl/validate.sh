#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/noarch/test-no-sourceurl-0.1.0-r0.apk
exists dist/noarch/subpackage-0.1.0-r0.apk
owner dist/noarch/test-no-sourceurl-0.1.0-r0.apk
owner dist/noarch/subpackage-0.1.0-r0.apk
exists pkg/test-no-sourceurl/home/root/.vellum/licenses/test-no-sourceurl/SOURCES
exists pkg/subpackage/home/root/.vellum/licenses/subpackage/SOURCES
