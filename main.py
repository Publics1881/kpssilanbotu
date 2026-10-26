import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SITELER = {
    "Kariyer Kapısı": "https://kariyerkapisi.gov.tr/",
    "İŞKUR": "https://www.iskur.gov.tr/",
    "Adalet Bakanlığı": "https://pgm.adalet.gov.tr/Home/TumHaberler/1",
    "YÖK": "https://www.yok.gov.tr/",
    "ÖSYM": "https://www.osym.gov.tr/",
    "Resmî Gazete": "https://www.resmigazete.gov.tr/",
}

ANAHTARLAR = [
    "3001", "dış ticaret", "ön lisans", "önlisans",
    "bilgisayar işletmenliği", "6225", "sertifika",
    "veri hazırlama", "veri kontrol", "vhki",
    "mübaşir", "zabıt katibi", "zabıt kâtibi",
    "icra katibi", "icra kâtibi", "cezaevi katibi",
    "cezaevi kâtibi", "ceza infaz", "öğrenci işleri",
    "büro personeli", "büro memuru", "düz memur",
    "memur alımı", "personel alımı"
]

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
DOSYA = "gonderilen_ilanlar.txt"

def gonderildi_mi(link):
    if not os.path.exists(DOSYA):
        return False
    with open(DOSYA, "r", encoding="utf-8") as f:
        return link in f.read().splitlines()

def kaydet(link):
    with open(DOSYA, "a", encoding="utf-8") as f:
        f.write(link + "\n")

def telegram_gonder(mesaj):
    if not TOKEN or not CHAT_ID:
        print("HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik.")
        return False

    api = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        r = requests.post(
            api,
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True
            },
            timeout=20
        )
        r.raise_for_status()
        sonuc = r.json()
        if not sonuc.get("ok"):
            print("Telegram hatası:", sonuc)
            return False
        return True
    except requests.RequestException as hata:
        print("Telegram gönderim hatası:", hata)
        return False

def tara(isim, adres):
    print(f"\n--- {isim} taranıyor ---")

    try:
        r = requests.get(
            adres,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=30
        )
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except requests.RequestException as hata:
        print(f"Erişim hatası: {hata}")
        return

    adet = 0
    ana_host = urlparse(adres).netloc

    for a in soup.find_all("a", href=True):
        baslik = a.get_text(" ", strip=True)
        link = urljoin(adres, a["href"])

        if not baslik or urlparse(link).netloc != ana_host:
            continue

        if not any(k.casefold() in baslik.casefold() for k in ANAHTARLAR):
            continue

        if gonderildi_mi(link):
            continue

        mesaj = (
            f"📢 KAMU PERSONEL İLANI\n\n"
            f"Kaynak: {isim}\n"
            f"Başlık: {baslik}\n"
            f"Bağlantı: {link}\n\n"
            "Kontrol edilecekler: ön lisans, Dış Ticaret, "
            "3001, bilgisayar sertifikası ve ilanın diğer şartları.\n"
            "Not: Uygunluk henüz doğrulanmadı."
        )

        print(f"İlan adayı: {baslik} | {link}")

        if telegram_gonder(mesaj):
            kaydet(link)
            adet += 1

    print(f"{isim}: {adet} yeni bağlantı gönderildi.")

def main():
    for isim, adres in SITELER.items():
        tara(isim, adres)

if __name__ == "__main__":
    main()
