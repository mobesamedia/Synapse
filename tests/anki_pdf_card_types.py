"""Run with Anki's Python runtime; uses only a temporary collection."""
import sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from anki.collection import Collection, AddNoteRequest
from pdf_card_types import resolve, validate
with tempfile.TemporaryDirectory(prefix='synapse-pdf-types-') as tmp:
 col=Collection(str(Path(tmp)/'collection.anki2'))
 try:
  before=col.models.all()
  undo=col.add_custom_undo_entry('PDF types test')
  notes=[]
  for kind,front,back in [('basic','Question','Answer'),('reversed','A','B'),('cloze','{{c1::One}} and {{c2::two}} plus {{c1::another}}','Extra')]:
   validate(kind,front,back)
   model=resolve(col,kind);assert resolve(col,kind)['id']==model['id']
   note=col.new_note(model);note.fields[:2]=[front,back];notes.append(note)
  col.add_notes([AddNoteRequest(note=n,deck_id=1) for n in notes])
  assert [len(n.cards()) for n in notes]==[1,2,2]
  assert all(n.cards()[0].question() for n in notes)
  col.merge_undo_entries(undo);col.undo()
  assert col.db.scalar('select count(*) from notes')==0
  assert col.models.all()==before
  for kind,front,back in [('cloze','No gaps',''),('reversed','A',''),('unknown','A','B')]:
   try:validate(kind,front,back)
   except ValueError:pass
   else:raise AssertionError(kind)
  print('PASS actual Anki stock types: 1 Basic, 2 reversed, 2 Cloze cards; templates render; one undo; invalid input rejected')
 finally:col.close()

# Exercise the actual transaction callback, including rollback after deck creation.
import ast, types, html
root=Path(__file__).resolve().parents[1]
pkg=types.ModuleType('pdf_creator_fixture');pkg.__path__=[str(root)];sys.modules[pkg.__name__]=pkg
module=ast.parse((root/'notebook_sidebar.py').read_text())
fn=next(n for n in ast.walk(module) if isinstance(n,ast.FunctionDef) and n.name=='create_batch')
with tempfile.TemporaryDirectory(prefix='synapse-pdf-batch-') as tmp:
 col=Collection(str(Path(tmp)/'collection.anki2'))
 try:
  cards=[dict(type='basic',front='A',back='B',include_source=True,pages=[1]),dict(type='cloze',front='{{c1::a}} {{c2::b}}',back='Extra',include_source=False,pages=[])]
  env={'__package__':pkg.__name__,'cards':cards,'undo_label':'PDF batch test','NotebookPanel':types.SimpleNamespace(_pdf_text_to_html=html.escape),'_pdf_source_html':lambda *a:'<small>source</small>','source_filename':'test.pdf','pdf_id':'','deck_name':'PDF Test','AddNoteRequest':AddNoteRequest}
  exec(compile(ast.Module(body=[fn],type_ignores=[]),'pdf-batch','exec'),env)
  env['create_batch'](col)
  assert col.db.scalar('select count(*) from cards')==3
  assert '<small>source</small>' in col.db.scalar('select flds from notes order by id limit 1')
  col.undo();assert col.db.scalar('select count(*) from notes')==0
  class FailAdd:
   def __getattr__(self,key):return getattr(col,key)
   def add_notes(self,*a,**kw):raise RuntimeError('synthetic failure')
  try:env['create_batch'](FailAdd())
  except RuntimeError:pass
  else:raise AssertionError('expected failure')
  assert col.decks.id_for_name('PDF Test') is None
  assert col.db.scalar('select count(*) from notes')==0
  print('PASS real batch transaction: source field, mixed types, undo and failure rollback')
 finally:col.close()
