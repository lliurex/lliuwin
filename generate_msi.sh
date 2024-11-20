#!/bin/bash

#Don't touch ->
PROJECT="LliuWin"
ARCH="x64"
UPID="00112232-GNUX-LL00-1907-019283746547"
EXE=lliuwin.exe
#<-

VERSION=$(head debian/changelog -n1 | grep -o "[0-9][0-9]\.[0-9]*")
DEVEL="LliureX Team"
DIST=./dist
MSI=${DIST}/lliuwin_installer_x64.msi
ICO=./data/images/lliuwin.ico
BUILD=./build
MAKEOPTS=""

function build
{
	make clean
	make $MAKEOPTS
}

function msi_build
{
	echo "Generating msi"
	echo "--------------"
	cp ${BUILD}/${EXE} ${DIST}
	echo msi-packager -n "$PROJECT" -v "$VERSION" -m "$DEVEL" -a "$ARCH" -u "$UPID" -i $ICO -e "$EXE" $DIST $MSI
	msi-packager -n "$PROJECT" -v "$VERSION" -m "$DEVEL" -a "$ARCH" -u "$UPID" -i $ICO -e "$EXE" $DIST $MSI
	RET=$?
	if [[ $RET -eq 0 ]]
	then
		echo "--------------"
		echo "Generated $MSI"
	else
		echo "##############"
		echo "BUILD FAILED"
		echo "##############"
	fi
}

RET=1
mkdir ${DIST} 2>/dev/null
[ ! -e ${BUILD}/${EXE} ] && build
msi_build

exit $RET
