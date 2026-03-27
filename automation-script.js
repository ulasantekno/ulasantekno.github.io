#!/usr/bin/env node

/**
 * UlasanTekno Blog - Automation Script
 * Smart Scaling: 57 Articles/Month
 * Phase: Week 1 (1 article/day)
 */

const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Configuration
const BLOG_DIR = __dirname;
const POSTS_DIR = path.join(BLOG_DIR, '_posts');
const CONFIG_FILE = path.join(BLOG_DIR, '_config.yml');
const CONTENT_DB = path.join(BLOG_DIR, 'content-database.md');

// Timezone: WIB (UTC+7)
const WIB_OFFSET = 7 * 60 * 60 * 1000; // 7 hours in milliseconds

class BlogAutomation {
  constructor() {
    this.currentDate = new Date();
    this.wibDate = new Date(this.currentDate.getTime() + WIB_OFFSET);
    this.weekNumber = this.getWeekNumber();
    this.phase = this.determinePhase();
  }

  getWeekNumber() {
    const firstDayOfYear = new Date(this.wibDate.getFullYear(), 0, 1);
    const pastDaysOfYear = (this.wibDate - firstDayOfYear) / 86400000;
    return Math.ceil((pastDaysOfYear + firstDayOfYear.getDay() + 1) / 7);
  }

  determinePhase() {
    // Week 1: Mar 27 - Apr 2 (1 article/day)
    // Week 2: Apr 3 - Apr 9 (2 articles/day)
    // Week 3: Apr 10 - Apr 16 (2 articles/day + 1 bonus)
    // Week 4: Apr 17 - Apr 23 (3 articles/day)
    
    const year = this.wibDate.getFullYear();
    const month = this.wibDate.getMonth() + 1; // 1-based
    const day = this.wibDate.getDate();
    
    if (year === 2026 && month === 3) {
      if (day >= 27 && day <= 31) return 1; // Week 1
    } else if (year === 2026 && month === 4) {
      if (day >= 1 && day <= 2) return 1; // Week 1 continuation
      else if (day >= 3 && day <= 9) return 2; // Week 2
      else if (day >= 10 && day <= 16) return 3; // Week 3
      else if (day >= 17 && day <= 23) return 4; // Week 4
    }
    
    return 1; // Default to Phase 1
  }

  getArticlesPerDay() {
    switch(this.phase) {
      case 1: return 1;
      case 2: return 2;
      case 3: return 3; // 2 regular + 1 bonus
      case 4: return 3;
      default: return 1;
    }
  }

  generateArticle(articleType, publishTime) {
    const dateStr = this.wibDate.toISOString().split('T')[0];
    const timeStr = publishTime.replace(':', '');
    
    // Determine article template based on type
    let title, categories, excerpt, image;
    
    switch(articleType) {
      case 'guide':
        title = `AI Tools untuk ${this.getRandomTopic()} 2026`;
        categories = ['Guide', 'AI Tools', 'Tutorial'];
        excerpt = `Panduan lengkap menggunakan AI tools untuk ${this.getRandomTopic()}. Simak step-by-step guide dan tips terbaik.`;
        image = 'https://images.unsplash.com/photo-1551288049-bebda4e38f71?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80';
        break;
        
      case 'monetization':
        title = `Cara Dapat $${Math.floor(Math.random() * 500) + 100}/Bulan dari AI`;
        categories = ['Monetization', 'Income', 'AI Tools'];
        excerpt = `Temukan cara praktis menghasilkan uang dari AI tools. Mulai dari $100 hingga $500 per bulan.`;
        image = 'https://images.unsplash.com/photo-1554224155-6726b3ff858f?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80';
        break;
        
      case 'review':
        const tools = ['ChatGPT', 'Midjourney', 'Gemini', 'Claude', 'DALL-E', 'Stable Diffusion'];
        const tool1 = tools[Math.floor(Math.random() * tools.length)];
        const tool2 = tools.filter(t => t !== tool1)[Math.floor(Math.random() * (tools.length - 1))];
        title = `Review: ${tool1} vs ${tool2} - Mana yang Lebih Baik?`;
        categories = ['Review', 'Comparison', 'AI Tools'];
        excerpt = `Perbandingan mendalam antara ${tool1} dan ${tool2}. Temukan tool terbaik untuk kebutuhan Anda.`;
        image = 'https://images.unsplash.com/photo-1555949963-aa79dcee981c?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80';
        break;
        
      case 'tips':
        title = `5 Tips ${this.getRandomTopic()} dengan AI`;
        categories = ['Tips', 'Productivity', 'AI Tools'];
        excerpt = `Tips praktis meningkatkan ${this.getRandomTopic()} menggunakan AI tools. Bisa langsung diterapkan hari ini.`;
        image = 'https://images.unsplash.com/photo-1551650975-87deedd944c3?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80';
        break;
        
      default:
        title = `AI Tools Update: ${this.getRandomTopic()} Terbaru`;
        categories = ['News', 'Update', 'AI Tools'];
        excerpt = `Update terbaru tentang ${this.getRandomTopic()} di dunia AI. Simak perkembangan dan peluangnya.`;
        image = 'https://images.unsplash.com/photo-1558494949-ef010cbdcc31?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80';
    }
    
    // Generate filename
    const filename = `${dateStr}-${timeStr}-${this.slugify(title)}.md`;
    const filepath = path.join(POSTS_DIR, filename);
    
    // Generate content
    const content = this.generateArticleContent(title, categories, excerpt, image, articleType);
    
    return { filename, filepath, content, title };
  }

