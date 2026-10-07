"""Synthetic history and profile backups only; never opens a real Anki profile."""
import ast
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import time
import types
import unittest
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from achievements import ReviewHistory, history_metrics, update_achievements
from developer_console import _achievement_gallery_items, _achievement_preview_items


class DB:
    def __init__(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE revlog (id INTEGER PRIMARY KEY, ease INTEGER)')
        self.queries = []

    def add(self, dt, ease=3):
        self.db.execute('INSERT INTO revlog VALUES (?, ?)', (int(dt.timestamp()*1000), ease))

    def all(self, sql, *args):
        self.queries.append(args)
        return self.db.execute(sql, args).fetchall()


class Achievements(unittest.TestCase):
    today = date(2026, 9, 9)

    def test_all_tiers_and_permanent_unlocks(self):
        counts = {self.today-timedelta(days=i): 300 for i in range(365)}
        data = {'xp': 42, 'custom': {'keep': True}}
        result, changed = update_achievements(data, counts, self.today)
        self.assertTrue(changed)
        self.assertEqual([b['tier'] for b in result[:3]], [3, 3, 3])
        self.assertEqual(len(data['achievements']['earned']['reviews']), 4)
        saved = json.loads(json.dumps(data))
        result, changed = update_achievements(saved, {}, self.today+timedelta(days=5))
        self.assertFalse(changed)
        self.assertEqual([b['tier'] for b in result[:3]], [3, 3, 3])
        self.assertTrue(all(b['target'] is None for b in result[:3]))
        self.assertEqual(saved['custom'], {'keep': True})
        self.assertEqual(saved['xp'], 42)

    def test_challenges_once_per_day_and_profile_isolation(self):
        data = {}
        for i in range(5):
            day = self.today + timedelta(days=i)
            update_achievements(data, {}, day, True)
            _, changed = update_achievements(data, {}, day, True)
            self.assertFalse(changed)
        result, _ = update_achievements(json.loads(json.dumps(data)), {}, self.today)
        self.assertEqual(result[3]['tier'], 0)
        self.assertEqual(result[3]['remaining'], 20)
        other, _ = update_achievements({}, {}, self.today)
        self.assertEqual(other[3]['value'], 0)

    def test_new_markers_dates_and_existing_profile_migration(self):
        old_day = (self.today - timedelta(days=10)).isoformat()
        data = {'achievements': {
            'earned': {'reviews': {'0': old_day}},
            'challenge_days': [],
        }}
        result, changed = update_achievements(data, {self.today: 500}, self.today)
        reviews = result[1]
        self.assertTrue(changed)
        self.assertFalse(reviews['isNew'])
        self.assertEqual(reviews['tiers'][0]['earnedAt'], old_day)
        self.assertEqual(data['achievements']['seen']['reviews'], ['0'])

        result, changed = update_achievements(data, {self.today: 5000}, self.today)
        reviews = result[1]
        self.assertTrue(changed)
        self.assertTrue(reviews['isNew'])
        self.assertEqual(reviews['tiers'][1]['earnedAt'], self.today.isoformat())

    def test_comeback_requires_seven_missing_days_and_three_consecutive_days(self):
        start = self.today-timedelta(days=10)
        counts = {start: 1, start+timedelta(days=8): 1, start+timedelta(days=9): 1}
        self.assertEqual(history_metrics(counts, self.today)['comeback'], 2)
        counts[self.today] = 1
        self.assertEqual(history_metrics(counts, self.today)['comeback'], 3)
        self.assertEqual(history_metrics(counts, self.today+timedelta(days=50))['comeback'], 3)
        # A first ever session and a six-day break are not a comeback.
        for offset in (0, 7):
            counts = {start+timedelta(days=offset+i): 1 for i in range(3)}
            counts[start] = 1
            self.assertEqual(history_metrics(counts, self.today)['comeback'], 0)

    def test_unfinished_comeback_expires_and_longest_streak_survives_break(self):
        counts = {self.today-timedelta(days=i): 1 for i in (12, 4, 3)}
        self.assertEqual(history_metrics(counts, self.today)['comeback'], 0)
        self.assertEqual(history_metrics(counts, self.today)['streak'], 2)
        self.assertEqual(history_metrics(counts, self.today)['current_streak'], 0)

    def test_next_streak_goal_uses_current_run_not_historical_record(self):
        counts = {self.today-timedelta(days=i): 1 for i in range(12, 19)}
        counts.update({self.today-timedelta(days=i): 1 for i in range(2)})
        result, _ = update_achievements({}, counts, self.today)
        streak = result[0]
        self.assertEqual(streak['value'], 7)
        self.assertEqual(streak['goalValue'], 2)
        self.assertEqual(streak['target'], 30)
        self.assertEqual(streak['goalRemaining'], 28)

    def test_developer_console_badge_scenarios_are_synthetic(self):
        nearby = _achievement_preview_items('near')
        self.assertEqual(nearby[1]['goalRemaining'], 20)
        comeback = _achievement_preview_items('comeback')
        self.assertEqual(comeback[4]['goalValue'], 2)
        tier = _achievement_preview_items('tier')
        self.assertEqual(tier[0]['tier'], 1)
        complete = _achievement_preview_items('complete')
        self.assertTrue(all(item['target'] is None for item in complete))
        for stage, tier in (("locked", -1), ("bronze", 0), ("silver", 1),
                            ("gold", 2), ("diamond", 3)):
            gallery = _achievement_gallery_items(stage)
            self.assertEqual(len(gallery), 5)
            self.assertTrue(all(item['tier'] == tier for item in gallery[:4]))
            self.assertEqual(gallery[4]['tier'], -1 if stage == "locked" else 0)

    def test_editable_achievement_assets_are_complete(self):
        expected = {
            key: ('locked', 'bronze', 'silver', 'gold', 'diamond')
            for key in ('streak', 'reviews', 'days', 'challenges')
        }
        expected['comeback'] = ('locked', 'earned')
        for key, variants in expected.items():
            for variant in variants:
                path = ROOT/'media'/'Achievements'/key/f'{variant}.svg'
                source = path.read_text(encoding='utf-8')
                self.assertIn('viewBox="0 0 120 120"', source)
                self.assertTrue(ET.fromstring(source).tag.endswith('svg'))

    def test_cached_incremental_history_sync_and_undo(self):
        db = DB()
        db.add(datetime(2026, 9, 8, 10))
        db.add(datetime(2026, 9, 9, 3, 59))
        db.add(datetime(2026, 9, 9, 4))
        db.add(datetime(2026, 9, 9, 5), ease=0)
        history = ReviewHistory()
        self.assertEqual(history.read(db, self.today, 4), {date(2026,9,8):2, self.today:1})
        history.read(db, self.today, 4)
        self.assertEqual(len(db.queries), 1)
        db.add(datetime(2026, 9, 9, 6))
        history.invalidate()
        self.assertEqual(history.read(db, self.today, 4)[self.today], 2)
        self.assertGreater(db.queries[-1][1], 0)
        db.db.execute('DELETE FROM revlog WHERE id = ?', (int(datetime(2026,9,9,6).timestamp()*1000),))
        history.invalidate()
        self.assertEqual(history.read(db, self.today, 4)[self.today], 1)
        db.add(datetime(2026, 8, 1, 12))
        history.invalidate(full=True)
        self.assertIn(date(2026,8,1), history.read(db, self.today, 4))
        self.assertEqual(db.queries[-1][1], 0)
        # Future Anki days are not counted, but appear when the day rolls over.
        db.add(datetime(2026, 9, 10, 5))
        history.invalidate()
        self.assertNotIn(date(2026,9,10), history.read(db, self.today, 4))
        self.assertIn(date(2026,9,10), history.read(db, self.today+timedelta(days=1), 4))

    @unittest.skipUnless(hasattr(time, 'tzset'), 'needs local timezone support')
    def test_dst_calendar_bucketing(self):
        previous = os.environ.get('TZ')
        try:
            os.environ['TZ'] = 'Europe/Berlin'
            time.tzset()
            for day in (date(2026,3,29), date(2026,10,25)):
                db = DB()
                db.add(datetime.combine(day, datetime.min.time()).replace(hour=3, minute=59))
                db.add(datetime.combine(day, datetime.min.time()).replace(hour=4))
                counts = ReviewHistory().read(db, day, 4)
                self.assertEqual(counts, {day-timedelta(days=1):1, day:1})
        finally:
            if previous is None:
                os.environ.pop('TZ', None)
            else:
                os.environ['TZ'] = previous
            time.tzset()

    def test_actual_backup_roundtrip_and_failed_replace(self):
        tree = ast.parse((ROOT/'gamification.py').read_text())
        source = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'GamificationManager')
        names = {'_save_to_json_backup', '_load_from_json_backup'}
        methods = [n for n in source.body if isinstance(n, ast.FunctionDef) and n.name in names]
        import typing
        namespace = {'json':json, 'os':os, 'Optional':typing.Optional, 'Dict':typing.Dict, 'ADDON_NAME':'test'}
        cls = ast.ClassDef(name='Backup', bases=[], keywords=[], body=methods, decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), 'backup', 'exec'), namespace)
        with tempfile.TemporaryDirectory() as directory:
            backup = namespace['Backup']()
            backup._get_profile_data_path = lambda: str(Path(directory)/'gamification.json')
            backup.data = {'xp':44}
            update_achievements(backup.data, {self.today:500}, self.today, True)
            backup._save_to_json_backup()
            expected = backup._load_from_json_backup()
            self.assertEqual(expected, backup.data)
            backup.data['xp'] = 99
            with patch.object(os, 'replace', side_effect=OSError('simulated interruption')):
                backup._save_to_json_backup()
            self.assertEqual(backup._load_from_json_backup(), expected)


if __name__ == '__main__':
    unittest.main()
