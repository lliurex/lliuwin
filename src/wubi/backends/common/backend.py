# Copyright (c) 2008 Agostino Russo
#
# Written by Agostino Russo <agostino.russo@gmail.com>
#
# This file is part of Wubi the Win32 Ubuntu Installer.
#
# Wubi is free software; you can redistribute it and/or modify
# it under 5the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2.1 of
# the License, or (at your option) any later version.
#
# Wubi is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import sys
import os
import tempfile
import locale
import struct
import logging
import time
import gettext
import glob
import shutil
import ConfigParser
import btdownloader
import downloader
import subprocess

from metalink import parse_metalink
from tasklist import ThreadedTaskList, Task
from distro import Distro
from mappings import lang_country2linux_locale
from utils import join_path, run_nonblocking_command, md5_password, copy_file, read_file, write_file, get_file_hash, reversed, find_line_in_file, unix_path, rm_tree, spawn_command
from signature import verify_gpg_signature
from wubi import errors
from os.path import abspath

log = logging.getLogger("CommonBackend")

class Backend(object):
    '''
    Implements non-platform-specific functionality
    Subclasses need to implement platform-specific getters
    '''
    def __init__(self, application):
        self.application = application
        self.info = application.info
        #~ if hasattr(sys,'frozen') and sys.frozen:
            #~ root_dir = dirname(abspath(sys.executable))
        #~ else:
            #~ root_dir = ''
        #~ self.info.root_dir = abspath(root_dir)
        self.info.temp_dir = join_path(self.info.root_dir, 'temp')
        self.info.data_dir = join_path(self.info.root_dir, 'data')
        self.info.bin_dir = join_path(self.info.root_dir, 'bin')
        self.info.image_dir = join_path(self.info.data_dir, 'images')
        self.info.translations_dir = join_path(self.info.root_dir, 'translations')
        self.info.trusted_keys = join_path(self.info.data_dir, 'trustedkeys.gpg')
        self.info.application_icon = join_path(self.info.image_dir, self.info.application_name.capitalize() + ".ico")
        self.info.icon = self.info.application_icon
        self.info.iso_md5_hashes = {}
        log.debug('data_dir=%s' % self.info.data_dir)
        if self.info.locale:
            locale.setlocale(locale.LC_ALL, self.info.locale)
            log.debug('user defined locale = %s' % self.info.locale)
        gettext.install(self.info.application_name, localedir=self.info.translations_dir, unicode=True, names=['ngettext'])

    def get_installation_tasklist(self):
        self.cache_cd_path()
        self.dimage_path = self.info.distro.diskimage
        self.cache_img_path()
        self.iso_path = self.info.distro.iso_path
        # don't use diskimage for a FAT32 target directory
        #if self.dimage_path and not self.cd_path and not self.iso_path and not self.info.target_drive.is_fat():
		#Lliurex-Live boots from iso, Lllurex from img
        if self.info.distro.name=='LliureX':
            if not self.info.target_drive.is_fat():
                 tasks = [
                 Task(self.select_target_dir,
                      description=_("Selecting the target directory")),
                 Task(self.create_dir_structure,
                      description=_("Creating the directories")),
                 Task(self.create_uninstaller,
                      description=_("Creating the uninstaller")),
                 Task(self.create_preseed_diskimage,
                      description=_("Creating a preseed file")),
                 Task(self.copy_installation_files, description=_("Copying installation files")),
                 Task(self.get_diskimage,
                      description=_("Retrieving installation files")),
                 Task(self.extract_diskimage, description=_("Extracting")),
		     	#Task(self.extract_kernel, description=_("Extracting the kernel")),
                 Task(self.choose_disk_sizes, description=_("Choosing disk sizes")),
                 Task(self.expand_diskimage,
                      description=_("Expanding")),
                 Task(self.create_swap_diskimage,
                      description=_("Creating virtual memory")),
                 Task(self.modify_bootloader,
                      description=_("Adding a new bootloader entry")),
                 Task(self.modify_grub_configuration, description=_("Setting up installation boot menu")),
#                 Task(self.diskimage_bootloader,
#                      description=_("Installing the bootloader")),
            ]
        else:
            tasks = [
            Task(self.select_target_dir, description=_("Selecting the target directory")),
            Task(self.create_dir_structure, description=_("Creating the installation directories")),
            Task(self.uncompress_target_dir, description=_("Uncompressing files")),
            Task(self.create_uninstaller, description=_("Creating the uninstaller")),
            Task(self.copy_installation_files, description=_("Copying installation files")),
            Task(self.get_iso, description=_("Retrieving installation files")),
            Task(self.extract_kernel, description=_("Extracting the kernel")),
            Task(self.choose_disk_sizes, description=_("Choosing disk sizes")),
            Task(self.create_preseed, description=_("Creating a preseed file")),
            Task(self.modify_bootloader, description=_("Adding a new bootloader entry")),
            Task(self.modify_grub_configuration, description=_("Setting up installation boot menu")),
            Task(self.create_virtual_disks, description=_("Creating the virtual disks")),
            Task(self.uncompress_files, description=_("Uncompressing files")),
            Task(self.eject_cd, description=_("Ejecting the CD")),
            ]
        description = _("Installing %(distro)s-%(version)s") % dict(distro=self.info.distro.name, version=self.info.version)
        tasklist = ThreadedTaskList(description=description, tasks=tasks)
        return tasklist

    def get_cdboot_tasklist(self):
        self.cache_cd_path()
        tasks = [
            Task(self.select_target_dir, description=_("Selecting the target directory")),
            Task(self.create_dir_structure, description=_("Creating the installation directories")),
            Task(self.uncompress_target_dir, description=_("Uncompressing files")),
            Task(self.create_uninstaller, description=_("Creating the uninstaller")),
            Task(self.copy_installation_files, description=_("Copying installation files")),
            Task(self.use_cd, description=_("Extracting CD content")),
            Task(self.extract_kernel, description=_("Extracting the kernel")),
            Task(self.create_preseed_cdboot, description=_("Creating a preseed file")),
            Task(self.modify_bootloader, description=_("Adding a new bootloader entry")),
            Task(self.modify_grub_configuration, description=_("Setting up installation boot menu")),
            Task(self.uncompress_files, description=_("Uncompressing files")),
            Task(self.eject_cd, description=_("Ejecting the CD")),
            ]
        tasklist = ThreadedTaskList(description=_("Installing CD boot helper"), tasks=tasks)
        return tasklist

    def get_reboot_tasklist(self):
        tasks = [
            Task(self.reboot, description=_("Rebooting")),
            ]
        tasklist = ThreadedTaskList(description=_("Rebooting"), tasks=tasks)
        return tasklist

    def get_uninstallation_tasklist(self):
        tasks = [
            Task(self.undo_bootloader, _("Remove bootloader entry")),
            Task(self.remove_target_dir, _("Remove target dir")),
            Task(self.remove_registry_key, _("Remove registry key")),]
        tasklist = ThreadedTaskList(description=_("Uninstalling %s") % self.info.previous_distro_name, tasks=tasks)
        return tasklist

    def show_info(self):
        log.debug("Showing info")
        os.startfile(self.info.cd_distro.website)

    def fetch_basic_info(self):
        '''
        Basic information required by the application dispatcher select_task()
        '''
        log.debug("Fetching basic info...")
        self.info.uninstall_before_install = False
        self.info.original_exe = self.get_original_exe()
        self.info.platform = self.get_platform()
        self.info.osname = self.get_osname()
        if not self.info.language:
            self.info.language, self.info.encoding = self.get_language_encoding()
        self.info.environment_variables = os.environ
        self.info.arch = self.get_arch()
        if self.info.force_i386:
            log.debug("Forcing 32 bit arch")
            self.info.arch = "i386"
        self.info.check_arch = (self.info.arch == "i386")
        self.info.distro = None
        self.info.distros = self.get_distros()
        distros = [((d.name.lower(), d.arch), d) for d in  self.info.distros]
        self.info.distros_dict = dict(distros)
        self.fetch_host_info()
        self.info.previous_uninstaller_path = self.get_uninstaller_path()
        self.info.previous_target_dir = self.get_previous_target_dir()
        self.info.previous_distro_name = self.get_previous_distro_name()
        self.info.keyboard_layout, self.info.keyboard_variant = self.get_keyboard_layout()
        if not self.info.locale:
            self.info.locale = self.get_locale(self.info.language)
        self.info.total_memory_mb = self.get_total_memory_mb()
        self.info.dimage_path, self.info.iso_distro = self.find_any_img()
        self.info.iso_path, self.info.iso_distro = self.find_any_iso()
        self.info.cd_path, self.info.cd_distro = self.find_any_cd()

    def get_distros(self):
        isolist_path = join_path(self.info.data_dir, 'isolist.ini')
        distros = self.parse_isolist(isolist_path)
        return distros

    def get_original_exe(self):
        if self.info.original_exe:
            original_exe = self.info.original_exe
        else:
            original_exe = abspath(sys.argv[0])
        log.debug("original_exe=%s" % original_exe)
        return original_exe

    def get_locale(self, language_country, fallback="en_US"):
        _locale = lang_country2linux_locale.get(language_country, None)
        if not _locale:
            _locale = lang_country2linux_locale.get(fallback)
        log.debug("python locale=%s" % str(locale.getdefaultlocale()))
        log.debug("locale=%s" % _locale)
        return _locale

    def get_platform(self):
        platform = sys.platform
        log.debug("platform=%s" % platform)
        return platform

    def get_osname(self):
        osname = os.name
        log.debug("osname=%s" % osname)
        return osname

    def get_language_encoding(self):
        language, encoding = locale.getdefaultlocale()
        log.debug("language=%s" % language)
        log.debug("encoding=%s" % encoding)
        return language, encoding

    def get_arch(self):
        #detects python/os arch not processor arch
        #overridden by platform specific backends
        arch = struct.calcsize('P') == 8 and "amd64" or "i386"
        log.debug("arch=%s" % arch)
        return arch

    def create_dir_structure(self, associated_task=None):
        self.info.disks_dir = join_path(self.info.target_dir, "disks")
        self.info.install_dir = join_path(self.info.target_dir, "install")
        self.info.install_boot_dir = join_path(self.info.install_dir, "boot")
        self.info.disks_boot_dir = join_path(self.info.disks_dir, "boot")
        dirs = [
            self.info.target_dir,
            self.info.disks_dir,
            self.info.install_dir,
            self.info.install_boot_dir,
            self.info.disks_boot_dir,
            join_path(self.info.disks_boot_dir, "grub"),
            join_path(self.info.install_boot_dir, "grub"),]
        for d in dirs:
            if not os.path.isdir(d):
                log.debug("Creating dir %s" % d)
                os.mkdir(d)

    def fetch_installer_info(self):
        '''
        Fetch information required by the installer
        '''

    def dummy_function(self):
        time.sleep(1)

    def check_metalink(self, metalink, base_url, associated_task=None):
        if self.info.skip_md5_check:
            return True
        url = base_url +"/" + self.info.distro.metalink_md5sums
        metalink_md5sums = downloader.download(url, self.info.install_dir, web_proxy=self.info.web_proxy)
        url = base_url +"/" + self.info.distro.metalink_md5sums_signature
        metalink_md5sums_signature = downloader.download(url, self.info.install_dir, web_proxy=self.info.web_proxy)
        if not verify_gpg_signature(metalink_md5sums, metalink_md5sums_signature, self.info.trusted_keys):
            log.error("Could not verify signature for metalink md5sums")
            return False
        md5sums = read_file(metalink_md5sums)
        log.debug("metalink md5sums:\n%s" % md5sums)
        md5sums = dict([reversed(line.split()) for line in md5sums.replace('*','').split('\n') if line])
        hashsum = md5sums.get(os.path.basename(metalink))
        if not hashsum:
            log.error("Could not find %s in metalink md5sums)" % os.path.basename(metalink))
            return False
        hash_len = len(hashsum)*4
        if hash_len == 160:
            hash_name = 'sha1'
        elif hash_len in [224, 256, 384, 512]:
            hash_name = 'sha' + str(hash_len)
        else:
            hash_name = 'md5'
        if self.info.distro.metalink:
           self.info.distro.metalink.files[0].hashes[0].type = hash_name
           self.info.distro.metalink.files[0].hashes[0].hash = hashsum
           return True
        hashsum2 = get_file_hash(metalink, hash_name)
        if hashsum != hashsum2:
            log.error("The %s of the metalink does not match (%s != %s)" % (hash_name, hashsum, hashsum2))
            return False
        return True

    def check_cd(self, cd_path, associated_task=None):
        associated_task.description = _("Checking CD %s") % cd_path
        if not self.info.distro.is_valid_cd(cd_path, check_arch=False):
            return False
        self.set_distro_from_arch(cd_path)
        if self.info.skip_md5_check:
            return True
        md5sums_file = join_path(cd_path, self.info.distro.md5sums)
        for rel_path in self.info.distro.get_required_files():
            if rel_path == self.info.distro.md5sums:
                continue
            check_file = associated_task.add_subtask(self.check_file)
            file_path = join_path(cd_path, rel_path)
            if not check_file(file_path, rel_path, md5sums_file):
                return False
        return True

    def check_iso(self, iso_path, associated_task=None):
        log.debug("Checking %s" % iso_path)
        if not self.info.distro.is_valid_iso(iso_path, check_arch=False):
            return False
        self.set_distro_from_arch(iso_path)
        if self.info.skip_md5_check:
            return True
        hashsum = None
