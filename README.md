# The Halal Algorithm — otomatik paylaşım sistemi

Instagram **@thehalalalgorithm** için her gün doğrulanmış bir ayet veya hadisi
sabit temalı bir görselle hazırlayıp belirlenen saatte paylaşan sistem.

## Nasıl çalışır

| Parça | Nerede | Ne yapar |
|---|---|---|
| İçerik ajanları (planlayıcı, küratör, metin yazarı, denetçi, görsel kontrol) | Claude zamanlanmış görevi (her gün) | Tema seçer, veritabanından içerik seçer, caption yazar, bağımsız denetimden geçirir, görseli üretip `queue/` klasörüne koyar. Talimatlar: `AGENT.md` |
| Analist | Claude zamanlanmış görevi (pazartesi) | `history/insights.json` verisini inceler, `notes/strategy.md` dosyasını günceller |
| Yayıncı | GitHub Actions, 15 dakikada bir (`publish.yml`) | Zamanı gelen gönderiyi, slot saatinin ±5 dakikası içinde rastgele seçilmiş anında Instagram'a paylaşır |
| Ana ajan | Repo bağlı herhangi bir Claude sohbeti | Sohbetle yönetim: önizleme, değiştirme, saatler, canlıya geçiş, durdurma (`AGENT.md` sonu) |
| Gece işi | GitHub Actions, her gece (`nightly.yml`) | Instagram token'ını yeniler ve sonucu kaydeder, gönderi istatistiklerini çeker |

Ayet ve hadis metinleri **yapay zekâ tarafından yazılmaz**: hepsi `data/` içindeki
veritabanından gelir ve görsele kodla basılır.

## Ayarlar — `config.yaml`

- `slots`: paylaşım saatleri; her slot kendi saat dilimiyle (ABD + Avrupa)
- `jitter_minutes`: her paylaşımın rastgele kaydırma aralığı (±dakika)
- `dry_run: true`: Instagram'a paylaşmaz; önizlemeyi ana ajandan istersin. Canlıya geçince `false` yap.
- `paused: true`: acil durdurma
- `slots[].type`: her slota ayet mi hadis mi gireceği (günde ayet / hadis / ayet / hadis)

## Kurulum

### 1. Telegram botu (isteğe bağlı — anlık hata bildirimi)
Gerekmez: sorunlar her günkü Claude çalışmasının raporunda (telefon bildirimi) görünür.
Paylaşım anında anlık uyarı istersen:
1. Telegram'da **@BotFather** → `/newbot` → botun token'ını kopyala.
2. Kendi botuna herhangi bir mesaj at.
3. Tarayıcıda `https://api.telegram.org/bot<TOKEN>/getUpdates` aç, `"chat":{"id": ...}` değerini kopyala.

### 2. Instagram API
1. developers.facebook.com → **Create App** → kullanım amacı olarak Instagram API'yi seç.
2. Uygulamada **Instagram → API setup with Instagram login** bölümüne gir.
3. Instagram Business hesabını ekle ve **Generate token** ile erişim token'ı oluştur
   (izinler: `instagram_business_basic`, `instagram_business_content_publish`,
   `instagram_business_manage_insights`).
4. Token'ı ve hesabın **Instagram user ID**'sini kopyala.

Kendi hesabın için uygulama "Development" modunda kalabilir.

### 3. GitHub Secrets
Repo → Settings → Secrets and variables → Actions → **New repository secret**:

| Ad | Değer |
|---|---|
| `IG_USER_ID` | Instagram user ID |
| `IG_ACCESS_TOKEN` | Instagram erişim token'ı |
| `TELEGRAM_BOT_TOKEN` *(isteğe bağlı)* | BotFather token'ı |
| `TELEGRAM_CHAT_ID` *(isteğe bağlı)* | getUpdates'teki chat id |
| `GH_PAT` *(isteğe bağlı)* | Bu repoda "Secrets: read and write" yetkili fine-grained token — Instagram token'ı yenilenince secret'ı otomatik günceller |

### 4. Actions'ı aç
Repo → **Actions** sekmesi → workflow'ları etkinleştir. `publish` workflow'unu
**Run workflow** ile bir kez elle çalıştırıp test et.

### 5. Canlıya geçiş
İlk hafta `dry_run: true` ile ana ajandan önizlemeleri iste ve kontrol et. Memnunsan
`dry_run: false` yap. Yeni hesap için günde 1 paylaşımla başla, 2 hafta sonra artır.

## Komutlar (elle kullanım)

```bash
cd scripts
python3 find.py search hadith "\bpatien"      # içerik ara
python3 find.py get quran:94:5-6               # tam kayıt
python3 render.py quran:94:5-6 ornek.jpg       # görsel üret
python3 enqueue.py list                        # kuyruk
python3 enqueue.py slots --days 2              # boş slotlar
```

## Kaynaklar ve lisanslar

- Hadis ve Kur'an verisi: [fawazahmed0/hadith-api](https://github.com/fawazahmed0/hadith-api),
  [fawazahmed0/quran-api](https://github.com/fawazahmed0/quran-api) (Unlicense). Yalnızca Kütüb-i Sitte
  (Buhârî, Müslim, Ebû Dâvûd, Tirmizî, Nesâî, İbn Mâce) kullanılır; Buhârî ve Müslim dışında Al-Albani / Zubair Ali Zai derecelerine göre süzülür; yalnızca sahih ve hasan kalır.
  İngilizce hadis tercümelerinin hakları çevirmenlerine aittir; her gönderide kaynak ve numara belirtilir.
- Kur'an İngilizce meali: Rowwad Translation Center, [QuranEnc.com](https://quranenc.com) — değiştirmeden yayımlanabilir. QuranEnc şartları kaynağın belirtilmesini istiyor; caption'larda yazılmadığı için profil biyografisinde belirtilmesi önerilir.
- Arapça Kur'an metni: Khaled Hosny quran-data; font: Amiri Quran.
- Fontlar: Amiri, Amiri Quran, EB Garamond, Marcellus (SIL Open Font License, `assets/fonts/OFL.txt`).
- Veritabanını yeniden üretmek için: `scripts/build_data.py`.
