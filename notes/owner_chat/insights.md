# İstatistikler: altyapı, sınırlar, bulgular

Ayrıntılı haftalık analiz `notes/strategy.md`'de (analist her pazartesi günceller). Bu dosya sahibinin
sohbetinde öğrenilenleri toplar.

## Veri nereden geliyor

`scripts/insights.py` (GitHub `nightly.yml`, günde iki kez: 22:41 ve 10:41 UTC):
- `history/insights.json`: son 45 günün her paylaşımı (reach, views, likes, comments, saved, shares,
  Reels'te ortalama izlenme ve atlanma), hesap bloğu (takipçi, kitle dağılımı, çevrimiçi saatler),
  `manual_posts` (sistemin paylaşmadığı, sahibinin elle paylaştığı gönderiler; hesabın medya listesinden),
  `followers_check` (aşağıda).
- `history/account_daily.jsonl`: 20 Ekim 2026'dan dünkü güne her Instagram günü (Pasifik saati gece
  yarısından gece yarısına) tek başına: follows, unfollows, reach_total, reach_followers,
  reach_non_followers, views_total, accounts_engaged. Son 7 gün her çalışmada yeniden ölçülür.
- `history/followers.jsonl`: her çalışmada takipçi sayısı ve okuma zamanı.
- `history/story_insights.jsonl`: Story'ler (24 saat içinde okunabiliyor).

## 10 Kasım düzeltmesi (sahibinin fark ettiği hata)

Eski kod günü `since = gece yarısı, until = ertesi gece yarısı` diye istiyordu; Instagram `until`'in gününü
de dahil sayıyor, yani her gün ertesi günü de içeriyordu (3 Kasım "100 takip" = 46 + 54). GitHub'da test
edildi (`insights-probe` dalı): `until = ertesi gece yarısı − 1 sn` Instagram'ın kendi günlük serisiyle
(reach, follower_count) her gün birebir aynı. Kod düzeltildi, 20 Ekim'den beri bütün günler yeniden çekildi.
Gönderi bazlı sayılar etkilenmedi.

**Kalıcı kontrol (`followers_check`):** her takipçi sayısı okuması, o güne kadarki net takipten çıkarılınca
"20 Ekim öncesi takipçi" için bir aralık verir; bütün aralıklar ortak bir sayıda kesişmeli (şu an 51–55) ve
her gün Instagram'ın günlük serisiyle aynı olmalı. Tutmazsa nightly açık sorun kaydeder ("Hesap
istatistikleri tutarsız"). Analist kuralı: `followers_check.ok` false ise hesap düzeyindeki sayıları yazma.

**Neden ders:** ilk analizde ve analist raporunda API sayıları hiç sağlaması yapılmadan kullanıldı; analist
aynı cümlede "121 → 335 takipçi" ve "net +398" yazmıştı. Bir sayıyı yazmadan önce onu doğrulayan başka bir
sayıyla karşılaştır.

## Bilinen API sınırları

- Instagram API bir günün takip sayısını ancak gün bitince veriyor ("bugün" 0 döner); uygulamadaki canlı
  "net takipçi" API'de yok. Canlı olan tek şey toplam takipçi sayısı: günlük net = gün sonu − gün başı.
  Kesin günlük net / kesin başlangıç için takipçi sayısını gece yarısında okumak gerekir (öneri, onay bekliyor).
- Veri 20 Ekim'de başlıyor: ilk gönderi Instagram saatiyle 20 Ekim 17:26 (İstanbul 21 Ekim 03:26);
  12–19 Ekim her şey 0.
- Reels başına `follows` / `profile_visits` dönmüyor; `reposts` hiç dönmüyor.
- Instagram'ın "ses kullanılamıyor" uyarısıyla arşive alınan gönderinin istatistiği boş (49:12, 6 Kas).

## Bulgular (11 Kasım'a kadar)

- **Büyüme tamamen keşiften:** erişimin ~%99'u takipçi olmayanlardan. Takip, erişimle birlikte artıyor
  (günlük takip ↔ takipçi-dışı erişim korelasyonu 0,89); 1.000 takipçi-dışı erişim başına ~4,1 takip.
- Takipçi: 26 Eki 58 → 2 Kas 121 → 9 Kas 335 → 11 Kas 447. 1-7 Kasım net +202 (önceki hafta +57).
- **Format:** fotoğraf gönderileri ~0 (30 Ekim'de bırakıldı); carousel üç denemede de 50 erişimin altında
  (10 Kasım'da kapatıldı); hadis Reels'i ayet Reels'inin ~%30'u (reel-us 10 Kasım'dan beri ayet).
- **Elle quiz'ler:** Guess the Surah aynı yaştaki ayet Reels'inin ~1,8 katı erişim aldı; yorum ve
  takip/görüntüleyen oranı en yüksek format (ikinci quiz %0,99). Trivia zayıf (~1.100 erişim). Tesbih en
  yüksek kayıt ve paylaşım (47 / 31) ama atlanma yüksek. Sesli mesaj 17:32: 1. günde 2.320 erişim, 32 kayıt,
  17 paylaşım (iyi).
- **Konu:** tanınan kısa sureler (Nâs, Felak, Kevser), peygamber duaları, günlük hayata dokunan pratik ahlak
  ayetleri (49:6 haber doğrulama, 17:23) en iyi; soyut ahlak hadisleri en zayıf.
- **Saat:** slot farkları küçük; takipçilerin çevrimiçi saati belirleyici değil (erişim takipçi dışından).
- **Kâri:** Alafasy en iyi (atlanma en düşük); Abdul Basit en zayıf.

## İstatistik panosu (artifact)

"Halal Algorithm Insights" — https://claude.ai/artifact/KZ1WE7TDMVcAPgXY38X1wx. Dashboard türünden;
veri kümeleri dosya olarak artifact'a yüklü (`Artifact` publish `asset: true` ile yükle, sonra
`ArtifactData` ile `datasets/<id>` → `source.url` güncelle; her yazımda `edit` ve `updated` damgası).
Veri kümeleri: `account`, `audience`, `daily` (10 Kas düzeltilmiş veriyle), `manual`, `online`, `reels`.
Hazırlama betikleri `notes/owner_chat/dashboard/`: `series.py` (git geçmişinden her gönderinin zaman içindeki
okumaları) → `build.py` (gönderi satırları, 24. saate enterpolasyon) → `analyze.py` (`res.json`: format,
kategori, slot, kâri karşılaştırmaları). Artifact'ın sayfası ve veri kümesi tanımlarının son hali
`dashboard/docs/` içinde (`files_index.html.json` = sayfa).
