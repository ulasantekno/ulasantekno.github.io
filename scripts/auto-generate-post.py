#!/usr/bin/env python3
"""Auto-generate blog posts from affiliate data.
Runs every 5 hours via cron.
"""

import json
import random
import os
import subprocess
import urllib.request
import urllib.parse
from datetime import datetime, timedelta
from pathlib import Path

# Configuration
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

# Templates for different product counts
TEMPLATES_5 = """---
date: {date}
title: "{title}"
description: "{description}"
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

Semoga rekomendasi ini membantu kamu menemukan {topic} yang tepat! Jangan lupa cek review di Shopee sebelum beli ya. {closing_emoji}
"""

def load_products():
    """Load all products from affiliate data files."""
    products = []
    for category_file in DATA_DIR.glob("*.json"):
        if category_file.name == "affiliate-links.json":
            continue
        try:
            with open(category_file) as f:
                data = json.load(f)
                for p in data.get("products", []):
                    p["category"] = CATEGORIES.get(category_file.stem, "Gadget")
                    products.append(p)
        except Exception as e:
            print(f"Error loading {category_file}: {e}")
    return products

def send_telegram_notification(message):
    """Send notification to Telegram if bot token is configured."""
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID', '1785346764')
    
    if not token:
        # Try loading from .env file
        env_file = REPO_PATH / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    if line.startswith('TELEGRAM_BOT_TOKEN='):
                        token = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
                    elif line.startswith('TELEGRAM_CHAT_ID='):
                        chat_id = line.strip().split('=', 1)[1].strip().strip('"').strip("'")
    
    if not token:
        print("ℹ️ No Telegram bot token configured, skipping notification")
        return False
    
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    
    try:
        data = urllib.parse.urlencode(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, method='POST')
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                print("✅ Telegram notification sent")
                return True
    except Exception as e:
        print(f"⚠️ Failed to send Telegram notification: {e}")
    return False

def generate_x_caption(title, url, subcategory, products, price_range):
    """Generate catchy caption for X/Twitter and Threads."""
    hashtags = "#UlasTekno #Rekomendasi #ShopeeID #Review"
    
    if subcategory.lower() in ['smartphone', 'hp']:
        hashtags += " #Smartphone #GadgetIndonesia"
    elif subcategory.lower() in ['tws', 'earphone', 'headset']:
        hashtags += " #Audio #TWS #Earphone"
    elif subcategory.lower() in ['laptop']:
        hashtags += " #Laptop #WFH #Kuliah"
    elif subcategory.lower() in ['smartwatch', 'jam tangan']:
        hashtags += " #Smartwatch #Wearable"
    elif subcategory.lower() in ['charger', 'powerbank']:
        hashtags += " #Charger #Powerbank #FastCharging"
    else:
        hashtags += " #Gadget #Teknologi"
    
    captions = [
        f"🛒 {title}\n\nLagi cari {subcategory} terbaik? Ini rekomendasi lengkap dengan harga & link Shopee!\n\n🔗 {url}\n\n{hashtags}",
        f"📢 BARU: {title}\n\nReview lengkap + perbandingan harga. Langsung cek link di bawah! 👇\n\n🔗 {url}\n\n{hashtags}",
        f"✨ Rekomendasi {subcategory} Terbaik 2026!\n\n{title}\n\nCek detail & harga terbaru di sini 👇\n\n🔗 {url}\n\n{hashtags}",
    ]
    
    return random.choice(captions)

def get_existing_slugs():
    """Get list of existing post slugs to avoid duplicates."""
    slugs = set()
    for post in POSTS_DIR.glob("*.md"):
        content = post.read_text()
        # Extract category mentions to track what's been covered
        for line in content.split("\n"):
            if line.startswith("category:"):
                slugs.add(line.strip())
    return slugs

def format_price(price):
    """Format price in Indonesian Rupiah."""
    return f"Rp {price:,.0f}".replace(",", ".")

