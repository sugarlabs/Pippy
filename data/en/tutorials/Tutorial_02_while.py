import time

def while_backward_count(number):
    while(number > -1):
        print  str(number) + " for the explosion!!!"
        time.sleep(1)
        number = number -1

number = input('Enter a number: ')
print "Let's count backward using a while sentence!!"
while_backward_count(number)
print "Kaboooommm!!!, X_X"
