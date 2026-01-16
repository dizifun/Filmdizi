import cloudscraper
from bs4 import BeautifulSoup
import re
import time
import base64
import codecs

# --- AYARLAR ---
BASE_URL = "https://www.hdfilmizle.life"
M3U_DOSYA_ADI = "playlist.m3u"
KAÇ_SAYFA_TARANSIN = 3  # Test için az tutalım, çalışırsa artırırsın

# Cloudscraper: Siteye "Ben Chrome Tarayıcıyım" diyen özel kütüphane
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

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
        # requests yerine scraper kullanıyoruz
        response = scraper.get(url, timeout=15)
        
        if response.status_code != 200: 
            print(f"   ⚠️ Site engelledi! Kod: {response.status_code}")
            return None, None

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
            
            # Referer header'ı ekleyerek player'a git
            # Cloudscraper'ın kendi header yönetimi vardır ama biz yine de ekleyelim
            headers_player = {'Referer': 'https://www.hdfilmizle.life/'}
            res_p = scraper.get(player_url, headers=headers_player, timeout=15)
            
            match_code = re.search(r'EE\.dd\([\"\']([a-zA-Z0-9+/=]+)[\"\']\)', res_p.text)
            if match_code:
                link = sifreyi_kir(match_code.group(1))
                if link and ".m3u8" in link:
                    return kategori, link.strip()
    except Exception as e:
        print(f"   Hata: {e}")
    return None, None

def baslat():
    m3u_baslat()
    print(f"🚀 Bulut Delici Modu Başlatıldı! {KAÇ_SAYFA_TARANSIN} sayfa taranıyor...")
    
    # Önce ana sayfaya bir "Merhaba" diyelim ki cookie alalım
    try:
        scraper.get(BASE_URL)
    except:
        pass
    
    basarili_sayisi = 0

    for sayfa in range(1, KAÇ_SAYFA_TARANSIN + 1):
        if sayfa == 1: url = BASE_URL
        else: url = f"{BASE_URL}/page/{sayfa}/"
        
        print(f"\n🌍 Sayfa {sayfa} taranıyor...")
        
        try:
            resp = scraper.get(url, timeout=20)
            
            if resp.status_code != 200:
                print(f"❌ Ana sayfa erişim hatası: {resp.status_code}")
                # Eğer 403 alıyorsak Cloudflare bizi tamamen engellemiştir.
                if resp.status_code == 403:
                    print("!!! CLOUDFLARE ENGELİ: GitHub IP'si kara listede !!!")
                    break
                continue

            soup = BeautifulSoup(resp.content, 'html.parser')
            filmler = soup.select("a.poster")
            if not filmler: filmler = soup.select(".film-content a")
            
            if not filmler:
                print("   ⚠️ Film bulunamadı (HTML yapısı değişmiş veya Gizli Engel yemiş olabilir).")
                break
                
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
                
                # Çok hızlı yaparsak ban yeriz, azıcık bekleyelim
                time.sleep(1) 
                
                kategori, video_link = film_detaylarini_getir(full_link)
                
                if video_link:
                    if sayfa == 1: kategori = f"YENİ EKLENENLER;{kategori}"
                    m3u_ekle(film_adi, poster, kategori, video_link)
                    print(f"+ Eklendi: {film_adi}")
                    basarili_sayisi += 1
                else:
                    print(f"- Video yok: {film_adi}")
                
        except Exception as e:
            print(f"Sayfa hatası: {e}")
            
    print(f"\n🏁 BİTTİ! Toplam {basarili_sayisi} film listeye eklendi.")

if __name__ == "__main__":
    baslat()
