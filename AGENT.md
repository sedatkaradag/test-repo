# İçerik ajanı talimatları (Claude zamanlanmış görevleri bunu okur)

Bu dosya, Claude'un her çalıştığında izlediği iş akışıdır. Davranışı değiştirmek
için bu dosyayı düzenlemen yeterli. Gönderi dili İngilizcedir.

## Değişmez kurallar

1. **Ayet veya hadis metnini asla kendin yazma, özetleme ya da düzeltme.** Metin
   yalnızca `scripts/find.py get <id>` çıktısından gelir. Görsele basılan metni
   `render.py` veritabanından alır.
2. Sadece veritabanındaki hadisler kullanılır (hepsi sahih/hasan olarak süzülmüştür).
3. Fıkhî hüküm (fetva) verme, "âlimler şöyle der" gibi kaynaksız iddia ekleme.
4. Bağlamından koparılınca yanlış anlaşılabilecek içerikleri seçme: savaş/cezalar,
   kölelik, yalnızca belirli bir olaya bağlı hükümler, cinsiyetle ilgili kolayca
   çarpıtılabilecek hükümler, ahiret azabını tek başına sert biçimde öne çıkaran metinler.
5. Ayet "and", "so", "then" veya küçük harfle başlıyorsa tek başına kullanma;
   anlam tamamlanacak şekilde aralık seç (ör. `quran:65:2-3`). Aralık en fazla 5 ayet.
6. Bir yanlışlık şüphesi varsa o slotu boş bırak ve raporla. Boş slot, hatalı gönderiden iyidir.

## Kurulum (her çalışmanın başında)

```bash
cd <repo klasörü> && git pull
pip install --break-system-packages -q pyyaml hijridate fonttools pillow
python3 -c "from PIL import features; assert features.check('raqm'), 'raqm missing'"
cd scripts
```
`raqm` yoksa Arapça doğru çizilemez: hiçbir şey kuyruğa ekleme ve bunu raporla.

## Günlük içerik akışı

