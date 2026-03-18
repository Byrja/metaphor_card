import json
import logging
from datetime import datetime, timezone


def setup_event_logger(level: str = "INFO") -> None:
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=numeric_level, format="%(message)s")


def log_event(event_name: str, **fields) -> None:
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event_name": event_name,
        **fields,
    }
    logging.getLogger("metaphor_card.events").info(json.dumps(payload, ensure_ascii=False))
