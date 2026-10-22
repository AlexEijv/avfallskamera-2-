"""Kör denna EN gång medan datorn har internet.
Laddar ner biblioteken och MobileNet-modellen till mappen lib/, så att sidan
fungerar även när datorn är kopplad till kamerans wifi (utan internet)."""
import os, json, urllib.request, urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = os.path.join(HERE, "lib")
os.makedirs(os.path.join(LIB, "mobilenet"), exist_ok=True)

SKRIPT = {
    "tf.min.js": "https://cdn.jsdelivr.net/npm/@tensorflow/tfjs@4.22.0/dist/tf.min.js",
    "mobilenet.min.js": "https://cdn.jsdelivr.net/npm/@tensorflow-models/mobilenet@2.1.1/dist/mobilenet.min.js",
    "knn-classifier.min.js": "https://cdn.jsdelivr.net/npm/@tensorflow-models/knn-classifier@1.2.6/dist/knn-classifier.min.js",
}
MODELLER = [
    "https://tfhub.dev/google/imagenet/mobilenet_v2_100_224/classification/3/model.json?tfjs-format=file",
    "https://www.kaggle.com/models/google/mobilenet-v2/tfJs/100-224-classification/3/model.json?tfjs-format=file",
]

def hamta(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read(), r.geturl()

for namn, url in SKRIPT.items():
    mal = os.path.join(LIB, namn)
    if os.path.exists(mal) and os.path.getsize(mal) > 1000:
        print("Har redan", namn)
        continue
    print("Hämtar", namn)
    data, _ = hamta(url)
    open(mal, "wb").write(data)

ok = False
for url in MODELLER:
    try:
        print("Hämtar modell från", url.split("?")[0])
        data, final = hamta(url)
        manifest = json.loads(data)
        bas = url.split("?")[0]          # skarvar mot ursprungsadressen (efter omdirigering pekar 'final' på en signerad länk)
        suffix = "?tfjs-format=file" if "tfjs-format" in url else ""
        filer = [p for g in manifest["weightsManifest"] for p in g["paths"]]
        for i, p in enumerate(filer, 1):
            print(f"  del {i}/{len(filer)}")
            d, _ = hamta(urllib.parse.urljoin(bas, p) + suffix)
            open(os.path.join(LIB, "mobilenet", p), "wb").write(d)
        open(os.path.join(LIB, "mobilenet", "model.json"), "wb").write(data)
        ok = True
        break
    except Exception as e:
        print("  misslyckades:", e)

print("\nKlart! Du kan nu koppla till kamerans wifi." if ok else
      "\nBiblioteken är hämtade men modellen gick inte att ladda ner. Sidan hämtar den då online istället.")
