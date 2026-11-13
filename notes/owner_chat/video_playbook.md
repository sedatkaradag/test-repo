# Video yapım rehberi (elle yapılan Reels)

Sahibinin bu formatlarda verdiği bütün geri bildirimler ve teknik boru hattı. Yeni bir video yapmadan önce
oku; aynı hatayı ikinci kez yapma.

## Genel çalışma şekli

1. **Örnek video geldiyse önce incele.** Claude in Chrome ile Instagram linkini aç; `video` elemanını
   durdurup (`v.pause(); v.currentTime = X`) ve video alanını `zoom` ile yakınlaştırarak 6-10 kare al.
   Açıklama metni `meta[property="og:description"]`'da (kaynak, hadis numarası burada yazıyor). Süre:
   `v.duration`. Sahnelerin kurgusuna, kamera açısına, derinliğe (bulanıklık), karakterlerin nasıl
   çizildiğine, yazı kartlarına dikkat et. Gerekirse sahibi istemeden tekrar aç ve bak.
2. **Uyarla, kopyalama.** Fikir ve sahne akışı aynı, görsel dil bizim: koyu yeşil (#0b1a17 / #10241f),
   altın (#e8c66a), fildişi (#f6efdc); EB Garamond (İngilizce), Marcellus (etiketler), Amiri (hadis Arapçası
   ve ﷺ), KFGQPC Hafs (Kur'an); hepsi `assets/fonts/`.
3. **Belirsizlik varsa başlamadan sor** (metin kapsamı, ses, format, plan). Önerilen seçenek başta.
4. **Metin:** ayet/hadis yalnızca kaynaktan (`scripts/content.py get`). Uzun hadiste sahibine hangi kısmın
   kullanılacağını sor; kısmı kelimesi kelimesine kullan. Bizim cümlelerimiz (giriş sorusu, kapanış sorusu,
   yönlendirme) hadis metninden ayrı biçimde gösterilir.
5. **Önce kareleri kontrol et**, sonra tam render. Tam render'dan sonra bağımsız doğrulayıcı alt ajan:
   metin kaynakla birebir mi, Arapça harf harf aynı mı, vurgu sesle senkron mu, Peygamber gösterilmiyor mu.
6. **Süre:** render'ı arka planda çalıştır (Bash `run_in_background`), süreyi önceden ölç (birkaç kare) ve
   sahibine söyle. Kare başına ~0,3 sn hedefle; daha yavaşsa önce hızlandır (aşağıda).

## Ortak teknik boru hattı

- **Render:** HTML/SVG/CSS sayfası, Chromium'da Python Playwright ile kare kare (`window.render(t)` →
  `page.screenshot(jpeg)` → ffmpeg image2pipe, 30 fps, 1080×1920, libx264 veryfast crf 19, AAC 160k).
  Ortamda Playwright ve Chromium hazır (`playwright install` yapma).
- **Hız:** her karede yüzlerce SVG elemanı + filtre (blur) çok yavaşlatır (Muâviye'de 30 dakikayı geçti).
  Kıpırdamayan katmanları bir kez PNG'ye çizip her karede `<image>` olarak kullan (`window.prepLayer`,
  `muawiya_muslim537/page.html`), görüntü yolları mutlak olsun (`Path.resolve()`), kayıttan önce her çekimi
  bir kez gösterip resimleri yüklet. `innerHTML` ile her karede yeni `<image>` yaratma (her karede yeniden
  çözülür); sabit eleman tutup yalnızca `transform` değiştir.
- **Kur'an tilaveti:** `audio-fetch.yml` (everyayah + quran-align kelime zamanları) → `drafts-audio` dalı.
  Kelime zamanları: Alafasy, Sudais, Abdul Basit, Husary, Minshawi, Shuraym, Shatri, Hani Rifai, Tablawi.
  Varsayılan kâri: **Alafasy** (sahibi tercih etti). Hizalama `[w, w+1, start_ms, end_ms]` (0 tabanlı).
- **İngilizce TTS (ücretsiz):** Kokoro-82M (Apache-2.0), GitHub Actions'ta çalışır (sandbox modeli indiremez).
  Ses: **bm_george** (İngiliz erkek, sahibi seçti), hız 0.95. Kod: `samples/tts/make_tts.py`, workflow
  `samples/tts/tts-work.yml.txt`. Çalıştırma: `tts-work` dalında `tts/script.json`'u değiştir ve push et
  (workflow yalnızca o dalda, push ile tetiklenir) → çıktı `tts-out` dalına (`hook/body/note/outro .wav + .json`,
  kelime başlangıç/bitiş zamanlarıyla). Actions "artifact" indirme proxy'de kapalı, o yüzden dala yazılıyor.
  `script.json`: `words: [{d: ekranda görünen, s: okunan}]`; okunuş düzeltmeleri yalnızca `s`'de
  (ﷺ → "peace be upon him,", "Abu Ad-Darda'" → "Abud Darda", "b." → "ibn", "Qur'an" → "Quran").
  Ekranda metin kaynakla birebir kalır. Kokoro token'ları ekrandaki kelimelere sırayla eşlenir ve script
  harfleri karşılaştırarak bunu doğrular.
- **Kelime vurgusu (karaoke):** altyazı 4-7 kelimelik parçalar (cümle/virgül sonunda böl, `b.` gibi
  kısaltmada bölme); okunan kelime altın kutu, koyu yazı. Giriş ve kapanış soruları da kelime kelime vurgulanır
  (sahibi istedi: "izleyiciyi başta kaçırmamak için").
- **ﷺ:** Garamond'da bu karakter yok; tarayıcı bozuk bir yedek gösteriyor. Amiri ile, 1,5 em, altın renkte.
- **Kaynak kontrolü:** veri setimizde birçok hadisin sonundaki kapanış tırnağı/noktası eksik. Ekranda sonu
  görünen bir hadiste sunnah.com metniyle karşılaştır (sunnah.com doğrudan açılmıyor; WebSearch sonucu
  linkini WebFetch ile ya da dev.ihadis.com). Buhârî 1968'in sonu `"Salman has spoken the truth."`.
- **Logo kapanışı:** `samples/logo_draw/frames_800/059.png` (son kare). Resmin üstünde ~148, altında ~140 px
  boşluk var; kırpmadan koyarsan logo aşağıda kalır (sahibi fark etti). Kırpılmış kutu kullan
  (`muawiya_muslim537/page.html` → `#logo`).
- **Sonradan düzeltme:** sadece son kısım hatalıysa tamamını yeniden çizme: `make.py <out> <bitiş> start=<sn>`
  ile o kısmı render edip ffmpeg `trim + concat` ile birleştir (11 Kasım'da logo hatası böyle düzeltildi).

## Format: Guess the Surah / Trivia / 99 Names

Komutlar ve set dosyaları: `samples/README.md`. Skill: `quran-quiz-reels`.
- Guess the Surah sırası ORTA, KOLAY, ORTA, ZOR; cevap şıklarının yerini değiştir; video 100 sn'yi geçmesin
  (uzun ayetler süreyi hızla şişirir: 39:53 tek başına ~29 sn sürdü).
- Ayet sureyi ele vermemeli: sure adının ya da bilinen adının kelimesi yok (Al-Mulk = "Tabarak"), surenin
  meşhur açılışı değil. Aynı surenin sonraki ayeti olur.
- Çeldiricileri benzer temalı/komşu surelerden seç (ör. 54:17 için Ar-Rahman; tekrar eden ayet).
- Kullanılmış ayetler: `content_log.md`.

## Format: sesli mesaj (Al-Isra 17:32) — `samples/voice_note/`

Yapı (örnekteki yapı birebir korunur, sahibi bunu istedi): HIM 12:46 AM / HER 12:47 AM iki panel →
sohbet ekranı (unknown, Active now) → ayetin sesli mesaj olarak kaydı → gönderildi → sohbet kararır → kapanış.
Sahibinin geri bildirimleri (hepsi uygulandı):
- Logonun tamamı kullanılsın (yarım değil); HER panelindeki çerçevede `logo_crop.png`.
- Mesaj gönderme animasyonu, oturuş (yatak kenarında oturuyorlar), saç tek parça, saksı düzgün.
- Kapanışa doğru sohbet penceresi kararıp tekrar aydınlanmasın (kararma katmanı geri açılmaz).
- Yazma sesi yazı bitince durmalı: harf başına bir tık, yazı bitince ses yok.
- Balon gönderilince sağ üst köşeye kaybolmasın: **balon kalbe dönüşüp kızın telefonuna uçsun** ve orada
  kaybolsun; iki mesajda da. İlk sahnede de animasyonlu.
- **Kalp kırmızı** (#e0353f). Kalp mesajın son karakteri olarak yazılsın; aynı kalp bildirimde ve sohbette.
- İkinci balon ilkiyle **aynı noktada** çıksın; uzun metin iki satıra bölünsün ("Can we talk tonight?" /
  "Just us ❤"), balon yukarı doğru büyür, kuyruğu yerinde kalır.
- Kâri Alafasy. Meal okunurken vurgu: okunan Arapça kelimenin İngilizce karşılığı altın, okunmuşlar fildişi,
  gelecekler soluk. Eşleme Arapça kelime başına İngilizce kelime listesi (bitişik olmayabilir: إِنَّهُۥ →
  "for it … indeed", كَانَ → "is").
- Meal sonuna nokta eklemek gibi küçük "düzeltmeler" bile yapılmaz (doğrulayıcı yakaladı).

## Format: hikâye videosu, çizim sahneler + TTS (Buhârî 1968) — `samples/story_video/salman_bukhari1968/`

Akış: giriş sorusu (bizim, kelime vurgulu) → hadis metni birebir, sahnelere bölünmüş (kardeşlik, kapıdaki
ziyaret, yemek "I am fasting", gece "uyu" ×2, seherde birlikte namaz, Selmân'ın sözü, Ebü'd-Derdâ'nın mescide
gidişi; Peygamber gösterilmez) → kapanış sorusu → logo.
Karakter çizim kuralları (sahibinin geri bildirimleri, sırasıyla):
- **Yüzsüz**, düz çizim; karakterler **yandan** (profil) duruyor, yüzleri kameraya dönük değil.
- **Sakal:** top sakal değil; ilk kalın sakal biraz inceltilip yüze oturtuldu: kulak hizasından çene hattı
  boyunca çeneye, yüz elipsine kırpılmış (`clipPath`), başın arkasında sakal yok. Önden görünüm gibi
  (yüzü saran halka) çizme. "Sadece ince çizgi" de çizme. Doğru hali `page.html` → `BEARD()`.
- Saç çizilecekse ona da dikkat (şimdilik türban/sarık kapalı).
- Türbandan sarkan parça türbana ve başa **yapışık** olmalı, arada boşluk olmamalı.
- Cübbenin önünde **boylu boyunca beyaz şerit olmasın** (içteki entari şeridi kaldırıldı).
- **Ten rengi** biraz koyu (#a87a52, #97683f) + yüz çevresinde hafif koyu kontur; bej duvarlarda karışmasın.
- Yatan karakterde baş, ayaktakiyle aynı baş/türban/sakal çiziminin yan yatırılmış hali (türban başta kalır).
- Her karakter **ilk göründüğünde** başının üstünde küçük isim etiketi (Marcellus, koyu yeşil hap), birkaç
  saniye sonra kaybolur; sonraki sahnelerde tekrar yok.
- Kapanış alıntısı: hadisin sonunda kaynaktaki kapanış tırnağı olmalı.

## Format: hikâye videosu, cemaat sahneleri + Arapça kartlar (Müslim 537) — `samples/story_video/muawiya_muslim537/`

Akış: giriş sorusu → hadisin namaz kısmı (Muâviye'nin anlatımı, "…or words to that effect." ile biter),
çekimler: geniş açı → Muâviye'ye yakın (isim etiketi; hapşırma) → "يَرْحَمُكَ اللَّهُ" → başların ona
döndüğü çekim → ellerin uyluğa vurduğu yakın çekim → namaz biter, öne doğru ışık → kartlar: "مَا رَأَيْتُ
مُعَلِّمًا…" (öğretmen cümlesi), مَا كَهَرَنِي / وَلاَ ضَرَبَنِي / وَلاَ شَتَمَنِي (scold / beat / revile sırayla
yanar), "إِنَّ هَذِهِ الصَّلاَةَ…" → bizim cümle "Look at the three things he did not do." (üç fiil kartı tekrar)
→ kapanış sorusu "When you correct someone's mistake, how will they remember that moment?" → logo.
Metin, Arapça, ses ve senkron bağımsız doğrulayıcıdan geçti (11 Kas).

Sahibinin geri bildirimleri:
- Kişiler **arkadan ve hafif yukarıdan**: başın üstünde dikişli takke (kufi) ya da küçük sarık, altında koyu
  saç, geniş yuvarlak omuzlar; hiç yüz yok. Başını çevirenlerde yalnızca yanağın kenarı.
- Arkadan bakınca en önde imam olurdu; gösterilemez: **öndeki saflar uzaklaştıkça bulanıklaşıp sisin ve
  ışığın içinde kaybolmalı, saffın ucu hiç görünmemeli.** En yakındaki saf da hafif bulanık (alan derinliği).
- **Bütün çekimler aynı dünyadan** olmalı: yakın çekimde de Muâviye'nin önünde öne doğru uzanan çok sayıda saf
  görünmeli (sadece bir saf değil); başların döndüğü çekimde de saflar sonsuza gitmeli.
- El vurma: kolun tamamı yukarı-aşağı kaymasın (sıvazlama gibi görünür). Omuz ve üst kol sabit, ön kol
  dirsekten kalkar, hızla inip uyluğa vurur, kısa durur.
- Kapanışta logo ve yazılar ekranın ortasında olmalı.
- **11 Kas son hali (sahibinin referans karesine göre, onay bekleniyor):** saflar perspektifle bir noktaya
  daralmıyor; örnekteki gibi **yatay şeritler halinde üst üste** (her saf ~%7 küçük, sise karışıyor, aralarında zemin
  çizgisi). Kişiler normal yapılı: omuz ~1,5 baş genişliği (96 birim), gövde kısa (118), omuz omuza; başta takke +
  koyu saç. "Stare" kısmında sakal yok, sadece başın dönüşü ve kulak. Sahibi: "kişileri bu kadar geniş yapmana gerek
  yok, normal boyda kiloda olabilirler ama 3 metre olmasın." Kod: `page.html` → `personTop`, `world` (G, STEP, F, SP).
- **Ondan önceki deneme:** "3 metre boy" sorununun asıl nedeni saflar arası mesafeydi:
  ardışık iki saffın baş aralığı örnekte ~1,4 baş genişliği, bizde 3,6 idi. Şimdi `DZ = 0.12` (60 saf ufka kadar),
  kişiler omuz omuza (`SP = 222`), gövde ayakta biter (omuzdan +430), arkadaki saf `z = 0.7`'de (alçakta, bulanık),
  sis ve bulanıklık mesafeye (z) göre. Aşağıdaki not bu düzeltmeden önceki teşhistir.
- **Önceki teşhis:** son sürümde kişiler "3 metre boyunda" görünüyordu. Sahibi: "tek yapman gereken ufku
  düzeltmekti; ufuk düzelmiş ama başka şeyler bozulmuş." Nedeni: perspektif dünyasında (`world()`) kişi
  boyu (omuzdan ayağa ~520 birim × ölçek) satır aralığına göre çok büyük ve gövde aşağı doğru 1000 birim
  uzatıldı; yakın çekimde 1,6× zoom ile gövdeler upuzun görünüyor. Düzeltme yönü: önceki (beğenilen) karakter
  çizimini ve oranlarını koru (gövde kısa, omuzlar geniş, kişiler arası mesafe gerçekçi), sadece saf sayısını
  ve ufka doğru kaybolmayı bu tek dünyada sağla; satır aralığını kişi boyuna göre ayarla (önden arkaya bir
  sonraki saffın omuz çizgisi, öndekinin başının hemen üstünde kalmalı), gövdeyi ekran dışına taşacak kadar
  uzatma, yakın çekimde zoom'u Muâviye'nin omuzları ekranın altında kalacak şekilde ayarla. Örnek videonun
  geniş ve yakın çekim karelerine bakıp oranları karşılaştır. Çizimden önce birkaç kareyi sahibine gönder.

## Format: vaaz sesi + çizgi illüstrasyon (Şeyh Kişk "Ölüm" denemesi, 12 Kas) — `samples/story_video/death_kishk/`

**Deneme; kanalda paylaşılmaz** (Hadîsü's-Sûr zayıf/münker; sahibinin tek seferlik istisnası, bkz. README "Kaynak kuralı").
Örnek: tab.takhayal'ın Arapça aslı (https://www.instagram.com/p/DfSwENuBmbK/) ve TheTazkiyyahGuide'ın İngilizce kopyası.
Sahibi "bizimki de benzer olsun" dedi: aynı sahne akışı, bizim renkler (koyu yeşil zemin, fildişi çizgi, altın vurgu), kendi çizimimiz.
- **Ses yazıya dökme:** `samples/asr/` (faster-whisper large-v3, `asr-work` dalı → `asr-out`; sahibi onayladı). Sandbox modeli
  indiremiyor. Whisper Mısır vaazında birkaç kelimeyi yanlış duydu; Arapça videonun ekran yazısıyla karşılaştırıp düzelt.
- **Çeviri bizim;** örnek videonun altyazısı kopyalanmaz. Ayet satırları `find.py`'den birebir (make.py kontrol eder), ayet etiketi
  ses sırasıyla (Kişk 81:13'ü 81:12'den önce okuyor). Arapça kartlar kaynaktan **kelime konumuyla** kesilir (elle yazılan Arapça
  kaynakla eşleşmez, yazma).
- `lines.txt`: `başlangıç | metin ([vurgu]) | sahne | ayet`. Render iki paralel parça (2 çekirdek), ~10 dk; düzeltmede sadece ilgili
  aralık yeniden çizilip `trim + concat` ile eklenir.
- Künye: en sonda soluk, küçük ("Voice: … · Concept: @tab.takhayal"), sahibi istedi.

## Format: "Pray anyway" yukarıdan seccade animasyonu (13 Kas) — `samples/story_video/pray_anyway/`

Sahibinin seçimleri: **müziksiz ortam sesi**, **nötr eller** (cinsiyet belli değil), **kendi ifadelerimiz** (örneğin
"Pray it sleepy" kalıbı kullanılmadı), **zengin illüstrasyon** (yukarıdan oda, vakte göre ışık, bizim yeşil/altın seccade).
- Akış: 5 vakit (etiketli) + 4 ruh hali + "Pray. *Anyway.*" (ışık tek noktaya iner, ses kesilir) + hadis kartı + logo; 28,4 sn.
- Hadis kartı: metin `find.py`'den, `display_text`/`split_narrator` (yalnız tipografi); Arapça kelime konumuyla kesilir;
  son cümle altına döner. Kaynakta "Lying" büyük L ile; düzeltilmez.
- Ses: `sound.py` gürültü + sinüs sentezi (örnek ses yok, müzik/melodi yok), sahne başına oda sesi ve olaylar
  (titreşim, klavye, saat, kapı, anahtar, cırcır böceği, fincan, yağmur, gök gürültüsü, kuş, sayfa, tesbih). -18 LUFS.
- Render tek parça ~4 dk. Mushaf yere değil rahleye konur.

## Format: kelime kelime yanan ayet Reels'i (13 Kas) — `samples/word_reel/`

Sahibinin isteği: okunan kelime en parlak (ışıltılı), okunmuşlar altın, okunmamışlar soluk; meal eşleşerek yanar
("zinaya yaklaşmayın" sesli mesaj videosundaki gibi). Görünüm sistem şablonu v3'ün aynısı (`reels.plan` + `layers`).
- Set dosyası: `map` (her Arapça kelimenin İngilizce kelime numaraları; metin değişmez) ve `events` (duyulduğu sırayla
  her kelime, tekrarlar dahil). Kelime zamanları audio-fetch'in `align.json`'ından.
- **Kârinin geri dönüp tekrar okuduğu yerler** `align.json`'da boşluk olarak görünür (31:14'te 14,25-22,8 sn: Alafasy
  3-10. kelimeleri yeniden okuyor). Tekrarı MFCC + DTW ile bul (librosa; önce kelime aralıklarını boşlukta ara, sonra
  aralığı boşluğa hizala; tekrar eden kelimelerin süreleri ilk okumayla örtüşmeli). Bağımsız doğrulayıcıya `map` ve
  `events`'i kontrol ettir.
- Render ~1,5 dk (32 sn video).
