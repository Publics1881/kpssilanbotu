import requests
import certifi
from bs4 import BeautifulSoup

url = "https://www.ilan.gov.tr/ilan-ara"

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    )
}

try:
    response = requests.get(
        url,
        headers=headers,
        timeout=30, verify=certifi.where()
    )

    print("HTTP DURUMU:", response.status_code)

    if response.status_code == 200:
        soup = BeautifulSoup(response.text, "html.parser")

        print("SAYFA BAŞLIĞI:", soup.title.string if soup.title else "Bulunamadı")

        for link in soup.find_all("a", href=True):
            title = link.get_text(strip=True)
            href = link["href"]

            if title and "/ilan/" in href:
                print(title)
                print("https://www.ilan.gov.tr" + href if href.startswith("/") else href)
                print("-" * 40)
    else:
        print("HATA: Site isteği kabul etmedi.")

except Exception as e:
    print("BAĞLANTI HATASI:", e)
