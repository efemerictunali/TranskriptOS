#!/usr/bin/env python3
"""
Türkçe Video Transkript Aracı
-----------------------------
Yerel video/ses dosyalarından veya YouTube (ve yt-dlp'nin desteklediği diğer
siteler) linklerinden Türkçe transkript çıkarır. Çıktı: .txt + .srt (altyazı)

Kurulum (bir kere):
    pip install faster-whisper yt-dlp
    # ffmpeg de gerekli:
    #   Windows: winget install ffmpeg
    #   macOS:   brew install ffmpeg
    #   Linux:   sudo apt install ffmpeg

Kullanım:
    python transkript.py video.mp4
    python transkript.py "https://www.youtube.com/watch?v=XXXX"
    python transkript.py klasor/                 # klasördeki tüm videolar
    python transkript.py video.mp4 --model large-v3   # en yüksek doğruluk
    python transkript.py video.mp4 --model small      # hızlı/zayıf bilgisayar
"""

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

MEDYA_UZANTILARI = {".mp4", ".mkv", ".mov", ".avi", ".webm", ".flv",
                    ".mp3", ".wav", ".m4a", ".ogg", ".flac", ".aac"}

# Her dil için Whisper'a verilen ipucu cümlesi (noktalama/doğruluk artırır).
DIL_IPUCU = {
    "tr": "Merhaba, bu bir Türkçe konuşmadır. Noktalama işaretlerine dikkat edilmiştir.",
    "en": "Hello, this is English speech. Punctuation has been applied carefully.",
}

# Bu boyutların İngilizceye özel (.en) sürümü, İngilizcede daha doğru ve hızlıdır.
EN_MODELLER = {"tiny", "base", "small", "medium"}


def model_adini_coz(model_adi: str, dil: str) -> str:
    """Dil İngilizce ve model küçük bir boyutsa .en sürümünü kullanır."""
    if dil == "en" and model_adi in EN_MODELLER:
        return model_adi + ".en"
    return model_adi


def zaman_srt(saniye: float) -> str:
    ms = int(round(saniye * 1000))
    s, ms = divmod(ms, 1000)
    d, s = divmod(s, 60)
    sa, d = divmod(d, 60)
    return f"{sa:02}:{d:02}:{s:02},{ms:03}"


def linkten_indir(url: str, hedef_klasor: str) -> Path:
    """yt-dlp ile sadece sesi indirir."""
    print(f"⬇️  İndiriliyor: {url}")
    sablon = os.path.join(hedef_klasor, "%(title).80s.%(ext)s")
    subprocess.run(
        ["yt-dlp", "-f", "bestaudio/best", "-x", "--audio-format", "m4a",
         "-o", sablon, url],
        check=True,
    )
    dosyalar = sorted(Path(hedef_klasor).glob("*"), key=os.path.getmtime)
    if not dosyalar:
        sys.exit("İndirme başarısız oldu.")
    return dosyalar[-1]


def model_yukle(model_adi: str, dil: str = "tr"):
    from faster_whisper import WhisperModel
    try:
        import torch  # noqa: F401
        gpu = torch.cuda.is_available()
    except ImportError:
        gpu = False
    model_adi = model_adini_coz(model_adi, dil)
    cihaz, tip = ("cuda", "float16") if gpu else ("cpu", "int8")
    print(f"🧠 Model yükleniyor: {model_adi} ({cihaz})")
    return WhisperModel(model_adi, device=cihaz, compute_type=tip)


def transkript_cikar(model, dosya: Path, cikti_klasoru: Path, dil: str = "tr"):
    print(f"🎙️  Transkript çıkarılıyor ({dil}): {dosya.name}")
    segmentler, bilgi = model.transcribe(
        str(dosya),
        language=dil,
        vad_filter=True,          # sessiz kısımları atlar, halüsinasyonu azaltır
        beam_size=5,
        initial_prompt=DIL_IPUCU.get(dil, ""),
    )

    cikti_klasoru.mkdir(parents=True, exist_ok=True)
    txt_yol = cikti_klasoru / f"{dosya.stem}.txt"
    srt_yol = cikti_klasoru / f"{dosya.stem}.srt"

    toplam = bilgi.duration or 1
    with open(txt_yol, "w", encoding="utf-8") as txt, \
         open(srt_yol, "w", encoding="utf-8") as srt:
        for i, seg in enumerate(segmentler, 1):
            metin = seg.text.strip()
            txt.write(metin + "\n")
            srt.write(f"{i}\n{zaman_srt(seg.start)} --> {zaman_srt(seg.end)}\n{metin}\n\n")
            yuzde = min(100, seg.end / toplam * 100)
            print(f"\r   %{yuzde:5.1f}", end="", flush=True)
    print(f"\n✅ Kaydedildi:\n   {txt_yol}\n   {srt_yol}")


def main():
    p = argparse.ArgumentParser(description="Videolardan Türkçe transkript çıkarır.")
    p.add_argument("girdi", help="Video dosyası, klasör veya URL")
    p.add_argument("--model", default="large-v3-turbo",
                   help="tiny | base | small | medium | large-v3 | large-v3-turbo (varsayılan)")
    p.add_argument("--dil", default="tr",
                   help="Konuşma dili: tr (Türkçe, varsayılan) | en (İngilizce) | diğer Whisper dil kodları")
    p.add_argument("--cikti", default="transkriptler", help="Çıktı klasörü")
    a = p.parse_args()

    cikti = Path(a.cikti)
    model = model_yukle(a.model, a.dil)

    if a.girdi.startswith(("http://", "https://")):
        with tempfile.TemporaryDirectory() as tmp:
            dosya = linkten_indir(a.girdi, tmp)
            transkript_cikar(model, dosya, cikti, a.dil)
        return

    yol = Path(a.girdi)
    if yol.is_dir():
        dosyalar = [f for f in sorted(yol.iterdir()) if f.suffix.lower() in MEDYA_UZANTILARI]
        if not dosyalar:
            sys.exit("Klasörde video/ses dosyası bulunamadı.")
        for f in dosyalar:
            transkript_cikar(model, f, cikti, a.dil)
    elif yol.is_file():
        transkript_cikar(model, yol, cikti, a.dil)
    else:
        sys.exit(f"Bulunamadı: {a.girdi}")


if __name__ == "__main__":
    main()
