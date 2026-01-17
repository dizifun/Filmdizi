import cloudscraper
import json
import os
import time

DB_DOSYA = "veritabani.json"
scraper = cloudscraper.create_scraper(browser={'browser': 'chrome','platform': 'windows','desktop': True})

def db_yukle():
    if os.path.exists(DB_DOSYA):
        with open(DB_DOSYA, "r", encoding="utf-8") as f: return json.load(f)
    return []

def db_kaydet(veri):
    with open(DB_DOSYA, "w", encoding="utf-8") as f: json.dump(veri, f, ensure_ascii=False, indent=4)

def altyazi_bul(video_url):
    base_url = video_url.rsplit('/', 1)[0] + "/"
    # En yaygın ihtimalleri deneyelim
    denemeler = ["subtitle-tur-1.vtt", "subtitle-tur.vtt", "subtitle-und-1.vtt", "subtitle-1.vtt"]
    
    for aday in denemeler:
        try:
            test_url = base_url + aday
            res = scraper.head(test_url, timeout=3)
            if res.status_code == 200: return test_url
        except: continue
    return "YOK"

def baslat():
    veriler = db_yukle()
    toplam = len(veriler)
    print(f"🕵️ TOPLAM {toplam} FİLM İÇİN ALTYAZI TARAMASI BAŞLADI...")

    for i, film in enumerate(veriler):
        # Eğer altyazi yoksa veya taranmamışsa (None, "", "YOK" olmayanlar)
        if not film.get("altyazi") or film.get("altyazi") == "":
            print(f"🔍 [{i+1}/{toplam}] {film['baslik']} taranıyor...")
            sonuc = altyazi_bul(film["video_url"])
            film["altyazi"] = sonuc
            
            if sonuc != "YOK":
                print(f"   ✅ BULDUM: {sonuc}")
                db_kaydet(veriler) # Her bulduğunda kaydet ki veriler garanti olsun
            
            time.sleep(0.1)

    db_kaydet(veriler)
    print("🏁 TARAMA TAMAMLANDI.")

if __name__ == "__main__":
    baslat()

