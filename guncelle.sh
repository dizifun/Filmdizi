#!/bin/bash
git pull

# 1. Adım: Yeni filmleri çek (HIZLI)
python bot_icerik.py

# 2. Adım: Veritabanından M3U dosyasını oluştur
python olustur_m3u.py

# 3. Adım: GitHub'a gönder
git add .
git commit -m "Veritabani Guncellendi"
git push

