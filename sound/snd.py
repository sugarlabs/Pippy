#! /usr/bin/env python

# TODO: Apply pitch envelope
#       define breakpoints function

import os
import csnd

orchlines = []
scorelines = []
instrlist = []
wavnum = [10]
fnum = [100]


def quit(self):
    perf.Stop()
    perf.Join()                                    
    cs.Reset()
    cs = None            

def defADSR(attack=0.01, decay=0.1, sustain=0.8, release=0.1):
    """Define an ADSR envelope. fnum = defADSR(attack = [0.01], decay = [0.1], sustain = [0.8], release = [0.1])"""
    att = int(1024 * attack)
    dec = int(1024 * decay)
    rel = int(1024 * release)
    bal = 1024 - (att + dec + rel)
    sus = min(1., sustain)

    fnum[0] += 1
    scorelines.append("f%ld 0 1024 7 0 %ld 1. %ld %f %ld %f %ld 0\n" % (fnum[0], att, dec, sus, bal, sus, rel))
    return fnum[0]

def playSine( pitch=1000, amplitude=5000, duration=1, starttime=0, envelope='default'):
    """Play a sine wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], envelope=['default'])"""
    if envelope == 'default':
        env = 100
    else:
        env = envelope

    if not 1 in instrlist:
        orchlines.append("instr 1\n")
        orchlines.append("aenv oscil 1, 1/p3, p6\n")
        orchlines.append("asig oscil p5*aenv, p4, 1\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(1)

    scorelines.append("i1 %s %s %s %s %s\n" % (str(starttime), str(duration), str(pitch), str(amplitude), str(env)))

def playSquare( pitch=1000, amplitude=5000, duration=1, starttime=0, envelope='default'):
    """Play a square wave (pitch = [1000], amplitude = [5000], duration = [1], starttime = [0], envelope=['default'])"""
    if envelope == 'default':
        env = 100
    else:
        env = envelope

    if not 2 in instrlist:
        orchlines.append("instr 2\n")
        orchlines.append("aenv oscil 1, 1/p3, p6\n")
        orchlines.append("asig oscil p5*aenv, p4, 2\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(2)

    scorelines.append("i2 %s %s %s %s %s\n" % (str(starttime), str(duration), str(pitch), str(amplitude), str(env)))

def playWave(sound='horse', pitch=1, amplitude=1, loop=False, duration=1, starttime=0, envelope='default'):
    """Play a wave file (sound = ['horse'], pitch = [1], amplitude = [1], loop = [False], duration = [1], starttime = [0], envelope=['default'])"""

    fullname = '/usr/share/activities/TamTam.activity/Resources/Sounds/' + str(sound)
    if loop == False:
        lp = 0
    else:
        lp = 1

    if envelope == 'default':
        env = 100
    else:
        env = envelope

    wavnum[0] += 1

    orchlines.append("instr %ld\n" % wavnum[0]) 
    orchlines.append("aenv oscil 1, 1/p3, p4\n")
    orchlines.append('asig diskin "%s", %s, 0, %ld\n' % (fullname, str(pitch), lp)) 
    orchlines.append("out asig*aenv\n")
    orchlines.append("endin\n\n")

    scorelines.append("i%ld %f %f %s\n" % (wavnum[0], float(starttime), float(duration), str(env)))

def audioOut():
    path = os.path.dirname(os.path.abspath(__file__))
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
    csd.write("f1 0 1024 10 1\n")
    csd.write("f2 0 1024 10 1 0 .33 0 .2 0 .143 0 .111\n")
    csd.write("f100 0 1024 7 0. 10 1. 950 1. 64 0.\n")
    for line in scorelines:
        csd.write(line)
    csd.write("e\n")
    csd.write("\n</CsScore>\n")
    csd.write("\n</CsoundSynthesizer>")
    csd.close()

    f = open(path + '/temp.csd', 'r')
    for line in f.readlines():
        print line[0:-1]
 
    #cs = csnd.Csound()
    #cs.Compile(path + '/temp.csd')
    #perf = csnd.CsoundPerformanceThread(cs)
    #perf.Play()


