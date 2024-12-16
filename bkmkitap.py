import requests
from bs4 import BeautifulSoup
import pandas as pd

# URL'nin temel kısmı
base_url = "https://www.bkmkitap.com/tyt-matematik-soru-bankalari?pg="


# Tüm ürünleri toplamak için bir liste
liste = []

# Sayfa döngüsü
for page in range(1, 43):  # 1'den 5'e kadar (5 dahil değil)
    # URL'yi oluştur
    url = f"{base_url}{page}"
    response = requests.get(url)
    html_icerigi = response.content
    soup = BeautifulSoup(html_icerigi, "html.parser")
    
    # Ürün isimlerini ve fiyatlarını al
    isim = soup.find_all("a", attrs={"class": "product-title py-10px text-center"})
    fiyat = soup.find_all("span", attrs={"class": "product-price"})
    
    # İsim ve fiyatları işleyerek listeye ekle
    for i in range(len(isim)):
        urun_isim = isim[i].text.strip("\n").strip()
        urun_fiyat = fiyat[i].text.strip("\n").strip()
        liste.append([urun_isim, urun_fiyat])

# Listeyi DataFrame'e dönüştür
cikti = pd.DataFrame(liste, columns=["Ürün İsimleri", "Fiyatlar"])
pd.set_option("display.max_rows", None)
pd.set_option("display.max_columns", None)
# DataFrame'i yazdır    
print(cikti)