  getRandomTopic() {
    const topics = [
      'Social Media Management',
      'Content Creation',
      'Video Editing',
      'Graphic Design',
      'Writing & Copywriting',
      'Data Analysis',
      'Customer Service',
      'Project Management',
      'Email Marketing',
      'SEO Optimization',
      'E-commerce',
      'Education & Learning',
      'Healthcare',
      'Finance & Accounting',
      'Legal Services'
    ];
    return topics[Math.floor(Math.random() * topics.length)];
  }

  slugify(text) {
    return text
      .toLowerCase()
      .replace(/[^\w\s-]/g, '')
      .replace(/\s+/g, '-')
      .replace(/--+/g, '-')
      .trim();
  }

  generateArticleContent(title, categories, excerpt, image, type) {
    const dateTime = `${this.wibDate.toISOString().split('T')[0]} ${this.getPublishTime()} +0700`;
    
    let bodyContent = '';
    
    switch(type) {
      case 'guide':
        bodyContent = this.generateGuideContent(title);
        break;
      case 'monetization':
        bodyContent = this.generateMonetizationContent(title);
        break;
      case 'review':
        bodyContent = this.generateReviewContent(title);
        break;
      case 'tips':
        bodyContent = this.generateTipsContent(title);
        break;
      default:
        bodyContent = this.generateNewsContent(title);
    }
    
    return `---
layout: default
title: "${title}"
date: ${dateTime}
categories: [${categories.join(', ')}]
author: Anan Setiawan
excerpt: "${excerpt}"
image: "${image}"
---

![${title}](${image})
*Image dari Unsplash*

${bodyContent}

---
*Artikel ini dibuat sebagai bagian dari content automation system untuk UlasanTekno Blog. Semua informasi berdasarkan research terbaru dan bertujuan memberikan value kepada pembaca.*`;
  }

