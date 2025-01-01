from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import pandas as pd
import time

def scrape_kitapsec():
    """
    Kitapsec sitesinden TYT kitap fiyat bilgilerini çeker.

    Returns:
        pandas.DataFrame: Ürün isimleri, fiyatlar ve kaynak bilgisi.
    """
    # Chrome driver'ı başlat
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Tarayıcıyı arka planda çalıştır
    driver = webdriver.Chrome(options=options)
    
    base_url = "https://www.kitapsec.com/Products/YKS-Kitaplari/TYT-Soru-Bankalari/1-6-0a0-0-0-0-0-0.xhtml"
    liste = []
    seen_titles = set()  # Tekrar eden ürünleri engellemek için

    try:
        # Sayfa döngüsü
        for page in range(1, 6):
            if page == 1:
                url = base_url
            else:
                url = f"{base_url}?page={page}"
                
            print(f"\nSayfa {page} yükleniyor...")
            driver.get(url)
            
            # Sayfanın yüklenmesini bekle
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "Ks_ContentUrunList"))
            )
            
            # İlk sayfa için HTML'i kaydet
            if page == 1:
                with open('kitapsec_debug.html', 'w', encoding='utf-8') as f:
                    f.write(driver.page_source)
                print("Debug için HTML kaydedildi")
            
            # Ürün kartlarını bul
            product_cards = driver.find_elements(By.CLASS_NAME, "Ks_UrunSatir")
            print(f"Sayfa {page}'de {len(product_cards)} ürün kartı bulundu")

            page_products = []  # Bu sayfadaki ürünleri geçici olarak sakla
            for card in product_cards:
                try:
                    # Başlık
                    title_elem = card.find_element(By.CSS_SELECTOR, "a.text span[itemprop='name']")
                    if not title_elem:
                        continue
                        
                    title = title_elem.text.strip()
                    
                    # Kitap olmayan öğeleri filtrele
                    if len(title) < 5:  # Minimum başlık uzunluğu
                        continue
                        
                    if any(word.lower() in title.lower() for word in ["anasayfa", "ürünler", "sepetim", "giriş yap"]):
                        continue
                    
                    # Fiyat
                    try:
                        price_elem = card.find_element(By.CSS_SELECTOR, "span.fiyat font.satis")
                        if not price_elem:
                            continue
                            
                        price_text = price_elem.text.strip().replace("TL", "").replace(",", ".")
                        price = float(price_text.split()[0])
                        if price <= 0:  # Geçersiz fiyatları filtrele
                            continue
                    except:
                        continue

                    page_products.append({
                        "title": title,
                        "price": price,
                        "source": "kitapsec.com"
                    })
                    print(f"Ürün eklendi: {title} - {price} TL")
                    
                except Exception as e:
                    print(f"Ürün işleme hatası: {str(e)}")
                    continue

            # Sayfadaki ürün sayısını kontrol et
            if len(page_products) == 0:
                print(f"Sayfa {page}'de ürün bulunamadı, işlem sonlandırılıyor...")
                break
                
            liste.extend(page_products)
            print(f"Sayfa {page}'den {len(page_products)} ürün eklendi.")

            # Sayfalar arası kısa bekleme
            if page < 5:
                time.sleep(1)

    finally:
        driver.quit()  # Tarayıcıyı kapat

    print(f"\nToplam {len(liste)} ürün bulundu")
    df = pd.DataFrame(liste)
    
    # Sonuçları CSV'ye kaydet
    if not df.empty:
        df.to_csv("kitapsec_products.csv", index=False, encoding="utf-8")
        print("\nSonuçlar 'kitapsec_products.csv' dosyasına kaydedildi.")
    
    return df

if __name__ == "__main__":
    data = scrape_kitapsec()
    print("\nDataFrame içeriği:")
    print(data)
    
    if not data.empty:
        data.to_csv("kitapsec_products.csv", index=False, encoding="utf-8")
        print("\nSonuçlar 'kitapsec_products.csv' dosyasına kaydedildi.")

