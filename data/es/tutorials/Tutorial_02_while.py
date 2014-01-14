# -*- coding: utf-8

import time

def while_cuenta_regresiva(numero):
    while(numero > -1):
        print  str(numero) + ' para la explosion!!!'
        time.sleep(1)
        numero = numero -1

numero = input('Escribe un numero: ')
print 'Cuenta regresiva usando sentencia while!!'
while_cuenta_regresiva(numero)
print 'Kaboooommm!!!, X_X'
