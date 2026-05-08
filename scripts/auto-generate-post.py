#!/usr/bin/env python3
"""Auto-generate blog posts from affiliate data — MULTI-MODE.
Modes: single review | top 5 | compare (2 products)
Runs every 3 hours via cron. Randomly picks mode each run.
"""

import json
import random
import os
import subprocess
import urllib.request
import urllib.parse
import re
import sys
from datetime import datetime
from pathlib import Path

# ─── CONFIG ──────────────────────────────────────────────────────────
REPO_PATH = Path(__file__).parent.parent
POSTS_DIR = REPO_PATH / "_posts"
DATA_DIR = REPO_PATH / "_data" / "affiliate-links"
CATEGORIES = {
    "gadget": "Gadget",
    "audio": "Audio",
    "smart-home": "Smart Home",
    "lifestyle": "Lifestyle",
    "beauty-tech": "Beauty Tech"
}
STATE_FILE = REPO_PATH / ".auto-generate-state.json"
DRY_RUN = "--dry-run" in sys.argv or os.environ.get("DRY_RUN") == "1"
NO_PUSH = "--no-push" in sys.argv or os.environ.get("NO_PUSH") == "1"
FORCED_MODE = next((arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--mode=")), None)

# ─── SHARED UTILITIES ────────────────────────────────────────────────

def load_products():
    products = []
    for category_file in DATA_DIR.glob("*.json"):
        if category_file.name == "affiliate-links.json":
            continue
        try:
            with open(category_file) as f:
                data = json.load(f)
                for p in data.get("products", []):
                    p = dict(p)  # avoid mutating source data
                    p["category"] = CATEGORIES.get(category_file.stem, p.get("category", "Gadget"))
                    p["source_file"] = category_file.name
                    products.append(p)
        except Exception as e:
            print(f"Error loading {category_file}: {e}")
    return products

def load_state():
    if not STATE_FILE.exists():
        return {"used_single_ids": [], "used_compare_pairs": [], "used_top5_sets": []}
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"⚠️ State unreadable, resetting: {e}")
        return {"used_single_ids": [], "used_compare_pairs": [], "used_top5_sets": []}
    state.setdefault("used_single_ids", [])
    state.setdefault("used_compare_pairs", [])
    state.setdefault("used_top5_sets", [])
    return state

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def product_key(product):
    return product.get("id") or generate_slug(product.get("name", "unknown"))

def compare_pair_key(a, b):
    return "|".join(sorted([product_key(a), product_key(b)]))

def existing_posts_text():
    chunks = []
    for post in POSTS_DIR.glob("*.md"):
        try:
            chunks.append(post.read_text(encoding="utf-8"))
        except UnicodeDecodeError:
            chunks.append(post.read_text(errors="ignore"))
    return "\n".join(chunks)

def is_product_already_covered(product, haystack=None):
    haystack = existing_posts_text() if haystack is None else haystack
    key = product_key(product)
    name = clean_product_name(product.get("name", ""))
    raw_name = product.get("name", "")
    tokens = [t for t in {key, name, raw_name} if t and len(t) >= 8]
    return any(t in haystack for t in tokens)

def select_fresh_single(products):
    state = load_state()
    used = set(state.get("used_single_ids", []))
    haystack = existing_posts_text()
    fresh = [p for p in products if product_key(p) not in used and not is_product_already_covered(p, haystack)]
    if not fresh:
        # All/most products have been covered; recycle safely without same-product spam in the state cycle.
        state["used_single_ids"] = []
        save_state(state)
        fresh = [p for p in products if not is_product_already_covered(p, haystack)] or products
    return random.choice(fresh)

def mark_single_used(product):
    state = load_state()
    used = state.setdefault("used_single_ids", [])
    key = product_key(product)
    if key not in used:
        used.append(key)
    save_state(state)

def mark_compare_used(a, b):
    state = load_state()
    pairs = state.setdefault("used_compare_pairs", [])
    key = compare_pair_key(a, b)
    if key not in pairs:
        pairs.append(key)
    save_state(state)

def mark_top5_used(selected):
    state = load_state()
    sets = state.setdefault("used_top5_sets", [])
    key = "|".join(sorted(product_key(p) for p in selected))
    if key not in sets:
        sets.append(key)
    save_state(state)


def send_telegram_notification(message):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '1785346764')
    if not token:
        env_file = REPO_PATH / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        token = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                    elif line.startswith('TELEGRAM_CHAT_ID='):
                        chat_id = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
    if not token:
        print("ℹ️ No Telegram bot token configured")
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML", "disable_web_page_preview": True}
    try:
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            return response.status == 200
    except Exception as e:
        print(f"⚠️ Telegram error: {e}")
    return False


def yaml_quote(value):
    """Return a safe double-quoted YAML scalar."""
    text = str(value).replace('\\', '\\\\').replace('"', '\\"')
    return f'"{text}"'

def format_price(price):
    return f"Rp {price:,.0f}".replace(",", ".")


def sanitize_title_for_yaml(title):
    """Remove characters that break YAML double-quoted strings."""
    return title.replace('"', '').replace('\\', '')


def generate_slug(name):
    slug = name.lower()
    slug = re.sub(r'[!?—–\"\'():]+', '', slug)
    slug = slug.replace(" ", "-").replace("/", "-").replace("'", "").replace('"', "").replace("&", "dan")
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:50]


