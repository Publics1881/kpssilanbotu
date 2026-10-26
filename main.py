import os
import re
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

HEDEF_KELIMELER = [
    "3001",
    "dış ticaret",
    "ön lisans",
    "önlisans",
    "6225",
    "bilgisayar işletmenliği",
    "bilgisayar sertifikası",
    "büro personeli",
    "büro memuru",
    "veri hazırlama",
    "veri kontrol",
    "vhki",
    "zabıt katibi",
    "zabıt kâtibi",
    "icra katibi",
    "icra kâtibi",
    "mübaşir",
    "memur alımı",
    "personel alımı",
    "destek personeli",
    "büro görevlisi",
]

KADRO_KELIMELERI = [
    "zabıt katibi",
    "zabıt kâtibi",
    "icra katibi",
    "icra kâtibi",
    "mübaşir",
    "büro personeli",
    "büro memuru",
    "veri hazırlama",
    "veri kontrol",
    "vhki",
    "dış ticaret",
    "3001",
    "6225",
    "ön lisans",
    "önlisans",
    "bilgisayar işletmenliği",
    "bilgisayar sertifikası",
    "memur alımı",
    "personel alımı",
    "destek personeli",
    "büro görevlisi",
]

HARIC_KELIMELER = [
    "sınav sonuçları",
    "sözlü sınav sonuçları",
    "başvuru sonuçları",
    "yerleştirme sonuçları",
    "yedek aday duyurusu",
    "sınav metinleri",
    "değerlendirme kriterleri",
    "görevde yükselme sınavı",
    "sınav sonuçlarına ilişkin",
]

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

DOSYA = "gonderilen_ilanlar.txt"

OTURUM = requests.Session()
OTURUM.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
})


def duzelt(metin):
    return re.sub(r"\s+", " ", metin or "").casefold().strip()


def gonderilenleri_oku():
    if not os.path.exists(DOSYA):
        return set()

    with open(DOSYA, "r", encoding="utf-8") as dosya:
        return set(s.strip() for s in dosya if s.strip())


GONDERILENLER = gonderilenleri_oku()


def kaydet(link):
    GONDERILENLER.add(link)
    with open(DOSYA, "a", encoding="utf-8") as dosya:
        dosya.write(link + "\n")


def telegram_gonder(mesaj):
    if not TOKEN or not CHAT_ID:
        print("HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik.")
        return False

    adres = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    try:
        cevap = OTURUM.post(
            adres,
            data={
                "chat_id": CHAT_ID,
                "text": mesaj,
                "disable_web_page_preview": True,
            },
            timeout=25,
        )

        sonuc = cevap.json()

        if not cevap.ok or not sonuc.get("ok"):
            print("Telegram gönderim hatası:", sonuc)
            return False

        return True

    except (requests.RequestException, ValueError) as hata:
        print("Telegram bağlantı hatası:", hata)
        return False


def sayfa_oku(adres):
    try:
        cevap = OTURUM.get(adres, timeout=25)
        cevap.raise_for_status()

        soup = BeautifulSoup(cevap.text, "html.parser")

        for etiket in soup([
            "script", "style", "nav", "footer", "header",
            "noscript", "svg"
        ]):
            etiket.decompose()

        baslik = soup.title.get_text(" ", strip=True) if soup.title else ""
        icerik = soup.get_text(" ", strip=True)

        return soup, baslik, icerik

    except requests.RequestException as hata:
        print(f"Sayfa okunamadı: {adres} | {hata}")
        return None, "", ""


def haric_mi(baslik):
    baslik = duzelt(baslik)
    return any(kelime in baslik for kelime in HARIC_KELIMELER)


def hedef_baslik_mi(baslik):
    baslik = duzelt(baslik)

    if not baslik or haric_mi(baslik):
        return False

    return any(kelime in baslik for kelime in KADRO_KELIMELERI)


def icerik_eslesmeleri(icerik):
    metin = duzelt(icerik)
    return [
        kelime for kelime in HEDEF_KELIMELER
        if kelime in metin
    ]


def tara(isim, adres):
    print(f"\n--- {isim} taranıyor ---")

    ana_host = urlparse(adres).netloc
    soup, _, _ = sayfa_oku(adres)

    if soup is None:
        return

    yeni_aday = 0
    incelenen = 0

    for a in soup.find_all("a", href=True):
        baslik = a.get_text(" ", strip=True)
        link = urljoin(adres, a["href"]).split("#")[0]

        if not baslik or not hedef_baslik_mi(baslik):
            continue

        if urlparse(link).netloc != ana_host:
            continue

        if link in GONDERILENLER:
            continue

        if link == adres:
            continue

        incelenen += 1

        if incelenen > 40:
            break

        _, sayfa_basligi, icerik = sayfa_oku(link)

        if not icerik:
            print(f"İçerik okunamadı: {baslik}")
            continue

        # İlan sayfasında hedeflenen kadro veya nitelik bulunmalı.
        eslesmeler = icerik_eslesmeleri(
            baslik + " " + sayfa_basligi + " " + icerik
        )

        if not eslesmeler:
            print(f"Filtrelendi: {baslik}")
            continue

        # Eski ilanları ve sonuç duyurularını mümkün olduğunca ele.
        if haric_mi(baslik) or haric_mi(sayfa_basligi):
            print(f"Sonuç/duyuru olduğu için elendi: {baslik}")
            continue

        mesaj = (
            "📢 KAMU İLANI - FİLTREDEN GEÇTİ\n\n"
            f"Kaynak: {isim}\n"
            f"Başlık: {baslik}\n"
            f"Bağlantı: {link}\n\n"
            f"Eşleşen ifadeler: {', '.join(eslesmeler[:8])}\n\n"
            "⚠️ Bu bir ilan adayıdır; kesin uygunluk değildir. "
            "Mezuniyet şartını, nitelik kodlarını, KPSS puanını, "
            "sertifika şartlarını, yaş koşullarını ve başvuru "
            "tarihini resmî ilandan kontrol et."
        )

        print(f"İlan adayı: {baslik}")

        if telegram_gonder(mesaj):
            kaydet(link)
            yeni_aday += 1

    print(f"{isim}: {yeni_aday} yeni ilan adayı gönderildi.")


def main():
    if not TOKEN or not CHAT_ID:
        print(
            "HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik. "
            "GitHub Actions Secret aktarımını kontrol et."
        )
        return

    for isim, adres in SITELER.items():
        try:
            tara(isim, adres)
        except Exception as hata:
            print(f"{isim} tarama hatası: {hata}")


if __name__ == "__main__":
    main()
