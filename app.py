from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, session
from sqlalchemy import create_engine, MetaData, Table, text
from sqlalchemy.orm import sessionmaker
from database import search_books_by_keyword, get_exact_matches
from bkmkitap import scrape_bkmkitap
from kitapisler import scrape_kitapisler
from kitapsec import scrape_kitapsec
from indekskitap import scrape_indekskitap
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
from utils import fetch_book_image

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY') or os.urandom(24)

# Veritabanı bağlantısı
engine = create_engine('postgresql://postgres:801018@localhost/kitap_projesi')
Session = sessionmaker(bind=engine)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    session = Session()
    try:
        if request.method == 'POST':
            username = request.form['username']
            password = request.form['password']
            
            metadata = MetaData()
            users = Table('users', metadata, autoload_with=engine)
            
            user = session.query(users).filter_by(username=username).first()
            
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = user.username
                session.commit()
                return redirect(url_for('index'))
            else:
                flash('Geçersiz kullanıcı adı veya şifre!')
                return redirect(url_for('login'))
                
        return render_template('login.html')
    except Exception as e:
        print(f"Giriş hatası: {e}")
        session.rollback()
        flash('Bir hata oluştu!')
        return redirect(url_for('login'))
    finally:
        session.close()

@app.route('/register', methods=['POST'])
def register():
    session = Session()
    try:
        username = request.form['username']
        password = request.form['password']
        
        metadata = MetaData()
        users = Table('users', metadata, autoload_with=engine)
        
        existing_user = session.query(users).filter_by(username=username).first()
        if existing_user:
            flash('Bu kullanıcı adı zaten kullanılıyor!')
            return redirect(url_for('login'))
        
        hashed_password = generate_password_hash(password)
        new_user = users.insert().values(username=username, password=hashed_password)
        session.execute(new_user)
        session.commit()
        
        flash('Kayıt başarılı! Şimdi giriş yapabilirsiniz.')
        return redirect(url_for('login'))
    except Exception as e:
        print(f"Kayıt hatası: {e}")
        session.rollback()
        flash('Bir hata oluştu!')
        return redirect(url_for('login'))
    finally:
        session.close()

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# Giriş kontrolü için decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Bu işlem için giriş yapmanız gerekiyor!')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Korumalı rotalar için decorator ekle
@app.route('/index')
def index():
    return render_template('index.html')

@app.route('/autocomplete', methods=['GET'])
def autocomplete():
    session = Session()
    try:
        search = request.args.get('q', '').strip()
        if not search or len(search) < 2:
            return jsonify([])
            
        metadata = MetaData()
        books_table = Table('books', metadata, autoload_with=engine)
        
        print(f"Arama terimi: {search}")  # Debug için
        
        # Kitap adlarında arama yapalım
        results = session.query(books_table.c.kitap_adi)\
            .filter(books_table.c.kitap_adi.ilike(f'%{search}%'))\
            .distinct()\
            .order_by(books_table.c.kitap_adi)\
            .limit(10)\
            .all()
        
        # Sonuçları liste haline getir
        kitaplar = [r[0] for r in results]
        print(f"Bulunan sonuçlar: {kitaplar}")  # Debug için
        
        session.commit()
        return jsonify(kitaplar)
        
    except Exception as e:
        print(f"Autocomplete hatası: {str(e)}")  # Hata mesajını yazdır
        session.rollback()
        return jsonify([])
    finally:
        session.close()

@app.route('/search', methods=['GET', 'POST'])
def search():
    session = Session()
    try:
        if request.method == 'POST':
            print("POST isteği alındı")  # Debug
            kitap_adi = request.form.get('kitap_adi', '').strip()
            print(f"Aranan kitap adı: {kitap_adi}")  # Debug
            
            if not kitap_adi or len(kitap_adi) < 2:
                print("Kitap adı çok kısa")  # Debug
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Lütfen en az 2 karakter içeren bir kitap adı girin!'})
                flash('Lütfen en az 2 karakter içeren bir kitap adı girin!')
                return redirect(url_for('index'))

            metadata = MetaData()
            books_table = Table('books', metadata, autoload_with=engine)
            
            # Tam eşleşme kontrolü
            exact_match = session.query(books_table).filter(books_table.c.kitap_adi == kitap_adi).first()
            print(f"Tam eşleşme sonucu: {exact_match}")  # Debug
            
            if exact_match:
                print(f"Tam eşleşme bulundu, ID: {exact_match.id}")  # Debug
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'redirect_url': url_for('exact_match_page', book_id=exact_match.id)})
                return redirect(url_for('exact_match_page', book_id=exact_match.id))
            
            # Benzer sonuçlar için yönlendirme
            print(f"Benzer sonuçlar için arama: {kitap_adi}")  # Debug
            similar_results = session.query(books_table)\
                .filter(books_table.c.kitap_adi.ilike(f'%{kitap_adi}%'))\
                .all()
            
            print(f"Bulunan benzer sonuçlar: {len(similar_results)}")  # Debug
            
            if similar_results:
                print("Benzer sonuçlar bulundu, similar_results sayfasına yönlendiriliyor")  # Debug
                similar_url = url_for('similar_results_page') + '?keyword=' + kitap_adi
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'redirect_url': similar_url})
                return redirect(similar_url)
            else:
                print("Benzer sonuç bulunamadı")  # Debug
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': 'Kitap bulunamadı!'})
                flash('Kitap bulunamadı!')
                return redirect(url_for('index'))
        
        session.commit()
        return render_template('search.html')
    except Exception as e:
        print(f"Arama hatası: {e}")
        session.rollback()
        flash('Bir hata oluştu!')
        return redirect(url_for('index'))
    finally:
        session.close()

