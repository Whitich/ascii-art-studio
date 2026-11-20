# ASCII Art Studio

**Turn an image into editable character art — entirely on your desktop.**

Türkçe arayüzlü, çevrimdışı ASCII/ANSI sanat stüdyosu.

![Örnek kaynak görsel](docs/sample.png)

## Öne çıkanlar

- **Tek tık stiller:** Terminal, Piksel afiş, Mürekkep ve Renkli portre; her stilin ayarlarını ayrıca değiştirebilirsiniz.
- **Taşınabilir proje:** Dosya → Proje Kaydet, kaynak görseli ve ayarları tek `.asciiproject` dosyasına gömer. Başka klasöre taşısanız da projeyi yeniden açabilirsiniz.
- **Altı çıktı yolu:** TXT, ANSI, PNG, HTML, SVG ve sade metin panosu. SVG, Dosya menüsündedir; metin tabanlı SVG görünümü kullanılan monospace yazı tipine bağlıdır.
- **Yerel çalışma:** Görseller yüklenmez; hesap veya sunucu gerekmez.
- **Renk tutarlılığı:** ANSI 16/256/TrueColor paleti renkli önizleme, PNG, HTML ve SVG'de kullanılır.

Proje dosyası kaynak görseli içerir; paylaşırken görselin de paylaşıldığını unutmayın.

## Windows indir

[Kurulum EXE ve taşınabilir ZIP](https://github.com/Whitich/ascii-art-studio/releases/latest) — Python kurulumu gerekmez. Windows x64 içindir. Dosyalar kod imzalı değildir; Windows bilinmeyen yayıncı uyarısı gösterebilir.

Önizleme üzerindeki − / 100% / + düğmeleri yakınlığı değiştirir; dışa aktarma boyutu etkilenmez. Bir görseli veya .asciiproject dosyasını EXE üzerine bırakarak da açabilirsiniz.

## Kaynak koddan başlatma

Python 3.12+ ve Pillow 13 gerekir:

```powershell
python -m pip install -r requirements.txt
python ascii_art_studio.py
```

`Start.bat` aynı klasörden başlatır. Mevcut Python kurulumu veya `.venv` kullanılabilir.

## Özellikler

- Kaydırılabilir ayar paneli, kaynak görsel ve ASCII sekmeleri.
- Arka planda dönüşüm; eski işlem sonuçları yeni ayarların üzerine yazılmaz.
- Hazır/özel karakter seti, ters çevirme, dither, parlaklık ve kontrast.
- TXT, ANSI 16/256/TrueColor, renkli PNG ve bağımsız HTML çıktısı.
- Panoya sade metin kopyalama; Ctrl+O açma, Ctrl+S PNG kaydı.
- EXIF yön düzeltmesi, saydam görsellerin siyah zemine birleştirilmesi.
- Ayarlar kullanıcı dizininde saklanır; eski yan dosyadan tercihler okunabilir.

## Sınırlar

Animasyonlu görsellerin ilk karesi kullanılır. Çıktı 250.000 karakterle ve PNG 40 megapikselle sınırlıdır. Büyük çıktılarda çizim/dışa aktarma zaman alabilir. Blok karakterlerin görünümü kurulu yazı tipine bağlıdır. PNG ve HTML seçilen renk paletini kullanır; yeşil metin görünümü ayrı bir okunabilirlik önizlemesidir. Görseller hiçbir sunucuya yüklenmez.

## Test

```powershell
python -m unittest discover -s tests -v
```
