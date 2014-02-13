#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (C) 2007,2008 One Laptop per Child Association, Inc.
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

'''XXX: This function seems to be broken. (CSA)
def quit(self):
perf.Stop()
perf.Join()
cs.Reset()
cs = None
'''

orchlines = []
scorelines = []
instrlist = []
fnum = [100]


class SoundLibraryNotFoundError(Exception):
    def __init__(self):
        Exception.__init__(self, _('Cannot find TamTamEdit sound library.'
                                   ' Did you install TamTamEdit?'))


def finddir():
    paths = ['/usr/share/sugar/activities', env.get_user_activities_path()]

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
                    os.path.expandvars('$SUGAR_PATH/activities') + \
                    tamtam_subdir,
                    tamtam_subdir
                ]

    if sound_candidate_dirs is not None:
        for directory in sound_candidate_dirs:
            if os.path.isdir(directory):
                return directory

    raise SoundLibraryNotFoundError()


def defAdsr(attack=0.01, decay=0.1, sustain=0.8, release=0.1):
    ''' Define an ADSR envelope. fnum = defADSR(attack = [0.01],
    decay = [0.1], sustain = [0.8], release = [0.1]) '''
    att = int(2048 * attack)
    dec = int(2048 * decay)
    rel = int(2048 * release)
    bal = 2048 - (att + dec + rel)
    sus = min(1., sustain)

    fnum[0] += 1
    scorelines.append('f%ld 0 2048 7 0 %ld 1. %ld %f %ld %f %ld 0\n' %
                      (fnum[0], att, dec, sus, bal, sus, rel))
    return fnum[0]


def defLineSegments(list=[0, 10, 1, 10, 0, 10, 1, 10, 0]):
    ''' Define a breakpoints envelope. list begin with the start
    value of the function and is follow by any pair values (duration,
    value). The number of elements in the list should be odd. '''

    totalLength = 0
    newlist = []
    for i in range(len(list)):
        if (i % 2) == 1:
            totalLength += list[i]

    for i in range(len(list)):
        if (i % 2) == 0:
            newlist.append(list[i])
        else:
            newlist.append(int(2048 * (list[i] / float(totalLength))))

    fnum[0] += 1
    scorelines.append('f' + str(fnum[0]) + ' 0 2048 -7 ' +
                      ' '.join([str(n) for n in newlist]) + '\n')
    return fnum[0]


def defComplexWave(list=[1, 0, 0, .3, 0, .2, 0, 0, .1]):
    ''' Define a complex waveform to be read with 'playComplex'
    function. list=[1, 0, 0, .3, 0, .2, 0, 0, .1] is a list of
    amplitude for succesive harmonics of a waveform '''
    fnum[0] += 1
    scorelines.append('f' + str(fnum[0]) + ' 0 2048 10 ' +
                      ' '.join([str(n) for n in list]) + '\n')
    return fnum[0]


def playSine(pitch=1000, amplitude=5000, duration=1, starttime=0,
             pitch_envelope='default', amplitude_envelope='default'):
    ''' Play a sine wave
    (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0],
    pitch_envelope=['default'], amplitude_envelope=['default']) '''
    _play(pitch, amplitude, duration, starttime, pitch_envelope,
          amplitude_envelope, 1)


def playSquare(pitch=1000, amplitude=5000, duration=1, starttime=0,
               pitch_envelope='default', amplitude_envelope='default'):
    ''' Play a square wave
    (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0],
    pitch_envelope=['default'], amplitude_envelope=['default']) '''
    _play(pitch, amplitude, duration, starttime, pitch_envelope,
          amplitude_envelope, 2)


def playSawtooth(pitch=1000, amplitude=5000, duration=1, starttime=0,
                 pitch_envelope='default', amplitude_envelope='default'):
    ''' Play a sawtooth wave (pitch = [1000], amplitude = [5000],
    duration = [1], starttime = [0], pitch_envelope=['default'],
    amplitude_envelope=['default']) '''
    _play(pitch, amplitude, duration, starttime, pitch_envelope,
          amplitude_envelope, 3)


