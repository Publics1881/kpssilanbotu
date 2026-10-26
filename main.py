import requests

url = "https://www.ilan.gov.tr/api/api/services/app/Ad/AdsByFilter"

veriler = {
    "keys": {"txv": [8]},
    "skipCount": 0,
    "maxResultCount": 12
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
    "Content-Type": "application/json",
    "Origin": "https://www.ilan.gov.tr",
    "Referer": "https://www.ilan.gov.tr/"
}

try:
    cevap = requests.post(
        url,
        json=veriler,
        headers=headers,
        timeout=30
    )

    print("HTTP DURUMU:", cevap.status_code)

    if cevap.status_code == 200:
        sonuc = cevap.json()

        if sonuc.get("success"):
            ilanlar = sonuc.get("result", {}).get("ads", [])

            print("BULUNAN İLAN SAYISI:", len(ilanlar))

            for ilan in ilanlar:
                print("İLAN:", ilan.get("title"))
        else:
            print("API HATASI:", sonuc.get("error"))
    else:
        print("HATA:", cevap.text[:500])

except Exception as hata:
    print("BAĞLANTI HATASI:", hata)
