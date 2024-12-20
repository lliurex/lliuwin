# LLiuWin

## IMPORTANT

Bitlocker protected drives are not capable of booting LliuWin. The only available options are: 

- Install to a non-protected partition or disk
- Disable bitlocker protection


## Introduction

Forked from wubiefi.

LliuWin is the Windows LliureX Installer. LliuWin installs LliureX inside a file within a windows partition. It does not require CD burning or dedicated partitions, the installation is a dual boot setup identical to a normal installation.

For generating the system image simply run *./generate_lliuwin_img.sh process [release]*. [More info](https://github.com/lliurex/lliuwin/blob/master/README_IMG.md)


After install finished chroot into the lliuwin disk and run some package integrity checks and ensure that lliuwin-wizard package is installed. If isn't the case then fix the installation with apt wizardry. 

For building the windows installer install msitools and wixl from ubuntu repositories and msi-packager as root from npm (*npm install -global msi-packager*)

Then run *./generate_msi.sh*. [More info](https://github.com/lliurex/lliuwin/blob/master/README_MSI.md)

For more information see: https://github.com/hakuna-m/wubiuefi/wiki

## Compiling


| Make Command         | Description                                                                                                                                                                                                               |
|----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `make`               | Builds lliuwin.exe, note that the first time you run it, you will have to install python inside of Wine, this is performed automatically, just confirm all the default choices in the installation screens that will appear. |
| `make runpy`         | Runs wubi under wine directly from source                                                                                                                                                                                 |
| `make runbin`        | Builds lliuwin and runs the packaged binary under wine                                                                                                                                                                       |
| `make wubizip`       | Creates a special zip file conatining python.exe and non byte compiled python files that is convenient for debugging purposes. Inside of Windows, unzip the archive, then run `python.exe main.py --verbose`              |
| `make pot`           | Generates a gettext template (`/po/wubi.pot`)                                                                                                                                                                             |
| `make check_wine`    | Creates the Wine environment if it doesn't exist.                                                                                                                                                                         |
| `make check_winboot` | Creates the environment for building and signing boot loaders if it doesn't exist.                                                                                                                                        |
| `make winboot`       | Creates the boot loader files (old version)                                                                                                                                                                               |
| `make winboot2`      | Creates the boot loader files (new version)                                                                                                                                                                               |
| `make clean`         | Removes built files                                                                                                                                                                                                       |
| `make distclean`     | Removes built files and environment                                                                                                                                                                                       |


## Code overview

* `/src/winui` : Thin ctypes wrapper around win32 native graphical user interface
* `/src/pylauncher` : Makes python code into an executable, the Python script is examined and all the dependencies are added to an LZMA archive, then an executable header is concatenated to the archive that decompresses it and runs the script using the Python DLL
* `/src/wubi` : The main Wubi application, the code is split between backend and frontend, where each runs in its own thread. The two interact via a tasklist object, where the frontend usually runs a tasklist which is a set of backend tasks. Backends and Frontends are platform specific. For now only the Windows platform is supported.
* `/data` : Settings for Wubi branding and customization
* `/po` : Translations
* `/bin` : Other binary files required at runtime (will be compiled at a later stage)

## Lliuwin tasks

Lliuwin performs the following tasks:

* Fetches information about the running system which will be used during installation
* Checks that the minimum installation requirements are met
* Retrieves required user information via a GUI
* Looks for available local CDs and ISO files
* Downloads the ISO if one is required, using Bittorrent and an HTTP download manager (not supported by lliuwin)
* Checks the ISO/CD MD5 sums and the MD5 signature
* Extracts the kernel and initrd from the ISO
* Adds a new boot entry to the existing windows bootloader
* Prepares a preseed file to be used during the Linux-side installation
* Allocates space for the virtual disk files

*The actual installation is performed within Linux after rebooting the machine.*

## Customization

* Edit the files in data as appropriate and build your image
* You will need to provide an ISO that is similar to the Ubuntu ISO and in particular it must have .disk/info formatted like .disk/info in the Ubuntu ISO
* You must provide a webserver with metalink file, metalink file MD5 checksums and signatures for the MD5 sums
* Add your signing key to `data/trustedkeys.gpg`
* Replace the generated dummy keys in `.key` with your signing keys for Secure Boot
* On the Linux side, the distribution must be capable of booting and rebooting off a loop file, perform an automatic installation and accept the special boot parameters that indicate the local preseed file and ISO image to boot from.

## License

GPL v2. See [LICENSE](./LICENSE)
