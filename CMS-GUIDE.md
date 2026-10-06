# Vertusma Authority CMS Guide

The Vertusma website can be managed from:

```text
https://YOUR-DOMAIN.com/admin
```

Use the production admin email/password configured in the hosting environment.

## Overview
Shows current property, hero, inquiry, custom section, and custom page totals.

## Website Content
Use this area for the main website copy and structure:

- Site/company name, tagline and SEO metadata
- Main navigation links and CTA
- Homepage section order
- Hero statistics
- About section
- Services and service cards
- Portfolio labels and search wording
- Live metric labels
- Mission, vision and legacy
- Core values
- How We Work steps
- Testimonial/trust statement
- CTA panel
- Contact information and form options
- Floating contact button
- Footer
- Property-detail-page default wording

Use **Show section** checkboxes to hide or restore major sections. Use arrow buttons in **Homepage section order** to move sections up/down.

Always click **Save Website Content** after changing website content.

## Branding & Theme
Change the Vertusma logo, favicon and color system. Images can be uploaded directly from your computer.

The approved default colors are retained unless you change them.

Click **Save Branding** to publish the changes.

## Hero Slides
Add, edit, upload an image, reorder, hide/show, or delete homepage hero slides.

## Custom Sections
Use **Custom Sections** when you want to add a new block to the homepage without a developer.

Each section supports:

- Anchor / section ID
- Eyebrow
- Heading
- Multiple paragraphs
- Image upload
- CTA button
- Theme
- Display order
- Active/hidden state

## Custom Pages
Use **Custom Pages** for new standalone pages such as:

- Investor Relations
- Careers
- FAQ
- Hospitality
- About a specific service
- New market/location information

A page URL is:

```text
/page/YOUR-SLUG
```

Example:

```text
/page/investor-relations
```

After creating a page, add that URL to **Website Content → Navigation** if you want it in the main menu.

Pages support publish/draft mode, image upload, CTA and SEO metadata.

## Properties
The property CMS allows the authority to:

- Add/edit/delete properties
- Set a custom URL slug
- Type any property sector/type
- Set portfolio status
- Upload the main property image
- Add an optional price/rate label
- Add units and square footage
- Feature a property
- Publish or keep it as a draft
- Set property-specific SEO metadata

Draft properties are not visible on the public website.

## Inquiries
Review contact-form leads, change the lead status, or delete inquiries.

## Image Uploads
The CMS accepts JPG, PNG, WEBP and GIF images up to 6 MB.

Uploaded media is stored in:

```text
public/uploads/
```

## Backup
For a complete CMS backup, preserve both:

```text
data/vertusma.db
public/uploads/
```

The database contains properties, inquiries, website settings, custom pages and custom sections. The uploads folder contains media uploaded from the CMS.


## Diverse People, Images & Videos

The **Website Content → Diverse people, images & videos** area controls the new residential, commercial, and hospitality media showcase.

- Add, remove, and reorder media cards.
- Upload card images directly from the admin portal.
- Use the image description field for accessible alt text.
- Add a public HTTPS MP4 video URL for a card to show a Play button.
- Videos are loaded only after a visitor clicks Play, which keeps the homepage lighter.
- For the strongest brand presentation, use authentic visuals showing residents, professionals, guests, and hospitality teams from varied racial and ethnic backgrounds in realistic property environments.
