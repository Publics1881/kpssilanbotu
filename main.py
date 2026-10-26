import requests
import xml.etree.ElementTree as ET

url = "https://www.kamupersoneli.net/rss/haberler/personel-alimi/"

try:
    response = requests.get(url, timeout=30)
    print("HTTP DURUMU:", response.status_code)
    response.raise_for_status()

    root = ET.fromstring(response.content)

    for item in root.findall(".//item"):
        title = item.findtext("title", default="Başlık yok")
        link = item.findtext("link", default="")
        print(title)
        print(link)
        print("-" * 40)

except Exception as e:
    print("HATA:", e)
