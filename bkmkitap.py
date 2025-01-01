from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import pandas as pd
import time

def scrape_bkmkitap():
    """
    BKM Kitap sitesinden TYT kitap bilgilerini Selenium kullanarak çeker.
    """
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.maximize_window()
    
    liste = []
    try:
        # İlk 5 sayfa için döngü
        for page in range(1, 6):
            url = f"https://www.bkmkitap.com/tyt-kitaplari?pg={page}"
            print(f"\nSayfa {page} yükleniyor: {url}")
            driver.get(url)
            time.sleep(5)
            
            print("Sayfa kaydırılıyor...")
            for _ in range(3):
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                time.sleep(2)
            
            products = driver.find_elements(By.CSS_SELECTOR, ".product-item")
            print(f"Sayfa {page}'de bulunan ürün sayısı: {len(products)}")
            
            for i, product in enumerate(products, 1):
                try:
                    print(f"\nSayfa {page} - Ürün {i} işleniyor...")
                    
                    # Başlık
                    title_element = product.find_element(By.CSS_SELECTOR, "a.product-title")
                    title = title_element.text.strip()
                    print(f"Başlık: {title}")
                    
                    # Fiyat
                    try:
                        price_element = product.find_element(By.CSS_SELECTOR, ".current-price .product-price")
                        price = float(price_element.text.replace("TL", "").replace("₺", "").replace(",", ".").strip())
                        print(f"Fiyat: {price}")
                    except:
                        print("Fiyat bulunamadı, ürün atlanıyor")
                        continue
                    
                    # Yayınevi
                    try:
                        publisher_element = product.find_element(By.CSS_SELECTOR, "a.brand-title")
                        publisher = publisher_element.text.strip()
                        print(f"Yayınevi: {publisher}")
                    except:
                        publisher = ""
                        print("Yayınevi bulunamadı")
                    
                    # Yazar
                    try:
                        author_element = product.find_element(By.CSS_SELECTOR, "a.model-title")
                        author = author_element.text.strip()
                        print(f"Yazar: {author}")
                    except:
                        author = ""
                        print("Yazar bulunamadı")
                    
                    # İndirim oranı
                    try:
                        discount_element = product.find_element(By.CSS_SELECTOR, ".product-discount")
                        discount = int(discount_element.text.strip())
                        print(f"İndirim: %{discount}")
                    except:
                        discount = 0
                        print("İndirim bulunamadı")
                    
                    # Ürün URL'i
                    try:
                        url = title_element.get_attribute("href")
                    except:
                        url = ""
                    
                    liste.append({
                        "title": title,
                        "price": price,
                        "publisher": publisher,
                        "author": author,
                        "discount": discount,
                        "url": url,
                        "source": "bkmkitap.com",
                        "page": page
                    })
                    print(f"Ürün başarıyla eklendi: {title}")
                    
                except Exception as e:
                    print(f"Ürün işleme hatası: {str(e)}")
                    continue
                    
    except Exception as e:
        print(f"Scraping error: {str(e)}")
        
    finally:
        driver.quit()
        
    print(f"\nToplam {len(liste)} ürün bulundu")
    return pd.DataFrame(liste)

if __name__ == "__main__":
    data = scrape_bkmkitap()
    print("\nDataFrame içeriği:")
    print(data)
    
    # Sonuçları CSV dosyasına kaydet
    data.to_csv("bkmkitap_products.csv", index=False, encoding="utf-8")
    print("\nSonuçlar 'bkmkitap_products.csv' dosyasına kaydedildi.")
