"""Live match tracking: singletons shared by the app, poller and routers."""
from .broadcaster import EventBroadcaster
from .manager import LiveMatchManager

broadcaster = EventBroadcaster()
live_manager = LiveMatchManager()
