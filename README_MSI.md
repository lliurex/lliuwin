After lliuwin is compiled a *msi package-installer must be populated.
The shell __generate_msi.sh__ populates one automatically. 

## REQUIREMENTS
 - apt-get install msitools wixl
 - sudo npm install -global msi-packager

## USAGE
As simply as
```
./generate_msi.sh
```

## CUSTOMIZATION
Some values could be configured from the script itself:
```
#Package release
VERSION:"23.01"
#Developer info
DEVEL="Lliurex Team"
#Target arch
ARCH="x64"
#Output dir
DIST=./dist
#MSI path
MSI=${DIST}/lliuwin_installer_${ARCH}.msi
#Build dir
BUILD=./build
#Options for make command
MAKEOPTS=""
```
## NOTE
As 2023-11-27 msi-packager from npm contains a critcal bug and fails:
```
TypeError [ERR_INVALID_CALLBACK]: Callback must be a function. Received undefined
    at maybeCallback (fs.js:145:9)
    at Object.write (fs.js:646:14)
    at /usr/local/lib/node_modules/msi-packager/index.js:33:10
    at /usr/local/lib/node_modules/msi-packager/generate-xml.js:15:5
    at /usr/local/lib/node_modules/msi-packager/generate-xml.js:166:7
    at /usr/local/lib/node_modules/msi-packager/node_modules/async-each/index.js:24:44
    at /usr/local/lib/node_modules/msi-packager/generate-xml.js:158:11
    at FSReqCallback.oncomplete (fs.js:169:5) {
  code: 'ERR_INVALID_CALLBACK'
}
```

For fix it's needed to edit /usr/local/lib/node_modules/msi-packager/index.js and fix the offending write call:

```
function writeXml(options, cb) {
  temp.open('msi-packager', function(err, info) {
  generateXml(options, function(err, xml) {
-  fs.write(info.fd, xml)
+   fs.write(info.fd, xml,function (err) {
+     if (err) return cb(err)
+     cb(null, info.path)
+   })
```
