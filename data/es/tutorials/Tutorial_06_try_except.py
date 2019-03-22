def es_numero_valido(num):
    try:
        int(num)
        print("Escribio un numero")
    except:
        print("Lo siento, no escribiste un numero")

number1 = eval(input("Escriba y le dire si es un numero: "))
es_numero_valido(number1)