def clean_product_name(name):
    """Remove marketing fluff from product names. Keep only product name + model."""
    import re
    # Remove bracketed content: [BARU], [ONLINE EXCLUSIVE], [specs...]
    name = re.sub(r'\[.*?\]', '', name)
    # Remove parenthetical marketing fluff
    name = re.sub(r'\(.*?\)', '', name)
    # Remove common marketing keywords (case-insensitive)
    marketing_words = [
        r'\bONLINE EXCLUSIVE\b', r'\bOFFICIAL\b', r'\bGARANSI\b',
        r'\bDISKON\b', r'\bPROMO\b', r'\bBEST SELLER\b',
        r'\bTERLARIS\b', r'\bHEMAT\b', r'\bDIJAMIN\b',
        r'\bTERMURAH\b', r'\bORIGINAL\b', r'\bRESMI\b',
        r'\bREADY STOCK\b', r'\bGRATIS\b', r'\bBONUS\b',
    ]
    for word in marketing_words:
        name = re.sub(word, '', name, flags=re.IGNORECASE)
    # Remove leftover separators that might fragment the name
    for sep in [' - ', ' | ', ' / ']:
        if sep in name:
            parts = name.split(sep)
            # Keep the shortest reasonable part that looks like a product name
            # (not empty, not just specs)
            for part in parts:
                part = part.strip()
                if len(part) > 3 and not re.match(r'^[\d,\.\s]+$', part):
                    name = part
                    break
            break
    # Clean up extra spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def extract_features_from_name(name):
    features = []
    nu = name.upper()
    m = re.search(r'(\d+)\s*mAh', name, re.I)
    if m: features.append(f"Kapasitas baterai {m.group(1)}mAh")
    m = re.search(r'(\d+)\s*W', name, re.I)
    if m and int(m.group(1)) >= 10: features.append(f"Daya {m.group(1)}W")
    if any(x in nu for x in ['ANC','NOISE CANCELLING']): features.append("Active Noise Cancellation")
    if any(x in nu for x in ['BLUETOOTH','WIRELESS']): features.append("Konektivitas nirkabel")
    if 'RGB' in nu: features.append("Lampu RGB customizable")
    if '5G' in nu: features.append("Support jaringan 5G")
    if any(x in nu for x in ['USB-C','TYPE-C','TYPE C']): features.append("Port USB Type-C")
    if any(x in nu for x in ['FAST CHARGING','QUICK CHARGE','PD']): features.append("Teknologi fast charging")
    if any(x in nu for x in ['4K','UHD','HDR']): features.append("Resolusi tinggi (4K/UHD/HDR)")
    if any(x in nu for x in ['IP67','IP68','WATERPROOF']): features.append("Tahan air dan debu")
    if 'GAMING' in nu: features.append("Optimasi untuk gaming")
    if 'KONDENSOR' in nu or 'CONDENSER' in nu: features.append("Mic tipe kondensor")
    if 'DYNAMIC' in nu: features.append("Mic tipe dynamic")
    if 'DOLBY' in nu: features.append("Dolby Audio support")
    if any(x in nu for x in ['LOSSLESS','HI-RES']): features.append("Audio Hi-Res / Lossless")
    if any(x in nu for x in ['INTEGRATED','BUILT-IN']): features.append("Kabel built-in")
    if any(x in nu for x in ['MAGNETIC','MAGSAFE']): features.append("Desain magnetic attachment")
    m = re.search(r'(\d+)\s*Hz', name, re.I)
    if m and int(m.group(1)) >= 90: features.append(f"Refresh rate {m.group(1)}Hz")
    m = re.search(r'(\d+)[/](\d+)[Gg][Bb]', name, re.I)
    if m: features.append(f"RAM {m.group(1)}GB / Storage {m.group(2)}GB")
    m = re.search(r'(\d+(?:\.\d+)?)\s*mm', name, re.I)
    if m and any(x in nu for x in ['DRIVER','EARPHONE','TWS','BUDS']):
        features.append(f"Driver {m.group(1)}mm")
    if 'STAND' in nu: features.append("Dilengkapi stand/holder")
    return features


def generate_specs_bullets(name):
    feats = extract_features_from_name(name)
    if len(feats) < 3:
        feats += ["Desain ergonomis dan nyaman digunakan", "Build quality premium", "Performa handal harian"]
    return "\n".join([f"- {f}" for f in feats[:8]])


def git_commit_and_push(title, filename, image_slug, base_slug, counter=1):
    """Shared git workflow. Returns article_url or None on failure."""
    env_path = REPO_PATH / ".env"
    gh_token = None
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                if line.startswith("GH_TOKEN="):
                    gh_token = line.strip().split("=", 1)[1]
                    break
    os.chdir(REPO_PATH)
    banner_path = REPO_PATH / "assets" / "images" / "posts" / f"{image_slug}-banner.jpg"
    now = datetime.now()
    jekyll_slug = base_slug.replace('---', '-').replace('--', '-')
    if counter > 1:
        jekyll_slug = f"{jekyll_slug}-{counter - 1}"
    article_url = f"https://ulasanteknoid.my.id/{now.year}/{now.month:02d}/{now.day:02d}/{jekyll_slug}.html"

    if DRY_RUN:
        print(f"🧪 DRY RUN: generated {filename.name}; skip git add/commit/push")
        try:
            filename.unlink()
        except FileNotFoundError:
            pass
        return article_url

    subprocess.run(["git", "add", str(filename)], check=True)
    if STATE_FILE.exists():
        subprocess.run(["git", "add", str(STATE_FILE)], check=True)
    if banner_path.exists() and banner_path.stat().st_size > 0:
        subprocess.run(["git", "add", str(banner_path)], check=True)
    subprocess.run(["git", "commit", "-m", f"🤖 Auto: {title[:60]}"], check=True)

    if NO_PUSH:
        print("🧪 NO_PUSH enabled: commit created, push skipped")
        return article_url

    if gh_token:
        push_url = f"https://{gh_token}@github.com/ulasantekno/ulasantekno.github.io.git"
        subprocess.run(["git", "push", push_url, "main"], check=True)
        subprocess.run(["git", "remote", "set-url", "origin",
                        "https://github.com/ulasantekno/ulasantekno.github.io.git"], check=False)
    else:
        subprocess.run(["git", "push", "origin", "main"], check=True)
    return article_url


def generate_banner(image_slug, title, category, subcategory):
    banner_generated = False
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        banner_script = os.path.join(script_dir, "unsplash_banner.py")
        if os.path.exists(banner_script):
            result = subprocess.run(
                ["/usr/bin/python3.12", banner_script, image_slug, title, category, subcategory],
                capture_output=True, text=True, timeout=30
            )
            if result.stderr: print(result.stderr)
            if result.returncode == 0:
                print(f"✅ Banner: {image_slug}-banner.jpg")
                banner_generated = True
    except Exception as e:
        print(f"⚠️ Banner error: {e}")
    if not banner_generated:
        fb = REPO_PATH / "assets" / "hero-banner.jpg"
        tb = REPO_PATH / "assets" / "images" / "posts" / f"{image_slug}-banner.jpg"
        if fb.exists() and not tb.exists():
            import shutil; shutil.copy(str(fb), str(tb))
            print("🖼️ Fallback banner used")
    return banner_generated


def check_duplicate(date_str, base_slug):
    """Check if post already exists today."""
    slug = f"{date_str}-{base_slug}"
    counter = 1
    while (POSTS_DIR / f"{slug}.md").exists():
        slug = f"{date_str}-{base_slug}-{counter}"
        counter += 1
    return POSTS_DIR / f"{slug}.md", counter


# ─── MODE: SINGLE REVIEW ─────────────────────────────────────────────

SINGLE_TEMPLATE = """---
date: {date}
title: {title}
description: {description}
image: "/assets/images/posts/{image_slug}-banner.jpg"
category: {category}
---

{intro}

---

## 📋 Spesifikasi & Fitur Utama

{specs}
- **Harga:** {price}

---

## ✅ Kelebihan

{pros}

---

## ❌ Kekurangan

{cons}

---

## 🎯 Cocok Untuk Siapa?

{target}

---

## 💡 Alternatif di Kelas yang Sama

{alternatives}

---

## 🏁 Kesimpulan

{conclusion}

🛒 [**Beli Sekarang di Shopee →**]({link})

---

{tips}

---

{closing}
"""


