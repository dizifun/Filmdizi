import requests
import json
import re
import concurrent.futures
import time
from urllib.parse import urljoin

# ==================== AYARLAR ====================
GITHUB_SOURCE_URL = 'https://raw.githubusercontent.com/nikyokki/nik-cloudstream/refs/heads/master/RecTV/src/main/kotlin/com/keyiflerolsun/RecTV.kt'
PROXY_URL = 'https://api.codetabs.com/v1/proxy/?quest=' + requests.utils.quote(GITHUB_SOURCE_URL)

# Sabitler
TIMEOUT = 20
MAX_WORKERS = 10  # Aynı anda kaç dizinin detayı çekilsin
FILE_SERIES = 'diziler.m3u'

class RecTVScraper:
    def __init__(self):
        # İlk koddaki Header yapısı korundu
        self.headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Referer': 'https://twitter.com/'
        }
        self.main_url = "https://m.prectv60.lol" # Fallback
        self.sw_key = ""
        self.series_buffer = ["#EXTM3U"]
        self.total_episodes = 0

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def fetch_github_config(self):
        """GitHub'dan güncel Key ve URL bilgilerini çeker (İlk koddan alındı)"""
        self.log("GitHub'dan yapılandırma çekiliyor...")
        content = None
        try:
            r = requests.get(GITHUB_SOURCE_URL, timeout=10)
            if r.status_code == 200: content = r.text
        except: pass
        
        if not content:
            try:
                r = requests.get(PROXY_URL, timeout=10)
                if r.status_code == 200: content = r.text
            except: pass

        if content:
            # Main URL
            m_url = re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content)
            if m_url: self.main_url = m_url.group(1)
            
            # SwKey
            s_key = re.search(r'private\s+(val|var)\s+swKey\s*=\s*"([^"]+)"', content)
            if s_key: self.sw_key = s_key.group(2)
            
            # User Agent (Varsa günceller)
            ua = re.search(r'headers\s*=\s*mapOf\([^)]*"user-agent"[^)]*to[^"]*"([^"]+)"', content, re.IGNORECASE)
            if ua: self.headers['User-Agent'] = ua.group(1)

            # Referer (Varsa günceller)
            ref = re.search(r'headers\s*=\s*mapOf\([^)]*"Referer"[^)]*to[^"]*"([^"]+)"', content, re.IGNORECASE)
            if ref: self.headers['Referer'] = ref.group(1)
            
            self.log(f"Config Güncellendi: URL={self.main_url} | KEY=...{self.sw_key[-10:]}")
            return True
        return False

    def find_working_domain(self):
        """Domain kontrolü (İlk koddan alındı)"""
        if self.test_domain(self.main_url):
            self.log(f"GitHub domaini çalışıyor: {self.main_url}")
            return

        self.log("GitHub domaini yanıt vermedi. Alternatifler taranıyor...")
        for i in range(65, 0, -1):
            domain = f"https://m.prectv{i}.lol"
            if self.test_domain(domain):
                self.main_url = domain
                self.log(f"Çalışan domain bulundu: {domain}")
                return
        self.log("UYARI: Varsayılan domain ile devam ediliyor.")

    def test_domain(self, url):
        try:
            # Basit bir test isteği
            test_url = f"{url}/api/serie/by/filtres/0/created/0/{self.sw_key}"
            r = requests.get(test_url, headers=self.headers, timeout=5, verify=False)
            return r.status_code == 200
        except:
            return False

    def fetch_episode_details(self, serie_item):
        """Tek bir dizinin detaylarına iner (Sezon -> Bölüm -> M3U8)"""
        serie_id = serie_item.get('id')
        title = serie_item.get('title', 'Bilinmeyen Dizi')
        image = serie_item.get('image', '')
        if image and not image.startswith('http'):
            image = urljoin(self.main_url, image)
            
        local_entries = []
        
        # Sezon API İsteği
        url = f"{self.main_url}/api/season/by/serie/{serie_id}/{self.sw_key}"
        try:
            r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
            if r.status_code != 200: return []
            seasons = r.json()
        except:
            return []

        if not seasons or not isinstance(seasons, list): return []

        for season in seasons:
            season_name = season.get('title', 'Sezon')
            episodes = season.get('episodes', [])
            
            for ep in episodes:
                ep_title = ep.get('title', 'Bölüm')
                
                # Kaynakları bul
                for source in ep.get('sources', []):
                    src_url = source.get('url')
                    if src_url and "m3u8" in src_url:
                        # URL Manipülasyonu yok, direkt ham URL
                        final_url = src_url
                        
                        full_title = f"{title} - {season_name} - {ep_title}"
                        quality = source.get('quality', '')
                        if quality: full_title += f" [{quality}]"

                        entry = (
                            f'#EXTINF:-1 tvg-id="{serie_id}" tvg-name="{full_title}" tvg-logo="{image}" group-title="{title}", {full_title}\n'
                            f'#EXTVLCOPT:http-user-agent={self.headers["User-Agent"]}\n'
                            f'#EXTVLCOPT:http-referrer={self.headers["Referer"]}\n'
                            f'{final_url}'
                        )
                        local_entries.append(entry)
        
        return local_entries

    def run(self):
        # 1. Config ve Domain Hazırlığı
        if not self.fetch_github_config():
            self.log("Config alınamadı, varsayılanlar kullanılıyor.")
        self.find_working_domain()

        self.log("Dizi taraması başlıyor...")
        
        page = 0
        empty_streak = 0

        while True:
            # Dizi Listesi API'si
            url = f"{self.main_url}/api/serie/by/filtres/0/created/{page}/{self.sw_key}"
            self.log(f"Sayfa {page} taranıyor...")
            
            try:
                r = requests.get(url, headers=self.headers, timeout=TIMEOUT, verify=False)
                if r.status_code != 200:
                    break # Hata varsa veya bittiyse çık
                
                series_list = r.json()
                if not series_list or not isinstance(series_list, list):
                    # Liste boşsa veya format bozuksa
                    empty_streak += 1
                    if empty_streak >= 2: # 2 boş sayfa gelirse tamamen dur
                        self.log("Tarama tamamlandı (İçerik bitti).")
                        break
                    page += 1
                    continue
                else:
                    empty_streak = 0

                # Bu sayfadaki dizileri PARALEL işle (Hızlandırma burada)
                # Sayfa içindeki 20 dizinin detaylarını aynı anda çekecek
                with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    # fetch_episode_details fonksiyonuna her bir diziyi gönderiyoruz
                    future_to_serie = {executor.submit(self.fetch_episode_details, s): s for s in series_list}
                    
                    for future in concurrent.futures.as_completed(future_to_serie):
                        try:
                            entries = future.result()
                            if entries:
                                self.series_buffer.extend(entries)
                                self.total_episodes += len(entries)
                        except Exception as e:
                            self.log(f"Dizi detay hatası: {e}")

                self.log(f"Sayfa {page} tamamlandı. Toplam Bölüm: {self.total_episodes}")
                page += 1
                
            except Exception as e:
                self.log(f"Genel Hata (Sayfa {page}): {e}")
                break

        # Dosyayı Kaydet
        with open(FILE_SERIES, 'w', encoding='utf-8') as f:
            f.write('\n'.join(self.series_buffer))
        
        self.log("="*30)
        self.log(f"İŞLEM BİTTİ.")
        self.log(f"Toplam Bölüm Sayısı: {self.total_episodes}")
        self.log(f"Kaydedilen Dosya: {FILE_SERIES}")
        self.log("="*30)

if __name__ == "__main__":
    requests.packages.urllib3.disable_warnings()
    scraper = RecTVScraper()
    scraper.run()
