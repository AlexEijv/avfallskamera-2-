# lamptest.py - kör i Thonny (Kör aktuellt skript) för att hitta vilken lampa som sitter på vilken pinne.
# Tänder EN pinne i taget i 1,5 sekunder och skriver ut vilken. Anteckna vilken lampa som lyser vid vilken pinne.
import time
from machine import Pin

PINNAR = [4, 2, 14, 13, 15, 12]      # IO-numren på kortet
for runda in range(2):
    for nr in PINNAR:
        p = Pin(nr, Pin.OUT, value=0)
        print("Tänd: IO" + str(nr))
        p.value(1)
        time.sleep(1.5)
        p.value(0)
        time.sleep(0.5)
print("Klart")
