# TranskriptOS

Videolardan **Türkçe ve İngilizce transkript** çıkaran basit araçlar. Bilgisayarda çalan sesi canlı olarak dinleyip anlık not alabilir ya da kayıtlı bir video dosyasını veya YouTube linkini yazıya dökebilir.

Tamamen yerelde çalışır. Ses hiçbir sunucuya gönderilmez, API anahtarı gerekmez. Arka planda OpenAI'ın açık kaynaklı Whisper modeli ([faster-whisper](https://github.com/SYSTRAN/faster-whisper)) kullanılır.

## Özellikler

- **Canlı mod:** Video, ders ya da toplantı izlerken sistem sesini dinler ve konuşmayı birkaç saniye gecikmeyle zaman damgalı olarak yazar.
- **Mikrofon modu:** Yüz yüze dersler ve toplantılar için.
- **Dosya / link modu:** `.mp4`, `.mkv`, `.mp3` gibi dosyalardan veya YouTube linklerinden `.txt` ve `.srt` (altyazı) üretir.
- **Çok dilli:** Varsayılan Türkçe'dir; `--dil en` ile İngilizce, diğer Whisper dil kodlarıyla (`de`, `fr`, `es`...) başka diller.
- **Tek tıkla kurulum (Windows):** Python yoksa kendisi kurar.
- GPU varsa otomatik olarak kullanır, yoksa CPU'da çalışır.

## Hızlı başlangıç (Windows)

1. Repoyu indir: **Code → Download ZIP**, sonra ZIP'i bir klasöre çıkar.
2. `BASLAT.bat` dosyasına çift tıkla.
   - İlk açılışta Python, gerekli paketler ve model otomatik kurulur. Bu birkaç dakika sürebilir.
3. Ekranda "Dinleniyor" yazınca videoyu oynat.
4. Bitirmek için `Ctrl + C`'ye bas. Notlar `notlar/` klasörüne kaydedilir.

Mikrofonu dinlemek için `MIKROFON_ILE_BASLAT.bat` dosyasını kullan.

## Manuel kurulum (Windows / macOS / Linux)

Python 3.10–3.13 ve [ffmpeg](https://ffmpeg.org/) gerekir. ffmpeg yalnızca dosya/link modu için lazım.

```bash
pip install faster-whisper soundcard "numpy<2" "av<14" yt-dlp
```

### Canlı transkript

```bash
python canli_transkript.py                 # sistem sesini dinler (Türkçe)
python canli_transkript.py --dil en        # İngilizce dinler
python canli_transkript.py --mikrofon      # mikrofonu dinler
python canli_transkript.py --model base    # zayıf bilgisayarlar için daha hızlı
python canli_transkript.py --esik 0.002    # ses kısıkken kelime kaçıyorsa
python canli_transkript.py --listele       # ses cihazlarını listeler
```

Örnek çıktı (`notlar/not_2026-11-03_22-05.txt`):

```
[00:00:04] Bugün sizlere yapay zekânın temellerinden bahsedeceğim.
[00:00:11] İlk olarak makine öğrenmesi nedir ona bakalım.
```

> **macOS:** Sistem sesini yakalamak için [BlackHole](https://github.com/ExistentialAudio/BlackHole) kur ve `--cihaz BlackHole` ile çalıştır.

### Dosyadan / linkten transkript

```bash
python transkript.py video.mp4                     # Türkçe (varsayılan)
python transkript.py video.mp4 --dil en            # İngilizce
python transkript.py "https://www.youtube.com/watch?v=..."
python transkript.py videolar/                     # klasördeki tüm dosyalar
python transkript.py video.mp4 --model large-v3    # en yüksek doğruluk
```

Çıktılar `transkriptler/` klasörüne `.txt` ve `.srt` olarak kaydedilir.

## Dil seçimi

Varsayılan dil Türkçe'dir. Başka bir dil için `--dil` parametresini kullan:

```bash
python transkript.py video.mp4 --dil en        # İngilizce
python canli_transkript.py --dil en            # İngilizce (canlı)
python transkript.py video.mp4 --dil de        # Almanca, vb.
```

İngilizce seçildiğinde küçük modeller (`tiny`, `base`, `small`, `medium`) otomatik olarak İngilizceye özel ve daha doğru olan `.en` sürümüne geçer (ör. `small` → `small.en`). `large-v3` ve `large-v3-turbo` zaten çok dillidir, olduğu gibi kullanılır.

## Model seçimi

| Model | Hız | Doğruluk | Ne zaman |
|---|---|---|---|
| `tiny` / `base` | Çok hızlı | Düşük | Çok zayıf bilgisayarlar |
| `small` | Hızlı | Orta | CPU'da canlı mod (varsayılan) |
| `medium` | Orta | İyi | Güçlü CPU |
| `large-v3-turbo` | Hızlı (GPU) | Çok iyi | GPU varsa canlı mod (varsayılan), dosya modu |
| `large-v3` | Yavaş | En iyi | Doğruluğun her şeyden önemli olduğu durumlar |

Modeller ilk kullanımda otomatik indirilir.

## Sorun giderme

- **`fromstring` hatası:** `pip install "numpy<2"` komutunu çalıştır.
- **`open() got an unexpected keyword argument 'metadata_errors'` hatası:** PyAV sürümü çok yeni. `pip install "av<14"` komutunu çalıştır.
- **Hiçbir şey yazılmıyor:** Sesin açık olduğundan emin ol, `--esik 0.002` ile dene.
- **"Bilgisayar geride kalıyor" uyarısı:** `--model base` veya `--model tiny` kullan.

## Lisans

[MIT](LICENSE)
