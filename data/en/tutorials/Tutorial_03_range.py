def sum_in_range(num1, num2):
    total = num1
    num1 = num1 + 1
    num2 = num2 + 1
    for i in range(num1, num2):
        print str(total) + " + " + str(i) + " = " + str(total+i)
        total = total + 1

number1 = int(input('Enter first number: '))
number2 = int(input('Enter second number: '))

if number1 < number2:
    sum_in_range(number1, number2)
else:
    sum_in_range(number2, number1)


