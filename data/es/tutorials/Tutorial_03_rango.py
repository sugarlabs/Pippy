def suma_en_rango(num1, num2):
    total = num1
    num1 = num1 + 1
    num2 = num2 + 1
    for i in range(num1, num2):
        print str(total) + " + " + str(i) + " = " + str(total+i)
        total = total + 1

numero1 = int(input('Escribe primer numero: '))
numero2 = int(input('Escribe segundo numero: '))

if numero1 > numero2:
    suma_en_rango(numero1, numero2)
else:
    suma_en_rango(numero2, numero1)


