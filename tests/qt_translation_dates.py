"""Real Qt study-plan and calendar localization, no real profile writes."""
import sys,types,importlib
from pathlib import Path
from datetime import date,timedelta
from aqt.qt import QApplication,QDate,QLabel,QDialogButtonBox
errors=[]
sys.excepthook=lambda kind,value,trace:errors.append(str(value))
app=QApplication([])
pkg=types.ModuleType('calendar_translation_fixture');pkg.__path__=[str(Path(__file__).resolve().parents[1])];sys.modules[pkg.__name__]=pkg
loc=importlib.import_module(pkg.__name__+'.locales')
m=importlib.import_module(pkg.__name__+'.configuration')
for lang in ('en','de','es','ko','pt','fr','vi','zh','hi','pl'):
 loc.USER_LANG=lang
 calendar=m.StudyPlanCalendarWidget(True)
 assert calendar.locale().name().startswith(lang),calendar.locale().name()
 calendar.setSelectedDate(QDate(2026,9,29));calendar.show();app.processEvents();calendar.close()
 today=date.today();plan={(today+timedelta(days=i)).strftime('%Y%m%d'):{'User subject':{'target_seconds':1200}} for i in (-1,0,1)}
 dialog=m.StudyPlanTimelineDialog(plan);dialog.show();app.processEvents()
 assert dialog.windowTitle()==loc._('Study Plan Timeline')
 assert dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Close).text()==loc._('Close')
 assert any(label.text()=='User subject' for label in dialog.findChildren(QLabel))
 if lang in ('ko','pl'):dialog.grab().save('/tmp/study-plan-'+lang+'.png')
 dialog.close()
assert not errors,errors
print('PASS Qt calendar and timeline in 10 languages; user subject unchanged')