@app.route('/book/<int:book_id>')
def book_detail(book_id):
    session = Session()
    try:
        metadata = MetaData()
        books_table = Table('books', metadata, autoload_with=engine)
        prices_table = Table('fiyatlar', metadata, autoload_with=engine)
        stores_table = Table('magaza', metadata, autoload_with=engine)

        # Debug için print ekleyelim
        print(f"Aranan kitap ID: {book_id}")

        query = (
            session.query(
                books_table.c.kitap_adi,
                prices_table.c.fiyat,
                stores_table.c.magaza_adi
            )
            .join(prices_table, books_table.c.id == prices_table.c.book_id)
            .join(stores_table, prices_table.c.magaza_id == stores_table.c.id)
            .filter(books_table.c.id == book_id)
        )

        results = query.all()
        print(f"Sorgu sonuçları: {results}")  # Debug için

        if not results:
            print("Kitap bulunamadı!")  # Debug için
            flash('Kitap bulunamadı!')
            return redirect(url_for('index'))

        book = {
            "name": results[0].kitap_adi,
            "prices": [{"amount": r.fiyat, "source": r.magaza_adi} for r in results]
        }
        print(f"Frontend'e gönderilen veri: {book}")  # Debug için

        session.commit()
        return render_template('book_detail.html', book=book)
    except Exception as e:
        print(f"Kitap detay hatası: {e}")
        session.rollback()
        flash('Bir hata oluştu!')
        return redirect(url_for('index'))
    finally:
        session.close()

@app.route('/scrape')
def scrape():
    bkmkitap_data = scrape_bkmkitap().to_dict(orient='records')
    kitapisler_data = scrape_kitapisler().to_dict(orient='records')
    kitapsec_data = scrape_kitapsec().to_dict(orient='records')
    indekskitap_data = scrape_indekskitap().to_dict(orient='records')

    all_data = bkmkitap_data + kitapisler_data + kitapsec_data + indekskitap_data
    return jsonify(all_data)

@app.route('/exact_match/<int:book_id>')
def exact_match_page(book_id):
    session = Session()
    try:
        metadata = MetaData()
        books_table = Table('books', metadata, autoload_with=engine)
        prices_table = Table('fiyatlar', metadata, autoload_with=engine)
        stores_table = Table('magaza', metadata, autoload_with=engine)

        # Önce seçilen kitabın adını al
        book_query = session.query(books_table).filter(books_table.c.id == book_id).first()
        if not book_query:
            session.rollback()
            flash('Kitap bulunamadı!')
            return redirect(url_for('index'))

        # Aynı isme sahip tüm kitapları bul
        query = text("""
            WITH cleaned_books AS (
                SELECT 
                    id,
                    kitap_adi,
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            LOWER(TRIM(kitap_adi)),
                            '^([a-zçğıöşü ]+ yayınları|[a-zçğıöşü ]+ yayınevi) ', ''
                        ),
                        ' ([a-zçğıöşü ]+ yayınları|[a-zçğıöşü ]+ yayınevi)$', ''
                    ) as normalized_name
                FROM books
            ),
            target_book AS (
                SELECT normalized_name
                FROM cleaned_books
                WHERE id = :book_id
            ),
            same_books AS (
                SELECT b.id
                FROM cleaned_books b, target_book tb
                WHERE b.normalized_name = tb.normalized_name
            )
            SELECT 
                m.magaza_adi,
                MIN(f.fiyat) as fiyat
            FROM same_books sb
            CROSS JOIN magaza m
            LEFT JOIN fiyatlar f ON f.book_id = sb.id AND f.magaza_id = m.id
            GROUP BY m.magaza_adi
            ORDER BY m.magaza_adi
        """)
        
        results = session.execute(query, {'book_id': book_id}).fetchall()
        
        # Sonuçları düzenle
        fiyatlar = {}
        for row in results:
            fiyatlar[row.magaza_adi] = row.fiyat

        book = {
            "kitap_adi": book_query.kitap_adi,
            "fiyatlar": fiyatlar
        }

        session.commit()
        return render_template('exact_match.html', book=book)
    except Exception as e:
        print(f"Tam eşleşme hatası: {e}")
        session.rollback()
        flash('Bir hata oluştu!')
        return redirect(url_for('index'))
    finally:
        session.close()

