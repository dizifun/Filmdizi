import json

DB_DOSYA = "veritabani.json"
M3U_DOSYA = "playlist.m3u"

def baslat():
    try:
        with open(DB_DOSYA, "r", encoding="utf-8") as f: veriler = json.load(f)
    except: veriler = []
        
    with open(M3U_DOSYA, "w", encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        
        for film in veriler:
            if not film.get('video_url'): continue
            sub_tag = f' subtitle="{film["altyazi"]}"' if film.get('altyazi') and film['altyazi'] != "YOK" else ""
            
            satir = f'#EXTINF:-1 tvg-logo="{film["poster"]}" group-title="{film["kategori"]}"{sub_tag},{film["baslik"]}\n{film["video_url"]}\n'
            f.write(satir)
            
    print(f"✅ {len(veriler)} film playlist.m3u dosyasına yazıldı!")

if __name__ == "__main__":
    baslat()

