#!/bin/bash
set -e
cd "$(dirname "$0")"
source ../lib.sh
ls -l
exists APKBUILD
exists test-systemd.post-install
exists test-systemd.post-upgrade
exists test-systemd.pre-deinstall
exists test-systemd.post-os-upgrade
exists test-systemd-socket.post-install
exists test-systemd-socket.post-upgrade
exists test-systemd-socket.pre-deinstall
exists test-systemd-socket.post-os-upgrade
exists test-systemd-empty.post-upgrade
exists test-systemd-empty.post-install

if ! grep -Fq '!fhs' APKBUILD; then
	echo "Missing !fhs option"
	exit 1
fi

# Check install variable has lifecycle scripts
if ! grep -Fq 'test-systemd.post-install' APKBUILD; then
	echo "Missing test-systemd.post-install in install"
	exit 1
fi
if ! grep -Fq 'test-systemd.post-upgrade' APKBUILD; then
	echo "Missing test-systemd.post-upgrade in install"
	exit 1
fi
if ! grep -Fq 'test-systemd.pre-deinstall' APKBUILD; then
	echo "Missing test-systemd.pre-deinstall in install"
	exit 1
fi

# Check package function copies units to /home/root/.vellum/share/
if ! grep -Fq 'install -Dm644 "$srcdir/foo.service" "$pkgdir/home/root/.vellum/share/test-systemd/foo.service"' APKBUILD; then
	echo "Missing package install for foo.service"
	exit 1
fi
if ! grep -Fq 'install -Dm644 "$srcdir/bar.socket" "$subpkgdir/home/root/.vellum/share/test-systemd-socket/bar.socket"' APKBUILD; then
	echo "Missing package install for bar.socket"
	exit 1
fi

# Check lifecycle scripts have SKIP_SYSTEMD_HANDLING guard
if ! grep -q 'if \[ "$SKIP_SYSTEMD_HANDLING" != "1" \]; then' test-systemd.post-install; then
	echo "Missing SKIP_SYSTEMD_HANDLING guard in post-install"
	exit 1
fi
if ! grep -q 'if \[ "$SKIP_SYSTEMD_HANDLING" != "1" \]; then' test-systemd.post-upgrade; then
	echo "Missing SKIP_SYSTEMD_HANDLING guard in post-upgrade"
	exit 1
fi
if ! grep -q 'if \[ "$SKIP_SYSTEMD_HANDLING" != "1" \]; then' test-systemd.pre-deinstall; then
	echo "Missing SKIP_SYSTEMD_HANDLING guard in pre-deinstall"
	exit 1
fi
if ! grep -q 'if \[ "$SKIP_SYSTEMD_HANDLING" != "1" \]; then' test-systemd.post-os-upgrade; then
	echo "Missing SKIP_SYSTEMD_HANDLING guard in post-os-upgrade"
	exit 1
fi

# Check post-install has expected systemd commands
if ! grep -q '/home/root/.vellum/bin/mount-rw' test-systemd.post-install; then
	echo "Missing mount-rw in post-install"
	exit 1
fi
if ! grep -q 'systemctl enable --now foo.service' test-systemd.post-install; then
	echo "Missing enable for foo.service in post-install"
	exit 1
fi

# Check pre-deinstall has disable
if ! grep -q 'systemctl disable --now foo.service' test-systemd.pre-deinstall; then
	echo "Missing disable in pre-deinstall"
	exit 1
fi

# Check postsosupgrade has enable without mount-rw
if ! grep -q 'systemctl enable --now foo.service' test-systemd.post-os-upgrade; then
	echo "Missing enable in post-os-upgrade"
	exit 1
fi
if grep -q 'mount-rw' test-systemd.post-os-upgrade; then
	echo "Unexpected mount-rw in post-os-upgrade"
	exit 1
fi

if ! grep -Fq 'postinstall() {' test-systemd-empty.post-upgrade; then
	echo "postinstall() method missing from test-systemd-empty.post-upgrade"
	exit 1
fi
if ! grep -Fq 'SKIP_SYSTEMD_HANDLING=1' test-systemd-empty.post-upgrade; then
	echo "SKIP_SYSTEMD_HANDLING=1 missing from test-systemd-empty.post-upgrade"
	exit 1
fi
