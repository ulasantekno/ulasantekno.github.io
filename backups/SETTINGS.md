# UlasTekno Auto-Blog Settings Backup

> **Backup Version:** 2.0  
> **Backup Date:** 2026-05-03  
> **Purpose:** Dokumentasi lengkap semua konfigurasi supaya kalau ganti API/token tidak perlu setup dari nol.

---

## 📁 Struktur Repo

```
/home/ubuntu/ulasantekno-repo/
├── _posts/                    # Artikel Jekyll
├── _data/affiliate-links/     # Data produk affiliate
├── assets/images/posts/       # Banner artikel
├── scripts/
│   ├── auto-generate-post.py  # Script utama generate artikel (MULTI-MODE)
│   ├── auto-generate-post-top5.py  # Backup script lama (top 5 only)
│   ├── unsplash_banner.py     # Generate banner image dari Unsplash
│   └── git-push.sh            # Wrapper push aman dengan token
├── .env                       # Token & secret (DI-IGNORE GIT!)
├── .env.example               # Template .env (boleh di-commit)
├── _config.yml                # Konfigurasi Jekyll
└── backups/                   # File backup ini
    ├── SETTINGS.md
    ├── cronjob-backup.json
    └── settings-prompt.md
```

---

## 🔑 Environment Variables (.env)

| Variable | Status | Penjelasan |
|---|---|---|
| `GH_TOKEN` | **WAJIB** | GitHub PAT untuk push otomatis |
| `TELEGRAM_BOT_TOKEN` | Opsional | Token bot Telegram untuk notifikasi |
| `TELEGRAM_CHAT_ID` | Opsional | ID chat Telegram penerima notif |
| `SHOPEE_AFFILIATE_ID` | Opsional | ID affiliate Shopee |
| `UNSPLASH_ACCESS_KEY` | Opsional | API key Unsplash (sudah ada default) |

### Cara Restore .env
```bash
cd /home/ubuntu/ulasantekno-repo
cp .env.example .env
# Edit .env, isi GH_TOKEN dan variabel lainnya
nano .env
```

---

## ⏰ Cronjob Configuration

### Current Job
| Property | Value |
|---|---|
| **Job ID** | `9e39dc815c37` |
| **Name** | UlasTekno Auto-Generate Article |
| **Schedule** | `every 180m` (tiap 3 jam) |
| **Repeat** | forever |
| **Deliver** | `origin` (kirim ke Telegram chat ini) |
| **Workdir** | `/home/ubuntu/ulasantekno-repo` |
| **Skills** | (none) |
| **Model** | default |

### Cara Restore Cronjob
```bash
# Hermes Agent command:
cronjob create
# Name: UlasTekno Auto-Generate Article
# Schedule: every 180m
# Workdir: /home/ubuntu/ulasantekno-repo
# Deliver: origin
# Prompt: (paste dari backups/settings-prompt.md)
```

---

## 📝 Prompt Cronjob (Lengkap)

