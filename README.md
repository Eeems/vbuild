# VBuild

Build tool for https://vellum.delivery

## Installation

Grab the latest compiled binary from the releases.

### System requirements

- podman or docker
- openssl
- bash

## Usage

vbuild is based off of alpine's abuild utility. It takes a VELBUILD file, translates it to a [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en) and then uses abuild to create the final package(s).

### VELBUILD Reference

VELBUILD is a superset of [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en). It uses largely the same format, but has a few key extra variables/functions.

#### category

What category that the package is in. This can be any string, but should be kept short.

#### upstream_author

The author of the upstream source of what is being packaged.

#### preinstall

A function containing the contents of $pkgname.pre-install. See [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en#Install_Scripts) for more information.

#### postinstall

A function containing the contents of $pkgname.post-install. See [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en#Install_Scripts) for more information.

#### preupgrade

A function containing the contents of $pkgname.pre-upgrade. See [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en#Install_Scripts) for more information.

#### postupgrade

A function containing the contents of $pkgname.post-upgrade. See [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en#Install_Scripts) for more information.

#### predeinstall

A function containing the contents of $pkgname.pre-deinstall. See [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en#Install_Scripts) for more information.

#### postdeinstall

A function containing the contents of $pkgname.post-install. See [APKBUILD(5)](https://man.archlinux.org/man/APKBUILD.5.en#Install_Scripts) for more information.

#### postosupgrade

A function containing the contents of $pkgname.post-os-upgrade.See [vellum-dev/vellum](https://github.com/vellum-dev/vellum/?tab=readme-ov-file#package-scripts) for more information.

### Configuration files

vbuild will generate keys in `~/.config/vbuild` that will be used to sign any packages produced. You can override these files if you wish to use your own pre-generated keys.

## Building from source

All building is handled with the Makefile. Run `make executable` to create the executable in the `dist/` directory.

### Requirements

- python 3.12-3.13
- python-venv
- podman (If building the builder image)