def playComplex(pitch=1000, amplitude=5000, duration=1, starttime=0,
                pitch_envelope='default', amplitude_envelope='default',
                wave='default'):
    ''' Play a complex wave
    (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0],
    pitch_envelope = ['default'], amplitude_envelope, wave = ['default'] ) '''
    if wave == 'default':
        wavetable = 10
    else:
        wavetable = wave
    _play(pitch, amplitude, duration, starttime, pitch_envelope,
          amplitude_envelope, wavetable)


def _play(pitch, amplitude, duration, starttime, pitch_envelope,
          amplitude_envelope, instrument):
    if pitch_envelope == 'default':
        pitenv = 99
    else:
        pitenv = pitch_envelope

    if amplitude_envelope == 'default':
        ampenv = 100
    else:
        ampenv = amplitude_envelope

    if not 1 in instrlist:
        orchlines.append('instr 1\n')
        orchlines.append('kpitenv oscil 1, 1/p3, p6\n')
        orchlines.append('aenv oscil 1, 1/p3, p7\n')
        orchlines.append('asig oscil p5*aenv, p4*kpitenv, p8\n')
        orchlines.append('out asig\n')
        orchlines.append('endin\n\n')
        instrlist.append(1)

    scorelines.append('i1 %s %s %s %s %s %s %s\n' %
                      (str(starttime), str(duration), str(pitch),
                       str(amplitude), str(pitenv), str(ampenv),
                       str(instrument)))


def playFrequencyModulation(pitch=500, amplitude=5000, duration=2, starttime=0,
                            carrier=1, modulator=.5, index=5,
                            pitch_envelope='default',
                            amplitude_envelope='default',
                            carrier_envelope='default',
                            modulator_envelope='default',
                            index_envelope='default', wave='default'):
    ''' Play a frequency modulation synthesis sound (pitch = [100],
    amplitude = [5000], duration = [2], starttime = [0], carrier =
    [1], modulator = [.5], index = [5], pitch_envelope = ['default'],
    amplitude_envelope = ['default'], carrier_envelope = ['default'],
    modulator_envelope = ['default'], index_envelope = ['default'],
    wave = ['default'] ) '''
    if pitch_envelope == 'default':
        pitenv = 99
    else:
        pitenv = pitch_envelope

    if amplitude_envelope == 'default':
        ampenv = 100
    else:
        ampenv = amplitude_envelope

    if carrier_envelope == 'default':
        carenv = 99
    else:
        carenv = carrier_envelope

    if modulator_envelope == 'default':
        modenv = 99
    else:
        modenv = modulator_envelope

    if index_envelope == 'default':
        indenv = 99
    else:
        indenv = index_envelope

    if wave == 'default':
        wavetable = 1
    else:
        wavetable = wave

    if not 7 in instrlist:
        orchlines.append('instr 7\n')
        orchlines.append('kpitenv oscil 1, 1/p3, p10\n')
        orchlines.append('kenv oscil 1, 1/p3, p11\n')
        orchlines.append('kcarenv oscil 1, 1/p3, p12\n')
        orchlines.append('kmodenv oscil 1, 1/p3, p13\n')
        orchlines.append('kindenv oscil 1, 1/p3, p14\n')
        orchlines.append('asig foscil p5*kenv, p4*kpitenv, p6*kcarenv, '
                         'p7*kmodenv, p8*kindenv, p9\n')
        orchlines.append('out asig\n')
        orchlines.append('endin\n\n')
        instrlist.append(7)

    scorelines.append('i7 %s %s %s %s %s %s %s %s %s %s %s %s %s\n' %
                      (str(starttime), str(duration), str(pitch),
                       str(amplitude), str(carrier), str(modulator),
                       str(index), str(wavetable),  str(pitenv), str(ampenv),
                       str(carenv), str(modenv), str(indenv)))


