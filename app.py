#!/usr/bin/env python3
"""Vertusma Property Management — dependency-free WSGI application.

This edition is designed for cPanel/CloudLinux "Setup Python App" hosting,
including Namecheap Shared Hosting. Passenger imports ``application`` from
``passenger_wsgi.py``.

No third-party Python package is required.

Local test:
    python app.py
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import mimetypes
import os
import re
import secrets
import sqlite3
import time
import urllib.parse
from datetime import datetime, timezone
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Any, Callable, Iterable
from wsgiref.simple_server import make_server

BASE_DIR = Path(__file__).resolve().parent
PUBLIC_DIR = BASE_DIR / "public"
DATA_DIR = BASE_DIR / "data"
DB_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "vertusma.db"))).expanduser()
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@vertusma.com").strip().lower()
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", str(60 * 60 * 12)))
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "0").strip() == "1"
MAX_BODY_BYTES = 10_000_000
UPLOAD_DIR = PUBLIC_DIR / "uploads"
MAX_UPLOAD_BYTES = 6_000_000

PROPERTY_TYPES = {
    "Residential",
    "Multifamily",
    "Commercial",
    "Hospitality",
    "Industrial",
    "Mixed-Use",
    "Adaptive Reuse",
}
PROPERTY_STATUSES = {"Managed", "Owned & Managed", "Investment", "Development"}
INQUIRY_STATUSES = {"New", "Contacted", "Qualified", "Closed"}

DEFAULT_SITE_CONFIG: dict[str, Any] = {
    "identity": {
        "site_name": "Vertusma Property Management",
        "tagline": "Stewardship. Performance. Hospitality.",
        "meta_title": "Vertusma Property Management | Stewardship. Performance. Hospitality.",
        "meta_description": "Vertusma Property Management delivers exceptional stewardship, asset management, hospitality, and operational excellence across diversified real estate portfolios.",
        "logo_url": "/assets/logo.svg",
        "logo_dark_url": "/assets/logo-dark.svg",
        "favicon_url": "/assets/logo-dark.svg"
    },
    "theme": {
        "deep_navy": "#0B1F33", "executive_navy": "#132C44", "heritage_gold": "#B08D57",
        "soft_gold": "#D2B887", "white": "#FFFFFF", "ivory": "#F7F5F0",
        "body_text": "#30343B", "muted_text": "#667085", "secondary_muted": "#98A2B3",
        "border": "#E5E7EB", "footer_bg": "#071522", "footer_text": "#B8C0CA"
    },
    "homepage_order": ["about", "services", "inclusiveMediaSection", "metricsSection", "portfolio", "mission", "values", "processSection", "testimonialSection", "ctaSection", "customSectionsHost", "contact"],
    "navigation": {
        "items": [
            {"label": "Home", "url": "/"}, {"label": "About", "url": "/about"},
            {"label": "Services", "url": "/services"}, {"label": "Portfolio", "url": "/portfolio"},
            {"label": "Contact", "url": "/contact"}
        ],
        "cta_label": "Discuss Your Property", "cta_url": "/contact"
    },
    "hero_extras": {
        "stat_2_value": "360°", "stat_2_label": "Asset stewardship",
        "stat_3_value": "24/7", "stat_3_label": "Service mindset", "scroll_label": "Scroll to discover"
    },
    "about": {
        "enabled": True, "eyebrow": "The Vertusma Standard", "title": "Every property should inspire pride.",
        "paragraph_1": "We manage residential, multifamily, commercial, hospitality, industrial, mixed-use, and adaptive reuse properties with one clear standard: protect the asset, serve the people, and strengthen long-term performance.",
        "paragraph_2": "Our approach combines hands-on property care, disciplined financial oversight, responsive communication, data-informed decisions, and a genuine hospitality mindset.",
        "button_label": "Our Mission & Vision", "button_url": "#mission",
        "image_url": "https://images.pexels.com/photos/7578877/pexels-photo-7578877.jpeg?auto=compress&cs=tinysrgb&w=1600",
        "image_alt": "Diverse prospective residents and a real estate professional outside a modern home",
        "note_title": "Stewardship in every detail.", "note_text": "Clean environments. Strong operations. Enduring value."
    },
    "services": {
        "enabled": True, "eyebrow": "Integrated Capabilities", "title": "Management built around the complete life of an asset.",
        "button_label": "Request a Consultation", "button_url": "/contact",
        "items": [
            {"title": "Property Management", "description": "Resident and tenant relations, inspections, maintenance, vendor coordination, leasing support, compliance, and daily operations."},
            {"title": "Asset Management", "description": "Strategic planning, performance analysis, capital allocation, risk oversight, reporting, and long-term value creation."},
            {"title": "Hospitality Operations", "description": "Guest experience, service standards, property presentation, operational coordination, and brand-conscious hospitality management."},
            {"title": "Investment Strategy", "description": "Opportunity evaluation, acquisition support, business planning, portfolio strategy, repositioning, and investment stewardship."},
            {"title": "Development & Repositioning", "description": "Adaptive reuse, renovations, capital projects, design coordination, operational readiness, and market-focused repositioning."},
            {"title": "Financial Oversight", "description": "Prudent budgeting, cash flow monitoring, expense control, owner reporting, forecasting, and transparent financial accountability."}
        ]
    },
    "inclusive_media": {
        "enabled": True,
        "eyebrow": "People · Places · Experiences",
        "title": "Welcoming spaces for every community.",
        "description": "Vertusma serves people from diverse racial and ethnic backgrounds across residential, commercial, and hospitality environments. Our visual story reflects the communities, teams, guests, residents, and partners our properties are designed to welcome.",
        "items": [
            {
                "category": "Residential",
                "title": "Homes where people feel welcome.",
                "description": "Resident-focused environments shaped around comfort, belonging, responsive service, and long-term quality of life.",
                "image_url": "https://images.pexels.com/photos/7578877/pexels-photo-7578877.jpeg?auto=compress&cs=tinysrgb&w=1400",
                "image_alt": "Diverse homebuyers and real estate professional outside a residential property",
                "video_url": "https://videos.pexels.com/video-files/7647241/7647241-uhd_3840_2160_24fps.mp4",
                "video_label": "Watch residential experience"
            },
            {
                "category": "Commercial",
                "title": "Workplaces built for connection.",
                "description": "Professional spaces that support diverse teams, productive tenancy, collaboration, and strong business experiences.",
                "image_url": "https://images.pexels.com/photos/8112161/pexels-photo-8112161.jpeg?auto=compress&cs=tinysrgb&w=1400",
                "image_alt": "Diverse professionals collaborating in a modern commercial office",
                "video_url": "https://videos.pexels.com/video-files/7147624/7147624-uhd_3840_2160_25fps.mp4",
                "video_label": "Watch commercial experience"
            },
            {
                "category": "Hospitality",
                "title": "Hospitality that welcomes every guest.",
                "description": "Thoughtful service, polished environments, and genuine care for travelers, guests, teams, and communities from every background.",
                "image_url": "https://images.pexels.com/photos/5378707/pexels-photo-5378707.jpeg?auto=compress&cs=tinysrgb&w=1400",
                "image_alt": "Hotel staff assisting a diverse guest couple in a premium hospitality setting",
                "video_url": "https://videos.pexels.com/video-files/7820474/7820474-hd_1920_1080_25fps.mp4",
                "video_label": "Watch hospitality experience"
            }
        ]
    },
    "metrics": {
        "enabled": True, "label": "Live portfolio overview", "title": "Performance starts with visibility.",
        "properties_label": "Assets in portfolio", "sectors_label": "Property sectors", "units_label": "Units / keys", "area_label": "Total square feet"
    },
    "portfolio": {
        "enabled": True, "eyebrow": "Selected Portfolio", "title": "Diverse assets. One uncompromising standard.",
        "button_label": "View Full Portfolio", "button_url": "/portfolio", "search_placeholder": "Search city, state or property"
    },
    "mission": {
        "enabled": True, "eyebrow": "Purpose & Direction", "title": "We protect what matters—and improve what is possible.",
        "mission_title": "Mission Statement",
        "mission_p1": "At Vertusma Property Management, our mission is to elevate the standard of property management by delivering exceptional stewardship, operational excellence, and personalized service across residential, commercial, multifamily, hospitality, and mixed-use properties.",
        "mission_p2": "Through integrity, innovation, proactive management, and disciplined financial oversight, we create clean, safe, well-maintained, and welcoming environments while protecting and enhancing the long-term value of every asset entrusted to our care.",
        "vision_title": "Vision Statement",
        "vision_p1": "Our vision is to become a premier real estate investment, asset management, and hospitality company recognized for transforming properties into exceptional destinations and high-performing investments.",
        "vision_p2": "We envision every Vertusma-managed property reflecting excellence in design, maintenance, hospitality, sustainability, and customer experience—creating enduring investor value, vibrant communities, and spaces where people can live, work, stay, and thrive.",
        "legacy_title": "Our Legacy", "legacy_text": "Our legacy will be measured not only by the properties we own and manage, but by the trust we earn, the communities we strengthen, and the lasting impact we create for generations to come."
    },
    "values": {
        "enabled": True, "eyebrow": "Our Core Values", "title": "The principles behind every decision.",
        "items": [
            {"title": "Integrity", "description": "Honesty, transparency, accountability, and ethical decisions centered on our clients and partners."},
            {"title": "Stewardship", "description": "We treat every property as our own, preserving, protecting, and enhancing its long-term value."},
            {"title": "Excellence", "description": "We pursue an exceptional standard across maintenance, financial management, service, and hospitality."},
            {"title": "Hospitality", "description": "We create welcoming environments through professionalism, respect, responsiveness, and genuine care."},
            {"title": "Innovation", "description": "Technology, data, and continuous improvement help us deliver smarter property solutions."},
            {"title": "Financial Responsibility", "description": "Disciplined oversight, prudent budgeting, and strategic planning safeguard every investment."},
            {"title": "Community", "description": "Safe, attractive, inclusive properties strengthen neighborhoods and local economic growth."},
            {"title": "Sustainability", "description": "Responsible operations and energy efficiency support clients, communities, and future generations."},
            {"title": "Partnership", "description": "Collaboration with owners, investors, residents, vendors, employees, and communities drives shared success."},
            {"title": "Service Above Expectations", "description": "Responsive communication and dependable execution inspire confidence, loyalty, and trust."}
        ]
    },
    "process": {
        "enabled": True, "eyebrow": "How We Work", "title": "Clarity from first conversation to long-term performance.",
        "items": [
            {"title": "Understand", "description": "We learn the asset, ownership priorities, stakeholder needs, risks, and performance goals."},
            {"title": "Plan", "description": "We establish an operational, financial, maintenance, service, and reporting roadmap."},
            {"title": "Execute", "description": "Our team coordinates people, vendors, systems, communication, and accountability."},
            {"title": "Improve", "description": "We measure outcomes, identify opportunities, and continuously strengthen asset performance."}
        ]
    },
    "testimonial": {
        "enabled": True, "eyebrow": "A Trusted Operating Partner",
        "quote": "Vertusma brings an ownership mindset to management—balancing the details people experience every day with the decisions that shape long-term value.",
        "author": "Investment Partner", "role": "Multifamily & mixed-use portfolio",
        "image_url": "https://images.pexels.com/photos/5378703/pexels-photo-5378703.jpeg?auto=compress&cs=tinysrgb&w=1400"
    },
    "cta": {
        "enabled": True, "eyebrow": "Build Enduring Value",
        "title": "Let’s create a better experience for your property, your people, and your investment.",
        "primary_label": "Start a Conversation", "primary_url": "/contact",
        "secondary_label": "info@vertusma.com", "secondary_url": "mailto:info@vertusma.com"
    },
    "contact": {
        "enabled": True, "eyebrow": "Contact Vertusma", "title": "Tell us about your property or investment goals.",
        "description": "Whether you are seeking property management, asset oversight, hospitality expertise, investment support, or a strategic operating partner, we welcome the conversation.",
        "email": "info@vertusma.com", "service_area": "United States · Select Markets",
        "sectors": "Residential · Commercial · Hospitality · Mixed-Use",
        "interest_options": ["Property Management", "Asset Management", "Hospitality Operations", "Investment Opportunity", "Development or Repositioning", "Other"],
        "submit_label": "Send Inquiry", "success_message": "Thank you. A Vertusma team member will contact you shortly."
    },
    "floating_cta": {"enabled": True, "label": "Discuss your property", "url": "/contact"},
    "footer": {
        "copy": "Exceptional stewardship, operational excellence, and personalized service across real estate, asset management, and hospitality.",
        "company_title": "Company",
        "company_links": [{"label": "About", "url": "/about"}, {"label": "Services", "url": "/services"}, {"label": "Portfolio", "url": "/portfolio"}, {"label": "Contact", "url": "/contact"}],
        "sectors_title": "Sectors", "sectors": ["Residential", "Multifamily", "Commercial", "Hospitality", "Mixed-Use"],
        "connect_title": "Connect", "location": "United States", "show_admin_link": True,
        "copyright": "Vertusma Property Management LLC. All rights reserved.", "bottom_tagline": "Stewardship · Performance · Hospitality"
    },
    "property_page": {
        "overview_eyebrow": "Property Overview", "overview_title_template": "Managing {title} with purpose.",
        "primary_label": "Discuss a Similar Property", "primary_url": "/contact", "secondary_label": "Back to Portfolio", "secondary_url": "/portfolio",
        "cta_eyebrow": "A Better Operating Partner", "cta_title": "Bring the Vertusma standard to your real estate portfolio.",
        "cta_label": "Start a Conversation", "cta_url": "/contact"
    }
}

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-") or f"property-{secrets.token_hex(3)}"


def db_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_database() -> None:
    with db_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS properties (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                property_type TEXT NOT NULL,
                city TEXT NOT NULL,
                state TEXT NOT NULL,
                status TEXT NOT NULL,
                address TEXT NOT NULL DEFAULT '',
                short_description TEXT NOT NULL,
                description TEXT NOT NULL,
                image_url TEXT NOT NULL DEFAULT '',
                units INTEGER NOT NULL DEFAULT 0,
                square_feet INTEGER NOT NULL DEFAULT 0,
                featured INTEGER NOT NULL DEFAULT 0 CHECK(featured IN (0,1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS hero_slides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eyebrow TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                highlight TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL,
                image_url TEXT NOT NULL,
                primary_label TEXT NOT NULL DEFAULT 'Explore Our Portfolio',
                primary_url TEXT NOT NULL DEFAULT '/portfolio',
                secondary_label TEXT NOT NULL DEFAULT 'Partner With Vertusma',
                secondary_url TEXT NOT NULL DEFAULT '/contact',
                sort_order INTEGER NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL DEFAULT '',
                interest TEXT NOT NULL,
                message TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'New',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS site_settings (
                id INTEGER PRIMARY KEY CHECK(id = 1),
                config_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS custom_sections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                anchor TEXT NOT NULL UNIQUE,
                eyebrow TEXT NOT NULL DEFAULT '',
                title TEXT NOT NULL,
                body TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                button_label TEXT NOT NULL DEFAULT '',
                button_url TEXT NOT NULL DEFAULT '',
                theme TEXT NOT NULL DEFAULT 'ivory',
                sort_order INTEGER NOT NULL DEFAULT 100,
                active INTEGER NOT NULL DEFAULT 1 CHECK(active IN (0,1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                slug TEXT NOT NULL UNIQUE,
                eyebrow TEXT NOT NULL DEFAULT '',
                intro TEXT NOT NULL DEFAULT '',
                body TEXT NOT NULL DEFAULT '',
                image_url TEXT NOT NULL DEFAULT '',
                button_label TEXT NOT NULL DEFAULT '',
                button_url TEXT NOT NULL DEFAULT '',
                seo_title TEXT NOT NULL DEFAULT '',
                seo_description TEXT NOT NULL DEFAULT '',
                published INTEGER NOT NULL DEFAULT 1 CHECK(published IN (0,1)),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                created_at INTEGER NOT NULL,
                expires_at INTEGER NOT NULL
            );
            """
        )
        # Safe schema upgrades for installations created by earlier Vertusma builds.
        existing_columns = {row[1] for row in conn.execute("PRAGMA table_info(properties)").fetchall()}
        for column, definition in {
            "price": "TEXT NOT NULL DEFAULT ''",
            "published": "INTEGER NOT NULL DEFAULT 1",
            "seo_title": "TEXT NOT NULL DEFAULT ''",
            "seo_description": "TEXT NOT NULL DEFAULT ''"
        }.items():
            if column not in existing_columns:
                conn.execute(f"ALTER TABLE properties ADD COLUMN {column} {definition}")
        if conn.execute("SELECT COUNT(*) FROM site_settings").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO site_settings (id, config_json, updated_at) VALUES (1, ?, ?)",
                (json.dumps(DEFAULT_SITE_CONFIG, ensure_ascii=False), utc_now()),
            )
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        if conn.execute("SELECT COUNT(*) FROM properties").fetchone()[0] == 0:
            seed_properties(conn)
        if conn.execute("SELECT COUNT(*) FROM hero_slides").fetchone()[0] == 0:
            seed_hero_slides(conn)


