"""Bounded public-source collection. Extraction proposes drafts, never facts."""

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import ipaddress
import json
import re
import socket
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, urljoin
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.releases import SourceDocument, UpgradeCandidate
from app.schemas.releases import SourceImport

TEAM_HOSTS = (
    "ferrari.com",
    "mercedesamgf1.com",
    "mclaren.com",
    "redbullracing.com",
    "astonmartinf1.com",
    "alpinef1.com",
    "williamsf1.com",
    "haasf1team.com",
    "visacashapprb.com",
    "audif1.com",
    "cadillacf1team.com",
)
ALLOWED_HOSTS = TEAM_HOSTS + (
    "fia.com",
    "formula1.com",
    "ferrari.com",
    "mercedesamgf1.com",
    "the-race.com",
    "motorsportweek.com",
    "motorsport.com",
    "autosport.com",
)
TEAM_PATTERNS = {
    "ferrari": r"\bferrari\b|\bsf[- ]?26\b",
    "mercedes": r"\bmercedes\b|\bw17\b",
    "mclaren": r"\bmclaren\b|\bmcl40\b",
    "red_bull": r"\bred bull(?: racing)?\b|\brb22\b",
    "aston_martin": r"\baston martin\b|\bamr26\b",
    "alpine": r"\balpine\b|\ba526\b",
    "williams": r"\bwilliams\b|\bfw48\b",
    "haas": r"\bhaas\b|\bvf[- ]?26\b",
    "racing_bulls": r"\bracing bulls\b|\bvcarb(?:[- ]?03)?\b",
    "audi": r"\baudi\b|\br26\b",
    "cadillac": r"\bcadillac\b|\bmac[- ]?26\b",
}
COMPONENT_PATTERNS = {
    "front_wing": r"\bfront wing\b",
    "rear_wing": r"\brear wing\b",
    "floor": r"\bfloor\b|\bunderfloor\b",
    "diffuser": r"\bdiffuser\b",
    "sidepods": r"\bsidepod|\bcooling inlet",
    "engine_cover": r"\bengine cover\b|\bairbox\b",
    "nose": r"\bnose(?:cone)?\b",
    "suspension": r"\bsuspension\b|\bpushrod\b|\bpullrod\b|\bbrake duct\b",
    "halo": r"\bhalo\b",
    "wheels": r"\bwheel(?:s)?\b|\btyre(?:s)?\b",
}
CHANGE = re.compile(
    r"\b(upgrad\w*|revis\w*|updat\w*|new|modif\w*|chang\w*|introduc\w*|redesign\w*)\b",
    re.I,
)


def canonical_url(url):
    parts = urlparse(url)
    if (
        parts.scheme not in {"http", "https"}
        or not parts.hostname
        or parts.username
        or parts.password
    ):
        raise ValueError("Use a public HTTP or HTTPS source URL.")
    query = [
        (k, v)
        for k, v in parse_qsl(parts.query)
        if not k.startswith("utm_") and k not in {"fbclid", "gclid"}
    ]
    return urlunparse(
        (
            parts.scheme.lower(),
            parts.netloc.lower(),
            parts.path or "/",
            "",
            urlencode(sorted(query)),
            "",
        )
    )