def playPluck(pitch=100, amplitude=5000, duration=2, starttime=0,
              pitch_envelope='default', amplitude_envelope='default'):
    ''' Play a string physical modeling sound (pitch = [100],
    amplitude = [5000], duration = [2], starttime = [0],
    pitch_envelope = ['default'], amplitude_envelope ) '''
    if pitch_envelope == 'default':
        pitenv = 99
    else:
        pitenv = pitch_envelope

    if amplitude_envelope == 'default':
        ampenv = 100
    else:
        ampenv = amplitude_envelope

    if not 8 in instrlist:
        orchlines.append('instr 8\n')
        orchlines.append('kpitenv oscil 1, 1/p3, p6\n')
        orchlines.append('kenv oscil 1, 1/p3, p7\n')
        orchlines.append('asig pluck p5*kenv, p4*kpitenv, 40, 0, 6\n')
        orchlines.append('asig butterlp asig, 4000\n')
        orchlines.append('out asig\n')
        orchlines.append('endin\n\n')
        instrlist.append(8)

    scorelines.append('i8 %s %s %s %s %s %s\n' %
                      (str(starttime), str(duration), str(pitch),
                       str(amplitude), str(pitenv), str(ampenv)))


def playWave(sound='horse', pitch=1, amplitude=1, loop=False, duration=1,
             starttime=0, pitch_envelope='default',
             amplitude_envelope='default'):
    ''' Play a wave file (sound = ['horse'], pitch = [1], amplitude =
    [1], loop = [False], duration = [1], starttime = [0],
    pitch_envelope=['default'], amplitude_envelope=['default']) '''
    if '/' in sound:
        fullname = sound
    else:
        fullname = os.path.join(finddir(), sound)

    if loop:
        lp = 1
    else:
        lp = 0

    if pitch_envelope == 'default':
        pitenv = 99
    else:
        pitenv = pitch_envelope

    if amplitude_envelope == 'default':
        ampenv = 100
    else:
        ampenv = amplitude_envelope

    if not 9 in instrlist:
        orchlines.append('instr 9\n')
        orchlines.append('kpitenv oscil 1, 1/p3, p8\n')
        orchlines.append('aenv oscil 1, 1/p3, p9\n')
        orchlines.append('asig diskin p4, p5*kpitenv, 0, p7\n')
        orchlines.append('out asig*p6*aenv\n')
        orchlines.append('endin\n\n')
        instrlist.append(9)

    scorelines.append("i9 %f %f '%s' %s %s %s %s %s\n" %
                      (float(starttime), float(duration), fullname, str(pitch),
                       str(amplitude), str(lp), str(pitenv), str(ampenv)))


def getSoundList():
    return sorted(os.listdir(finddir()))

temp_path = None


def audioOut(file=None):
    ''' Compile a .csd file and start csound to run it. If a string is
    given as argument, it write a wave file on disk instead of sending
    sound to hp. (file = [None]) '''
    global temp_path
    if temp_path is None:
        temp_path = os.path.join(env.get_profile_path(), 'pippy')
        if not os.path.isdir(temp_path):
            os.mkdir(temp_path)
    path = temp_path
    csd = open(os.path.join(path, 'temp.csd'), 'w')
    csd.write('<CsoundSynthesizer>\n\n')
    csd.write('<CsOptions>\n')
    if file is None:
        csd.write('-+rtaudio=alsa -odevaudio -m0 -d -b256 -B512\n')
    else:
        file = os.path.join(path, '%s.wav' % file)
        csd.write('-+rtaudio=alsa -o%s -m0 -W -d -b256 -B512\n' % file)
    csd.write('</CsOptions>\n\n')
    csd.write('<CsInstruments>\n\n')
    csd.write('sr=16000\n')
    csd.write('ksmps=50\n')
    csd.write('nchnls=1\n\n')
    for line in orchlines:
        csd.write(line)
    csd.write('\n</CsInstruments>\n\n')
    csd.write('<CsScore>\n\n')
    csd.write('f1 0 2048 10 1\n')
    csd.write('f2 0 2048 10 1 0 .33 0 .2 0 .143 0 .111\n')
    csd.write('f3 0 2048 10 1 .5 .33 .25 .2 .175 .143 .125 .111 .1\n')
    csd.write('f10 0 2048 10 1 0 0 .3 0 .2 0 0 .1\n')
    csd.write('f99 0 2048 7 1 2048 1\n')
    csd.write('f100 0 2048 7 0. 10 1. 1900 1. 132 0.\n')
    for line in scorelines:
        csd.write(line)
    csd.write('e\n')
    csd.write('\n</CsScore>\n')
    csd.write('\n</CsoundSynthesizer>')
    csd.close()

    os.system('csound ' + path + '/temp.csd >/dev/null 2>/dev/null')
