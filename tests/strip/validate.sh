#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/x86_64/test-strip-1.0-r0.apk
exists dist/x86_64/test-strip-sub-1.0-r0.apk
owner dist/x86_64/test-strip-1.0-r0.apk

if ! grep -Fq 'find "$srcdir" -type f -print0' APKBUILD; then
	echo "Missing srcdir strip snippet in build()"
	exit 1
fi
if ! grep -Fq 'xargs -0 "${STRIP:-strip}" --strip-unneeded' APKBUILD; then
	echo "Missing strip command"
	exit 1
fi
if ! grep -Fq '!strip' APKBUILD; then
	echo "Missing !strip option"
	exit 1
fi
if readelf -S pkg/test-strip/usr/bin/hello | grep -q '\.symtab'; then
	echo "hello is not stripped"
	exit 1
fi
if ! grep -q 'hello' pkg/test-strip/usr/share/test-strip/hello-copy.c; then
	echo "Non-ELF file missing"
	exit 1
fi
if readelf -S pkg/test-strip-sub/usr/bin/hello-copy | grep -q '\.symtab'; then
	echo "hello-copy is not stripped"
	exit 1
fi
