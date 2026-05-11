"""Scientific web API clients for MitoRAG Phase 5."""

from mitorag_web.biorxiv import BioRxivClient
from mitorag_web.cache import MemoryCache, RedisCache
from mitorag_web.europe_pmc import EuropePMCClient
from mitorag_web.models import (
    BioRxivPreprint,
    EuropePMCResult,
    PubMedAbstract,
    PubMedResult,
    PubTatorAnnotation,
    S2Paper,
    WebChunk,
)
from mitorag_web.pubmed import PubMedClient
from mitorag_web.pubtator import PubTatorClient
from mitorag_web.rate_limiter import AsyncRateLimiter, pubmed_rate_limiter
from mitorag_web.semantic_scholar import SemanticScholarClient

__all__ = [
    "AsyncRateLimiter",
    "BioRxivClient",
    "BioRxivPreprint",
    "EuropePMCClient",
    "EuropePMCResult",
    "MemoryCache",
    "PubMedAbstract",
    "PubMedClient",
    "PubMedResult",
    "PubTatorAnnotation",
    "PubTatorClient",
    "RedisCache",
    "S2Paper",
    "SemanticScholarClient",
    "WebChunk",
    "__version__",
    "pubmed_rate_limiter",
]

__version__ = "1.0.0"
