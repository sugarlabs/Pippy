# Pascal's triangle
lines = 9
vector = [1]

for i in range(1, lines + 1):
    vector.insert(0, 0)
    vector.append(0)

for i in range(0, lines):
    newvector = vector[:]
    for j in range(0, len(vector) - 1):
        if (newvector[j] == 0):
            print '  ',
        else:
            print '%2d' % newvector[j],
        newvector[j] = vector[j - 1] + vector[j + 1]
    print
    vector = newvector[:]
