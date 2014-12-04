def is_valid_number(num):
    try:
        int(num)
        print "You wrote a number"
    except:
        print "Sorry but, you didn't write a number"

number1 = raw_input("Give me any input and I will tell you if it's a number: ")
is_valid_number(number1)
