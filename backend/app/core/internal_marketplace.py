"""Gnosis Internal Agent Marketplace — Publish and discover reusable agents."""
import uuid, logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

logger = logging.getLogger("gnosis.internal_marketplace")


@dataclass
class MarketplaceListing:
    id: str
    agent_id: str
    title: str
    description: str
    category: str
    author: str
    version: str
    downloads: int = 0
    rating: float = 0.0
    published_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: List[str] = field(default_factory=list)


class InternalMarketplaceEngine:
    def __init__(self):
        self._listings: Dict[str, MarketplaceListing] = {}
        self._ratings: Dict[str, List[float]] = {}

    def publish(self, agent_id: str, title: str, description: str, category: str,
                author: str, version: str, tags: Optional[List[str]] = None) -> MarketplaceListing:
        listing = MarketplaceListing(
            id=uuid.uuid4().hex[:12],
            agent_id=agent_id,
            title=title,
            description=description,
            category=category,
            author=author,
            version=version,
            tags=tags or [],
        )
        self._listings[listing.id] = listing
        self._ratings[listing.id] = []
        logger.info(f"Published listing {listing.id}: {title}")
        return listing

    def unpublish(self, listing_id: str) -> bool:
        if listing_id not in self._listings:
            raise KeyError("Listing not found")
        del self._listings[listing_id]
        self._ratings.pop(listing_id, None)
        logger.info(f"Unpublished listing {listing_id}")
        return True

    def search(self, query: Optional[str] = None, category: Optional[str] = None) -> List[MarketplaceListing]:
        results = list(self._listings.values())
        if category:
            results = [r for r in results if r.category.lower() == category.lower()]
        if query:
            q = query.lower()
            results = [
                r for r in results
                if q in r.title.lower()
                or q in r.description.lower()
                or any(q in t.lower() for t in r.tags)
            ]
        return sorted(results, key=lambda r: r.downloads, reverse=True)

    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        return self._listings.get(listing_id)

    def rate(self, listing_id: str, score: float) -> MarketplaceListing:
        listing = self._listings.get(listing_id)
        if not listing:
            raise KeyError("Listing not found")
        if not (1.0 <= score <= 5.0):
            raise ValueError("Rating score must be between 1 and 5")
        self._ratings[listing_id].append(score)
        all_scores = self._ratings[listing_id]
        listing.rating = round(sum(all_scores) / len(all_scores), 2)
        logger.info(f"Listing {listing_id} rated {score}, avg now {listing.rating}")
        return listing

    def increment_downloads(self, listing_id: str) -> MarketplaceListing:
        listing = self._listings.get(listing_id)
        if not listing:
            raise KeyError("Listing not found")
        listing.downloads += 1
        return listing


internal_marketplace_engine = InternalMarketplaceEngine()