1. **Durum kontrolü:** `python3 enqueue.py list` çıktısında `failed` veya `missed`
   durumundaki gönderileri ve hata mesajlarını (`queue/<slot>.json` → `error`) not al;
   rapora en üstte yaz. Son 24 saatte `published` (veya dry_run'da `dry_run_sent`)
   hiç yoksa yayıncı çalışmıyor olabilir: bunu da raporla.
2. **Boş slotları bul:** `python3 enqueue.py slots --days 2`. Çıktıdaki anahtarlar
   (ör. `2026-10-21_us-evening`) slot kimliğidir. Boş slot yoksa rapora geç.
3. **Planlayıcı:** Her boş slot için bir tema seç.
   - `python3 calendar_info.py 3` → özel günler (Cuma, Ramazan, Zilhicce vb.) önceliklidir.
   - `history/posted.jsonl` son 20 kayıt ve `notes/strategy.md` (varsa) oku.
   - Her slotun türü `config.yaml` → `slots[].type` ile sabittir (günde ayet / hadis /
     ayet / hadis). `enqueue.py slots` çıktısında da yazar; başka tür seçme.
   - Son 3 gönderinin temasını tekrarlama.
   - Tema örnekleri: patience, gratitude, mercy, du'a, kindness to parents, honesty,
     forgiveness, trust in Allah (tawakkul), remembrance (dhikr), good character,
     charity, prayer, Friday reminders, hope after hardship.
4. **Küratör:** `python3 find.py search hadith "<regex>"` veya `search quran "<regex>"`
   ile 2-4 farklı arama yap (ör. `"\bpatien|\bsabr"`). Adayları oku ve seç:
   - Tek başına anlaşılır, faydalı, evrensel bir mesaj.
   - Görselde rahat okunacak uzunluk (yaklaşık 320 karakter altı).
   - Parça/eksik metin olmasın ("the above-mentioned hadith" gibi).
   - Seçimden önce `python3 find.py get <id>` ile tam kaydı oku.
5. **Metin yazarı:** Caption'ı bir dosyaya yaz (ör. `/tmp/caption.txt`). Yapı:
   ```
   <Kanca cümlesi: en fazla 12 kelime, metinde olmayan iddia yok>

   <2-3 cümlelik sade İngilizce tefekkür; sadece metnin söylediğine dayanır>

   — <referans>  (hadis ise: "Sahih al-Bukhari 6018 · Grade: Sahih")

   <Kapanış cümlesi: her gönderide farklı>

   <3-5 hashtag>
   ```
   - Ton slot saatine uysun: sabah ve öğle kısa ve enerjik, akşam sakin ve tefekküre dönük.
   - **Link, alan adı ve meal/çeviri kaynağı yazma** (kod bunları reddeder).
   - **Kapanış cümlesi** son 8 gönderidekilerin hiçbiriyle aynı olamaz (kod kontrol eder).
     Hep "save this" deme; türleri değiştir: birine göndermeye çağır ("Send this to someone
     who…"), soru sor ("Which one will you choose?"), yoruma davet et ("Name one…"),
     kaydetmeye çağır ("Save it for the moment…"), küçük bir eyleme çağır ("Pick one small
     deed today…"). İçeriğe özel olsun.
   - **Hashtag'ler:** 3-5 adet (2026'da 5'in üstü erişimi düşürebiliyor); son 4 gönderiyle
     örtüşme %50'yi geçemez (kod kontrol eder). En fazla 1 geniş etiket (#quran, #hadith gibi),
     gerisi konuya özel (#smileissadaqah, #morningdua, #muslimhabits gibi).
   - **Arama için:** Kanca cümlesinde konunun aranan adı geçsin (patience, dua, forgiveness,
     gratitude); Instagram araması etiketten çok caption kelimelerine bakıyor.
     Son gönderilerin etiketlerine `python3 enqueue.py list` ve `queue/*.json` ile bak.
   - Metni caption'da alıntılayacaksan birebir veritabanındaki gibi olmalı. En fazla 2 emoji.
   - Kuyruktaki bir caption'ı değiştirmek için: `python3 enqueue.py recaption --slot <slot> --caption-file <dosya>`.
6. **Denetçi (bağımsız alt ajan):** `Agent` aracıyla ayrı bir ajan başlat ve şu
   görevi ver (yerine id, dosya yolu yaz):
   > You are an independent reviewer for an Islamic Instagram page. Run
   > `cd <repo>/scripts && python3 find.py get <ID>` and read `<caption dosyası>`.
   > Reject if: the text could be misunderstood out of context (war, punishments,
   > slavery, event-specific rulings, easily distorted gender rulings); a Qur'an
   > excerpt starts mid-sentence; the caption adds claims, rulings or scholarly
   > opinions not in the text; the caption misquotes the text; the reference or
   > grade is wrong; the tone is sensational; for hadith, the narrator named in the
   > English text does not match the narrator in the Arabic chain (`arabic` field)
   > — the image would show the wrong name. Reply only with JSON:
   > {"verdict": "approve" | "reject", "reasons": ["..."]}
   **Her kararı kaydet** (onay da red de):
   `python3 review_log.py --entry <ID> --slot <slot> --verdict approve|reject --round <tur> --reasons "<gerekçe 1> | <gerekçe 2>"`
   Red gelirse gerekçeye göre 4. adıma dön (en fazla 3 tur). Üçüncüde de red
   gelirse o slotu boş bırak.
   Her gönderi için **yeni** bir denetçi başlat; önceki denetçiyi devam ettirme (bağımsızlık).
7. **Görsel ve kuyruk:**
   ```bash
   python3 enqueue.py add --entry <ID> --slot <slot anahtarı> \
     --caption-file /tmp/caption.txt --theme "<tema>" --review "<denetçi özeti>"
   ```
   `REJECT` dönerse nedenine göre düzelt ya da başka içerik seç.
   Sonra oluşan `queue/*.jpg` dosyasını **Read ile açıp bak**: taşma, kutucuk
   (eksik glif), okunaksız satır varsa kuyruk dosyalarını sil ve başka içerik seç.
7b. **Günün Reels'i:** `slots` çıktısında `reel` türünde boş slot varsa, aynı günün onaylı
   gönderilerinden en çok paylaşılmaya uygun olanı seç (kısa, evrensel, güçlü kanca).
   Reels için **ayrı ve farklı** bir caption yaz (ilk satır izleyiciyi durduran kanca,
   sonra 1-2 cümle, kapanış, 3-5 etiket); denetçi bu caption'ı da aynı kurallarla incelesin
   ve kararı `review_log.py` ile kaydet. Sonra:
   `python3 enqueue.py add-reel --source <gönderi slotu> --slot <tarih>_reel --caption-file <dosya> --review "<özet>"`
   Video sessiz, aynı şablon; metin yukarıdan aşağı belirir. Metin değişmez, yeni hadis/ayet yok.
8. **Kaydet:**
   ```bash
   cd .. && git add queue history && git commit -m "content: <tarih> <id'ler>" && git pull --rebase && git push
   ```
9. **Kontrol panelini güncelle** (aşağıdaki "Kontrol paneli" bölümü).
10. **Rapor:** En üstte sorunlar (başarısız/kaçan gönderi, boş bırakılan slot),
   sonra eklenenler (slot, id, tema). Sorun yoksa tek satır yeterli. Bu rapor
   çalışma bittiğinde sahibine bildirim olarak gider.

## Kontrol paneli

Panel: https://claude.ai/artifact/3t2rUDYs4j5aEiSAwc2NEJ (sahibin canlı takip sayfası).
Her çalışmanın (günlük, haftalık, ana ajan değişiklikleri) sonunda:

1. `python3 scripts/panel_rows.py /tmp/panel` → satır dosyaları.
2. Yeni kuyruk görsellerini panele yükle: `Artifact` aracı, `action: "publish"`,
   `url` = panel adresi, `asset: true`, `file_paths` = yeni `queue/*.jpg` dosyaları.
   Dönen her `url`'yi ilgili satır dosyasına `image_url` olarak ekle.
3. `ArtifactData` ile yaz (`url` = panel adresi; önce `list` ile mevcut sürümleri oku,
   var olan belgelerde `if_version` ver; tek `batch` çağrısı kullan):
   - `queue/<slot>` ← `/tmp/panel/queue/<slot>.json` (zaten yüklü görseli tekrar yükleme;
     mevcut `image_url` değerini koru)
   - `meta/state` ← `/tmp/panel/meta/state.json` (çalışma saatini script saatten damgalar; elle yazma)
   - `reviews/<YYYY-MM-DD>` ← `/tmp/panel/reviews/<gün>.json` (denetim kayıtları; script hazırlar)
   - `log/<YYYY-MM-DD>` ← o günün belgesinin `entries` listesine bu çalışmanın adımlarını
     ekle (`{"ts", "agent", "text"}`; `ts` değerini `date -u +%Y-%m-%dT%H:%M:%SZ` ile al, tahmin etme; agent: Planlayıcı, Küratör, Metin yazarı, Denetçi,
     Tasarımcı, Analist, Ana ajan). Belge yoksa `{"day": "...", "entries": [...]}` ile oluştur.
4. 14 günden eski `queue/*` panel satırlarını ve 30 günden eski `log/*` belgelerini sil.

Panel güncellemesi başarısız olursa işi durdurma; raporda belirt.

## Haftalık analist akışı (pazartesi)

1. Kurulum adımları + `git pull` (insights pazartesi 03:41 UTC'de güncellenir).
2. `history/insights.json` oku. Python ile tema, tür (quran/hadith) ve slot
   bazında ortalama reach / saved / shares hesapla.
3. `notes/strategy.md` dosyasını güncelle: en iyi 3 tema, en zayıf 3 tema,
   önerilen tür oranı, saat önerisi (online_followers verisi varsa ona dayan).
   Tarihli kısa bir değişiklik notu ekle.
4. Saatleri sadece güçlü kanıt varsa ve son değişiklikten 14 gün geçtiyse
   `config.yaml` → `slots` içinde değiştir; `dry_run` ve slot sayısına dokunma.
5. Commit + push, ardından kısa bir haftalık özet yaz.

## Ana ajan (sahibiyle sohbet)

Repo bağlı herhangi bir Claude sohbeti ana ajandır. Sahibi doğal dille şunları ister,
sen de dosyaları ve komutları kullanarak yaparsın; her değişiklikten sonra commit + push:

- "Yarının gönderilerini göster" → `enqueue.py list`, ilgili `queue/*.jpg` dosyalarını
  ve caption'ları göster.
- "Şunu değiştir / şunu çıkar" → ilgili `queue/<slot>.*` dosyalarını sil, içerik akışının
  3-8. adımlarıyla o slotu yeniden doldur.
- "Saatleri değiştir / slot ekle" → `config.yaml` → `slots`.
- "Canlıya geç" → `dry_run: false`. "Durdur" → `paused: true`.
- "Nasıl gidiyor?" → `history/posted.jsonl`, `history/insights.json`, `notes/strategy.md`
  özetini ver.
- Kural değişikliği istenirse bu dosyayı (AGENT.md) güncelle; sonraki çalışmalar onu izler.
