from __future__ import annotations

from dataclasses import dataclass, field
from html import unescape
import logging
import re
from typing import Sequence
from xml.etree import ElementTree as ET

import httpx
from sqlalchemy.orm import Session

try:
    from app.models.models import Component, Race, Team
    from app.schemas.schemas import UpgradeIngestItem
except ModuleNotFoundError:  # Docker image expects backend.* imports
    from backend.models.models import Component, Race, Team
    from backend.schemas.schemas import UpgradeIngestItem

logger = logging.getLogger(__name__)


DEFAULT_FEED_URLS: tuple[str, ...] = (
    "https://www.motorsportweek.com/feed/",
    "https://www.the-race.com/rss/",
)

UPGRADE_KEYWORDS: tuple[str, ...] = (
    "upgrade",
    "upgrades",
    "updated",
    "update",
    "revised",
    "revision",
    "new package",
    "aero package",
    "floor",
    "diffuser",
    "front wing",
    "rear wing",
    "sidepod",
    "suspension",
    "brake duct",
)

TEAM_ALIAS_OVERRIDES: dict[str, tuple[str, ...]] = {
    "red bull": (
        "red bull racing",
        "oracle red bull",
        "oracle red bull racing",
    ),
    "rb": (
        "racing bulls",
        "visa cash app rb",
        "vcarb",
    ),
    "kick sauber": (
        "sauber",
        "stake",
        "stake f1",
    ),
}

ZONE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "front wing": ("front wing", "endplate", "mainplane", "flap"),
    "rear wing": ("rear wing", "beam wing", "drs", "gurney"),
    "floor": ("floor", "underfloor", "tunnel", "fence"),
    "floor edge": ("floor edge", "edge wing"),
    "diffuser": ("diffuser", "strake", "expansion"),
    "sidepod": ("sidepod", "cooling inlet", "coke bottle"),
    "brake duct": ("brake duct", "duct inlet", "brake cooling"),
    "engine cover": ("engine cover", "bodywork", "cooling exit"),
    "suspension arm": ("wishbone", "suspension arm", "pushrod", "pullrod"),
    "nose": ("nose", "nosecone"),
}

COMPONENT_ALIAS_OVERRIDES: dict[str, tuple[str, ...]] = {
    "front wing endplate": ("endplate",),
    "front wing mainplane": ("mainplane", "front wing"),
    "floor edge": ("floor edge",),
    "floor fence": ("floor fence", "fence"),
    "diffuser strake": ("diffuser strake", "diffuser"),
    "sidepod inlet": ("sidepod inlet", "cooling inlet"),
    "rear wing flap": ("rear wing flap", "drs flap", "rear wing"),
    "brake duct inlet": ("brake duct",),
    "engine cover bodywork": ("engine cover", "bodywork"),
    "suspension fairing": ("suspension fairing", "wishbone"),
}


@dataclass
class FeedEntry:
    title: str
    summary: str
    link: str
    source: str


@dataclass
class UpgradeTrackerStats:
    scanned_entries: int = 0
    candidates: int = 0
    skipped_non_upgrade: int = 0
    skipped_no_team: int = 0
    skipped_no_component: int = 0
    skipped_no_race: int = 0
    feed_errors: list[str] = field(default_factory=list)


def _clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _looks_like_upgrade(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in UPGRADE_KEYWORDS)


def _find_first_text(node: ET.Element, paths: Sequence[str]) -> str:
    for path in paths:
        value = node.findtext(path)
        if value:
            return _clean_text(value)
    return ""


