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

def playSine( pitch=1000, amp=5000, dur=1, starttime=0):
    """Play a sine wave (pitch = [1000], amp = [5000], dur = [1], starttime = [0])"""
    if not 1 in instrlist:
        orchlines.append("instr 1\n")
        orchlines.append("asig oscil p5, p4, 1\n")
        orchlines.append("out asig\n")
        orchlines.append("endin\n")
        instrlist.append(1)

    scorelines.append("i1 %f %f %f %f\n" % (float(starttime), float(dur), float(pitch), float(amp)))

def audioOut():
    path = os.path.dirname(os.path.abspath(__file__))
    csd = open(path + "/temp.csd", "w")
    csd.write("<CsoundSynthesizer>\n")
    csd.write("<CsOptions>\n")
    csd.write("-+rtaudio=alsa -odevaudio -m0 -d -b256 -B512\n")
    csd.write("</CsOptions>\n")
    csd.write("<CsInstruments>\n")
    csd.write("sr=16000\n")
    csd.write("ksmps=64\n")
    csd.write("nchnls=1\n")
    for line in orchlines:
        csd.write(line)
    csd.write("</CsInstruments>\n")
    csd.write("<CsScore>\n")
    csd.write("f1 0 1024 10 1\n")
    for line in scorelines:
        csd.write(line)
    csd.write("e\n")
    csd.write("</CsScore>\n")
    csd.write("</CsoundSynthesizer>\n")
    csd.close()

    cs = csnd.Csound()
    cs.Compile(path + '/temp.csd')
    perf = csnd.CsoundPerformanceThread(cs)
    perf.Play()


