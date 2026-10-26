import requests

siteler = {
    "Kariyer Kapısı": "https://kariyerkapisi.gov.tr/",
    "İŞKUR": "https://www.iskur.gov.tr/",
    "Adalet Bakanlığı": "https://pgm.adalet.gov.tr/Home/TumHaberler/1",
    "YÖK": "https://www.yok.gov.tr/",
    "Resmî Gazete": "https://www.resmigazete.gov.tr/"
}

for isim, url in siteler.items():
    try:
        cevap = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30
        )
        print(f"{isim}: HTTP {cevap.status_code}")
    except requests.RequestException as hata:
        print(f"{isim}: BAĞLANTI HATASI - {hata}")
