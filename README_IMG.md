Lliuwin needs some wizardry in order to work flawlessly.

The shell __generate_lliuwin_img.sh__ does this in an automated way.
## USAGE
```
./generate_lliuwin_img.sh --help
	--process [release]: Make all. Release defaults to $RELEASE
	--allocate [SIZE]: Allocates a file of SIZE ($SIZE by default)
	--debootstrap: Mounts the rootfs file for debootstrap
	--mount [--enable]: Mounts the chroot. If --enable then also mount bindings
	--umount: Umounts the chroot
	--install: Install the meta-package inside the chroot
	--upgrade: Upgrades the image (needs a generated chroot)
	--chroot: chroot to lliuwin image
	--clean: Removes the image
	--meta [lliurex-meta-package]: Sets target metapackage to [lliurex-meta-package]
	--compress: Compress the rootfs image
	--img: Name for the rootfs image
	--help: Shows this missage
```

## CHANGE DEFAULT VALUES
Some values may be adjusted editing the shell. There're no parms for them.

```
#Manages the chroot location
LOCAL_CHROOT=/home/${SUDO_USER}/lliuwin_chroot
#Release (major)
LLX_RELEASE=$(lliurex-version -n | cut -d "." -f1)
#Full image path
LOCAL_IMG=/home/${SUDO_USER}/lliurex${LLX_RELEASE}-latest-lliuwin.img 
#Desired size for the image
SIZE=11G
#Release (one of jammy|focal|noble...)
RELEASE=$(lsb_release -s --codename)
#Meta package for the rootfs
LLIUREX_META=lliurex-meta-desktop-lite
#Required packages
EXTRA_PACKAGES="linux-firmware lliuwin-wizard rebost-gui" 
#Required packages from Ubuntu
UBUNTU_PACKAGES="zram-config" 
```
