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
7. **Kaynak metinde yazım hatası varsa o içeriği kullanma** (ör. çeviride "meas", hadiste
   "say- ing"). Metni düzeltmek yasak; `integrity.py` bunları yakalar, başka içerik seç.
8. Kur'an Arapçası veritabanı oluşturulurken Kral Fahd Kur'an Kompleksi (Medine Mushafı)
   metniyle harf harf karşılaştırılır; uyuşmayan tek bir ayet bile olursa veritabanı oluşmaz.
   Kartlardaki Arapça, Kral Fahd Kompleksi'nin kendi Hafs metni (`arabic_display`, v18) ve
   kendi Mushaf fontuyla çizilir; bu metin de saklı metinle harf harf karşılaştırılmıştır.
9. **Yorum yanıtı asla onaysız gönderilmez.** `comments/outbox/`'a yalnızca sahibinin panelde
   onayladığı (`status: "approved"`) yanıt yazılır, onaylanan metin harfi harfine aynen.

## Kurulum (her çalışmanın başında)

```bash
cd <repo klasörü> && git pull
pip install --break-system-packages -q pyyaml hijridate fonttools pillow uharfbuzz pyspellchecker numpy
python3 -c "from PIL import features; assert features.check('raqm'), 'raqm missing'"
cd scripts
```
`raqm` yoksa Arapça doğru çizilemez: hiçbir şey kuyruğa ekleme ve bunu raporla.

## Günlük içerik akışı