def generate_slug(name):
    """Generate URL-friendly slug from product name."""
    import re
    slug = name.lower()
    slug = re.sub(r'[!?—–\"\'()]+', '', slug)
    slug = slug.replace(" ", "-").replace("/", "-").replace("'", "").replace('"', "")
    slug = re.sub(r'-+', '-', slug)
    return slug.strip('-')[:50]

def clean_product_name(name):
    """Clean product name to just Brand + Model/Type, removing embellishments."""
    # List of separators that usually indicate the start of extra specs
    separators = [' - ', ' | ', ' [', ' (', ' / ']
    cleaned = name
    for sep in separators:
        if sep in cleaned:
            cleaned = cleaned.split(sep)[0]
    return cleaned.strip()

def generate_description(products, topic):
    """Generate SEO description."""
    names = ", ".join([p["name"].split()[0] for p in products[:3]])
    return f"Rekomendasi {topic} terbaik tahun 2026: {names} dengan harga terjangkau. Update harga dan link Shopee terbaru!"

def generate_intro(topic, count, price_range):
    """Generate introduction paragraph with hook."""
    hooks = {
        "Smartphone": "Lagi cari smartphone yang worth it di tahun 2026? Dengan banyaknya pilihan di pasaran, memilih yang tepat bisa bikin bingung.",
        "TWS": "Mau upgrade pengalaman mendengarkan musik atau podcast? TWS (True Wireless Stereo) adalah pilihan paling praktis tanpa kabel yang berantakan.",
        "Laptop": "Butuh laptop baru untuk kerja, kuliah, atau gaming? Tahun 2026, banyak laptop powerful dengan harga makin terjangkau.",
        "Smartwatch": "Pengen mulai hidup sehat atau butuh notifikasi di pergelangan tangan? Smartwatch bisa jadi asisten harian yang nggak boleh dilewatkan.",
        "Charger": "HP sering lowbat di saat genting? Charger fast charging bisa jadi penyelamat harimu dengan pengisian cepat dalam hitungan menit.",
        "Powerbank": "Sering keluar rumah dan khawatir HP mati? Powerbank portable adalah solusi paling praktis untuk tetap terhubung seharian.",
        "Smart TV": "Pengen pengalaman nonton yang lebih seru di rumah? Smart TV dengan resolusi tinggi bisa mengubah ruang tamu jadi mini bioskop.",
        "Tablet": "Butuh perangkat yang lebih besar dari HP tapi lebih praktis dari laptop? Tablet adalah pilihan tepat untuk kerja dan hiburan.",
        "Mic": "Mau mulai streaming, podcast, atau sekadar suara jernih di meeting? Mic USB kondensor adalah solusi paling praktis — tinggal colok langsung pakai.",
        "Keyboard": "Ngetik lama bikin pegal? Mechanical keyboard dengan switch yang nyaman bisa meningkatkan produktivitas dan pengalaman gaming.",
        "Mouse": "Butuh mouse yang presisi dan nyaman untuk kerja atau gaming? Pilihan mouse wireless modern sudah sangat responsif tanpa delay.",
        "default": f"Tahun 2026, {topic} menjadi salah satu produk paling dicari. Dengan banyaknya pilihan brand dan fitur, menemukan yang paling worth it butuh referensi tepat.",
    }
    hook = hooks.get(topic, hooks["default"])
    
    cta = f"Berikut **{count} rekomendasi {topic} terbaik {price_range}** yang bisa kamu dapatkan di Shopee dengan harga terjangkau!"
    
    return hook + "\n\n" + cta + f"\n\nLangsung aja simak daftar {topic} terbaik berikut ini!"

