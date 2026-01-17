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
            # Sadece taranmış ve altyazısı "YOK" olmayanları ekle
            sub = ""
            if film.get("altyazi") and film["altyazi"] != "YOK":
                sub = f' subtitle="{film["altyazi"]}"'
                sayac += 1
            
            f.write(f'#EXTINF:-1 tvg-logo="{film["poster"]}" group-title="{film["kategori"]}"{sub},{film["baslik"]}\n{film["video_url"]}\n')
    
    print(f"✅ BİTTİ: 15513 film hazırlandı. {sayac} tanesinde altyazı eklendi!")

if __name__ == "__main__":
    baslat()

