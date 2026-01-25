from django.utils import timezone

ALLOWED_RECENT_SEARCH_KEYS = ('hotels', 'buses', 'packages')


def get_recent_searches(session):
    """Return normalized recent searches stored in session."""
    recent = session.get('recent_searches') or {}
    for key in ALLOWED_RECENT_SEARCH_KEYS:
        recent.setdefault(key, [])
    return recent


def _is_duplicate(entry, candidate):
    """Check if candidate matches entry ignoring timestamp."""
    candidate_copy = {k: v for k, v in candidate.items() if k != 'ts'}
    for key, value in candidate_copy.items():
        if entry.get(key) != value:
            return False
    # Ensure no extra keys change meaning
    return True


def update_recent_search(session, category, payload, max_items=5):
    """Persist a recent search payload into session (per category)."""
    if category not in ALLOWED_RECENT_SEARCH_KEYS:
        return

    cleaned = {k: v for k, v in payload.items() if v not in (None, '')}
    if not cleaned:
        return

    cleaned['ts'] = timezone.now().isoformat()

    recent = get_recent_searches(session)
    existing = recent.get(category, [])
    deduped = [item for item in existing if not _is_duplicate(cleaned, item)]
    deduped.insert(0, cleaned)
    recent[category] = deduped[:max_items]

    session['recent_searches'] = recent
    session.modified = True
