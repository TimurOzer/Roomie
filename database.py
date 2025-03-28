import sqlite3

class Database:
    def __init__(self, db_name):
        self.conn = sqlite3.connect(db_name)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ilanlar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                baslik TEXT NOT NULL,
                aciklama TEXT NOT NULL,
                fiyat TEXT NOT NULL,
                konum TEXT NOT NULL,
                cinsiyet TEXT NOT NULL,
                oda_sayisi TEXT NOT NULL,
                sigara INTEGER DEFAULT 0,
                alkol INTEGER DEFAULT 0,
                evcil_hayvan INTEGER DEFAULT 0,
                resimler TEXT,
                tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.conn.commit()

    def ilan_ekle(self, baslik, aciklama, fiyat, konum, cinsiyet, oda_sayisi, 
                 sigara, alkol, evcil_hayvan, resimler):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO ilanlar 
            (baslik, aciklama, fiyat, konum, cinsiyet, oda_sayisi, 
             sigara, alkol, evcil_hayvan, resimler)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (baslik, aciklama, fiyat, konum, cinsiyet, oda_sayisi, 
              sigara, alkol, evcil_hayvan, resimler))
        self.conn.commit()

    def get_ilanlar(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM ilanlar ORDER BY tarih DESC')
        columns = [column[0] for column in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_ilan(self, ilan_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM ilanlar WHERE id = ?', (ilan_id,))
        columns = [column[0] for column in cursor.description]
        row = cursor.fetchone()
        return dict(zip(columns, row)) if row else None

    def close(self):
        self.conn.close()