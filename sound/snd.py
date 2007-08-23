#! /usr/bin/env python
import os
import csnd

orchlines = []
scorelines = []
instrlist = []


def quit(self):
    perf.Stop()
    perf.Join()                                    
    cs.Reset()
    cs = None            

def defEnvelope(attack=0.01, decay=0.1, sustain=0.8, release=0.1):
    """Define an envelope (attack = [0.01], decay = [0.1], sustain = [0.8], release = [0.1])"""
    att = int(1024 * attack)
    dec = int(1024 * decay)
    rel = int(1024 * release)
    bal = 1024 - (att + dec + rel)
    sus = min(1., sustain)

    scorelines.append("f100 0 1024 7 0 %ld 1. %ld %f %ld %f %ld 0" % (att, dec, sus, bal, sus, rel))

def playSine( pitch=1000, amp=5000, dur=1, starttime=0):
    """Play a sine wave (pitch = [1000], amp = [5000], dur = [1], starttime = [0])"""
    if not 1 in instrlist:
        orchlines.append("instr 1\n")
        orchlines.append("asig oscil p5, p4, 1\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(1)

    scorelines.append("i1 %s %s %s %s\n" % (str(starttime), str(dur), str(pitch), str(amp)))

def playSquare( pitch=1000, amp=5000, dur=1, starttime=0):
    """Play a square wave (pitch = [1000], amp = [5000], dur = [1], starttime = [0])"""
    if not 2 in instrlist:
        orchlines.append("instr 2\n")
        orchlines.append("asig oscil p5, p4, 2\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n\n")
        instrlist.append(2)

    scorelines.append("i2 %f %f %f %f\n" % (float(starttime), float(dur), float(pitch), float(amp)))

def playWave(name='horse', pitch=1, amp=1, loop=False, dur=1, starttime=0):
    """Play a wave file (name = ['horse'], pitch = [1], amp = [1], loop = [False], dur = [1], starttime = [0])"""
    fullname = '/usr/share/activities/TamTam.activity/Resources/Sounds/' + str(name)
    if loop == False:
        lp = 0
    else:
        lp = 1

    orchlines.append("instr 10\n") 
    orchlines.append('asig diskin "%s", %s, 0, %ld\n' % (fullname, str(pitch), lp)) 
    orchlines.append("out asig\n")
    orchlines.append("endin\n\n")

    scorelines.append("i10 %s %s\n" % (float(starttime), float(dur)))

def audioOut():
    path = os.path.dirname(os.path.abspath(__file__))
    csd = open(path + "/temp.csd", "w")
    csd.write("<CsoundSynthesizer>\n\n")
    csd.write("<CsOptions>\n")
    csd.write("-+rtaudio=alsa -odevaudio -m0 -d -b256 -B512\n")
    csd.write("</CsOptions>\n\n")
    csd.write("<CsInstruments>\n\n")
    csd.write("sr=16000\n")
    csd.write("ksmps=64\n")
    csd.write("nchnls=1\n\n")
    for line in orchlines:
        csd.write(line)
    csd.write("\n</CsInstruments>\n\n")
    csd.write("<CsScore>\n\n")
    csd.write("f1 0 1024 10 1\n")
    csd.write("f2 0 1024 10 1 0 .33 0 .2 0 .143 0 .111\n")
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


