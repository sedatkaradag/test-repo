# Sahibinin sohbeti: yeni sohbette buradan başla

Bu klasör, sahibinin (Sedat) Claude ile yaptığı sohbetin hafızasıdır. Yeni bir sohbet açıldığında asistan
önce bunları okur, sonra işe başlar. Amaç: yeni sohbetin eskisinden hiçbir farkı olmaması.

**Okuma sırası (yeni sohbette ilk iş):**
1. Repo: `git clone https://github.com/sedatkaradag/test-repo /home/claude/test-repo` (ya da `git pull`).
   Video sayfaları fontları ve logoyu `file:///home/claude/test-repo/...` yolundan okur; repo bu yolda olmalı.
2. Bu dosya (tercihler, kurallar, linkler, açık işler).
3. [`content_log.md`](content_log.md): elle yapılan her içerik, kullanılan her ayet/hadis, caption'lar, sonuçlar.
   **Yeni quiz / video hazırlarken buradaki ayet ve hadisler tekrar kullanılmaz.**
4. [`video_playbook.md`](video_playbook.md): video yaparken dikkat edilenler, sahibinin bütün geri bildirimleri,
   teknik boru hattı (render, TTS, kelime zamanlaması, doğrulama).
5. [`insights.md`](insights.md): istatistik altyapısı, bilinen sınırlar, şu ana kadarki bulgular.
6. [`../../samples/README.md`](../../samples/README.md): elle yapılan formatların komutları ve set dosyaları.
7. [`../strategy.md`](../strategy.md): haftalık analistin notları (her pazartesi güncellenir).
8. [`../../AGENT.md`](../../AGENT.md) → "Ana ajan (sahibiyle sohbet)" bölümü ve "Değişmez kurallar".

## Linkler

| Ne | Nerede |
|---|---|
| Instagram | @thehalalalgorithm (11 Kasım 2026: 447 takipçi, 110 gönderi) |
| Repo | github.com/sedatkaradag/test-repo (ana dal `main`) |
| Kontrol paneli (artifact) | https://claude.ai/artifact/3t2rUDYs4j5aEiSAwc2NEJ (AGENT.md → "Kontrol paneli") |
| İstatistik panosu "Halal Algorithm Insights" (Dashboard türü artifact) | https://claude.ai/artifact/KZ1WE7TDMVcAPgXY38X1wx — veriler artifact'ın kendi deposunda (`datasets/*`, dosya kaynakları `/_blob/...`); `ArtifactData` ile güncellenir, sayfa `files/index.html` |
| claude.ai Projesi | "The Halal Algorithm" (bu klasörün özeti `claude/handoff.md` olarak orada da var) |

## Sahibinin tercihleri ve kalıcı kurallar

**İletişim**
- Sahibi Türkçe yazar; yanıtlar Türkçe ve kısa. Uzun adım anlatımı yok; sonuç + gerekirse tek satır açıklama.
- Bir hatayı sahibi fark ederse: dürüstçe kabul et, nedenini açıkla, kalıcı çözümü (otomatik kontrol vb.) kur.
  "Kesin değil" diye yarım iş bırakma: veri doğru olacak şekilde baştan düzgün kur.
- Sahibini bekletme. Uzun süren işi (render vb.) arka planda çalıştır, ne kadar süreceğini söyle; bir şey
  30 dakikayı geçecekse önce hızlandır. (11 Kasım'da 30 dk'lık bekleme şikâyeti oldu.)
- Limit: sahibi 5 saatlik kullanım limitiyle çalışıyor; gereksiz tekrar işten ve dolaylı yollardan kaçın.

