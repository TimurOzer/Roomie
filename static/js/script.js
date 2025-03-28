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