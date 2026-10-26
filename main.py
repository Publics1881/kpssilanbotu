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

# Yalnızca istediğin kadrolar
HEDEF_KADROLAR = [
    "zabıt katibi",
    "zabıt kâtibi",
    "icra katibi",
    "icra kâtibi",
    "veri hazırlama kontrol işletmeni",
    "cezaevi kâtibi",
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

HARIC_KELIMELER = [
    "sınav sonuçları",
    "başvuru sonuçları",
    "yerleştirme sonuçları",
    "sözlü sınav sonuçları",
    "yedek aday duyurusu",
    "sınav sonuçlarına ilişkin",
]

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()
DOSYA = "gonderilen_ilanlar.txt"

OTURUM = requests.Session()
OTURUM.headers.update({
    "User-Agent": "Mozilla/5.0"
})


def duzelt(metin):
    metin = (metin or "").casefold()
    metin = metin.replace("ı", "i")
    metin = re.sub(r"\s+", " ", metin)
    return metin.strip()


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
            "script", "style", "nav", "footer",
            "header", "noscript", "svg"
        ]):
            etiket.decompose()

        baslik = soup.title.get_text(" ", strip=True) if soup.title else ""
        icerik = soup.get_text(" ", strip=True)

        return soup, baslik, icerik

    except requests.RequestException as hata:
        print(f"Sayfa okunamadı: {adres} | {hata}")
        return None, "", ""


def hedef_bul(metin):
    metin = duzelt(metin)

    return [
        kadro for kadro in HEDEF_KADROLAR
        if duzelt(kadro) in metin
    ]


def sonuc_duyurusu_mu(metin):
    metin = duzelt(metin)

    return any(
        duzelt(kelime) in metin
        for kelime in HARIC_KELIMELER
    )


def tara(isim, adres):
    print(f"\n--- {isim} taranıyor ---")

    ana_host = urlparse(adres).netloc
    soup, _, _ = sayfa_oku(adres)

    if soup is None:
        return

    yeni = 0
    incelenen = 0

    for a in soup.find_all("a", href=True):
        baslik = a.get_text(" ", strip=True)
        link = urljoin(adres, a["href"]).split("#")[0]

        if not baslik:
            continue

        if urlparse(link).netloc != ana_host:
            continue

        if link in GONDERILENLER or link == adres:
            continue

        # Genel ifadeler değil, yalnızca hedef kadrolar
        if not hedef_bul(baslik):
            continue

        if sonuc_duyurusu_mu(baslik):
            continue

        incelenen += 1

        if incelenen > 40:
            break

        _, sayfa_basligi, icerik = sayfa_oku(link)

        if not icerik:
            continue

        tam_metin = baslik + " " + sayfa_basligi + " " + icerik

        if sonuc_duyurusu_mu(baslik + " " + sayfa_basligi):
            continue

        eslesmeler = hedef_bul(tam_metin)

        if not eslesmeler:
            continue

        mesaj = (
            "📢 KAMU PERSONEL İLANI\n\n"
            f"Kaynak: {isim}\n"
            f"Başlık: {baslik}\n"
            f"Bağlantı: {link}\n\n"
            f"Eşleşen kadrolar: {', '.join(eslesmeler)}\n\n"
            "⚠️ Başvurmadan önce mezuniyet, nitelik kodları "
            "ve başvuru tarihini resmî ilandan kontrol et."
        )

        if telegram_gonder(mesaj):
            kaydet(link)
            yeni += 1
            print("Gönderildi:", baslik)

    print(f"{isim}: {yeni} yeni ilan gönderildi.")


def main():
    if not TOKEN or not CHAT_ID:
        print("HATA: TELEGRAM_BOT_TOKEN veya TELEGRAM_CHAT_ID eksik.")
        return

    for isim, adres in SITELER.items():
        try:
            tara(isim, adres)
        except Exception as hata:
            print(f"{isim} tarama hatası: {hata}")


if __name__ == "__main__":
    main()
