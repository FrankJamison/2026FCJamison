import csv
import os
import secrets
import smtplib
import ssl
from io import StringIO
from io import BytesIO
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Tuple
from urllib.parse import urljoin
from zipfile import ZIP_DEFLATED, ZipFile

from flask import Response, abort, jsonify, redirect, render_template, request, url_for

from __init__ import app


PROJECT_HOSTED = {
    "2026SpacePortfolio": "https://spaceportfolio.fcjamison.com/",
    "2026HackerNews": "https://hackernews.fcjamison.com/",
    "2025PasswordCheck": "https://passwordcheck.fcjamison.com/",
    "2020CharacterVault": "https://charactervault.fcjamison.com/",
    "2018Questkeeper": "https://questkeeper.fcjamison.com/",
    "2018FrankJamison": "https://frankjamison2018.fcjamison.com/",
    "2018FranksClassicCars": "https://classiccars.fcjamison.com/",
    "2007GlobeBank": "https://globebank.fcjamison.com/",
}

PORTFOLIO_METADATA = {
    "2026SpacePortfolio": {
        "title": "Space Portfolio | Full-Stack Flask App",
        "description": "Full-stack Flask web application with space-themed design, Jinja2 templating, Bootstrap layout, and contact system demonstrating production-ready development practices.",
    },
    "2026HackerNews": {
        "title": "Hacker News Aggregator | Tech News Tool",
        "description": "Automated technical news aggregation and curation platform. Reduce research time with centralized, curated content from Hacker News.",
    },
    "2025JamisonStamps": {
        "title": "JamisonStamps.com | E-Commerce Platform",
        "description": "End-to-end e-commerce storefront with catalog management, checkout flow, and PayPal payment integration for collectibles sales.",
    },
    "2025PasswordCheck": {
        "title": "Password Exposure Checker | Security Tool",
        "description": "Privacy-first breach detection using k-anonymity hashing. Check if passwords appear in data breaches without exposing credentials.",
    },
    "2025FrankJamison": {
        "title": "FrankJamison.com 2025 | Portfolio Site",
        "description": "2025 iteration of professional portfolio site showcasing full-stack development projects, technical writing, and web accessibility best practices.",
    },
    "2024PassionateTeachingJourney": {
        "title": "Passionate Teaching Journey | Education Blog",
        "description": "Custom WordPress content platform for education publishing. Improved article discoverability with optimized navigation and topic-based organization.",
    },
    "2021DnD5eTools": {
        "title": "DnD5eTools | D&D Companion Utility",
        "description": "Lightweight browser toolkit for Dungeons & Dragons 5th Edition. Generators, utilities, and reference tools for tabletop gaming sessions.",
    },
    "2020AncientWhiteArmyVetNode": {
        "title": "AncientWhiteArmyVet.com | Node RPG Tools",
        "description": "Node.js-based RPG utility platform with role-playing game generators, stat rollers, and character creation tools for tabletop gaming.",
    },
    "2020CharacterVault": {
        "title": "Character Vault | RPG Character Manager",
        "description": "Full-stack application for creating, storing, and managing tabletop RPG character sheets. Interactive character database with web interface.",
    },
    "2020AngularCLI": {
        "title": "Angular CLI Application | Frontend Framework",
        "description": "Full-featured Angular CLI project demonstrating component architecture, dependency injection, reactive programming, and modern web development practices.",
    },
    "2020BudgetApplication": {
        "title": "Budget Application | Financial Tracker",
        "description": "Personal finance management tool with income/expense tracking, budget planning, and financial reporting capabilities for better money management.",
    },
    "2020PigGame": {
        "title": "The Pig Game | JavaScript Game",
        "description": "Turn-based dice game built with vanilla JavaScript. Learn dice game logic, score tracking, and interactive game state management.",
    },
    "2020AncientWhiteArmyVet": {
        "title": "AncientWhiteArmyVet RPG Tools | Game Utilities",
        "description": "Tabletop RPG utility suite with dice rollers, stat generators, and character creation tools for role-playing game sessions.",
    },
    "2019FrankJamison": {
        "title": "FrankJamison.com 2019 | Portfolio Site",
        "description": "2019 portfolio iteration featuring web development projects, case studies, and professional accomplishments in full-stack web development.",
    },
    "2019VeteranJobInfo": {
        "title": "VeteranJobInfo.us | Veteran Employment Resource",
        "description": "Job information and employment resource platform for veterans. Information architecture and content organization for veteran job seekers.",
    },
    "2019AncientWhiteArmyVet": {
        "title": "AncientWhiteArmyVet RPG Tools 2019 | Utilities",
        "description": "2019 version of tabletop RPG utility tools with dice rollers, generators, and reference utilities for gaming sessions.",
    },
    "2018Questkeeper": {
        "title": "QuestKeeper | D&D Campaign Manager",
        "description": "Campaign management tool for Dungeons & Dragons game masters. Character sheets, quest tracking, and session organization.",
    },
    "2018FrankJamison": {
        "title": "FrankJamison.com 2018 | Portfolio Site",
        "description": "2018 portfolio website showcasing web development projects and professional experience in full-stack and frontend development.",
    },
    "2018FranksClassicCars": {
        "title": "Frank's Classic Cars | Vehicle Showcase Site",
        "description": "Classic automobile showcase and sales website with vehicle catalog, detailed listings, and contact management for classic car collector.",
    },
    "2017RPGStatRoller": {
        "title": "RPG Stat Roller | Character Creator",
        "description": "Interactive tool for rolling and generating RPG character statistics. Quick character generation with randomized stat distribution.",
    },
    "2017RiversideMassageAndSpa": {
        "title": "Riverside Massage & Spa | Service Website",
        "description": "Local business website for massage therapy and spa services. Service listings, pricing, appointments, and contact information.",
    },
    "2017StopwatchApplication": {
        "title": "Stopwatch & Countdown Timer | Time Tool",
        "description": "Browser-based stopwatch and countdown timer application. Functional time tracking utility built with HTML, CSS, and JavaScript.",
    },
    "2017JavaScriptGuessingGame": {
        "title": "JavaScript Guessing Game | Interactive Game",
        "description": "Number guessing game built with vanilla JavaScript. Learn game logic, random number generation, and user interaction handling.",
    },
    "2017FrankJamison": {
        "title": "FrankJamison.com 2017 | Portfolio Site",
        "description": "2017 portfolio website featuring web development projects and professional work in responsive design and frontend development.",
    },
    "2016FrankJamison": {
        "title": "FrankJamison.com 2016 | Portfolio Site",
        "description": "2016 portfolio iteration showcasing web design and development projects with responsive layouts and user interface work.",
    },
    "2016VirtualWorld": {
        "title": "Virtual World | Interactive Environment",
        "description": "Interactive web-based virtual world or 3D environment. Explores web graphics, interactive visualization, and immersive user experiences.",
    },
    "2015JamisonWebDesign": {
        "title": "Jamison Web Design | Web Design Agency",
        "description": "Web design agency portfolio and service site. Showcases design work, services offered, and client projects from web design practice.",
    },
    "2015MiFamiliaTacoCatering": {
        "title": "Mi Familia Taco Catering | Catering Service",
        "description": "Mexican catering service website with menu items, pricing, event booking, and contact information for local food service business.",
    },
    "2015RPGBooksProject": {
        "title": "The RPG Book Library | Reference Database",
        "description": "Digital library and database for tabletop RPG rulebooks and references. Catalog organization and book information management system.",
    },
    "2015FrankJamison": {
        "title": "FrankJamison.com 2015 | Portfolio Site",
        "description": "2015 portfolio website featuring web development and design projects with artistic direction and professional presentation.",
    },
}

