"""Execute the real XP methods against isolated SQLite review logs."""
import ast
import copy
from datetime import date, datetime, timedelta
from pathlib import Path
import sqlite3
import time
import types
import unittest
from typing import Union

ROOT = Path(__file__).resolve().parents[1]
DAY = date.today()
START = int(datetime.combine(DAY, datetime.min.time()).timestamp() * 1000)

class DB:
    def __init__(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.execute('CREATE TABLE revlog(id INTEGER PRIMARY KEY, time INTEGER, ease INTEGER)')
        self.fail = False
    def first(self, sql, *args):
        if self.fail:
            raise RuntimeError('synthetic database failure')
        return self.conn.execute(sql, args).fetchone()

class Config(dict):
    fail = False
    def __setitem__(self, key, value):
        if self.fail:
            raise RuntimeError('synthetic config failure')
        super().__setitem__(key, copy.deepcopy(value))

class StudyXP(unittest.TestCase):
    def setUp(self):
        self.db = DB()
        self.conf = Config()
        self.mw = types.SimpleNamespace(col=types.SimpleNamespace(db=self.db, conf=self.conf))
        tree = ast.parse((ROOT / 'gamification.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'GamificationManager')
        names = {'credit_study_xp', 'add_xp', 'get_xp_for_level', 'get_remaining_xp'}
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in names]
        ns = dict(mw=self.mw, datetime=datetime, timedelta=timedelta, time=types.SimpleNamespace(time=lambda:(START+86399999)/1000), Union=Union,
                  XP_PER_MINUTE_STUDIED=10, XP_LEVEL_BASE=100, XP_LEVEL_FACTOR=1.065,
                  CONFIG_KEY='xp', _anki_today=lambda: DAY)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), 'gamification.py', 'exec'), ns)
        self.manager_type = ns['GamificationManager']
        self.gm = self.manager()
    def manager(self, data=None):
        gm = self.manager_type()
        gm.data = copy.deepcopy(data or {'level': 1, 'xp': 0, 'last_time_xp_check_day': int(DAY.strftime('%Y%m%d'))})
        gm._get_rollover_hour = lambda: 0
        gm._save_to_json_backup = lambda: None
        gm.get_rank_info_for_level = lambda level: {}
        gm.get_level = lambda: gm.data['level']
        return gm
    def review(self, offset, ms=6000, ease=3):
        self.db.conn.execute('INSERT INTO revlog VALUES (?,?,?)', (START + offset, ms, ease))
    def test_immediate_credit_restart_and_repeat_do_not_duplicate(self):
        self.review(1, 30000)
        self.assertEqual(self.gm.credit_study_xp(START), 5)
        self.assertEqual(self.gm._study_session_xp, 5)
        self.assertEqual(self.gm.credit_study_xp(START), 0)
        restarted = self.manager(self.conf['xp'])
        self.assertEqual(restarted.credit_study_xp(), 0)
        self.assertEqual(restarted.data['xp'], 5)
    def test_fraction_carries_between_sessions(self):
        self.review(1, 3000)
        self.assertEqual(self.gm.credit_study_xp(START), 0)
        self.review(2, 3000)
        self.assertEqual(self.gm.credit_study_xp(START+2), 1)
        self.assertEqual(self.gm._study_session_xp, 1)
    def test_cap_negative_time_and_manual_entries(self):
        self.review(1, 60000)
        self.review(2, -6000)
        self.review(3, 45000, 0)
        self.assertEqual(self.gm.credit_study_xp(START), 7)
        self.assertEqual(self.gm._study_session_xp, 7)
    def test_five_remaining_levels_up_immediately(self):
        self.gm.data['xp'] = 95
        self.review(1, 30000)
        self.gm.credit_study_xp(START)
        self.assertEqual((self.gm.data['level'], self.gm.data['xp']), (2, 0))
    def test_old_finalized_days_not_repaid_and_missed_days_caught_up(self):
        self.review(-86400000, 45000)
        self.review(1, 6000)
        self.assertEqual(self.gm.credit_study_xp(), 1)
        other = self.manager({'level':1, 'xp':0, 'last_time_xp_check_day':int((DAY-timedelta(days=1)).strftime('%Y%m%d'))})
        self.assertEqual(other.credit_study_xp(), 8)
    def test_query_failure_keeps_receipt_retryable(self):
        self.review(1, 30000)
        before = copy.deepcopy(self.gm.data)
        self.db.fail = True
        self.assertEqual(self.gm.credit_study_xp(START), 0)
        self.assertEqual(self.gm.data, before)
        self.db.fail = False
        self.assertEqual(self.gm.credit_study_xp(START), 5)
    def test_save_failure_keeps_xp_and_receipt_together(self):
        self.review(1, 30000)
        before = copy.deepcopy(self.gm.data)
        self.conf['xp'] = before
        self.gm.data = self.conf['xp']  # even a shared config object must remain intact
        self.conf.fail = True
        self.assertEqual(self.gm.credit_study_xp(START), 0)
        self.assertEqual(self.gm.data, before)
        self.assertEqual(self.conf['xp'], before)
        self.conf.fail = False
        self.assertEqual(self.gm.credit_study_xp(START), 5)
    def test_late_reviews_with_older_ids_are_counted(self):
        self.review(10, 6000)
        self.assertEqual(self.gm.credit_study_xp(), 1)
        self.review(5, 6000)
        self.assertEqual(self.gm.credit_study_xp(), 1)
    def test_undo_and_restore_does_not_pay_twice(self):
        self.review(1, 6000)
        self.gm.credit_study_xp()
        self.db.conn.execute('DELETE FROM revlog')
        self.assertEqual(self.gm.credit_study_xp(), 0)
        self.review(1, 6000)
        self.assertEqual(self.gm.credit_study_xp(), 0)
    def test_catchup_not_reported_as_current_session(self):
        self.review(1, 30000)
        self.review(2, 12000)
        self.assertEqual(self.gm.credit_study_xp(START+2), 7)
        self.assertEqual(self.gm._study_session_xp, 2)
        self.gm.credit_study_xp(START+2)
        self.assertEqual(self.gm._study_session_xp, 2)

    def test_rollover_boundary_excludes_already_finalized_early_reviews(self):
        self.gm._get_rollover_hour = lambda: 4
        self.review(3*3600000, 30000)
        self.review(5*3600000, 12000)
        self.assertEqual(self.gm.credit_study_xp(), 2)

    def test_finished_screen_uses_actual_award_and_can_retry(self):
        self.review(1, 60000)
        self.mw._sp_session_start_ms = START
        self.mw.gamification_manager = self.gm
        tree = ast.parse((ROOT / 'deck_overview.py').read_text())
        func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == '_session_summary_inner')
        ns = {'mw':self.mw, '_':lambda text:text, '_palette':lambda night:{}}
        exec(compile(ast.Module(body=[func],type_ignores=[]),'deck_overview.py','exec'),ns)
        html = ns['_session_summary_inner']()
        self.assertIn('+7 XP earned', html)
        self.assertIn('93 XP to next level', html)
        self.assertEqual(self.gm.data['xp'], 7)
        self.assertEqual(ns['_session_summary_inner'](), html)

if __name__ == '__main__':
    unittest.main()