1. **Durum kontrolü:** `python3 enqueue.py list` çıktısında `failed` veya `missed`
   durumundaki gönderileri ve hata mesajlarını (`queue/<slot>.json` → `error`) not al;
   rapora en üstte yaz. Son 24 saatte `published` (veya dry_run'da `dry_run_sent`)
   hiç yoksa yayıncı çalışmıyor olabilir: bunu da raporla.
   **Yayıncı canlı mı?** Yayıncı her çalışmanın sonunda bir sonrakini kendisi başlatır.
   `gh api "repos/sedatkaradag/test-repo/actions/workflows/publish.yml/runs?per_page=1" --jq '.workflow_runs[0] | [.status,.created_at]'`
   Şu an çalışan (`in_progress`/`queued`) bir çalışma yoksa zincir kopmuştur: yeniden başlat
   `gh api -X POST repos/sedatkaradag/test-repo/actions/workflows/publish.yml/dispatches -f ref=main`
   ve raporda belirt.
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

   <referans>  (hadis ise: "Sahih al-Bukhari 6018 · Grade: Sahih")

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
   - **Uzun tire (— veya –) kullanma**; yapay zekâ yazısı gibi duruyor. Virgül, nokta ya da yeni
     satır kullan (kod reddeder). Ayet ve hadis metninin kendisi kaynaktaki gibi kalır.
   - Kuyruktaki bir caption'ı değiştirmek için: `python3 enqueue.py recaption --slot <slot> --caption-file <dosya>`.
     Komut önce kod kontrollerini çalıştırır, metin değiştiyse öğeyi `hold`'a alır; **yeni bir
     denetçi** onaylayınca `enqueue.py approve` ile yayına döner.
   - **Kuyruktaki bir gönderide sorun görülürse** (denetçi ya da ana ajan): hemen
     `python3 enqueue.py hold --slot <slot> --reason "..."` ile beklemeye al (yayıncı
     sadece `ready` olanları paylaşır). Görsel hatası çizim kodundan geliyorsa kod
     düzeltilir, sonra `python3 enqueue.py rerender --slot <slot>` (görsel/Story/video
     yeniden çizilir, öğe `hold` kalır). Yeni bir denetçi onaylarsa
     `python3 enqueue.py approve --slot <slot> --review "<karar>"`. Onaysız `hold` öğe asla
     elle `ready` yapılmaz.
5b. **Kod kontrolü (denetçiden önce):** Metni denetçiye göndermeden önce kuyruğa ekleyeceğin
   komutun aynısını `--check` ile çalıştır. Hiçbir şey kuyruğa eklenmez; bütün kod kuralları
   (bütünlük, kartın sığması, tekrar, caption kuralları, yazım) denenir:
   ```bash
   python3 enqueue.py add --check --entry <ID> --slot <slot anahtarı> --caption-file /tmp/caption.txt --theme "<tema>"
   ```
   `REJECT` dönerse metni düzelt ya da başka içerik seç ve tekrar `--check` çalıştır.
   `CHECK OK` görmeden denetçiye gönderme. Denetçi böylece her zaman son metni görür.
6. **Denetçi (son kontrol, bağımsız alt ajan):** `Agent` aracıyla ayrı bir ajan başlat ve şu
   görevi ver (yerine id, dosya yolu yaz):
   > You are an independent reviewer for an Islamic Instagram page. Mistakes are not
   > acceptable here: a wrong word in a verse or hadith is a serious error.
   > 1. Run `cd <repo>/scripts && python3 find.py get <ID>` and
   >    `python3 integrity.py <ID>`. Any "hard" issue = reject. Read every "flag" and
   >    judge it (a flagged word must be a correct transliteration, not a typo).
   > 2. Render the card: `python3 render.py <ID> /tmp/review_<n>.jpg` and OPEN the image
   >    with the Read tool. Compare what is drawn with the source text: for Qur'an,
   >    go through the Arabic word by word (no missing, extra, merged or split words,
   >    no missing or misplaced marks, nothing cut off at a line end). Zoom into each
   >    pair of lines (crop 2.5x with Pillow) and check mark by mark: every vowel,
   >    sukun, shadda, tanween, dagger alif, small waw/yaa, madd and small high meem on
   >    the right letter, nothing floating, touching another line or cut off. The
   >    card draws the King Fahd Complex text (`arabic_display`) with the Complex's own
   >    font, so pause signs (ۖ ۗ ۚ ...) appear as in the Madinah Mushaf: each must sit
   >    right after/above its own word. Only ۞ and ۩ are left out on purpose. The
   >    verse-end number must stay with its verse. For both, the
   >    English on the card must be the source English. The reference line must match.
   > 3. Read `<caption dosyası>` and check spelling and grammar sentence by sentence.
   > Reject if: anything in steps 1-3 is wrong; the text could be misunderstood out of
   > context (war, punishments, slavery, event-specific rulings, easily distorted gender
   > rulings); a Qur'an excerpt starts mid-sentence; the caption adds claims, rulings or
   > scholarly opinions not in the text, or misquotes it; the reference or grade is
   > wrong; the tone is sensational; for hadith, the narrator named in the English text
   > does not match the narrator in the Arabic chain (`arabic` field).
   > Reply only with JSON:
   > {"verdict": "approve" | "reject", "arabic_checked": true | false, "reasons": ["..."]}
   `arabic_checked` Kur'an içeriklerinde mutlaka `true` olmalı; değilse red say.
   `enqueue.py` kuyruğa eklemeden önce `integrity.py` kontrollerini kendisi de çalıştırır
   ve herhangi bir sorun varsa reddeder. Bu, denetçinin yerine geçmez; ikisi birlikte zorunlu.
   **Her kararı kaydet** (onay da red de):
   `python3 review_log.py --entry <ID> --slot <slot> --verdict approve|reject --round <tur> --reasons "<gerekçe 1> | <gerekçe 2>"`
   Red gelirse gerekçeye göre 4. adıma dön (en fazla 3 tur); düzeltilen ya da yeni metin yine
   5b'den (kod kontrolü) geçer, sonra **yeni** bir denetçiye gider. Üçüncüde de red gelirse
   o slotu boş bırak.
   Her gönderi için **yeni** bir denetçi başlat; önceki denetçiyi devam ettirme (bağımsızlık).
7. **Görsel ve kuyruk:**
   ```bash
   python3 enqueue.py add --entry <ID> --slot <slot anahtarı> \
     --caption-file /tmp/caption.txt --theme "<tema>" --review "<denetçi özeti>"
   ```
   5b'deki komutun aynısı, `--check` olmadan ve `--review` ile. **Denetçi onayından sonra
   caption'da, içerikte ve slotta hiçbir değişiklik yapılmaz.** Kod kontrolleri 5b'de geçtiği için
   burada `REJECT` beklenmez; yine de dönerse metni düzeltme: o içerikten vazgeç, açık sorun
   kaydet (`issues.py add --kind rule`) ve slotu baştan doldur (4 → 5b → yeni denetçi) ya da boş bırak.
   Sonra oluşan `queue/*.jpg` dosyasını **Read ile açıp bak**: taşma, kutucuk
   (eksik glif), okunaksız satır varsa kuyruk dosyalarını sil ve başka içerik seç
   (o içerik atılır, düzeltilmez).
7b. **Günün Reels'i:** `slots` çıktısında `reel` türünde boş slot varsa, Reels için **kendi
   içeriğini** seç; hiçbir gönderinin kopyası olmaz. Tür sırayla değişir: önceki Reels ayetse bu
   hadis, hadisse ayet (`enqueue.py list` ile son Reels'in türüne bak; kod da kontrol eder).
   3-6. adımları aynen uygula: tema (son 3 gönderi ve son 3 Reels'ten farklı), kısa ve en çok
   paylaşılmaya uygun içerik (yaklaşık 250 karakter altı, güçlü tek mesaj), ayrı caption (ilk
   satır izleyiciyi durduran kanca, sonra 1-2 cümle, kapanış, 3-5 etiket), denetçiden önce kod
   kontrolü (`python3 enqueue.py add-reel --check --entry <ID> --slot <tarih>_reel --caption-file <dosya> --theme "<tema>"`),
   sonra **yeni** bağımsız denetçi ve `review_log.py` kaydı. Onaydan sonra hiçbir şey değişmez. Sonra:
   `python3 enqueue.py add-reel --entry <ID> --slot <tarih>_reel --caption-file <dosya> --theme "<tema>" --review "<özet>"`
   Kod son 365 günde paylaşılan veya kuyruktaki içerikleri ve yanlış türü reddeder.
   Kart metni yukarıdan aşağı belirir. Oluşan `queue/<slot>.jpg` kartını Read ile aç. Kapak (`cover`):
   videonun son karesi, bitmiş kart (9:16); profil ızgarasında boş yeşil ekran görünmesin diye
   kod kendisi üretir ve yayıncı Instagram'a kapak olarak gönderir.
   **Ayet Reels'lerinde tilavet:** kartta hangi ayetler varsa ses de tam olarak onlar. Anlam
   için gerekirse bir önceki ya da sonraki ayeti de aralığa kat (tilavet en fazla ~60 sn).
   Kâriyi `enqueue.py` sırayla seçer (`config.yaml` → `reels.recitation.reciters`) ve
   caption'ın en altına "Recitation: <ad>" satırını kendisi ekler; o satırı sen yazma.
   Öğe `audio_pending` olarak girer; GitHub `reel-audio` işi push'tan sonra sesi everyayah.com'dan
   indirip videoya ekler, ses seviyesini eşitler ve öğeyi `ready` yapar. Sesi eklenmemiş Reels
   yayınlanmaz. Atanan kâride ayet yoksa sıradaki kâriler denenir (caption'daki ad kendiliğinden
   güncellenir); hiçbirinde yoksa Reels sessiz çıkar ve "Recitation" satırı silinir. Hadis
   Reels'leri sessizdir. **Günde tek Reels** (`reel` slotu); ek Reels ancak sahibi isterse.
7d. **Ayet gönderilerinin Story'si:** `enqueue.py add` ayet gönderileri için Story'yi kendiliğinden
   tilavetli 9:16 video olarak hazırlar (`story_video`, `story_audio`; kâri sırası Reels'le ortak).
   GitHub sesi ekler; eklenemezse ya da video reddedilirse yayıncı görsel Story'yi atar, gönderi
   hiçbir durumda etkilenmez. Story'siz çıkmış bir ayet gönderisine sonradan tilavetli Story:
   `python3 enqueue.py add-story --source <gönderi slotu> --at <UTC zaman>`.
   Panelde ayrı kart açılmaz: Story yayınlanınca videosunu yükleyip **kaynak gönderinin** satırına
   `story_video_url`, `story_audio` ve `story_kind: "video"` yaz.
7c. **Haftalık carousel:** `slots` çıktısında `carousel` türünde boş slot varsa (haftada bir):
   tek bir tema seç (son 4 carousel'den farklı; `notes/strategy.md` en iyi temaları söylüyorsa
   onlardan), aynı temada 5 içerik seç (ayet, hadis ya da karışık; hepsi bağlamdan bağımsız,
   tam cümle, son 365 günde paylaşılmamış). Kapak başlığı kısa ve aranabilir olsun
   ("5 Qur'an passages on patience", "5 duas from the Sunnah"); ayet aralığı varsa
   "verses" değil "passages" de. Caption'da her içeriğin referansı ayrı satırda. Önce kod kontrolü:
   aşağıdaki komutun aynısını `--check` ile çalıştır, `CHECK OK` olmadan ilerleme. Sonra **denetçi
   tüm seti birlikte** incelesin (her öğe + başlık + caption); kararı kaydet. Onaydan sonra
   hiçbir şey değişmez. Sonra:
   `python3 enqueue.py add-carousel --entries <id1,id2,...> --slot <tarih>_carousel --title "<başlık>" --subtitle "<alt başlık>" --caption-file <dosya> --theme "<tema>" --review "<özet>"`
   Kapak görselini (`queue/<slot>_0.jpg`) Read ile açıp kontrol et.
8. **Kaydet:**
   ```bash
   cd .. && git add queue history && git commit -m "content: <tarih> <id'ler>" && git pull --rebase && git push
   ```
9. **Kontrol panelini güncelle** (aşağıdaki "Kontrol paneli" bölümü).
10. **Açık sorunlar:** Bu çalışmada fark ettiğin her sorunu "Açık sorunlar" bölümündeki gibi kaydet,
   commit + push et ve panelde `issues/<id>` belgesini yaz.
11. **Rapor:** En üstte sorunlar (başarısız/kaçan gönderi, boş bırakılan slot),
   sonra eklenenler (slot, id, tema). Sorun yoksa tek satır yeterli. Bu rapor
   çalışma bittiğinde sahibine bildirim olarak gider.

## Kontrol paneli

Panel: https://claude.ai/artifact/3t2rUDYs4j5aEiSAwc2NEJ (sahibin canlı takip sayfası).
Her çalışmanın (günlük, haftalık, ana ajan değişiklikleri) sonunda:

1. `python3 scripts/panel_rows.py /tmp/panel` → satır dosyaları.
2. Yeni kuyruk görsellerini panele yükle: `Artifact` aracı, `action: "publish"`,
   `url` = panel adresi, `asset: true`, `file_paths` = yeni `queue/*.jpg`, `queue/*_story.jpg`
   ve `queue/*.mp4` dosyaları. Dönen url'leri ilgili satır dosyasına ekle: gönderi görseli
   `image_url`, Story görseli `story_url`, Reels videosu `video_url` (Reels satırında
   `image_url` olarak Reels'in kendi kartını kullan; `audio_pending` Reels'in videosunu ses
   eklenince yükle, "Panel senkronu" bunu tamamlar; `story_audio.done` olan gönderilerin
   `queue/<slot>_story.mp4` videosunu da yükleyip `story_video_url` yaz). Carousel'de tüm kartları
   (`queue/<slot>_0.jpg` ... ) yükle: kapak `image_url`, hepsi sırayla `card_urls` listesi.
3. `ArtifactData` ile yaz (`url` = panel adresi; önce `list` ile mevcut sürümleri oku,
   var olan belgelerde `if_version` ver; tek `batch` çağrısı kullan):
   - `queue/<slot>` ← `/tmp/panel/queue/<slot>.json` (zaten yüklü görseli tekrar yükleme;
     mevcut `image_url` değerini koru)
   - `meta/state` ← `/tmp/panel/meta/state.json` (çalışma saatini script saatten damgalar; elle yazma)
   - `reviews/<YYYY-MM-DD>` ← `/tmp/panel/reviews/<gün>.json` (denetim kayıtları; script hazırlar)
   - `issues/<id>` ← `/tmp/panel/issues/<id>.json` (açık sorunlar; durumu değişenleri yaz)
   - `log/<YYYY-MM-DD>` ← o günün belgesinin `entries` listesine bu çalışmanın adımlarını
     ekle (`{"ts", "agent", "text"}`; `ts` değerini `date -u +%Y-%m-%dT%H:%M:%SZ` ile al, tahmin etme; agent: Planlayıcı, Küratör, Metin yazarı, Denetçi,
     Tasarımcı, Analist, Ana ajan). Belge yoksa `{"day": "...", "entries": [...]}` ile oluştur.
4. 14 günden eski `queue/*` panel satırlarını ve 30 günden eski `log/*` belgelerini sil.

Panel güncellemesi başarısız olursa işi durdurma; raporda belirt.

Panel, yayınlanan gönderiyi paylaşımdan sonra 24 saat "Kuyruktaki gönderiler"de
"Yayında" olarak gösterir; sonra yalnızca "Yayınlananlar" tablosunda kalır (sayfa kendisi yapar).

## Panel senkronu (her slottan sonra)

GitHub yayıncısı panele yazamaz; paylaşımları repoya kaydeder. Bu kısa çalışma repodaki
durumu panele taşır ve yorum yanıtlarını yürütür. İçerik üretmez, kuyruğu, görselleri veya
config'i değiştirmez; yalnızca `comments/outbox/` için commit atar.

1. `git pull` (repo yoksa Kurulum'daki gibi klonla).
2. `python3 scripts/panel_rows.py /tmp/panel`.
3. Panelden `queue` koleksiyonunu `ArtifactData list` ile oku. Her repo satırı için yalnızca
   `status`, `media_id`, `posted_at`, `error`, `story_kind` alanlarından farklı olanları `update` ile yaz
   (`if_version` ver; `image_url`, `story_url`, `video_url`, `card_urls`'e dokunma; repoda
   olmayan alanı yazma). Panelde hiç olmayan bir satır varsa ekleme, raporda belirt.
   Tüm yazımlar tek `batch`.
4. Bu çalışmada "Yayında"ya geçen her gönderi için `log/<YYYY-MM-DD>` belgesine
   `{"ts": <posted_at>, "agent": "Yayıncı", "text": "<referans> yayınlandı (<İstanbul saati>)…"}`
   ekle (Story/carousel/Reels olduğunu belirt). Gün belgesi `posted_at`'in UTC günüdür.
5. Sorun kontrolü: `publish_at` 20 dakikadan eski olup repoda hâlâ `ready`, `publishing` veya
   `audio_pending` olan, `error`'unda "recitation could not be added" yazan `hold` Reels, ya da
   `failed` / `missed` olan gönderi var mı? **Tilavet eklenen Reels:** repoda `audio.done: true`
   olup panel satırında `audio.done` olmayan her Reels ya da Story öğesi için `queue/<slot>.mp4`'ü
   panele yükle, satırın `video_url`, `audio`, `status`, `publish_at` ve `caption` alanlarını
   güncelle; `story_audio.done` olup panelde `story_video_url` olmayan gönderiler için
   `queue/<slot>_story.mp4`'ü yükleyip `story_video_url` ve `story_audio` yaz. Varsa en üstte bildir ve
   `log`'a "Ana ajan" olarak not düş. Yayıncıyı veya kuyruğu kendin değiştirme.
6. **Zamanlama kontrolü:** aşağıdaki "Senkron zamanlaması" adımlarını uygula (slot
   saatleri değiştiyse görevler burada kendini düzeltir).
7. **Yorumlar:** aşağıdaki "Yorum yanıtları" adımlarını uygula.
8. Fark ettiğin sorunları "Açık sorunlar" bölümündeki gibi kaydet ve `issues/<id>` panel
   belgesini yaz.
9. Rapor: en üstte onay bekleyen yorum sayısı ("2 yorum yanıtı onayını bekliyor") ve sana
   bırakılan yorumlar; sorun yoksa tek satır ("Panel güncel: X yayında, sorun yok").

### Senkron zamanlaması

Senkron görevlerinin saatleri `config.yaml` slotlarından hesaplanır; elle saat yazma.

1. `python3 scripts/sync_schedule.py` → olması gereken görevler (`tasks`: `name`,
   `cron_expression`) ve ortak `prompt`.
2. `list_triggers` ile adı "Halal Algorithm – panel senkronu · " ile başlayan görevleri bul.
3. Eşleştir (ada göre):
   - cron farklıysa `update_trigger` ile yalnızca `cron_expression`'ı güncelle. **Görev
     metnini (prompt) asla otomatik değiştirme**: farklıysa değiştirmeden raporda belirt;
     metin yalnızca sahibinin onayıyla, sohbetteki ana ajan tarafından güncellenir;
   - listede olup görevi olmayan için `create_trigger` (`name`, `cron_expression`,
     `prompt` = script'teki prompt, `initiation`: "human_schedule", bildirim: push) ama
     yalnızca slot saatleri değiştiği için yeni bir saat dilimi gerekiyorsa;
   - görevi olup listede olmayanı (o saat diliminde artık slot yok) `delete_trigger` ile sil.
4. Değişiklik yaptıysan log'a "Ana ajan" olarak tek satır yaz (eski → yeni saat) ve raporda belirt.

Slot saatlerini değiştiren her çalışma (haftalık analist, ana ajan) commit + push'tan
hemen sonra bu adımları uygular.

## Yorum yanıtları (kendi gönderilerimize gelen yorumlar)

Akış: GitHub `comments-fetch` saatte bir yeni yorumları `comments/inbox.json`'a yazar →
senkron çalışması her yeni yorum için panele taslak koyar → sahibi panelde onaylar, düzenler
veya reddeder → sonraki senkron çalışması onaylananları `comments/outbox/`'a yazıp push eder →
GitHub `comments-send` gönderir ve sonucu `comments/sent.jsonl`'a yazar. Başka hesapların
gönderilerine asla yorum yazılmaz; API buna izin vermez, bu sistem de yapmaz.

**Panel belgesi** `comments/<comment_id>`: `comment_id, media_id, permalink, post_ref, slot,
username, text, ts, category ("reply" | "escalate" | "ignore"), reason, draft, status, reply,
approved_at, sent_at, reply_id, error`. `status`: `pending` (taslak onayda) · `escalated`
(sahibine bırakıldı) · `ignored` · `approved` (sahibi onayladı, `reply` = gönderilecek metin) ·
`rejected` · `sending` · `sent` · `failed` · `skipped` · `answered_in_app` (sahibi uygulamadan
kendisi yanıtladı). `approved` ve `rejected`'ı yalnızca sahibi (panel) yazar; sen yazma.

Her senkron çalışmasında, sırayla:

1. `comments/inbox.json`, `comments/sent.jsonl` ve panelin `comments` koleksiyonunu oku.
2. **Sonuçları işle:** `sent.jsonl`'daki her kayıt için panel belgesi `approved` veya `sending`
   ise `status` = kayıttaki durum (`sent` / `failed` / `skipped`), `sent_at` = `at`, `reply_id`,
   `error`. Inbox'ta `answered: true` olup panelde `pending` / `escalated` olanı `answered_in_app` yap.
3. **Yeni yorumlar** (inbox'ta olup panelde olmayan, `answered: false`): her birini sınıflandır,
   gerekiyorsa taslak yaz, panele `set` ile ekle (`if_version` yok, yeni belge). Gönderinin
   caption'ını `queue/<slot>.json`'dan oku; yanıt o gönderiye ve yorumun kendisine özel olsun.
   - `reply` → `status: "pending"`, `draft` dolu. Teşekkür, "Ameen", dua, kişisel paylaşım,
     gönderinin kaynağını soran yorum (yalnızca caption'daki referansla yanıtla).
   - `escalate` → `status: "escalated"`, `draft` boş, `reason` tek cümle. Hüküm/fetva veya
     gönderinin ötesinde dini soru, mezhep/akide tartışması, hadisin sıhhatine veya meale
     itiraz, sayfaya eleştiri, siyasi konu, sıkıntı veya kriz belirtisi (bunu raporda en üste koy).
     Emin değilsen `escalate`.
   - `ignore` → `status: "ignored"`, `reason`. Spam, bot, reklam, link, hakaret. Yanıt yok;
     gizleme/silme kararı sahibinin.
4. **Taslak kuralları:** yorumun dilinde (emin değilsen İngilizce), 1-2 kısa cümle, en fazla
   200 karakter; sıcak, sade, yoruma özel; uzun tire (— –) yok. Ayet veya hadis alıntılama, yeni hadis ekleme,
   hüküm verme, "âlimler der ki" deme; link, etiket, "DM at", "takip et" yok; en fazla bir emoji.
   Son 50 yanıtta (panel `reply`/`draft` + `sent.jsonl`) geçen bir cümleyi tekrar etme;
   son 10 yanıtla aynı kelimeyle başlama.
5. **Onaylananları gönder:** panelde `approved` olup `sent.jsonl`'da `sent` kaydı olmayan her
   belge için `comments/outbox/<comment_id>.json` yaz:
   `{"comment_id", "message": <panel reply alanı, aynen>, "approved_at"}`. Sonra
   `git add comments/outbox && git commit -m "comments: send <n> approved" && git pull --rebase && git push`
   ve bu belgeleri `sending` yap. `gh run list -R sedatkaradag/test-repo -w comments-send.yml -L 1`
   ile en fazla 3 dakika bekle; bitince `git pull` ve 2. adımı tekrarla. Bitmezse sonraki
   çalışma tamamlar.
6. `log/<gün>` belgesine `agent: "Yorum ajanı"` ile tek satır: kaç yeni yorum, kaç taslak,
   kaç yanıt gönderildi (yorum metnini log'a yazma).

Tüm panel yazımları tek `batch`, var olan belgelerde `if_version` ile.

## Haftalık analist akışı (pazartesi)

1. Kurulum adımları + `git pull` (insights pazartesi 03:41 UTC'de güncellenir).
2. `history/insights.json` oku. Python ile tema, tür (quran/hadith) ve slot
   bazında ortalama reach / saved / shares hesapla.
3. `notes/strategy.md` dosyasını güncelle: en iyi 3 tema, en zayıf 3 tema,
   önerilen tür oranı, saat önerisi (online_followers verisi varsa ona dayan).
   Tarihli kısa bir değişiklik notu ekle.
4. Saatleri sadece güçlü kanıt varsa ve son değişiklikten 14 gün geçtiyse
   `config.yaml` → `slots` içinde değiştir; `dry_run` ve slot sayısına dokunma.
   Saat değiştirdiysen push'tan sonra "Senkron zamanlaması" adımlarını uygula.
5. Commit + push, ardından kısa bir haftalık özet yaz.

## Açık sorunlar

Herhangi bir çalışma (günlük, haftalık, senkron, ana ajan) bir sorun fark ettiğinde raporda
söylemekle yetinmez, kaydeder:

```bash
python3 scripts/issues.py add --kind <code|rule|content|publish|other> --source "<ajan, tarih>" \
  --ref "<slot veya id>" --title "<tek cümle>" --detail "<ne oldu, etkisi, varsa öneri>"
```

- `code`: script hatası (ör. çizim hatası yüzünden içerik elendi). Kodu **sen düzeltme**; kaydet.
- `rule`: bir kural esnetildi ya da atlandı (ör. onaydan sonra metin değişti). Ne yaptığını yaz.
- `content`: bir içerik sorun yüzünden elendi ya da değiştirildi.
- `publish`: paylaşım, Story, tilavet veya panel hatası.
Aynı başlıkla açık bir kayıt varsa script yenisini açmaz. Kaydettikten sonra commit + push et,
panelde `issues/<id>` belgesini yaz. Kayıtları yalnızca ana ajan kapatır
(`python3 scripts/issues.py close <id> --resolution "..."`), sahibinin onayıyla.

## Ana ajan (sahibiyle sohbet)

Repo bağlı herhangi bir Claude sohbeti ana ajandır. Açık sorunları sahibi panelden takip eder;
sen ancak sahibi isteyince bakarsın. Sahibi doğal dille şunları ister,
sen de dosyaları ve komutları kullanarak yaparsın; her değişiklikten sonra commit + push:

- "Yarının gönderilerini göster" → `enqueue.py list`, ilgili `queue/*.jpg` dosyalarını
  ve caption'ları göster.
- "Şunu değiştir / şunu çıkar" → ilgili `queue/<slot>.*` dosyalarını sil, içerik akışının
  3-8. adımlarıyla o slotu yeniden doldur.
- "Saatleri değiştir / slot ekle" → `config.yaml` → `slots` (Reels/carousel saatleri
  `reels.slot` / `carousel.slot`); push'tan sonra "Senkron zamanlaması" adımlarını uygula.
- "Canlıya geç" → `dry_run: false`. "Durdur" → `paused: true`.
- "Yorumları göster / şu yorumu yanıtla" → "Yorum yanıtları" bölümü. Sahibi sohbette bir
  yanıtı açıkça onaylarsa panel belgesini `approved` yap (`reply` = onaylanan metin,
  `approved_at` = şimdi) ve 5. adımı hemen uygula.
- "Nasıl gidiyor?" → `history/posted.jsonl`, `history/insights.json`, `notes/strategy.md`
  özetini ver.
- Kural değişikliği istenirse bu dosyayı (AGENT.md) güncelle; sonraki çalışmalar onu izler.
