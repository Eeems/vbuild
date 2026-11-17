#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/noarch/test-sourceurl-0.1.0-r0.apk
exists dist/noarch/subpackage-0.1.0-r0.apk
owner dist/noarch/test-sourceurl-0.1.0-r0.apk
owner dist/noarch/subpackage-0.1.0-r0.apk
exists pkg/test-sourceurl/home/root/.vellum/licenses/test-sourceurl/SOURCES
exists pkg/subpackage/home/root/.vellum/licenses/subpackage/SOURCES
exists pkg/test-sourceurl/home/root/.vellum/licenses/test-sourceurl/LICENSE
exists pkg/subpackage/home/root/.vellum/licenses/subpackage/LICENSE