def generate_product_desc(product, index, topic):
    """Generate natural product description."""
    name = clean_product_name(product['name'])
    price = format_price(product['price'])
    
    # Extract features from name for more specific descriptions
    features = []
    if any(x in name for x in ['RGB', 'LED']):
        features.append("dengan lampu RGB yang bikin setup makin aesthetic")
    if any(x in name for x in ['Wireless', 'Bluetooth', 'TWS']):
        features.append("tanpa kabel yang bikin gerak lebih leluasa")
    if any(x in name for x in ['Fast Charging', 'PD', 'Quick Charge']):
        features.append("dengan teknologi fast charging yang hemat waktu")
    if any(x in name for x in ['Noise Cancelling', 'ANC', 'DSP']):
        features.append("dengan teknologi peredam bising aktif")
    if any(x in name for x in ['Gaming', 'Esports']):
        features.append("yang dioptimasi khusus untuk performa gaming")
    if any(x in name for x in ['4K', 'UHD', 'HDR']):
        features.append("dengan kualitas gambar tajam dan warna hidup")
    
    feature_str = ", ".join(features) if features else "dengan fitur lengkap"
    
    templates = [
        f"{name} {feature_str}. Hadir dengan harga {price}, produk ini menawarkan kualitas terbaik di kelasnya.",
        f"Dengan harga {price}, {name} {feature_str}. Pilihan yang sangat worth it untuk budget kamu tanpa mengorbankan kualitas.",
        f"{name} adalah solusi praktis {feature_str}. Dengan harga {price}, produk ini jadi favorit banyak pengguna berkat performa dan daya tahannya.",
        f"{feature_str.capitalize()}, {name} hadir dengan harga {price}. Produk ini cocok buat kamu yang cari kualitas terbaik tanpa keluar budget terlalu besar.",
    ]
    return random.choice(templates)

def generate_specs(product):
    """Generate detailed specs list from product name."""
    name = product['name']
    specs = []
    
    # Extract specs from product name keywords
    spec_patterns = {
        'Tipe': [
            (['Kondensor', 'Condenser'], 'Kondensor'),
            (['Dynamic', 'Dinamik'], 'Dynamic'),
            (['Omnidirectional'], 'Omnidirectional'),
            (['Cardioid'], 'Cardioid'),
            (['USB', 'Type-C'], 'USB'),
            (['Wireless', 'Bluetooth'], 'Wireless'),
            (['Mechanical'], 'Mechanical'),
            (['Optical'], 'Optical'),
            (['Gaming'], 'Gaming'),
        ],
        'Koneksi': [
            (['USB-C', 'Type-C'], 'USB Type-C'),
            (['USB', 'USB A'], 'USB'),
            (['Bluetooth', 'BT'], 'Bluetooth'),
            (['Wireless', '2.4G'], 'Wireless 2.4GHz'),
            (['XLR'], 'XLR + USB'),
        ],
        'Fitur': [
            (['RGB', 'LED'], 'RGB Lighting'),
            (['Noise Cancelling', 'ANC', 'DSP'], 'AI Noise Cancelling'),
            (['Fast Charging', 'PD', 'Quick Charge'], 'Fast Charging'),
            (['Wireless Charging', 'Qi'], 'Wireless Charging'),
            (['Touch Screen', 'Touchscreen'], 'Layar Sentuh'),
            (['Fingerprint', 'Face ID'], 'Sensor Biometrik'),
            (['Waterproof', 'IP67', 'IP68'], 'Tahan Air & Debu'),
            (['Magnetic', 'MagSafe'], 'Magnetic Attachment'),
        ],
        'Baterai': [
            (['mAh'], 'Kapasitas baterai besar'),
            (['Hours', 'Jam', 'Hari', 'Days'], 'Baterai tahan lama'),
        ],
        'Kompatibel': [
            (['PC', 'Laptop', 'Mac'], 'Windows, Mac, Linux'),
            (['iOS', 'iPhone', 'iPad'], 'iOS & iPadOS'),
            (['Android'], 'Android'),
            (['PS5', 'PlayStation', 'Xbox', 'Switch'], 'PC, Console, Mobile'),
        ],
    }
    
    # Check patterns
    found_cats = set()
    for category, patterns in spec_patterns.items():
        for keywords, label in patterns:
            if any(kw.lower() in name.lower() for kw in keywords):
                if category not in found_cats:
                    specs.append(f"- {category}: {label}")
                    found_cats.add(category)
                break
    
    # Fallback generic specs
    if len(specs) < 3:
        fallback = [
            "- Desain ergonomis dan nyaman dipakai seharian",
            "- Build quality premium dengan material berkualitas",
            "- Performa handal untuk penggunaan sehari-hari",
            "- Garansi resmi untuk ketenangan pikiran",
        ]
        for f in fallback:
            if len(specs) < 4:
                specs.append(f)
    
    return "\n".join(specs[:5])

