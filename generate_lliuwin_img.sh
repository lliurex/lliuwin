#!/bin/bash
# Copyright 2023 LliureX Team

#This script attempts to create a lliurex system inside a ext3 image

LOCAL_CHROOT=/home/${SUDO_USER}/lliuwin_chroot
LOCAL_IMG=/home/${SUDO_USER}/lliuwin2.img
SIZE=11G
RELEASE=jammy
LLIUREX_META=lliurex-meta-desktop-lite
EXTRA_PACKAGES="linux-firmware lliuwin-wizard"
UBUNTU_PACKAGES="zram-config"

function show_help()
{
	printf "\n"
	printf "Helper for building a lliurex rootfs for Lliuwin\n"
	printf "Usage:\n"
	printf "\t$0 --OPTION [option args]. The release is optional, defaults to $RELEASE\n"
	printf "Config of extra-packages is done editing this shell\n"
	printf "Options:\n"
	printf "\t--process [release]: Make all. Usually you want this. Release defaults to $RELEASE\n"
	printf "\t--allocate [SIZE]: Allocates a file of SIZE ($SIZE by default)\n"
	printf "\t--debootstrap: Mounts the rootfs file for debootstrap\n"
	printf "\t--mount [--enable]: Mounts the chroot. If --enable then also mount bindings\n"
	printf "\t--umount: Umounts the chroot\n"
	printf "\t--install: Install the meta-package inside the chroot\n"
	printf "\t--chroot: chroot to lliuwin image\n"
	printf "\t--clean: Removes the image\n"
	printf "\t--meta lliurex-meta-package: Sets target metapackage to lliurex-meta-package\n"
	printf "\t--help: Shows this missage\n"
	printf "\n"
	exit 0
}


function generate_sources
{
	echo "deb http://lliurex.net/$RELEASE $RELEASE main multiverse preschool restricted universe">$LOCAL_CHROOT/etc/apt/sources.list
	echo "deb http://lliurex.net/$RELEASE $RELEASE-security main multiverse restricted universe">>$LOCAL_CHROOT/etc/apt/sources.list
	echo "deb http://lliurex.net/$RELEASE $RELEASE-updates main multiverse restricted universe">>$LOCAL_CHROOT/etc/apt/sources.list
}

