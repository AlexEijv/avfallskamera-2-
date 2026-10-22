# main.py för ESP32-CAM (MicroPython)
# Gör tre saker:
#   1. Startar ett öppet wifi (ESP32 är åtkomstpunkt) på adressen 192.168.4.2
#   2. http://192.168.4.2/capture   -> en JPEG-bild från kameran
#   3. http://192.168.4.2/led?gron=1&gul=0&rod=0&ms=3000  -> tänder lamporna; ms = släck automatiskt efter så många millisekunder
# Testsida med levande bild och lampknappar: http://192.168.4.2/
#
# Krav: en MicroPython-firmware med kameramodulen ("import camera" ska fungera i Thonny).

import network, socket, time, gc
import camera
from machine import Pin, Timer

# AI-Thinker ESP32-CAM: PWDN must be LOW before the camera is initialized.
pwdn = Pin(32, Pin.OUT)
pwdn.value(0)
time.sleep(0.5)

# ---------- Inställningar ----------
SSID = "Avfallskamera"          # skriv namnet på det wifi du redan kopplar till om du vill behålla det
IP = "192.168.4.2"
LAMP_PINNAR = {"gron": 2, "gul": 4, "rod": 14}   # Din koppling: grön IO2, gul IO4, röd IO14.
# OBS: IO4 är även kortets vita blixtlampa, den lyser med när IO4 är tänd. Lampor ska ha motstånd 220-330 ohm.

# ---------- Lampor ----------
LAMPOR = {namn: Pin(pin, Pin.OUT, value=0) for namn, pin in LAMP_PINNAR.items()}

tim = Timer(0)

def lamptest():
    """Tänder varje lampa i tur och ordning. Visar om kopplingen fungerar."""
    for namn, lampa in LAMPOR.items():
        print("Lamptest:", namn, "på IO" + str(LAMP_PINNAR[namn]))
        lampa.value(1)
        time.sleep(0.8)
        lampa.value(0)
        time.sleep(0.2)
    for lampa in LAMPOR.values():
        lampa.value(1)
    time.sleep(0.8)
    for lampa in LAMPOR.values():
        lampa.value(0)

lamptest()   # körs varje gång kortet startar

def alla_av(_=None):
    for lampa in LAMPOR.values():
        lampa.value(0)

def satt_lampor(query):
    ms = 0
    for del_ in query.split("&"):
        if "=" in del_:
            namn, varde = del_.split("=", 1)
            if namn in LAMPOR:
                LAMPOR[namn].value(1 if varde == "1" else 0)
            elif namn == "ms":
                try:
                    ms = int(varde)
                except ValueError:
                    ms = 0
    tim.deinit()
    # säkerhetsslock: släck själv efter ms även om datorn tappar kontakten
    if ms > 0 and any(l.value() for l in LAMPOR.values()):
        tim.init(period=ms, mode=Timer.ONE_SHOT, callback=alla_av)

# ---------- Wifi ----------
ap = network.WLAN(network.AP_IF)
ap.active(True)
ap.config(essid=SSID, authmode=network.AUTH_OPEN)
ap.ifconfig((IP, "255.255.255.0", IP, "8.8.8.8"))
print("Wifi:", SSID, "adress:", ap.ifconfig()[0])

# ---------- Kamera ----------
camera.init(0, format=camera.JPEG)
try:
    camera.framesize(camera.FRAME_QVGA)   # 320x240, snabbt. Byt till FRAME_VGA för skarpare bild.
except Exception as e:
    print("Kunde inte sätta bildstorlek:", e)
time.sleep(1)

# ---------- Webbserver ----------
SIDA = b"""<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center">
<h3>Avfallskamera</h3><img id="b" width="320"><br><br>
<button onclick="l('gron=1&gul=0&rod=0')">Gron</button>
<button onclick="l('gron=0&gul=1&rod=0')">Gul</button>
<button onclick="l('gron=0&gul=0&rod=1')">Rod</button>
<button onclick="l('gron=0&gul=0&rod=0')">Av</button>
<script>
function l(q){fetch('/led?'+q)}
function n(){var i=document.getElementById('b');i.onload=function(){setTimeout(n,100)};
i.onerror=function(){setTimeout(n,1000)};i.src='/capture?t='+Date.now()}
n();
</script></body></html>"""

def skicka(conn, data):
    mv = memoryview(data)
    i = 0
    while i < len(mv):
        n = conn.send(mv[i:i + 1024])
        if n:
            i += n

def svar(conn, status, typ, data):
    skicka(conn, ("HTTP/1.1 %s\r\nContent-Type: %s\r\nContent-Length: %d\r\n"
                  "Access-Control-Allow-Origin: *\r\nCache-Control: no-store\r\nConnection: close\r\n\r\n"
                  % (status, typ, len(data))).encode())
    skicka(conn, data)

def hantera(conn):
    forfragan = conn.recv(1024).decode("utf-8", "ignore")
    rad = forfragan.split("\r\n")[0].split(" ")
    if len(rad) < 2:
        return
    vag, _, query = rad[1].partition("?")
    if vag == "/capture":
        bild = camera.capture()
        if bild:
            svar(conn, "200 OK", "image/jpeg", bild)
        else:
            svar(conn, "500 Internal Server Error", "text/plain", b"ingen bild")
    elif vag == "/led":
        print("LED-kommando:", query)
        satt_lampor(query)
        svar(conn, "200 OK", "text/plain", b"ok")
    elif vag == "/lamptest":
        lamptest()
        svar(conn, "200 OK", "text/plain", b"lamptest klart")
    elif vag == "/":
        svar(conn, "200 OK", "text/html", SIDA)
    else:
        svar(conn, "404 Not Found", "text/plain", b"finns inte")

server = socket.socket()
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind(("", 80))
server.listen(3)
print("Servern är igång på http://%s/" % IP)

while True:
    conn = None
    try:
        conn, adr = server.accept()
        conn.settimeout(5)
        hantera(conn)
    except Exception as e:
        print("Fel:", e)
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass
        gc.collect()
