---
name: local-seo-optimizer
description: "Full local SEO optimization for client websites built with React + Vite + TypeScript. Use this skill any time the user mentions SEO, search engine optimization, meta tags, schema markup, Google Business Profile, local search ranking, sitemap, robots.txt, structured data, or wants to optimize a client website for search visibility. Also trigger when the user wants to create service-specific landing pages, add Open Graph / Twitter Card tags, or generate SEO strategy documents and GBP setup guides."
---

# Local SEO Optimizer

This skill performs a complete local SEO overhaul on a React + Vite + TypeScript client website. It takes a site from zero SEO infrastructure to fully optimized with meta tags, schema markup, individual service pages, and deliverable strategy documents — all in one session.

The workflow is designed for local service businesses (contractors, agencies, tradespeople, etc.) whose websites are typically single-page React apps with no SEO work done yet. The output is dramatic: a site that was invisible to Google becomes properly indexed with rich results, service-specific landing pages targeting real search queries, and professional documents the client can act on independently.

## Prerequisites

The target project should be a React + Vite + TypeScript frontend. The skill will install additional dependencies as needed (`react-router-dom`, `react-helmet-async`). If the project uses a different stack, adapt the implementation patterns accordingly but follow the same SEO strategy.

## Workflow Overview

The process has 7 phases. Complete them in order — each phase builds on the previous one.

1. **Discovery** — Gather business details, audit the current site
2. **Research** — Identify competitors and target keywords
3. **Homepage SEO** — Meta tags, Open Graph, Twitter Cards, JSON-LD schema, geographic tags
4. **Crawlability** — robots.txt and sitemap.xml
5. **Service Pages** — Individual landing pages with unique SEO per service
6. **Code Quality** — Alt tags, internal linking, semantic HTML, tests
7. **Deliverables** — SEO strategy document and Google Business Profile setup guide

---

## Phase 1: Discovery

### Gather Business Information

Before touching any code, collect these details from the user. Ask questions conversationally — don't dump a form at them. Some of this may already be available in the codebase or conversation history.

**Required:**
- Business name and display name
- Physical address (street, city, state, zip)
- Phone number and email
- Website URL / domain
- Service area (city, county, state, or radius)
- List of services offered
- Business hours
- Social media URLs (Facebook, Instagram, etc.)

**Helpful but not blocking:**
- Year founded, founder name
- Price range indicator (e.g., "$$")
- Payment methods accepted
- Any existing Google Business Profile
- Any existing reviews or testimonials
- Unique selling points or stats (e.g., "Over 11,000 acres treated")

### Audit the Current Site

Open the site (or read the codebase) and check for:
- Existing meta tags in `index.html` (title, description, keywords)
- Any structured data / JSON-LD
- robots.txt and sitemap.xml in `public/`
- Image alt attributes
- Internal linking structure
- Whether routing exists (react-router-dom) or if it's a single-page render
- Existing page components and their structure

Document what's missing. Almost everything will be missing for a typical client site — that's expected and fine.

---

## Phase 2: Research

### Competitor Research

Search for 3-5 competitors in the same service area and industry. Look at:
- What keywords they rank for
- How their title tags and meta descriptions are structured
- Whether they have individual service pages
- Their Google Business Profile presence

Use web search to find competitors. A good search query pattern: `"{service type} {city/state}"` (e.g., "drone spraying Nebraska", "plumber Denver CO").

### Keyword Identification

For each service the business offers, identify:
- **Primary keyword**: The main search term (e.g., "agricultural drone spraying Nebraska")
- **Secondary keywords**: Variations and long-tail terms (e.g., "drone crop spraying", "aerial spraying services near me")
- **Location modifiers**: City, state, region variants

Structure keywords so each service page targets a distinct primary keyword. Avoid keyword cannibalization — no two pages should target the same primary term.

---

## Phase 3: Homepage SEO

### Install Dependencies

If not already present:

```bash
cd frontend && npm install react-router-dom react-helmet-async
```

### Update `index.html`