def generate_single(products):
    product = select_fresh_single(products)
    subcat = product.get("subcategory", "Produk")
    cat = product.get("category", "Gadget")
    name = clean_product_name(product['name'])
    price = format_price(product['price'])
    year = 2026

    titles = [
        f"Review {name}: Worth It di Tahun {year}?",
        f"Mengulas {name} — Detail, Harga & Rekomendasi",
        f"{name} Review Lengkap: Kelebihan, Kekurangan & Alternatif",
        f"Apakah {name} Worth It? Review Jujur {year}",
        f"{name}: Review Mendalam untuk Pembeli Cerdas",
    ]
    title = random.choice(titles)

    date_str = datetime.now().strftime("%Y-%m-%d")
    base_slug = generate_slug(title)
    filename, counter = check_duplicate(date_str, base_slug)

    image_slug = generate_slug(title)
    description = f"Review lengkap {name} {year}: kelebihan, kekurangan, spesifikasi, dan harga terbaru {price}. Cek sebelum beli!"

    # Pros
    pros_list = []
    nu = product['name'].upper()
    if product['price'] < 300000: pros_list += ["Harga sangat terjangkau", "Value for money tinggi"]
    elif product['price'] < 1000000: pros_list += ["Harga kompetitif dengan fitur sebanding produk mahal"]
    else: pros_list += ["Build quality dan performa premium", "Fitur flagship kelas atas"]
    if any(x in nu for x in ['ANC','NOISE CANCELLING']): pros_list.append("Peredam bising aktif efektif")
    if 'WIRELESS' in nu or 'BLUETOOTH' in nu: pros_list.append("Bebas kabel — praktis untuk mobilitas tinggi")
    if any(x in nu for x in ['FAST CHARGING','QUICK CHARGE','PD']): pros_list.append("Pengisian cepat — hemat waktu")
    if 'mAh' in nu: pros_list.append("Baterai besar — tahan seharian")
    if '5G' in nu: pros_list.append("Support 5G — future-proof")
    if 'RGB' in nu: pros_list.append("Desain aesthetic RGB customizable")
    if 'GAMING' in nu: pros_list.append("Dioptimasi untuk gaming")
    if any(x in nu for x in ['WATERPROOF','IP67','IP68']): pros_list.append("Tahan air dan debu")
    if any(x in nu for x in ['MAGNETIC','MAGSAFE']): pros_list.append("Attachment magnetic praktis")
    if any(x in nu for x in ['INTEGRATED','BUILT-IN']): pros_list.append("Kabel built-in — nggak perlu bawa tambahan")
    while len(pros_list) < 4: pros_list.append("Kompatibel dengan berbagai perangkat populer")
    pros = "\n".join([f"- {p}" for p in pros_list[:6]])

    # Cons
    cons_list = []
    if product['price'] < 300000: cons_list += ["Material build lebih ringan", "Beberapa fitur advanced absen"]
    elif product['price'] < 1000000: cons_list += ["Performa masih di bawah flagship", "Fitur flagship tertentu absen"]
    else: cons_list += ["Harga cukup tinggi", "Mungkin overkill untuk kebutuhan dasar"]
    if 'WIRELESS' in nu or 'BLUETOOTH' in nu or 'TWS' in nu: cons_list.append("Baterai perlu di-charge berkala")
    if any(x in nu for x in ['ANC','NOISE CANCELLING']): cons_list.append("ANC mengurangi awareness lingkungan")
    if '5G' in nu: cons_list.append("Baterai 5G cenderung lebih boros")
    if 'RGB' in nu: cons_list.append("RGB bisa mengganggu di ruang gelap")
    while len(cons_list) < 3: cons_list.append("Stok warna/varian terbatas di beberapa seller")
    cons = "\n".join([f"- {c}" for c in cons_list[:5]])

    # Target audience
    if product['price'] < 300000: bt = "budget-conscious user atau pemula"
    elif product['price'] < 1000000: bt = "pengguna harian yang butuh keseimbangan fitur dan harga"
    else: bt = "enthusiast atau power user yang siap investasi premium"
    aud_map = {
        "Smartphone": "pengguna aktif sosial media, content creator, atau gamer mobile",
        "TWS": "commuter, remote worker yang sering meeting, atau pecinta musik",
        "Earphone": "pengguna yang cari audio berkualitas tanpa perlu charging",
        "Powerbank": "traveler, content creator outdoor, atau yang sering jauh dari stop kontak",
        "Charger": "pengguna multi-device yang butuh pengisian cepat",
        "Smartwatch": "fitness enthusiast atau profesional sibuk yang butuh tracking kesehatan",
        "Microphone": "streamer, podcaster, gamer, atau content creator",
        "Soundbar": "keluarga yang pengen upgrade pengalaman nonton di rumah",
        "Tablet": "pelajar, profesional mobile, atau pengguna yang butuh layar besar",
        "Keyboard": "programmer, writer, atau gamer",
        "Mouse": "desainer, gamer FPS, atau profesional yang butuh presisi",
    }
    aud = aud_map.get(subcat, "pengguna umum yang butuh solusi praktis")
    target = f"Produk ini cocok untuk **{aud}** yang juga termasuk **{bt}**. Kalau kamu masuk di profil tersebut, produk ini sangat worth dipertimbangkan."

    # Alternatives
    same = [p for p in products if p.get("subcategory") == subcat and p["id"] != product["id"]]
    alts = "Belum ada data alternatif yang cukup. Nantikan update dari UlasTekno!"
    if len(same) >= 2:
        cheaper = [p for p in same if p["price"] < product["price"]]
        pricier = [p for p in same if p["price"] > product["price"]]
        lines = ["Kalau produk ini belum cocok, berikut alternatif di kategori yang sama:", ""]
        if cheaper:
            c = random.choice(cheaper)
            lines.append(f"- **Budget:** [{clean_product_name(c['name'])}]({c['link']}) — {format_price(c['price'])}")
        if pricier:
            p = random.choice(pricier)
            lines.append(f"- **Premium:** [{clean_product_name(p['name'])}]({p['link']}) — {format_price(p['price'])}")
        alts = "\n".join(lines) if len(lines) > 2 else alts

    # Conclusion
    if product['price'] < 300000: val = "pilihan entry-level dengan value tinggi"
    elif product['price'] < 1000000: val = "sweet spot antara fitur dan harga"
    else: val = "investasi berkualitas untuk pengalaman premium"
    conclusion = f"Secara keseluruhan, **{name}** adalah {val}. Dengan fitur yang ditawarkan, produk ini layak masuk daftar pertimbangan kamu.\n\nJangan lupa cek review pembeli asli di Shopee sebelum checkout ya!"

    # Tips
    tips_map = {
        "Smartphone": ["Cek update software minimal 2-3 tahun ke depan", "Bandingkan harga antar seller", "Pastikan garansi resmi Indonesia"],
        "TWS": ["Cek codec audio support (aptX/LDAC)", "Pastikan touch control bisa dikustomisasi", "Baca review soal latency kalau gamer"],
        "Powerbank": ["Hitung kebutuhan — 10000mAh untuk daily, 20000mAh+ untuk travel", "Pastikan support fast charging HP kamu", "Cek berat — 20000mAh bisa terasa berat"],
        "Charger": ["Cek power output — 20W+ untuk iPhone, 33W+ untuk Android", "GaN charger lebih ringan dan tidak panas", "Multi-port lebih praktis untuk banyak device"],
        "Smartwatch": ["Pastikan kompatibel dengan HP kamu", "Cek sensor kesehatan yang tersedia", "Baterai life — minimal 1-2 hari"],
        "Microphone": ["Cek polar pattern — cardioid untuk solo", "Mic condenser lebih detail tapi sensitif bising", "Cek butuh phantom power atau USB plug & play"],
        "Smart TV": ["Ukur jarak duduk ke TV — 43\" untuk 2-3m, 55\"+ untuk 3-4m", "Cek resolusi — minimal 4K untuk 50\" ke atas", "Pastikan ada app streaming yang kamu butuhkan"],
    }
    tip_items = tips_map.get(subcat, ["Baca ulasan real user di Shopee", "Bandingkan harga antar seller", "Pastikan garansi resmi"])
    tips = f"## 💡 Tips Sebelum Membeli {subcat}\n\n" + "\n".join([f"- {t}" for t in tip_items])
    tips += "\n\n**💡 Tips tambahan:** Selalu cek voucher Shopee dan gratis ongkir sebelum checkout!"

    # Intro & closing
    intro_hooks = {
        "Smartphone": f"Lagi cari smartphone baru yang worth it di tahun {year}? **{name}** hadir dengan harga **{price}** dan sejumlah fitur menarik. Tapi apakah produk ini benar-benar cocok untuk kebutuhan harianmu? Yuk, kita ulas detailnya!",
        "TWS": f"TWS makin jadi pilihan utama untuk audio nirkabel. **{name}** dengan harga **{price}** masuk radar banyak pengguna. Tapi seberapa worth it? Simak review lengkapnya!",
        "Powerbank": f"HP mati di tengah jalan masih jadi mimpi buruk. **{name}** datang sebagai solusi dengan harga **{price}**. Tapi apakah kapasitasnya cukup?",
        "Smartwatch": f"Pengen hidup lebih sehat atau butuh asisten di pergelangan tangan? **{name}** hadir dengan harga **{price}**. Kita ulas apakah smartwatch ini sesuai ekspektasi.",
        "Microphone": f"Mau mulai streaming, podcast, atau suara jernih di meeting? **{name}** dengan harga **{price}** jadi salah satu pilihan populer. Ini review lengkapnya!",
    }
    intro = intro_hooks.get(subcat, f"**{name}** hadir di pasaran dengan harga **{price}** dan menawarkan sejumlah fitur menarik. Tapi apakah produk ini benar-benar worth it? Yuk, kita ulas detail lengkap kelebihan dan kekurangannya!")
    emojis = {"Smartphone":"📱✨","TWS":"🎧🔥","Earphone":"🎧✨","Laptop":"💻🚀","Smartwatch":"⌚💪","Charger":"⚡🔋","Powerbank":"🔋🎯","Smart TV":"📺🍿","Tablet":"📱💻","Microphone":"🎙️✨","Soundbar":"🔊🍿","Keyboard":"⌨️✨","Mouse":"🖱️🎯"}
    closing = f"Itu dia review lengkapnya! Semoga membantu kamu memutuskan produk yang tepat. Kalau ada pertanyaan, tinggalkan komentar ya. {emojis.get(subcat, '🛍️✨')}"

    content = SINGLE_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S +0700"),
        title=yaml_quote(sanitize_title_for_yaml(title)), description=yaml_quote(description), image_slug=image_slug,
        category=cat, intro=intro, specs=generate_specs_bullets(product['name']),
        price=price, pros=pros, cons=cons, target=target,
        alternatives=alts, conclusion=conclusion, link=product["link"],
        tips=tips, closing=closing
    )

    filename.write_text(content, encoding="utf-8")
    if filename.stat().st_size == 0:
        filename.unlink()
        return {"success": False, "reason": "empty_file"}

    if not DRY_RUN:
        mark_single_used(product)
        generate_banner(image_slug, title, cat, subcat)
    else:
        print("🧪 DRY RUN: skip banner generation")
    url = git_commit_and_push(title, filename, image_slug, base_slug, counter)
    if not url:
        return {"success": False, "reason": "git_error"}

    return {
        "success": True, "mode": "single", "title": title, "url": url,
        "subcategory": subcat, "product_name": product['name'],
        "price": price, "image_slug": image_slug
    }