**Sistem**
- Sistemde (workflow'lar, `scripts/`, `AGENT.md`, `config.yaml`, kuyruk, zamanlanmış görevler) sahibinin açık
  onayı olmadan değişiklik yapma. `samples/` ve `notes/owner_chat/` içinde çalışmak, audio-fetch ve TTS
  dallarını kullanmak serbest.
- Zamanlanmış görevleri yalnızca bu sohbet (ana ajan) değiştirir.
- Ayet ve hadis metni asla elle yazılmaz, özetlenmez, düzeltilmez: yalnızca `scripts/find.py` /
  `scripts/content.py` ya da doğrulanmış kaynak (sunnah.com metni). Arapça da kaynaktan kesilerek alınır
  (kelime iskeleti karşılaştırılarak; bkz. `samples/story_video/muawiya_muslim537/build_script.py`).
- Yorum yanıtları sahibinin onayı olmadan asla gönderilmez; yorum yanıtlarında emoji yok.
- Doğruluk kritik işlerde (Arapça, meal, istatistik) bağımsız bir doğrulayıcı alt ajan çalıştır.

**Video / içerik işleri**
- Sahibi örnek video gönderip "aynısını yap" dediğinde birebir kopya istenmiyor: **fikri ve sahneleri alıp
  bizim kanalın görsel diline uyarla.** Örneği önce dikkatle incele (Chrome ile videoyu durdurup kare kare
  bakılabiliyor; bkz. playbook).
- Uzun sürecek video işlerinde belirsiz bir nokta varsa **başlamadan önce sor** (AskUserQuestion, önerilen
  seçenek başta). Sonra tekrar tekrar revize ettirmemek için her detayı kontrol et; sahibi "tekrar revize
  etmeyelim" diyor.
- Peygamber (s.a.v.) hiçbir görselde gösterilmez (namaz sahnelerinde imam da görünmez).
- Caption'lar İngilizce, kısa: hook + kısa açıklama + yorum/gönder/takip çağrısı + kaynak + hashtag.
  Quiz caption'larında emoji kullanmıyoruz (sahibi bazen kendisi ekliyor).
- Hadis caption'ında hadisten alıntı yapılacaksa kaynaktaki çeviri aynen kullanılır, kendi çevirimiz değil.

## Sistem özeti (ayrıntı: AGENT.md, README.md)

Otomatik: günde 4 ayet Reels'i (slotlar `config.yaml` → `reels.slots`; reel-us 10 Kasım'dan beri hadis değil
ayet), içerik ajanı her sabah kuyruğu doldurur, GitHub `publish.yml` paylaşır, `nightly.yml` token ve
istatistik çeker, haftalık analist `notes/strategy.md`'yi günceller. Haftalık carousel 10 Kasım'da kapatıldı.
Hadis Reels'i artık yalnızca sahibi isteyince.

Zamanlanmış görevler (Claude, hepsi `permission_mode: auto`):

| Görev | Zaman |
|---|---|
| Halal Algorithm – günlük içerik | her gün 08:37 İstanbul |
| Halal Algorithm – haftalık analist | pazartesi 09:23 İstanbul |
| Halal Algorithm – elle gönderi paylaş (`trig_0179CkSGe4s3w7e3V71V9KHb`) | takvimsiz; panelde "Paylaş"a basınca |
| Panel senkronu · Europe/Berlin | her gün 08:32 Berlin |
| Panel senkronu · Asia/Karachi | her gün 20:47 Karaçi |
| Panel senkronu · America/New_York | her gün 13:17 ve 21:17 New York |

## Elle gönderiler (12 Kasım 2026'dan beri)

