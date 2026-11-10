# Strateji notları

Analist her pazartesi bu dosyayı günceller.

## Güncel durum (2026-11-09, veri: insights.json 2026-11-09 01:58 UTC)

Kapsam: 1-8 Kasım Reels'leri; ortalamalara yalnızca en az 24 saatlik paylaşımlar katıldı (yaş = `fetched_at` −
`posted_at`). Hesap: **335 takipçi** (2 Kasım: 121). `online_followers_by_utc_hour` artık geliyor. Reels'lerde
gönderi başına `follows` / `profile_visits` hâlâ yok; `reposts` hiç dönmüyor. 2026-11-06_reel-eu (49:12) için
Instagram hiç istatistik vermiyor (56 saatlik, `stats: {}`): ortalamalardan çıkarıldı, açık sorun S-015.

| Tür (1-8 Kas, 24 sa+) | n | Yaş | Ort. reach | Ort. kayıt | Ort. paylaşım | Kayıt/reach | Paylaşım/reach | Ort. izlenme | İzlenme/süre | Atlanma |
|---|---|---|---|---|---|---|---|---|---|---|
| Reels, ayet (tilavetli) | 21 | 32-187 sa | 1796 | 29.1 | 10.7 | %1.62 | %0.59 | 6.6 sn | %30 | %66.0 |
| Reels, hadis (sessiz) | 7 | 24-193 sa | 556 | 4.6 | 2.9 | %0.82 | %0.51 | 3.7 sn | %30 | %67.9 |
| Carousel (4 Kas) | 1 | 99 sa | 37 | 0 | 0 | 0 | 0 | - | - | - |

| Slot (1-8 Kas, 24 sa+) | n | Yaş | Ort. reach | Kayıt/reach | Paylaşım/reach | İzlenme | Atlanma | Takipçi online (UTC saat) |
|---|---|---|---|---|---|---|---|---|
| reel-eu-am (08:15 Berlin = 07:15 UTC) | 7 | 43-187 sa | 1493 | %1.48 | %0.48 | 6.5 sn | %66.3 | 156 (zirve) |
| reel-pk (20:30 Karaçi = 15:30 UTC) | 7 | 34-178 sa | 1980 | %1.64 | %0.41 | 6.7 sn | %65.7 | 81 |
| reel-eu (13:00 New York = 18:00 UTC) | 6 | 32-176 sa | 1931 | %1.72 | %0.93 | 6.7 sn | %66.4 | 70 (en düşük) |
| reel-us (20:30 New York = 01:30 UTC, hadis) | 7 | 24-193 sa | 556 | %0.82 | %0.51 | 3.7 sn | %67.9 | 144 |

reel-pk ortalamasını Nâs (5691, sahibinin seçimi) yukarı çekiyor; Nâs hariç reel-pk 1361.

