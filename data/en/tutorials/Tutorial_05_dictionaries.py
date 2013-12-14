basket = { 'oranges': 12, 'pears': 5, 'apples': 4 }

basket['bananas'] = 5

print basket
print "There are %d various items in the basket" % len(basket)

print basket['apples']
basket['apples'] = 8
print basket['apples']

print basket.get('oranges', 'undefined')
print basket.get('cherries', 'undefined')
