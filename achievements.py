"""Permanent achievements and cached review history. No Qt or Anki imports."""
from datetime import date, datetime, timedelta


TIERS = ("Bronze", "Silver", "Gold", "Diamond")
BADGES = (
    ("streak", "Study streak", (7, 30, 100, 365),
     "Study on consecutive Anki days. Your longest recorded streak counts, even after a break."),
    ("reviews", "Reviews", (500, 5000, 25000, 100000),
     "Answer cards. Repeated answers to the same card count; manual rescheduling does not."),
    ("days", "Study days", (7, 30, 100, 365),
     "Study on different Anki days. One answer is enough for a day to count. Breaks are welcome."),
    ("challenges", "Daily goals", (5, 25, 100, 365),
     "Complete daily challenges. Each day counts once, even without claiming XP. Counting starts with this feature."),
    ("comeback", "Welcome back", (3,),
     "After at least seven full days without reviews, study on three consecutive Anki days. This is a one-time achievement."),
)

GOAL_UNITS = {
    "streak": ("streak day", "streak days"),
    "reviews": ("review", "reviews"),
    "days": ("study day", "study days"),
    "challenges": ("daily goal", "daily goals"),
    "comeback": ("study day", "study days"),
}


class ReviewHistory:
    """Scan once per profile, then re-read only the last cached Anki day onward.

    A sync invalidates the entire snapshot because older reviews may arrive.
    Date bucketing applies historical local time BEFORE shifting the rollover.
    """
    def __init__(self):
        self.counts = {}
        self.day = None
        self.rollover = None
        self.dirty = True

    def invalidate(self, full=False):
        self.dirty = True
        if full:
            self.day = None

    def read(self, db, today, rollover):
        rollover = max(0, min(23, int(rollover)))
        if not self.dirty and self.day == today and self.rollover == rollover:
            return self.counts
        full = self.day is None or self.rollover != rollover or today < self.day
        start = 0 if full else int((datetime.combine(self.day, datetime.min.time())
                                   + timedelta(hours=rollover)).timestamp() * 1000)
        end = int((datetime.combine(today + timedelta(days=1), datetime.min.time())
                   + timedelta(hours=rollover)).timestamp() * 1000)
        rows = db.all(
            "SELECT date(id / 1000, 'unixepoch', 'localtime', ?), COUNT(*) "
            "FROM revlog WHERE ease > 0 AND id >= ? AND id < ? GROUP BY 1",
            f"-{rollover} hours", start, end)
        # Do not replace a valid snapshot until the database query succeeds.
        counts = {} if full else {d: n for d, n in self.counts.items() if d < self.day}
        counts.update({date.fromisoformat(d): int(n) for d, n in rows if d})
        self.counts, self.day, self.rollover, self.dirty = counts, today, rollover, False
        return counts


def history_metrics(counts, today):
    days = sorted(d for d, n in counts.items() if n > 0 and d <= today)
    longest = run = comeback_run = 0
    returned = False
    comeback_earned = False
    previous = None
    for day in days:
        gap = (day - previous).days if previous else None
        if gap == 1:
            run += 1
        else:
            run = 1
            returned = gap is not None and gap >= 8
        longest = max(longest, run)
        comeback_run = min(3, run) if returned else 0
        comeback_earned = comeback_earned or comeback_run >= 3
        previous = day
    # An unfinished comeback expires after another missed Anki day.
    current_streak = run if previous is not None and (today - previous).days <= 1 else 0
    if previous is None or (today - previous).days > 1:
        comeback_run = 0
    return {"reviews": sum(counts[d] for d in days), "days": len(days),
            "streak": longest, "current_streak": current_streak,
            "comeback": 3 if comeback_earned else comeback_run}


def update_achievements(data, counts, today, challenge_achieved=False, translate=lambda s: s):
    """Add fields without replacing existing gamification or unknown badge data."""
    changed = "achievements" not in data
    state = data.setdefault("achievements", {"earned": {}, "challenge_days": []})
    earned = state.setdefault("earned", {})
    # Existing profiles already have earned tiers.  On the first version that
    # supports new markers, adopt those tiers as seen so an update does not
    # label the complete achievement history as new.
    if not isinstance(state.get("seen"), dict):
        state["seen"] = {
            key: list(saved.keys()) for key, saved in earned.items()
            if isinstance(saved, dict)
        }
        changed = True
    seen = state["seen"]
    favorite = state.get("favorite")
    challenge_days = state.setdefault("challenge_days", [])
    day_key = today.isoformat()
    if challenge_achieved and day_key not in challenge_days:
        challenge_days.append(day_key)
        changed = True
    values = history_metrics(counts, today)
    values["challenges"] = len(set(challenge_days))
    result = []
    for key, name, thresholds, description in BADGES:
        saved = earned.get(key, {})
        seen_tiers = seen.get(key, [])
        if not isinstance(seen_tiers, list):
            seen_tiers = []
        value = values[key]
        for index, threshold in enumerate(thresholds):
            if value >= threshold and str(index) not in saved:
                saved[str(index)] = day_key
                earned[key] = saved
                changed = True
        tier = max((i for i in range(len(thresholds)) if str(i) in saved), default=-1)
        next_index = tier + 1
        target = thresholds[next_index] if next_index < len(thresholds) else None
        goal_value = values["current_streak"] if key == "streak" else value
        unit_one, unit_many = GOAL_UNITS[key]
        result.append({
            "id": key, "name": translate(name), "description": translate(description),
            "tier": tier, "value": value, "target": target,
            "remaining": max(0, target - value) if target is not None else 0,
            "goalValue": goal_value,
            "goalRemaining": max(0, target - goal_value) if target is not None else 0,
            "goalUnitOne": translate(unit_one), "goalUnitMany": translate(unit_many),
            "isNew": any(str(i) not in seen_tiers for i in range(len(thresholds))
                         if str(i) in saved),
            "isFavorite": favorite == key,
            "tiers": [{"name": translate(TIERS[i]) if len(thresholds) > 1 else translate("Earned"),
                       "target": threshold, "earned": str(i) in saved,
                       "earnedAt": saved.get(str(i))}
                      for i, threshold in enumerate(thresholds)],
        })
    return result, changed
