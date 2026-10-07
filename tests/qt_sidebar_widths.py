"""Native Qt separator drags and session-only per-tool width restoration."""
import importlib,sys,time,types
from pathlib import Path
from PyQt6 import QtCore,QtWidgets,QtTest,QtGui
app=QtWidgets.QApplication(['sidebar-widths-test'])
app.setQuitOnLastWindowClosed(False)
qt=types.ModuleType('aqt.qt')
for module in (QtCore,QtWidgets):
 for name in dir(module):setattr(qt,name,getattr(module,name))
sys.modules['aqt.qt']=qt
pkg=types.ModuleType('sidebar_width_fixture');pkg.__path__=[str(Path(__file__).resolve().parents[1])];sys.modules[pkg.__name__]=pkg
widths=importlib.import_module(pkg.__name__+'.sidebar_widths')

def spin():
 for _ in range(25):app.processEvents();time.sleep(.005)
class Content(QtWidgets.QWidget):
 def __init__(self, preferred=320):
  super().__init__();self.preferred=preferred
 def sizeHint(self):return QtCore.QSize(self.preferred,400)
def window():
 w=QtWidgets.QMainWindow();w.resize(1200,750);center=QtWidgets.QWidget();center.setMinimumWidth(200);w.setCentralWidget(center);w.show();spin();return w
def dock(w,key,tracked=True,preferred=320):
 d=QtWidgets.QDockWidget(key,w);d.setTitleBarWidget(QtWidgets.QWidget());d.setMinimumSize(300,0);d.setWidget(Content(preferred));d.hide()
 if tracked:widths.attach(w,d,key)
 w.addDockWidget(QtCore.Qt.DockWidgetArea.RightDockWidgetArea,d);return d
def drag(w,d,delta):
 start=QtCore.QPoint(d.x()-3,d.y()+min(200,d.height()//2))
 before=d.width()
 QtTest.QTest.mousePress(w,QtCore.Qt.MouseButton.LeftButton,pos=start)
 for i in range(1,11):
  pos=start+QtCore.QPoint(round(delta*i/10),0)
  event=QtGui.QMouseEvent(QtCore.QEvent.Type.MouseMove,QtCore.QPointF(pos),QtCore.QPointF(w.mapToGlobal(pos)),QtCore.Qt.MouseButton.NoButton,QtCore.Qt.MouseButton.LeftButton,QtCore.Qt.KeyboardModifier.NoModifier)
  app.sendEvent(w,event);app.processEvents()
 QtTest.QTest.mouseRelease(w,QtCore.Qt.MouseButton.LeftButton,pos=start+QtCore.QPoint(delta,0));spin()
 assert d.width()!=before,('native separator did not move',before,d.width(),start)
 assert d._synapse_width.widths[d._synapse_width.feature]==d.width(),('drag not recorded',d._synapse_width.widths,d.width())

w=window();baseline=400
# Different web-content hints must not determine the starting width.
for key,hint in [('gamification',300),('ai',800),('website',900),('notebook',640),('mindmap',1000)]:
 probe=dock(w,key,preferred=hint);probe.show();spin()
 assert probe.width()==400,(key,hint,probe.width())
 probe.hide();w.removeDockWidget(probe);probe.deleteLater();spin()
a=dock(w,'mindmap');b=dock(w,'gamification');a.show();spin();assert a.width()==baseline,(a.width(),baseline)
drag(w,a,-330);wide=a.width();a.hide();b.show();spin();assert b.width()==baseline,(b.width(),baseline)
drag(w,b,-45);small=b.width();b.hide();a.show();spin();assert a.width()==wide,(a.width(),wide)
# Internal tools share the group's width and must not trigger a restore.
widths.select(a,'roadmap');assert not a._synapse_width.timer.isActive();spin();assert a.width()==wide
drag(w,a,-40);wide=a.width();road=wide;widths.select(a,'mindmap');spin();assert a.width()==wide
# Main-window resizes must not replace the manually selected width.
w.resize(680,750);spin();assert a._synapse_width.widths['maps']==wide
a.hide();a.show();spin();assert a.width()<=w.width()-200
w.resize(1200,750);spin();a.hide();a.show();spin();assert a.width()==wide
# A main-window resize during a held mouse press is not a splitter preference.
start=QtCore.QPoint(20,20)
QtTest.QTest.mousePress(w,QtCore.Qt.MouseButton.LeftButton,pos=start)
w.resize(1000,750);spin()
QtTest.QTest.mouseRelease(w,QtCore.Qt.MouseButton.LeftButton,pos=start);spin()
assert a._synapse_width.widths['maps']==wide
w.resize(1200,750);spin()
# Automatic area changes never teach the neighboring feature a new width.
b.show();spin();assert a._synapse_width.widths['maps']==wide
b.hide();a.hide();a.show();spin();assert a.width()==wide
# Moving the content into an enlarged/embedded view and back keeps preferences.
flag=[True];a._synapse_width.suspended=lambda:flag[0];a.hide();widths.select(a,'roadmap');spin();flag[0]=False;a.show();spin();assert a.width()==road
# Floating geometry is independent of the docked width.
a.setFloating(True);spin();a.resize(850,500);spin();assert a._synapse_width.widths['maps']==road
a.setFloating(False);spin();assert a.width()==road,(a.width(),road)
a.hide();b.show();spin();assert b.width()==small
# Left-side docks use the same per-feature restoration.
b.hide();w.removeDockWidget(b);w.addDockWidget(QtCore.Qt.DockWidgetArea.LeftDockWidgetArea,b)
b.show();spin();assert b.width()==small
# Destroying the dock resets the session's remembered width.
b.hide();w.removeDockWidget(b);b.deleteLater();app.processEvents();fresh=dock(w,'gamification');fresh.show();spin();assert fresh.width()==baseline
# Notebook, To-do and PDF likewise share one group.
fresh.hide();notes=dock(w,'notebook');notes.show();spin();assert notes.width()==400
drag(w,notes,-100);note_width=notes.width()
for tool in ['todo','pdf','notebook']:
 widths.select(notes,tool);assert not notes._synapse_width.timer.isActive();spin();assert notes.width()==note_width
notes.hide()
# A pending restore can be safely destroyed before its timer runs.
last=dock(w,'pending');last.show();last.deleteLater();QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete);spin()
w.close();w.deleteLater();spin()
print('PASS native splitter drags; independent docks; shared internal tabs; 400 px start despite different content hints; window shrink; embedded/floating return; session reset; pending deletion')
