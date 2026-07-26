#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists test-triggers.trigger
exists test-triggers-sub.trigger

# Check triggers variable in APKBUILD
if ! grep -Fq 'triggers=' APKBUILD; then
	echo "Missing triggers variable in APKBUILD"
	exit 1
fi
if ! grep -Fq "test-triggers.trigger=/usr/share/man:/usr/local/share/man:/lib/modules/*" APKBUILD; then
	echo "Missing main package trigger paths in APKBUILD"
	exit 1
fi

# Check subpackage triggers variable
if ! grep -Fq 'test-triggers-sub.trigger=/usr/share/doc' APKBUILD; then
	echo "Missing subpackage trigger paths in APKBUILD"
	exit 1
fi

# Check trigger file content
if ! grep -q '#!/bin/sh' test-triggers.trigger; then
	echo "Missing shebang in trigger file"
	exit 1
fi
if ! grep -q 'echo "triggered"' test-triggers.trigger; then
	echo "Missing trigger body"
	exit 1
fi
if ! grep -q '#!/bin/sh' test-triggers-sub.trigger; then
	echo "Missing shebang in subpackage trigger file"
	exit 1
fi
if ! grep -q 'echo "subpackage triggered"' test-triggers-sub.trigger; then
	echo "Missing subpackage trigger body"
	exit 1
fi

# Check no automatic variables in output
if grep -q "builddir=" APKBUILD; then
  # shellcheck disable=SC2016
  echo '$builddir present'
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

# Check trigger function is not in APKBUILD
if grep -q 'trigger()' APKBUILD; then
	echo "trigger() function should not be in APKBUILD"
	exit 1
fi
