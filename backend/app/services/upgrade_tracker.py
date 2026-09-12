"""Compatibility adapter for the consolidated draft-only source collector."""
from app.services.sources import fetch_bytes, feed_links, import_source, extract_candidates

__all__ = ["fetch_bytes", "feed_links", "import_source", "extract_candidates"]
