import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import base64
import codecs

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmizle.life"
M3U_DOSYA_ADI = "playlist.m3u"
SAYFA_BASI_KATEGORI = 500  # Tüm sayfaları gezmesi için yüksek sayı

# --- KATEGORİ LİSTESİ ---
KATEGORILER = [
    ("Aile", "/tur/aile-1/"),
    ("Aksiyon", "/tur/aksiyon-2/"),
    ("Animasyon", "/tur/animasyon-1/"),
    ("Belgesel", "/tur/belgesel/"),
    ("Bilim Kurgu", "/tur/bilim-kurgu-1/"),
    ("Dram", "/tur/dram-1/"),
    ("Fantastik", "/tur/fantastik-1/"),
    ("Gerilim", "/tur/gerilim-1/"),
    ("Gizem", "/tur/gizem-1/"),
    ("Komedi", "/tur/komedi-1/"),
    ("Korku", "/tur/korku-1/"),
    ("Macera", "/tur/macera-1/"),
    ("Müzik", "/tur/muzik/"),
    ("Romantik", "/tur/romantik-1/"),
    ("Savaş", "/tur/savas-1/"),
    ("Suç", "/tur/suc-1/"),
    ("Tarih", "/tur/tarih-1/"),
    ("TV Film", "/tur/tv-film-1/"),
    ("Vahşi Batı", "/tur/vahsi-bati/"),
    ("Yerli Film", "/tur/yerli-film-izle-1/")
]

EKLENEN_LINKLER = set()

scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})

def m3u_baslat():
    with open(M3U_DOSYA_ADI, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

def m3u_ekle(film_adi, poster, kategori, link):
    if not kategori: kategori = "Genel"
    kategori = kategori.replace(",", " -")
    
    # Altyazı etiketi YOK, sadece video
    satir = f'#EXTINF:-1 tvg-logo="{poster}" group-title="{kategori}",{film_adi}\n{link}\n'
    
    with open(M3U_DOSYA_ADI, "a", encoding="utf-8") as f:
        f.write(satir)

def sifreyi_kir(sifreli_metin):
    try:
        eksik = len(sifreli_metin) % 4
        if eksik: sifreli_metin += '=' * (4 - eksik)
        adim1 = base64.b64decode(sifreli_metin).decode('utf-8')
        adim2 = codecs.decode(adim1, 'rot_13')
        return adim2[::-1]
    except:
        return None

def film_detaylarini_getir(url):
    try:
        response = scraper.get(url, timeout=15)
        if response.status_code != 200: return None

        soup = BeautifulSoup(response.content, "html.parser")
        
        player_url = None
        iframes = soup.find_all("iframe")
        for iframe in iframes:
            if "vidrame" in iframe.get("src", ""):
                player_url = iframe.get("src")
                break
        
        if not player_url:
            match = re.search(r'https://vidrame\.pro/[a-zA-Z0-9/]+', str(response.content))
            if match: player_url = match.group(0)

        if player_url:
            if player_url.startswith("//"): player_url = "https:" + player_url
            h_player = {'Referer': 'https://www.hdfilmizle.life/'}
            res_p = scraper.get(player_url, headers=h_player, timeout=15)
            
            # Sadece şifreyi çöz ve linki al
            match_code = re.search(r'EE\.dd\([\"\']([a-zA-Z0-9+/=]+)[\"\']\)', res_p.text)
            if match_code:
                link = sifreyi_kir(match_code.group(1))
                if link and ".m3u8" in link:
                    return link.strip()
    except:
        pass
    return None

def baslat():
    m3u_baslat()
    print(f"🚀 HIZLI MOD BAŞLATILDI! (Sadece Videolar)\n")
    
    toplam_eklenen = 0

    for kat_adi, kat_url in KATEGORILER:
        print(f"📂 KATEGORİ: {kat_adi}")
        
        for sayfa in range(1, SAYFA_BASI_KATEGORI + 1):
            if sayfa == 1: tam_url = BASE_URL + kat_url
            else: tam_url = BASE_URL + kat_url + f"page/{sayfa}/"
            
            try:
                resp = scraper.get(tam_url, timeout=20)
                soup = BeautifulSoup(resp.content, 'html.parser')
                filmler = soup.select("a.poster")
                
                if not filmler:
                    print(f"   🏁 {kat_adi} bitti.")
                    break
                
                for kutu in filmler:
                    href = kutu.get('href')
                    if not href: continue
                    full_link = BASE_URL + href if href.startswith("/") else href
                    
                    if full_link in EKLENEN_LINKLER: continue
                    
                    t_tag = kutu.find("h2", class_="title") or kutu.find("div", class_="title")
                    film_adi = t_tag.text.strip() if t_tag else "Film"
                    
                    img = kutu.find("img")
                    poster = ""
                    if img:
                        poster = img.get('data-src') or img.get('src')
                        if poster and not poster.startswith("http"): poster = BASE_URL + poster
                    
                    # Sadece videoyu çek
                    video_link = film_detaylarini_getir(full_link)
                    
                    if video_link:
                        m3u_ekle(film_adi, poster, kat_adi, video_link)
                        EKLENEN_LINKLER.add(full_link)
                        toplam_eklenen += 1
                        print(f"   ✅ {film_adi}")
                    
                    # Hızlı gitmesi için bekleme süresi çok kısa
                    time.sleep(0.01)
                
            except Exception as e:
                print(f"   ❌ Hata: {e}")
                
    print(f"\n🏁 İŞLEM TAMAM! Toplam {toplam_eklenen} film eklendi.")

if __name__ == "__main__":
    baslat()

