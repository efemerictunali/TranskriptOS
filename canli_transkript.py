#!/usr/bin/env python3
"""
Canlı Türkçe Transkript (Not Alıcı)
-----------------------------------
Bilgisayarda çalan sesi (YouTube, Zoom, video oynatıcı... ne çalıyorsa)
dinler, Türkçe konuşmayı anlık yazıya döker ve zaman damgalı olarak
notlar/ klasörüne kaydeder. Mikrofon yerine sistem sesini dinler, yani
hoparlörden/kulaklıktan gelen sesi yakalar.

Kurulum (bir kere):
    pip install faster-whisper soundcard numpy

Kullanım:
    python canli_transkript.py                 # sistem sesini dinler
    python canli_transkript.py --mikrofon      # mikrofonu dinler (ders, toplantı)
    python canli_transkript.py --listele       # ses cihazlarını gösterir
    python canli_transkript.py --model small   # zayıf bilgisayar için daha hızlı
Durdurmak için: Ctrl + C

Notlar:
  * Windows ve Linux'ta sistem sesi doğrudan yakalanır.
  * macOS'ta sistem sesi için ücretsiz "BlackHole" sürücüsü kurulmalı, sonra:
        python canli_transkript.py --cihaz BlackHole
"""

import argparse
import datetime
import queue
import sys
import threading
import time
from pathlib import Path

import numpy as np

HEDEF_SR = 16000      # Whisper'ın beklediği örnekleme hızı
KAYIT_SR = 48000      # Kayıt hızı (48k -> 16k'ya 3'e bölerek indiriyoruz)
BLOK_SN = 0.5         # Her okumada alınan ses süresi (saniye)
MIN_PARCA_SN = 3.0    # Bir parçayı en erken bu süreden sonra işle
MAX_PARCA_SN = 12.0   # Sessizlik gelmese de bu sürede mutlaka işle

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def sure_yaz(sn: float) -> str:
    sn = int(sn)
    return f"{sn // 3600:02}:{sn % 3600 // 60:02}:{sn % 60:02}"


def cihazlari_listele():
    import soundcard as sc
    print("Hoparlörler:")
    for s in sc.all_speakers():
        print("   -", s.name)
    print("Dinlenebilir kaynaklar (mikrofon + loopback):")
    for m in sc.all_microphones(include_loopback=True):
        print("   -", m.name)


def kaynak_sec(mikrofon: bool, cihaz: str | None):
    import soundcard as sc
    if cihaz:
        for m in sc.all_microphones(include_loopback=True):
            if cihaz.lower() in m.name.lower():
                return m
        sys.exit(f"'{cihaz}' adlı cihaz bulunamadı. --listele ile bak.")
    if mikrofon:
        return sc.default_microphone()
    hoparlor = sc.default_speaker()
    return sc.get_microphone(id=str(hoparlor.name), include_loopback=True)


def dinleyici(kaynak, q: queue.Queue, dur: threading.Event):
    """Arka planda sürekli ses okur, 16 kHz mono parçalar halinde kuyruğa atar."""
    with kaynak.recorder(samplerate=KAYIT_SR, channels=1, blocksize=1024) as rec:
        while not dur.is_set():
            veri = rec.record(numframes=int(KAYIT_SR * BLOK_SN))
            mono = veri.mean(axis=1) if veri.ndim > 1 else veri
            n = len(mono) // 3 * 3
            mono = mono[:n].reshape(-1, 3).mean(axis=1)   # 48k -> 16k
            q.put(mono.astype(np.float32))


def model_yukle(model_adi: str | None):
    from faster_whisper import WhisperModel
    try:
        import ctranslate2
        gpu = ctranslate2.get_cuda_device_count() > 0
    except Exception:
        gpu = False
    if model_adi is None:
        model_adi = "large-v3-turbo" if gpu else "small"
    cihaz, tip = ("cuda", "float16") if gpu else ("cpu", "int8")
    print(f"Model yükleniyor: {model_adi} ({'GPU' if gpu else 'CPU'}) ...")
    return WhisperModel(model_adi, device=cihaz, compute_type=tip), gpu


def main():
    p = argparse.ArgumentParser(description="Canlı Türkçe transkript / not alıcı")
    p.add_argument("--mikrofon", action="store_true", help="Sistem sesi yerine mikrofonu dinle")
    p.add_argument("--cihaz", help="Belirli bir ses cihazı (adın bir kısmı yeterli)")
    p.add_argument("--listele", action="store_true", help="Ses cihazlarını listele ve çık")
    p.add_argument("--model", help="tiny | base | small | medium | large-v3-turbo | large-v3")
    p.add_argument("--esik", type=float, default=0.005,
                   help="Sessizlik eşiği (ses kısıkken kelime kaçırıyorsa düşür, ör. 0.002)")
    p.add_argument("--klasor", default="notlar", help="Notların kaydedileceği klasör")
    a = p.parse_args()

    if a.listele:
        cihazlari_listele()
        return

    model, gpu = model_yukle(a.model)
    kaynak = kaynak_sec(a.mikrofon, a.cihaz)

    Path(a.klasor).mkdir(exist_ok=True)
    dosya_yolu = Path(a.klasor) / f"not_{datetime.datetime.now():%Y-%m-%d_%H-%M}.txt"
    dosya = open(dosya_yolu, "w", encoding="utf-8")
    dosya.write(f"# Canlı transkript - {datetime.datetime.now():%d.%m.%Y %H:%M}\n\n")

    q: queue.Queue = queue.Queue()
    dur = threading.Event()
    threading.Thread(target=dinleyici, args=(kaynak, q, dur), daemon=True).start()

    print(f"\nDinleniyor: {kaynak.name}")
    print(f"Notlar: {dosya_yolu.resolve()}")
    print("Videoyu başlat. Durdurmak için Ctrl + C\n" + "-" * 50)

    tampon, parca_sure, sessiz_blok = [], 0.0, 0
    gecen_sure = 0.0          # kayıt başından beri geçen ses süresi
    onceki_metin = ""

    try:
        while True:
            blok = q.get()
            tampon.append(blok)
            parca_sure += BLOK_SN
            sessiz_blok = sessiz_blok + 1 if np.sqrt(np.mean(blok ** 2)) < a.esik else 0

            # Cümle sonu gibi bir sessizlik gelince ya da parça çok uzayınca işle
            if not ((parca_sure >= MIN_PARCA_SN and sessiz_blok >= 1) or parca_sure >= MAX_PARCA_SN):
                continue

            ses = np.concatenate(tampon)
            baslangic = gecen_sure
            gecen_sure += parca_sure
            tampon, parca_sure, sessiz_blok = [], 0.0, 0

            if np.sqrt(np.mean(ses ** 2)) < a.esik:
                continue  # tamamen sessiz parça

            segmentler, _ = model.transcribe(
                ses,
                language="tr",
                beam_size=5 if gpu else 1,
                vad_filter=True,
                initial_prompt=onceki_metin[-200:] or "Türkçe konuşma.",
            )
            metin = " ".join(s.text.strip() for s in segmentler).strip()
            if not metin:
                continue

            satir = f"[{sure_yaz(baslangic)}] {metin}"
            print(satir)
            dosya.write(satir + "\n")
            dosya.flush()
            onceki_metin += " " + metin

            if q.qsize() * BLOK_SN > 20:
                print("   (uyarı: bilgisayar geride kalıyor, --model base veya tiny dene)")

    except KeyboardInterrupt:
        pass
    finally:
        dur.set()
        dosya.close()
        print("-" * 50 + f"\nKaydedildi: {dosya_yolu.resolve()}")


if __name__ == "__main__":
    main()
