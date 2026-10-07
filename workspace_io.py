"""Native workspace file actions. Always called outside a WebChannel callback."""
import json
from pathlib import Path
from . import workspace_assets as assets
from .locales import _


def image_folder():
    from aqt import mw
    if not mw or not mw.pm or not mw.pm.profileFolder():
        raise ValueError('No Anki profile is open.')
    return Path(mw.pm.profileFolder())/'SynapsePro_Data'/'workspace_images'


def enabled_tools():
    from .workspace_preferences import enabled
    return enabled('maps')


def boot_script():
    from .workspace_strings import translations
    return ('window.__WORKSPACE_I18N__='+json.dumps(translations())+';'
            'window.__WORKSPACE_TOOLS__='+json.dumps(enabled_tools())+';'
            'window.__WORKSPACE_IMAGE_BASE__='+json.dumps(image_folder().as_uri()+'/')+';')


def action(panel, command):
    from aqt.qt import QFileDialog
    if not panel.web_view or panel._unload_in_progress or getattr(panel, '_workspace_file_busy', False):
        return
    panel._workspace_file_busy = True
    asynchronous = False
    web = panel.web_view
    generation = panel._page_generation
    def send(name, data):
        if panel.web_view is web and panel._page_generation == generation:
            web.page().runJavaScript('window.'+name+' && window.'+name+'('+json.dumps(data, ensure_ascii=True)+');')
    try:
        folder = image_folder()
        if command == 'image-add':
            path, _filter = QFileDialog.getOpenFileName(panel, _('Add image'), '', 'Images (*.png *.jpg *.jpeg *.webp)')
            send('__workspaceImageAdded', assets.prepare_image(path, folder) if path else None)
        elif command == 'workspace-import':
            path, _filter = QFileDialog.getOpenFileName(panel, _('Import'), '', 'JSON (*.json)')
            if not path:
                return
            if Path(path).stat().st_size > assets.MAX_BUNDLE_BYTES:
                raise ValueError('File exceeds 64 MB.')
            payload = json.loads(Path(path).read_text(encoding='utf-8'))
            if panel.current_tool == 'roadmap':
                from . import roadmap_store
                roadmap_store.validate(payload)
                for doc in payload['maps']:
                    doc['assets'] = payload.get('assets', doc.get('assets', {}))
                    clean = assets.import_bundle(doc, folder)
                    doc.clear()
                    doc.update(clean)
                payload.pop('assets', None)
            else:
                if isinstance(payload, dict) and not isinstance(payload.get('nodes'), list):
                    wrapped = next((value for value in payload.values() if isinstance(value, dict) and isinstance(value.get('nodes'), list)), None)
                    if wrapped is not None:
                        payload = wrapped
                if not isinstance(payload, dict) or not isinstance(payload.get('nodes'), list):
                    raise ValueError('Invalid mindmap file.')
                payload = assets.import_bundle(payload, folder)
            from .workspace_links import clean_links
            documents=payload['maps'] if panel.current_tool=='roadmap' else [payload]
            for document in documents:
                for obj in document.get('objects',document.get('nodes',[])):
                    if 'ankiLinks' in obj:obj['ankiLinks']=clean_links(obj['ankiLinks'])
            send('__workspaceImported', payload)
        elif command in ('workspace-export', 'roadmap-export'):
            def export(document):
                try:
                    if not document or panel.web_view is not web or panel._page_generation != generation:
                        return
                    payload = assets.export_bundle(document, folder)
                    if panel.current_tool == 'roadmap':
                        payload = {'version':1, 'active':document['id'], 'maps':[payload]}
                    path, _filter = QFileDialog.getSaveFileName(panel, _('Export'), 'FreeMap.json' if panel.current_tool=='roadmap' else 'MindMap.json', 'JSON (*.json)')
                    if path:
                        assets.atomic_write(path, json.dumps(payload, ensure_ascii=False, separators=(',',':')).encode('utf-8'))
                except Exception as error:
                    send('__workspaceError', _('Export failed.')+' '+str(error))
                finally:
                    panel._workspace_file_busy = False
            asynchronous = True
            web.page().runJavaScript('window.__workspaceDocument && window.__workspaceDocument()', export)
    except Exception as error:
        send('__workspaceError', _('Image or import failed.')+' '+str(error))
        send('__workspaceImageAdded', None)
        asynchronous = False
    finally:
        if not asynchronous:
            panel._workspace_file_busy = False
