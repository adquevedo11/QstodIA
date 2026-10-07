"""Invalidate go-live agent cache when findings change severity or status."""
from __future__ import annotations

import logging
import os
import threading

from django.db.models.signals import post_save
from django.dispatch import receiver

logger = logging.getLogger(__name__)

AGENT_URL = os.environ.get("GOLIVE_AGENT_URL", "http://localhost:8001")

WATCHED_FIELDS = {"severity", "active", "verified", "false_p", "out_of_scope", "risk_accepted", "duplicate"}


def _invalidate_engagement_cache(engagement_id: int) -> None:
    """Fire-and-forget DELETE to the agent cache endpoint."""
    try:
        import requests  # noqa: PLC0415 -- lazy to avoid startup cost
        requests.delete(f"{AGENT_URL}/cache/{engagement_id}", timeout=5)
    except Exception:
        pass


@receiver(post_save, sender="dojo.Finding")
def invalidate_go_live_cache_on_finding_change(sender, instance, created, update_fields, **kwargs):
    if created:
        return
    if update_fields is not None and not WATCHED_FIELDS.intersection(update_fields):
        return
    try:
        engagement_id = instance.test.engagement_id
    except Exception:
        return
    threading.Thread(
        target=_invalidate_engagement_cache,
        args=(engagement_id,),
        daemon=True,
    ).start()