def _parse_feed_xml(xml_text: str, source_url: str, max_items: int) -> list[FeedEntry]:
    root = ET.fromstring(xml_text)
    entries: list[FeedEntry] = []

    rss_items = root.findall(".//item")
    if rss_items:
        for node in rss_items[:max_items]:
            title = _find_first_text(node, ("title", "{*}title"))
            summary = _find_first_text(
                node,
                (
                    "description",
                    "{*}description",
                    "{http://purl.org/rss/1.0/modules/content/}encoded",
                ),
            )
            link = _find_first_text(node, ("link", "{*}link"))
            if title:
                entries.append(
                    FeedEntry(
                        title=title,
                        summary=summary,
                        link=link,
                        source=source_url,
                    )
                )
        return entries

    atom_items = root.findall(".//{*}entry")
    for node in atom_items[:max_items]:
        title = _find_first_text(node, ("{*}title", "title"))
        summary = _find_first_text(node, ("{*}summary", "{*}content", "summary", "content"))
        link = ""
        link_node = node.find("{*}link") or node.find("link")
        if link_node is not None:
            link = _clean_text(link_node.attrib.get("href", ""))
            if not link and link_node.text:
                link = _clean_text(link_node.text)
        if title:
            entries.append(
                FeedEntry(
                    title=title,
                    summary=summary,
                    link=link,
                    source=source_url,
                )
            )
    return entries


def fetch_feed_entries(
    feed_urls: Sequence[str] = DEFAULT_FEED_URLS,
    max_per_feed: int = 20,
    timeout_seconds: float = 12.0,
) -> tuple[list[FeedEntry], list[str]]:
    entries: list[FeedEntry] = []
    errors: list[str] = []

    headers = {
        "User-Agent": "F1EngineeringDashboardBot/0.1 (+https://github.com/prayag2301/f1-engineering-dashboard)",
        "Accept": "application/rss+xml, application/atom+xml, application/xml, text/xml;q=0.9",
    }

    with httpx.Client(timeout=timeout_seconds, follow_redirects=True, headers=headers) as client:
        for url in feed_urls:
            try:
                response = client.get(url)
                response.raise_for_status()
                parsed = _parse_feed_xml(response.text, source_url=url, max_items=max_per_feed)
                entries.extend(parsed)
            except Exception as exc:  # pragma: no cover - defensive branch
                msg = f"{url}: {exc}"
                logger.warning("Feed fetch failed: %s", msg)
                errors.append(msg)

    return entries, errors


def _team_aliases(teams: Sequence[Team]) -> list[tuple[str, Team]]:
    alias_map: dict[str, Team] = {}

    for team in teams:
        aliases = {
            _clean_text(team.name).lower(),
            _clean_text(team.full_name or "").lower(),
        }
        for alias in TEAM_ALIAS_OVERRIDES.get(_clean_text(team.name).lower(), ()):  # pragma: no branch
            aliases.add(alias.lower())

        for alias in aliases:
            if not alias:
                continue
            if alias == "rb":
                # Too noisy in text; keep richer aliases like "racing bulls" instead.
                continue
            alias_map[alias] = team

    return sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True)


def _extract_team(text: str, aliases: Sequence[tuple[str, Team]]) -> Team | None:
    lowered = text.lower()
    for alias, team in aliases:
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, lowered):
            return team
    return None


def _component_hints(components: Sequence[Component]) -> list[tuple[Component, set[str]]]:
    hints: list[tuple[Component, set[str]]] = []
    for component in components:
        name = _clean_text(component.name).lower()
        zone = _clean_text(component.zone.value).lower()

        keywords = {name, zone}
        keywords.update(COMPONENT_ALIAS_OVERRIDES.get(name, ()))
        keywords.update(ZONE_KEYWORDS.get(zone, ()))

        for token in re.split(r"[^a-z0-9]+", name):
            if len(token) >= 5:
                keywords.add(token)

        hints.append((component, {keyword for keyword in keywords if keyword}))
    return hints


def _extract_component(
    text: str,
    component_hints: Sequence[tuple[Component, set[str]]],
) -> Component | None:
    lowered = text.lower()
    winner: Component | None = None
    best_score = 0

    for component, keywords in component_hints:
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score > best_score:
            best_score = score
            winner = component

    if best_score == 0:
        return None
    return winner