# ─── MODE: TOP 5 ─────────────────────────────────────────────────────

TOP5_TEMPLATE = """---
date: {date}
title: {title}
description: {description}
image: "/assets/images/posts/{image_slug}-banner.jpg"
category: {category}
---

{intro}

---

## 1. {p1_name}

**Harga: {p1_price}**

{p1_desc}

**Spesifikasi:**
{p1_specs}

**Cocok untuk:** {p1_target}

🛒 [**Beli Sekarang di Shopee →**]({p1_link})

---

## 2. {p2_name}

**Harga: {p2_price}**

{p2_desc}

**Spesifikasi:**
{p2_specs}

**Cocok untuk:** {p2_target}

🛒 [**Beli Sekarang di Shopee →**]({p2_link})

---

## 3. {p3_name}

**Harga: {p3_price}**

{p3_desc}

**Spesifikasi:**
{p3_specs}

**Cocok untuk:** {p3_target}

🛒 [**Beli Sekarang di Shopee →**]({p3_link})

---

## 4. {p4_name}

**Harga: {p4_price}**

{p4_desc}

**Spesifikasi:**
{p4_specs}

**Cocok untuk:** {p4_target}

🛒 [**Beli Sekarang di Shopee →**]({p4_link})

---

## 5. {p5_name}

**Harga: {p5_price}**

{p5_desc}

**Spesifikasi:**
{p5_specs}

**Cocok untuk:** {p5_target}

🛒 [**Beli Sekarang di Shopee →**]({p5_link})

---

{buying_tips}

---

{closing}
"""


def _top5_product_desc(p, idx, subcat):
    name = clean_product_name(p['name'])
    price = format_price(p['price'])
    feats = []
    if any(x in p['name'].upper() for x in ['RGB']): feats.append("dengan lampu RGB aesthetic")
    if any(x in p['name'].upper() for x in ['WIRELESS','BLUETOOTH','TWS']): feats.append("tanpa kabel — gerak lebih leluasa")
    if any(x in p['name'].upper() for x in ['FAST CHARGING','PD','QUICK CHARGE']): feats.append("dengan teknologi fast charging")
    if any(x in p['name'].upper() for x in ['ANC','NOISE CANCELLING']): feats.append("dengan peredam bising aktif")
    if 'GAMING' in p['name'].upper(): feats.append("yang dioptimasi untuk gaming")
    if any(x in p['name'].upper() for x in ['4K','UHD','HDR']): feats.append("dengan kualitas gambar tajam")
    fs = ", ".join(feats) if feats else "dengan fitur lengkap"
    templates = [
        f"{name} {fs}. Hadir dengan harga {price}, produk ini menawarkan kualitas terbaik di kelasnya.",
        f"Dengan harga {price}, {name} {fs}. Pilihan yang sangat worth it untuk budget kamu.",
        f"{name} adalah solusi praktis {fs}. Dengan harga {price}, produk ini jadi favorit banyak pengguna.",
    ]
    return random.choice(templates)