#        if not self.info.distro.metalink:
#            get_metalink = associated_task.add_subtask(
#                self.get_metalink, description=_("Downloading information on installation files"))
#            get_metalink()
#            if not self.info.distro.metalink:
#                log.error("ERROR: the metalink file is not available, cannot check the md5 for %s, ignoring" % iso_path)
#                return True
#        for hash in self.info.distro.metalink.files[0].hashes:
#            if hash.type in ['md5','sha1','sha224','sha256','sha384','sha512']:
#                hashsum = hash.hash
#                hash_name = hash.type
#        if not hashsum:
#            log.error("ERROR: Could not find any md5 hash in the metalink for the ISO %s, ignoring" % iso_path)
#            return True
#        hashsum2 = self.info.iso_md5_hashes.get(iso_path, None)
#        if not hashsum2:
#            get_hash = associated_task.add_subtask(
#                get_file_hash,
#                description = _("Checking installation files") )
#            hashsum2 = get_hash(iso_path, hash_name)
#            if not iso_path.startswith(self.info.install_dir):
#                self.info.iso_md5_hashes[iso_path] = hashsum2
#        if hashsum != hashsum2:
#            log.exception("Invalid %s for ISO %s (%s != %s)" % (hash_name, iso_path, hashsum, hashsum2))
#            return False
        return True

    def select_mirrors(self, urls):
        '''
        Sort urls by preference giving a "boost" to the urls in the
        same country as the client
        '''
        def cmp(x, y):
            return y.score - x.score #reverse order
        urls = list(urls)
        for url in urls:
            url.score = url.preference
            if self.info.country == url.location:
                url.score += 50
        urls.sort(cmp)
        return urls

    def cache_img_path(self):
        self.dimage_path = None
        self.dimage_path = self.find_img()
		#if self.info.cd_distro \
		#and self.info.distro == self.info.cd_distro \
		#and self.info.cd_path \
		#and os.path.isdir(self.info.cd_path):
		#    self.cd_path = self.info.cd_path
		#else:
		#    self.cd_path = self.find_cd()

		#if not self.cd_path:
		#    if self.info.iso_distro \
		#    and self.info.distro == self.info.iso_distro \
		#    and os.path.isfile(self.info.iso_path):
		#        self.iso_path = self.info.iso_path
		#    else:
		#        self.iso_path = self.find_iso()
    
    def cache_cd_path(self):
        self.iso_path = None
        self.cd_path = None
        if self.info.cd_distro \
        and self.info.distro == self.info.cd_distro \
        and self.info.cd_path \
        and os.path.isdir(self.info.cd_path):
            self.cd_path = self.info.cd_path
        else:
            self.cd_path = self.find_cd()

        if not self.cd_path:
            if self.info.iso_distro \
            and self.info.distro == self.info.iso_distro \
            and os.path.isfile(self.info.iso_path):
                self.iso_path = self.info.iso_path
            else:
                self.iso_path = self.find_iso()

    def create_diskimage_dirs(self, associated_task=None):
        self.info.disks_dir = join_path(self.info.target_dir, "disks")
        self.info.disks_boot_dir = join_path(self.info.disks_dir, "boot")
        dirs = [
            self.info.target_dir,
            self.info.disks_dir,
            self.info.disks_boot_dir,
            join_path(self.info.disks_boot_dir, "grub"),
            ]
        for d in dirs:
            if not os.path.isdir(d):
                log.debug("Creating dir %s" % d)
                os.mkdir(d)

    def download_diskimage(self, associated_task=None):
        log.debug("Could not find any ISO or CD, downloading one now")
        self.info.cd_path = None
        url = self.info.distro.metalink_url
        dimage_name=self.info.distro.metalink_url.split("/")[-1]
        save_as = join_path(self.info.install_dir, dimage_name)
        if os.path.exists(save_as):
            try:
                os.unlink(save_as)
            except OSError:
                logging.exception('Could not remove: %s' % save_as)
        download = associated_task.add_subtask(
             downloader.download,
             is_required = True)
        dimage_path = download(url, save_as, web_proxy=self.info.web_proxy)
        if dimage_path:
            self.info.dimage_path = dimage_path
            return True

    def download_iso(self, associated_task=None):
        log.debug("Could not find any ISO or CD, downloading one now")
        self.info.cd_path = None
        url = self.info.distro.metalink_url
        iso_name=self.info.distro.metalink_url.split("/")[-1]
        save_as = join_path(self.info.install_dir, iso_name)
        if os.path.exists(save_as):
            try:
                os.unlink(save_as)
            except OSError:
                logging.exception('Could not remove: %s' % save_as)
        download = associated_task.add_subtask(
             downloader.download,
             is_required = True)
        iso_path = download(url, save_as, web_proxy=self.info.web_proxy)
        if iso_path:
            check_iso = associated_task.add_subtask(
                self.check_iso,
                description = _("Checking installation files"))
            if check_iso(iso_path):
                self.info.iso_path = iso_path
                return True
            else:
                os.unlink(iso_path)

    def get_metalink(self, associated_task=None):
        associated_task.description = _("Downloading information on installation files")
        try:
            url = self.info.distro.metalink_url
            metalink = downloader.download(url, self.info.install_dir, web_proxy=self.info.web_proxy)
            base_url = os.path.dirname(url)
        except Exception, err:
            log.error("Cannot download metalink file %s err=%s" % (url, err))
            try:
                url = self.info.distro.metalink_url2
                metalink = downloader.download(url, self.info.install_dir, web_proxy=self.info.web_proxy)
                base_url = os.path.dirname(url)
            except Exception, err:
                log.error("Cannot download metalink file2 %s err=%s" % (url, err))
                return
        metalink_filename, metalink_extension = os.path.splitext(metalink)
        if metalink_extension == '.list':
            self.info.distro.metalink = parse_metalink(join_path(self.info.data_dir, 'list.metalink'))
            metalink = metalink_filename + ".iso"
            self.info.distro.metalink.files[0].name = os.path.basename(metalink)
            self.info.distro.metalink.files[0].urls[0].url = base_url + "/" + self.info.distro.metalink.files[0].name + ".torrent"
            self.info.distro.metalink.files[0].urls[1].url = base_url + "/" + self.info.distro.metalink.files[0].name
        if not self.check_metalink(metalink, base_url):
            log.exception("Cannot authenticate the metalink file, it might be corrupt")
        if not self.info.distro.metalink:
            self.info.distro.metalink = parse_metalink(metalink)

    def get_prespecified_diskimage(self, associated_task):
        '''
        Use a local disk image specificed on the command line
        '''
        log.debug("Searching for image at %s" % self.info.dimage_path)
        if self.dimage_path and os.path.exists(self.dimage_path):
            return True
        if self.info.dimage_path \
        and os.path.exists(self.info.dimage_path):
            #TBD shall we do md5 check? Doesn't work well with daylies
            #TBD if a specified disk image cannot be used notify the user
            self.dimage_path = self.info.dimage_path
            log.debug("Trying to use pre-specified disk image %s" % self.info.dimage_path)
            is_valid_dimage = associated_task.add_subtask(
                self.info.distro.is_valid_dimage,
                description = _("Validating %s") % self.info.dimage_path)
            if is_valid_dimage(self.info.dimage_path, self.info.check_arch):
                self.info.cd_path = None
                return True

    def get_prespecified_iso(self, associated_task):

        if self.iso_path \
        and os.path.exists(self.iso_path):
			return True

        if self.info.iso_path \
        and os.path.exists(self.info.iso_path):
            #TBD shall we do md5 check? Doesn't work well with daylies
            #TBD if a specified ISO cannot be used notify the user
            log.debug("Trying to use pre-specified ISO %s" % self.info.iso_path)
            is_valid_iso = associated_task.add_subtask(
                self.info.distro.is_valid_iso,
                description = _("Validating %s") % self.info.iso_path)
            if is_valid_iso(self.info.iso_path, self.info.check_arch):
                self.info.cd_path = None
            return self.copy_iso(self.info.iso_path, associated_task)

    def set_distro_from_arch(self, cd_or_iso_path):
        '''
        Make sure that the distro is in line with the arch
        This is to make sure that a 32 bit local CD or ISO
        is used even though the arch is 64 bits
        '''
        if self.info.check_arch:
            return
        arch = self.info.distro.get_info(cd_or_iso_path)[3]
        if self.info.distro.arch == arch:
            return
        name = self.info.distro.name
        log.debug("Using distro %s %s instead of %s %s" % \
            (name, arch, name, self.info.distro.arch))
        distro = self.info.distros_dict.get((name.lower(), arch))
        self.info.distro = distro

    def copy_diskimage(self, dimage_path, associated_task):
        if not dimage_path:
            return
        dimage_name = self.info.distro.diskimage.split('/')[-1]
        dest = os.path.join(self.info.disks_dir, dimage_name)
        copy_dimage = associated_task.add_subtask(
            copy_file,
            description = _("Copying installation files"))
        log.debug("Copying %s > %s" % (dimage_path, dest))
        copy_dimage(dimage_path, dest)
        return True

    def copy_iso(self, iso_path, associated_task):
        if not iso_path:
            return
        dest = join_path(self.info.install_dir, "installation.iso")
        check_iso = associated_task.add_subtask(
            self.check_iso,
            description = _("Checking installation files"))
        if check_iso(iso_path):
            if os.path.dirname(iso_path) == dest:
                move_iso = associated_task.add_subtask(
                    shutil.move,
                    description = _("Copying installation files"))
                log.debug("Moving %s > %s" % (iso_path, dest))
                move_iso(iso_path, dest)
            else:
                copy_iso = associated_task.add_subtask(
                    copy_file,
                    description = _("Copying installation files"))
                log.debug("Copying %s > %s" % (iso_path, dest))
                copy_iso(iso_path, dest)
            self.info.cd_path = None
            self.info.iso_path = dest
            return True

    def use_cd(self, associated_task):
        if self.cd_path:
            extract_iso = associated_task.add_subtask(
                copy_file,
                description = _("Extracting files from %s") % self.cd_path)
            self.info.iso_path = join_path(self.info.install_dir, "installation.iso")
            try:
                extract_iso(self.cd_path, self.info.iso_path)
            except Exception, err:
                log.error(err)
                self.info.cd_path = None
                self.info.iso_path = None
                return False
            self.info.cd_path = self.cd_path
            #This will often fail before release as the CD might not match the latest daily ISO
            check_iso = associated_task.add_subtask(
                self.check_iso,
                description = _("Checking installation files"))
            if not check_iso(self.info.iso_path):
                subversion = self.info.cd_distro.get_info(self.info.cd_path)[2]
                if subversion.lower() in ("alpha", "beta", "release candidate"):
                    log.error("CD check failed, but ignoring because CD is %s" % subversion)
                else:
                    self.info.cd_path = None
                    self.info.iso_path = None
                    return False
            return True

    def use_iso(self, associated_task):
        if self.iso_path:
            log.debug("Trying to use ISO %s" % self.iso_path)
            return self.copy_iso(self.iso_path, associated_task)

    def get_diskimage(self, associated_task=None):
        '''
        Get a diskimage either locally or from the mirror
        '''
        if self.get_prespecified_diskimage(associated_task):
            return associated_task.finish()
        if self.download_diskimage(associated_task):
            return associated_task.finish()
        raise Exception("Could not retrieve the required disk image files")

    def get_iso(self, associated_task=None):
        if self.get_prespecified_iso(associated_task) \
        or self.use_cd(associated_task) \
        or self.use_iso(associated_task) \
        or self.download_iso(associated_task):
            return associated_task.finish()
        raise Exception("Could not retrieve the required installation files")

    def extract_kernel(self):
        bootdir = self.info.install_boot_dir
        # Extract kernel, initrd, md5sums
        if self.info.cd_path:
            log.debug("Copying files from CD %s" % self.info.cd_path)
            for src in [
            join_path(self.info.cd_path, self.info.distro.md5sums),
            join_path(self.info.cd_path, self.info.distro.kernel),
            join_path(self.info.cd_path, self.info.distro.initrd),]:
                shutil.copy(src, bootdir)
        elif self.info.iso_path:
            log.debug("Extracting files from ISO %s" % self.info.iso_path)
            self.extract_file_from_iso(self.info.iso_path, self.info.distro.md5sums, output_dir=bootdir)
            self.extract_file_from_iso(self.info.iso_path, self.info.distro.kernel, output_dir=bootdir)
            self.extract_file_from_iso(self.info.iso_path, self.info.distro.initrd, output_dir=bootdir)
        else:
            raise Exception("Could not retrieve the required installation files")
        # Check the files
        log.debug("Checking kernel, initrd and md5sums")
        self.info.kernel = join_path(bootdir, os.path.basename(self.info.distro.kernel))
        self.info.initrd = join_path(bootdir, os.path.basename(self.info.distro.initrd))
        md5sums = join_path(bootdir, os.path.basename(self.info.distro.md5sums))
        paths = [
            (self.info.kernel, self.info.distro.kernel),
            (self.info.initrd, self.info.distro.initrd),]
        for file_path, rel_path in paths:
                if not self.check_file(file_path, rel_path, md5sums):
                    raise Exception("File %s is corrupted" % file_path)

    def check_file(self, file_path, relpath, md5sums, associated_task=None):
        log.debug("  checking %s" % file_path)
        if associated_task:
            associated_task.description = _("Checking %s") % file_path
        relpath = relpath.replace("\\", "/")
        md5line = find_line_in_file(md5sums, "./%s" % relpath, endswith=True)
        if not md5line:
            raise Exception("Cannot find md5 in %s for %s" % (md5sums, relpath))
        reference_hash = md5line.split()[0]
        hash_len = len(reference_hash)*4
        if hash_len == 160:
            hash_name = 'sha1'
        elif hash_len in [224, 256, 384, 512]:
            hash_name = 'sha' + str(hash_len)
        else:
            hash_name = 'md5'
        hash_file = get_file_hash(file_path, hash_name, associated_task)
        log.debug("  %s %s = %s %s %s" % (file_path, hash_name, hash_file, hash_file == reference_hash and "==" or "!=", reference_hash))
        return hash_file == reference_hash

    def create_preseed_diskimage(self):
        source = join_path(self.info.data_dir, 'preseed.disk')
        template = read_file(source)
        password = md5_password(self.info.password)
        dic = dict(
            timezone = self.info.timezone,
            password = password,
            keyboard_variant = self.info.keyboard_variant,
            keyboard_layout = self.info.keyboard_layout,
            locale = self.info.locale,
            user_full_name = self.info.user_full_name,
            username = self.info.username)
        for k,v in dic.items():
            k = "$(%s)" % k
            template = template.replace(k, v)
        preseed_file = join_path(self.info.install_dir, "preseed_llx.cfg")
        write_file(preseed_file, template)

        source = join_path(self.info.data_dir, "lliuwinldr-disk.cfg")
        target = join_path(self.info.install_dir, "lliuwinldr-disk.cfg")
        copy_file(source, target)

    def create_preseed_cdboot(self):
        source = join_path(self.info.data_dir, 'preseed.cdboot')
        target = join_path(self.info.custominstall, "preseed.cfg")
        copy_file(source, target)

    def create_preseed(self):
        template_file = join_path(self.info.data_dir, 'preseed.' + self.info.distro.name)
        if not os.path.exists(template_file):
            template_file = join_path(self.info.data_dir, 'preseed.lupin')
        template = read_file(template_file)
        if self.info.distro.packages:
            distro_packages_skip = ''
        else:
            distro_packages_skip = '#'
        partitioning = ""
        partitioning += "d-i partman-auto/disk string LIDISK\n"
        partitioning += "d-i partman-auto/method string loop\n"
        partitioning += "d-i partman-auto-loop/partition string LIPARTITION\n"
        partitioning += "d-i partman-auto-loop/recipe string \\\n"
        disks_dir = unix_path(self.info.disks_dir) + '/'
        if self.info.root_size_mb:
            partitioning += '  %s 3000 %s %s $default_filesystem method{ format } format{ } use_filesystem{ } $default_filesystem{ } mountpoint{ / } . \\\n' \
            %(disks_dir + 'root.disk', self.info.root_size_mb, self.info.root_size_mb)
        if self.info.swap_size_mb:
            partitioning += '  %s 100 %s %s linux-swap method{ swap } format{ } . \\\n' \
            %(disks_dir + 'swap.disk', self.info.swap_size_mb, self.info.swap_size_mb)
        if self.info.home_size_mb:
            partitioning += '  %s 100 %s %s $default_filesystem method{ format } format{ } use_filesystem{ } $default_filesystem{ } mountpoint{ /home } . \\\n' \
            %(disks_dir + 'home.disk', self.info.home_size_mb, self.info.home_size_mb)
        if self.info.usr_size_mb:
            partitioning += '  %s 100 %s %s $default_filesystem method{ format } format{ } use_filesystem{ } $default_filesystem{ } mountpoint{ /usr } . \\\n' \
            %(disks_dir + 'usr.disk', self.info.usr_size_mb, self.info.usr_size_mb)
        partitioning += "\n"
        safe_host_username = self.info.host_username.replace(" ", "+")
        user_directory = self.info.user_directory.replace("\\", "/")[2:]
        host_os_name = "Windows XP Professional" #TBD
        password = md5_password(self.info.password)
        dic = dict(
            timezone = self.info.timezone,
            password = password,
            user_full_name = self.info.user_full_name,
            distro_packages_skip  = distro_packages_skip,
            distro_packages = self.info.distro.packages,
            host_username = self.info.host_username,
            username = self.info.username,
            partitioning = partitioning,
            user_directory = user_directory,
            safe_host_username = safe_host_username,
            host_os_name = host_os_name,
            custom_installation_dir = unix_path(self.info.custominstall),)
        content = template
        for k,v in dic.items():
            k = "$(%s)" % k
            content = content.replace(k, v)
        preseed_file = join_path(self.info.custominstall, "preseed.cfg")
        write_file(preseed_file, content)

    def modify_bootloader(self):
        #platform specific
        pass

    def modify_grub_configuration(self):
        template_file = join_path(self.info.data_dir, 'grub.install.cfg')
        template = read_file(template_file)
        rootflags = "rootflags=sync"
        if self.info.distro.name=='LliureX-Live':
            isopath = unix_path(self.info.iso_path)
            dic = dict(
                custom_installation_dir = unix_path(self.info.custominstall),
                iso_path = isopath,
                keyboard_variant = self.info.keyboard_variant,
                keyboard_layout = self.info.keyboard_layout,
                locale = self.info.locale,
                accessibility = self.info.accessibility,
                kernel = unix_path(self.info.kernel),
                initrd = unix_path(self.info.initrd),
                rootflags = rootflags,
                title1 = "Booting the LliureX installation.",
                title2 = "For more boot options, press `ESC' now...",
                lliurex_mode_title = "LliureX",
                normal_mode_title = "LliureX Live",
			    #pae_mode_title = "PAE mode",
			    # safe_graphic_mode_title = "Safe graphic mode",
			    #intel_graphics_workarounds_title = "Intel graphics workarounds",
			    #nvidia_graphics_workarounds_title = "Nvidia graphics workarounds",
			    #acpi_workarounds_title = "ACPI workarounds",
			    #verbose_mode_title = "Verbose mode",
			    #demo_mode_title =  "Demo mode",
            )
        else:
            isopath = ""
            kernel=''
            initrd=''
            dic=dict(
                lliurex_mode_title = "LliureX",
                title1 = "Booting the LliureX installation.",
                title2 = "For more boot options, press `ESC' now...",
                rootflags = rootflags,
                custom_installation_dir = unix_path(self.info.custominstall),
                iso_path = isopath,
                keyboard_variant = self.info.keyboard_variant,
                keyboard_layout = self.info.keyboard_layout,
                locale = self.info.locale,
                accessibility = self.info.accessibility,
            )
        ## TBD at the moment we are extracting the ISO, not the CD content
        #~ elif self.info.cd_path:
            #~ isopath = unix_path(self.info.cd_path)
        content = template
        for k,v in dic.items():
            k = "$(%s)" % k
            content = content.replace(k, v)
        if self.info.run_task == "cd_boot":
            content = content.replace(" automatic-ubiquity", "")
            content = content.replace(" iso-scan/filename=", "")
        grub_config_file = join_path(self.info.install_boot_dir, "grub", "grub.cfg")
        write_file(grub_config_file, content)

    def remove_target_dir(self, associated_task=None):
        if not os.path.isdir(self.info.previous_target_dir):
            log.debug("Cannot find %s" % self.info.previous_target_dir)
            return
        log.debug("Deleting %s" % self.info.previous_target_dir)
        try:
            rm_tree(self.info.previous_target_dir)
        except OSError, e:
            if e.errno == 22:
                log.exception('Unable to remove the target directory.')
                # Invalid argument - likely a corrupt file.
                cmd = spawn_command(['chkdsk', '/F'])
                cmd.communicate(input='Y%s' % os.linesep)
                raise errors.WubiCorruptionError

    def find_img(self, associated_task=None):
        log.debug("Searching for local IMG")
        for path in self.get_iso_search_paths():
            log.debug("IMG path: %s"%path)
            path = join_path(path, '*.img')
            imgs = glob.glob(path)
            for img in imgs:
#                if self.info.distro.is_valid_iso(iso, self.info.check_arch):
                log.debug("Found local IMG: %s"%img)
                return img

    def find_iso(self, associated_task=None):
        log.debug("Searching for local ISO")
        for path in self.get_iso_search_paths():
            path = join_path(path, '*.iso')
            isos = glob.glob(path)
            for iso in isos:
                if self.info.distro.is_valid_iso(iso, self.info.check_arch):
                    return iso

    def find_any_img(self):
        '''
        look for local IMGs or pre specified IMG
        '''
        #Use pre-specified IMG
        if self.info.dimage_path \
        and os.path.exists(self.info.dimage_path):
            log.debug("Checking pre-specified IMG %s" % self.info.dimage_path)
            for distro in self.info.distros:
                #if distro.is_valid_iso(self.info.iso_path, self.info.check_arch):
                    #self.info.cd_path = None
                 return self.info.dimage_path, 'LliureX'
        #Search local IMGs
        log.debug("Searching for local IMGs")
        imgs=[]
        for path in self.get_iso_search_paths():
            log.debug("Seach %s"%path)
            if os.path.isdir(path):
                for f in os.listdir(path):
                    if f.endswith(".img"):
                        imgs.append(os.path.join(path,f))
			#path = join_path(path, '*.img')
			#imgs = glob.glob(path)
            for img in imgs:
                #for distro in self.info.distros:
                    #if distro.is_valid_iso(iso, self.info.check_arch):
                return img, 'LliureX'
        return None, None
    
    def find_any_iso(self):
        '''
        look for local ISOs or pre specified ISO
        '''
        #Use pre-specified ISO
        if self.info.iso_path \
        and os.path.exists(self.info.iso_path):
            log.debug("Checking pre-specified ISO %s" % self.info.iso_path)
            for distro in self.info.distros:
                if distro.is_valid_iso(self.info.iso_path, self.info.check_arch):
                    self.info.cd_path = None
                    return self.info.iso_path, distro
        #Search local ISOs
        log.debug("Searching for local ISOs")
        isos=[]
        for path in self.get_iso_search_paths():
            log.debug("Seach %s"%path)
            if os.path.isdir(path):
                for f in os.listdir(path):
                    if f.endswith(".iso"):
                        isos.append(os.path.join(path,f))
			#path = join_path(path, '*.iso')
			#isos = glob.glob(path)
            log.debug("ISOS %s"%isos)
            for iso in isos:
                for distro in self.info.distros:
                    if distro.is_valid_iso(iso, self.info.check_arch):
                        return iso, distro
        return None, None

    def find_any_cd(self):
        log.debug("Searching for local CDs")
        for path in self.get_cd_search_paths():
            path = abspath(path)
            for distro in self.info.distros:
                if distro.is_valid_cd(path, self.info.check_arch):
                    if self.info.original_exe[:2] != path[:2]:
                        # We don't want to use the CD if it's inserted when the
                        # user is running Wubi from disk.
                        return None, None
                    else:
                        return path, distro
        return None, None

    def find_cd(self):
        log.debug("Searching for local CD")
        for path in self.get_cd_search_paths():
            path = abspath(path)
            if self.info.distro.is_valid_cd(path, self.info.check_arch):
                return path

    def parse_isolist(self, isolist_path):
        log.debug('Parsing isolist=%s' % isolist_path)
        isolist = ConfigParser.ConfigParser()
        isolist.read(isolist_path)
        distros = []
        for distro in isolist.sections():
            log.debug('  Adding distro %s' % distro)
            kargs = dict(isolist.items(distro))
            kargs['backend'] = self
            distros.append(Distro(**kargs))
            #order is lost in configparser, use the ordering attribute
        def compfunc(x, y):
            if x.ordering == y.ordering:
                return 0
            elif x.ordering > y.ordering:
                return 1
            else:
                return -1
        distros.sort(compfunc)
        return distros

    def run_previous_uninstaller(self):
        if not self.info.previous_uninstaller_path \
        or not os.path.isfile(self.info.previous_uninstaller_path):
            return
        previous_uninstaller = self.info.previous_uninstaller_path.lower()
        uninstaller = self.info.previous_uninstaller_path
        command = [uninstaller, "--uninstall"]
        # Propagate noninteractive mode to the uninstaller
        if self.info.non_interactive:
            command.append("--noninteractive")
        if 0 and previous_uninstaller.lower() == self.info.original_exe.lower():
            # This block is disabled as the functionality is achived via pylauncher
            if self.info.original_exe.lower().startswith(self.info.previous_target_dir.lower()):
                log.debug("Copying uninstaller to a temp directory, so that we can delete the containing directory")
                uninstaller = tempfile.NamedTemporaryFile()
                uninstaller.close()
                uninstaller = uninstaller.name
                copy_file(self.info.previous_uninstaller_path, uninstaller)
            log.info("Launching asynchronously previous uninstaller %s" % uninstaller)
            run_nonblocking_command(command, show_window=True)
            return True
        elif get_file_hash(self.info.original_exe) == get_file_hash(self.info.previous_uninstaller_path):
            log.info("This is the uninstaller running")
        else:
            log.info("Launching previous uninestaller %s" % uninstaller)
            subprocess.call(command)
            # Note: the uninstaller is now non-blocking so we can just as well quit this running version
            # TBD: make this call synchronous by waiting for the children process of the uninstaller
            self.application.quit()
            return True