Elle yapılan videolar (quiz, hikâye vb.) artık panelin **"Elle gönderiler"** bölümüne konur; sahibi orada
izler, caption'ı düzeltir, **Paylaş / Revize iste / Reddet** der. Paylaş → "elle gönderi paylaş" görevi
kuyruğa alır → yayıncı paylaşır (en geç ~15 dk) → görev `content_log.md` ve kullanılan ayet listesini
günceller. Adımlar: `AGENT.md` → "Elle gönderiler". Script: `scripts/manual_post.py`.
- Bu sohbette bir video bittiğinde: sohbette gönder **ve** panele koy ("Ana ajan: yeni elle gönderi ekleme").
- **Her yeni sohbette:** panelde `manual` koleksiyonunda `status: "revision"` olan var mı bak; varsa notu uygula.
- Bunlar denetçi/`integrity` adımlarından geçmez (sahibinin kararı: "ben manuel kontrol ediyorum, ama
  oluştururken dikkat et"). Hazırlarken doğrulayıcı alt ajan ve kaynak kuralları yine geçerli.
- Story'ye gitmez, deneme (trial) Reels değildir; istatistikte eskisi gibi `manual_posts` grubunda.
- İlk gerçek kullanımda kontrol et: panelin "Paylaş" düğmesi görevi başlatabildi mi (Claude Code Remote
  bağlantısı izni). Başlatamazsa sahibi sohbette "paylaş" der, ana ajan aynı adımları uygular.

## Kaynak kuralı (sahibinin sözü, 12 Kasım 2026)

**Yalnızca sahih ve hasen kaynak.** Sahibi açıkça onay vermedikçe bunun dışına asla çıkılmaz. Tek istisna:
Şeyh Kişk sesli "Ölüm" deneme videosu (Hadîsü's-Sûr, zayıf/münker); **kanalda paylaşılmayacak**, yalnızca
"yapabilir miyiz" denemesi. Her şey yayınlanacakmış gibi yapılır (caption'da rivayetin zayıflığı belirtilir).
Bu istisna başka içeriğe emsal değildir.

## Açık işler (11 Kasım 2026 itibarıyla)
- **"Pray anyway" (13 Kas)** panelde onay bekliyor (`manual/2026-11-13-pray-anyway`). İlk gerçek elle gönderi:
  sahibi Paylaş'a basınca görevin panelden tetiklenip tetiklenmediğini kontrol et (`list_triggers` → last_run).
  Örnek: taj_ul_furqan https://www.instagram.com/reel/DfpYfq9MgHx/ (fikir alındı, sözler ve çizimler bizim).
- **Şeyh Kişk "Ölüm" deneme videosu** (12 Kas): örnek https://www.instagram.com/p/DfcgRWbsX-1 (2:49,
  krem zemin çizgi illüstrasyon, serif altyazı, turuncu italik vurgu, ayet etiketleri). Bizde: koyu yeşil zemin,
  fildişi çizgi, altın vurgu, tam 2:49, aynı ses. Ses: sahibi videoyu yükleyecek. Arapça yazıya dökülüp
  İngilizceye bizim çevirimiz yapılacak (örneğin altyazısı kopyalanmaz); ayet satırları veritabanından.
  Kanalda paylaşılmayacak; panelin "Elle gönderiler"ine konmaz.

1. **Muâviye videosu (Sahih Muslim 537)** — 11 Kasım'da saf aralığı düzeltilip yeniden gönderildi; sahibinin onayı bekleniyor. Önceki durum: sahibi son sürümü beğenmedi: "insanların boyları 3 metre gibi
   görünüyor". Saflar artık sonsuza gidiyor (bu istenen), ama perspektifte kişiler çok uzun/dar duruyor.
   Düzeltilecek: tek dünya + kamera yaklaşımı korunacak; boy/omuz oranı ve satır aralığı gerçekçi olacak
   (kişi yüksekliği satır aralığına göre küçük, omuz genişliği ~0.45 × boy, baş ~1/7). Ayrıntılar ve bütün
   geri bildirimler: `video_playbook.md` → "Muâviye". Kod: `samples/story_video/muawiya_muslim537/`.
   Videonun diğer kısımları (metin, kartlar, ses, kapanış) onaylı ve doğrulandı.
2. **Hadis veri setinde eksik kapanış tırnağı:** `data/hadith.jsonl.gz` içindeki 29.198 hadisin 11.457'sinde
   tırnak sayısı tek (sona kesilmiş `"`/nokta olabilir; ör. Buhârî 1968 `...spoken the truth` — sunnah.com'da
   `"Salman has spoken the truth."`). Sistem değişikliği olduğu için sahibine soruldu, cevap bekleniyor.
3. **Takipçi başlangıç sayısını kesinleştirme:** veri 20 Ekim'de başlıyor; o günden önceki takipçi sayısı
   51–55 arası (aralık, çünkü takipçi sayısı gün içinde okunuyor). Kesin sayı için Pasifik gece yarısından
   hemen sonra (İstanbul 11:00) takipçi sayısını okuyan küçük bir zamanlanmış çalışma önerildi; onay bekliyor.
4. **Muâviye caption'ı:** önerilen caption'daki "I have not seen a teacher..." cümlesi bizim aktarımımız;
   kaynaktaki çeviriyle ("neither before him nor after him have I seen a leader who gave better instruction
   than he") değiştirilmesi önerildi.
5. **Geçici GitHub dalları:** `insights-probe` (istatistik testi, silinebilir), `diag-comments`,
   `diag-insights`, `test-reels-v2` (eski testler). `tts-work` ve `tts-out` TTS için kullanılıyor, kalsın.
   Bu oturumdan dal silmek mümkün değil (proxy yazma izni vermiyor); sahibi GitHub → Branches'tan siler.