def check_remote(url):
    parts = urlparse(canonical_url(url))
    host = parts.hostname
    if parts.port not in {None, 80, 443} or not any(
        host == h or host.endswith("." + h) for h in ALLOWED_HOSTS
    ):
        raise ValueError(
            "Automatic fetching is limited to configured public F1 publishers. Paste the article text for another source."
        )
    addresses = socket.getaddrinfo(host, parts.port or 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError("The source must resolve to public internet addresses.")


def fetch_bytes(url):
    settings = get_settings()
    with httpx.Client(
        timeout=settings.SOURCE_TIMEOUT_SECONDS,
        follow_redirects=False,
        trust_env=False,
        headers={
            "User-Agent": "F1EngineeringDashboard/1.0 (public technical references; manual review)",
            "Accept": "text/html,application/pdf,application/rss+xml,application/atom+xml",
        },
    ) as client:
        for _ in range(4):
            check_remote(url)
            with client.stream("GET", url) as response:
                if response.is_redirect:
                    url = urljoin(url, response.headers.get("location", ""))
                    continue
                response.raise_for_status()
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > settings.SOURCE_MAX_BYTES:
                        raise ValueError("Source exceeds the download limit.")
                return (
                    bytes(data),
                    response.headers.get("content-type", ""),
                    str(response.url),
                )
    raise ValueError("Too many source redirects.")


def parse_date(value):
    if not value:
        return None
    try:
        date = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        try:
            date = parsedate_to_datetime(value)
        except (ValueError, TypeError, OverflowError):
            return None
    return (
        date.replace(tzinfo=timezone.utc)
        if date.tzinfo is None
        else date.astimezone(timezone.utc)
    )


def parse_document(data, mime, url):
    if data.startswith(b"%PDF"):
        import fitz

        with fitz.open(stream=data, filetype="pdf") as pdf:
            if len(pdf) > 250:
                raise ValueError("PDF exceeds the page limit.")
            pages = [
                {"page": i + 1, "text": page.get_text()} for i, page in enumerate(pdf)
            ]
            return {
                "text": "\n\n".join(p["text"] for p in pages),
                "pages": pages,
                "title": pdf.metadata.get("title") or urlparse(url).path.split("/")[-1],
                "published_at": None,
                "image_urls": [],
                "source_type": "fia_submission" if "car_presentation" in url else "pdf",
            }
    soup = BeautifulSoup(data, "html.parser")
    published = soup.find(
        "meta", attrs={"property": "article:published_time"}
    ) or soup.find("meta", attrs={"name": "date"})
    date = parse_date(published.get("content", "")) if published else None
    if date is None:

        def dated_article(node):
            if isinstance(node, list):
                return next(
                    (value for child in node if (value := dated_article(child))), None
                )
            if isinstance(node, dict):
                if node.get("datePublished"):
                    return parse_date(node["datePublished"])
                return dated_article(node.get("@graph", []))
            return None

        for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
            try:
                date = dated_article(json.loads(script.get_text()))
            except (ValueError, TypeError):
                continue
            if date:
                break
    title = soup.title.get_text(" ", strip=True) if soup.title else urlparse(url).path
    main = soup.find("article") or soup.find("main") or soup.body or soup
    images = list(
        dict.fromkeys(
            urljoin(url, img.get("src", ""))
            for img in main.find_all("img")
            if img.get("src")
        )
    )[:30]
    for tag in main.find_all(["script", "style", "nav", "footer", "header", "aside"]):
        tag.decompose()
    blocks = main.find_all(["h1", "h2", "h3", "p", "li"])
    text = (
        "\n\n".join(b.get_text(" ", strip=True) for b in blocks)
        if blocks
        else main.get_text(" ", strip=True)
    )
    if len(text) < 100 or any(
        t in text[:800].lower()
        for t in (
            "verify that you're not a robot",
            "access denied",
            "enable javascript to continue",
        )
    ):
        raise ValueError(
            "The publisher did not provide readable article text. Use manual text import."
        )
    return {
        "text": text[:200_000],
        "title": title,
        "published_at": date,
        "pages": [],
        "image_urls": images,
        "source_type": (
            "team_release"
            if any(
                urlparse(url).hostname == h or urlparse(url).hostname.endswith("." + h)
                for h in TEAM_HOSTS
            )
            else "article"
        ),
    }


def extract_candidates(document, season=2026):
    result = []

    def append_claim(paragraph, team, components, page):
        years = {int(value) for value in re.findall(r"\b20[2-9][0-9]\b", paragraph)}
        if years and season not in years:
            return  # A clearly dated 2027 development is not a 2026 upgrade.
        for component in components:
            result.append(
                UpgradeCandidate(
                    source_id=document.id,
                    team_key=team,
                    season=season,
                    component=component,
                    event_name=document.event_name,
                    summary=paragraph[:2000],
                    supporting_passage=paragraph[:4000],
                    page=page,
                    evidence_status="unverified",
                    representation="annotation_only",
                    status="draft",
                )
            )

    chunks = document.pages or [{"page": None, "text": document.text}]
    for chunk in chunks:
        # FIA submissions have numbered table rows. Match the submitted component
        # label, so a downstream-flow explanation cannot invent another upgrade.
        rows = re.split(r"\n\s*\d{1,2}\s*\n", chunk["text"])
        if (
            document.source_type == "fia_submission"
            and len(rows) > 1
            and re.search(r"Updated\s+component", rows[0], re.I)
        ):
            teams = [
                key
                for key, pattern in TEAM_PATTERNS.items()
                if re.search(pattern, rows[0], re.I)
            ]
            team = teams[0] if len(teams) == 1 else None
            for row in rows[1:]:
                paragraph = re.sub(r"\s+", " ", row).strip()
                if not paragraph:
                    continue
                label = re.split(
                    r"\b(?:Performance|Circuit\s+specific|Reliability)\b",
                    paragraph,
                    maxsplit=1,
                    flags=re.I,
                )[0]
                components = [
                    key
                    for key, pattern in COMPONENT_PATTERNS.items()
                    if re.search(pattern, label, re.I)
                ]
                # Keep unfamiliar submissions unresolved for the maintainer.
                append_claim(paragraph, team, components or [None], chunk["page"])
            continue
        context = None
        for paragraph in re.split(r"\n\s*\n|(?<=[.!?;])\s+(?=[A-Z])", chunk["text"]):
            paragraph = re.sub(r"\s+", " ", paragraph).strip()
            if not paragraph:
                continue
            teams = [
                key
                for key, pattern in TEAM_PATTERNS.items()
                if re.search(pattern, paragraph, re.I)
            ]
            if (
                len(teams) == 1
                and len(paragraph) < 100
                and not CHANGE.search(paragraph)
            ):
                context = teams[0]
                continue
            if len(teams) > 1:
                context = None
            components = [
                key
                for key, pattern in COMPONENT_PATTERNS.items()
                if re.search(pattern, paragraph, re.I)
            ]
            if not CHANGE.search(paragraph) or not (components or teams or context):
                continue
            team = teams[0] if len(teams) == 1 else context if not teams else None
            append_claim(paragraph, team, components or [None], chunk["page"])
    return result[:200]


def import_source(db: Session, payload: SourceImport):
    url = canonical_url(payload.url)
    if payload.text:
        parsed = {
            "text": payload.text,
            "pages": [],
            "image_urls": [],
            "title": payload.title or url,
            "source_type": "manual",
            "published_at": payload.published_at,
        }
    else:
        data, mime, final_url = fetch_bytes(url)
        parsed = parse_document(data, mime, final_url)
        url = canonical_url(final_url)
    digest = hashlib.sha256(
        re.sub(r"\s+", " ", parsed["text"]).strip().encode()
    ).hexdigest()
    existing = (
        db.query(SourceDocument)
        .filter_by(canonical_url=url, content_hash=digest)
        .first()
    )
    if existing:
        return existing, [], True
    source = SourceDocument(
        url=payload.url,
        canonical_url=url,
        content_hash=digest,
        title=payload.title or parsed["title"],
        publisher=payload.publisher or urlparse(url).hostname,
        source_type=parsed["source_type"],
        published_at=payload.published_at
        or parsed["published_at"]
        or payload.fallback_published_at,
        event_name=payload.event_name,
        text=parsed["text"],
        pages=parsed["pages"],
        image_urls=parsed["image_urls"],
    )
    db.add(source)
    db.flush()
    candidates = extract_candidates(source, payload.season)
    db.add_all(candidates)
    db.flush()
    return source, candidates, False


def feed_links(data):
    root = ET.fromstring(data)
    result = []
    for item in root.findall(".//item") + root.findall(".//{*}entry"):
        title = item.findtext("title") or item.findtext("{*}title") or ""
        link = item.findtext("link") or ""
        if not link:
            for node in item.findall("{*}link"):
                if node.get("rel", "alternate") == "alternate":
                    link = node.get("href", "")
                    break
        date = parse_date(item.findtext("pubDate") or item.findtext("{*}published"))
        if title and link:
            result.append({"url": link, "title": title, "published_at": date})
    return result


def discover_links(entry, data, url):
    """Find bounded, deduplicated article links without wandering into other sports."""
    if entry["kind"] == "document":
        return [{"url": url, "published_at": None}]
    if entry["kind"] == "feed":
        items = [
            item
            for item in feed_links(data)
            if re.search(
                r"\bf1\b|formula.?1|formula.?one",
                item["url"] + " " + item["title"],
                re.I,
            )
            and not re.search(
                r"/(motogp|imsa|indycar|nascar|formula-e)/", item["url"], re.I
            )
        ]
    else:
        soup = BeautifulSoup(data, "html.parser")
        for node in soup.find_all(["nav", "footer", "header", "aside"]):
            node.decompose()
        host = urlparse(url).hostname
        items = [
            {"url": urljoin(url, a["href"]), "published_at": None}
            for a in soup.find_all("a", href=True)
            if re.search(entry["link_pattern"], a["href"] + " " + a.get_text(" "), re.I)
            and urlparse(urljoin(url, a["href"])).hostname == host
        ]
    unique = {}
    for item in items:
        target = canonical_url(item["url"])
        if target != canonical_url(url):
            unique.setdefault(target, {**item, "url": target})
    return list(unique.values())[: entry.get("limit", 5)]
