import sqlite3
import os

class Database:
    def __init__(self, db_name='ev_arkadasi.db'):
        self.db_path = os.path.join(os.path.dirname(__file__), db_name)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
        self.upgrade_database()  # Bu satırı ekleyin
        
    def _create_tables(self):
        cursor = self.conn.cursor()
        
        # Kullanıcılar tablosu
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
        
        # database.py'de _create_tables fonksiyonunu güncelleyin
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesaj_istekleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            gonderen_id INTEGER NOT NULL,
            alici_id INTEGER NOT NULL,
            ilan_id INTEGER NOT NULL,
            tip TEXT NOT NULL,  -- 'cay' veya 'kahve'
            durum TEXT NOT NULL DEFAULT 'beklemede',  -- 'beklemede', 'kabul', 'red'
            oda_id INTEGER,  -- Yeni eklenen sütun
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(gonderen_id) REFERENCES users(id),
            FOREIGN KEY(alici_id) REFERENCES users(id),
            FOREIGN KEY(ilan_id) REFERENCES ilanlar(id),
            FOREIGN KEY(oda_id) REFERENCES mesaj_odalari(id),
            UNIQUE(gonderen_id, alici_id, ilan_id)
        )
        ''')
        
        # Mesajlaşma odaları tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesaj_odalari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ilan_id INTEGER NOT NULL,
            kullanici1_id INTEGER NOT NULL,
            kullanici2_id INTEGER NOT NULL,
            olusturulma_tarihi TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(ilan_id) REFERENCES ilanlar(id),
            FOREIGN KEY(kullanici1_id) REFERENCES users(id),
            FOREIGN KEY(kullanici2_id) REFERENCES users(id),
            UNIQUE(kullanici1_id, kullanici2_id, ilan_id)
        )
        ''')
        
        # Mesajlar tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS mesajlar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            oda_id INTEGER NOT NULL,
            gonderen_id INTEGER NOT NULL,
            mesaj TEXT NOT NULL,
            okundu BOOLEAN DEFAULT 0,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(oda_id) REFERENCES mesaj_odalari(id),
            FOREIGN KEY(gonderen_id) REFERENCES users(id)
        )
        ''')
        # Beğeniler tablosu
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS begeniler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ilan_id INTEGER NOT NULL,
            gonderen_id INTEGER NOT NULL,
            tip TEXT NOT NULL,  -- 'cay' veya 'kahve'
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(ilan_id) REFERENCES ilanlar(id),
            FOREIGN KEY(gonderen_id) REFERENCES users(id),
            UNIQUE(ilan_id, gonderen_id)  -- Bir kullanıcı bir ilana sadece bir kez beğeni gönderebilir
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
                if filters.get('cinsiyet') and filters['cinsiyet'].lower() != 'farketmez':
                    conditions.append("cinsiyet = ?")
                    params.append(filters['cinsiyet'])
                
                try:
                    if filters.get('min_fiyat'):
                        conditions.append("fiyat >= ?")
                        params.append(float(filters['min_fiyat']))
                    if filters.get('max_fiyat'):
                        conditions.append("fiyat <= ?")
                        params.append(float(filters['max_fiyat']))
                except (ValueError, TypeError):
                    pass
                
                for key in ['sigara', 'alkol', 'evcil_hayvan']:
                    if key in filters and filters[key] in [True, False, 1, 0, '1', '0']:
                        conditions.append(f"{key} = ?")
                        params.append(1 if str(filters[key]) in ['1', 'True', True] else 0)
                
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

    # BEGENI İŞLEMLERİ
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

    def get_begeniler(self, ilan_id=None, kullanici_id=None, is_ev_sahibi=False):
        try:
            cursor = self.conn.cursor()
            query = '''
                SELECT b.*, u.username, i.baslik as ilan_baslik,
                       mi.durum as istek_durumu
                FROM begeniler b
                JOIN users u ON b.gonderen_id = u.id
                JOIN ilanlar i ON b.ilan_id = i.id
                LEFT JOIN mesaj_istekleri mi ON 
                    mi.ilan_id = b.ilan_id AND 
                    mi.gonderen_id = b.gonderen_id
            '''
            params = []
            
            conditions = []
            if ilan_id:
                conditions.append("b.ilan_id = ?")
                params.append(ilan_id)
            
            if kullanici_id:
                if is_ev_sahibi:
                    conditions.append("i.user_id = ?")  # Ev sahibinin ilanları
                else:
                    conditions.append("b.gonderen_id = ?")  # Gönderenin beğenileri
                params.append(kullanici_id)
            
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY b.tarih DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print("Beğeni getirme hatası:", e)
            return []

    # MESAJ İSTEKLERİ
    def mesaj_istegi_ekle(self, gonderen_id, alici_id, ilan_id, tip):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO mesaj_istekleri (gonderen_id, alici_id, ilan_id, tip)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(gonderen_id, alici_id, ilan_id) DO UPDATE SET
                tip = excluded.tip,
                durum = CASE WHEN durum = 'red' THEN 'beklemede' ELSE durum END
            ''', (gonderen_id, alici_id, ilan_id, tip))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("Mesaj isteği ekleme hatası:", e)
            return None

    def mesaj_istegi_guncelle(self, istek_id, durum):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                UPDATE mesaj_istekleri SET durum = ? WHERE id = ?
            ''', (durum, istek_id))
            self.conn.commit()
            print(f"Güncellenen istek: {istek_id}, yeni durum: {durum}")
            return cursor.rowcount
        except sqlite3.Error as e:
            print("Mesaj isteği güncelleme hatası:", e)
            return 0
            
    def get_mesaj_istegi(self, istek_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT mi.*, u.username as gonderen_username, i.baslik as ilan_baslik
            FROM mesaj_istekleri mi
            JOIN users u ON mi.gonderen_id = u.id
            JOIN ilanlar i ON mi.ilan_id = i.id
            WHERE mi.id = ?
        ''', (istek_id,))
        return cursor.fetchone()
    def get_user_by_id(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        return cursor.fetchone()
    def get_mesaj_istekleri(self, kullanici_id, durum=None):
        try:
            cursor = self.conn.cursor()
            query = '''
                SELECT mi.*, u.username as gonderen_username, 
                       i.baslik as ilan_baslik, mo.id as oda_id
                FROM mesaj_istekleri mi
                JOIN users u ON mi.gonderen_id = u.id
                JOIN ilanlar i ON mi.ilan_id = i.id
                LEFT JOIN mesaj_odalari mo ON mi.oda_id = mo.id
                WHERE mi.alici_id = ?
            '''
            params = [kullanici_id]
            
            if durum:
                query += " AND mi.durum = ?"
                params.append(durum)
            
            query += " ORDER BY mi.tarih DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print("Mesaj istekleri getirme hatası:", e)
            return []

    # MESAJ ODALARI
    def mesaj_odasi_olustur(self, ilan_id, kullanici1_id, kullanici2_id):
        try:
            # Önce var olan odayı kontrol et
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT id FROM mesaj_odalari 
                WHERE ilan_id = ? AND 
                ((kullanici1_id = ? AND kullanici2_id = ?) OR 
                (kullanici1_id = ? AND kullanici2_id = ?))
            ''', (ilan_id, kullanici1_id, kullanici2_id, kullanici2_id, kullanici1_id))
            
            existing = cursor.fetchone()
            if existing:
                return existing['id']  # Var olan oda ID'sini döndür
            
            # Yeni oda oluştur
            cursor.execute('''
                INSERT INTO mesaj_odalari (ilan_id, kullanici1_id, kullanici2_id)
                VALUES (?, ?, ?)
            ''', (ilan_id, kullanici1_id, kullanici2_id))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("Mesaj odası oluşturma hatası:", e)
            return None

    def get_mesaj_odasi(self, oda_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM mesaj_odalari WHERE id = ?
        ''', (oda_id,))
        return cursor.fetchone()

    # MESAJLAR
    def mesaj_ekle(self, oda_id, gonderen_id, mesaj):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                INSERT INTO mesajlar (oda_id, gonderen_id, mesaj)
                VALUES (?, ?, ?)
            ''', (oda_id, gonderen_id, mesaj))
            self.conn.commit()
            return cursor.lastrowid
        except sqlite3.Error as e:
            print("Mesaj ekleme hatası:", e)
            return None

    def get_mesajlar(self, oda_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute('''
                SELECT m.*, u.username
                FROM mesajlar m
                JOIN users u ON m.gonderen_id = u.id
                WHERE m.oda_id = ?
                ORDER BY m.tarih ASC
            ''', (oda_id,))
            return [dict(row) for row in cursor.fetchall()]
        except sqlite3.Error as e:
            print("Mesajlar getirme hatası:", e)
            return []

    # KULLANICI İŞLEMLERİ
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
    def execute(self, query, params=()):
        try:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            return cursor
        except sqlite3.Error as e:
            print("SQL execute hatası:", e)
            return None
    # Database sınıfına ekleyin
    def get_mesaj_odasi_by_users(self, ilan_id, user1_id, user2_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT id FROM mesaj_odalari 
            WHERE ilan_id = ? AND 
            ((kullanici1_id = ? AND kullanici2_id = ?) OR 
            (kullanici1_id = ? AND kullanici2_id = ?))
        ''', (ilan_id, user1_id, user2_id, user2_id, user1_id))
        return cursor.fetchone()
    def upgrade_database(self):
        try:
            cursor = self.conn.cursor()
            # Tabloda oda_id sütunu var mı kontrol et
            cursor.execute("PRAGMA table_info(mesaj_istekleri)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'oda_id' not in columns:
                cursor.execute('ALTER TABLE mesaj_istekleri ADD COLUMN oda_id INTEGER REFERENCES mesaj_odalari(id)')
                self.conn.commit()
                print("Veritabanı şeması güncellendi: oda_id eklendi")
        except sqlite3.Error as e:
            print("Veritabanı güncelleme hatası:", e)  
    # database.py'ye bu fonksiyonu ekleyin ve çağırın
    def debug_mesaj_odalari(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM mesaj_odalari")
        return cursor.fetchall()          
    # DİĞER METODLAR
    def get_mesaj_istekleri_for_room(self, oda_id):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM mesaj_istekleri WHERE oda_id = ?
        ''', (oda_id,))
        return [dict(row) for row in cursor.fetchall()]
    def onar_mesaj_odalari(self):
        try:
            cursor = self.conn.cursor()
            # Eksik oda_id'leri olan istekleri bul
            cursor.execute("""
                SELECT mi.id, mi.gonderen_id, mi.alici_id, mi.ilan_id
                FROM mesaj_istekleri mi
                WHERE mi.durum = 'kabul' AND mi.oda_id IS NULL
            """)
            eksikler = cursor.fetchall()
            
            for eksik in eksikler:
                # Önce var olan bir oda olup olmadığını kontrol et
                oda = self.get_mesaj_odasi_by_users(eksik['ilan_id'], eksik['gonderen_id'], eksik['alici_id'])
                
                if oda:
                    oda_id = oda['id']
                else:
                    # Yeni oda oluştur
                    oda_id = self.mesaj_odasi_olustur(
                        eksik['ilan_id'],
                        eksik['gonderen_id'],
                        eksik['alici_id']
                    )
                
                if oda_id:
                    cursor.execute("""
                        UPDATE mesaj_istekleri SET oda_id = ? WHERE id = ?
                    """, (oda_id, eksik['id']))
            
            self.conn.commit()
        except sqlite3.Error as e:
            print("Mesaj odası onarım hatası:", e)
            self.conn.rollback()
    def close(self):
        if hasattr(self, 'conn') and self.conn:
            self.conn.close()

    def __del__(self):
        self.close()

if __name__ == '__main__':
    db = Database('test.db')
    
    # Test verileri ekle
    user_id = db.user_ekle('testuser', 'testpass', 'test@example.com')
    ilan_id = db.ilan_ekle(user_id, 'Test İlan', 'Açıklama', 1000, 'İstanbul', 
                          'farketmez', '2+1', False, False, True)
    
    print("Tüm ilanlar:", db.get_ilanlar())
    print("Tek ilan:", db.get_ilan(ilan_id))
    print("Kullanıcı:", db.get_user('testuser'))