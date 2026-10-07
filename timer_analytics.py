"""Read-only aggregation of Anki's existing answer times; no study hooks."""
import time

EXPANDED_KEY = "synapsepro_timer_analytics_expanded"


def collect_analytics(col, now=None):
    now = time.time() if now is None else now
    cutoff = getattr(col.sched, "day_cutoff", None)
    if cutoff is None:
        cutoff = getattr(col.sched, "dayCutoff", None)
    if callable(cutoff):
        cutoff = cutoff()
    start = (int(cutoff) if cutoff else int(now)) - 30 * 86400
    # Original deck for cards temporarily moved into filtered decks. Manual
    # rescheduling entries have no learning duration and must not count.
    rows = col.db.all("""
        SELECT CASE WHEN c.odid != 0 THEN c.odid ELSE c.did END,
               sum(r.time), count(*)
        FROM revlog r JOIN cards c ON c.id = r.cid
        WHERE r.id >= ? AND r.id <= ? AND r.type IN (0, 1, 2, 3)
          AND r.ease > 0 AND r.time > 0
        GROUP BY 1
    """, start * 1000, int(now * 1000))
    names = {int(d.id): d.name for d in col.decks.all_names_and_ids()}
    nodes = {}
    for did, milliseconds, answers in rows:
        name = names.get(int(did))
        if not name:
            continue
        parts = name.split("::")
        for depth in range(1, len(parts) + 1):
            path = "::".join(parts[:depth])
            node = nodes.setdefault(path, {"key": path, "name": parts[depth-1],
                "milliseconds": 0, "answers": 0, "ownMilliseconds": 0, "children": []})
            node["milliseconds"] += int(milliseconds)
            node["answers"] += int(answers)
            if depth == len(parts):
                node["ownMilliseconds"] += int(milliseconds)
    roots = []
    for path, node in nodes.items():
        if "::" in path:
            nodes[path.rsplit("::", 1)[0]]["children"].append(node)
        else:
            roots.append(node)
    def sort_tree(items):
        items.sort(key=lambda n: (-n["milliseconds"], n["name"].casefold()))
        for node in items:
            sort_tree(node["children"])
    sort_tree(roots)
    expanded = col.get_config(EXPANDED_KEY, [])
    if not isinstance(expanded, list):
        expanded = []
    return {"decks": roots, "milliseconds": sum(n["milliseconds"] for n in roots),
            "answers": sum(n["answers"] for n in roots),
            "expanded": [k for k in expanded if isinstance(k, str) and k in nodes]}


def save_expanded(col, keys):
    if isinstance(keys, list):
        col.set_config(EXPANDED_KEY, list(dict.fromkeys(
            key for key in keys if isinstance(key, str) and len(key) <= 2048))[:500])
