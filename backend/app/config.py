import os 
from dataclasses import dataclass

@dataclass(frozen=True)
class Setting: 
    cookie_name: str
    cookie_secure: bool
    session_hours: int
    allowed_origins: frozenset[str]


setting = Setting(cookie_name="FutBotSession", 
                  cookie_secure=os.getenv("AUTH_COOKIE_SECURE", "false"), 
                  session_hours=os.getenv("AUTH_SESSION_HOURS", "8"), 
                  allowed_origins=frozenset(origin.strip().rstrip("/")
                                            for origin in os.getenv("AUTH_ALLOWED_ORIGINS").split(",")
                                            if origin.strip()))