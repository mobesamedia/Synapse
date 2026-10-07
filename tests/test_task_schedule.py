import sys, unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from task_schedule import normalize_tasks

class CalendarTests(unittest.TestCase):
    def test_daily_rollover_preserves_id_and_unknown_fields(self):
        task={'id':'a','done':True,'repeat':'daily','completed_on':'2026-09-09','custom':12}
        self.assertTrue(normalize_tasks([task],today=date(2026,9,9))[0]['done'])
        result=normalize_tasks([task],today=date(2026,9,15))[0]
        self.assertFalse(result['done']);self.assertEqual(result['id'],'a');self.assertEqual(result['custom'],12)
        self.assertEqual(len(normalize_tasks([task],today=date(2026,10,1))),1)
        self.assertTrue(task['done'])
    def test_weekly_and_selected_weekdays(self):
        task={'done':True,'repeat':'weekly','repeat_anchor':'2026-09-07','completed_on':'2026-09-09'}
        self.assertTrue(normalize_tasks([task],today=date(2026,9,13))[0]['done'])
        self.assertFalse(normalize_tasks([task],today=date(2026,9,14))[0]['done'])
        task.update(repeat='weekdays',repeat_days=[1,5])
        self.assertEqual(normalize_tasks([task],today=date(2026,9,10))[0]['due_on'],'2026-09-11')
    def test_cleanup_only_known_one_time_completions(self):
        tasks=[{'id':'old','done':True},{'id':'today','done':True,'completed_on':'2026-09-09'}, {'id':'remove','done':True,'completed_on':'2026-09-08'}, {'id':'repeat','done':True,'repeat':'daily','completed_on':'2026-09-08'}, {'id':'open','done':False}]
        self.assertEqual(len(normalize_tasks(tasks,today=date(2026,9,9))),5)
        self.assertEqual([t['id'] for t in normalize_tasks(tasks,True,date(2026,9,9))],['old','today','repeat','open'])
    def test_leap_year_and_year_boundary(self):
        for completed,today in [('2024-02-28',date(2024,2,29)),('2026-12-31',date(2027,1,1))]:
            self.assertFalse(normalize_tasks([{'done':True,'repeat':'daily','completed_on':completed}],today=today)[0]['done'])

if __name__=='__main__':unittest.main()
