"""Deferred WebChannel actions; only read-only Anki queries and browser navigation."""
import json
from urllib.parse import unquote
from . import workspace_links as links
from .workspace_strings import _


def open_link(parent, value):
    import aqt
    from aqt.operations import QueryOp
    from aqt.utils import showWarning
    from aqt.qt import sip
    if getattr(parent,'_workspace_link_opening',False):return
    link=links.clean_link(value)
    collection=aqt.mw.col
    parent._workspace_link_opening=True
    def active():
        return not sip.isdeleted(parent) and aqt.mw is not None and aqt.mw.col is collection
    def done(target):
        parent._workspace_link_opening=False
        if not active():return
        if target is None:
            showWarning(_('This link was not found in this collection. Use Link Card to choose a replacement. The map has not been changed.'),parent=parent)
            return
        browser=aqt.dialogs.open('Browser',aqt.mw)
        def navigate():
            if not active():return
            try:
                # Browser.search_for() explicitly requires pending editor changes
                # to be flushed by the caller. Never discard a user's field edit.
                if target.get('cid') and browser.table.is_notes_mode():
                    browser.table.toggle_state(False,target['search'])
                    switch=browser._switch
                    blocked=switch.blockSignals(True)
                    try:switch.setChecked(False)
                    finally:switch.blockSignals(blocked)
                browser.search_for(target['search'])
            except Exception as error:
                if active():showWarning(str(error),parent=parent)
        editor=getattr(browser,'editor',None)
        if editor:
            save=getattr(editor,'call_after_note_saved',None) or editor.saveNow
            save(navigate)
        else:navigate()
    def failed(error):
        parent._workspace_link_opening=False
        if active():showWarning(str(error),parent=parent)
    try:
        QueryOp(parent=parent,op=lambda col:links.resolve(col,link) if col is collection else None,success=done).failure(failed).run_in_background()
    except Exception as error:
        failed(error)


def action(panel,command):
    if not panel.web_view or panel._unload_in_progress:return
    if getattr(panel,'_workspace_link_busy',False):return
    panel._workspace_link_busy=True
    web=panel.web_view;generation=panel._page_generation;request=None
    def send(value):
        if panel.web_view is web and panel._page_generation==generation:
            web.page().runJavaScript('window.__workspaceLinksPicked && window.__workspaceLinksPicked('+json.dumps({'requestId':request,'links':value},ensure_ascii=True)+');')
    try:
        name,raw=command.split(':',1)
        if len(raw)>60000:raise ValueError('Invalid link request')
        payload=json.loads(unquote(raw))
        if name=='anki-open':open_link(panel,links.clean_link(payload))
        elif name=='anki-links':
            request=payload.get('requestId')
            if not isinstance(request,str) or len(request)>100:raise ValueError('Invalid request')
            from .workspace_link_dialog import LinkDialog
            dialog=LinkDialog(panel,links.clean_links(payload.get('links',[])),str(payload.get('seed',''))[:160])
            dialog.exec()
            send(dialog.result_links)
            if dialog.open_after:
                from aqt.qt import QTimer
                QTimer.singleShot(0,lambda:open_link(panel,dialog.open_after))
    except Exception as error:
        from aqt.utils import showWarning
        showWarning(_('Could not open Anki links.')+' '+str(error),parent=panel)
        send(None)
    finally:
        panel._workspace_link_busy=False
