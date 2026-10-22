"""Lokal server för avfallskameran.
 - Serverar index.html, samples/ och lib/
 - /esp?u=<url>  hämtar en stillbild från ESP32-CAM:en åt webbläsaren (undviker CORS-problem)
 - Provar port 8000-8010 tills en är ledig
"""
import http.server, socketserver, webbrowser, urllib.request, urllib.parse, ipaddress

class Server(http.server.ThreadingHTTPServer):
    allow_reuse_address = False          # ger tydligt fel i stället för tyst dubbelbindning på Windows
    daemon_threads = True

class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".bin": "application/octet-stream", ".json": "application/json", ".js": "text/javascript"}

    def do_GET(self):
        if self.path.startswith("/esp?"):
            return self.proxy()
        return super().do_GET()

    def proxy(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        url = q.get("u", [""])[0]
        try:
            p = urllib.parse.urlparse(url)
            if p.scheme != "http" or not ipaddress.ip_address(p.hostname).is_private:
                raise ValueError("Bara http-adresser på lokala nätverk (t.ex. 192.168.x.x) tillåts")
            with urllib.request.urlopen(url, timeout=5) as r:
                data = r.read()
                ctype = r.headers.get_content_type() or "image/jpeg"
        except Exception as e:
            self.send_error(502, str(e)[:120].replace("\n", " "))
            return
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):
        if "/esp?" not in (args[0] if args else ""):   # tysta bildhämtningarna i terminalen
            super().log_message(fmt, *args)

for port in range(8000, 8011):
    try:
        httpd = Server(("", port), Handler)
        break
    except OSError:
        print(f"Port {port} är upptagen, provar nästa…")
else:
    raise SystemExit("Hittade ingen ledig port mellan 8000 och 8010.")

url = f"http://localhost:{port}/index.html"
print(f"Öppna {url}   (avsluta med Ctrl+C)")
print("Använd alltid SAMMA adress/port, annars glömmer webbläsaren vad AI:n lärt sig.")
webbrowser.open(url)
try:
    httpd.serve_forever()
except KeyboardInterrupt:
    print("Avslutar.")
