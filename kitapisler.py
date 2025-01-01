from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import pandas as pd
import time

def scrape_kitapisler():
    """
    Kitapisler sitesinden TYT kitap fiyat bilgilerini çeker.

    Returns:
        pandas.DataFrame: Ürün isimleri, fiyatlar ve kaynak bilgisi.
    """
    # Chrome driver'ı başlat
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    driver = webdriver.Chrome(options=options)
    
    url = "https://www.kitapisler.com/TYT-Temel-Yeterlilik-Testi-1197"
    liste = []
    seen_titles = set()

    try:
        print("Sayfa yükleniyor...")
        driver.get(url)
        
        # Sayfanın yüklenmesi için bekle
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        
        print("Sayfa yüklendi, ürünler için bekleniyor...")
        time.sleep(5)  # Dinamik içeriğin yüklenmesi için ek bekleme
        
        # JavaScript ile sayfayı aşağı kaydır
        for _ in range(5):  # Daha fazla scroll
            driver.execute_script("""
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            """)
            time.sleep(2)
        
        print("Ürünler aranıyor...")
        
        # Sayfa kaynağını kaydet (debug için)
        with open('kitapisler_debug.html', 'w', encoding='utf-8') as f:
            f.write(driver.page_source)
        
        # Ürün kartlarını bul - farklı seçicileri dene
        selectors = [
            ".productItem",
            ".ItemOrj",
            ".productDetail",
            "[data-info]",
            ".productContent",
            ".productIcon",
            ".productImage",
            ".categoryPrice",
            ".productName",
            ".detailLink",
            ".list_title_type1_text",
            ".listingProduct",
            ".productList .productItem",
            ".productList [data-info]",
            ".productList .ItemOrj"
        ]
        
        product_cards = []
        for selector in selectors:
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, selector)
                if cards:
                    print(f"'{selector}' seçicisi ile {len(cards)} ürün bulundu")
                    product_cards = cards
                    break
            except Exception as e:
                print(f"Seçici hatası ({selector}): {str(e)}")
                continue
        
        if not product_cards:
            print("Ürün kartları bulunamadı, tüm linkleri kontrol ediyorum...")
            links = driver.find_elements(By.TAG_NAME, "a")
            product_links = []
            for link in links:
                try:
                    href = link.get_attribute("href")
                    if href and not href.startswith("javascript:") and not "filtre" in href and not "kategori" in href.lower():
                        text = link.text.strip()
                        if text and len(text) > 10 and not text.endswith("Yayınları"):
                            product_links.append(link)
                except:
                    continue
            
            if product_links:
                print(f"{len(product_links)} ürün linki bulundu")
                product_cards = product_links
        
        print(f"{len(product_cards)} ürün kartı bulundu")
        
        for card in product_cards:
            try:
                # Önce kartın kendisini veya parent elementini kontrol et
                parent = card
                try:
                    parent = card.find_element(By.XPATH, "./..")
                except:
                    pass
                
                # Başlık için farklı yöntemleri dene
                title = None
                title_selectors = [
                    "a[title]",
                    ".productName",
                    ".detailLink",
                    ".productName a",
                    "h2 a",
                    "h3 a",
                    ".name a",
                    ".list_title_type1_text"
                ]
                
                for selector in title_selectors:
                    try:
                        title_elem = parent.find_element(By.CSS_SELECTOR, selector)
                        title = title_elem.get_attribute("title") or title_elem.text
                        if title:
                            title = title.strip()
                            break
                    except:
                        continue
                
                if not title:
                    try:
                        title = card.get_attribute("title") or card.text
                        if title:
                            title = title.strip()
                    except:
                        continue
                
                if not title or len(title) < 10 or title in seen_titles or title.endswith("Yayınları"):
                    continue
                
                # Fiyat için farklı yöntemleri dene
                price = None
                price_selectors = [
                    ".discountPrice span",
                    ".currentPrice",
                    ".newPrice",
                    ".discountPrice",
                    ".price",
                    ".salePrice",
                    ".categoryPrice",
                    ".listingPriceNormal",
                    ".listingPrice"
                ]
                
                for selector in price_selectors:
                    try:
                        price_elem = parent.find_element(By.CSS_SELECTOR, selector)
                        price_text = price_elem.text.strip()
                        if price_text:
                            # Fiyat metnini temizle
                            price_text = price_text.replace("₺", "").replace("TL", "").replace(",", ".").strip()
                            try:
                                price = float(price_text.split()[0])
                                break
                            except (ValueError, IndexError):
                                continue
                    except:
                        continue
                
                if not price:
                    continue
                
                # Geçerli ürünü listeye ekle
                seen_titles.add(title)
                liste.append({
                    "title": title,
                    "price": price,
                    "source": "kitapisler.com"
                })
                print(f"Ürün eklendi: {title} - {price}₺")
                
            except Exception as e:
                print(f"Ürün işleme hatası: {str(e)}")
                continue

    except Exception as e:
        print(f"Genel hata: {str(e)}")
    finally:
        driver.quit()

    print(f"\nToplam {len(liste)} ürün bulundu")
    return pd.DataFrame(liste)

if __name__ == "__main__":
    data = scrape_kitapisler()
    print("\nDataFrame içeriği:")
    print(data)
    
    if not data.empty:
        data.to_csv("kitapisler_products.csv", index=False, encoding="utf-8")
        print("\nSonuçlar 'kitapisler_products.csv' dosyasına kaydedildi.")
