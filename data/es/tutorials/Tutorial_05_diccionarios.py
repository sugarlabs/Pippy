canasta = { 'naranjas': 12, 'peras': 5, 'manzanas': 4 }

canasta['bananas'] = 5

print canasta
print "Hay %d tipos de fruta en la canasta" % len(canasta)

print canasta['manzanas']
canasta['manzanas'] = 8
print canasta['manzanas']

print canasta.get('naranjas', 'undefined')
print canasta.get('cerezas', 'undefined')
