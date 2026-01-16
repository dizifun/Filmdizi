import requests
from bs4 import BeautifulSoup
import re
import time
import base64
import codecs

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmizle.life"
M3U_DOSYA_ADI = "playlist.m3u"
KAÇ_SAYFA_TARANSIN = 10  # İstersen bu sayıyı arttırabilirsin

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://www.hdfilmizle.life/'
}

def m3u_baslat():
    with open(M3U_DOSYA_ADI, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")

def m3u_ekle(film_adi, poster, kategori, link):
    if not kategori: kategori = "Genel"
    kategori = kategori.replace(",", " -")
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
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200: return None, None

        soup = BeautifulSoup(response.content, "html.parser")
        
        # Kategori
        kategori = "Sinema"
        tur_etiketleri = soup.select('a[href*="/tur/"]') 
        if tur_etiketleri:
            kategori = tur_etiketleri[0].text.strip()
        
        # Player Linki
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
            h_player = HEADERS.copy()
            h_player['Referer'] = 'https://www.hdfilmizle.life/'
            res_p = requests.get(player_url, headers=h_player, timeout=10)
            
            match_code = re.search(r'EE\.dd\([\"\']([a-zA-Z0-9+/=]+)[\"\']\)', res_p.text)
            if match_code:
                link = sifreyi_kir(match_code.group(1))
                if link and ".m3u8" in link:
                    return kategori, link.strip()
    except:
        pass
    return None, None

def baslat():
    m3u_baslat()
    print(f"🚀 İşlem Başladı! {KAÇ_SAYFA_TARANSIN} sayfa taranıyor...")
    
    for sayfa in range(1, KAÇ_SAYFA_TARANSIN + 1):
        if sayfa == 1: url = BASE_URL
        else: url = f"{BASE_URL}/page/{sayfa}/"
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            soup = BeautifulSoup(resp.content, 'html.parser')
            filmler = soup.select("a.poster")
            if not filmler: filmler = soup.select(".film-content a")
            
            if not filmler: break
                
            for kutu in filmler:
                href = kutu.get('href')
                if not href: continue
                full_link = BASE_URL + href if href.startswith("/") else href
                
                t_tag = kutu.find("h2", class_="title") or kutu.find("div", class_="title")
                film_adi = t_tag.text.strip() if t_tag else "Film"
                
                img = kutu.find("img")
                poster = ""
                if img:
                    poster = img.get('data-src') or img.get('src')
                    if poster and not poster.startswith("http"): poster = BASE_URL + poster
                
                kategori, video_link = film_detaylarini_getir(full_link)
                
                if video_link:
                    if sayfa == 1: kategori = f"YENİ EKLENENLER;{kategori}"
                    m3u_ekle(film_adi, poster, kategori, video_link)
                    print(f"+ Eklendi: {film_adi}")
                
        except Exception as e:
            print(f"Hata: {e}")

if __name__ == "__main__":
    baslat()
