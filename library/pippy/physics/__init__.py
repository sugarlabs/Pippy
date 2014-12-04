import sys

__all__ = ['locals', 'menu']

# Use own 'elements' modified module
# http://bugs.sugarlabs.org/ticket/3361
# sys.path.append('library/pippy/physics/Elements-0.13-py2.5.egg')
from myelements import Elements
