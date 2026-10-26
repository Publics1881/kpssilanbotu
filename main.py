import requests

siteler = {
    "Kariyer Kapısı": "https://kariyerkapisi.gov.tr/",
    "İlan.gov.tr": "https://www.ilan.gov.tr/ilan-ara",
    "Kamu Personeli": "https://www.kamupersoneli.net/",
    "İŞKUR": "https://www.iskur.gov.tr/",
    "Resmî Gazete": "https://www.resmigazete.gov.tr/"
}

for isim, url in siteler.items():
    try:
        cevap = requests.get(url, timeout=20)
        print(f"{isim}: HTTP {cevap.status_code}")
    except requests.RequestException as hata:
        print(f"{isim}: BAĞLANTI HATASI - {hata}")
