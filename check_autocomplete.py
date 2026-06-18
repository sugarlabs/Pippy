#!/usr/bin/python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2023 Sugar Labs
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

"""
Helper script to check if python3-jedi is installed
and offer to install it if it's missing.
"""

import os
import sys
import subprocess
import logging
from gi.repository import Gtk
from gettext import gettext as _

def check_jedi_installed():
    """Check if jedi is installed and available"""
    try:
        import jedi
        return True
    except ImportError:
        return False

def is_debian_based():
    """Check if this is a Debian-based system"""
    return os.path.exists('/etc/debian_version')

def is_fedora_based():
    """Check if this is a Fedora-based system"""
    return os.path.exists('/etc/fedora-release')

def install_jedi():
    """Try to install jedi using the appropriate package manager"""
    install_cmd = None
    
    if is_debian_based():
        install_cmd = ['apt-get', 'install', '-y', 'python3-jedi']
    elif is_fedora_based():
        install_cmd = ['dnf', 'install', '-y', 'python3-jedi']
    
    if not install_cmd:
        return False, _("Couldn't determine your system's package manager. Please install python3-jedi manually.")
    
    try:
        # Need to run with pkexec to get root privileges
        cmd = ['pkexec'] + install_cmd
        result = subprocess.run(cmd, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.PIPE)
        
        if result.returncode == 0:
            return True, _("Jedi was installed successfully!")
        else:
            error = result.stderr.decode('utf-8')
            return False, _("Failed to install Jedi: ") + error
    except Exception as e:
        return False, _("Error during installation: ") + str(e)

def show_installation_dialog():
    """Show a dialog asking if the user wants to install Jedi"""
    dialog = Gtk.MessageDialog(
        None, 0, Gtk.MessageType.QUESTION,
        Gtk.ButtonsType.YES_NO,
        _("Python Jedi library not found")
    )
    dialog.format_secondary_text(
        _("Code autocompletion requires the Python Jedi library. "
          "Would you like to install it now?")
    )
    
    response = dialog.run()
    dialog.destroy()
    
    if response == Gtk.ResponseType.YES:
        return True
    else:
        return False

def show_result_dialog(success, message):
    """Show the result of the installation attempt"""
    dialog_type = Gtk.MessageType.INFO if success else Gtk.MessageType.ERROR
    title = _("Installation Complete") if success else _("Installation Failed")
    
    dialog = Gtk.MessageDialog(
        None, 0, dialog_type,
        Gtk.ButtonsType.OK,
        title
    )
    dialog.format_secondary_text(message)
    
    dialog.run()
    dialog.destroy()

def main():
    """Main function to check and offer installation of Jedi"""
    # Initialize logging
    logging.basicConfig(level=logging.INFO)
    
    # Check if Jedi is installed
    if check_jedi_installed():
        logging.info("Python Jedi library is already installed.")
        return 0
    
    # Offer to install Jedi
    if show_installation_dialog():
        success, message = install_jedi()
        show_result_dialog(success, message)
        
        if success:
            return 0
        else:
            return 1
    else:
        return 0

if __name__ == "__main__":
    sys.exit(main()) 