ANALYTICS_HEADERS = [
    "server_timestamp",
    "client_timestamp",
    "event",
    "event_category",
    "event_label",
    "page_path",
    "link_url",
    "section_id",
    "scroll_percent",
    "user_agent",
    "referrer",
    "ip",
]

ALLOWED_ANALYTICS_EVENTS = {
    "hero_cta_click",
    "featured_project_click",
    "contact_quick_action_click",
    "contact_submit_attempt",
    "contact_submit_success",
    "contact_submit_error",
    "section_visible",
    "scroll_depth_milestone",
}

KNOWN_BOT_UA_TOKENS = {
    "bot",
    "crawler",
    "spider",
    "headless",
    "lighthouse",
    "pagespeed",
    "wget",
    "curl",
    "python-requests",
    "python-urllib",
    "httpclient",
    "scrapy",
}


def _get_local_portfolio_slugs() -> list[str]:
    static_root = Path(app.static_folder or "static")
    portfolio_root = static_root / "portfolio"
    if not portfolio_root.exists() or not portfolio_root.is_dir():
        return []

    slugs: list[str] = []
    for child in portfolio_root.iterdir():
        if not child.is_dir():
            continue
        if (child / "index.html").exists():
            slugs.append(child.name)
    return sorted(set(slugs))


def _site_url_root() -> str:
    configured = (os.getenv("SITE_URL") or "").strip()
    if configured:
        return configured.rstrip("/") + "/"
    return request.url_root


def _parse_env_list(name: str) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return []
    parts: list[str] = []
    for line in raw.replace(",", "\n").splitlines():
        item = line.strip()
        if not item:
            continue
        parts.append(item)
    return parts


