"""Live match tracking: singletons shared by the app, poller and routers."""
from .broadcaster import EventBroadcaster
from .manager import LiveMatchManager

broadcaster = EventBroadcaster()
live_manager = LiveMatchManager()

# In-memory cache of currently in-progress ATP singles, refreshed every 5 min
# by the atp_live poller and read by the /api/live endpoint.
atp_live: dict = {"matches": []}
