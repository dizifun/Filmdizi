import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import base64
import codecs
import json
import os

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmizle.life"
DB_DOSYA = "veritabani.json"
SAYFA_BASI_KATEGORI = 500

KATEGORILER = [
    ("Aile", "/tur/aile-1/"), ("Aksiyon", "/tur/aksiyon-2/"), ("Animasyon", "/tur/animasyon-1/"),
    ("Belgesel", "/tur/belgesel/"), ("Bilim Kurgu", "/tur/bilim-kurgu-1/"), ("Dram", "/tur/dram-1/"),
    ("Fantastik", "/tur/fantastik-1/"), ("Gerilim", "/tur/gerilim-1/"), ("Gizem", "/tur/gizem-1/"),
    ("Komedi", "/tur/komedi-1/"), ("Korku", "/tur/korku-1/"), ("Macera", "/tur/macera-1/"),
    ("Müzik", "/tur/muzik/"), ("Romantik", "/tur/romantik-1/"), ("Savaş", "/tur/savas-1/"),
    ("Suç", "/tur/suc-1/"), ("Tarih", "/tur/tarih-1/"), ("TV Film", "/tur/tv-film-1/"),
    ("Vahşi Batı", "/tur/vahsi-bati/"), ("Yerli Film", "/tur/yerli-film-izle-1/")
]

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})

def db_yukle():
    if os.path.exists(DB_DOSYA):
        with open(DB_DOSYA, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def db_kaydet(veri):
    with open(DB_DOSYA, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=4)

def sifreyi_kir(sifreli_metin):
    try:
        eksik = len(sifreli_metin) % 4
        if eksik: sifreli_metin += '=' * (4 - eksik)
        return codecs.decode(base64.b64decode(sifreli_metin).decode('utf-8'), 'rot_13')[::-1]
    except: return None

def video_linki_bul(url):
    try:
        res = scraper.get(url, timeout=10)
        soup = BeautifulSoup(res.content, "html.parser")
        iframe = soup.find("iframe", src=re.compile("vidrame"))
        p_url = iframe['src'] if iframe else None
        
        if not p_url:
            match = re.search(r'https://vidrame\.pro/[a-zA-Z0-9/]+', str(res.content))
            if match: p_url = match.group(0)

        if p_url:
            if p_url.startswith("//"): p_url = "https:" + p_url
            res_p = scraper.get(p_url, headers={'Referer': BASE_URL}, timeout=10)
            match = re.search(r'EE\.dd\([\"\']([a-zA-Z0-9+/=]+)[\"\']\)', res_p.text)
            if match:
                link = sifreyi_kir(match.group(1))
                if link and ".m3u8" in link: return link.strip()
    except: pass
    return None

def baslat():
    veritabani = db_yukle()
    kayitli_linkler = {v['sayfa_url'] for v in veritabani}
    
    print("🚀 İÇERİK BOTU BAŞLADI (Hızlı Mod)...")
    
    for kat, yol in KATEGORILER:
        print(f"📂 {kat} taranıyor...")
        for sayfa in range(1, SAYFA_BASI_KATEGORI + 1):
            url = BASE_URL + yol + (f"page/{sayfa}/" if sayfa > 1 else "")
            try:
                soup = BeautifulSoup(scraper.get(url).content, 'html.parser')
                filmler = soup.select("a.poster")
                if not filmler: break
                
                yeni_sayi = 0
                for kutu in filmler:
                    href = BASE_URL + kutu.get('href')
                    if href in kayitli_linkler: continue
                    
                    baslik = kutu.find(class_="title").text.strip()
                    img = kutu.find("img").get('data-src') or kutu.find("img").get('src')
                    if img and not img.startswith("http"): img = BASE_URL + img
                    
                    video = video_linki_bul(href)
                    if video:
                        yeni_veri = {
                            "baslik": baslik, "poster": img, "kategori": kat,
                            "video_url": video, "sayfa_url": href, "altyazi": None
                        }
                        veritabani.append(yeni_veri)
                        kayitli_linkler.add(href)
                        yeni_sayi += 1
                        print(f"   ✅ {baslik}")
                        
                if yeni_sayi > 0: db_kaydet(veritabani)
            except: pass
    print("🏁 İÇERİK TARAMASI BİTTİ.")

if __name__ == "__main__":
    baslat()

