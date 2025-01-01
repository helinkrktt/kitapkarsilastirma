from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, select, ForeignKey, text
from sqlalchemy.engine.url import URL
from sqlalchemy.orm import sessionmaker
import pandas as pd
from pprint import pprint

def get_database_url():
    DATABASE_CONFIG = {
        "drivername": "postgresql",
        "username": "postgres",  # PostgreSQL kullanıcı adı
        "password": "801018",  # PostgreSQL şifresi
        "host": "localhost",     # Veritabanı sunucusunun adresi
        "port": 5432,             # PostgreSQL varsayılan portu
        "database": "kitap_projesi",  # Veritabanı adı
    }
    return URL.create(**DATABASE_CONFIG)

# Veritabanı bağlantı URL'si oluştur
DATABASE_URL = get_database_url()

# SQLAlchemy motorunu oluştur
engine = create_engine(DATABASE_URL, echo=True)

def insert_data_to_table(data):
    """
    Verilen verileri books, magaza, fiyatlar ve products tablolarına ekler.
    Her kayıt için ayrı transaction kullanır.

    Args:
        data (pandas.DataFrame): Eklenecek verileri içeren DataFrame.
    """
    # DataFrame'i kopyala
    df = data.copy()
    
    # Sütun isimlerini standartlaştır
    column_mappings = {
        'product_name': 'title',
        'name': 'title',
        'kitap_adi': 'title',
        'fiyat': 'price',
        'magaza': 'source'
    }
    
    df = df.rename(columns=column_mappings, errors='ignore')
    
    if 'title' not in df.columns or 'price' not in df.columns or 'source' not in df.columns:
        raise ValueError("Gerekli sütunlar bulunamadı: title, price, source")

    Session = sessionmaker(bind=engine)
    
    # Tabloları tanımla
    metadata = MetaData()
    books = Table('books', metadata,
        Column('id', Integer, primary_key=True),
        Column('kitap_adi', String)
    )

    magaza = Table('magaza', metadata,
        Column('id', Integer, primary_key=True),
        Column('magaza_adi', String)
    )

    fiyatlar = Table('fiyatlar', metadata,
        Column('id', Integer, primary_key=True),
        Column('book_id', Integer, ForeignKey('books.id')),
        Column('magaza_id', Integer, ForeignKey('magaza.id')),
        Column('fiyat', Float)
    )

    products = Table('products', metadata,
        Column('product_name', String),
        Column('price', Float),
        Column('source', String)
    )

    successful_inserts = 0
    failed_inserts = 0

    for index, row in df.iterrows():
        session = Session()  # Her kayıt için yeni bir session oluştur
        try:
            # 1. Products tablosuna ekle
            products_insert = products.insert().values(
                product_name=row['title'],
                price=row['price'],
                source=row['source']
            )
            session.execute(products_insert)

            # 2. Kitabı kontrol et veya ekle
            book_select = select(books).where(books.c.kitap_adi == row['title'])
            book_result = session.execute(book_select).first()
            
            if book_result is None:
                book_insert = books.insert().values(kitap_adi=row['title'])
                book_result = session.execute(book_insert)
                book_id = book_result.inserted_primary_key[0]
            else:
                book_id = book_result[0]

            # 3. Mağazayı kontrol et veya ekle
            magaza_select = select(magaza).where(magaza.c.magaza_adi == row['source'])
            magaza_result = session.execute(magaza_select).first()
            
            if magaza_result is None:
                magaza_insert = magaza.insert().values(magaza_adi=row['source'])
                magaza_result = session.execute(magaza_insert)
                magaza_id = magaza_result.inserted_primary_key[0]
            else:
                magaza_id = magaza_result[0]

            # 4. Fiyat kaydının var olup olmadığını kontrol et
            fiyat_select = select(fiyatlar).where(
                (fiyatlar.c.book_id == book_id) & 
                (fiyatlar.c.magaza_id == magaza_id)
            )
            fiyat_result = session.execute(fiyat_select).first()

            # Eğer bu kitap-mağaza kombinasyonu için fiyat yoksa ekle
            if fiyat_result is None:
                fiyat_insert = fiyatlar.insert().values(
                    book_id=book_id,
                    magaza_id=magaza_id,
                    fiyat=row['price']
                )
                session.execute(fiyat_insert)

            session.commit()
            successful_inserts += 1
            print(f"Kayıt başarıyla eklendi: {row['title']}")

        except Exception as e:
            session.rollback()
            failed_inserts += 1
            print(f"Kayıt eklenirken hata oluştu: {str(e)}")
            print(f"Hatalı satır: {row}")
        finally:
            session.close()

    print(f"\nİşlem tamamlandı:")
    print(f"Başarılı kayıtlar: {successful_inserts}")
    print(f"Başarısız kayıtlar: {failed_inserts}")
    print(f"Toplam kayıt: {len(df)}")

