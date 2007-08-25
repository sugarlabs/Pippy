#! /usr/bin/env python

# does csound5 support string in pfield? for wave player intrument

import os
from sugar import env

orchlines = []
scorelines = []
instrlist = []
wavnum = [10]
complexnum  = [10]
fnum = [100]

temp_path = env.get_profile_path() + '/pippy'
if not os.path.isdir(temp_path):
    os.mkdir(temp_path)

def quit(self):
    perf.Stop()
    perf.Join()                                    
    cs.Reset()
    cs = None            

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
    complexnum[0] += 1
    scorelines.append("f" + str(complexnum[0]) + " 0 2048 10 " + " ".join([str(n) for n in list]))
    return complexnum[0]

def playSine( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a sine wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, 1)

def playSquare( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a square wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, 2)

def playSawtooth( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a sawtooth wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    _play(pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, 3)

def _play( pitch, amplitude, duration, starttime, pitch_envelope, amplitude_envelope, instrument):
    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    if not instrument in instrlist:
        orchlines.append("instr %ld\n" % instrument)
        orchlines.append("kpitenv oscil 1, 1/p3, p6\n")
        orchlines.append("aenv oscil 1, 1/p3, p7\n")
        orchlines.append("asig oscil p5*aenv, p4*kpitenv, %ld\n" % instrument)
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(instrument)

    scorelines.append("i%ld %s %s %s %s %s %s\n" % (instrument, str(starttime), str(duration), str(pitch), str(amplitude), str(pitenv), str(ampenv)))

def playComplex( pitch=1000, amplitude=5000, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default', wave='default'):
    """Play a complex wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], pitch_envelope = ['default'], amplitude_envelope, wave = ['default'] )"""
    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    if wave == 'default': wavetable = 10
    else: wavetable = wave

    if not 4 in instrlist:
        orchlines.append("instr 4\n")
        orchlines.append("kpitenv oscil 1, 1/p3, p6\n")
        orchlines.append("aenv oscil 1, 1/p3, p7\n")
        orchlines.append("asig oscil p5*aenv, p4*kpitenv, p8\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(4)

    scorelines.append("i4 %s %s %s %s %s %s %s\n" % (str(starttime), str(duration), str(pitch), str(amplitude), str(pitenv), str(ampenv), str(wavetable)))

def playWave(sound='horse', pitch=1, amplitude=1, loop=False, duration=1, starttime=0, pitch_envelope='default', amplitude_envelope='default'):
    """Play a wave file (sound = ['horse'], pitch = [1], amplitude = [1], loop = [False], duration = [1], starttime = [0], pitch_envelope=['default'], amplitude_envelope=['default'])"""
    fullname = '/usr/share/activities/TamTam.activity/Resources/Sounds/' + str(sound)

    if loop == False: lp = 0
    else: lp = 1

    if pitch_envelope == 'default': pitenv = 99
    else: pitenv = pitch_envelope

    if amplitude_envelope == 'default': ampenv = 100
    else: ampenv = amplitude_envelope

    wavnum[0] += 1

    orchlines.append("instr %ld\n" % wavnum[0]) 
    orchlines.append("kpitenv oscil 1, 1/p3, p4\n")
    orchlines.append("aenv oscil 1, 1/p3, p5\n")
    orchlines.append('asig diskin "%s", %s*kpitenv, 0, %ld\n' % (fullname, str(pitch), lp)) 
    orchlines.append("out asig*%f*aenv\n" % float(amplitude))
    orchlines.append("endin\n\n")

    scorelines.append("i%ld %f %f %s %s\n" % (wavnum[0], float(starttime), float(duration), str(pitenv), str(ampenv)))

def audioOut():
    path = temp_path
    csd = open(path + "/temp.csd", "w")
    csd.write("<CsoundSynthesizer>\n\n")
    csd.write("<CsOptions>\n")
    csd.write("-+rtaudio=alsa -odevaudio -m0 -d -b256 -B512\n")
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
    csd.write("f100 0 2048 7 0. 15 1. 1900 1. 132 0.\n")
    for line in scorelines:
        csd.write(line)
    csd.write("e\n")
    csd.write("\n</CsScore>\n")
    csd.write("\n</CsoundSynthesizer>")
    csd.close()
 
    os.system('csound ' + path + '/temp.csd')