This is the most impactful single file change. Add all of the following to `<head>`:

**Primary meta tags:**
```html
<title>{Business Name} | {Primary Service} in {Location}</title>
<meta name="description" content="{Compelling 150-160 char description with primary keyword, location, phone number}" />
<meta name="keywords" content="{comma-separated keywords covering all services and location}" />
<meta name="robots" content="index, follow" />
<link rel="canonical" href="https://{domain}/" />
```

**Geographic meta tags** (critical for local SEO):
```html
<meta name="geo.region" content="US-{STATE}" />
<meta name="geo.placename" content="{City}, {State}" />
<meta name="geo.position" content="{latitude};{longitude}" />
<meta name="ICBM" content="{latitude}, {longitude}" />
```

**Open Graph tags** (for Facebook/LinkedIn sharing):
```html
<meta property="og:type" content="website" />
<meta property="og:url" content="https://{domain}/" />
<meta property="og:title" content="{Business Name} | {Services} in {Location}" />
<meta property="og:description" content="{Compelling description}" />
<meta property="og:image" content="https://{domain}/og-image.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:site_name" content="{Business Name}" />
<meta property="og:locale" content="en_US" />
```

**Twitter Card tags:**
```html
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{Business Name} | {Services} in {Location}" />
<meta name="twitter:description" content="{Compelling description}" />
<meta name="twitter:image" content="https://{domain}/og-image.jpg" />
```

### JSON-LD Structured Data in `index.html`

Add two JSON-LD blocks as `<script type="application/ld+json">` in `<head>`:

**1. LocalBusiness schema** — This is the most important schema for local SEO. Include:
- `@type`: "LocalBusiness" (or a more specific subtype like "HomeAndConstructionBusiness")
- `name`, `alternateName`, `description`, `url`, `telephone`, `email`
- `image`, `logo`
- `foundingDate`, `founder` (if known)
- `address` as PostalAddress
- `geo` as GeoCoordinates
- `areaServed` (State, City, or GeoCircle)
- `openingHoursSpecification` array
- `priceRange`
- `paymentAccepted`
- `hasOfferCatalog` with an `OfferCatalog` listing each service as a Service offer
- `sameAs` array with social media URLs

**2. WebSite schema** — Simple but enables sitelinks in search results:
```json
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "{Business Name}",
  "url": "https://{domain}",
  "description": "{Short description}"
}
```

### Add Helmet to Landing Page

Wrap the existing landing/home page component with `<Helmet>` from `react-helmet-async` to set homepage-specific meta tags. This allows the homepage to have its own title/description while service pages override them.

Update `main.tsx` to wrap the app with `<HelmetProvider>` and `<BrowserRouter>`:

```tsx
import { BrowserRouter } from 'react-router-dom'
import { HelmetProvider } from 'react-helmet-async'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HelmetProvider>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </HelmetProvider>
  </StrictMode>,
)
```

---

## Phase 4: Crawlability

### robots.txt

Create `frontend/public/robots.txt`:

```
# {Business Name} - robots.txt
User-agent: *
Allow: /

# Sitemap location
Sitemap: https://{domain}/sitemap.xml

# Block crawling of internal/dev assets
Disallow: /assets/
```

### sitemap.xml