def generate_target_audience(product, topic):
    """Generate 'Cocok untuk:' target audience."""
    name = product['name']
    price = product['price']
    
    audiences = {
        "Smartphone": [
            "Pengguna harian yang butuh HP andal untuk kerja dan sosial media",
            "Content creator yang butuh kamera dan performa tinggi",
            "Gamer mobile yang cari HP dengan refresh rate tinggi",
        ],
        "TWS": [
            "Pengguna aktif yang butuh audio nirkabel untuk olahraga dan commute",
            "Remote worker yang sering meeting online dan butuh mic jernih",
            "Music enthusiast yang cari kualitas suara premium tanpa kabel",
        ],
        "Laptop": [
            "Mahasiswa dan profesional yang butuh laptop ringan untuk mobilitas tinggi",
            "Gamer yang cari performa tinggi dengan harga terjangkau",
            "Content creator yang butuh layar akurat dan prosesor cepat",
        ],
        "Smartwatch": [
            "Pengguna aktif yang ingin tracking fitness dan kesehatan harian",
            "Profesional sibuk yang butuh notifikasi tanpa harus buka HP terus",
            "Fashion-conscious user yang cari wearable yang stylish",
        ],
        "Charger": [
            "Pengguna yang HP-nya sering lowbat dan butuh pengisian cepat",
            "Traveler yang butuh charger portable dan multi-port",
            "Pengguna multi-device yang punya HP, tablet, dan TWS",
        ],
        "Powerbank": [
            "Pengguna mobile yang sering keluar rumah seharian",
            "Traveler dan commuter yang butuh daya cadangan",
            "Content creator yang sering shooting outdoor tanpa stop kontak",
        ],
        "Smart TV": [
            "Keluarga yang pengen pengalaman nonton sinematik di rumah",
            "Gamer yang butuh layar besar dengan input lag rendah",
            "Binge-watcher yang suka marathon serial Netflix seharian",
        ],
        "Mic": [
            "Streamer dan podcaster pemula yang butuh mic plug & play",
            "Gamer yang butuh komunikasi jernih saat multiplayer",
            "Content creator yang mulai serius dengan kualitas audio",
        ],
        "Keyboard": [
            "Programmer dan writer yang ngetik lama butuh kenyamanan",
            "Gamer yang cari responsivitas tinggi dan anti-ghosting",
            "Remote worker yang mau setup kerja yang ergonomis",
        ],
        "Mouse": [
            "Profesional yang butuh presisi tinggi untuk desain dan editing",
            "Gamer FPS yang butuh tracking akurat dan responsif",
            "Pengguna harian yang cari mouse nyaman untuk kerja seharian",
        ],
        "default": [
            "Pengguna yang cari kualitas terbaik di kelas harganya",
            "Pemula yang baru mulai explore produk dalam kategori ini",
            "Budget-conscious user yang nggak mau kompromi kualitas",
        ],
    }
    
    topic_audiences = audiences.get(topic, audiences["default"])
    
    # Price-based selection
    if price < 300000:
        return f"Pemula dan budget hunter yang butuh solusi terjangkau tanpa mengorbankan kualitas dasar."
    elif price < 800000:
        return random.choice(topic_audiences[:2])
    else:
        return random.choice(topic_audiences) + " yang siap investasi lebih untuk kualitas premium."