def seed_properties(conn: sqlite3.Connection) -> None:
    now = utc_now()
    rows = [
        (
            "The Meridian Residences",
            "the-meridian-residences",
            "Multifamily",
            "Atlanta",
            "GA",
            "Managed",
            "Midtown Atlanta, Georgia",
            "A modern multifamily community positioned for resident comfort and long-term performance.",
            "Vertusma oversees operations, resident experience, preventive maintenance, vendor management, budgeting, and asset-level reporting for this contemporary residential community.",
            "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?auto=format&fit=crop&w=1600&q=85",
            168,
            214000,
            1,
            now,
            now,
        ),
        (
            "Harborline Business Center",
            "harborline-business-center",
            "Commercial",
            "Tampa",
            "FL",
            "Owned & Managed",
            "Westshore, Tampa, Florida",
            "A professionally managed business environment designed for productive, lasting tenancy.",
            "Our team coordinates leasing support, building systems, tenant relations, capital planning, and disciplined financial oversight to protect the property's competitive position.",
            "https://images.pexels.com/photos/8112161/pexels-photo-8112161.jpeg?auto=compress&cs=tinysrgb&w=1600",
            34,
            126000,
            1,
            now,
            now,
        ),
        (
            "Solara Hotel & Courtyard",
            "solara-hotel-courtyard",
            "Hospitality",
            "Charleston",
            "SC",
            "Investment",
            "Historic District, Charleston, South Carolina",
            "A hospitality asset shaped around memorable stays, operational discipline, and local character.",
            "Vertusma's hospitality strategy integrates guest experience, property presentation, revenue awareness, maintenance standards, and partnership-driven operations.",
            "https://images.pexels.com/photos/7512139/pexels-photo-7512139.jpeg?auto=compress&cs=tinysrgb&w=1600",
            92,
            88000,
            1,
            now,
            now,
        ),
        (
            "Oak & Foundry District",
            "oak-and-foundry-district",
            "Mixed-Use",
            "Nashville",
            "TN",
            "Development",
            "Wedgewood-Houston, Nashville, Tennessee",
            "An adaptive mixed-use concept connecting residences, workplaces, retail, and neighborhood life.",
            "The project vision combines thoughtful redevelopment, flexible commercial space, community-oriented amenities, and sustainable long-term asset planning.",
            "https://images.unsplash.com/photo-1497366811353-6870744d04b2?auto=format&fit=crop&w=1600&q=85",
            74,
            176000,
            0,
            now,
            now,
        ),
        (
            "Cedar Grove Homes",
            "cedar-grove-homes",
            "Residential",
            "Charlotte",
            "NC",
            "Managed",
            "South Charlotte, North Carolina",
            "A collection of welcoming homes maintained for comfort, curb appeal, and dependable ownership returns.",
            "Vertusma manages resident communication, inspections, maintenance coordination, leasing workflows, and owner reporting across the portfolio.",
            "https://images.pexels.com/photos/7937731/pexels-photo-7937731.jpeg?auto=compress&cs=tinysrgb&w=1600",
            24,
            48600,
            0,
            now,
            now,
        ),
        (
            "Northgate Logistics Campus",
            "northgate-logistics-campus",
            "Industrial",
            "Dallas",
            "TX",
            "Investment",
            "North Dallas, Texas",
            "A scalable industrial asset focused on uptime, tenant service, safety, and efficient operations.",
            "Management priorities include facility readiness, preventive maintenance, contract oversight, compliance coordination, and performance reporting.",
            "https://images.unsplash.com/photo-1553413077-190dd305871c?auto=format&fit=crop&w=1600&q=85",
            8,
            310000,
            0,
            now,
            now,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO properties (
            title, slug, property_type, city, state, status, address,
            short_description, description, image_url, units, square_feet,
            featured, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def seed_hero_slides(conn: sqlite3.Connection) -> None:
    now = utc_now()
    rows = [
        (
            "Real Estate · Asset Management · Hospitality",
            "Properties cared for.",
            "Value built to last.",
            "Vertusma elevates property performance through exceptional stewardship, disciplined operations, thoughtful hospitality, and personalized service.",
            "https://images.pexels.com/photos/7578877/pexels-photo-7578877.jpeg?auto=compress&cs=tinysrgb&w=2200",
            "Explore Our Portfolio", "/portfolio", "Partner With Vertusma", "/contact", 10, 1, now, now,
        ),
        (
            "Ownership-Minded Property Management",
            "Operational excellence.",
            "Every day, every detail.",
            "From resident experience and preventive maintenance to financial oversight and reporting, we manage every touchpoint with an ownership mindset.",
            "https://images.pexels.com/photos/8112161/pexels-photo-8112161.jpeg?auto=compress&cs=tinysrgb&w=2200",
            "Discover Our Services", "/services", "Discuss Your Property", "/contact", 20, 1, now, now,
        ),
        (
            "Strategy · Repositioning · Long-Term Performance",
            "Better decisions today.",
            "Stronger assets tomorrow.",
            "Vertusma connects asset strategy, capital planning, hospitality thinking, and disciplined execution to create durable long-term value.",
            "https://images.pexels.com/photos/5378707/pexels-photo-5378707.jpeg?auto=compress&cs=tinysrgb&w=2200",
            "View Featured Assets", "/portfolio", "Start a Conversation", "/contact", 30, 1, now, now,
        ),
    ]
    conn.executemany(
        """
        INSERT INTO hero_slides (
            eyebrow, title, highlight, description, image_url, primary_label, primary_url,
            secondary_label, secondary_url, sort_order, active, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )


def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    result = dict(row)
    for key in ("featured", "active", "published"):
        if key in result:
            result[key] = bool(result[key])
    return result


def deep_merge(default: Any, override: Any) -> Any:
    if isinstance(default, dict) and isinstance(override, dict):
        result = dict(default)
        for key, value in override.items():
            result[key] = deep_merge(default.get(key), value) if key in default else value
        return result
    return override if override is not None else default


def get_site_config() -> dict[str, Any]:
    with db_connection() as conn:
        row = conn.execute("SELECT config_json FROM site_settings WHERE id = 1").fetchone()
    if not row:
        return json.loads(json.dumps(DEFAULT_SITE_CONFIG))
    try:
        saved = json.loads(row["config_json"])
    except (TypeError, json.JSONDecodeError):
        saved = {}
    return deep_merge(DEFAULT_SITE_CONFIG, saved if isinstance(saved, dict) else {})


def save_site_config(config: dict[str, Any]) -> dict[str, Any]:
    merged = deep_merge(DEFAULT_SITE_CONFIG, config)
    with db_connection() as conn:
        conn.execute(
            "INSERT INTO site_settings (id, config_json, updated_at) VALUES (1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET config_json=excluded.config_json, updated_at=excluded.updated_at",
            (json.dumps(merged, ensure_ascii=False), utc_now()),
        )
    return merged


def query_custom_sections(admin: bool = False) -> list[dict[str, Any]]:
    with db_connection() as conn:
        if admin:
            rows = conn.execute("SELECT * FROM custom_sections ORDER BY sort_order ASC, id ASC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM custom_sections WHERE active = 1 ORDER BY sort_order ASC, id ASC").fetchall()
    return [row_to_dict(row) for row in rows]


def query_pages(admin: bool = False) -> list[dict[str, Any]]:
    with db_connection() as conn:
        if admin:
            rows = conn.execute("SELECT * FROM pages ORDER BY updated_at DESC, id DESC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM pages WHERE published = 1 ORDER BY title COLLATE NOCASE ASC").fetchall()
    return [row_to_dict(row) for row in rows]


class Request:
    def __init__(self, environ: dict[str, Any]):
        self.environ = environ
        self.method = str(environ.get("REQUEST_METHOD", "GET")).upper()
        self.path = str(environ.get("PATH_INFO", "/")) or "/"
        self.query = urllib.parse.parse_qs(str(environ.get("QUERY_STRING", "")))

    def query_value(self, name: str, default: str = "") -> str:
        values = self.query.get(name)
        return str(values[0]) if values else default

    def json(self) -> dict[str, Any] | None:
        try:
            length = int(self.environ.get("CONTENT_LENGTH") or "0")
        except (TypeError, ValueError):
            return None
        if length <= 0 or length > MAX_BODY_BYTES:
            return None
        raw = self.environ["wsgi.input"].read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    def cookie(self, name: str) -> str | None:
        header = str(self.environ.get("HTTP_COOKIE", ""))
        if not header:
            return None
        cookie = SimpleCookie()
        try:
            cookie.load(header)
        except Exception:
            return None
        morsel = cookie.get(name)
        return morsel.value if morsel else None


class Response:
    def __init__(
        self,
        body: bytes | str = b"",
        status: int = HTTPStatus.OK,
        content_type: str = "text/plain; charset=utf-8",
        headers: list[tuple[str, str]] | None = None,
    ):
        self.body = body.encode("utf-8") if isinstance(body, str) else body
        self.status = int(status)
        self.headers = list(headers or [])
        self.headers.extend(
            [
                ("Content-Type", content_type),
                ("Content-Length", str(len(self.body))),
                ("X-Content-Type-Options", "nosniff"),
                ("X-Frame-Options", "SAMEORIGIN"),
                ("Referrer-Policy", "strict-origin-when-cross-origin"),
                ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
            ]
        )

    def wsgi(self, start_response: StartResponse) -> Iterable[bytes]:
        phrase = HTTPStatus(self.status).phrase if self.status in HTTPStatus._value2member_map_ else "Unknown"
        start_response(f"{self.status} {phrase}", self.headers)
        return [self.body]


def json_response(data: Any, status: int = HTTPStatus.OK, headers: list[tuple[str, str]] | None = None) -> Response:
    all_headers = [("Cache-Control", "no-store")]
    if headers:
        all_headers.extend(headers)
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return Response(body, status, "application/json; charset=utf-8", all_headers)


def json_error(status: int, message: str, details: Any | None = None) -> Response:
    payload: dict[str, Any] = {"error": message}
    if details is not None:
        payload["details"] = details
    return json_response(payload, status)


def file_response(path: Path, status: int = HTTPStatus.OK) -> Response:
    try:
        content = path.read_bytes()
    except OSError:
        return json_error(HTTPStatus.NOT_FOUND, "File not found")
    mime, _ = mimetypes.guess_type(path.name)
    content_type = mime or "application/octet-stream"
    if content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
        content_type += "; charset=utf-8"
    return Response(content, status, content_type)


def serve_static(path: str) -> Response:
    relative = path.lstrip("/") or "index.html"
    candidate = (PUBLIC_DIR / relative).resolve()
    try:
        candidate.relative_to(PUBLIC_DIR.resolve())
    except ValueError:
        return json_error(HTTPStatus.FORBIDDEN, "Forbidden")
    if candidate.is_dir():
        candidate = candidate / "index.html"
    if not candidate.exists() or not candidate.is_file():
        return file_response(PUBLIC_DIR / "404.html", HTTPStatus.NOT_FOUND)
    return file_response(candidate)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def clean_expired_sessions(conn: sqlite3.Connection) -> None:
    conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (int(time.time()),))


def is_admin(request: Request) -> bool:
    token = request.cookie("vertusma_session")
    if not token:
        return False
    with db_connection() as conn:
        clean_expired_sessions(conn)
        row = conn.execute(
            "SELECT expires_at FROM sessions WHERE token_hash = ?",
            (hash_token(token),),
        ).fetchone()
    return bool(row and row["expires_at"] > int(time.time()))


def require_admin(request: Request) -> Response | None:
    return None if is_admin(request) else json_error(HTTPStatus.UNAUTHORIZED, "Admin authentication required")


def cookie_header(token: str, max_age: int) -> str:
    secure = "; Secure" if COOKIE_SECURE else ""
    return f"vertusma_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}{secure}"


def query_properties(request: Request, admin: bool = False) -> Response:
    clauses: list[str] = []
    if not admin:
        clauses.append("published = 1")
    params: list[Any] = []
    property_type = request.query_value("type").strip()
    featured = request.query_value("featured").strip().lower()
    search = request.query_value("q").strip()
    if property_type and property_type != "All":
        clauses.append("property_type = ?")
        params.append(property_type)
    if featured in {"1", "true", "yes"}:
        clauses.append("featured = 1")
    if search:
        clauses.append("(title LIKE ? OR city LIKE ? OR state LIKE ? OR property_type LIKE ?)")
        term = f"%{search}%"
        params.extend([term, term, term, term])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with db_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM properties {where} ORDER BY featured DESC, updated_at DESC, id DESC",
            params,
        ).fetchall()
    return json_response({"properties": [row_to_dict(row) for row in rows], "count": len(rows), "admin": admin})


def query_hero_slides(admin: bool = False) -> Response:
    with db_connection() as conn:
        if admin:
            rows = conn.execute("SELECT * FROM hero_slides ORDER BY sort_order ASC, id ASC").fetchall()
        else:
            rows = conn.execute("SELECT * FROM hero_slides WHERE active = 1 ORDER BY sort_order ASC, id ASC").fetchall()
    return json_response({"slides": [row_to_dict(row) for row in rows], "count": len(rows)})


def normalize_hero_payload(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, str]]:
    fields = {
        "eyebrow": str(payload.get("eyebrow", "")).strip(),
        "title": str(payload.get("title", "")).strip(),
        "highlight": str(payload.get("highlight", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "image_url": str(payload.get("image_url", "")).strip(),
        "primary_label": str(payload.get("primary_label", "Explore Our Portfolio")).strip(),
        "primary_url": str(payload.get("primary_url", "/portfolio")).strip(),
        "secondary_label": str(payload.get("secondary_label", "Partner With Vertusma")).strip(),
        "secondary_url": str(payload.get("secondary_url", "/contact")).strip(),
    }
    errors: dict[str, str] = {}
    if len(fields["title"]) < 3:
        errors["title"] = "Title must be at least 3 characters."
    if len(fields["description"]) < 20:
        errors["description"] = "Description must be at least 20 characters."
    if not (fields["image_url"].startswith("/") or re.match(r"^https?://", fields["image_url"], re.I)):
        errors["image_url"] = "Use an uploaded image path or a complete http(s) image URL."
    for key in ("primary_url", "secondary_url"):
        value = fields[key]
        if value and not (value.startswith("/") or re.match(r"^https?://", value, re.I)):
            errors[key] = "Use a site path beginning with / or a complete URL."
    try:
        sort_order = int(payload.get("sort_order", 0) or 0)
    except (TypeError, ValueError):
        sort_order = 0
        errors["sort_order"] = "Sort order must be a whole number."
    active = 1 if bool(payload.get("active", True)) else 0
    if errors:
        return None, errors
    fields.update({"sort_order": sort_order, "active": active})
    return fields, errors


def normalize_property_payload(
    payload: dict[str, Any], current_id: int | None = None
) -> tuple[dict[str, Any] | None, dict[str, str]]:
    fields = {
        "title": str(payload.get("title", "")).strip(),
        "property_type": str(payload.get("property_type", "")).strip(),
        "city": str(payload.get("city", "")).strip(),
        "state": str(payload.get("state", "")).strip().upper(),
        "status": str(payload.get("status", "")).strip(),
        "address": str(payload.get("address", "")).strip(),
        "short_description": str(payload.get("short_description", "")).strip(),
        "description": str(payload.get("description", "")).strip(),
        "image_url": str(payload.get("image_url", "")).strip(),
        "price": str(payload.get("price", "")).strip(),
        "seo_title": str(payload.get("seo_title", "")).strip(),
        "seo_description": str(payload.get("seo_description", "")).strip(),
    }
    errors: dict[str, str] = {}
    if len(fields["title"]) < 3:
        errors["title"] = "Title must be at least 3 characters."
    if len(fields["property_type"]) < 2:
        errors["property_type"] = "Property type is required."
    if len(fields["city"]) < 2:
        errors["city"] = "City is required."
    if not re.fullmatch(r"[A-Z]{2}", fields["state"]):
        errors["state"] = "Use a two-letter state code."
    if len(fields["status"]) < 2:
        errors["status"] = "Portfolio status is required."
    if len(fields["short_description"]) < 15:
        errors["short_description"] = "Add a concise portfolio description."
    if len(fields["description"]) < 30:
        errors["description"] = "Add a detailed property description."
    try:
        units = max(0, int(payload.get("units", 0) or 0))
        square_feet = max(0, int(payload.get("square_feet", 0) or 0))
    except (TypeError, ValueError):
        errors["metrics"] = "Units and square feet must be whole numbers."
        units, square_feet = 0, 0
    featured = 1 if bool(payload.get("featured")) else 0
    published = 1 if bool(payload.get("published", True)) else 0
    requested_slug = slugify(str(payload.get("slug", "")) or fields["title"])
    if errors:
        return None, errors
    with db_connection() as conn:
        if current_id is None:
            row = conn.execute("SELECT id FROM properties WHERE slug = ?", (requested_slug,)).fetchone()
        else:
            row = conn.execute(
                "SELECT id FROM properties WHERE slug = ? AND id != ?", (requested_slug, current_id)
            ).fetchone()
    if row:
        requested_slug = f"{requested_slug}-{secrets.token_hex(2)}"
    fields.update(
        {"slug": requested_slug, "units": units, "square_feet": square_feet, "featured": featured, "published": published}
    )
    return fields, errors


def handle_request(request: Request) -> Response:
    method = request.method
    path = request.path.rstrip("/") or "/"

    if method == "OPTIONS":
        return Response(
            b"",
            HTTPStatus.NO_CONTENT,
            "text/plain; charset=utf-8",
            [("Allow", "GET, POST, PUT, PATCH, DELETE, OPTIONS")],
        )

    # Public pages and static files.
    if method == "GET" and path in {"/", "/about", "/services", "/portfolio", "/contact"}:
        return file_response(PUBLIC_DIR / "index.html")
    if method == "GET" and (path == "/property" or path.startswith("/property/")):
        return file_response(PUBLIC_DIR / "property.html")
    if method == "GET" and path == "/admin":
        return file_response(PUBLIC_DIR / "admin.html")
    if method == "GET" and (path == "/page" or path.startswith("/page/")):
        return file_response(PUBLIC_DIR / "page.html")

    # Public API.
    if method == "GET" and path == "/api/health":
        return json_response({"ok": True, "service": "Vertusma Property Management", "runtime": "WSGI"})
    if method == "GET" and path == "/api/site-config":
        return json_response({"config": get_site_config(), "custom_sections": query_custom_sections(), "pages": query_pages()})
    if method == "GET" and path.startswith("/api/pages/"):
        slug = urllib.parse.unquote(path.rsplit("/", 1)[-1])
        with db_connection() as conn:
            row = conn.execute("SELECT * FROM pages WHERE slug = ? AND published = 1", (slug,)).fetchone()
        return json_response({"page": row_to_dict(row), "config": get_site_config()}) if row else json_error(HTTPStatus.NOT_FOUND, "Page not found")
    if method == "GET" and path == "/api/hero-slides":
        return query_hero_slides()
    if method == "GET" and path == "/api/properties":
        return query_properties(request)
    if method == "GET" and path.startswith("/api/properties/"):
        identifier = urllib.parse.unquote(path.rsplit("/", 1)[-1])
        with db_connection() as conn:
            if identifier.isdigit():
                row = conn.execute("SELECT * FROM properties WHERE id = ? AND published = 1", (int(identifier),)).fetchone()
            else:
                row = conn.execute("SELECT * FROM properties WHERE slug = ? AND published = 1", (identifier,)).fetchone()
        return json_response({"property": row_to_dict(row)}) if row else json_error(HTTPStatus.NOT_FOUND, "Property not found")

    if method == "POST" and path == "/api/inquiries":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        name = str(payload.get("name", "")).strip()
        email = str(payload.get("email", "")).strip().lower()
        phone = str(payload.get("phone", "")).strip()
        company = str(payload.get("company", "")).strip()
        interest = str(payload.get("interest", "")).strip()
        message = str(payload.get("message", "")).strip()
        errors: dict[str, str] = {}
        if len(name) < 2:
            errors["name"] = "Please enter your name."
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
            errors["email"] = "Please enter a valid email address."
        if len(interest) < 2:
            errors["interest"] = "Please select an area of interest."
        if len(message) < 10:
            errors["message"] = "Please provide at least 10 characters."
        if errors:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Please correct the highlighted fields.", errors)
        with db_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO inquiries (name, email, phone, company, interest, message, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, 'New', ?)
                """,
                (name[:120], email[:180], phone[:50], company[:180], interest[:100], message[:4000], utc_now()),
            )
        return json_response(
            {"message": get_site_config().get("contact", {}).get("success_message", "Thank you. A Vertusma team member will contact you shortly."), "inquiry_id": cursor.lastrowid},
            HTTPStatus.CREATED,
        )

    # Authentication.
    if method == "POST" and path == "/api/admin/login":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        email = str(payload.get("email", "")).strip().lower()
        password = str(payload.get("password", ""))
        if not (hmac.compare_digest(email, ADMIN_EMAIL) and hmac.compare_digest(password, ADMIN_PASSWORD)):
            time.sleep(0.2)
            return json_error(HTTPStatus.UNAUTHORIZED, "Invalid email or password")
        token = secrets.token_urlsafe(32)
        now = int(time.time())
        with db_connection() as conn:
            clean_expired_sessions(conn)
            conn.execute(
                "INSERT INTO sessions (token_hash, created_at, expires_at) VALUES (?, ?, ?)",
                (hash_token(token), now, now + SESSION_MAX_AGE),
            )
        return json_response(
            {"authenticated": True, "email": ADMIN_EMAIL},
            headers=[("Set-Cookie", cookie_header(token, SESSION_MAX_AGE))],
        )

    if method == "POST" and path == "/api/admin/logout":
        token = request.cookie("vertusma_session")
        if token:
            with db_connection() as conn:
                conn.execute("DELETE FROM sessions WHERE token_hash = ?", (hash_token(token),))
        return json_response(
            {"authenticated": False},
            headers=[("Set-Cookie", cookie_header("", 0))],
        )

    if method == "GET" and path == "/api/admin/session":
        authenticated = is_admin(request)
        return json_response({"authenticated": authenticated, "email": ADMIN_EMAIL if authenticated else None})

    # Protected admin API.
    if path.startswith("/api/admin/"):
        auth_error = require_admin(request)
        if auth_error:
            return auth_error

    if method == "GET" and path == "/api/admin/site-config":
        return json_response({"config": get_site_config()})

    if method == "PUT" and path == "/api/admin/site-config":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        config = payload.get("config", payload)
        if not isinstance(config, dict):
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Config must be an object")
        return json_response({"config": save_site_config(config), "saved": True})

    if method == "POST" and path == "/api/admin/upload":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        data_url = str(payload.get("data_url", ""))
        match = re.fullmatch(r"data:(image/(?:jpeg|png|webp|gif));base64,([A-Za-z0-9+/=\s]+)", data_url)
        if not match:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Upload a JPG, PNG, WEBP, or GIF image.")
        try:
            raw = base64.b64decode(match.group(2), validate=True)
        except Exception:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid image data.")
        if not raw or len(raw) > MAX_UPLOAD_BYTES:
            return json_error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Image must be smaller than 6 MB.")
        ext = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp", "image/gif": ".gif"}[match.group(1)]
        filename = f"{int(time.time())}-{secrets.token_hex(8)}{ext}"
        UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        (UPLOAD_DIR / filename).write_bytes(raw)
        return json_response({"url": f"/uploads/{filename}"}, HTTPStatus.CREATED)

    if method == "GET" and path == "/api/admin/custom-sections":
        return json_response({"sections": query_custom_sections(admin=True)})

    if method == "POST" and path == "/api/admin/custom-sections":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        title = str(payload.get("title", "")).strip()
        anchor = slugify(str(payload.get("anchor", "")) or title)
        if len(title) < 2:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Section title is required")
        theme = str(payload.get("theme", "ivory")).strip()
        if theme not in {"white", "ivory", "navy", "executive"}: theme = "ivory"
        now = utc_now()
        with db_connection() as conn:
            if conn.execute("SELECT id FROM custom_sections WHERE anchor = ?", (anchor,)).fetchone():
                anchor = f"{anchor}-{secrets.token_hex(2)}"
            cur = conn.execute("INSERT INTO custom_sections (anchor, eyebrow, title, body, image_url, button_label, button_url, theme, sort_order, active, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (anchor, str(payload.get("eyebrow", "")).strip(), title, str(payload.get("body", "")).strip(), str(payload.get("image_url", "")).strip(), str(payload.get("button_label", "")).strip(), str(payload.get("button_url", "")).strip(), theme, int(payload.get("sort_order", 100) or 100), 1 if bool(payload.get("active", True)) else 0, now, now))
            row = conn.execute("SELECT * FROM custom_sections WHERE id = ?", (cur.lastrowid,)).fetchone()
        return json_response({"section": row_to_dict(row)}, HTTPStatus.CREATED)

    custom_match = re.fullmatch(r"/api/admin/custom-sections/(\d+)", path)
    if custom_match and method in {"PUT", "DELETE"}:
        section_id = int(custom_match.group(1))
        if method == "DELETE":
            with db_connection() as conn:
                cur = conn.execute("DELETE FROM custom_sections WHERE id = ?", (section_id,))
            return json_response({"deleted": True}) if cur.rowcount else json_error(HTTPStatus.NOT_FOUND, "Section not found")
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        title = str(payload.get("title", "")).strip()
        if len(title) < 2:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Section title is required")
        anchor = slugify(str(payload.get("anchor", "")) or title)
        theme = str(payload.get("theme", "ivory")).strip()
        if theme not in {"white", "ivory", "navy", "executive"}: theme = "ivory"
        with db_connection() as conn:
            duplicate = conn.execute("SELECT id FROM custom_sections WHERE anchor = ? AND id != ?", (anchor, section_id)).fetchone()
            if duplicate: anchor = f"{anchor}-{secrets.token_hex(2)}"
            cur = conn.execute("UPDATE custom_sections SET anchor=?, eyebrow=?, title=?, body=?, image_url=?, button_label=?, button_url=?, theme=?, sort_order=?, active=?, updated_at=? WHERE id=?",
                (anchor, str(payload.get("eyebrow", "")).strip(), title, str(payload.get("body", "")).strip(), str(payload.get("image_url", "")).strip(), str(payload.get("button_label", "")).strip(), str(payload.get("button_url", "")).strip(), theme, int(payload.get("sort_order", 100) or 100), 1 if bool(payload.get("active", True)) else 0, utc_now(), section_id))
            row = conn.execute("SELECT * FROM custom_sections WHERE id = ?", (section_id,)).fetchone()
        return json_response({"section": row_to_dict(row)}) if cur.rowcount and row else json_error(HTTPStatus.NOT_FOUND, "Section not found")

    if method == "GET" and path == "/api/admin/pages":
        return json_response({"pages": query_pages(admin=True)})

    if method == "POST" and path == "/api/admin/pages":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        title = str(payload.get("title", "")).strip()
        if len(title) < 2:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Page title is required")
        slug = slugify(str(payload.get("slug", "")) or title)
        now = utc_now()
        with db_connection() as conn:
            if conn.execute("SELECT id FROM pages WHERE slug = ?", (slug,)).fetchone(): slug = f"{slug}-{secrets.token_hex(2)}"
            cur = conn.execute("INSERT INTO pages (title, slug, eyebrow, intro, body, image_url, button_label, button_url, seo_title, seo_description, published, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (title, slug, str(payload.get("eyebrow", "")).strip(), str(payload.get("intro", "")).strip(), str(payload.get("body", "")).strip(), str(payload.get("image_url", "")).strip(), str(payload.get("button_label", "")).strip(), str(payload.get("button_url", "")).strip(), str(payload.get("seo_title", "")).strip(), str(payload.get("seo_description", "")).strip(), 1 if bool(payload.get("published", True)) else 0, now, now))
            row = conn.execute("SELECT * FROM pages WHERE id = ?", (cur.lastrowid,)).fetchone()
        return json_response({"page": row_to_dict(row)}, HTTPStatus.CREATED)

    page_match = re.fullmatch(r"/api/admin/pages/(\d+)", path)
    if page_match and method in {"PUT", "DELETE"}:
        page_id = int(page_match.group(1))
        if method == "DELETE":
            with db_connection() as conn:
                cur = conn.execute("DELETE FROM pages WHERE id = ?", (page_id,))
            return json_response({"deleted": True}) if cur.rowcount else json_error(HTTPStatus.NOT_FOUND, "Page not found")
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        title = str(payload.get("title", "")).strip()
        if len(title) < 2:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Page title is required")
        slug = slugify(str(payload.get("slug", "")) or title)
        with db_connection() as conn:
            duplicate = conn.execute("SELECT id FROM pages WHERE slug = ? AND id != ?", (slug, page_id)).fetchone()
            if duplicate: slug = f"{slug}-{secrets.token_hex(2)}"
            cur = conn.execute("UPDATE pages SET title=?, slug=?, eyebrow=?, intro=?, body=?, image_url=?, button_label=?, button_url=?, seo_title=?, seo_description=?, published=?, updated_at=? WHERE id=?",
                (title, slug, str(payload.get("eyebrow", "")).strip(), str(payload.get("intro", "")).strip(), str(payload.get("body", "")).strip(), str(payload.get("image_url", "")).strip(), str(payload.get("button_label", "")).strip(), str(payload.get("button_url", "")).strip(), str(payload.get("seo_title", "")).strip(), str(payload.get("seo_description", "")).strip(), 1 if bool(payload.get("published", True)) else 0, utc_now(), page_id))
            row = conn.execute("SELECT * FROM pages WHERE id = ?", (page_id,)).fetchone()
        return json_response({"page": row_to_dict(row)}) if cur.rowcount and row else json_error(HTTPStatus.NOT_FOUND, "Page not found")

    if method == "GET" and path == "/api/admin/hero-slides":
        return query_hero_slides(admin=True)

    if method == "POST" and path == "/api/admin/hero-slides":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        data, errors = normalize_hero_payload(payload)
        if errors or data is None:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Please correct the hero slide fields.", errors)
        now = utc_now()
        with db_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO hero_slides (eyebrow, title, highlight, description, image_url, primary_label, primary_url, secondary_label, secondary_url, sort_order, active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (data["eyebrow"], data["title"], data["highlight"], data["description"], data["image_url"], data["primary_label"], data["primary_url"], data["secondary_label"], data["secondary_url"], data["sort_order"], data["active"], now, now),
            )
            row = conn.execute("SELECT * FROM hero_slides WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return json_response({"slide": row_to_dict(row)}, HTTPStatus.CREATED)

    hero_admin_match = re.fullmatch(r"/api/admin/hero-slides/(\d+)", path)
    if hero_admin_match and method in {"PUT", "DELETE"}:
        slide_id = int(hero_admin_match.group(1))
        if method == "DELETE":
            with db_connection() as conn:
                cursor = conn.execute("DELETE FROM hero_slides WHERE id = ?", (slide_id,))
            return json_response({"deleted": True}) if cursor.rowcount else json_error(HTTPStatus.NOT_FOUND, "Hero slide not found")
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        data, errors = normalize_hero_payload(payload)
        if errors or data is None:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Please correct the hero slide fields.", errors)
        with db_connection() as conn:
            existing = conn.execute("SELECT id FROM hero_slides WHERE id = ?", (slide_id,)).fetchone()
            if not existing:
                return json_error(HTTPStatus.NOT_FOUND, "Hero slide not found")
            conn.execute(
                """UPDATE hero_slides SET eyebrow=?, title=?, highlight=?, description=?, image_url=?, primary_label=?, primary_url=?, secondary_label=?, secondary_url=?, sort_order=?, active=?, updated_at=? WHERE id=?""",
                (data["eyebrow"], data["title"], data["highlight"], data["description"], data["image_url"], data["primary_label"], data["primary_url"], data["secondary_label"], data["secondary_url"], data["sort_order"], data["active"], utc_now(), slide_id),
            )
            row = conn.execute("SELECT * FROM hero_slides WHERE id = ?", (slide_id,)).fetchone()
        return json_response({"slide": row_to_dict(row)})

    if method == "GET" and path == "/api/admin/properties":
        return query_properties(request, admin=True)

    if method == "POST" and path == "/api/admin/properties":
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        data, errors = normalize_property_payload(payload)
        if errors or data is None:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Please correct the property fields.", errors)
        now = utc_now()
        with db_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO properties (
                    title, slug, property_type, city, state, status, address,
                    short_description, description, image_url, units, square_feet, price,
                    featured, published, seo_title, seo_description, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data["title"], data["slug"], data["property_type"], data["city"], data["state"],
                    data["status"], data["address"], data["short_description"], data["description"],
                    data["image_url"], data["units"], data["square_feet"], data["price"], data["featured"], data["published"],
                    data["seo_title"], data["seo_description"], now, now,
                ),
            )
            row = conn.execute("SELECT * FROM properties WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return json_response({"property": row_to_dict(row)}, HTTPStatus.CREATED)

    property_admin_match = re.fullmatch(r"/api/admin/properties/(\d+)", path)
    if property_admin_match and method in {"PUT", "DELETE"}:
        property_id = int(property_admin_match.group(1))
        if method == "DELETE":
            with db_connection() as conn:
                cursor = conn.execute("DELETE FROM properties WHERE id = ?", (property_id,))
            return json_response({"deleted": True}) if cursor.rowcount else json_error(HTTPStatus.NOT_FOUND, "Property not found")
        with db_connection() as conn:
            existing = conn.execute("SELECT id FROM properties WHERE id = ?", (property_id,)).fetchone()
        if not existing:
            return json_error(HTTPStatus.NOT_FOUND, "Property not found")
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        data, errors = normalize_property_payload(payload, current_id=property_id)
        if errors or data is None:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Please correct the property fields.", errors)
        with db_connection() as conn:
            conn.execute(
                """
                UPDATE properties SET
                    title=?, slug=?, property_type=?, city=?, state=?, status=?, address=?,
                    short_description=?, description=?, image_url=?, units=?, square_feet=?, price=?,
                    featured=?, published=?, seo_title=?, seo_description=?, updated_at=? WHERE id=?
                """,
                (
                    data["title"], data["slug"], data["property_type"], data["city"], data["state"],
                    data["status"], data["address"], data["short_description"], data["description"],
                    data["image_url"], data["units"], data["square_feet"], data["price"], data["featured"], data["published"],
                    data["seo_title"], data["seo_description"], utc_now(), property_id,
                ),
            )
            row = conn.execute("SELECT * FROM properties WHERE id = ?", (property_id,)).fetchone()
        return json_response({"property": row_to_dict(row)})

    if method == "GET" and path == "/api/admin/inquiries":
        status = request.query_value("status").strip()
        params: list[Any] = []
        where = ""
        if status and status != "All":
            where = "WHERE status = ?"
            params.append(status)
        with db_connection() as conn:
            rows = conn.execute(
                f"SELECT * FROM inquiries {where} ORDER BY created_at DESC, id DESC", params
            ).fetchall()
        return json_response({"inquiries": [row_to_dict(row) for row in rows], "count": len(rows)})

    inquiry_admin_match = re.fullmatch(r"/api/admin/inquiries/(\d+)", path)
    if inquiry_admin_match and method in {"PATCH", "DELETE"}:
        inquiry_id = int(inquiry_admin_match.group(1))
        if method == "DELETE":
            with db_connection() as conn:
                cursor = conn.execute("DELETE FROM inquiries WHERE id = ?", (inquiry_id,))
            return json_response({"deleted": True}) if cursor.rowcount else json_error(HTTPStatus.NOT_FOUND, "Inquiry not found")
        payload = request.json()
        if payload is None:
            return json_error(HTTPStatus.BAD_REQUEST, "Invalid JSON body")
        status = str(payload.get("status", "")).strip()
        if status not in INQUIRY_STATUSES:
            return json_error(HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid inquiry status")
        with db_connection() as conn:
            cursor = conn.execute("UPDATE inquiries SET status = ? WHERE id = ?", (status, inquiry_id))
            row = conn.execute("SELECT * FROM inquiries WHERE id = ?", (inquiry_id,)).fetchone()
        if cursor.rowcount == 0 or not row:
            return json_error(HTTPStatus.NOT_FOUND, "Inquiry not found")
        return json_response({"inquiry": row_to_dict(row)})

    if path.startswith("/api/"):
        return json_error(HTTPStatus.NOT_FOUND, "Endpoint not found")
    if method == "GET":
        return serve_static(path)
    return json_error(HTTPStatus.NOT_FOUND, "Endpoint not found")


def application(environ: dict[str, Any], start_response: StartResponse) -> Iterable[bytes]:
    """WSGI callable imported by Passenger."""
    try:
        response = handle_request(Request(environ))
    except Exception:
        # Do not expose server internals to the browser. Passenger/cPanel logs
        # retain the traceback for diagnosis.
        import traceback

        traceback.print_exc()
        response = json_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
    return response.wsgi(start_response)


# Create and seed the database when Passenger imports the application.
init_database()


if __name__ == "__main__":
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    print(f"Vertusma website running at http://{host}:{port}")
    print(f"Admin dashboard: http://{host}:{port}/admin")
    print("Press Ctrl+C to stop.")
    with make_server(host, port, application) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down...")
