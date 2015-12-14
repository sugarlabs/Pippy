import platform
if platform.architecture()[0] == '64bit':
    from box2d_64 import *
else:
    from box2d_32 import *