def generate_buying_tips(topic):
    """Generate buying tips section with emoji categories."""
    
    tip_categories = {
        "Smartphone": {
            "icon": "📱",
            "title": "Sesuaikan dengan kebutuhan harian",
            "items": [
                "**Casual user** → Fokus ke baterai besar dan layar nyaman",
                "**Gamer** → Cari refresh rate tinggi dan chipset gaming",
                "**Fotografer** → Prioritaskan kamera utama dan stabilisasi video",
                "**Professional** → RAM besar dan multitasking lancar",
            ]
        },
        "TWS": {
            "icon": "🎧",
            "title": "Perhatikan fitur audio dan kenyamanan",
            "items": [
                "**Active commuting** → Noise cancelling + fitur ambient mode",
                "**Workout** → IP rating tinggi dan ear hooks yang aman",
                "**Meeting sering** → Mic berkualitas dan battery life panjang",
                "**Audiophile** → Driver besar dan codec aptX/LDAC support",
            ]
        },
        "Laptop": {
            "icon": "💻",
            "title": "Pilih berdasarkan penggunaan utama",
            "items": [
                "**Pelajar/kerja** → Laptop ringan dengan baterai tahan 8+ jam",
                "**Gaming** → GPU dedicated dan cooling system bagus",
                "**Design/edit** → Layar color-accurate dan RAM minimal 16GB",
                "**Budget tight** → Chromebook atau laptop dengan SSD yang cepat",
            ]
        },
        "Smartwatch": {
            "icon": "⌚",
            "title": "Pertimbangkan ekosistem dan fitur kesehatan",
            "items": [
                "**iPhone user** → Apple Watch untuk integrasi terbaik",
                "**Android user** → Galaxy Watch atau Wear OS lainnya",
                "**Fitness enthusiast** → Cari GPS akurat dan heart rate monitor",
                "**Fashion first** → Prioritaskan desain dan strap yang bisa diganti",
            ]
        },
        "Charger": {
            "icon": "⚡",
            "title": "Cek kompatibilitas dan power output",
            "items": [
                "**HP saja** → Charger single port 20W-30W sudah cukup",
                "**Multi-device** → Cari charger dengan 2-3 port berbeda",
                "**Traveler** → GaN charger yang ringan dan tidak panas",
                "**Power user** → 65W+ untuk ngecas laptop juga",
            ]
        },
        "Powerbank": {
            "icon": "🔋",
            "title": "Pilih kapasitas dan port sesuai kebutuhan",
            "items": [
                "**Daily carry** → 10000mAh cukup untuk 2-3x charge HP",
                "**Travel/jalan-jalan** → 20000mAh+ untuk seharian outdoor",
                "**Fast charging** → Pastikan support PD atau Quick Charge",
                "**Wireless fan** → Pilih yang ada Qi wireless charging",
            ]
        },
        "Smart TV": {
            "icon": "📺",
            "title": "Perhatikan ukuran ruangan dan resolusi",
            "items": [
                "**Kamar (2-3m)** → 32-43 inch sudah cukup nyaman",
                "**Ruang tamu (3-4m)** → 50-55 inch untuk immersive experience",
                "**Home theater** → 65 inch+ dengan Dolby Vision/Atmos",
                "**Gaming** → Cari low input lag dan HDMI 2.1",
            ]
        },
        "Mic": {
            "icon": "🎤",
            "title": "Pilih berdasarkan polar pattern dan koneksi",
            "items": [
                "**Solo streaming** → Cardioid untuk fokus ke suara kamu saja",
                "**Podcast ramai** → Omnidirectional untuk tangkap semua arah",
                "**Musik/recording** → Condenser untuk detail frekuensi tinggi",
                "**Gaming casual** → USB plug & play tanpa setup ribet",
            ]
        },
        "default": {
            "icon": "🛒",
            "title": "Tips memilih produk terbaik",
            "items": [
                "**Cek ulasan real** → Baca komentar pembeli yang sudah pakai",
                "**Bandingkan harga** → Harga bisa beda antar seller di Shopee",
                "**Pastikan garansi** → Beli dari official store atau seller terpercaya",
                "**Sesuaikan budget** → Pilih fitur yang benar-benar kamu butuhkan",
            ]
        },
    }
    
    cat = tip_categories.get(topic, tip_categories["default"])
    
    lines = [
        f"## {cat['icon']} Tips Memilih {topic} Terbaik",
        "",
        f"**{cat['icon']} {cat['title']}:**",
    ]
    for item in cat["items"]:
        lines.append(item)
    
    lines.extend([
        "",
        "**💡 Tips tambahan:**",
        "- Selalu cek rating dan review terbaru sebelum checkout",
        "- Manfaatkan voucher dan gratis ongkir di Shopee",
        "- Beli dari seller dengan respons chat cepat untuk after-sales",
    ])
    
    return "\n".join(lines)

