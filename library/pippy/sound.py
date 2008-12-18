#! /usr/bin/env python
import os
import sys
from gettext import gettext as _

dirs = ['/usr/share/activities/TamTamEdit.activity/common/Resources/Sounds/',
        '/home/olpc/Activities/TamTamEdit.activity/common/Resources/Sounds/']
orchlines = []
scorelines = []
instrlist = []
fnum = [100]

"""XXX: This function seems to be broken. (CSA)
def quit(self):
    perf.Stop()
    perf.Join()                                    
    cs.Reset()
    cs = None            
"""

def finddir():
    for d in dirs:
        if os.path.isdir(d):
            return d

def defAdsr(attack=0.01, decay=0.1, sustain=0.8, release=0.1):
    """Define an ADSR envelope. fnum = defADSR(attack = [0.01], decay = [0.1], sustain = [0.8], release = [0.1])"""
    att = int(2048 * attack)
    dec = int(2048 * decay)
    rel = int(2048 * release)
    bal = 2048 - (att + dec + rel)
    sus = min(1., sustain)

    fnum[0] += 1
    scorelines.append("f%ld 0 2048 7 0 %ld 1. %ld %f %ld %f %ld 0\n" % (fnum[0], att, dec, sus, bal, sus, rel))
    return fnum[0]

def defLineSegments(list=[0,10,1,10,0,10,1,10,0]):
    """Define a breakpoints envelope. list=[0,10,1,10,0,10,1,10,0]. list begin with the start value of the function and is follow by any pair values (duration, value). The number of elements in the list should odd."""

    totalLength = 0
    newlist = []
    for i in range(len(list)):
        if (i % 2) == 1:
            totalLength += list[i]

    for i in range(len(list)):
        if (i % 2) == 0: newlist.append(list[i])
        else: newlist.append(int(2048 * (list[i] / float(totalLength))))

    fnum[0] += 1
    scorelines.append("f" + str(fnum[0]) + " 0 2048 -7 " + " ".join([str(n) for n in newlist]) + '\n')
    return fnum[0]

def defComplexWave(list=[1,0,0,.3,0,.2,0,0,.1]):
    """Define a complex waveform to be read with 'playComplex' function. list=[1,0,0,.3,0,.2,0,0,.1]
is a list of amplitude for succesive harmonics of a waveform"""
    fnum[0] += 1
    scorelines.append("f" + str(fnum[0]) + " 0 2048 10 " + " ".join([str(n) for n in list]) + '\n')
    return fnum[0]

def playSine( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a sine wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, 1)

def playSquare( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a square wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, 2)

def playSawtooth( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a sawtooth wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, 3)

def playComplex( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default', wave='default'):
    """Play a complex wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope = ['default'], amplitude_envelope, wave = ['default'] )"""
    if wave == 'default': wavetable = 10
    else: wavetable = wave
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, wavetable)