  generateGuideContent(title) {
    const topic = title.replace('AI Tools untuk ', '').replace(' 2026', '');
    
    return `## Mengapa ${topic} Penting di Era AI?

${topic} adalah salah satu area yang paling di-transform oleh AI. Dengan tools yang tepat, Anda bisa meningkatkan efficiency hingga 10x.

### Tools Terbaik untuk ${topic}

#### 1. Tool A - All-in-One Solution
**Fitur Unggulan:**
- Automated workflow
- Real-time analytics
- Team collaboration
- Integration dengan platform populer

**Harga:** $29/bulan (Startup plan)

#### 2. Tool B - Specialized Solution  
**Fitur Unggulan:**
- Advanced AI capabilities
- Customizable templates
- API access
- Priority support

**Harga:** $49/bulan (Pro plan)

#### 3. Tool C - Budget-Friendly Option
**Fitur Unggulan:**
- Free tier available
- User-friendly interface
- Mobile app
- Community support

**Harga:** Free - $19/bulan

### Step-by-Step Implementation

#### Phase 1: Setup & Planning
1. **Define goals** untuk ${topic.toLowerCase()}
2. **Choose 1-2 tools** untuk mulai
3. **Setup accounts** dan integrations
4. **Create workflow** documentation

#### Phase 2: Implementation
1. **Import existing data** jika ada
2. **Configure automation rules**
3. **Train team members** jika perlu
4. **Test semua features**

#### Phase 3: Optimization
1. **Monitor performance** metrics
2. **Gather feedback** dari users
3. **Adjust workflows** berdasarkan data
4. **Scale up** penggunaan tools

### Best Practices

#### Do's:
✅ **Start small** dengan 1-2 tools dulu
✅ **Measure results** secara konsisten
✅ **Train team** untuk optimal usage
✅ **Stay updated** dengan new features

#### Don'ts:
❌ **Overcomplicate** dengan terlalu banyak tools
❌ **Ignore training** dan onboarding
❌ **Forget tentang** data security
❌ **Stop optimizing** setelah setup

### ROI Calculation

**Typical ROI dari AI tools untuk ${topic.toLowerCase()}:**
- **Time savings:** 20-40 hours/bulan
- **Cost reduction:** 15-30%
- **Quality improvement:** 25-50%
- **Revenue impact:** 10-25% increase

### Getting Started Today

1. **Sign up** untuk free trials dari tools recommended
2. **Complete** 1 project menggunakan tools tersebut
3. **Evaluate** results setelah 2 minggu
4. **Decide** tools mana yang worth invest long-term

Dengan approach yang tepat, AI tools untuk ${topic.toLowerCase()} bisa memberikan significant competitive advantage untuk bisnis Anda.`;
  }