def generate_closing_emoji(topic):
    """Generate closing emoji based on topic."""
    emojis = {
        "Smartphone": "📱✨",
        "TWS": "🎧🔥",
        "Laptop": "💻🚀",
        "Smartwatch": "⌚💪",
        "Charger": "⚡🔋",
        "Powerbank": "🔋🎯",
        "Smart TV": "📺🍿",
        "Tablet": "📱💻",
        "Mic": "🎙️✨",
        "Keyboard": "⌨️✨",
        "Mouse": "🖱️🎯",
        "default": "🛍️✨",
    }
    return emojis.get(topic, emojis["default"])

def generate_image_placeholder(product):
    """Generate image placeholder - DISABLED (no images)."""
    return ""

def select_products_by_subcategory(products):
    """Select a random subcategory with at least 5 products."""
    # Group by subcategory
    by_subcat = {}
    for p in products:
        subcat = p.get("subcategory", "Lainnya")
        if subcat not in by_subcat:
            by_subcat[subcat] = []
        by_subcat[subcat].append(p)
    
    # Find subcategories with 5+ products
    valid_subcats = {k: v for k, v in by_subcat.items() if len(v) >= 5}
    
    if not valid_subcats:
        # Fallback: use any category with most products
        subcat = max(by_subcat.keys(), key=lambda k: len(by_subcat[k]))
        return subcat, by_subcat[subcat][:5]
    
    subcat = random.choice(list(valid_subcats.keys()))
    selected = random.sample(valid_subcats[subcat], 5)
    selected.sort(key=lambda x: x["price"], reverse=True)
    
    return subcat, selected