def _truthy_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _clean(value: Optional[str], *, max_len: int = 5000) -> str:
    if value is None:
        return ""
    value = str(value).strip()
    if len(value) > max_len:
        value = value[:max_len]
    return value


def _append_csv(path: Path, headers: list[str], row: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = path.exists()

    with path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        if not file_exists:
            writer.writeheader()
        writer.writerow({h: row.get(h, "") for h in headers})


def _analytics_events_path() -> Path:
    configured = _clean(os.getenv("ANALYTICS_EVENTS_PATH"), max_len=2000)
    if configured:
        return Path(configured)
    return Path("data/analytics_events.csv")


def _parse_iso_datetime(raw: str) -> Optional[datetime]:
    raw = _clean(raw, max_len=100)
    if not raw:
        return None

    try:
        normalized = raw.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _safe_int(raw: str) -> Optional[int]:
    raw = _clean(raw, max_len=50)
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _safe_int_env(name: str, default: int, *, low: int, high: int) -> int:
    raw = _clean(os.getenv(name), max_len=30)
    parsed = _safe_int(raw)
    if parsed is None:
        return default
    return max(low, min(parsed, high))


def _analytics_retention_days() -> int:
    return _safe_int_env("ANALYTICS_RETENTION_DAYS", 180, low=7, high=3650)


def _analytics_max_rows() -> int:
    return _safe_int_env("ANALYTICS_MAX_ROWS", 200000, low=1000, high=2000000)


def _analytics_prune_interval_seconds() -> int:
    return _safe_int_env("ANALYTICS_PRUNE_MIN_INTERVAL_SEC", 900, low=30, high=86400)


def _analytics_admin_token() -> str:
    return _clean(os.getenv("ANALYTICS_ADMIN_TOKEN"), max_len=200)


def _analytics_admin_enabled() -> bool:
    return bool(_analytics_admin_token())


def _analytics_request_token() -> str:
    query_token = _clean(request.args.get("token"), max_len=200)
    if query_token:
        return query_token
    return _clean(request.headers.get("X-Analytics-Token"), max_len=200)


def _analytics_admin_authorized() -> bool:
    expected = _analytics_admin_token()
    provided = _analytics_request_token()
    if not expected or not provided:
        return False
    return secrets.compare_digest(provided, expected)


def _ua_contains_bot_token(user_agent: str) -> bool:
    user_agent_lower = _clean(user_agent, max_len=600).lower()
    if not user_agent_lower:
        return True
    return any(token in user_agent_lower for token in KNOWN_BOT_UA_TOKENS)


def _is_noise_analytics_event(payload: dict) -> tuple[bool, str]:
    event_name = _clean(payload.get("event"), max_len=120)
    if not event_name:
        return True, "missing_event"

    if event_name not in ALLOWED_ANALYTICS_EVENTS:
        return True, "unknown_event"

    user_agent = _clean(request.headers.get("User-Agent"), max_len=400)
    if _ua_contains_bot_token(user_agent):
        return True, "bot_ua"

    page_path = _clean(payload.get("page_path"), max_len=500)
    if page_path and not page_path.startswith("/"):
        return True, "invalid_page_path"

    if event_name == "scroll_depth_milestone":
        milestone = _safe_int(_clean(str(payload.get("scroll_percent", "")), max_len=10))
        if milestone not in {25, 50, 75, 100}:
            return True, "invalid_scroll_percent"

    return False, ""


def _prune_analytics_events(*, retention_days: int, max_rows: int) -> dict[str, int]:
    path = _analytics_events_path()
    if not path.exists():
        return {
            "before": 0,
            "after": 0,
            "deleted": 0,
        }

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(retention_days, 1))
    kept: list[dict[str, str]] = []
    before_count = 0

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            before_count += 1
            dt = _parse_iso_datetime(_clean(row.get("server_timestamp"), max_len=100))
            if not dt or dt < cutoff:
                continue
            kept.append({h: _clean(row.get(h), max_len=5000) for h in ANALYTICS_HEADERS})

    if max_rows > 0 and len(kept) > max_rows:
        kept = kept[-max_rows:]

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=ANALYTICS_HEADERS)
        writer.writeheader()
        writer.writerows(kept)

    after_count = len(kept)
    return {
        "before": before_count,
        "after": after_count,
        "deleted": max(before_count - after_count, 0),
    }


def _maybe_prune_analytics_events() -> dict[str, int]:
    path = _analytics_events_path()
    if path.exists():
        age_seconds = datetime.now(timezone.utc).timestamp() - path.stat().st_mtime
        if age_seconds < _analytics_prune_interval_seconds():
            return {
                "before": 0,
                "after": 0,
                "deleted": 0,
            }

    return _prune_analytics_events(
        retention_days=_analytics_retention_days(),
        max_rows=_analytics_max_rows(),
    )