def search_books_by_keyword(keyword):
    """
    Belirtilen anahtar kelimeye göre 'books' tablosunda kitap_adi sütununda arama yapar.

    Args:
        keyword (str): Aranacak anahtar kelime.

    Returns:
        list: Anahtar kelimeye göre eşleşen kitap kayıtları.
    """
    try:
        Session = sessionmaker(bind=engine)
        session = Session()

        # Tabloyu tanımla
        metadata = MetaData()
        books = Table('books', metadata,
            Column('id', Integer, primary_key=True),
            Column('kitap_adi', String)
        )

        # Sorguyu oluştur
        query = select(books).where(books.c.kitap_adi.ilike(f"%{keyword}%"))

        # Sorguyu çalıştır ve sonuçları al
        results = session.execute(query).fetchall()

        # Sonuçları listeye dönüştür
        books_list = [dict(row._mapping) for row in results]
        return books_list

    except Exception as e:
        print(f"Arama sırasında hata oluştu: {e}")
        return []

    finally:
        session.close()

def save_books_to_db(books):
    """
    Kitap verilerini veritabanına kaydeder.
    
    Args:
        books (list): Kaydedilecek kitap verileri listesi.
    """
    Session = sessionmaker(bind=engine)
    session = Session()
    successful = 0
    failed = 0

    # Tabloları tanımla
    metadata = MetaData()
    books_table = Table('books', metadata,
        Column('id', Integer, primary_key=True),
        Column('kitap_adi', String)
    )

    magaza_table = Table('magaza', metadata,
        Column('id', Integer, primary_key=True),
        Column('magaza_adi', String)
    )

    fiyatlar_table = Table('fiyatlar', metadata,
        Column('id', Integer, primary_key=True),
        Column('book_id', Integer, ForeignKey('books.id')),
        Column('magaza_id', Integer, ForeignKey('magaza.id')),
        Column('fiyat', Float)
    )

    products_table = Table('products', metadata,
        Column('product_name', String),
        Column('price', Float),
        Column('source', String)
    )

    try:
        for book in books:
            try:
                # 1. Products tablosuna ekle
                products_insert = products_table.insert().values(
                    product_name=book['product_name'],
                    price=book['price'],
                    source=book['source']
                )
                session.execute(products_insert)

                # 2. Kitabı ekle veya bul
                book_select = select(books_table).where(books_table.c.kitap_adi == book['product_name'])
                book_result = session.execute(book_select).first()
                
                if book_result is None:
                    book_insert = books_table.insert().values(kitap_adi=book['product_name'])
                    book_result = session.execute(book_insert)
                    book_id = book_result.inserted_primary_key[0]
                else:
                    book_id = book_result[0]

                # 3. Mağazayı ekle veya bul
                magaza_select = select(magaza_table).where(magaza_table.c.magaza_adi == book['source'])
                magaza_result = session.execute(magaza_select).first()
                
                if magaza_result is None:
                    magaza_insert = magaza_table.insert().values(magaza_adi=book['source'])
                    magaza_result = session.execute(magaza_insert)
                    magaza_id = magaza_result.inserted_primary_key[0]
                else:
                    magaza_id = magaza_result[0]

                # 4. Fiyat kaydını ekle
                fiyat_insert = fiyatlar_table.insert().values(
                    book_id=book_id,
                    magaza_id=magaza_id,
                    fiyat=book['price']
                )
                session.execute(fiyat_insert)
                successful += 1
                
            except Exception as e:
                print(f"Kitap kaydedilirken hata oluştu: {book['product_name']} - {str(e)}")
                failed += 1
                continue

        session.commit()
        print(f"Kayıt işlemi tamamlandı. Başarılı: {successful}, Başarısız: {failed}")
        
    except Exception as e:
        print(f"Toplu kayıt sırasında hata oluştu: {str(e)}")
        session.rollback()
    finally:
        session.close()

def get_exact_matches(book_name):
    """
    Belirtilen kitabın tüm kaynaklardaki fiyatlarını getirir.
    
    Args:
        book_name (str): Aranacak kitabın tam adı
        
    Returns:
        dict: Her kaynaktaki fiyat bilgisi ve kitap detayları
        {
            'kitap_adi': str,
            'fiyatlar': {
                'magaza_adi': fiyat veya None (stokta yoksa)
            }
        }
    """
    try:
        Session = sessionmaker(bind=engine)
        session = Session()

        # Kitabı bul
        query = text("""
            SELECT b.kitap_adi, m.magaza_adi, f.fiyat
            FROM books b
            CROSS JOIN magaza m
            LEFT JOIN fiyatlar f ON f.book_id = b.id AND f.magaza_id = m.id
            WHERE b.kitap_adi = :book_name
        """)
        
        results = session.execute(query, {'book_name': book_name}).fetchall()
        
        if not results:
            return None
            
        # Sonuçları düzenle
        response = {
            'kitap_adi': book_name,
            'fiyatlar': {}
        }
        
        for row in results:
            magaza_adi = row[1]
            fiyat = row[2]  # None olabilir (stokta yoksa)
            response['fiyatlar'][magaza_adi] = fiyat
            
        return response

    except Exception as e:
        print(f"Fiyat karşılaştırma sırasında hata oluştu: {e}")
        return None

    finally:
        session.close()