def generate_post():
    """Generate a new blog post."""
    products = load_products()
    if len(products) < 5:
        print("Not enough products to generate post")
        return False
    
    subcategory, selected = select_products_by_subcategory(products)
    
    # Determine price range
    prices = [p["price"] for p in selected]
    min_price = min(prices)
    max_price = max(prices)
    
    if max_price >= 1000000:
        price_range = f"di bawah {format_price(max_price)}"
    else:
        price_range = f"mulai {format_price(min_price)}"
    
    # Generate title
    year = 2026
    titles = [
        f"5 {subcategory} Terbaik {price_range} {year}",
        f"Rekomendasi 5 {subcategory} Terbaik {year} ({price_range})",
        f"5 {subcategory} Terbaik {year} — Update Harga Terbaru!",
        f"Top 5 {subcategory} Paling Worth It {year}",
    ]
    title = random.choice(titles)
    
    # Generate slug and filename (support multiple posts per day)
    date_str = datetime.now().strftime("%Y-%m-%d")
    base_slug = title.lower().replace(" ", "-").replace("/", "-").replace("—", "-").replace("(", "").replace(")", "").replace("!", "").replace("?", "")[:75]
    slug = f"{date_str}-{base_slug}"
    counter = 1
    while (POSTS_DIR / f"{slug}.md").exists():
        slug = f"{date_str}-{base_slug}-{counter}"
        counter += 1
    filename = POSTS_DIR / f"{slug}.md"
    
    # Post slug for URL (without date prefix)
    if counter == 1:
        post_slug = base_slug
    else:
        post_slug = f"{base_slug}-{counter-1}"
    
    # Check if post already exists for today
    if filename.exists():
        print(f"Post already exists: {filename}")
        return {"success": False, "reason": "exists"}
    
    # Prepare template variables
    image_slug = generate_slug(title)
    description = generate_description(selected, subcategory)
    intro = generate_intro(subcategory, 5, price_range)
    
    template_vars = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0700"),
        "title": title,
        "description": description,
        "image_slug": image_slug,
        "category": selected[0]["category"],
        "topic": subcategory,
        "intro": intro,
        "buying_tips": generate_buying_tips(subcategory),
        "closing_emoji": generate_closing_emoji(subcategory),
    }
    
    # Add product variables
    for i, p in enumerate(selected, 1):
        template_vars[f"p{i}_name"] = clean_product_name(p["name"])
        template_vars[f"p{i}_price"] = format_price(p["price"])
        template_vars[f"p{i}_link"] = p["link"]
        template_vars[f"p{i}_desc"] = generate_product_desc(p, i, subcategory)
        template_vars[f"p{i}_specs"] = generate_specs(p)
        template_vars[f"p{i}_target"] = generate_target_audience(p, subcategory)
    
    # Generate post content
    content = TEMPLATES_5.format(**template_vars)
    
    # Write file
    filename.write_text(content, encoding="utf-8")
    file_size = filename.stat().st_size
    print(f"Generated post: {filename} ({file_size} bytes)")
    
    if file_size == 0:
        print("❌ Generated file is empty (0 bytes), aborting.")
        filename.unlink()
        return {"success": False, "reason": "empty_file"}
    
    # Generate banner image
    banner_generated = False
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        banner_script = os.path.join(script_dir, "unsplash_banner.py")
        if os.path.exists(banner_script):
            result = subprocess.run(
                ["/usr/bin/python3.12", banner_script, image_slug, title, selected[0]["category"], subcategory],
                capture_output=True, text=True, timeout=30
            )
            print(result.stderr)  # Print search keyword info
            if result.returncode == 0:
                print(f"✅ Generated banner: {image_slug}.jpg")
                banner_generated = True
            else:
                print(f"⚠️ Banner generation failed: {result.stderr}")
    except Exception as e:
        print(f"⚠️ Could not generate banner: {e}")
    
    # Fallback image if banner was not generated
    if not banner_generated:
        fallback_banner = REPO_PATH / "assets" / "hero-banner.jpg"
        target_banner = REPO_PATH / "assets" / "images" / "posts" / f"{image_slug}-banner.jpg"
        if fallback_banner.exists() and not target_banner.exists():
            import shutil
            shutil.copy(str(fallback_banner), str(target_banner))
            print(f"🖼️ Using fallback banner: {target_banner}")
        # Update image reference in the post to use hero-banner if still missing
        if not target_banner.exists():
            # Replace image path in content to hero-banner
            content = content.replace(
                f'/assets/images/posts/{image_slug}-banner.jpg',
                '/assets/hero-banner.jpg'
            )
            filename.write_text(content, encoding="utf-8")
            print("📝 Updated image reference to fallback hero-banner.jpg")
    
    # Git commit and push
    try:
        # Load GH_TOKEN from .env
        env_path = REPO_PATH / ".env"
        gh_token = None
        if env_path.exists():
            with open(env_path, "r") as f:
                for line in f:
                    if line.startswith("GH_TOKEN="):
                        gh_token = line.strip().split("=", 1)[1]
                        break
        
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", str(filename)], check=True)
        
        # Only add banner image if it actually exists
        banner_path = REPO_PATH / "assets" / "images" / "posts" / f"{image_slug}-banner.jpg"
        if banner_path.exists() and banner_path.stat().st_size > 0:
            subprocess.run(["git", "add", str(banner_path)], check=True)
            print(f"✅ Banner image added: {banner_path}")
        else:
            print(f"⚠️ Banner image not found or empty, skipping: {banner_path}")
        
        subprocess.run(["git", "commit", "-m", f"🤖 Auto-generate: {title}"], check=True)
        
        # Push with token if available
        if gh_token:
            push_url = f"https://{gh_token}@github.com/ulasantekno/ulasantekno.github.io.git"
            subprocess.run(["git", "push", push_url, "main"], check=True)
            # Clean token from remote URL in git config (security)
            subprocess.run(["git", "remote", "set-url", "origin", "https://github.com/ulasantekno/ulasantekno.github.io.git"], check=False)
        else:
            subprocess.run(["git", "push", "origin", "main"], check=True)
            print("⚠️ Pushed without token (GH_TOKEN not found in .env)")
        
        print(f"✅ Successfully pushed: {title}")
        
        # Build article URL (match Jekyll permalink format)
        # Jekyll converts multiple dashes to single dash and uses UTC date
        now = datetime.now()
        jekyll_slug = base_slug.replace('---', '-').replace('--', '-')
        article_url = f"https://ulasanteknoid.my.id/{now.year}/{now.month:02d}/{now.day:02d}/{jekyll_slug}.html"
        return {
            "success": True,
            "title": title,
            "url": article_url,
            "slug": post_slug,
            "date": date_str,
            "subcategory": subcategory,
            "products": selected,
            "price_range": price_range,
            "image_slug": image_slug
        }
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")
        return {"success": False, "reason": "git_error", "error": str(e)}

