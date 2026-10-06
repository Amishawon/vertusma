# Vertusma Property Management — Fully Dynamic CMS Edition

This is the Namecheap/cPanel-compatible custom Vertusma Property Management website. It uses a dependency-free Python WSGI backend, HTML/CSS/JavaScript frontend, and SQLite database.

## Authority-controlled CMS

The `/admin` portal is now the control center for the website. The site authority can manage content without editing source code.

### Website Content
- Company/site name, tagline, browser title and SEO description
- Main navigation links and navigation CTA
- Homepage hero statistics
- About section copy, buttons, image and image note
- Services heading and an unlimited/reorderable service list
- Diverse People & Media showcase for residential, commercial, and hospitality visuals
- Inclusive media cards support direct image uploads plus public HTTPS MP4 video URLs
- Portfolio headings and search wording
- Live portfolio metric labels
- Mission, vision and legacy statements
- Unlimited/reorderable core values
- Unlimited/reorderable process steps
- Testimonial/trust statement and image
- Main CTA section
- Contact section, public email, service area, sectors, form labels/options and success message
- Floating contact CTA
- Footer copy, columns, links, sectors, location, copyright and tagline
- Property-detail-page default labels and CTAs
- Show/hide controls for major homepage sections
- Reorder the core homepage sections from the CMS

### Branding & Theme
- Upload/replace primary logo, dark/admin logo and favicon
- Change the full brand color system from the CMS
- Client-approved default palette remains Deep Navy + White + Heritage Gold

### Hero Slider
- Add, edit, upload image, hide/show, reorder and delete hero slides

### Custom Homepage Sections
- Add unlimited new homepage content sections
- Editable anchor, eyebrow, title, body, image, CTA, theme, order and visibility
- White, Warm Ivory, Deep Navy and Executive Navy section styles

### Custom Pages
- Create standalone pages without a developer
- Editable page title, URL slug, eyebrow, intro, body, hero image, CTA and SEO metadata
- Publish/draft control
- Public URLs use `/page/page-slug`
- Add a custom page to the main menu from Website Content → Navigation

### Properties
- Add/edit/delete properties
- Any property type/sector can be typed in; it is no longer limited to hard-coded categories
- Flexible portfolio status
- Upload property image or use an image URL
- Optional price/rate label
- Units and square footage
- Featured flag
- Publish/draft control
- Editable URL slug
- Per-property SEO title and description
- Public property filters are generated dynamically from published property sectors

### Inquiries
- View incoming contact inquiries
- Update lead status
- Delete inquiries

### Image Uploads
Images can be uploaded directly from the admin portal. Uploaded JPG, PNG, WEBP and GIF files are stored under:

```text
public/uploads/
```

Maximum image size: 6 MB.

## Technology
- Python WSGI backend
- SQLite database
- HTML5 / CSS3 / vanilla JavaScript frontend
- Passenger/cPanel compatible
- No third-party Python packages required

## Local testing

Windows:

```text
start-local.bat
```

macOS/Linux:

```bash
chmod +x start-local.sh
./start-local.sh
```

Open:

```text
Website: http://127.0.0.1:8000
Admin:   http://127.0.0.1:8000/admin
```

Default local credentials:

```text
Email: admin@vertusma.com
Password: ChangeMe123!
```

Set secure environment credentials before production.

## Client-approved brand defaults

- Deep Navy `#0B1F33`
- Executive Navy `#132C44`
- Heritage Gold `#B08D57`
- Soft Gold `#D2B887`
- White `#FFFFFF`
- Warm Ivory `#F7F5F0`
- Body text `#30343B`
- Muted text `#667085` / `#98A2B3`
- Borders `#E5E7EB`
- Footer `#071522`

These defaults can now also be changed by the authority from **Admin → Branding & Theme**.

## Production deployment

See `NAMECHEAP-DEPLOYMENT.md`.