@app.route('/similar_results')
def similar_results_page():
    print("Similar results sayfası çağrıldı")  # Debug
    session = Session()
    try:
        # Arama terimini al
        keyword = request.args.get('keyword', '').strip()
        print(f"Alınan keyword: {keyword}")  # Debug
        
        if not keyword or len(keyword) < 2:
            print("Geçersiz keyword")  # Debug
            flash('Geçersiz arama terimi!')
            return redirect(url_for('index'))

        metadata = MetaData()
        books_table = Table('books', metadata, autoload_with=engine)
        prices_table = Table('fiyatlar', metadata, autoload_with=engine)
        stores_table = Table('magaza', metadata, autoload_with=engine)

        print(f"Aranan kelime: {keyword}")  # Debug

        # Kitapları ve fiyatları al
        query = text("""
            WITH cleaned_books AS (
                SELECT 
                    id,
                    kitap_adi,
                    REGEXP_REPLACE(
                        REGEXP_REPLACE(
                            LOWER(TRIM(kitap_adi)),
                            '^([a-zçğıöşü ]+ yayınları|[a-zçğıöşü ]+ yayınevi) ', ''
                        ),
                        ' ([a-zçğıöşü ]+ yayınları|[a-zçğıöşü ]+ yayınevi)$', ''
                    ) as normalized_name
                FROM books b
                WHERE b.kitap_adi ILIKE :keyword
            ),
            book_groups AS (
                SELECT 
                    normalized_name,
                    MIN(id) as representative_id,
                    MIN(kitap_adi) as representative_name,
                    array_agg(id) as all_book_ids
                FROM cleaned_books
                GROUP BY normalized_name
            )
            SELECT 
                bg.representative_id as id,
                bg.representative_name as kitap_adi,
                MIN(f.fiyat) as min_price
            FROM book_groups bg
            LEFT JOIN LATERAL unnest(bg.all_book_ids) AS book_ids ON true
            LEFT JOIN fiyatlar f ON f.book_id = book_ids
            GROUP BY bg.representative_id, bg.representative_name, bg.normalized_name
            ORDER BY bg.normalized_name
        """)
        
        results = session.execute(query, {'keyword': f'%{keyword}%'}).fetchall()
        print(f"Sorgu sonuçları: {results}")  # Debug
        
        books = []
        for result in results:
            if result.min_price:  # Sadece fiyatı olan kitapları göster
                books.append({
                    'id': result.id,
                    'name': result.kitap_adi,
                    'price': result.min_price
                })

        print(f"Frontend'e gönderilen kitaplar: {books}")  # Debug

        if not books:
            print("Kitap bulunamadı")  # Debug
            flash('Benzer kitap bulunamadı!')
            return redirect(url_for('index'))

        print("Template'e gönderiliyor")  # Debug
        session.commit()
        return render_template('similar_results.html', books=books, keyword=keyword)

    except Exception as e:
        print(f"Benzer sonuçlar hatası: {str(e)}")  # Debug - stack trace için str(e)
        session.rollback()
        flash('Bir hata oluştu!')
        return redirect(url_for('index'))
    finally:
        session.close()

@app.route('/fetch_book_image/<path:book_name>')
def fetch_book_image(book_name):
    session = Session()
    try:
        metadata = MetaData()
        books_table = Table('books', metadata, autoload_with=engine)
        
        # Kitap bilgisini veritabanından al
        book = session.query(books_table.c.image_url)\
            .filter(books_table.c.kitap_adi == book_name)\
            .first()
            
        if book and book.image_url:
            session.commit()
            return redirect(book.image_url)
        else:
            # Varsayılan bir resim döndür
            session.commit()
            return redirect(url_for('static', filename='images/default_book.jpg'))
    except Exception as e:
        print(f"Resim getirme hatası: {e}")
        session.rollback()
        return redirect(url_for('static', filename='images/default_book.jpg'))
    finally:
        session.close()

if __name__ == '__main__':
     app.run(host='0.0.0.0', port=3335, debug=True) 