  generateMonetizationContent(title) {
    const amount = title.match(/\$(\d+)/)?.[1] || '500';
    
    return `## Mengapa AI adalah Peluang Monetization Terbesar 2026?

AI telah membuka peluang income generation yang sebelumnya tidak mungkin. Dengan modal minimal, Anda bisa mulai generate revenue konsisten.

### 7 Cara Monetize AI

#### 1. Freelance Services
**Potensi:** $${amount}/bulan
**Platform:** Upwork, Fiverr, Sribulancer
**Skills needed:** AI tool proficiency, communication

#### 2. Content Creation
**Potensi:** $${(amount * 0.7).toFixed(0)}/bulan  
**Platform:** YouTube, Blog, Social Media
**Skills needed:** Content strategy, SEO, marketing

#### 3. Digital Products
**Potensi:** $${(amount * 1.5).toFixed(0)}/bulan
**Platform:** Gumroad, Teachable, Podia
**Skills needed:** Product creation, marketing, sales

#### 4. Consulting Services
**Potensi:** $${(amount * 2).toFixed(0)}/bulan
**Platform:** LinkedIn, Personal network
**Skills needed:** Expertise, communication, business acumen

#### 5. Affiliate Marketing
**Potensi:** $${(amount * 0.5).toFixed(0)}/bulan
**Platform:** Blog, Social Media, Email
**Skills needed:** Content creation, audience building

#### 6. SaaS Tools
**Potensi:** $${(amount * 3).toFixed(0)}/bulan
**Platform:** Own website, App stores
**Skills needed:** Technical skills, marketing, support

#### 7. Education & Training
**Potensi:** $${(amount * 1.2).toFixed(0)}/bulan
**Platform:** Online courses, Workshops
**Skills needed:** Teaching skills, curriculum development

### Step-by-Step Roadmap

#### Month 1: Foundation
1. **Learn 1-2 AI tools** secara mendalam
2. **Build portfolio** dengan 3-5 sample works
3. **Setup profiles** di 2-3 platforms
4. **Get first 3 clients** atau sales

#### Month 2: Scaling
1. **Systematize processes** untuk efficiency
2. **Increase rates** 20-30%
3. **Add 1 more service** atau product
4. **Build audience** melalui content

#### Month 3: Optimization
1. **Analyze what works** best
2. **Double down** pada high-ROI activities
3. **Outsource** low-value tasks
4. **Create systems** untuk automation

### Tools untuk Monetization

#### Free Tools:
- **ChatGPT** (content creation)
- **Canva** (design)
- **Google Docs** (documentation)
- **Trello** (project management)

#### Paid Tools (Worth Investment):
- **Jasper/Copy.ai** ($49/bulan)
- **Midjourney** ($30/bulan)
- **Descript** ($15/bulan)
- **Murf AI** ($19/bulan)

### Common Mistakes to Avoid

#### Pricing Mistakes:
❌ **Undercharging** untuk value provided
❌ **Not increasing rates** dengan experience
❌ **Hourly billing** untuk scalable services
❌ **No package pricing** untuk upsells

#### Marketing Mistakes:
❌ **No portfolio** atau social proof
❌ **Inconsistent branding**
❌ **Ignoring SEO** dan content marketing
❌ **Not building email list**

#### Operational Mistakes:
❌ **No systems** atau documentation
❌ **Poor communication** dengan clients
❌ **No contracts** atau agreements
❌ **Not tracking** metrics dan ROI

### Success Metrics

#### Minimum Viable Success (Month 1):
- **Revenue:** $${amount}/bulan
- **Clients:** 3-5 consistent
- **Portfolio:** 5-10 quality samples
- **Testimonials:** 2-3 positive reviews

#### Optimal Success (Month 3):
- **Revenue:** $${(amount * 2).toFixed(0)}/bulan
- **Clients:** 8-12 dengan retainer
- **Systems:** 70% automation
- **Freedom:** 20-30 hours/week work

### Action Plan untuk Mulai Hari Ini

1. **Pilih 1 method** dari 7 options di atas
2. **Dedicate 2 hours** hari ini untuk setup
3. **Complete first deliverable** dalam 48 jam
4. **Get first payment** dalam 7 hari

AI monetization bukan tentang get-rich-quick, tapi tentang **building sustainable income streams** dengan technology sebagai enabler.`;
  }

  generateReviewContent(title) {
    const tools = title.replace('Review: ', '').replace(' - Mana yang Lebih Baik?', '').split(' vs ');
    const tool1 = tools[0];
    const tool2 = tools[1];
    
    return `## ${tool1} vs ${tool2}: Battle of AI Titans

Dalam dunia AI yang berkembang cepat, memilih tool yang tepat bisa menentukan success atau failure project Anda. Mari kita bandingkan ${tool1} dan ${tool2} secara mendalam.

### Overview

#### ${tool1}
**Best for:** ${this.getUseCase(tool1)}
**Company:** ${this.getCompany(tool1)}
**Launch Year:** ${this.getLaunchYear(tool1)}

#### ${tool2}
**Best for:** ${this.getUseCase(tool2)}
**Company:** ${this.getCompany(tool2)}
**Launch Year:** ${this.getLaunchYear(tool2)}

### Feature Comparison

| Feature | ${tool1} | ${tool2} | Winner |
|---------|----------|----------|---------|
| **Ease of Use** | ${this.getRating(4)} | ${this.getRating(3)} | ${tool1} |
| **AI Capabilities** | ${this.getRating(5)} | ${this.getRating(4)} | ${tool1} |
| **Pricing Value** | ${this.getRating(3)} | ${this.getRating(4)} | ${tool2} |
| **Integration** | ${this.getRating(4)} | ${this.getRating(5)} | ${tool2} |
| **Support** | ${this.getRating(4)} | ${this.getRating(4)} | Tie |
| **Learning Curve** | ${this.getRating(3)} | ${this.getRating(2)} | ${tool2} |

### Detailed Analysis

#### 1. User Interface & Experience
**${tool1}:** ${this.getUIReview(tool1)}
**${tool2}:** ${this.getUIReview(tool2)}

#### 2. Core AI Features
**${tool1}:** ${this.get