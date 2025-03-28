import sqlite3
import os

class Database:
    def __init__(self, db_name='ev_arkadasi.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Kullanıcılar tablosu (yorum satırları kaldırıldı)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # İlanlar tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ilanlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            aciklama TEXT NOT NULL,
            fiyat REAL NOT NULL,
            konum TEXT NOT NULL,
            cinsiyet TEXT NOT NULL,
            oda_sayisi TEXT NOT NULL,
            sigara BOOLEAN DEFAULT 0,
            alkol BOOLEAN DEFAULT 0,
            evcil_hayvan BOOLEAN DEFAULT 0,
            resimler TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_id INTEGER,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        ''')
        
        self.conn.commit()

    # İLAN İŞLEMLERİ
    def ilan_ekle(self, user_id, baslik, aciklama, fiyat, konum, cinsiyet, 
                 oda_sayisi, sigara=False, alkol=False, evcil_hayvan=False, resimler=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO ilanlar 
                (user_id, baslik, aciklama, fiyat, konum, cinsiyet, oda_sayisi, 
                 sigara, alkol, evcil_hayvan, resimler)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, baslik, aciklama, fiyat, konum, cinsiyet, oda_sayisi,
                  sigara, alkol, evcil_hayvan, resimler))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("İlan ekleme hatası:", e)
            return None

    def get_ilanlar(self, filters=None):
        try:
            cursor = self.conn.cursor()
            query = "SELECT * FROM ilanlar"
            params = []
            
            if filters:
                conditions = []
                for key, value in filters.items():
                    if key == 'min_fiyat':
                        conditions.append("fiyat >= ?")
                        params.append(value)
                    elif key == 'max_fiyat':
                        conditions.append("fiyat <= ?")
                        params.append(value)
                    elif key == 'cinsiyet' and value != 'farketmez':
                        conditions.append("cinsiyet = ?")
                        params.append(value)
                    elif key in ['sigara', 'alkol', 'evcil_hayvan']:
                        conditions.append(f"{key} = ?")
                        params.append(1 if value else 0)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY tarih DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print("İlan getirme hatası:", e)
            return []

    def get_ilan(self, ilan_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT i.*, u.username, u.email, u.phone 
                FROM ilanlar i
                LEFT JOIN users u ON i.user_id = u.id
                WHERE i.id = ?
            ''', (ilan_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            print("İlan detay hatası:", e)
            return None

    # KULLANICI İŞLEMLERİ (TEK BİR TANE OLMALI!)
    def user_ekle(self, username, password, email, phone=None):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO users (username, password, email, phone)
                VALUES (?, ?, ?, ?)
            ''', (username, password, email, phone))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None

    def get_user(self, username):
        try:
            cursor = self.conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            return cursor.fetchone()
        except sqlite3.Error:
            return None
            
    # DİĞER METODLAR
    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def __del__(self):
        self.close()

# Test için
if __name__ == '__main__':
    db = Database('test.db')
    
    # Test verileri ekle
    user_id = db.user_ekle('testuser', 'testpass', 'test@example.com')
    ilan_id = db.ilan_ekle(user_id, 'Test İlan', 'Açıklama', 1000, 'İstanbul', 
                          'farketmez', '2+1', False, False, True)
    
    print("Tüm ilanlar:", db.get_ilanlar())
    print("Tek ilan:", db.get_ilan(ilan_id))
    print("Kullanıcı:", db.get_user('testuser'))