from platform import architecture
from platform import system as platformsystem

s = platformsystem()
arch, arch2 = architecture()

print "Loading box2d for %s (%s)" % (s, arch)

if s == 'Linux':
    if arch == "64bit": 
        from box2d_linux64 import *
    else: 
#        try:
        from box2d_linux32 import *
#        except:
#            from box2d_linux32ppc import *
#
#elif s == 'Windows': 
#    from box2d_win import *
#    
#elif s == 'Darwin': 
#    from box2d_macosx import *
