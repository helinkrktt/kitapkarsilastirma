import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_indekskitap():
    """
    İndeks Kitap sitesinden TYT kitap bilgilerini ilk 5 sayfadan çeker.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'tr-TR,tr;q=0.9',
    }
    
    liste = []
    base_url = "https://www.indekskitap.com/kategori/yks-tyt"
    
    # İlk 5 sayfayı tara
    for page in range(1, 6):
        url = f"{base_url}?page={page}"
        print(f"\nSayfa {page} yükleniyor: {url}")
        
        try:
            response = requests.get(url, headers=headers)
            print(f"Status Code: {response.status_code}")
            
            if response.status_code != 200:
                print(f"Sayfa {page} yüklenemedi, diğer sayfaya geçiliyor...")
                continue
            
            # Encoding'i manuel ayarla
            response.encoding = 'utf-8'
            
            # HTML'i parse et
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Debug için HTML'i kaydet (sadece ilk sayfa için)
            if page == 1:
                with open('indekskitap_debug.html', 'w', encoding='utf-8') as f:
                    f.write(soup.prettify())
                print("HTML dosyası kaydedildi")
            
            # Ürünleri bul
            products = soup.find_all('div', class_='showcase')
            print(f"Sayfa {page}'de bulunan ürün sayısı: {len(products)}")
            
            for product in products:
                try:
                    # Başlık
                    title_elem = product.find('div', class_='showcase-title')
                    if not title_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    
                    # Fiyat
                    price = None
                    price_new_elem = product.find('div', class_='showcase-price-new')
                    if price_new_elem:
                        price_text = price_new_elem.get_text(strip=True)
                        try:
                            price = float(price_text.replace("TL", "").replace("₺", "")
                                       .replace(".", "").replace(",", ".").strip())
                        except:
                            print(f"Fiyat dönüştürülemedi: {price_text}")
                            continue
                    
                    # Yayınevi
                    publisher = ""
                    brand_elem = product.find('div', class_='showcase-brand')
                    if brand_elem:
                        publisher = brand_elem.get_text(strip=True)
                    
                    # Stok durumu
                    stock_status = "Stokta Var"
                    if product.find(class_='out-of-stock') or product.find(class_='showcase-onsiparis'):
                        stock_status = "Stokta Yok"
                    
                    liste.append({
                        "title": title,
                        "price": price,
                        "publisher": publisher,
                        "stock": stock_status,
                        "source": "indekskitap.com",
                        "page": page
                    })
                    
                    print(f"Ürün eklendi: {title}")
                    
                except Exception as e:
                    print(f"Ürün işleme hatası: {str(e)}")
                    continue
            
            # Sayfalar arası bekleme
            if page < 5:
                time.sleep(2)  # 2 saniye bekle
                
        except Exception as e:
            print(f"Sayfa {page} için genel hata: {str(e)}")
            continue
    
    print(f"\nToplam {len(liste)} ürün bulundu")
    return pd.DataFrame(liste)

if __name__ == "__main__":
    data = scrape_indekskitap()
    print("\nDataFrame içeriği:")
    print(data)
    
    if not data.empty:
        data.to_csv("indekskitap_products.csv", index=False, encoding="utf-8")
        print("\nSonuçlar 'indekskitap_products.csv' dosyasına kaydedildi.")