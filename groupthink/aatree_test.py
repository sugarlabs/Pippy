from aatree import *
x = TreeList()
y = AATreeList()

def test(a):
    a[0] = 1
    a[1] = 2
    a[2] = 3
    a[3] = 4
    a[1] = 'b'
    del a[2]
    assert a.index('b') == 1
    assert a.index(4) == 2
    
test(x)
test(y)