def _top5_target(p, subcat):
    aud = {
        "Smartphone": ["Pengguna harian untuk kerja dan sosial media", "Content creator", "Gamer mobile"],
        "TWS": ["Pengguna aktif untuk olahraga dan commute", "Remote worker yang sering meeting", "Music enthusiast"],
        "Laptop": ["Mahasiswa dan profesional", "Gamer", "Content creator"],
        "Smartwatch": ["Fitness enthusiast", "Profesional sibuk", "Fashion-conscious user"],
        "Charger": ["Pengguna yang HP sering lowbat", "Traveler", "Pengguna multi-device"],
        "Powerbank": ["Pengguna mobile yang sering keluar", "Traveler", "Content creator outdoor"],
        "Smart TV": ["Keluarga yang pengen pengalaman nonton sinematik", "Gamer", "Binge-watcher"],
        "Microphone": ["Streamer dan podcaster", "Gamer", "Content creator"],
        "Tablet": ["Pelajar", "Profesional mobile", "Pengguna yang butuh layar besar"],
    }
    opts = aud.get(subcat, ["Pengguna yang cari kualitas terbaik", "Pemula", "Budget-conscious user"])
    if p['price'] < 300000: return f"Pemula dan budget hunter — butuh solusi terjangkau tanpa kompromi kualitas dasar."
    elif p['price'] < 800000: return random.choice(opts[:2])
    else: return random.choice(opts) + " yang siap investasi lebih untuk kualitas premium."


def _top5_buying_tips(subcat):
    tips = {
        "Smartphone": ("📱", "Sesuaikan dengan kebutuhan harian", ["**Casual user** → Fokus baterai besar dan layar nyaman", "**Gamer** → Cari refresh rate tinggi", "**Fotografer** → Prioritaskan kamera", "**Professional** → RAM besar dan multitasking lancar"]),
        "TWS": ("🎧", "Perhatikan fitur audio", ["**Commuter** → ANC + ambient mode", "**Workout** → IP rating tinggi", "**Meeting sering** → Mic berkualitas", "**Audiophile** → Driver besar dan codec aptX/LDAC"]),
        "Laptop": ("💻", "Pilih berdasarkan penggunaan", ["**Pelajar/kerja** → Ringan + baterai 8+ jam", "**Gaming** → GPU dedicated", "**Design/edit** → Layar color-accurate + 16GB RAM", "**Budget** → Chromebook atau SSD cepat"]),
        "Smartwatch": ("⌚", "Pertimbangkan ekosistem", ["**iPhone** → Apple Watch", "**Android** → Galaxy Watch/Wear OS", "**Fitness** → GPS akurat + heart rate", "**Fashion** → Desain dan strap ganti"]),
        "Charger": ("⚡", "Cek kompatibilitas", ["**HP saja** → Single port 20W-30W", "**Multi-device** → 2-3 port", "**Traveler** → GaN charger ringan", "**Power user** → 65W+ untuk laptop"]),
        "Powerbank": ("🔋", "Pilih kapasitas sesuai kebutuhan", ["**Daily** → 10000mAh cukup", "**Travel** → 20000mAh+", "**Fast charging** → Support PD/QC", "**Wireless** → Qi wireless charging"]),
        "Smart TV": ("📺", "Perhatikan ukuran ruangan", ["**Kamar (2-3m)** → 32-43 inch", "**Ruang tamu (3-4m)** → 50-55 inch", "**Home theater** → 65 inch+ Dolby Vision", "**Gaming** → Low input lag + HDMI 2.1"]),
        "Microphone": ("🎤", "Pilih berdasarkan polar pattern", ["**Solo streaming** → Cardioid", "**Podcast ramai** → Omnidirectional", "**Musik/recording** → Condenser", "**Gaming casual** → USB plug & play"]),
    }
    icon, title, items = tips.get(subcat, ("🛒", "Tips memilih produk", ["Cek ulasan real", "Bandingkan harga antar seller", "Pastikan garansi resmi", "Sesuaikan budget dengan kebutuhan"]))
    lines = [f"## {icon} Tips Memilih {subcat} Terbaik", "", f"**{icon} {title}:**"]
    for it in items: lines.append(it)
    lines.extend(["", "**💡 Tips tambahan:**", "- Cek rating dan review terbaru sebelum checkout", "- Manfaatkan voucher dan gratis ongkir di Shopee", "- Beli dari seller responsif untuk after-sales"])
    return "\n".join(lines)


def generate_top5(products):
    emojis = {"Smartphone":"📱✨","TWS":"🎧🔥","Earphone":"🎧✨","Laptop":"💻🚀","Smartwatch":"⌚💪","Charger":"⚡🔋","Powerbank":"🔋🎯","Smart TV":"📺🍿","Tablet":"📱💻","Microphone":"🎙️✨","Soundbar":"🔊🍿","Keyboard":"⌨️✨","Mouse":"🖱️🎯"}
    state = load_state()
    used_sets = set(state.get("used_top5_sets", []))
    by_subcat = {}
    for p in products:
        sc = p.get("subcategory", "Lainnya")
        by_subcat.setdefault(sc, []).append(p)
    valid = {k: v for k, v in by_subcat.items() if len(v) >= 5}
    if not valid:
        sc = max(by_subcat.keys(), key=lambda k: len(by_subcat[k]))
        selected = by_subcat[sc][:5]
    else:
        subcats = list(valid.keys())
        random.shuffle(subcats)
        selected = None
        sc = subcats[0]
        for candidate_sc in subcats:
            pool = valid[candidate_sc]
            for _ in range(25):
                candidate = random.sample(pool, 5)
                key = "|".join(sorted(product_key(p) for p in candidate))
                if key not in used_sets:
                    sc = candidate_sc
                    selected = candidate
                    break
            if selected:
                break
        if selected is None:
            state["used_top5_sets"] = []
            save_state(state)
            sc = random.choice(list(valid.keys()))
            selected = random.sample(valid[sc], 5)
    selected.sort(key=lambda x: x["price"], reverse=True)

    prices = [p["price"] for p in selected]
    min_p, max_p = min(prices), max(prices)
    pr = f"di bawah {format_price(max_p)}" if max_p >= 1000000 else f"mulai {format_price(min_p)}"
    year = 2026

    titles = [
        f"5 {sc} Terbaik {pr} {year}",
        f"Rekomendasi 5 {sc} Terbaik {year} ({pr})",
        f"5 {sc} Terbaik {year} — Update Harga Terbaru!",
        f"Top 5 {sc} Paling Worth It {year}",
        f"{sc} Terbaik {year}: Dari Budget Sampai Premium!",
    ]
    title = random.choice(titles)

    date_str = datetime.now().strftime("%Y-%m-%d")
    base_slug = generate_slug(title)
    filename, counter = check_duplicate(date_str, base_slug)
    image_slug = generate_slug(title)

    cat = selected[0]["category"]
    desc = f"Rekomendasi {sc} terbaik tahun {year}: {', '.join([clean_product_name(p['name']) for p in selected[:2]])} dan lainnya. Update harga dan link Shopee terbaru!"

    # Intro
    hooks = {
        "Smartphone": f"Lagi cari smartphone yang worth it di tahun {year}? Dengan banyaknya pilihan, memilih yang tepat bisa bikin bingung.",
        "TWS": f"Mau upgrade pengalaman mendengarkan musik atau podcast? TWS adalah pilihan paling praktis tanpa kabel.",
        "Laptop": f"Butuh laptop baru untuk kerja, kuliah, atau gaming? Tahun {year}, banyak laptop powerful dengan harga terjangkau.",
        "Smartwatch": f"Pengen mulai hidup sehat atau butuh notifikasi? Smartwatch bisa jadi asisten harian.",
        "Charger": f"HP sering lowbat di saat genting? Charger fast charging bisa jadi penyelamat.",
        "Powerbank": f"Sering keluar rumah dan khawatir HP mati? Powerbank portable adalah solusi paling praktis.",
        "Smart TV": f"Pengen pengalaman nonton yang lebih seru di rumah? Smart TV bisa mengubah ruang tamu jadi mini bioskop.",
        "Tablet": f"Butuh perangkat yang lebih besar dari HP tapi lebih praktis dari laptop? Tablet adalah pilihan tepat.",
        "Microphone": f"Mau mulai streaming, podcast, atau suara jernih di meeting? Mic USB kondensor adalah solusi paling praktis.",
    }
    hook = hooks.get(sc, f"Tahun {year}, {sc} menjadi salah satu produk paling dicari. Dengan banyaknya pilihan, menemukan yang paling worth it butuh referensi tepat.")
    intro = hook + f"\n\nBerikut **5 rekomendasi {sc} terbaik {pr}** yang bisa kamu dapatkan di Shopee!\n\nLangsung aja simak daftar {sc} terbaik berikut ini!"

    # Build template vars
    tvars = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0700"),
        "title": yaml_quote(sanitize_title_for_yaml(title)), "description": yaml_quote(desc), "image_slug": image_slug,
        "category": cat, "intro": intro,
        "buying_tips": _top5_buying_tips(sc),
        "closing": f"Semoga rekomendasi ini membantu kamu menemukan {sc} yang tepat! Jangan lupa cek review di Shopee sebelum beli ya. {emojis.get(sc, '🛍️✨')}",
    }
    for i, p in enumerate(selected, 1):
        tvars[f"p{i}_name"] = clean_product_name(p["name"])
        tvars[f"p{i}_price"] = format_price(p["price"])
        tvars[f"p{i}_link"] = p["link"]
        tvars[f"p{i}_desc"] = _top5_product_desc(p, i, sc)
        tvars[f"p{i}_specs"] = generate_specs_bullets(p["name"])
        tvars[f"p{i}_target"] = _top5_target(p, sc)

    content = TOP5_TEMPLATE.format(**tvars)
    filename.write_text(content, encoding="utf-8")
    if filename.stat().st_size == 0:
        filename.unlink()
        return {"success": False, "reason": "empty_file"}

    if not DRY_RUN:
        mark_top5_used(selected)
        generate_banner(image_slug, title, cat, sc)
    else:
        print("🧪 DRY RUN: skip banner generation")
    url = git_commit_and_push(title, filename, image_slug, base_slug, counter)
    if not url:
        return {"success": False, "reason": "git_error"}

    return {
        "success": True, "mode": "top5", "title": title, "url": url,
        "subcategory": sc, "products": selected, "price_range": pr,
        "image_slug": image_slug
    }