- **Büyüme (2026-11-10'da düzeltildi):** 1-7 Kasım **208 yeni takip, 6 takipten çıkma (net +202)**; önceki hafta
  (25-31 Ekim) net +57. Günlük erişim ort. 6.4 bin (önceki hafta 2.6 bin), etkileşen hesap günde 708 (316). Erişimin
  **%99'u takipçi olmayanlardan**: büyüme hâlâ tamamen keşiften. En iyi günler 4 Kasım (54 takip) ve 3 Kasım (46):
  Nâs/Felak Reels'leri ve iki elle quiz denemesinin olduğu günler. Takipçi sayısıyla tutarlı: 2 Kasım 121 → 9 Kasım 335.
  (Bu maddenin ilk hali hatalı veriyle yazılmıştı: eski `insights.py` her güne ertesi günü de ekliyordu; 408 / +398 /
  12.2 bin / 1371 / 100 / 88 yanlıştı.)
- **Kitle:** takipçilerin %20'si Hindistan, %15'i Pakistan, sonra S. Arabistan, İngiltere, ABD, BAE; etkileşenlerin
  %40'ı Hindistan. Yaş ağırlıkla 25-34 (takipçi) ve 18-34 (etkileşen); erkek ağırlıklı.
  Takipçiler en çok **04-10 UTC** arası çevrimiçi (156-173), en az **15-19 UTC** (63-81).
- **Hadis Reels'i yine düştü:** v3'te 5 Reels (48 sa+) ort. 416 reach, kayıt/reach %0.77, paylaşım/reach %0.34;
  v2'nin son üç hadis Reels'i (30 Eki-1 Kas) ort. 864. En iyi hadis 4835 (işleri kolaylaştırmak, 727). Ayetin ~%30'u.
- **İzleyiciyi tutma:** ayet ve hadis Reels'inde izlenme videonun ~%30'u, atlanma %66-68 (ilk 3 sn kayıp büyük).
  30 sn üstü 4 ayet Reels'i (Nâs, 49:6, Ayyub 21:83-84, 6:162-163) ort. 3059 reach, kayıt/reach %2.08, izlenme 11.6 sn:
  uzun video cezalandırılmıyor, güçlü içerikte izlenme süresi uzuyor. 20 sn altı ve 20-30 sn grupları aynı (~1455).
- **Şablon v3 karşılaştırması (her iki taraf 48 sa+):**

  | Grup | n | Yaş | Ort. reach | Kayıt/reach | Paylaşım/reach | İzlenme | Atlanma |
  |---|---|---|---|---|---|---|---|
  | Ayet v2 (30-31 Eki) | 6 | 201-235 sa | 1331 | %1.57 | %0.45 | 6.0 sn | %63.9 |
  | Ayet v3 (sahibinin seçimleri hariç) | 14 | 58-187 sa | 1484 | %1.65 | %0.63 | 6.0 sn | %67.2 |
  | Hadis v2 (30 Eki-1 Kas) | 3 | 193-242 sa | 864 | %1.20 | %0.85 | 4.1 sn | %66.0 |
  | Hadis v3 | 5 | 48-168 sa | 416 | %0.77 | %0.34 | 3.6 sn | %69.2 |

  Ayette reach, kayıt ve paylaşım oranı biraz daha iyi, izlenme aynı, **atlanma ~3 puan kötü**. Hesap bu arada 2.5 kat
  büyüdü, tema/kâri da farklı; erişim farkı şablona bağlanamaz. Atlanmadaki artış ilk karede (kanca + üst etiket)
  bir şeyin eskisi kadar tutmadığını düşündürüyor ama kanıt zayıf. Hadiste her ölçüm kötüleşti (n=3 vs 5).
  Şablon için karar önerilmiyor; 16 Kasım'da yeniden bak.
- **Story (Reels'in kopyası):** 24 saatini dolduran 4 Story ort. 15 reach (8-19); 0 takip, 0 yanıt. Gezinme: 49 ileri
  dokunma, 9 kaydırma, 8 çıkış. Maliyeti yok, devam.
- **Kâri (30 Eki+, 48 sa+):** Alafasy n=6 ort. 2372 (Nâs dahil; hariç 1708), atlanma %62.9 (en düşük); Sudais n=3
  1746; Dosari n=4 1479; Abdul Basit n=3 1340, atlanma %71.0 ve izlenme oranı %23 (en zayıf); Muaiqly n=5 1214.
  Minshawi ve Husary birer Reels ile en yüksek kayıt oranları (%3.6, %2.6) ama n=1. Ağırlıklar değiştirilmedi
  (tema etkisi baskın, n küçük); Abdul Basit bir hafta daha zayıf kalırsa ağırlığı 3 → 2 düşünülsün.

### En iyi 3 tema (Reels, reach, 1-8 Kasım, 24 sa+)
1. Nâs suresi / vesveseden Allah'a sığınmak (114:1-6, reel-pk, sahibinin seçimi): 5691 reach, 74 kayıt, 18 paylaşım
2. Haberi paylaşmadan önce doğrulamak (49:6, reel-eu): 3408 reach, 80 kayıt, **49 paylaşım** (32 saatlik, hâlâ artıyor)
3. Allah Latîf'tir / rızık (42:19, reel-eu-am): 2270 reach, 38 kayıt, 21 paylaşım

Yakından izleyenler: Eyyub'un duası / sıkıntı (21:83-84): 1880 reach, **67 kayıt** (%3.6); Felak (113:1-5): 1907;
Kevser 1827. 2:152 (zikir) 19 saatte 58 paylaşım aldı (henüz 24 saat değil). Ortak çizgi: tanınan kısa sureler,
peygamber duaları ve günlük hayata doğrudan dokunan pratik ayetler ("birine gönder" etkisi: 49:6, 17:23).

### En zayıf 3 tema (Reels, reach, 1-8 Kasım, 24 sa+)
1. Kalp ve ameller, görünüş değil (hadis, Müslim 6543): 301
2. Hayır söyle ya da sus (hadis, İbn Mâce 3971): 327, atlanma %73.8
3. Yoldan eziyeti kaldırmak (hadis, Buhari 2472): 336

En zayıf üçü de hadis. En zayıf ayet: ölümü hatırlatma (29:57, reel-pk): 1081 reach, 0 paylaşım.

### Önerilen tür oranı
- Şimdilik 3 ayet + 1 hadis Reels; ama hadis slotu ayetin ~%30'unda ve düşüyor. **Sahibine öneri:** reel-us'u bir
  hafta ayet Reels'i (ya da elle quiz denemesi) olarak denemek; kararı ana ajan/sahibi verir (analist slot türünü
  değiştirmez).
- Ayet Reels'inde tanınan kısa sureler, peygamber duaları (Eyyub, Yunus, Adem, Zekeriya) ve pratik, paylaşılabilir
  ahlak ayetleri (49:6, 17:23) öncelikli. 30 sn üstü güçlü metinlerden kaçınmaya gerek yok.
- Hadis Reels'inde öfke (Müslim 6643, 1368) ve kolaylaştırma (4835, 727) gibi somut, günlük tavsiyeler soyut
  ahlak hadislerinden iyi.
- **Carousel:** üçüncü örnek (4 Kas) de 37 reach (eşik 50). Üç denemede de Reels'in %3'ünün altında. Öneri: sahibi
  onaylarsa haftalık carousel'i Reels'e (ya da quiz Reels'ine) çevirmek.
- **Quiz Reels'leri (elle):** iki denemede takip / görüntüleyen %0.54 ve %0.99, ayet Reels'inden yüksek. Haftada 1-2
  quiz denemesine devam önerilir (3-5 örnekle karar).


### Format karşılaştırması: fotoğraf, Reels, carousel (sahibinin isteğiyle ek analiz, 2026-10-29)

Soru: 30 Ekim'de fotoğraf gönderilerini bırakıp günde 4 Reels + haftalık carousel'e geçmeyi veri
destekliyor mu? Veri: 24 saatten eski 43 paylaşım (20-28 Ekim).

| Format | n | Reach / gönderi | Views | Beğeni | Kayıt | Paylaşım | Toplam reach |
|---|---|---|---|---|---|---|---|
| Fotoğraf (ayet + hadis) | 30 | 8.3 | 15.5 | 0.27 | 0 | 0 | 249 |
| Reels (hepsi) | 12 | 615.2 | 710.8 | 67.9 | 6.58 | 3.83 | 7382 |
| · ayet Reels'i | 7 | 904.6 | 1042.6 | 113.3 | 10.7 | 5.1 | |
| · hadis Reels'i | 5 | 210.0 | 246.2 | 4.4 | 0.8 | 2.0 | |
| Carousel | 1 | 8.0 | 21.0 | 0 | 0 | 0 | 8 |

- Aynı günler (27-28 Ekim): fotoğraf ort. 5.5 reach, Reels ort. 1041. Fark tek bir iyi günden gelmiyor.
- 30 fotoğraf gönderisinin toplamı 249 reach, 0 kayıt, 0 paylaşım; 12 Reels'in toplamı 7382 reach,
  79 kayıt, 46 paylaşım. En zayıf Reels (117) bile en iyi fotoğraf gönderisinden (22) 5 kat fazla.
- Fotoğraf erişimi hafta boyunca ~20'den ~5'e düştü; takipçiye günde çok gönderi düşmesi bunu
  açıklıyor olabilir. Takipçi 26 Ekim'de 58, 29 Ekim'de 87: artış, Reels'in büyüdüğü günlere denk geliyor.
- **Takip / gönderi ve izlenme süresi ölçülemedi:** `insights.py` bu metrikleri çekmiyor (açık sorun
  kaydedildi). Takip etkisi için yalnızca hesap düzeyindeki takipçi artışı var.
- Carousel n=1 (8 reach, fotoğraf düzeyinde); hüküm vermek için erken.

**Sonuç: Veri değişikliği açıkça destekliyor.** Reels gönderi başına yaklaşık 74 kat erişim alıyor;
kayıt ve paylaşımın tamamı Reels'ten geliyor. Fotoğraf gönderilerinin hiçbir metrikte katkısı yok.
Çekince: hadis Reels'i ayet Reels'inin ~1/4'ü; dördüncü Reels'in hadis olması en zayıf halka, ama yine
de fotoğraf gönderisinden ~25 kat iyi. Carousel 4 Kasım'daki ikinci örnekten sonra değerlendirilsin;
o da 50 reach'in altında kalırsa Reels'e çevrilmesi düşünülsün.


### Saat önerisi
**Değişiklik yok.** Son saat değişikliği 30 Ekim'de yürürlüğe girdi (reel-eu-am); 14 gün 13 Kasım'da doluyor.
Kanıt da değişikliği gerektirmiyor: `online_followers` 04-10 UTC'de zirve, 15-19 UTC'de dip gösteriyor, ama en iyi
iki slot (reel-eu 18:00 UTC, reel-pk 15:30 UTC) tam dip saatlerde. Erişimin %99'u takipçi olmayanlardan geldiği için
takipçilerin çevrimiçi saati belirleyici değil. Hindistan/Pakistan akşamı (reel-pk) kitleye uygun. 16 Kasım'da
reel-us'un (01:30 UTC) hadis mi saat mi yüzünden zayıf olduğunu ayırmak için önce tür denemesi önerilir.

## Elle yapılan testler (sistem dışı; 10 Kasım'dan beri nightly `manual_posts` olarak izler)

Bu paylaşımlar `history/posted.jsonl`'da yok. 10 Kasım'dan itibaren gece toplama bunları kendisi bulur (`insights.json` → `manual_posts`); ilk iki satır Instagram'ın gönderi istatistiklerinden elle alındı.
Karşılaştırırken aynı yaştaki Reels'leri kullan.

| Tarih | Ne | Yaş | Görüntüleme | Görüntüleyen | Beğeni | Yorum (kişi) | Kayıt | Paylaşım | Takip | Takip / görüntüleyen |
|---|---|---|---|---|---|---|---|---|---|---|
| 2026-11-03 ~17:30 İst. | "Guess the Surah" quiz (3 soru: Felak 1-2, Bakara 2:201, Enbiyâ 21:88; Sudais; 48,7 sn) | 20 sa | 1894 | 1664 | 110 | 3 | 9 | 2 | 9 | %0.54 |
| 2026-11-04 ~17:30 İst. | Quiz 2: "Can you name all 4 Surahs?" (Yâsîn 36:82, İhlâs 1-2, İnşirâh 5-6, Ankebût 29:2; orta-kolay-orta-zor; Sudais; ölçülmüş kelime zamanlaması; cevapta meal; finalde cevaplar ve paylaşım çağrısı; 62 sn) | 27 sa | 4068 | 3440 | 286 | 3 | 18 | 16 | 34 | %0.99 |
| karşılaştırma | Kevser 108:1-3 (Reels) | 22 sa | 2033 | 1742 | 273 | 0 | 19 | 2 | 4 | %0.23 |
| karşılaştırma | Nâs 114:1-6 (Reels) | 22 sa | 4373 | 3723 | 379 | 1 | 55 | 15 | 26 | %0.70 |

İlk quiz: erişim olağan Reels düzeyinde (patlama yok), beğeni ve kayıt oranı düşük, ama yorum ve takip / görüntüleyen
oranı ayet Reels'inin ortalamasının üstünde. Tek örnek; karar için 3-5 deneme gerekir.
Uygulama istatistikleri (sahibinin ekran görüntüleri, 2026-11-04): ortalama izlenme 10 sn (48 sn videoda %21; aynı
günlerde ayet Reels'i 5,8-7,5 sn, Nâs 12,1 sn), geçme oranı %62,9 (Instagram: tipik Reels'inden "daha düşük", yani iyi),
yorum oranı %0,4 ("daha yüksek"); paylaşım %0,1, beğeni %6,6, kayıt %0,5 tipikten düşük. Tutma eğrisi: 3. saniyede %40,
sonra neredeyse düz (~%20 sona kadar izliyor). Kaynak: Reels sekmesi %77,9, Keşfet %19,7. Sonuç: kalanlar sonuna kadar
izliyor; kayıp ilk 3 saniyede ve paylaşım yok denecek kadar az.
Quiz 2 (uygulama, 2026-11-05 20:25): ortalama izlenme 16 sn, geçme %58,5 (tipikten iyi), paylaşım %0,4 ve yorum %0,2
(ikisi de tipikten yüksek), beğeni %8,0 ve kayıt %0,5 (tipikten düşük); 3. saniyede %46, sonra ~%25 sona kadar; 27. saatte
hâlâ yükseliyor (tipik Reels 1. günden sonra düzleşiyor). Takip / görüntüleyen %0,99: şimdiye kadarki en yüksek Reels.

## Değişiklik notları
- 2026-10-26: İlk haftalık analiz. Saat değişikliği yok (kanıt zayıf, online_followers yok).
- 2026-10-29: İkinci haftalık analiz. Ayet Reels'i yeni slotlarda ~5 kat büyüdü; saat değişikliği yok (slotlar 27 ve 30 Ekim'de değişti, 14 gün dolmadı).
- 2026-10-29 (ek çalışma): Fotoğraf / Reels / carousel karşılaştırması eklendi; veri 30 Ekim geçişini destekliyor. config.yaml'a dokunulmadı.
- 2026-11-01: **Reels şablonu v3'e geçti** (sahibinin kararı). İlk v3 Reels: 2026-11-01_reel-eu-am (Muhammed 47:7) ve o günün diğer üç Reels'i. Değişenler: etiket altında ilerleme çizgisi; ayette tam meal baştan soluk, okunan ayetin kelimeleri yanar; referans mealin hemen altında; okuma boyunca sabit slogan ("Follow & Share The Qur'an" / "... The Sunnah"), sonra kapanış cümlesi; hesap adı 27 punto; sonda kalan metin 0,5 sn'de yanar. Video süresi aynı (ayet +3,2 sn, hadis +3,0 sn). **Haftalık analizde karşılaştır:** 2026-10-30..10-31 Reels'leri (v2) ile 2026-11-01'den itibaren yayınlananlar (v3; posted.jsonl `posted_at` 2026-11-01 ve sonrası) arasında reels_skip_rate, ig_reels_avg_watch_time, follows/reach ve shares/reach; ayrıca account_daily.jsonl'de günlük follows. En az 7 gün v3 verisi birikmeden şablon hakkında karar önerme; tema/kâri/saat farkını da hesaba kat.
- 2026-11-02: Üçüncü haftalık analiz. Takipçi 87 → 121; erişimin %99'u keşiften. Hadis Reels'i 627 ort. reach'e çıktı (slot değişikliği önerisi geri çekildi). Carousel iki örnekte de ~10 reach: Reels'e çevrilmesi önerildi. v3 şablonu için veri yetersiz (9 Kasım'da bakılacak). Saat değişikliği yok (14 gün dolmadı), config.yaml'a dokunulmadı.
- 2026-11-09: Dördüncü haftalık analiz. Takipçi 121 → 335 (net +202/hafta; ilk yazılan +398 hatalı veriydi, 2026-11-10'da düzeltildi), erişimin %99'u keşiften. En iyi temalar Nâs, 49:6 (haber doğrulama), 42:19; en zayıf üçü hadis Reels'i (v3'te ort. 416). Şablon v3: ayette atlanma ~3 puan kötü, diğer ölçümler aynı ya da iyi; karar yok. Carousel üçüncü kez eşiğin altında (37). 49:12 Reels'inin istatistiği yok (S-015). Saat değişikliği yok (14 gün 13 Kasım'da doluyor; online saatler en iyi slotlarla çelişiyor), config.yaml'a dokunulmadı.
- 2026-11-10 (sahibinin kararları): S-015 kapatıldı: 2026-11-06_reel-eu (49:12) Reels'ini sahibi Instagram'ın "ses kullanılamıyor" uyarısı yüzünden arşive aldı; istatistiği bu yüzden boş, analizlere katma. **reel-us 2026-11-09 slotundan (10 Kasım 04:30 İstanbul) itibaren ayet**; kuyruktaki iki hadis (İbn Mâce 1847, Buhârî 13) çıkarıldı (hadis Reels'i v3'te ayetin ~%30'unda kaldı; hadis artık yalnızca sahibi isteyince). **Haftalık carousel kapatıldı** (üç denemede de 50 erişimin altında). 16 Kasım analizinde reel-us'un ayet olarak diğer slotlarla karşılaştırmasını yap (saat etkisini tür etkisinden ayırmak için).
- 2026-11-10: **Hesap istatistikleri düzeltildi** (sahibinin fark ettiği hata). `insights.py` günlük sayıları Instagram'dan "bu gece yarısından ertesi gece yarısına" diye istiyordu; Instagram bitiş gününü de dahil saydığı için her gün ertesi günün takip, erişim, görüntüleme ve etkileşen sayılarını da içeriyordu. Artık her gün tek başına ölçülüyor, 20 Ekim'den beri bütün günler yeniden çekildi ve her çalışmada takipçi sayısıyla ve Instagram'ın kendi günlük serisiyle karşılaştırılıyor (tutmazsa açık sorun). Gönderi bazlı sayılar (reach, kayıt, izlenme, atlanma) bu hatadan etkilenmedi. 1.000 takipçi-dışı erişim başına takip oranı ~4.1 olarak aynı kaldı (iki taraf birlikte şişmişti).
