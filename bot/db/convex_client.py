from convex import ConvexClient
from bot.config import CONVEX_URL

_client: ConvexClient | None = None


def get_client() -> ConvexClient:
    global _client
    if _client is None:
        _client = ConvexClient(CONVEX_URL)
    return _client