# ─── MODE: COMPARE 2 PRODUCTS ────────────────────────────────────────

COMPARE_TEMPLATE = """---
date: {date}
title: {title}
description: {description}
image: "/assets/images/posts/{image_slug}-banner.jpg"
category: {category}
---

{intro}

---

## 📋 Spesifikasi {name_a}

{specs_a}
- **Harga:** {price_a}

---

## 📋 Spesifikasi {name_b}

{specs_b}
- **Harga:** {price_b}

---

## ⚖️ Perbandingan Langsung

| Aspek | {name_a} | {name_b} |
|---|---|---|
| **Harga** | {price_a} | {price_b} |
| **Selisih Harga** | — | {price_diff} |
{compare_rows}

---

## ✅ Kelebihan {name_a}

{pros_a}

---

## ✅ Kelebihan {name_b}

{pros_b}

---

## ❌ Kekurangan {name_a}

{cons_a}

---

## ❌ Kekurangan {name_b}

{cons_b}

---

## 🎯 Siapa yang Cocok untuk {name_a}?

{target_a}

---

## 🎯 Siapa yang Cocok untuk {name_b}?

{target_b}

---

## 🏁 Kesimpulan

{conclusion}

🛒 [**Beli {name_a} di Shopee →**]({link_a})
🛒 [**Beli {name_b} di Shopee →**]({link_b})

---

{tips}

---

{closing}
"""


def _compare_rows(feats_a, feats_b):
    """Build comparison table rows from feature lists."""
    all_feats = list(dict.fromkeys(feats_a + feats_b))  # unique, preserve order
    rows = []
    for feat in all_feats[:6]:
        a_mark = "✅ Ada" if feat in feats_a else "❌ Tidak"
        b_mark = "✅ Ada" if feat in feats_b else "❌ Tidak"
        rows.append(f"| **{feat}** | {a_mark} | {b_mark} |")
    if not rows:
        rows = ["| **Fitur unggulan** | ✅ Tersedia | ✅ Tersedia |"]
    return "\n".join(rows)


def _compare_pros(product, is_cheaper, price_diff=None):
    """Generate pros for comparison mode."""
    name = clean_product_name(product['name'])
    price = product['price']
    nu = product['name'].upper()
    pros = []

    if is_cheaper:
        if price_diff:
            pros.append(f"Harga lebih terjangkau — hemat {price_diff}")
        else:
            pros.append("Harga lebih terjangkau — hemat signifikan")
        pros.append("Value for money lebih tinggi untuk budget terbatas")
    else:
        pros.append("Fitur lebih lengkap dan spesifikasi lebih tinggi")
        pros.append("Performa lebih optimal untuk penggunaan berat")

    if any(x in nu for x in ['ANC','NOISE CANCELLING']): pros.append("Peredam bising aktif")
    if 'WIRELESS' in nu or 'BLUETOOTH' in nu: pros.append("Bebas kabel — praktis")
    if any(x in nu for x in ['FAST CHARGING','PD','QUICK CHARGE']): pros.append("Fast charging")
    if '5G' in nu: pros.append("Support 5G")
    if 'RGB' in nu: pros.append("Desain RGB aesthetic")
    if any(x in nu for x in ['4K','UHD','HDR']): pros.append("Kualitas gambar/resolusi tinggi")
    if any(x in nu for x in ['IP67','IP68','WATERPROOF']): pros.append("Tahan air dan debu")
    if 'MAGNETIC' in nu: pros.append("Desain magnetic attachment")

    while len(pros) < 4:
        pros.append("Build quality solid dan tahan lama")
    # Remove duplicates
    seen = set()
    unique = []
    for p in pros:
        if p not in seen:
            seen.add(p)
            unique.append(p)
    return "\n".join([f"- {p}" for p in unique[:5]])


def _compare_cons(product, is_cheaper):
    """Generate cons for comparison mode."""
    nu = product['name'].upper()
    cons = []

    if is_cheaper:
        cons.append("Beberapa fitur premium mungkin absen dibanding versi mahal")
        cons.append("Performa maksimal masih di bawah kelas atas")
    else:
        cons.append("Harga lebih mahal — perlu pertimbangan budget")
        cons.append("Mungkin overkill untuk penggunaan dasar sehari-hari")

    if 'WIRELESS' in nu or 'BLUETOOTH' in nu or 'TWS' in nu:
        cons.append("Baterai perlu di-charge secara berkala")
    if any(x in nu for x in ['ANC','NOISE CANCELLING']):
        cons.append("ANC mengurangi awareness lingkungan")

    while len(cons) < 3:
        cons.append("Varian warna/ukuran terbatas di beberapa seller")
    return "\n".join([f"- {c}" for c in cons[:4]])


