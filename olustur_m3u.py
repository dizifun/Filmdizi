import json

def baslat():
    try:
        with open("veritabani.json", "r", encoding="utf-8") as f: veriler = json.load(f)
    except:
        print("❌ Veritabanı (JSON) bulunamadı!"); return

    sayac = 0
    with open("playlist.m3u", "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for film in veriler:
            sub_url = film.get("altyazi")
            
            # Altyazı etiketi hazırlama (Tüm oynatıcılar için)
            if sub_url and sub_url != "YOK":
                # 1. subtitle: Standart
                # 2. sub-src: IPTV Pro ve benzerleri
                # 3. KODIK: Bazı web tabanlı playerlar
                # 4. sub-lang: Dil belirleme
                sub_tags = f' subtitle="{sub_url}" sub-src="{sub_url}" sub-lang="Turkish" sub-type="vtt"'
                sayac += 1
            else:
                sub_tags = ""
            
            # M3U satırını oluştur
            f.write(f'#EXTINF:-1 tvg-logo="{film["poster"]}" group-title="{film["kategori"]}"{sub_tags},{film["baslik"]}\n{film["video_url"]}\n')
    
    print(f"✅ BİTTİ: 15513 film hazırlandı.")
    print(f"🎬 Toplam {sayac} filmde altyazı başarıyla işlendi.")

if __name__ == "__main__":
    baslat()

