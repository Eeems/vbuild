#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh

exists APKBUILD
exists xovi-extensions.post-install
exists qt-resource-rebuilder.post-install
exists webserver-remote.post-install
exists webserver-remote.post-os-upgrade

# Check install variables: expect exactly 3 (main + qt_resource_rebuilder + webserver_remote)
install_count=$(grep -c "^    install='" APKBUILD || true)
main_install=$(grep -c "^install='" APKBUILD || true)
if [ "$main_install" -ne 1 ]; then
	echo "expected 1 main install variable, found $main_install"
	exit 1
fi
if [ "$install_count" -ne 2 ]; then
	echo "expected 2 subpackage install variables, found $install_count"
	exit 1
fi
# Main install should contain xovi-extensions.post-install
if ! grep -q "xovi-extensions.post-install" APKBUILD; then
	echo "main package install script missing from install variable"
	exit 1
fi

# Check subpackage functions have their own install variables
# qt_resource_rebuilder should have qt-resource-rebuilder.post-install
if ! grep -q "qt-resource-rebuilder.post-install" APKBUILD; then
	echo "subpackage qt-resource-rebuilder install script missing"
	exit 1
fi
# webserver_remote should have webserver-remote.post-install and webserver-remote.post-os-upgrade
if ! grep -q "webserver-remote.post-install" APKBUILD; then
	echo "subpackage webserver-remote post-install missing"
	exit 1
fi
if ! grep -q "webserver-remote.post-os-upgrade" APKBUILD; then
	echo "subpackage webserver-remote post-os-upgrade missing"
	exit 1
fi

# Check post-os-upgrade install line in subpackage function
# shellcheck disable=SC2016
if ! grep -Fq 'install -Dm755 "$startdir"/"$pkgname".post-os-upgrade "$pkgdir"/home/root/.vellum/hooks/post-os-upgrade/"$pkgname";' APKBUILD; then
	echo "post-os-upgrade install line missing"
	exit 1
fi

# Check subpackage functions exist in APKBUILD
if ! grep -q "qt_resource_rebuilder()" APKBUILD; then
	echo "subpackage function qt_resource_rebuilder missing"
	exit 1
fi
if ! grep -q "webserver_remote()" APKBUILD; then
	echo "subpackage function webserver_remote missing"
	exit 1
fi

# Check subpackage functions have variables declared
if ! grep -q "pkgdesc=" APKBUILD; then
	echo "subpackage pkgdesc missing"
	exit 1
fi

# Check no automatic variables in output
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

# Check lifecycle file content
if ! grep -q "qt-resource-rebuilder installed" qt-resource-rebuilder.post-install; then
	echo "qt-resource-rebuilder.post-install has wrong content"
	exit 1
fi
if ! grep -q "webserver-remote installed" webserver-remote.post-install; then
	echo "webserver-remote.post-install has wrong content"
	exit 1
fi
if ! grep -q "xovi/rebuild_hashtable" xovi-extensions.post-install; then
	echo "xovi-extensions.post-install has wrong content"
	exit 1
fi

# Check lifecycle files have proper shebang
if ! head -1 qt-resource-rebuilder.post-install | grep -q "#!/bin/sh"; then
	echo "qt-resource-rebuilder.post-install missing shebang"
	exit 1
fi
if ! head -1 webserver-remote.post-install | grep -q "#!/bin/sh"; then
	echo "webserver-remote.post-install missing shebang"
	exit 1
fi
if ! head -1 xovi-extensions.post-install | grep -q "#!/bin/sh"; then
	echo "xovi-extensions.post-install missing shebang"
	exit 1
fi
if ! head -1 webserver-remote.post-os-upgrade | grep -q "#!/bin/sh"; then
	echo "webserver-remote.post-os-upgrade missing shebang"
	exit 1
fi
