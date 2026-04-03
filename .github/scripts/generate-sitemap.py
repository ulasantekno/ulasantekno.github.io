#!/usr/bin/env python3
"""
Generate sitemap.xml for UlasanTekno Jekyll site.
Run this script after any changes to _posts or static pages.
"""

import os
import re
import sys
from datetime import datetime

POSTS_DIR = '_posts'
URL_BASE = 'https://ulasantekno.github.io'
SITEMAP_PATH = 'sitemap.xml'

STATIC_PAGES = [
    ('', 'weekly', '1.0'),
    ('about.html', 'monthly', '0.8'),
    ('archive.html', 'monthly', '0.8'),
    ('contact.html', 'monthly', '0.7'),
    ('disclaimer.html', 'monthly', '0.5'),
    ('privacy-policy.html', 'yearly', '0.5'),
]

def extract_date_from_frontmatter(filepath):
    """Extract date from YAML frontmatter."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for date: YYYY-MM-DD
            match = re.search(r'date:\s*(\d{4}-\d{2}-\d{2})', content)
            if match:
                return match.group(1)
    except Exception:
        pass
    return None

def generate_post_url(filename):
    """Generate Jekyll-style permalink from filename."""
    slug = filename[:-3]  # remove .md
    parts = slug.split('-')
    if len(parts) >= 3:
        year, month, day = parts[0], parts[1], parts[2]
        title_slug = '-'.join(parts[3:])
        return f'{URL_BASE}/{year}/{month}/{day}/{title_slug}.html'
    else:
        # fallback
        return f'{URL_BASE}/{slug}.html'

def main():
    print(f"Generating sitemap for {URL_BASE}")
    
    # Start XML
    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    
    # Static pages
    for page, changefreq, priority in STATIC_PAGES:
        loc = URL_BASE + ('/' + page if page else '')
        xml_lines.extend([
            '  <url>',
            f'    <loc>{loc}</loc>',
            f'    <lastmod>{datetime.now().strftime("%Y-%m-%d")}</lastmod>',
            f'    <changefreq>{changefreq}</changefreq>',
            f'    <priority>{priority}</priority>',
            '  </url>',
        ])
    
    # Posts
    post_files = sorted([f for f in os.listdir(POSTS_DIR) if f.endswith('.md')])
    for filename in post_files:
        filepath = os.path.join(POSTS_DIR, filename)
        post_date = extract_date_from_frontmatter(filepath)
        if not post_date:
            # fallback to filename date
            match = re.match(r'(\d{4})-(\d{2})-(\d{2})', filename)
            if match:
                post_date = f'{match[1]}-{match[2]}-{match[3]}'
            else:
                post_date = datetime.now().strftime('%Y-%m-%d')
        
        url = generate_post_url(filename)
        xml_lines.extend([
            '  <url>',
            f'    <loc>{url}</loc>',
            f'    <lastmod>{post_date}</lastmod>',
            '    <changefreq>monthly</changefreq>',
            '    <priority>0.6</priority>',
            '  </url>',
        ])
    
    xml_lines.append('</urlset>')
    
    # Write to file
    with open(SITEMAP_PATH, 'w', encoding='utf-8') as f:
        f.write('\n'.join(xml_lines))
    
    print(f"Sitemap generated with {len(post_files)} posts.")
    sys.exit(0)

if __name__ == '__main__':
    main()