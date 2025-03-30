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
        
        # Mesajlar tablosu (ileride kullanılmak üzere)
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesajlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gonderen_id INTEGER NOT NULL,
            alici_id INTEGER NOT NULL,
            ilan_id INTEGER NOT NULL,
            mesaj TEXT NOT NULL,
            okundu BOOLEAN DEFAULT 0,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(gonderen_id) REFERENCES users(id),
            FOREIGN KEY(alici_id) REFERENCES users(id),
            FOREIGN KEY(ilan_id) REFERENCES ilanlar(id)
        )
        ''')
        
        self.conn.commit()        
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
                # Cinsiyet filtresi (boş değilse ve 'farketmez' değilse)
                if filters.get('cinsiyet') and filters['cinsiyet'].lower() != 'farketmez':
                    conditions.append("cinsiyet = ?")
                    params.append(filters['cinsiyet'])
                
                # Fiyat aralığı (sadece sayısal değerler için)
                try:
                    if filters.get('min_fiyat'):
                        conditions.append("fiyat >= ?")
                        params.append(float(filters['min_fiyat']))
                    if filters.get('max_fiyat'):
                        conditions.append("fiyat <= ?")
                        params.append(float(filters['max_fiyat']))
                except (ValueError, TypeError):
                    pass  # Geçersiz fiyat değerlerini görmezden gel
                
                # Diğer filtreler (sigara, alkol, evcil_hayvan)
                for key in ['sigara', 'alkol', 'evcil_hayvan']:
                    if key in filters and filters[key] in [True, False, 1, 0, '1', '0']:
                        conditions.append(f"{key} = ?")
                        params.append(1 if str(filters[key]) in ['1', 'True', True] else 0)
                
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY tarih DESC"  # Veya "id DESC"
            print("DEBUG SQL:", query, params)  # Hata ayıklama için
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
    # Yeni metodlar
    def begeni_ekle(self, ilan_id, gonderen_id, tip):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO begeniler (ilan_id, gonderen_id, tip)
                VALUES (?, ?, ?)
            ''', (ilan_id, gonderen_id, tip))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("Beğeni ekleme hatası:", e)
            return None

    def get_begeniler(self, ilan_id=None, kullanici_id=None):
        try:
            cursor = self.conn.cursor()
            query = '''
                SELECT b.*, u.username, i.baslik as ilan_baslik 
                FROM begeniler b
                JOIN users u ON b.gonderen_id = u.id
                JOIN ilanlar i ON b.ilan_id = i.id
            '''
            params = []
            
            conditions = []
            if ilan_id:
                conditions.append("b.ilan_id = ?")
                params.append(ilan_id)
            if kullanici_id:
                conditions.append("i.user_id = ?")
                params.append(kullanici_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY b.tip DESC, b.tarih DESC"  # Kahve önce, çay sonra
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print("Beğeni getirme hatası:", e)
            return []
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