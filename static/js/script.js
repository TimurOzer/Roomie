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
// Beğeni butonları için AJAX
document.querySelectorAll('.aksiyon-btn').forEach(btn => {
    btn.addEventListener('click', function() {
        const card = this.closest('.ilan-karti');
        const ilanId = card.dataset.ilanId;
        let tip = '';
        
        if (this.classList.contains('begenme-btn')) {
            return; // Çarpı butonu için işlem yapma
        } else if (this.classList.contains('cay-btn')) {
            tip = 'cay';
        } else if (this.classList.contains('kahve-btn')) {
            tip = 'kahve';
        }
        
        fetch('/begeni', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
            },
            body: `ilan_id=${ilanId}&tip=${tip}`
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Başarılı olduğunda buton rengini değiştir
                this.style.backgroundColor = tip === 'cay' ? '#e8f5e9' : '#fff3e0';
                this.style.fontWeight = 'bold';
            } else {
                alert('Beğeni gönderilemedi: ' + (data.error || 'Bilinmeyen hata'));
            }
        })
        .catch(error => {
            console.error('Hata:', error);
            alert('Bir hata oluştu');
        });
    });
});