def generate_compare(products):
    state = load_state()
    used_pairs = set(state.get("used_compare_pairs", []))
    by_subcat = {}
    for p in products:
        sc = p.get("subcategory", "Lainnya")
        by_subcat.setdefault(sc, []).append(p)

    # Need at least 2 products in same subcat
    valid = {k: v for k, v in by_subcat.items() if len(v) >= 2}
    if not valid:
        return {"success": False, "reason": "no_compare_pair"}

    pair = None
    sc = random.choice(list(valid.keys()))
    subcats = list(valid.keys())
    random.shuffle(subcats)
    for candidate_sc in subcats:
        pool = valid[candidate_sc]
        for _ in range(35):
            candidate = random.sample(pool, 2)
            if compare_pair_key(candidate[0], candidate[1]) not in used_pairs:
                sc = candidate_sc
                pair = candidate
                break
        if pair:
            break
    if pair is None:
        state["used_compare_pairs"] = []
        save_state(state)
        sc = random.choice(list(valid.keys()))
        pair = random.sample(valid[sc], 2)
    pair.sort(key=lambda x: x["price"])
    a, b = pair

    name_a = clean_product_name(a['name'])
    name_b = clean_product_name(b['name'])
    price_a = format_price(a['price'])
    price_b = format_price(b['price'])
    diff = format_price(abs(b['price'] - a['price']))
    year = 2026
    cat = a.get("category", "Gadget")

    titles = [
        f"{name_a} vs {name_b}: Mana yang Lebih Worth It?",
        f"Perbandingan {name_a} dan {name_b} — Beda Harga {diff}, Beda Fitur?",
        f"{name_a} atau {name_b}? Review Perbandingan Detail {year}",
        f"{name_a} vs {name_b}: Pilih yang Mana untuk Budgetmu?",
        f"Head-to-Head: {name_a} vs {name_b} — Review Lengkap",
    ]
    title = random.choice(titles)

    date_str = datetime.now().strftime("%Y-%m-%d")
    base_slug = generate_slug(title)
    filename, counter = check_duplicate(date_str, base_slug)
    image_slug = generate_slug(title)

    description = f"Perbandingan lengkap {name_a} vs {name_b} {year}: beda harga {diff}, kelebihan, kekurangan, dan rekomendasi. Cek sebelum beli!"

    # Intro
    intro = (
        f"Bingung memilih antara **{name_a}** ({price_a}) dan **{name_b}** ({price_b})? "
        f"Keduanya masuk dalam kategori **{sc}**, tapi beda harga **{diff}** dan tentunya beda fitur.\n\n"
        f"Di artikel ini, kita akan bandingkan langsung spesifikasi, kelebihan, kekurangan, dan cocok untuk siapa masing-masing produk. "
        f"Yuk, simak perbandingan lengkapnya agar kamu bisa pilih yang paling sesuai kebutuhan dan budget!"
    )

    # Compare rows
    feats_a = extract_features_from_name(a['name'])
    feats_b = extract_features_from_name(b['name'])
    compare_rows = _compare_rows(feats_a, feats_b)

    # Pros/cons
    pros_a = _compare_pros(a, is_cheaper=True, price_diff=diff)
    pros_b = _compare_pros(b, is_cheaper=False, price_diff=diff)
    cons_a = _compare_cons(a, is_cheaper=True)
    cons_b = _compare_cons(b, is_cheaper=False)

    # Target
    target_a = f"**{name_a}** cocok untuk kamu yang prioritaskan **budget terjangkau** tanpa mengorbankan fitur esensial. Ideal untuk pemula, pengguna harian, atau yang baru pertama kali mencoba {sc.lower()}."
    target_b = f"**{name_b}** lebih cocok untuk **power user dan enthusiast** yang butuh performa maksimal dan fitur lengkap. Pilihan tepat kalau kamu siap investasi lebih untuk pengalaman premium jangka panjang."

    # Conclusion
    conclusion = (
        f"Jadi, **{name_a} vs {name_b}** — mana yang lebih worth it?\n\n"
        f"Kalau kamu cari **solusi terjangkau** yang sudah cukup untuk kebutuhan harian, **{name_a}** adalah pilihan solid. "
        f"Tapi kalau kamu butuh **fitur lengkap dan performa tinggi** untuk penggunaan berat, **{name_b}** sepadan dengan selisih harga **{diff}**-nya.\n\n"
        f"Intinya: pilih yang sesuai **kebutuhan dan budget** kamu. Nggak ada yang salah, yang penting cocok!"
    )

    # Tips
    tips_map = {
        "Smartphone": ["Cek update software minimal 2-3 tahun ke depan", "Bandingkan harga antar seller", "Pastikan garansi resmi Indonesia"],
        "TWS": ["Cek codec audio support (aptX/LDAC)", "Baca review soal latency kalau gamer", "Pastikan touch control bisa dikustomisasi"],
        "Powerbank": ["Hitung kebutuhan — 10000mAh untuk daily, 20000mAh+ untuk travel", "Pastikan support fast charging HP kamu", "Cek berat — 20000mAh bisa terasa berat"],
        "Charger": ["Cek power output — 20W+ untuk iPhone, 33W+ untuk Android", "GaN charger lebih ringan dan tidak panas", "Multi-port lebih praktis untuk banyak device"],
        "Smartwatch": ["Pastikan kompatibel dengan HP kamu", "Cek sensor kesehatan yang tersedia", "Baterai life — minimal 1-2 hari"],
        "Smart TV": ["Ukur jarak duduk ke TV — 43\" untuk 2-3m, 55\"+ untuk 3-4m", "Cek resolusi — minimal 4K untuk 50\" ke atas", "Pastikan ada app streaming yang kamu butuhkan"],
    }
    tip_items = tips_map.get(sc, ["Baca ulasan real user di Shopee", "Bandingkan harga antar seller", "Pastikan garansi resmi"])
    tips = f"## 💡 Tips Membandingkan {sc}\n\n" + "\n".join([f"- {t}" for t in tip_items])
    tips += "\n\n**💡 Tips tambahan:** Bandingkan harga di beberapa seller Shopee — kadang beda ratusan ribu untuk produk yang sama!"

    emojis = {"Smartphone":"📱✨","TWS":"🎧🔥","Earphone":"🎧✨","Laptop":"💻🚀","Smartwatch":"⌚💪","Charger":"⚡🔋","Powerbank":"🔋🎯","Smart TV":"📺🍿","Tablet":"📱💻","Microphone":"🎙️✨","Soundbar":"🔊🍿","Keyboard":"⌨️✨","Mouse":"🖱️🎯"}
    closing = f"Itu dia perbandingan lengkap antara {name_a} dan {name_b}! Semoga membantu kamu memilih yang tepat. Ada pertanyaan? Tinggalkan komentar ya. {emojis.get(sc, '🛍️✨')}"

    content = COMPARE_TEMPLATE.format(
        date=datetime.now().strftime("%Y-%m-%d %H:%M:%S +0700"),
        title=yaml_quote(sanitize_title_for_yaml(title)), description=yaml_quote(description), image_slug=image_slug,
        category=cat, intro=intro,
        name_a=name_a, name_b=name_b,
        specs_a=generate_specs_bullets(a['name']),
        specs_b=generate_specs_bullets(b['name']),
        price_a=price_a, price_b=price_b, price_diff=diff,
        compare_rows=compare_rows,
        pros_a=pros_a, pros_b=pros_b, cons_a=cons_a, cons_b=cons_b,
        target_a=target_a, target_b=target_b,
        conclusion=conclusion, link_a=a['link'], link_b=b['link'],
        tips=tips, closing=closing
    )

    filename.write_text(content, encoding="utf-8")
    if filename.stat().st_size == 0:
        filename.unlink()
        return {"success": False, "reason": "empty_file"}

    if not DRY_RUN:
        mark_compare_used(a, b)
        generate_banner(image_slug, title, cat, sc)
    else:
        print("🧪 DRY RUN: skip banner generation")
    url = git_commit_and_push(title, filename, image_slug, base_slug, counter)
    if not url:
        return {"success": False, "reason": "git_error"}

    return {
        "success": True, "mode": "compare", "title": title, "url": url,
        "subcategory": sc, "product_a": name_a, "product_b": name_b,
        "price_a": price_a, "price_b": price_b,
        "image_slug": image_slug
    }