if __name__ == "__main__":
    print(f"🚀 Auto-generate started at {datetime.now()}")
    result = generate_post()
    
    if result and result.get("success"):
        # Generate X/Threads caption
        x_caption = generate_x_caption(
            result['title'],
            result['url'],
            result['subcategory'],
            result['products'],
            result['price_range']
        )
        result['x_caption'] = x_caption
        
        # Save result to JSON for external tools
        result_file = REPO_PATH / ".last_generate_result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            # Remove non-serializable data
            json_result = {k: v for k, v in result.items() if k != 'products'}
            json.dump(json_result, f, indent=2, ensure_ascii=False)
        
        # Telegram notification
        tg_message = (
            f"✅ <b>Artikel Baru Terbit!</b>\n\n"
            f"📌 <b>{result['title']}</b>\n\n"
            f"🔗 {result['url']}\n\n"
            f"<b>📝 Caption X/Threads:</b>\n"
            f"<pre>{x_caption}</pre>\n\n"
            f"GitHub sudah di-push, tunggu 1-2 menit untuk build Jekyll."
        )
        send_telegram_notification(tg_message)
        
        # Also print to stdout for cronjob capture
        print("\n" + "="*50)
        print("📝 CAPTION X/THREADS:")
        print("="*50)
        print(x_caption)
        print("="*50)
        
    elif result and result.get("reason") == "exists":
        print("⏭️ Artikel hari ini sudah ada, skip.")
        # Save skip status
        result_file = REPO_PATH / ".last_generate_result.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({"success": False, "reason": "exists", "date": datetime.now().strftime("%Y-%m-%d")}, f)
    else:
        error_msg = result.get('error', 'Unknown error') if result else 'No result'
        send_telegram_notification(
            f"❌ <b>Auto-blog gagal</b>\n\n"
            f"Error: {error_msg}\n\n"
            f"Cek log di server ya."
        )
    
    exit(0 if (result and result.get("success")) else 1)
