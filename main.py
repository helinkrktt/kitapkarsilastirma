import database
from indekskitap import scrape_indekskitap
from kitapisler import scrape_kitapisler
from kitapsec import scrape_kitapsec
from bkmkitap import scrape_bkmkitap
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, ForeignKey
import pandas as pd
from sqlalchemy import select
# Veritabanı oturumu oluştur
Session = sessionmaker(bind=database.engine)
session = Session()

def main():
    try:
        # BKMKitap verilerini çek ve kaydet
        print("BKMKitap verileri çekiliyor...")
        bkmkitap_data = scrape_bkmkitap()
        bkmkitap_data = bkmkitap_data.rename(columns={'title': 'product_name'})
        bkmkitap_data['source'] = 'bkmkitap'
        print(bkmkitap_data.head())  # Check DataFrame
        database.insert_data_to_table(bkmkitap_data)

        # IndeksKitap verilerini çek ve kaydet
        print("IndeksKitap verileri çekiliyor...")
        indeks_data = scrape_indekskitap()
        indeks_data = indeks_data.rename(columns={'title': 'product_name'})
        indeks_data['source'] = 'indekskitap'
        print(indeks_data.head())  # Check DataFrame
        database.insert_data_to_table(indeks_data)

        # KitapIsler verilerini çek ve kaydet
        print("KitapIsler verileri çekiliyor...")
        kitapisler_data = scrape_kitapisler()
        kitapisler_data = kitapisler_data.rename(columns={'title': 'product_name'})
        kitapisler_data['source'] = 'kitapisler'
        print(kitapisler_data.head())  # Check DataFrame
        database.insert_data_to_table(kitapisler_data)

        # KitapSec verilerini çek ve kaydet
        print("KitapSec verileri çekiliyor...")
        kitapsec_data = scrape_kitapsec()
        kitapsec_data = kitapsec_data.rename(columns={'title': 'product_name'})
        kitapsec_data['source'] = 'kitapsec'
        print(kitapsec_data.head())  # Check DataFrame
        database.insert_data_to_table(kitapsec_data)

        print("Tüm işlemler başarıyla tamamlandı!")
    except Exception as e:
        print("Bir hata oluştu:", e)
    finally:
        session.close()

def insert_data_to_db(data):
    try:
        # Veritabanı oturumu oluştur
        Session = sessionmaker(bind=database.engine)
        session = Session()

        # Tablo tanımları
        metadata = MetaData()

        books_table = Table('books', metadata,
                            Column('id', Integer, primary_key=True),
                            Column('kitap_adi', String))

        magaza_table = Table('magaza', metadata,
                             Column('id', Integer, primary_key=True),
                             Column('magaza_adi', String))

        fiyatlar_table = Table('fiyatlar', metadata,
                               Column('id', Integer, primary_key=True),
                               Column('book_id', Integer, ForeignKey('books.id')),
                               Column('magaza_id', Integer, ForeignKey('magaza.id')),
                               Column('fiyat', Float))

        products_table = Table('products', metadata,
                               Column('product_name', String),
                               Column('price', Float),
                               Column('source', String),
                               Column('image_url', String))

        # Tabloyu oluştur
        metadata.create_all(database.engine)

        # Verileri ekleyin
        for index, row in data.iterrows():
            # Books tablosuna ekle
            book_insert_stmt = books_table.insert().values(kitap_adi=row['product_name'])
            result = session.execute(book_insert_stmt)
            book_id = result.inserted_primary_key[0]

            # Magaza tablosuna ekle
            magaza_insert_stmt = magaza_table.insert().values(magaza_adi=row['source'])
            result = session.execute(magaza_insert_stmt)
            magaza_id = result.inserted_primary_key[0]

            # Fiyatlar tablosuna ekle
            fiyatlar_insert_stmt = fiyatlar_table.insert().values(
                book_id=book_id,
                magaza_id=magaza_id,
                fiyat=row['price']
            )
            session.execute(fiyatlar_insert_stmt)

            # Products tablosuna ekle
            products_insert_stmt = products_table.insert().values(
                product_name=row['product_name'],
                price=row['price'],
                source=row['source'],
                image_url=row['image_url']
            )
            session.execute(products_insert_stmt)

        session.commit()

    except Exception as e:
        print(f"Veri ekleme sırasında hata oluştu: {e}")
        session.rollback()

    finally:
        session.close()

def search_books_by_keyword(keyword):
    try:
        Session = sessionmaker(bind=database.engine)
        session = Session()
        metadata = MetaData()
        books_table = Table('books', metadata, autoload_with=database.engine)

        query = select(books_table).where(books_table.c.kitap_adi.ilike(f"%{keyword}%"))
        results = session.execute(query).fetchall()
        books = [dict(row._mapping) for row in results]
        return books

    except Exception as e:
        print(f"Arama sırasında hata oluştu: {e}")
        return []

    finally:
        session.close()

if __name__ == "__main__":
    main()
