my_list = []

num = 1

while(num < 5):
    data = input("Please enter number " + str(num) + ":")
    my_list.append(int(data))
    num = num + 1

print "You entered the following numbers:"
print my_list
