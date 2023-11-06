#!/bin/bash
# Copyright 2023 LliureX Team

#This script attempts to create a lliurex system inside a ext3 image

LOCAL_CHROOT=/home/${SUDO_USER}/lliuwin_chroot
LOCAL_IMG=/home/${SUDO_USER}/lliuwin2.img
IMG_SIZE=11G
RELEASE=jammy
if [[ ! "x"$2 == "x" ]]
then
	RELEASE=$2
fi
REMOTE_URL=http://lliurex.net/${RELEASE} 
LLIUREX_META=lliurex-meta-desktop-lite
EXTRA_PACKAGES="linux-firmware lliuwin-wizard"

function mount_img()
{
	if [ $MOUNT -eq 0 ]
	then
		mount $LOCAL_IMG $LOCAL_CHROOT
		if [[ $2 == "--enable" ]]
		then
			echo "Binding mounts"
			mount --bind /dev $LOCAL_CHROOT/dev
			mount --bind /dev/pts $LOCAL_CHROOT/dev/pts
			echo "proc $LOCAL_CHROOT/proc proc defaults 0 0" > /etc/fstab
			echo "sysfs $LOCAL_CHROOT/sys sysfs defaults 0 0" >> /etc/fstab
			mount --bind /sys $LOCAL_CHROOT/sys
		fi
		mount --bind /proc $LOCAL_CHROOT/proc 
		echo "Mount ${LOCAL_CHROOT}: $?"
		MOUNT=1
	fi
}

function debootstrap_img()
{
	mkdir $LOCAL_CHROOT 2>/dev/null
	mount $LOCAL_IMG $LOCAL_CHROOT
	debootstrap  --no-check-gpg --arch amd64 $RELEASE $LOCAL_CHROOT http://lliurex.net/$RELEASE
	echo "LANG=$LANG" >> $LOCAL_CHROOT/etc/profile
	echo "LANGUAGE=$LANGUAGE" >> $LOCAL_CHROOT/etc/profile
	echo "LC_ALL=$LC_ALL" >> $LOCAL_CHROOT/etc/profile
	umount $LOCAL_CHROOT
}

function configure_chroot()
{
	mount_img
	grep -i lliurex.net /etc/apt/sources.list > $LOCAL_CHROOT/etc/apt/sources.list
	touch $LOCAL_CHROOT/etc/mtab
}

function install_meta()
{
	cat << EOF | chroot $LOCAL_CHROOT
	rm /var/cache/apt/archives/*
	apt-get update
	dpkg --configure -a
	rm /var/cache/apt/archives/*
	apt-get install -y $LLIUREX_META
	rm /var/cache/apt/archives/*
	apt-get upgrade -y
	rm /var/cache/apt/archives/*
	apt-get install -y $EXTRA_PACKAGES
	apt-get autoremove -y
	rm /var/cache/apt/archives/*
	rm /vmlinuz /initrd.gz /initrd.img 2>/dev/null
	ln -s /boot/vmlinuz /vmlinuz 
	ln -s /boot/initrd.img /initrd.img
EOF
}

function umount_chroot()
{
	umount $LOCAL_CHROOT/dev/pts
	umount $LOCAL_CHROOT/dev
	umount $LOCAL_CHROOT/proc 
	umount $LOCAL_CHROOT/sys 
	umount $LOCAL_CHROOT
	echo "umount $LOCAL_CHROOT: $?"
	rm $LOCAL_CHROOT/root/.bash_history 2>/dev/null
}

function allocate_img()
{
	echo "Populating $LOCAL_IMG"
	fallocate -l $IMG_SIZE $LOCAL_IMG
	echo "Formatting"
	mkfs.ext3 $LOCAL_IMG
}

function show_help()
{
	printf "\n"
	printf "Helper for building a lliurex rootfs for Lliuwin\n"
	printf "Usage:\n"
	printf "\t$0 [bionic|focal|jammy|...]. The release is optional, defaults to $RELEASE\n"
	printf "Config is done editing this shell\n"
	printf "Options:\n"
	printf "\tprocess: Make all. Usually you want this, other options are only for developing/testing the image.\n"
	printf "\tallocate: Allocates a IMAGE_SIZE file (value defined in script) \n"
	printf "\tdebootstrap: Mounts the rootfs file for debootstrap\n"
	printf "\tmount [--enable]: Mounts the chroot. If --enable then also mount bindings\n"
	printf "\tumount: Umounts the chroot\n"
	printf "\tinstall: Install the meta-package inside the chroot\n"
	printf "\thelp: Shows this missage\n"
	printf "\n"
	exit 0
}

function clean()
{
	umount_chroot
	rm -r $LOCAL_CHROOT
	rm $LOCAL_IMG

}

function only_root()
{
	if [ $UID -ne 0 ]
	then
		echo "Only root allowed"
		exit 1
	fi
	printf "RELEASE: $RELEASE\nURL: $REMOTE_URL\n"
}
#Flag for avoiding duplicated mounts
MOUNT=0
if [ $# -gt 0 ]
then
	case $1 in
		"process")
			only_root
			allocate_img
			debootstrap_img
			configure_chroot
			install_meta
			umount_chroot
			;;
		"allocate")
			only_root
			allocate_img
			;;
		"debootstrap")
			only_root
			debootstrap_img
			;;
		"mount")
			only_root
			configure_chroot
			;;
		"umount")
			only_root
			umount_chroot
			;;
		"install")
			only_root
			configure_chroot
			install_meta
			umount_chroot
			;;
		"clean")
			only_root
			clean
			;;
		*)
			show_help
			;;
	esac
else
	show_help
fi
exit 0
