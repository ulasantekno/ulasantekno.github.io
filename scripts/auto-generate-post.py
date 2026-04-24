#!/usr/bin/env python3
"""
Auto-generate blog posts from affiliate data.
Runs every 5 hours via cron.
"""

import json
import random
import os
import subprocess
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
image: "/assets/images/posts/{image_slug}.jpg"
category: {category}
---

{intro}

---

## 1. {p1_name}

- **Harga:** {p1_price}
- {p1_specs}

{p1_desc}

**Link Shopee:** [{p1_name}]({p1_link}){{:target="_blank"}}

---

## 2. {p2_name}

- **Harga:** {p2_price}
- {p2_specs}

{p2_desc}

**Link Shopee:** [{p2_name}]({p2_link}){{:target="_blank"}}

---

## 3. {p3_name}

- **Harga:** {p3_price}
- {p3_specs}

{p3_desc}

**Link Shopee:** [{p3_name}]({p3_link}){{:target="_blank"}}

---

## 4. {p4_name}

- **Harga:** {p4_price}
- {p4_specs}

{p4_desc}

**Link Shopee:** [{p4_name}]({p4_link}){{:target="_blank"}}

---

## 5. {p5_name}

- **Harga:** {p5_price}
- {p5_specs}

{p5_desc}

**Link Shopee:** [{p5_name}]({p5_link}){{:target="_blank"}}

---

## Kesimpulan

{conclusion}

Semua link di atas adalah **link affiliate Shopee**. Jika kamu membeli melalui link tersebut, kami mendapat komisi kecil tanpa biaya tambahan untukmu. Terima kasih sudah mendukung Ulasan Tekno! 🙏
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
    return name.lower().replace(" ", "-").replace("/", "-").replace("'", "").replace('"', "")[:50]

def generate_description(products, topic):
    """Generate SEO description."""
    names = ", ".join([p["name"].split()[0] for p in products[:3]])
    return f"Rekomendasi {topic} terbaik tahun 2026: {names} dengan harga terjangkau. Update harga dan link Shopee terbaru!"

def generate_intro(topic, count, price_range):
    """Generate introduction paragraph."""
    intros = [
        f"Tahun 2026, {topic} menjadi salah satu produk paling dicari di pasaran. Dengan berbagai pilihan dari brand ternama, menemukan {topic} terbaik dengan harga terjangkau bukan lagi hal sulit.",
        f"Bingung memilih {topic} yang tepat? Jangan khawatir! Kami telah merangkum {count} rekomendasi {topic} terbaik {price_range} yang paling worth it untuk tahun 2026.",
        f"Di artikel ini, kami akan membahas {count} {topic} terbaik dengan harga {price_range}. Dari fitur, spesifikasi, hingga link pembelian — semua lengkap di sini!",
    ]
    return random.choice(intros) + f"\n\nLangsung aja simak daftar {topic} terbaik berikut ini!"

def generate_conclusion(products, topic):
    """Generate conclusion paragraph."""
    best = products[0]
    value = min(products, key=lambda x: x["price"])
    
    conclusions = [
        f"Dari kelima {topic} di atas, pilihan terbaik untuk performa adalah **{best['name']}** dengan harga {format_price(best['price'])}. Tapi kalau budget terbatas, **{value['name']}** di harga {format_price(value['price'])} sudah sangat worth it!",
        f"Kesimpulannya, **{best['name']}** menawarkan value terbaik di kelasnya. Namun jika mencari yang paling terjangkau, **{value['name']}** adalah pilihan yang tidak kalah bagus.",
        f"Semua {topic} di atas sudah kami seleksi berdasarkan harga, fitur, dan ulasan pengguna. Pilihan terbaik jatuh pada **{best['name']}**, tapi **{value['name']}** adalah alternatif terbaik untuk budget minim.",
    ]
    return random.choice(conclusions)

def generate_product_desc(product, index):
    """Generate product description."""
    templates = [
        f"Produk #{index} dengan harga {format_price(product['price'])}. {product['name']} menawarkan fitur lengkap dengan harga yang sangat kompetitif.",
        f"Dengan harga {format_price(product['price'])}, {product['name']} adalah pilihan yang sangat worth it untuk budget kamu.",
        f"{product['name']} hadir dengan harga {format_price(product['price'])}. Produk ini menjadi favorit banyak pengguna berkat kualitas dan harganya yang bersahabat.",
    ]
    return random.choice(templates)

