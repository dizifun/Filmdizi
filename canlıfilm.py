#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import urllib3
import json
import re
import concurrent.futures
import time
from urllib.parse import urljoin

# SSL Uyarılarını Gizle
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== AYARLAR ====================
GITHUB_SOURCE_URL = 'https://raw.githubusercontent.com/nikyokki/nik-cloudstream/refs/heads/master/RecTV/src/main/kotlin/com/keyiflerolsun/RecTV.kt'
PROXY_URL = 'https://api.codetabs.com/v1/proxy/?quest=' + requests.utils.quote(GITHUB_SOURCE_URL)

M3U_USER_AGENT = 'googleusercontent'
TIMEOUT = 15
MAX_WORKERS = 10
MAX_RETRIES = 3 # Hata anında kaç kere tekrar deneyeceği

FILE_LIVE = 'canli.m3u'
FILE_MOVIES = 'filmler.m3u'

class RecTVMasterScraper:
    def __init__(self):
        # Header'lar (Filmler için VOD header ayrı tutuluyor)
        self.headers_default = {
            'User-Agent': 'okhttp/4.12.0',
            'Referer': 'https://twitter.com/'
        }
        self.headers_vod = {
            'User-Agent': 'Dart/3.7 (dart:io)',
            'Referer': 'https://twitter.com/'
        }
        
        self.main_url = "https://m.prectv60.lol" 
        self.sw_key = "4F5A9C3D9A86FA54EACEDDD635185/c3c5bd17-e37b-4b94-a944-8a3688a30452/"
        
        self.found_items = {"live": 0, "movies": 0}
        self.buffer_live = ["#EXTM3U"]
        self.buffer_movies = ["#EXTM3U"]

    def log(self, message):
        print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def request_with_retry(self, url, headers):
        """Hata durumunda hemen pes etmeyen, tekrar deneyen istek motoru"""
        for i in range(MAX_RETRIES):
            try:
                r = requests.get(url, headers=headers, timeout=TIMEOUT, verify=False)
                if r.status_code == 200:
                    return r
                elif r.status_code == 404:
                    return None
                else:
                    time.sleep(1) 
            except requests.exceptions.RequestException:
                time.sleep(1)
                continue
        return None

    def fetch_github_config(self):
        """GitHub'dan en güncel ayarları akıllıca parse eder"""
        self.log("GitHub'dan yapılandırma çekiliyor...")
        content = None
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        try:
            r = requests.get(GITHUB_SOURCE_URL, headers=headers, timeout=10, verify=False)
            if r.status_code == 200: content = r.text
        except: pass

        if not content:
            try:
                r = requests.get(PROXY_URL, headers=headers, timeout=10, verify=False)
                if r.status_code == 200: content = r.text
            except: pass

        if content:
            # Main URL
            m_url = re.search(r'override\s+var\s+mainUrl\s*=\s*"([^"]+)"', content)
            if m_url: self.main_url = m_url.group(1)

            # SwKey
            s_key = re.search(r'private\s+(val|var)\s+swKey\s*=\s*"([^"]+)"', content)
            if s_key: self.sw_key = s_key.group(2)

            # User Agent
            ua = re.search(r'headers\s*=\s*mapOf\([^)]*"user-agent"[^)]*to[^"]*"([^"]+)"', content, re.IGNORECASE | re.DOTALL)
            if ua: self.headers_default['User-Agent'] = ua.group(1)

            # Referer
            ref = re.search(r'headers\s*=\s*mapOf\([^)]*"Referer"[^)]*to[^"]*"([^"]+)"', content, re.IGNORECASE | re.DOTALL)
            if ref: self.headers_default['Referer'] = ref.group(1)

            self.log(f"Config Güncellendi: URL={self.main_url} | KEY=...{self.sw_key[-10:]}")
            return True
        return False

    def test_domain(self, url):
        """Domain'in ve API'nin gerçekten çalışıp çalışmadığını test eder"""
        try:
            test_url = f"{url}/api/channel/by/filtres/0/0/0/{self.sw_key}"
            r = requests.get(test_url, headers=self.headers_default, timeout=5, verify=False)
            
            if r.status_code == 200 and isinstance(r.json(), list):
                return True
            else:
                self.log(f"Test Başarısız ({url}): HTTP {r.status_code}")
                return False
        except Exception as e:
            return False

    def find_working_domain(self):
        """Mevcut adres çalışmıyorsa uzantıyı algılayıp 80'den geriye tarar"""
        if self.test_domain(self.main_url):
            self.log(f"✓ API Testi Başarılı: {self.main_url}")
            return

        self.log("✗ Mevcut domain yanıt vermedi. Tarama başlatılıyor...")
        
        # Dinamik uzantı tespiti (örn: .sbs, .lol, .tv)
        try:
            base_ext = self.main_url.split('.')[-1]
        except:
            base_ext = "sbs"

        for i in range(80, 0, -1):
            domain = f"https://m.prectv{i}.{base_ext}"
            if self.test_domain(domain):
                self.main_url = domain
                self.log(f"✓ Çalışan yeni domain bulundu: {domain}")
                return

        self.log("UYARI: Hiçbir domain çalışmıyor olabilir. Yine de devam ediliyor...")

    def process_content(self, items, content_type, category_name):
        """Gelen veriyi ayrıştırıp M3U formatına çevirir"""
        count = 0
        current_headers = self.headers_default if content_type == "live" else self.headers_vod

        for item in items:
            if 'sources' not in item: continue

            for source in item['sources']:
                # Hem m3u8 hem de mp4 formatlarını kabul et
                if (source.get('type') == 'm3u8' or source.get('type') == 'mp4') and source.get('url'):
                    title = item.get('title', 'Bilinmeyen')
                    image = item.get('image', '')
                    if image and not image.startswith('http'):
                        image = urljoin(self.main_url + '/', image.lstrip('/'))

                    tid = item.get('id', '')

                    # Filmler için kategori / dil belirteci
                    if content_type == "movies":
                        cat_str = "".join([c.get('title', '').lower() for c in item.get('categories', [])])
                        if "dublaj" in title.lower() or "tr" in title.lower() or "türkçe" in cat_str:
                            title += " [TR Dublaj]"
                        elif "altyazı" in title.lower() or "al tyazı" in title.lower():
                            title += " [Altyazılı]"

                    # M3U Satırları
                    entry = f'#EXTINF:-1 tvg-id="{tid}" tvg-name="{title}" tvg-logo="{image}" group-title="{category_name}", {title}'
                    entry += f'\n#EXTVLCOPT:http-user-agent={M3U_USER_AGENT}'
                    entry += f'\n#EXTVLCOPT:http-referrer={current_headers["Referer"]}'
                    entry += f'\n{source["url"]}'

                    if content_type == "live":
                        self.buffer_live.append(entry)
                        self.found_items["live"] += 1
                    elif content_type == "movies":
                        self.buffer_movies.append(entry)
                        self.found_items["movies"] += 1

                    count += 1
        return count

    def scrape_category(self, api_template, category_name, content_type, start_page=0):
        """Bir kategoriyi boş sayfa gelene kadar tarar"""
        page = start_page
        empty_streak = 0
        current_headers = self.headers_default if content_type == "live" else self.headers_vod

        while True:
            url = f"{self.main_url}/{api_template.replace('SAYFA', str(page))}{self.sw_key}"
            
            r = self.request_with_retry(url, current_headers)

            if not r: 
                empty_streak += 1
                if empty_streak >= 3: break # 3 kere boş gelirse o kategoriyi bitir
                page += 1
                continue

            try:
                data = r.json()
                if not data or not isinstance(data, list):
                    empty_streak += 1
                else:
                    count = self.process_content(data, content_type, category_name)
                    if count == 0:
                        empty_streak += 1
                    else:
                        empty_streak = 0 # Veri geldiyse sayacı sıfırla

                if empty_streak >= 3: break
                page += 1

            except Exception as e:
                empty_streak += 1
                if empty_streak >= 3: break

    def run(self):
        print("\n" + "="*40)
        self.log("RecTV Master Scraper Başlatılıyor...")
        print("="*40)

        # 1. Config Çek ve Test Et
        self.fetch_github_config()
        self.find_working_domain()

        # 2. Tarama Görevleri Listesi
        tasks = [
            ("api/channel/by/filtres/0/0/SAYFA/", "Canlı TV", "live"),
            ("api/movie/by/filtres/0/created/SAYFA/", "Son Eklenen Filmler", "movies"),
            ("api/movie/by/filtres/14/created/SAYFA/", "Aile", "movies"),
            ("api/movie/by/filtres/1/created/SAYFA/", "Aksiyon", "movies"),
            ("api/movie/by/filtres/13/created/SAYFA/", "Animasyon", "movies"),
            ("api/movie/by/filtres/19/created/SAYFA/", "Belgesel", "movies"),
            ("api/movie/by/filtres/4/created/SAYFA/", "Bilim Kurgu", "movies"),
            ("api/movie/by/filtres/2/created/SAYFA/", "Dram", "movies"),
            ("api/movie/by/filtres/10/created/SAYFA/", "Fantastik", "movies"),
            ("api/movie/by/filtres/3/created/SAYFA/", "Komedi", "movies"),
            ("api/movie/by/filtres/8/created/SAYFA/", "Korku", "movies"),
            ("api/movie/by/filtres/17/created/SAYFA/", "Macera", "movies"),
            ("api/movie/by/filtres/5/created/SAYFA/", "Romantik", "movies"),
            ("api/movie/by/filtres/15/created/SAYFA/", "Suç", "movies"),
            ("api/movie/by/filtres/6/created/SAYFA/", "Gerilim", "movies"),
            ("api/movie/by/filtres/23/created/SAYFA/", "Yerli Filmler", "movies"),
        ]

        self.log("Çoklu Tarama başlıyor... (Canlı TV ve Filmler)")

        # 3. İş Parçacıkları (Thread) ile Hızlı Tarama
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_url = {
                executor.submit(self.scrape_category, t[0], t[1], t[2]): t 
                for t in tasks
            }

            for future in concurrent.futures.as_completed(future_to_url):
                task = future_to_url[future]
                try:
                    future.result()
                    self.log(f"✓ Tamamlandı: {task[1]}")
                except Exception as exc:
                    self.log(f"✗ Hata - {task[1]}: {exc}")

        # 4. Dosyaları Kaydet
        self.save_file(FILE_LIVE, self.buffer_live)
        self.save_file(FILE_MOVIES, self.buffer_movies)

        print("\n" + "="*40)
        self.log(f"İŞLEM BİTTİ - TOPLAM BULUNAN:")
        self.log(f"📺 Canlı TV : {self.found_items['live']} kanal")
        self.log(f"🎬 Filmler  : {self.found_items['movies']} film")
        print("="*40 + "\n")

    def save_file(self, filename, content_list):
        with open(filename, 'w', encoding='utf-8') as f:
            f.write('\n'.join(content_list))
        self.log(f"💾 Dosya kaydedildi: {filename}")

if __name__ == "__main__":
    scraper = RecTVMasterScraper()
    scraper.run()