def _play( pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, instrument):
    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    if not 1 in instrlist:
        orchlines.append("instr 1\n")
        orchlines.append("kpitenv oscil 1, 1/p3, p6\n")
        orchlines.append("aenv oscil 1, 1/p3, p7\n")
        orchlines.append("asig oscil p5*aenv, p4*kpitenv, p8\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(1)

    scorelines.append("i1 %s %s %s %s %s %s %s\n" % (str(starttime), str(duration), str(pitch), str(amplitude), str(pitenv), str(ampenv), str(instrument)))

def playFrequencyModulation( pitch=500, amplitude=5000, duration=2, starttime=0, carrier=1, modulator=.5, index=5, pitch_envelope='default', amplitude_envelope='default', carrier_envelope='default', modulator_envelope='default', index_envelope='default', wave='default'):
    """Play a frequency modulation synthesis sound (pitch = [100], amplitude = [5000], duration = [2], starttime = [0], carrier = [1], modulator = [.5], index = [5], pitch_envelope = ['default'], amplitude_envelope = ['default'], carrier_envelope = ['default'], modulator_envelope = ['default'], index_envelope = ['default'], wave = ['default'] )"""
    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    if carrier_envelope == 'default': carenv = 99
    else: carenv = carrier_envelope

    if modulator_envelope == 'default': modenv = 99
    else: modenv = modulator_envelope

    if index_envelope == 'default': indenv = 99
    else: indenv = index_envelope

    if wave == 'default': wavetable = 1
    else: wavetable = wave

    if not 7 in instrlist:
        orchlines.append("instr 7\n")
        orchlines.append("kpitenv oscil 1, 1/p3, p10\n")
        orchlines.append("kenv oscil 1, 1/p3, p11\n")
        orchlines.append("kcarenv oscil 1, 1/p3, p12\n")
        orchlines.append("kmodenv oscil 1, 1/p3, p13\n")
        orchlines.append("kindenv oscil 1, 1/p3, p14\n")
        orchlines.append("asig foscil p5*kenv, p4*kpitenv, p6*kcarenv, p7*kmodenv, p8*kindenv, p9\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(7)

    scorelines.append("i7 %s %s %s %s %s %s %s %s %s %s %s %s %s\n" % (str(starttime), str(duration), str(pitch), str(amplitude), str(carrier), str(modulator), str(index), str(wavetable),  str(pitenv), str(ampenv), str(carenv), str(modenv), str(indenv)))

def playPluck( pitch=100, amplitude=5000, duration=2, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a string physical modeling sound (pitch = [100], amplitude = [5000], duration = [2], starttime = [0], pitch_envelope = ['default'], amplitude_envelope )"""
    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    if not 8 in instrlist:
        orchlines.append("instr 8\n")
        orchlines.append("kpitenv oscil 1, 1/p3, p6\n")
        orchlines.append("kenv oscil 1, 1/p3, p7\n")
        orchlines.append("asig pluck p5*kenv, p4*kpitenv, 40, 0, 6\n")
        orchlines.append("asig butterlp asig, 4000\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(8)

    scorelines.append("i8 %s %s %s %s %s %s\n" % (str(starttime), str(duration), str(pitch), str(amplitude), str(pitenv), str(ampenv)))

def playWave(sound='horse', pitch=1, amplitude=1, loop=False, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a wave file (sound = ['horse'], pitch = [1], amplitude = [1], loop = [False], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    if '/' in sound:
        fullname = sound
    else:
        fullname = finddir() + str(sound)

    if loop == False: lp = 0
    else: lp = 1

    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    if not 9 in instrlist:
        orchlines.append("instr 9\n") 
        orchlines.append("kpitenv oscil 1, 1/p3, p8\n")
        orchlines.append("aenv oscil 1, 1/p3, p9\n")
        orchlines.append("asig diskin p4, p5*kpitenv, 0, p7\n") 
        orchlines.append("out asig*p6*aenv\n")
        orchlines.append("endin\n\n")
        instrlist.append(9)

    scorelines.append('i9 %f %f "%s" %s %s %s %s %s\n' % (float(starttime), float(duration), fullname, str(pitch), str(amplitude), str(lp), str(pitenv), str(ampenv)))
    
def getSoundList():
    list = finddir()
    if list == None:
        print _("Please install TamTamEdit's sound library.")
        sys.exit(0)
    return sorted(os.listdir(list))

temp_path=None
def audioOut(file=None):
    """Compile a .csd file and start csound to run it. If a string is given as argument, it write a wave file on disk instead of sending sound to hp. (file = [None])"""
    global temp_path
    import os
    if temp_path is None:
        from sugar import env
        import os.path
        temp_path = env.get_profile_path() + '/pippy'
        if not os.path.isdir(temp_path):
            os.mkdir(temp_path)
    path = temp_path
    csd = open(path + "/temp.csd", "w")
    csd.write("<CsoundSynthesizer>\n\n")
    csd.write("<CsOptions>\n")
    if file == None:
        csd.write("-+rtaudio=alsa -odevaudio -m0 -d -b256 -B512\n")
    else:
        file = path + "/" + str(file) + ".wav"
        csd.write("-+rtaudio=alsa -o%s -m0 -W -d -b256 -B512\n" % file)
    csd.write("</CsOptions>\n\n")
    csd.write("<CsInstruments>\n\n")
    csd.write("sr=16000\n")
    csd.write("ksmps=50\n")
    csd.write("nchnls=1\n\n")
    for line in orchlines:
        csd.write(line)
    csd.write("\n</CsInstruments>\n\n")
    csd.write("<CsScore>\n\n")
    csd.write("f1 0 2048 10 1\n")
    csd.write("f2 0 2048 10 1 0 .33 0 .2 0 .143 0 .111\n")
    csd.write("f3 0 2048 10 1 .5 .33 .25 .2 .175 .143 .125 .111 .1\n")
    csd.write("f10 0 2048 10 1 0 0 .3 0 .2 0 0 .1\n")
    csd.write("f99 0 2048 7 1 2048 1\n")
    csd.write("f100 0 2048 7 0. 10 1. 1900 1. 132 0.\n")
    for line in scorelines:
        csd.write(line)
    csd.write("e\n")
    csd.write("\n</CsScore>\n")
    csd.write("\n</CsoundSynthesizer>")
    csd.close()
 
    os.system('csound ' + path + '/temp.csd >/dev/null 2>/dev/null')
