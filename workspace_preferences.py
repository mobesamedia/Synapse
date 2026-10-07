"""Small profile-local tool visibility dialog, independent of general settings."""
import json
from pathlib import Path
from .workspace_assets import atomic_write
from .workspace_strings import _

GROUPS = {'maps': ('mindmap', 'roadmap'), 'notebook': ('notebook', 'todo', 'pdf')}
LABELS = {'mindmap':'MindMap', 'roadmap':'FreeMap', 'notebook':'Notebook', 'todo':'To-Do', 'pdf':'PDF'}

def path():
    from aqt import mw
    folder = mw.pm.profileFolder()
    if not folder:
        raise ValueError('No Anki profile is open.')
    return Path(folder)/'SynapsePro_Data'/'workspace_preferences.json'

def enabled(group):
    try:
        from . import addon_settings
    except ImportError:
        addon_settings = {}
    result = {key: bool(addon_settings.get('workspace_'+key+'_tab', True)) for key in GROUPS[group]}
    try:
        data=json.loads(path().read_text(encoding='utf-8'))
        result.update({key:data[key] for key in result if isinstance(data.get(key),bool)})
    except (OSError, ValueError, AttributeError):
        pass
    if not any(result.values()):
        result[GROUPS[group][0]]=True
    return result

def show(parent, group):
    from aqt.qt import QDialog, QVBoxLayout, QLabel, QCheckBox, QDialogButtonBox
    from aqt.utils import showWarning
    dialog=QDialog(parent)
    dialog.setWindowTitle(_('Workspace settings'))
    from aqt import mw
    from .theme import dialog_palette
    if mw and mw.pm.night_mode():
        c = dialog_palette(True)
        dialog.setStyleSheet(f"""
            QDialog {{background:{c['bg']};color:{c['text']};}}
            QLabel,QCheckBox {{color:{c['text']};}}
            QPushButton {{background:{c['grey_light']};color:{c['text']};border:0;border-radius:6px;padding:7px 14px;}}
            QPushButton:hover {{background:{c['grey_dark']};}}
            QPushButton:disabled {{color:{c['text_faint']};}}
            QPushButton:focus {{border:1px solid {c['blue_accent']};}}
        """)
    layout=QVBoxLayout(dialog)
    info=QLabel(_('Choose which tabs are visible. Hiding a tab does not delete its data.'))
    info.setWordWrap(True)
    layout.addWidget(info)
    checks={}
    for key, value in enabled(group).items():
        check=QCheckBox(_(LABELS[key]));check.setChecked(value)
        checks[key]=check;layout.addWidget(check)
    buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
    layout.addWidget(buttons)
    save=buttons.button(QDialogButtonBox.StandardButton.Save)
    for check in checks.values():
        check.toggled.connect(lambda: save.setEnabled(any(c.isChecked() for c in checks.values())))
    def accept():
        try:
            target=path()
            data=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
            if not isinstance(data,dict): raise ValueError('Invalid workspace preferences')
            data.update({key:c.isChecked() for key,c in checks.items()})
            atomic_write(target,json.dumps(data).encode('utf-8'))
        except Exception as error:
            showWarning(str(error),parent=dialog)
            return
        dialog.accept()
    buttons.accepted.connect(accept)
    buttons.rejected.connect(dialog.reject)
    dialog.setMinimumWidth(340)
    return bool(dialog.exec())


def save(group, values):
    """Validate the complete group before replacing its profile-local preferences."""
    if not isinstance(values, dict) or set(values) != set(GROUPS[group]):
        raise ValueError('Invalid workspace preferences')
    if any(type(v) is not bool for v in values.values()) or not any(values.values()):
        raise ValueError('Keep at least one tab visible.')
    target = path()
    data = json.loads(target.read_text(encoding='utf-8')) if target.exists() else {}
    if not isinstance(data, dict):
        raise ValueError('Invalid workspace preferences')
    data.update(values)
    atomic_write(target, json.dumps(data).encode('utf-8'))


def popup_script(group):
    from aqt import mw
    from .theme import dialog_palette
    c = dialog_palette(bool(mw.pm.night_mode()))
    payload = dict(group=group, values=enabled(group), labels={k: _(LABELS[k]) for k in GROUPS[group]},
                   title=_('Workspace settings'), description=_('Choose which tabs are visible. Hiding a tab does not delete its data.'),
                   save=_('Save'), cancel=_('Cancel'), close=_('Close'), colors=c)
    return '(' + Path(__file__).with_name('workspace_settings.js').read_text(encoding='utf-8') + ')(' + json.dumps(payload) + ');'


def save_command(group, command):
    from urllib.parse import unquote
    if len(command) > 2000:
        raise ValueError('Invalid workspace preferences')
    save(group, json.loads(unquote(command.split(':', 1)[1])))


def popup_error(error):
    return 'window.synapseWorkspaceSettingsError?.(' + json.dumps(_(str(error))) + ');'
