#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists dist/x86_64/test-strip-1.0-r0.apk
exists dist/x86_64/test-strip-sub-1.0-r0.apk
owner dist/x86_64/test-strip-1.0-r0.apk

exists test-strip.build
if ! grep -Fq 'find "$srcdir" -type f -print0' test-strip.build; then
	echo "Missing srcdir strip snippet in build script"
	exit 1
fi
if ! grep -Fq 'xargs -0 -r "${STRIP:-strip}" --strip-unneeded' test-strip.build; then
	echo "Missing strip command"
	exit 1
fi
if ! grep -Fq '!strip' APKBUILD; then
	echo "Missing !strip option"
	exit 1
fi
exists pkg/test-strip/usr/bin/hello
if ! readelf -S pkg/test-strip/usr/bin/hello >/dev/null; then
	echo "Unable to inspect hello binary"
	exit 1
fi
if readelf -S pkg/test-strip/usr/bin/hello | grep -q '\.symtab'; then
	echo "hello is not stripped"
	exit 1
fi
exists pkg/test-strip/usr/share/test-strip/hello-copy.c
if ! grep -q 'hello' pkg/test-strip/usr/share/test-strip/hello-copy.c; then
	echo "Non-ELF file missing"
	exit 1
fi
exists pkg/test-strip-sub/usr/bin/hello-copy
if ! readelf -S pkg/test-strip-sub/usr/bin/hello-copy >/dev/null; then
	echo "Unable to inspect hello-copy binary"
	exit 1
fi
if readelf -S pkg/test-strip-sub/usr/bin/hello-copy | grep -q '\.symtab'; then
	echo "hello-copy is not stripped"
	exit 1
fi