# ─── MAIN ────────────────────────────────────────────────────────────

def generate_x_caption(result):
    """Generate X/Threads caption based on mode."""
    mode = result.get("mode", "single")
    title = result["title"]
    url = result["url"]
    subcat = result.get("subcategory", "Produk")

    hashtags = "#UlasTekno #ReviewProduk #ShopeeID"
    cat_map = {
        'smartphone': ' #Smartphone #GadgetIndonesia', 'hp': ' #Smartphone #GadgetIndonesia',
        'tws': ' #Audio #TWS', 'earphone': ' #Audio #Earphone', 'headset': ' #Audio #Headset',
        'laptop': ' #Laptop #WFH', 'smartwatch': ' #Smartwatch #Wearable', 'jam tangan': ' #Smartwatch',
        'charger': ' #Charger #FastCharging', 'powerbank': ' #Powerbank',
        'microphone': ' #Microphone #Streaming', 'mic': ' #Microphone',
        'soundbar': ' #Audio #HomeTheater', 'tablet': ' #Tablet',
        'keyboard': ' #Keyboard #Gaming', 'mouse': ' #Mouse #Gaming',
    }
    hashtags += cat_map.get(subcat.lower(), ' #Gadget #Teknologi')

    if mode == "single":
        captions = [
            f"📢 REVIEW BARU: {title}\n\nReview lengkap + kelebihan & kekurangan. Cek di sini! 👇\n\n🔗 {url}\n\n{hashtags}",
            f"🧐 {title}\n\nIni review jujur + worth it atau nggak di tahun 2026.\n\n🔗 {url}\n\n{hashtags}",
        ]
    elif mode == "top5":
        captions = [
            f"🛒 {title}\n\nLagi cari {subcat} terbaik? Ini rekomendasi lengkap dengan harga & link Shopee!\n\n🔗 {url}\n\n{hashtags}",
            f"📢 BARU: {title}\n\nReview lengkap + perbandingan harga. Langsung cek! 👇\n\n🔗 {url}\n\n{hashtags}",
            f"✨ Rekomendasi {subcat} Terbaik 2026!\n\nCek detail & harga terbaru di sini 👇\n\n🔗 {url}\n\n{hashtags}",
        ]
    else:  # compare
        pa = result.get("product_a", "Produk A")
        pb = result.get("product_b", "Produk B")
        captions = [
            f"⚖️ PERBANDINGAN BARU: {pa} vs {pb}\n\nMana yang lebih worth it? Cek review lengkapnya! 👇\n\n🔗 {url}\n\n{hashtags}",
            f"🥊 {title}\n\nBeda harga, beda fitur — kita bedah detailnya!\n\n🔗 {url}\n\n{hashtags}",
        ]
    return random.choice(captions)


def main():
    print(f"🚀 Auto-generate started at {datetime.now()}")
    if DRY_RUN:
        print("🧪 DRY RUN mode active: no commit, no push, no Telegram notification")
    products = load_products()
    if len(products) < 2:
        print("Not enough products")
        return {"success": False, "reason": "no_products"}

    # Randomly pick mode (weighted: single 45%, top5 30%, compare 25%).
    # Single review gets a little more weight because it targets long-tail product SEO best.
    if FORCED_MODE:
        if FORCED_MODE not in {"single", "top5", "compare"}:
            return {"success": False, "reason": f"invalid_mode:{FORCED_MODE}"}
        mode = FORCED_MODE
    else:
        mode = random.choices(["single", "top5", "compare"], weights=[45, 30, 25])[0]
    print(f"🎲 Selected mode: {mode.upper()}")

    if mode == "single":
        result = generate_single(products)
    elif mode == "top5":
        result = generate_top5(products)
    else:
        result = generate_compare(products)
        # Fallback to single if compare failed (e.g., no pair)
        if not result.get("success") and result.get("reason") == "no_compare_pair":
            print("⚠️ No pair for compare, falling back to single")
            result = generate_single(products)

    if result and result.get("success"):
        x_cap = generate_x_caption(result)
        result['x_caption'] = x_cap

        # Save result JSON
        if not DRY_RUN:
            result_file = REPO_PATH / ".last_generate_result.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                clean = {k: v for k, v in result.items() if k not in ('products', 'product')}
                json.dump(clean, f, indent=2, ensure_ascii=False)

        # Telegram
        if not DRY_RUN:
            mode_labels = {"single": "📖 Review Produk", "top5": "📋 Top 5 Rekomendasi", "compare": "⚖️ Perbandingan"}
            label = mode_labels.get(result.get("mode", "single"), "🤖 Artikel Baru")
            tg = (
                f"✅ <b>{label} Terbit!</b>\n\n"
                f"📌 <b>{result['title']}</b>\n\n"
                f"🔗 {result['url']}\n\n"
                f"<b>📝 Caption X/Threads:</b>\n"
                f"<pre>{x_cap}</pre>\n\n"
                f"GitHub sudah di-push, tunggu 1-2 menit untuk build Jekyll."
            )
            send_telegram_notification(tg)

        print("\n" + "="*50)
        print("📝 CAPTION X/THREADS:")
        print("="*50)
        print(x_cap)
        print("="*50)

    elif result and result.get("reason") == "exists":
        print("⏭️ Artikel hari ini sudah ada, skip.")
        with open(REPO_PATH / ".last_generate_result.json", 'w') as f:
            json.dump({"success": False, "reason": "exists", "date": datetime.now().strftime("%Y-%m-%d")}, f)
    else:
        err = result.get('error', 'Unknown') if result else 'No result'
        send_telegram_notification(f"❌ <b>Auto-blog gagal</b>\n\nError: {err}\n\nCek log di server ya.")

    return result


if __name__ == "__main__":
    result = main()
    exit(0 if (result and result.get("success")) else 1)
