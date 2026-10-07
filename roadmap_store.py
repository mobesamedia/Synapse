"""Profile-local roadmap persistence. No Anki imports; callers supply the path."""
from contextlib import contextmanager
import json
import math
import os
import re
import sqlite3

try:
    from .workspace_icons import validate_document as validate_icons
except ImportError:
    from workspace_icons import validate_document as validate_icons


def validate(data):
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('maps'), list):
        raise ValueError('Invalid roadmap collection')
    ids = set()
    for doc in data['maps']:
        if not isinstance(doc, dict) or not isinstance(doc.get('id'), str) or not re.fullmatch(r'[-a-zA-Z0-9_]{1,100}', doc['id']) or doc['id'] in ids:
            raise ValueError('Invalid or duplicate roadmap ID')
        ids.add(doc['id'])
        if not isinstance(doc.get('name'), str) or not isinstance(doc.get('objects'), list):
            raise ValueError('Invalid roadmap document')
        validate_icons(doc)
        objects = {}
        for obj in doc['objects']:
            if not isinstance(obj, dict) or not isinstance(obj.get('id'), str) or not re.fullmatch(r'[-a-zA-Z0-9_]{1,100}', obj['id']) or obj['id'] in objects:
                raise ValueError('Invalid object ID')
            objects[obj['id']] = obj
            if obj.get('image') and (not isinstance(obj['image'], str) or not re.fullmatch(r'[a-f0-9]{64}\.(png|jpg)', obj['image'])):
                raise ValueError('Invalid image reference')
            if obj.get('kind') == 'image' and not obj.get('image'):
                raise ValueError('Missing image reference')
            if obj.get('kind') not in ('shape', 'text', 'arrow', 'image', 'icon'):
                raise ValueError('Invalid object kind')
            keys = ('x', 'y', 'w', 'h', 'rotation') if obj['kind'] != 'arrow' else ()
            for key in keys:
                value = obj.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e7:
                    raise ValueError('Invalid geometry')
            if keys and (obj['w'] < 1 or obj['h'] < 1):
                raise ValueError('Invalid dimensions')
        for obj in objects.values():
            if obj['kind'] == 'arrow':
                for key in ('a', 'b'):
                    end = obj.get(key)
                    if not isinstance(end, dict):
                        raise ValueError('Invalid arrow endpoint')
                    if end.get('node'):
                        target = objects.get(end['node'])
                        if not target or target['kind'] == 'arrow' or end.get('side') not in ('top', 'right', 'bottom', 'left'):
                            raise ValueError('Invalid connection')
                    else:
                        for coord in ('x', 'y'):
                            value = end.get(coord)
                            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e7:
                                raise ValueError('Invalid endpoint coordinates')
    if data.get('active') is not None and data['active'] not in ids:
        raise ValueError('Unknown active roadmap')
    return data


@contextmanager
def _connect(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    con = sqlite3.connect(path, timeout=2)
    try:
        with con:
            con.execute('CREATE TABLE IF NOT EXISTS roadmaps (id TEXT PRIMARY KEY, body TEXT NOT NULL)')
            con.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
            yield con
    finally:
        con.close()


def load(path):
    with _connect(path) as con:
        maps = [json.loads(row[0]) for row in con.execute('SELECT body FROM roadmaps ORDER BY rowid')]
        row = con.execute("SELECT value FROM settings WHERE key='active'").fetchone()
    active = row[0] if row and any(m['id'] == row[0] for m in maps) else (maps[0]['id'] if maps else None)
    return validate({'version': 1, 'active': active, 'maps': maps})


def save(path, data):
    validate(data)
    # One transaction: document updates, deletions, and selected document agree.
    with _connect(path) as con:
        old = dict(con.execute('SELECT id, body FROM roadmaps'))
        current = set()
        for doc in data['maps']:
            body = json.dumps(doc, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
            current.add(doc['id'])
            if old.get(doc['id']) != body:
                con.execute('INSERT OR REPLACE INTO roadmaps VALUES (?, ?)', (doc['id'], body))
        for key in old.keys() - current:
            con.execute('DELETE FROM roadmaps WHERE id=?', (key,))
        con.execute("INSERT OR REPLACE INTO settings VALUES ('active', ?)", (data.get('active'),))


def is_first_use(path):
    """Only offer starter content before any collection has been saved.

    The existing active setting survives an empty collection, so deliberately
    deleted documents never cause a tutorial to reappear. Read failures must
    propagate to the host's read-only barrier.
    """
    with _connect(path) as con:
        return (con.execute("SELECT 1 FROM settings WHERE key='active'").fetchone() is None
                and con.execute('SELECT 1 FROM roadmaps LIMIT 1').fetchone() is None)
