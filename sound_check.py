#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2013,14 Walter Bender (walter@sugarlabs.org)
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

import os
from gettext import gettext as _

from sugar3 import env


class SoundLibraryNotFoundError(Exception):
    def __init__(self):
        Exception.__init__(self, _('Cannot find TamTamEdit sound library.'
                                   ' Did you install TamTamEdit?'))


def finddir():
    paths = ['/usr/share/sugar/activities', env.get_user_activities_path()]
    paths.append(os.path.join(os.path.expanduser('~'), 'Activities'))

    sound_candidate_dirs = None

    for path in paths:
        if not os.path.exists(path):
            continue
        for f in os.listdir(path):
            if f in ['TamTamMini.activity', 'TamTamJam.activity',
                     'TamTamEdit.activity', 'TamTamSynthLab.activity',
                     'MusicKeyboard.activity']:
                bundle_dir = os.path.join(path, f)
                tamtam_subdir = str(
                    os.path.join(bundle_dir, 'common', 'Resources', 'Sounds'))
                sound_candidate_dirs = [
                    os.path.expandvars('$SUGAR_PATH/activities') +
                    tamtam_subdir,
                    tamtam_subdir
                ]

    if sound_candidate_dirs is not None:
        for directory in sound_candidate_dirs:
            if os.path.isdir(directory):
                return directory

    raise SoundLibraryNotFoundError()