Create `frontend/public/sitemap.xml` listing every page. The homepage gets priority 1.0, service pages get 0.8-0.9:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://{domain}/</loc>
    <lastmod>{today's date}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <!-- One <url> entry per service page -->
  <url>
    <loc>https://{domain}/services/{service-slug}</loc>
    <lastmod>{today's date}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>
```

---

## Phase 5: Service Pages

This is the highest-value phase for local SEO. Each service gets its own URL with unique keywords, schema, and content — turning one generic page into many targeted landing pages that Google can rank individually.

### Set Up Routing

Update `App.tsx` to use React Router:

```tsx
import { Routes, Route } from 'react-router-dom'
import { LandingPage } from './pages/LandingPage'
import { ServicePage } from './pages/ServicePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/services/:slug" element={<ServicePage />} />
    </Routes>
  )
}
```

### Create Service Data File

Create `src/data/servicePages.ts` with a typed array of service definitions. Each service should have:

```ts
export interface ServicePageData {
  slug: string              // URL-friendly identifier
  title: string             // Display title
  metaTitle: string         // SEO title tag (include location + keyword)
  metaDescription: string   // 150-160 chars with keyword, location, phone
  keywords: string          // Comma-separated target keywords
  heroHeading: string
  heroSubheading: string
  content: {
    intro: string           // 2-3 sentences, front-load the primary keyword
    howItWorks: string      // Process description
    benefits: string[]      // 4-6 bullet points
    whyDrone: string        // (or whyService) — differentiator paragraph
    cta: string             // Call to action text
  }
  faq: Array<{ question: string; answer: string }>  // 3-5 FAQ items per service
  relatedServices: string[] // slugs of related services for internal linking
}
```

Export a `getServiceBySlug(slug)` helper function.

**Content writing guidelines:**
- Front-load the primary keyword in the first sentence of each section
- Include the business location/service area naturally in the text
- Write FAQ questions the way a real customer would ask them (use "How much does...", "What areas do you...", "How long does...")
- Each FAQ answer should be 2-4 sentences — enough for Google to pull as a featured snippet
- Related services create internal links, which helps SEO — every service should link to 2-3 others

### Create Service Page Component

Create `src/pages/ServicePage.tsx` with:

**Per-page SEO via Helmet:**
- Unique `<title>` from `metaTitle`
- Unique `<meta name="description">` from `metaDescription`
- Unique `<meta name="keywords">`
- Canonical URL: `https://{domain}/services/{slug}`
- Open Graph tags with service-specific title/description
- Twitter Card tags

**Per-page JSON-LD schemas:**
1. **Service schema** — `@type: "Service"` with name, description, provider (referencing the LocalBusiness `@id` from index.html), areaServed, and URL
2. **FAQPage schema** — `@type: "FAQPage"` with the FAQ Q&A pairs (this is what makes FAQ rich results appear in Google)
3. **BreadcrumbList schema** — Home > Services > {Service Name}

**Page structure:**
- Breadcrumb navigation (Home > {Service Name})
- Hero section with heading and subheading
- Content body: intro, how it works, benefits list, differentiator
- FAQ accordion (expandable Q&A sections)
- Sidebar with CTA card (phone number, contact prompt) and related service links
- Full footer with navigation links to all services (internal linking is critical for SEO)

### Add Service Page CSS

Add styles for the service page layout to `src/global.css`. Key elements to style:
- `.service-breadcrumbs` — breadcrumb navigation
- `.service-hero` — hero banner
- `.service-content` — two-column layout (main + sidebar)
- `.service-benefits` — benefits list
- `.service-faq` — accordion FAQ
- `.service-sidebar`, `.service-cta-card` — sidebar elements
- Responsive breakpoints for mobile

---

## Phase 6: Code Quality

### Image Alt Tags

Audit every `<img>` tag in the codebase. Replace empty or missing `alt` attributes with descriptive text that includes the business name where natural:
- Logo: `alt="{Business Name} logo"`
- Service images: `alt="{Business Name} {service description}"`
- Generic photos: descriptive text about what's shown

### Internal Linking

Update the landing page footer and any navigation to use `<Link>` components (from react-router-dom) pointing to each service page. Every page on the site should link to every other page through navigation or footer — this creates a strong internal link graph.

### Semantic HTML

Ensure proper heading hierarchy (one `<h1>` per page, `<h2>` for sections, etc.) and use semantic elements (`<nav>`, `<main>`, `<article>`, `<section>`, `<footer>`).

### Update Tests

Update `App.test.tsx` to wrap the app with `<HelmetProvider>` and `<BrowserRouter>` since routing is now required. Add the `setupTests.ts` mocks if needed:

```ts
// Mock IntersectionObserver for jsdom (if scroll animations are used)
globalThis.IntersectionObserver = class IntersectionObserver {
  readonly root: Element | null = null
  readonly rootMargin: string = ''
  readonly thresholds: ReadonlyArray<number> = []
  constructor() {}
  observe() { return null }
  unobserve() { return null }
  disconnect() { return null }
  takeRecords(): IntersectionObserverEntry[] { return [] }
}

// Mock matchMedia for responsive hooks
globalThis.matchMedia = globalThis.matchMedia || function(query: string) {
  return {
    matches: false, media: query, onchange: null,
    addListener: function() {}, removeListener: function() {},
    addEventListener: function() {}, removeEventListener: function() {},
    dispatchEvent: function() { return false },
  }
}
```

Run all tests and fix any failures before moving on.

---

## Phase 7: Deliverables

Generate two professional documents for the client using the `docx` skill.

### SEO Strategy Document

A comprehensive document covering:
1. **SEO business context** — summary of the business, target market, competitive landscape
2. **Google Business Profile setup guide** — step-by-step instructions with pre-written content the client can copy/paste into their GBP
3. **90-day SEO roadmap** — phased plan for ongoing optimization (month 1: GBP + citations, month 2: reviews + content, month 3: backlinks + monitoring)
4. **Website changes summary** — table of every SEO change made to the site with before/after descriptions

### Google Business Profile Setup Guide (Standalone)

A separate, client-facing document focused solely on GBP setup. This is the one the client will actually use — keep the language simple and actionable. Include:
1. Step-by-step instructions for claiming/creating the GBP listing
2. Pre-written business description they can copy/paste
3. Recommended categories (primary + secondary)
4. Service list with descriptions
5. Photo recommendations
6. Post templates for the first few GBP posts
7. Checklist table they can print and work through

Both documents should be `.docx` format so the client can edit them.

---

## Common Gotchas

These are issues that came up during the original development of this workflow. Watch out for them:

- **IntersectionObserver in tests**: If the site uses scroll animations with IntersectionObserver, jsdom doesn't support it. Add the mock to `setupTests.ts` before running tests.
- **matchMedia in tests**: Same issue if responsive hooks use `window.matchMedia`. Add the mock.
- **File sync between Windows and Linux mounts**: If editing files via the Edit tool and running tests via bash, there can be sync delays. If tests don't see your changes, try writing the file directly via bash (`cat > file << 'EOF'`).
- **Null bytes from edits**: Large files edited repeatedly can accumulate null bytes. If you see TS1127 "Invalid character" errors, clean with: `tr -d '\0' < file.tsx > file.tmp && mv file.tmp file.tsx`
- **Test wrapper updates**: After adding routing and Helmet, existing tests will break if they don't wrap the component in `<BrowserRouter>` and `<HelmetProvider>`. Update the test render helpers.
- **Unused imports**: TypeScript strict mode will flag unused imports. Clean up after refactoring (e.g., remove `useCallback` if you remove a callback).

---

## Checklist

Use this to verify completeness before wrapping up:

- [ ] `index.html` has: title, description, keywords, canonical, robots, geo tags, OG tags, Twitter tags, LocalBusiness JSON-LD, WebSite JSON-LD
- [ ] `robots.txt` exists in `public/` with sitemap reference
- [ ] `sitemap.xml` exists in `public/` listing all pages
- [ ] `react-router-dom` and `react-helmet-async` are installed
- [ ] `main.tsx` wraps app with `HelmetProvider` and `BrowserRouter`
- [ ] `App.tsx` uses `Routes` with home and service page routes
- [ ] Service data file exists with typed definitions for each service
- [ ] Each service has: unique metaTitle, metaDescription, keywords, FAQ items, related services
- [ ] Service page component has: Helmet with unique SEO, Service/FAQ/Breadcrumb JSON-LD schemas
- [ ] All images have descriptive alt tags
- [ ] Footer and navigation link to all service pages using `<Link>` components
- [ ] Landing page has `<Helmet>` with homepage meta tags
- [ ] All tests pass
- [ ] SEO strategy document generated (.docx)
- [ ] GBP setup guide generated (.docx)