def _analytics_daily_series(days: int = 30) -> list[dict[str, int | str]]:
    rows = _collect_recent_analytics(days)
    now_utc = datetime.now(timezone.utc).date()

    buckets: dict[str, dict] = {}
    for offset in range(days - 1, -1, -1):
        key = (now_utc - timedelta(days=offset)).isoformat()
        buckets[key] = {
            "date": key,
            "events": 0,
            "cta_clicks": 0,
            "contact_attempts": 0,
            "contact_successes": 0,
            "engaged_sections": set(),
            "max_scroll": 0,
        }

    for row in rows:
        dt = _parse_iso_datetime(_clean(row.get("server_timestamp"), max_len=100))
        if not dt:
            continue
        date_key = dt.date().isoformat()
        bucket = buckets.get(date_key)
        if not bucket:
            continue

        bucket["events"] += 1
        event_name = _clean(row.get("event"), max_len=120)
        if event_name in {"hero_cta_click", "featured_project_click", "contact_quick_action_click"}:
            bucket["cta_clicks"] += 1
        elif event_name == "contact_submit_attempt":
            bucket["contact_attempts"] += 1
        elif event_name == "contact_submit_success":
            bucket["contact_successes"] += 1
        elif event_name == "section_visible":
            section_id = _clean(row.get("section_id"), max_len=80)
            if section_id:
                bucket["engaged_sections"].add(section_id)

        if event_name == "scroll_depth_milestone":
            milestone = _safe_int(_clean(row.get("scroll_percent"), max_len=10))
            if milestone is not None:
                bucket["max_scroll"] = max(bucket["max_scroll"], milestone)

    peak_events = max((bucket["events"] for bucket in buckets.values()), default=0)
    output: list[dict[str, int | str]] = []
    for bucket in buckets.values():
        events = int(bucket["events"])
        bar_pct = 0
        if peak_events > 0:
            bar_pct = int(round((events / peak_events) * 100))

        output.append(
            {
                "date": str(bucket["date"]),
                "events": events,
                "cta_clicks": int(bucket["cta_clicks"]),
                "contact_attempts": int(bucket["contact_attempts"]),
                "contact_successes": int(bucket["contact_successes"]),
                "engaged_sections": len(bucket["engaged_sections"]),
                "max_scroll": int(bucket["max_scroll"]),
                "bar_pct": bar_pct,
            }
        )

    return output


def _analytics_series_csv(days: int = 30) -> str:
    series = _analytics_daily_series(days)
    buffer = StringIO()
    headers = [
        "date",
        "events",
        "cta_clicks",
        "contact_attempts",
        "contact_successes",
        "engaged_sections",
        "max_scroll",
    ]
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in series:
        writer.writerow({
            "date": row.get("date", ""),
            "events": row.get("events", 0),
            "cta_clicks": row.get("cta_clicks", 0),
            "contact_attempts": row.get("contact_attempts", 0),
            "contact_successes": row.get("contact_successes", 0),
            "engaged_sections": row.get("engaged_sections", 0),
            "max_scroll": row.get("max_scroll", 0),
        })
    return buffer.getvalue()


def _analytics_raw_events_csv(days: int = 30) -> str:
    rows = _collect_recent_analytics(days)
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=ANALYTICS_HEADERS)
    writer.writeheader()
    for row in rows:
        writer.writerow({h: _clean(row.get(h), max_len=5000) for h in ANALYTICS_HEADERS})
    return buffer.getvalue()


def _analytics_bundle_manifest(days: int, *, generated_at: str) -> str:
    lines = [
        "FCJamison Analytics Export Bundle",
        "",
        f"Generated (UTC): {generated_at}",
        f"Window days: {days}",
        "",
        "Included files:",
        f"- analytics-{days}d.csv: Daily aggregate metrics by date.",
        f"- analytics-raw-{days}d.csv: Raw event rows from analytics ingestion.",
        "",
        "Column notes:",
        "- Daily aggregates: date, events, cta_clicks, contact_attempts, contact_successes, engaged_sections, max_scroll",
        "- Raw events: server_timestamp, client_timestamp, event, event_category, event_label, page_path, link_url, section_id, scroll_percent, user_agent, referrer, ip",
    ]
    return "\n".join(lines) + "\n"


def _collect_recent_analytics(days: int = 30) -> list[dict[str, str]]:
    path = _analytics_events_path()
    if not path.exists():
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=max(days, 1))
    rows: list[dict[str, str]] = []

    with path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = _parse_iso_datetime(_clean(row.get("server_timestamp"), max_len=100))
            if not dt or dt < cutoff:
                continue
            rows.append(row)

    return rows


