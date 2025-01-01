import requests
from bs4 import BeautifulSoup

def fetch_book_image(book_name):
    search_url = f"https://www.example.com/search?q={book_name}"
    response = requests.get(search_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Örnek: İlk görseli al
    image_tag = soup.find('img', class_='book-image')
    if image_tag:
        return image_tag['src']
    return None
