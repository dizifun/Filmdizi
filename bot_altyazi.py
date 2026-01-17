import requests
import json
import time

DB_DOSYA = "veritabani.json"

def db_yukle():
    with open(DB_DOSYA, "r", encoding="utf-8") as f: return json.load(f)

def db_kaydet(veri):
    with open(DB_DOSYA, "w", encoding="utf-8") as f: json.dump(veri, f, ensure_ascii=False, indent=4)

def altyazi_ara(m3u8_link):
    base_url = m3u8_link.rsplit('/', 1)[0] + "/"
    diller = ["tur", "eng", "und", "tr", "en"]
    bulunanlar = []
    
    for dil in diller:
        adaylar = [f"subtitle-{dil}.vtt"] + [f"subtitle-{dil}-{i}.vtt" for i in range(1, 8)]
        if dil == "tur": adaylar.append("subtitle.vtt")
        
        for aday in adaylar:
            try:
                r = requests.head(base_url + aday, timeout=1)
                if r.status_code == 200: bulunanlar.append(base_url + aday)
            except: pass
    return bulunanlar if bulunanlar else None

def baslat():
    veriler = db_yukle()
    taranacak = [v for v in veriler if v['altyazi'] is None]
    
    print(f"🕵️ ALTYAZI DEDEKTİFİ: {len(taranacak)} film kontrol edilecek...")
    
    for i, film in enumerate(veriler):
        if film['altyazi'] is not None: continue
        
        print(f"🔍 [{i+1}] Aranıyor: {film['baslik']}")
        altyazilar = altyazi_ara(film['video_url'])
        
        if altyazilar:
            film['altyazi'] = altyazilar[0]
            print(f"   🎉 BULUNDU: {len(altyazilar)} altyazı.")
            db_kaydet(veriler)
        else:
            film['altyazi'] = "YOK" # Yoksa işaretle, tekrar arama
            
    print("🏁 ALTYAZI TARAMASI BİTTİ.")

if __name__ == "__main__":
    baslat()

