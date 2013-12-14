mi_lista = []

num = 1

while(num < 5):
    data = input("Porfavor escriba el numero " + str(num) + ":")
    mi_lista.append(int(data))
    num = num + 1

print "Tu escribiste los siguientes numeros:"
print mi_lista
