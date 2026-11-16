#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/noarch/test-no-sourceurl-0.1.0-r0.apk
exists dist/noarch/test-sub-0.1.0-r0.apk
owner dist/noarch/test-no-sourceurl-0.1.0-r0.apk
owner dist/noarch/test-sub-0.1.0-r0.apk

echo "Checking main package license/sources..."
tar -xzf dist/noarch/test-no-sourceurl-0.1.0-r0.apk -C /tmp/test-no-sourceurl 2>/dev/null || true
if [ -f /tmp/test-no-sourceurl/home/root/.vellum/licenses/test-no-sourceurl/LICENSE ]; then
	echo "Main package LICENSE exists"
else
	echo "Main package LICENSE missing"
	exit 1
fi
if [ -f /tmp/test-no-sourceurl/home/root/.vellum/licenses/test-no-sourceurl/SOURCES ]; then
	echo "Main package SOURCES exists"
	cat /tmp/test-no-sourceurl/home/root/.vellum/licenses/test-no-sourceurl/SOURCES
else
	echo "Main package SOURCES missing"
	exit 1
fi

echo "Checking subpackage license/sources..."
tar -xzf dist/noarch/test-sub-0.1.0-r0.apk -C /tmp/test-sub 2>/dev/null || true
if [ -f /tmp/test-sub/home/root/.vellum/licenses/test-sub/LICENSE ]; then
	echo "Subpackage LICENSE exists"
else
	echo "Subpackage LICENSE missing"
	exit 1
fi
if [ -f /tmp/test-sub/home/root/.vellum/licenses/test-sub/SOURCES ]; then
	echo "Subpackage SOURCES exists"
	cat /tmp/test-sub/home/root/.vellum/licenses/test-sub/SOURCES
else
	echo "Subpackage SOURCES missing"
	exit 1
fi

if grep -q "https://github.com/asivery/appload-rmstream" /tmp/test-no-sourceurl/home/root/.vellum/licenses/test-no-sourceurl/SOURCES; then
	echo "Main package SOURCES defaults to url"
else
	echo "Main package SOURCES has wrong URL (should be url)"
	exit 1
fi

if grep -q "https://github.com/asivery/appload-rmstream" /tmp/test-sub/home/root/.vellum/licenses/test-sub/SOURCES; then
	echo "Subpackage SOURCES defaults to url"
else
	echo "Subpackage SOURCES has wrong URL (should be url)"
	exit 1
fi

if grep -q "GPL-3.0" /tmp/test-no-sourceurl/home/root/.vellum/licenses/test-no-sourceurl/LICENSE 2>/dev/null; then
	echo "Main package LICENSE copied from local file"
else
	echo "Main package LICENSE content may be wrong"
	exit 1
fi

echo "All sourceurl defaulting tests passed!"