function mount_img()
{
	if [ -z $CHKMOUNT  ]
	then
		mkdir $LOCAL_CHROOT 2>/dev/null
		EMPTY="$(ls ${LOCAL_CHROOT})"
		if [ ${#EMPTY} -gt 0 ]
		then
			echo "$LOCAL_CHROOT seems not empty. Not mounting"
			return
		fi
		mount $LOCAL_IMG $LOCAL_CHROOT
		if [ ! -z $ENABLE ]
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
		CHKMOUNT=1
	else
		echo "$LOCAL_CHROOT already mounted"
		return
	fi
}

function debootstrap_img()
{
	mkdir $LOCAL_CHROOT 2>/dev/null
	mount $LOCAL_IMG $LOCAL_CHROOT
	debootstrap  --no-check-gpg --arch amd64 $RELEASE $LOCAL_CHROOT http://lliurex.net/$RELEASE
	if [ $? -ne 0 ]
	then 
		echo "************ ERROR **********"
		echo "There's no release named $RELEASE"
		exit 1
	fi
	echo "LANG=$LANG" >> $LOCAL_CHROOT/etc/profile
	echo "LANGUAGE=$LANGUAGE" >> $LOCAL_CHROOT/etc/profile
	echo "LC_ALL=$LC_ALL" >> $LOCAL_CHROOT/etc/profile
	umount $LOCAL_CHROOT
}

function configure_chroot()
{
	mount_img
	generate_sources
	touch $LOCAL_CHROOT/etc/mtab
}

function enter_chroot()
{
	chroot $LOCAL_CHROOT
}

function install_meta()
{
	if [ ${#EXTRA_PACKAGES} -gt 0 ]
	then
		EXTRA_INSTALL="apt-get install -y $EXTRA_PACKAGES"
	fi
	if [ ${#UBUNTU_PACKAGES} -gt 0 ]
	then
		UBUNTU_INSTALL="echo deb http://archive.ubuntu.com/ubuntu/ $RELEASE main multiverse restricted universe >>/etc/apt/sources.list;echo deb http://archive.ubuntu.com/ubuntu/ $RELEASE-security main multiverse restricted universe >>/etc/apt/sources.list;echo deb http://archive.ubuntu.com/ubuntu/ $RELEASE-updates main multiverse restricted universe >>/etc/apt/sources.list;apt-get update -y;apt-get install -y $UBUNTU_PACKAGES"
	fi
	cat << EOF | chroot $LOCAL_CHROOT
	rm /var/cache/apt/archives/*
	apt-get update
	dpkg --configure -a
	apt clean
	apt-get install -y $LLIUREX_META
	apt-get install -f -y
	apt clean
	lliurex-upgrade -u
	$EXTRA_INSTALL
	$UBUNTU_INSTALL
	apt-get autoremove -y
	apt clean
	rm /vmlinuz /initrd.gz /initrd.img 2>/dev/null
	ln -s /boot/vmlinuz /vmlinuz 
	ln -s /boot/initrd.img /initrd.img
EOF
	generate_sources
}

function umount_chroot()
{
	umount $LOCAL_CHROOT/dev/pts
	umount $LOCAL_CHROOT/dev
	umount $LOCAL_CHROOT/proc 
	umount $LOCAL_CHROOT/sys 
	umount $LOCAL_CHROOT
	if [ $?==0 ]
	then
		echo "$LOCAL_CHROOT disabled"
		rm $LOCAL_CHROOT/root/.bash_history 2>/dev/null
		rm $LOCAL_CHROOT/root/var/cache/apt/archives/* 2>/dev/null
	else
		echo "umount ERROR $LOCAL_CHROOT: $?"
	fi
}

function allocate_img()
{
	echo "Populating $LOCAL_IMG"
	if [ -n $SIZE ] && [ "$SIZE" -eq "$SIZE" 2>/dev/null ] 
	then
		SIZE="${SIZE}G"
	fi
	
	fallocate -l $SIZE $LOCAL_IMG
	echo "Formatting"
	mkfs.ext4 $LOCAL_IMG
}

function compress_img
{
	rm -v $LOCAL_IMG.tar.xz 2>/dev/null
	echo "Compressing $LOCAL_IMG"
FROMSIZE=`du -sk --apparent-size ${LOCAL_IMG} | cut -f 1`;
CHECKPOINT=`echo ${FROMSIZE}/50 | bc`;
echo "Estimated: [==================================================]";

echo -n "Progress:  ["
tar --transform='s!.*/!!' -c --record-size=1K --checkpoint="${CHECKPOINT}" --checkpoint-action="ttyout=>" -f - "${LOCAL_IMG}" 2>/dev/null | xz > "$(dirname ${LOCAL_IMG})/$(basename ${LOCAL_IMG}).tar.xz" 
echo "]"

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
}


#### MAIN ####

ACTION=0
while [ ! -z $1 ]
do
	case $1 in
		"--enable")
			ENABLE=1
			;;
		"--process")
			PROCESS=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--allocate")
			ALLOCATE=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--mount")
			MOUNT=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--umount")
			UMOUNT=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--debootstrap")
			DEBOOTSTRAP=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--install")
			INSTALL=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--chroot")
			CHROOT=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--meta")
			META=1
			;;
		"--compress")
			COMPRESS=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--clean")
			CLEAN=1
			ACTION=$(expr $ACTION + 1)
			;;
		"--help")
			show_help
			;;
		"lliurex-"*)
			[ ! -z $META ] && LLIUREX_META=$1
			;;
		[0-9]*)
			[ ! -z $ALLOCATE ] && SIZE=$1
			;;
		*)
			RELEASE=$1
			;;
	esac
	shift
done

if [ $ACTION -ne 1 ]
then
	echo ""
	echo "*****"
	echo "/*Only one action allowed*/"
	echo "*****"
	show_help
fi

only_root
if [ ! -z $PROCESS ]
then
	allocate_img
	debootstrap_img
	configure_chroot
	install_meta
	umount_chroot
	compress_img
elif [ ! -z $ALLOCATE ]
then
	allocate_img
elif [ ! -z $DEBOOTSTRAP ]
then
	debootstrap_img
elif [ ! -z $MOUNT ]
then
	configure_chroot
elif [ ! -z $UMOUNT ]
then
	umount_chroot
elif [ ! -z $INSTALL ]
then
	ENABLE=1
	configure_chroot
	install_meta
	umount_chroot
elif [ ! -z $CHROOT ]
then
	ENABLE=1
	configure_chroot
	enter_chroot
	umount_chroot
elif [ ! -z $COMPRESS ]
then
	compress_img
elif [ ! -z $CLEAN ]
then
	clean
else
	show_help
fi
exit 0