```
Kamu adalah bot otomasi UlasTekno. Tugasmu menjalankan auto-generate artikel blog dan kirim notifikasi ke user.

**LANGKAH WAJIB:**

1. **Sync repo terlebih dahulu:**
   ```bash
   cd /home/ubuntu/ulasantekno-repo
   git fetch origin main
   git merge origin/main --no-edit || git reset --hard origin/main
   ```

2. **Load GH_TOKEN dari .env:**
   ```bash
   export GH_TOKEN=$(grep GH_TOKEN .env | cut -d= -f2)
   ```

3. **Jalankan auto-generate:**
   ```bash
   /usr/bin/python3.12 scripts/auto-generate-post.py
   ```

4. **Baca hasil generate:**
   Cek file `.last_generate_result.json` untuk melihat status:
   ```bash
   cat /home/ubuntu/ulasantekno-repo/.last_generate_result.json 2>/dev/null || echo "No result file"
   ```

5. **Format pesan notifikasi untuk user:**
   - Kalau artikel baru berhasil: Ambil `title`, `url`, `x_caption` dari JSON
   - Format pesan dengan emoji dan HTML bold
   - Sertakan caption X/Threads yang siap copy-paste

6. **Output akhirmu HARUS berupa pesan Telegram yang lengkap.**
   Contoh format output:
   ```
   ✅ <b>Artikel Baru Terbit!</b>
   
   📌 <b>{title}</b>
   
   🔗 {url}
   
   <b>📝 Caption X/Threads (siap copy):</b>
   <pre>
   {x_caption}
   </pre>
   
   ⏳ GitHub Pages rebuild ~1-2 menit.
   ```

**CATATAN:**
- Jika output script bilang "Artikel hari ini sudah ada, skip", kirim pesan singkat: "⏭️ Artikel hari ini sudah ada, cronjob skip generate."
- Jika gagal, kirim pesan error lengkap.
- JANGAN buat artikel manual; biarkan script Python yang handle.
- Output final kamu akan otomatis dikirim ke chat Telegram user.
```

---

## 🛠️ Fitur Auto-Generate yang Sudah Aktif

| Fitur | Status | File |
|---|---|---|
| Generate artikel otomatis (MULTI-MODE) | ✅ | `scripts/auto-generate-post.py` |
| Mode: Review 1 produk | ✅ | `scripts/auto-generate-post.py` |
| Mode: Top 5 rekomendasi | ✅ | `scripts/auto-generate-post.py` |
| Mode: Perbandingan 2 produk | ✅ | `scripts/auto-generate-post.py` |
| Random mode selector tiap run | ✅ | `scripts/auto-generate-post.py` |
| Banner image dari Unsplash | ✅ | `scripts/unsplash_banner.py` |
| Fallback banner (hero-banner.jpg) | ✅ | `scripts/auto-generate-post.py` |
| Validasi file > 0 byte | ✅ | `scripts/auto-generate-post.py` |
| Push ke GitHub dengan GH_TOKEN | ✅ | `scripts/auto-generate-post.py` |
| Generate caption X/Threads | ✅ | `scripts/auto-generate-post.py` |
| Keyword Unsplash sesuai judul | ✅ | `scripts/unsplash_banner.py` |
| Git remote URL auto-clean | ✅ | `scripts/auto-generate-post.py` |

---

## 🔗 Link Penting

| Link | URL |
|---|---|
| Blog Live | https://ulasanteknoid.my.id |
| GitHub Repo | https://github.com/ulasantekno/ulasantekno.github.io |
| Archive Artikel | https://ulasanteknoid.my.id/archive.html |
| Unsplash Developers | https://unsplash.com/developers |
| Telegram BotFather | https://t.me/BotFather |
| Shopee Affiliate | https://affiliate.shopee.co.id/ |

---

## ⚠️ Hal yang Perlu Diperhatikan

1. **Jangan commit `.env` ke Git** — sudah di `.gitignore`
2. **Revoke GH_TOKEN lama** kalau pernah terekspos di chat
3. **Unsplash rate limit** — 50 request/jam untuk demo key
4. **GitHub Pages rebuild** — butuh 1-2 menit setelah push
5. **Jekyll timezone** — tanggal URL pakai UTC, bisa beda 1 hari

---

## 🔄 Checklist Ganti API/Token Baru

- [ ] Update `GH_TOKEN` di `.env`
- [ ] Update `TELEGRAM_BOT_TOKEN` di `.env` (kalau ada)
- [ ] Test push manual: `./scripts/git-push.sh "test"`
- [ ] Test generate: `python3 scripts/auto-generate-post.py`
- [ ] Cek banner: `python3 scripts/unsplash_banner.py test "Test" Gadget default`
- [ ] Verify cronjob masih aktif: `cronjob list`
- [ ] Cek blog live: https://ulasanteknoid.my.id

---

*Backup dibuat otomatis oleh Hermes Agent.*
