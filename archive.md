---
layout: default
title: "Archive - Semua Artikel"
permalink: /archive.html
---

<div class="archive-header">
  <h1>📚 Semua Artikel</h1>
  <p>Koleksi lengkap artikel UlasanTekno</p>
</div>

<div class="category-filter">
  <h3>Filter by Kategori:</h3>
  <div class="category-tags">
    <a href="/archive.html" class="category-tag">Semua</a>
    <a href="/archive.html#productivity" class="category-tag">Productivity</a>
    <a href="/archive.html#ai-tools" class="category-tag">AI Tools</a>
    <a href="/archive.html#review" class="category-tag">Review</a>
    <a href="/archive.html#comparison" class="category-tag">Comparison</a>
    <a href="/archive.html#tutorial" class="category-tag">Tutorial</a>
  </div>
</div>

<div class="archive-list">
  {% for post in site.posts %}
  <div class="archive-item">
    <h3><a href="{{ post.url }}">{{ post.title }}</a></h3>
    <div class="archive-meta">
      <span class="archive-date">{{ post.date | date: "%d %B %Y" }}</span>
      <span class="archive-category">
        {% if post.categories %}
          {{ post.categories | join: ", " }}
        {% endif %}
      </span>
    </div>
    <p class="archive-excerpt">
      {% if post.excerpt %}
        {{ post.excerpt }}
      {% else %}
        {{ post.content | strip_html | truncate: 150 }}
      {% endif %}
    </p>
  </div>
  {% endfor %}
</div>

<style>
.archive-header {
  text-align: center;
  margin-bottom: 40px;
  padding-bottom: 20px;
  border-bottom: 2px solid #159957;
}

.archive-header h1 {
  color: #155799;
  margin-bottom: 10px;
}

.archive-header p {
  color: #666;
  font-size: 1.1em;
}

.category-filter {
  text-align: center;
  margin-bottom: 40px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.category-filter h3 {
  color: #155799;
  margin-bottom: 15px;
  font-size: 1.1em;
}

.category-tags {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 10px;
}

.category-tag {
  display: inline-block;
  padding: 6px 14px;
  background: #fff;
  color: #155799;
  text-decoration: none;
  border-radius: 20px;
  font-size: 0.9em;
  border: 1px solid #155799;
  transition: all 0.2s;
}

.category-tag:hover {
  background: #155799;
  color: #fff;
}

.archive-list {
  max-width: 800px;
  margin: 0 auto;
}

.archive-item {
  margin-bottom: 30px;
  padding-bottom: 25px;
  border-bottom: 1px solid #eee;
}

.archive-item h3 {
  margin-bottom: 8px;
}

.archive-item h3 a {
  color: #155799;
  text-decoration: none;
}

.archive-item h3 a:hover {
  color: #159957;
  text-decoration: underline;
}

.archive-meta {
  display: flex;
  gap: 20px;
  margin-bottom: 10px;
  font-size: 0.9em;
  color: #777;
}

.archive-date {
  color: #159957;
  font-weight: 500;
}

.archive-excerpt {
  color: #555;
  line-height: 1.6;
}

@media screen and (max-width: 768px) {
  .archive-meta {
    flex-direction: column;
    gap: 5px;
  }
}
</style>
