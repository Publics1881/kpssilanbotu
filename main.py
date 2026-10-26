import os
import re
import requests
from datetime import datetime, date
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
    "sınav duyurusu",
    "sonuç duyurusu",
    "yedek aday",
]

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
DOSYA = "gonderilen_ilanlar.txt"

OTURUM = requests.Session()
OTURUM.headers.update({"User-Agent": "Mozilla/5.0"})


def normalize(metin):
    metin = (metin or "").casefold()
    metin = metin.replace("ı", "i")
    return re.sub(r"\s+", " ", metin).strip()


def sayfa_oku(url):
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

    except requests.RequestException as hata:
        print(f"Sayfa okunamadı: {url} | {hata}")
        return None, "", ""


def tarih_bul(metin):
    metin = metin or ""

    desenler = [
        r"\b(\d{1,2})[./-](\d{1,2})[./-](20\d{2})\b",
        r"\b(20\d{2})[./-](\d{1,2})[./-](\d{1,2})\b",
    ]

    bulunan = []

    for desen in desenler:
        for eslesme in re.finditer(desen, metin):
            try:
                parcalar = eslesme.groups()

                if desen == desenler[0]:
                    gun, ay, yil = map(int, parcalar)
                else:
                    yil, ay, gun = map(int, parcalar)

                bulunan.append(date(yil, ay, gun))
            except ValueError:
                continue

    aylar = {
        "ocak": 1, "şubat": 2, "subat": 2, "mart": 3,
        "nisan": 4, "mayıs": 5, "mayis": 5, "haziran": 6,
        "temmuz": 7, "ağustos": 8, "agustos": 8,
        "eylül": 9, "eylul": 9, "ekim": 10, "kasım": 11,
        "kasim": 11, "aralık": 12, "aralik": 12,
    }

    for eslesme in re.finditer(
        r"\b(\d{1,2})\s+([a-zçğıöşü]+)\s+(20\d{2})\b",
        normalize(metin),
    ):
        try:
            gun = int(eslesme.group(1))
            ay = aylar[eslesme.group(2)]
            yil = int(eslesme.group(3))
            bulunan.append(date(yil, ay, gun))
        except (ValueError, KeyError):
            continue

    return max(bulunan) if bulunan else None


def gonderilenleri_oku():
    if not os.path.exists(DOSYA):
        return set()

    with open(DOSYA, "r", encoding="utf-8") as f:
        return {satir.strip() for satir in f if satir.strip()}


GONDERILENLER = gonderilenleri_oku()


def kaydet(link):
    GONDERILENLER.add(link)
    with open(DOSYA, "a", encoding="utf-8") as f:
        f.write(link + "\n")


def telegram_gonder(mesaj):
    if not TOKEN or not CHAT_ID:
        print("HATA: Telegram Secret bilgileri eksik.")
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

    except (requests.RequestException, ValueError) as hata:
        print("Telegram hatası:", hata)
        return False


def tara(kaynak, adres):
    print(f"\n--- {kaynak} taranıyor ---")
    ana_host = urlparse(adres).netloc
    soup, _, _ = sayfa_oku(adres)

    if soup is None:
        return

    yeni = 0
    incelenen = 0

    for a in soup.find_all("a", href=True):
        baslik = a.get_text(" ", strip=True)
        link = urljoin(adres, a["href"]).split("#")[0]
        norm_baslik = normalize(baslik)

        if not baslik or urlparse(link).netloc != ana_host:
            continue

        if link == adres or link in GONDERILENLER:
            continue

        if any(normalize(k) in norm_baslik for k in HARIC_BASLIKLAR):
            continue

        # Başlıkta yalnızca hedef kadrolardan biri aranır.
        eslesme = [
            k for k in HEDEF_KADROLAR
            if normalize(k) in norm_baslik
        ]

        if not eslesme:
            continue

        incelenen += 1
        if incelenen > 50:
            break

        _, sayfa_basligi, icerik = sayfa_oku(link)

        if not icerik:
            continue

        if any(
            normalize(k) in normalize(baslik + " " + sayfa_basligi)
            for k in HARIC_BASLIKLAR
        ):
            continue

        # Sayfada tarih bulunamazsa yanlış ilan göndermemek için ele.
        tarih = tarih_bul(baslik + " " + sayfa_basligi + " " + icerik)

        if tarih is None:
            print("Tarih bulunamadı, elendi:", baslik)
            continue

        # Yalnızca bugünden sonraki tarihli ilanlar.
        if tarih <= date.today():
            print("Güncel değil, elendi:", baslik, tarih)
            continue

        mesaj = (
            "📢 YENİ KAMU İLANI\n\n"
            f"Kaynak: {kaynak}\n"
            f"Başlık: {baslik}\n"
            f"İlan tarihi: {tarih.strftime('%d.%m.%Y')}\n"
            f"Eşleşen kadro: {', '.join(eslesme)}\n"
            f"Bağlantı: {link}\n\n"
            "⚠️ Başvuru şartlarını ve son başvuru tarihini "
            "resmî ilandan kontrol et."
        )

        if telegram_gonder(mesaj):
            kaydet(link)
            yeni += 1

    print(f"{kaynak}: {yeni} ilan gönderildi.")


def main():
    if not TOKEN or not CHAT_ID:
        print("HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik.")
        return

    for kaynak, adres in SITELER.items():
        try:
            tara(kaynak, adres)
        except Exception as hata:
            print(f"{kaynak} hatası: {hata}")


if __name__ == "__main__":
    main()
