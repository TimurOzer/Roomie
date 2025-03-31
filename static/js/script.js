document.addEventListener('DOMContentLoaded', function() {
    // İletişim bilgilerini göster/gizle
    const iletisimBtn = document.querySelector('.iletisim-btn');
    if (iletisimBtn) {
        iletisimBtn.addEventListener('click', function() {
            const bilgiler = document.querySelector('.iletisim-bilgileri');
            if (bilgiler.style.display === 'none' || !bilgiler.style.display) {
                bilgiler.style.display = 'block';
                this.textContent = 'İletişim Bilgilerini Gizle';
            } else {
                bilgiler.style.display = 'none';
                this.textContent = 'İletişim Bilgilerini Göster';
            }
        });
    }
    
    // Dosya yükleme uyarısı
    const fileInput = document.getElementById('resimler');
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            const files = this.files;
            if (files.length > 5) {
                alert('En fazla 5 resim yükleyebilirsiniz!');
                this.value = '';
            }
        });
    }
    
    // Flash mesajlarını otomatik kapatma
    const flashMessages = document.querySelectorAll('.flash');
    flashMessages.forEach(msg => {
        setTimeout(() => {
            msg.style.opacity = '0';
            setTimeout(() => msg.remove(), 500);
        }, 5000);
    });
});

// Beğenme butonları için etkileşim
// Mesaj istekleri sayfası işlemleri
document.querySelectorAll('.istek-kabul-btn, .istek-red-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const form = this.closest('.istek-kabul-form');
        const istekId = form.dataset.istekId;
        const islem = this.classList.contains('istek-kabul-btn') ? 'kabul' : 'red';
        
        fetch('/mesaj_istek_islem', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: `istek_id=${istekId}&islem=${islem}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload(); // Sayfayı yenile
            } else {
                alert('İşlem yapılamadı: ' + (data.error || 'Bilinmeyen hata'));
            }
        })
        .catch(error => {
            console.error('Hata:', error);
            alert('Bir hata oluştu');
        });
    });
});

// Mesaj gönderme formu
document.querySelector('.mesaj-gonder-form')?.addEventListener('submit', function(e) {
    e.preventDefault();
    const odaId = this.dataset.odaId;
    const mesaj = this.mesaj.value.trim();
    
    if (!mesaj) return;
    
    fetch('/mesaj_gonder', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: `oda_id=${odaId}&mesaj=${encodeURIComponent(mesaj)}`
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            this.mesaj.value = '';
            // Mesajı ekrana ekle veya sayfayı yenile
            location.reload(); // Basitçe sayfayı yenileyelim
        } else {
            alert('Mesaj gönderilemedi: ' + (data.error || 'Bilinmeyen hata'));
        }
    })
    .catch(error => {
        console.error('Hata:', error);
        alert('Bir hata oluştu');
    });
});

// Çay/Kahve gönderme butonları için event listener
document.addEventListener('click', function(e) {
    // Çay veya kahve butonuna tıklanıp tıklanmadığını kontrol et
    if (e.target.classList.contains('cay-btn') || e.target.classList.contains('kahve-btn')) {
        const btn = e.target;
        const card = btn.closest('.ilan-karti');
        
        if (!card) {
            console.error('İlan kartı bulunamadı');
            return;
        }
        
        const ilanId = card.dataset.ilanId;
        const tip = btn.dataset.tip || 
                   (btn.classList.contains('cay-btn') ? 'cay' : 'kahve');
        
        // CSRF token'ını güvenli şekilde al
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value || 
                         document.querySelector('meta[name="csrf-token"]')?.content;
        
        if (!csrfToken) {
            console.error('CSRF token bulunamadı');
            alert('Güvenlik hatası: CSRF token eksik');
            return;
        }
        
        if (!ilanId) {
            console.error('İlan ID bulunamadı');
            return;
        }
        
        console.log('Gönderiliyor:', { ilanId, tip, csrfToken });
        
        fetch('/begeni', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `ilan_id=${ilanId}&tip=${tip}`
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Buton görünümünü güncelle
                btn.style.backgroundColor = tip === 'cay' ? '#e8f5e9' : '#fff3e0';
                btn.style.fontWeight = 'bold';
                btn.disabled = true;
                
                // Kullanıcıya bilgi ver
                alert(`${tip === 'cay' ? 'Çay' : 'Kahve'} gönderildi! İlan sahibi mesajınızı onayladığında bildirim alacaksınız.`);
                
                // İsteğe bağlı: İlan kartını gri yap
                card.style.opacity = '0.6';
            } else {
                alert('Hata: ' + (data.error || 'Bilinmeyen hata'));
            }
        })
        .catch(error => {
            console.error('Fetch error:', error);
            alert('İşlem sırasında hata oluştu: ' + error.message);
        });
    }
});

// Mesaj istekleri sayfası işlemleri - GÜNCELLENMİŞ VERSİYON
document.querySelectorAll('.istek-kabul-btn, .istek-red-btn').forEach(btn => {
    btn.addEventListener('click', function(e) {
        e.preventDefault();
        const form = this.closest('.istek-islem-form');
        const istekId = form.dataset.istekId;
        const islem = this.dataset.islem; // 'kabul' veya 'red'
        const csrfToken = form.querySelector('input[name="csrf_token"]').value;

        fetch("{{ url_for('mesaj_istek_islem') }}", {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': csrfToken
            },
            body: `istek_id=${istekId}&islem=${islem}&csrf_token=${csrfToken}`
        })
        .then(response => {
            if (!response.ok) throw new Error('Network error');
            return response.json();
        })
        .then(data => {
            if (data.success) {
                const istekKarti = form.closest('.istek-karti');
                if (islem === 'kabul') {
                    istekKarti.innerHTML = `
                        <div class="alert alert-success">
                            İstek kabul edildi. Yönlendiriliyorsunuz...
                        </div>
                    `;
                    // 2 saniye sonra mesajlaşma sayfasına yönlendir
                    setTimeout(() => {
                        window.location.href = "{{ url_for('mesajlar') }}";
                    }, 2000);
                } else {
                    istekKarti.style.opacity = '0.5';
                    form.innerHTML = '<div class="alert alert-warning">İstek reddedildi</div>';
                }
            } else {
                alert('Hata: ' + (data.error || 'Bilinmeyen hata'));
            }
        })
        .catch(error => {
            console.error('Hata:', error);
            alert('İşlem sırasında hata oluştu');
        });
    });
});