def _analytics_breakdown(days: int = 30) -> dict[str, list[dict[str, int | str]]]:
    rows = _collect_recent_analytics(days)
    action_counts: dict[str, int] = {}
    section_counts: dict[str, int] = {}

    for row in rows:
        event_name = _clean(row.get("event"), max_len=120)
        event_label = _clean(row.get("event_label"), max_len=300)

        if event_name in {
            "hero_cta_click",
            "featured_project_click",
            "contact_quick_action_click",
            "contact_submit_attempt",
            "contact_submit_success",
            "contact_submit_error",
        }:
            key = event_label or event_name
            action_counts[key] = action_counts.get(key, 0) + 1

        if event_name == "section_visible":
            section_id = _clean(row.get("section_id"), max_len=80)
            if section_id:
                section_counts[section_id] = section_counts.get(section_id, 0) + 1

    top_actions = sorted(
        ({"name": name, "count": count} for name, count in action_counts.items()),
        key=lambda item: (-int(item["count"]), str(item["name"])),
    )[:8]

    top_sections = sorted(
        ({"name": name, "count": count} for name, count in section_counts.items()),
        key=lambda item: (-int(item["count"]), str(item["name"])),
    )[:8]

    return {
        "top_actions": top_actions,
        "top_sections": top_sections,
    }


def _analytics_event_mix(days: int = 30) -> list[dict[str, int | float | str]]:
    rows = _collect_recent_analytics(days)
    counts: dict[str, int] = {}

    label_map = {
        "hero_cta_click": "Hero CTA",
        "featured_project_click": "Featured Project Click",
        "contact_quick_action_click": "Contact Quick Action",
        "contact_submit_attempt": "Contact Submit Attempt",
        "contact_submit_success": "Contact Submit Success",
        "contact_submit_error": "Contact Submit Error",
        "section_visible": "Section Visible",
        "scroll_depth_milestone": "Scroll Milestone",
    }

    for row in rows:
        event_name = _clean(row.get("event"), max_len=120)
        if not event_name:
            continue
        counts[event_name] = counts.get(event_name, 0) + 1

    total = sum(counts.values())
    if total <= 0:
        return []

    color_palette = [
        "#e14a73",
        "#f08da8",
        "#ffb26b",
        "#8cc8ff",
        "#7adfb8",
        "#c9a7ff",
        "#ffd86a",
        "#9aa4b2",
    ]

    sorted_counts = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:8]
    mix: list[dict[str, int | float | str]] = []

    for idx, (event_name, count) in enumerate(sorted_counts):
        pct = round((count / total) * 100.0, 1)
        mix.append(
            {
                "event": event_name,
                "label": label_map.get(event_name, event_name.replace("_", " ").title()),
                "count": int(count),
                "percent": pct,
                "color": color_palette[idx % len(color_palette)],
            }
        )

    return mix