def generate_specs(product):
    """Generate specs list from product name or fallback."""
    name = product['name']
    specs = []
    
    # Extract common specs from name
    if 'GB' in name or 'TB' in name:
        specs.append('Storage besar untuk kebutuhan harian')
    if '5G' in name:
        specs.append('Jaringan 5G super cepat')
    if 'AMOLED' in name or 'QLED' in name or 'OLED' in name:
        specs.append('Panel layar premium dengan warna tajam')
    if 'Hz' in name:
        import re
        hz = re.search(r'(\d+)Hz', name)
        if hz:
            specs.append(f'Refresh rate {hz.group(1)}Hz untuk tampilan mulus')
    if '4K' in name:
        specs.append('Resolusi 4K Ultra HD')
    if 'Wireless' in name or 'TWS' in name or 'Bluetooth' in name:
        specs.append('Konektivitas wireless tanpa kabel')
    if 'Battery' in name or 'Days' in name or 'Hari' in name:
        specs.append('Baterai tahan lama')
    if 'W' in name and ('charger' in name.lower() or 'charging' in name.lower()):
        specs.append('Fast charging untuk pengisian cepat')
    if 'Smart' in name:
        specs.append('Fitur smart dengan kontrol aplikasi')
    if 'Gaming' in name:
        specs.append('Optimasi gaming untuk performa maksimal')
    
    if not specs:
        specs.append('Build quality terbaik di kelasnya')
        specs.append('Performa handal untuk penggunaan sehari-hari')
    
    return '\n- '.join(specs[:2])

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
    
    # Generate slug and filename
    date_str = datetime.now().strftime("%Y-%m-%d")
    slug = f"{date_str}-" + title.lower().replace(" ", "-").replace("/", "-").replace("—", "-").replace("(", "").replace(")", "").replace("!", "").replace("?", "")[:80]
    filename = POSTS_DIR / f"{slug}.md"
    
    # Check if post already exists for today
    if filename.exists():
        print(f"Post already exists: {filename}")
        return False
    
    # Prepare template variables
    image_slug = generate_slug(title)
    description = generate_description(selected, subcategory)
    intro = generate_intro(subcategory, 5, price_range)
    conclusion = generate_conclusion(selected, subcategory)
    
    template_vars = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M:%S +0700"),
        "title": title,
        "description": description,
        "image_slug": image_slug,
        "category": selected[0]["category"],
        "intro": intro,
        "conclusion": conclusion,
    }
    
    # Add product variables
    for i, p in enumerate(selected, 1):
        template_vars[f"p{i}_name"] = p["name"]
        template_vars[f"p{i}_price"] = format_price(p["price"])
        template_vars[f"p{i}_link"] = p["link"]
        template_vars[f"p{i}_desc"] = generate_product_desc(p, i)
        template_vars[f"p{i}_specs"] = generate_specs(p)
    
    # Generate post content
    content = TEMPLATES_5.format(**template_vars)
    
    # Write file
    filename.write_text(content, encoding="utf-8")
    print(f"Generated post: {filename}")
    
    # Generate banner image
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        banner_script = os.path.join(script_dir, "unsplash_banner.py")
        if os.path.exists(banner_script):
            result = subprocess.run(
                ["python3", banner_script, image_slug, f"5 {subcategory} Terbaik 2026"],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"✅ Generated banner: {image_slug}.jpg")
            else:
                print(f"⚠️ Banner generation failed: {result.stderr}")
    except Exception as e:
        print(f"⚠️ Could not generate banner: {e}")
    
    # Git commit and push
    try:
        os.chdir(REPO_PATH)
        subprocess.run(["git", "add", str(filename)], check=True)
        subprocess.run(["git", "commit", "-m", f"🤖 Auto-generate: {title}"], check=True)
        subprocess.run(["git", "push", "origin", "main"], check=True)
        print(f"✅ Successfully pushed: {title}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Git error: {e}")
        return False

if __name__ == "__main__":
    print(f"🚀 Auto-generate started at {datetime.now()}")
    success = generate_post()
    exit(0 if success else 1)
