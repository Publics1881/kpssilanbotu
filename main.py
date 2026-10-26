CHAT_ID,
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


if name == "__main__":
    main()