def _analytics_kpis(days: int = 30) -> dict:
    rows = _collect_recent_analytics(days)
    counts: dict[str, int] = {}
    unique_sections: set[str] = set()
    max_scroll = 0

    for row in rows:
        event_name = _clean(row.get("event"), max_len=120)
        if event_name:
            counts[event_name] = counts.get(event_name, 0) + 1

        if event_name == "section_visible":
            section_id = _clean(row.get("section_id"), max_len=80)
            if section_id:
                unique_sections.add(section_id)

        if event_name == "scroll_depth_milestone":
            milestone = _safe_int(_clean(row.get("scroll_percent"), max_len=10))
            if milestone is not None:
                max_scroll = max(max_scroll, milestone)

    cta_clicks = (
        counts.get("hero_cta_click", 0)
        + counts.get("featured_project_click", 0)
        + counts.get("contact_quick_action_click", 0)
    )
    contact_attempts = counts.get("contact_submit_attempt", 0)
    contact_successes = counts.get("contact_submit_success", 0)
    success_rate = 0.0
    if contact_attempts > 0:
        success_rate = round((contact_successes / contact_attempts) * 100.0, 1)

    return {
        "window_days": days,
        "events": len(rows),
        "cta_clicks": cta_clicks,
        "contact_attempts": contact_attempts,
        "contact_successes": contact_successes,
        "contact_success_rate": success_rate,
        "engaged_sections": len(unique_sections),
        "max_scroll_milestone": max_scroll,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _analytics_badges(days: int = 30) -> list[dict[str, str]]:
    kpis = _analytics_kpis(days)
    return [
        {
            "key": "cta_clicks",
            "label": f"CTA Clicks ({days}d)",
            "value": str(kpis["cta_clicks"]),
            "hint": "Hero, featured, and contact quick-action clicks",
        },
        {
            "key": "contact_success_rate",
            "label": f"Contact Success Rate ({days}d)",
            "value": f"{kpis['contact_success_rate']:.1f}%",
            "hint": "Successful submissions / contact attempts",
        },
        {
            "key": "engaged_sections",
            "label": f"Section Engagement ({days}d)",
            "value": str(kpis["engaged_sections"]),
            "hint": f"Unique tracked sections viewed, max scroll {kpis['max_scroll_milestone']}%",
        },
    ]


def _request_ip() -> str:
    xff = _clean(request.headers.get("X-Forwarded-For"), max_len=300)
    if xff:
        return xff.split(",", 1)[0].strip()[:100]
    return _clean(request.remote_addr, max_len=100)


def _smtp_context() -> ssl.SSLContext:
    allow_invalid = _truthy_env("SMTP_ALLOW_INVALID_CERT", False)
    ca_file = _clean(os.getenv("SMTP_CA_FILE"), max_len=2000)

    if allow_invalid:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx

    if ca_file:
        return ssl.create_default_context(cafile=ca_file)

    return ssl.create_default_context()


def _send_email(*, subject: str, body: str, reply_to: Optional[str] = None) -> Tuple[bool, str]:
    host = _clean(os.getenv("SMTP_HOST"), max_len=255)
    port_raw = _clean(os.getenv("SMTP_PORT"), max_len=20) or "465"
    user = _clean(os.getenv("SMTP_USER"), max_len=255)
    password = os.getenv("SMTP_PASSWORD") or ""

    from_addr = _clean(os.getenv("SMTP_FROM"), max_len=255) or user
    to_addr = _clean(os.getenv("SMTP_TO"), max_len=255) or user

    use_ssl = _truthy_env("SMTP_USE_SSL", True)
    use_tls = _truthy_env("SMTP_USE_TLS", False)

    if not host or not to_addr or not from_addr:
        return False, "Email is not configured (missing SMTP_HOST/SMTP_FROM/SMTP_TO)."

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    if reply_to:
        msg["Reply-To"] = reply_to
    msg.set_content(body)

    try:
        port = int(port_raw)
    except ValueError:
        return False, "Email is misconfigured (SMTP_PORT must be a number)."

    ctx = _smtp_context()

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=20) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as server:
                server.ehlo()
                if use_tls:
                    server.starttls(context=ctx)
                    server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        return True, ""
    except Exception as e:
        return False, f"Email send failed: {e}"


@app.get("/")
def index():
    return render_template(
        "home/index.html",
        analytics_kpi_badges=_analytics_badges(days=30),
        portfolio_metadata=PORTFOLIO_METADATA,
    )


@app.post("/analytics/event")
def analytics_event():
    payload = request.get_json(silent=True) or {}

    filtered, reason = _is_noise_analytics_event(payload)
    if filtered:
        return jsonify({"ok": True, "skipped": True, "reason": reason}), 202

    event_name = _clean(payload.get("event"), max_len=120)
    if not event_name:
        return jsonify({"ok": False, "error": "Missing event."}), 400

    _maybe_prune_analytics_events()

    row = {
        "server_timestamp": datetime.now(timezone.utc).isoformat(),
        "client_timestamp": _clean(payload.get("client_timestamp"), max_len=100),
        "event": event_name,
        "event_category": _clean(payload.get("event_category"), max_len=120),
        "event_label": _clean(payload.get("event_label"), max_len=300),
        "page_path": _clean(payload.get("page_path"), max_len=500),
        "link_url": _clean(payload.get("link_url"), max_len=2000),
        "section_id": _clean(payload.get("section_id"), max_len=120),
        "scroll_percent": _clean(str(payload.get("scroll_percent", "")), max_len=10),
        "user_agent": _clean(request.headers.get("User-Agent"), max_len=400),
        "referrer": _clean(request.referrer, max_len=2000),
        "ip": _request_ip(),
    }

    _append_csv(_analytics_events_path(), ANALYTICS_HEADERS, row)
    return jsonify({"ok": True})


@app.get("/analytics/summary")
def analytics_summary():
    days_raw = request.args.get("days", "30")
    days = _safe_int(days_raw) or 30
    days = max(1, min(days, 365))
    return jsonify({"ok": True, "summary": _analytics_kpis(days=days)})


@app.get("/analytics/admin")
def analytics_admin():
    if not _analytics_admin_enabled():
        abort(404)

    if not _analytics_admin_authorized():
        return Response("Forbidden", status=403, mimetype="text/plain")

    days = _safe_int(request.args.get("days", "30")) or 30
    days = max(7, min(days, 365))
    summary = _analytics_kpis(days=days)
    series = _analytics_daily_series(days=days)
    breakdown = _analytics_breakdown(days=days)
    event_mix = _analytics_event_mix(days=days)
    has_activity = any(int(row.get("events", 0)) > 0 for row in series)

    return render_template(
        "home/analytics_admin.html",
        analytics_summary=summary,
        analytics_series=series,
        analytics_top_actions=breakdown["top_actions"],
        analytics_top_sections=breakdown["top_sections"],
        analytics_event_mix=event_mix,
        analytics_has_activity=has_activity,
        analytics_days=days,
        analytics_retention_days=_analytics_retention_days(),
        analytics_max_rows=_analytics_max_rows(),
        analytics_token=_analytics_request_token(),
    )


