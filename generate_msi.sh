#!/bin/bash
PROJECT="LliuWin"
VERSION="23.01"
DEVEL="LliureX Team"
ARCH="x64"
UPID="00112232-GNUX-LL00-1907-019283746547"
DIST=./dist
MSI=${DIST}/lliuwin_installer_x64.msi
ICO=./data/images/lliuwin.ico
BUILD=./build
EXE=lliuwin.exe
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