def _race_aliases(races: Sequence[Race]) -> list[tuple[str, Race]]:
    alias_map: dict[str, Race] = {}
    for race in races:
        name = _clean_text(race.name).lower()
        aliases = {name}
        aliases.add(name.replace(" grand prix", " gp"))
        aliases.add(name.replace(" gp", ""))
        if " gp" in name:
            aliases.add(name.replace(" gp", " grand prix"))

        for alias in aliases:
            alias = alias.strip()
            if alias:
                alias_map[alias] = race

    return sorted(alias_map.items(), key=lambda item: len(item[0]), reverse=True)


def _default_race(races: Sequence[Race]) -> Race | None:
    if not races:
        return None
    return max(races, key=lambda race: (race.season, race.round_number, race.date))


def _extract_race(
    text: str,
    aliases: Sequence[tuple[str, Race]],
    fallback: Race | None,
) -> Race | None:
    lowered = text.lower()
    for alias, race in aliases:
        pattern = rf"\b{re.escape(alias)}\b"
        if re.search(pattern, lowered):
            return race
    return fallback


def collect_upgrade_ingest_items(
    db: Session,
    season: int | None = None,
    max_entries: int = 50,
    feed_urls: Sequence[str] = DEFAULT_FEED_URLS,
) -> tuple[list[UpgradeIngestItem], UpgradeTrackerStats]:
    """
    Fetch RSS feed entries and map parsable entries to UpgradeIngestItem rows.

    The mapper intentionally prefers conservative matching:
      - entry must look like an upgrade story
      - team must be recognized
      - component must be recognized
      - race must be recognized or inferred via latest known race fallback
    """
    stats = UpgradeTrackerStats()

    teams = db.query(Team).all()
    components = db.query(Component).all()
    race_query = db.query(Race)
    if season is not None:
        race_query = race_query.filter(Race.season == season)
    races = race_query.order_by(Race.round_number).all()

    if not teams:
        stats.feed_errors.append("No teams found in database")
        return [], stats
    if not components:
        stats.feed_errors.append("No components found in database")
        return [], stats
    if not races:
        stats.feed_errors.append("No races found in database")
        return [], stats

    per_feed = max(5, (max_entries // max(len(feed_urls), 1)) + 2)
    entries, feed_errors = fetch_feed_entries(feed_urls=feed_urls, max_per_feed=per_feed)
    stats.feed_errors.extend(feed_errors)

    team_aliases = _team_aliases(teams)
    component_hints = _component_hints(components)
    race_aliases = _race_aliases(races)
    race_fallback = _default_race(races)

    items: list[UpgradeIngestItem] = []
    seen: set[tuple[str, str, str, str]] = set()

    for entry in entries:
        if len(items) >= max_entries:
            break

        stats.scanned_entries += 1
        merged_text = _clean_text(f"{entry.title} {entry.summary}")

        if not _looks_like_upgrade(merged_text):
            stats.skipped_non_upgrade += 1
            continue

        team = _extract_team(merged_text, team_aliases)
        if team is None:
            stats.skipped_no_team += 1
            continue

        component = _extract_component(merged_text, component_hints)
        if component is None:
            stats.skipped_no_component += 1
            continue

        race = _extract_race(merged_text, race_aliases, race_fallback)
        if race is None:
            stats.skipped_no_race += 1
            continue

        description = entry.title.strip() or entry.summary.strip()
        if not description:
            stats.skipped_non_upgrade += 1
            continue

        detail = entry.summary.strip() or None
        dedupe_key = (
            str(team.id),
            str(race.id),
            str(component.id),
            _clean_text(description).lower(),
        )
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)

        items.append(
            UpgradeIngestItem(
                team_id=team.id,
                race_id=race.id,
                component_id=component.id,
                description=description,
                technical_detail=detail,
                source=entry.link or entry.source,
            )
        )

    stats.candidates = len(items)
    return items, stats


__all__ = [
    "DEFAULT_FEED_URLS",
    "UpgradeTrackerStats",
    "collect_upgrade_ingest_items",
    "fetch_feed_entries",
]
