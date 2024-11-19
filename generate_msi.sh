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
echo "Generating msi"
mkdir ${DIST} 2>/dev/null
cp ${BUILD}/${EXE} ${DIST}
echo msi-packager -n "$PROJECT" -v "$VERSION" -m "$DEVEL" -a "$ARCH" -u "$UPID" -i $ICO -e "$EXE" $DIST $MSI
msi-packager -n "$PROJECT" -v "$VERSION" -m "$DEVEL" -a "$ARCH" -u "$UPID" -i $ICO -e "$EXE" $DIST $MSI
if [[ $? -eq 0 ]]
then
	echo "Generated $MSI"
fi

exit $?