@app.get("/analytics/export.csv")
def analytics_export_csv():
    if not _analytics_admin_enabled():
        abort(404)

    if not _analytics_admin_authorized():
        return Response("Forbidden", status=403, mimetype="text/plain")

    days = _safe_int(request.args.get("days", "30")) or 30
    days = max(7, min(days, 365))
    csv_body = _analytics_series_csv(days=days)
    filename = f"analytics-{days}d.csv"

    return Response(
        csv_body,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/analytics/export-raw.csv")
def analytics_export_raw_csv():
    if not _analytics_admin_enabled():
        abort(404)

    if not _analytics_admin_authorized():
        return Response("Forbidden", status=403, mimetype="text/plain")

    days = _safe_int(request.args.get("days", "30")) or 30
    days = max(7, min(days, 365))
    csv_body = _analytics_raw_events_csv(days=days)
    filename = f"analytics-raw-{days}d.csv"

    return Response(
        csv_body,
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/analytics/export-bundle.zip")
def analytics_export_bundle_zip():
    if not _analytics_admin_enabled():
        abort(404)

    if not _analytics_admin_authorized():
        return Response("Forbidden", status=403, mimetype="text/plain")

    days = _safe_int(request.args.get("days", "30")) or 30
    days = max(7, min(days, 365))
    generated_at = datetime.now(timezone.utc).isoformat()

    aggregate_csv = _analytics_series_csv(days=days)
    raw_csv = _analytics_raw_events_csv(days=days)
    manifest_txt = _analytics_bundle_manifest(days, generated_at=generated_at)

    zip_buffer = BytesIO()
    with ZipFile(zip_buffer, mode="w", compression=ZIP_DEFLATED) as zip_file:
        zip_file.writestr("README.txt", manifest_txt)
        zip_file.writestr(f"analytics-{days}d.csv", aggregate_csv)
        zip_file.writestr(f"analytics-raw-{days}d.csv", raw_csv)

    zip_payload = zip_buffer.getvalue()
    filename = f"analytics-bundle-{days}d.zip"

    return Response(
        zip_payload,
        mimetype="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@app.get("/analytics/prune")
def analytics_prune():
    if not _analytics_admin_enabled():
        abort(404)

    if not _analytics_admin_authorized():
        return jsonify({"ok": False, "error": "Forbidden"}), 403

    result = _prune_analytics_events(
        retention_days=_analytics_retention_days(),
        max_rows=_analytics_max_rows(),
    )
    return jsonify({
        "ok": True,
        "retention_days": _analytics_retention_days(),
        "max_rows": _analytics_max_rows(),
        "result": result,
    })


@app.get("/robots.txt")
def robots_txt():
    site_root = _site_url_root().rstrip("/")
    body = "\n".join(
        [
            "User-agent: *",
            "Disallow:",
            f"Sitemap: {site_root}/sitemap.xml",
            "",
        ]
    )
    return Response(body, mimetype="text/plain")


@app.get("/sitemap.xml")
def sitemap_xml():
    today = datetime.now(timezone.utc).date().isoformat()
    urls: list[tuple[str, str]] = []
    seen: set[str] = set()

    def add_url(loc: str) -> None:
        loc = (loc or "").strip()
        if not loc or loc in seen:
            return
        seen.add(loc)
        urls.append((loc, today))

    add_url(url_for("index", _external=True))

    for path in _parse_env_list("SITEMAP_PATHS"):
        if path.startswith("http://") or path.startswith("https://"):
            add_url(path)
            continue
        normalized = path if path.startswith("/") else f"/{path}"
        add_url(urljoin(_site_url_root(), normalized.lstrip("/")))

    for abs_url in _parse_env_list("SITEMAP_URLS"):
        add_url(abs_url)

    include_projects = _truthy_env("SITEMAP_INCLUDE_PROJECTS", True)
    if include_projects:
        project_slugs = sorted(set(PROJECT_HOSTED.keys())
                               | set(_get_local_portfolio_slugs()))
        for slug in project_slugs:
            add_url(url_for("project_index", project_slug=slug, _external=True))

    lines: list[str] = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        "<urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">",
    ]
    for loc, lastmod in urls:
        lines.extend(
            [
                "  <url>",
                f"    <loc>{loc}</loc>",
                f"    <lastmod>{lastmod}</lastmod>",
                "  </url>",
            ]
        )
    lines.append("</urlset>")

    return Response("\n".join(lines) + "\n", mimetype="application/xml")


@app.get("/projects/<project_slug>")
@app.get("/projects/<project_slug>/")
def project_index(project_slug: str):
    project_slug = _clean(project_slug, max_len=200)
    if not project_slug or not all(ch.isalnum() or ch in {"-", "_"} for ch in project_slug):
        abort(404)

    # ****************************
    # If a static build exists locally, prefer it.
    # ****************************
    static_root = Path(app.static_folder or "static")
    local_index = static_root / "portfolio" / project_slug / "index.html"
    if local_index.exists():
        return redirect(url_for("static", filename=f"portfolio/{project_slug}/index.html"))

    if project_slug in PROJECT_HOSTED:
        return redirect(PROJECT_HOSTED[project_slug])

    # ****************************
    # Minimal fallback: project repos follow the slug name.
    # ****************************
    github_org = _clean(os.getenv("GITHUB_ORG"), max_len=100) or "FrankJamison"
    return redirect(f"https://github.com/{github_org}/{project_slug}")


@app.post("/leave-reply")
def leave_reply():
    # ****************************
    # Honeypot field: if filled, treat as bot submission.
    # ****************************
    hp = _clean(request.form.get("hp"), max_len=200)
    if hp:
        return jsonify({"ok": True})

    name = _clean(request.form.get("name"), max_len=200)
    email = _clean(request.form.get("email"), max_len=254)
    website = _clean(request.form.get("website"), max_len=500)
    comment = _clean(request.form.get("comment"), max_len=5000)
    blog_title = _clean(request.form.get("blog_title"), max_len=300)
    page_url = _clean(request.form.get("page_url"), max_len=2000)

    if not name or not email or not comment:
        return jsonify({"ok": False, "error": "Name, email, and comment are required."})

    now = datetime.now(timezone.utc).isoformat()

    # ****************************
    # Persist submissions locally for quick review/backup.
    # ****************************
    _append_csv(
        Path("data/leave_reply.csv"),
        headers=["timestamp", "name", "email", "website",
                 "blog_title", "page_url", "comment"],
        row={
            "timestamp": now,
            "name": name,
            "email": email,
            "website": website,
            "blog_title": blog_title,
            "page_url": page_url,
            "comment": comment,
        },
    )

    subject = f"Portfolio blog reply: {blog_title or 'Leave a Reply'}"
    body = "\n".join(
        [
            "New blog reply submitted:",
            f"Time (UTC): {now}",
            f"Name: {name}",
            f"Email: {email}",
            f"Website: {website}",
            f"Blog title: {blog_title}",
            f"Page: {page_url}",
            "",
            "Comment:",
            comment,
        ]
    )

    # ****************************
    # Send notification email with Reply-To set to the visitor.
    # ****************************
    ok, err = _send_email(subject=subject, body=body, reply_to=email)
    if not ok:
        return jsonify({"ok": False, "error": err})

    return jsonify({"ok": True})


@app.post("/contact")
def contact_message():
    # ****************************
    # Honeypot field: if filled, treat as bot submission.
    # ****************************
    hp = _clean(request.form.get("hp"), max_len=200)
    if hp:
        return jsonify({"ok": True})

    name = _clean(request.form.get("name"), max_len=200)
    phone = _clean(request.form.get("phone"), max_len=50)
    email = _clean(request.form.get("email"), max_len=254)
    subject = _clean(request.form.get("subject"), max_len=300)
    message = _clean(request.form.get("message"), max_len=8000)
    page_url = _clean(request.form.get("page_url"), max_len=2000)

    if not name or not email or not subject or not message:
        return jsonify({"ok": False, "error": "Name, email, subject, and message are required."})

    now = datetime.now(timezone.utc).isoformat()

    # ****************************
    # Persist submissions locally for quick review/backup.
    # ****************************
    _append_csv(
        Path("data/contact_messages.csv"),
        headers=["timestamp", "name", "email",
                 "phone", "subject", "page_url", "message"],
        row={
            "timestamp": now,
            "name": name,
            "email": email,
            "phone": phone,
            "subject": subject,
            "page_url": page_url,
            "message": message,
        },
    )

    mail_subject = f"Portfolio contact: {subject}"
    body = "\n".join(
        [
            "New contact message submitted:",
            f"Time (UTC): {now}",
            f"Name: {name}",
            f"Email: {email}",
            f"Phone: {phone}",
            f"Page: {page_url}",
            "",
            "Message:",
            message,
        ]
    )

    # ****************************
    # Send notification email with Reply-To set to the visitor.
    # ****************************
    ok, err = _send_email(subject=mail_subject, body=body, reply_to=email)
    if not ok:
        return jsonify({"ok": False, "error": err})

    return jsonify({"ok": True})
