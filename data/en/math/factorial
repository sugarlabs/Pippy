import time


def factorial_recursive(number):
    """ Define a factorial function in recursive flavor """
    result = 1
    if number > 0:
        result = number * factorial_recursive(number - 1)
        print 'factorizing: ', number, ' result: ', result
    return result


def factorial_iterative(number):
    """ Define a factorial function in iterative flavor """
    result = 1
    for i in range(1, number + 1):
        result = result * i
        print 'factorizing: ', i, ' result: ', result
    return result


def calculate(number, type):
    """ Calculate factorial using recursive and iterative methods """
    start = time.time()
    if type == 0:
        type_s = 'recursive'
        factorial_recursive(number)
    else:
        type_s = 'iterative'
        factorial_iterative(number)
    delta = time.time() - start
    if delta > 0:
        print 'Type: ', type_s, ' in: ', 1 / delta
    else:
        print 'Type: ', type_s

# ask for a number to compute the factorial of
number = input('Please input a number:')
print 'Calculating...'
calculate(number, 0)
calculate(number, 1)
