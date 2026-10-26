import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

SITELER = {
    "Adalet Bakanlığı": "https://pgm.adalet.gov.tr/Home/TumHaberler/1",
    "Kariyer Kapısı": "https://kariyerkapisi.gov.tr/",
    "İŞKUR": "https://www.iskur.gov.tr/",
    "YÖK": "https://www.yok.gov.tr/",
    "ÖSYM": "https://www.osym.gov.tr/",
    "Resmî Gazete": "https://www.resmigazete.gov.tr/",
}

HEDEF_KADROLAR = [
    "zabıt katibi",
    "zabıt kâtibi",
    "icra katibi",
    "icra kâtibi",
    "veri hazırlama kontrol işletmeni",
    "cezaevi kâtibi",
    "cezaevi katibi",
    "mübaşir",
    "vhki",
    "veri hazırlama",
    "veri kontrol",
    "büro personeli",
    "büro görevlisi",
    "öğrenci işleri",
    "bilgisayar işletmeni",
    "bilgisayar işletmenliği",
    "bilgisayar sertifikası",
]

HARIC_BASLIKLAR = [
    "sınav sonuçları",
    "başvuru sonuçları",
    "yerleştirme sonuçları",
    "sözlü sınav sonuçları",
    "uygulama sınav metinleri",
    "uygulamalı sınav metinleri",
    "değerlendirme kriterleri",
    "görevde yükselme sınavı",
    "yedek aday",
]

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
DOSYA = "gonderilen_ilanlar.txt"

OTURUM = requests.Session()
OTURUM.headers.update({"User-Agent": "Mozilla/5.0"})


def norm(metin):
    metin = (metin or "").casefold().replace("ı", "i")
    return re.sub(r"\s+", " ", metin).strip()


def oku(url):
    try:
        r = OTURUM.get(url, timeout=25)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        for etiket in soup(
            ["script", "style", "nav", "footer", "header", "noscript"]
        ):
            etiket.decompose()

        baslik = soup.title.get_text(" ", strip=True) if soup.title else ""
        icerik = soup.get_text(" ", strip=True)
        return soup, baslik, icerik
    except requests.RequestException as e:
        print("Sayfa okunamadı:", url, e)
        return None, "", ""


def hedefler(metin):
    metin = norm(metin)
    return [k for k in HEDEF_KADROLAR if norm(k) in metin]


def haric_mi(baslik):
    baslik = norm(baslik)
    return any(norm(k) in baslik for k in HARIC_BASLIKLAR)


def gonder(mesaj):
    if not TOKEN or not CHAT_ID:
        print("HATA: Telegram Secret eksik.")
        return False

    try:
        r = OTURUM.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True,
            },
            timeout=25,
        )
        sonuc = r.json()
        if not r.ok or not sonuc.get("ok"):
            print("Telegram hatası:", sonuc)
            return False
        return True
    except (requests.RequestException, ValueError) as e:
        print("Telegram hatası:", e)
        return False


def tara(kaynak, adres):
    print(f"\n--- {kaynak} taranıyor ---")
    ana_host = urlparse(adres).netloc
    soup, _, _ = oku(adres)

    if soup is None:
        return

    gonderilen = set()
    if os.path.exists(DOSYA):
        with open(DOSYA, "r", encoding="utf-8") as f:
            gonderilen = {x.strip() for x in f if x.strip()}

    sayac = 0

    for a in soup.find_all("a", href=True):
        baslik = a.get_text(" ", strip=True)
        link = urljoin(adres, a["href"]).split("#")[0]

        if not baslik or urlparse(link).netloc != ana_host:
            continue
        if link == adres or link in gonderilen:
            continue
        if haric_mi(baslik):
            continue

        eslesme = hedefler(baslik)
        if not eslesme:
            continue

        _, sayfa_basligi, icerik = oku(link)
        if not icerik:
            continue
        if haric_mi(baslik + " " + sayfa_basligi):
            continue

        # Test amacıyla tarih kontrolü uygulanmıyor.
        mesaj = (
            "📢 KAMU İLANI - TEST\n\n"
            f"Kaynak: {kaynak}\n"
            f"Başlık: {baslik}\n"
            f"Eşleşen ifadeler: {', '.join(eslesme)}\n"
            f"Bağlantı: {link}\n\n"
            "⚠️ Test sürümü: Tarih ve başvuru uygunluğu doğrulanmadı."
        )

        if gonder(mesaj):
            with open(DOSYA, "a", encoding="utf-8") as f:
                f.write(link + "\n")
            gonderilen.add(link)
            sayac += 1

    print(f"{kaynak}: {sayac} ilan gönderildi.")


def main():
    if not TOKEN or not CHAT_ID:
        print("HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik.")
        return

    for kaynak, adres in SITELER.items():
        try:
            tara(kaynak, adres)
        except Exception as e:
            print(f"{kaynak} hatası:", e)


if __name__ == "__main__":
    main()
