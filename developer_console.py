"""Developer tools: local diagnostics and isolated visual previews."""
import json
from datetime import date, timedelta
from pathlib import Path

enabled = False


def _achievement_preview_items(scenario, translate=lambda text: text):
    """Build synthetic badge states without reading or changing an Anki profile."""
    try:
        from .achievements import update_achievements
    except ImportError:
        from achievements import update_achievements

    today = date(2026, 1, 31)
    data = {}
    if scenario == 'near':
        counts = {today: 480}
    elif scenario == 'comeback':
        counts = {today - timedelta(days=10): 1,
                  today - timedelta(days=1): 1, today: 1}
    elif scenario == 'tier':
        counts = {today - timedelta(days=offset): 1 for offset in range(30)}
    elif scenario == 'complete':
        counts = {today - timedelta(days=offset): 300 for offset in range(365)}
        earned = {
            key: {str(index): today.isoformat() for index in range(count)}
            for key, count in (("streak", 4), ("reviews", 4), ("days", 4),
                               ("challenges", 4), ("comeback", 1))
        }
        data = {"achievements": {
            "earned": earned,
            "challenge_days": [(today - timedelta(days=offset)).isoformat()
                               for offset in range(365)],
        }}
    else:
        raise ValueError(f"Unknown achievement preview scenario: {scenario}")
    return update_achievements(data, counts, today, translate=translate)[0]


def _achievement_gallery_items(stage, translate=lambda text: text):
    """Return all badge categories at one visual stage for comparison."""
    try:
        from .achievements import BADGES, GOAL_UNITS, TIERS
    except ImportError:
        from achievements import BADGES, GOAL_UNITS, TIERS

    stage_index = {"locked": -1, "bronze": 0, "silver": 1,
                   "gold": 2, "diamond": 3}.get(stage)
    if stage_index is None:
        raise ValueError(f"Unknown achievement gallery stage: {stage}")
    items = []
    for key, name, thresholds, description in BADGES:
        tier = (-1 if stage == "locked" else 0) if key == "comeback" else stage_index
        tier = min(tier, len(thresholds) - 1)
        next_index = tier + 1
        target = thresholds[next_index] if next_index < len(thresholds) else None
        value = thresholds[tier] if tier >= 0 else 0
        unit_one, unit_many = GOAL_UNITS[key]
        items.append({
            "id": key, "name": translate(name), "description": translate(description),
            "tier": tier, "value": value, "target": target,
            "remaining": max(0, target - value) if target is not None else 0,
            "goalValue": value,
            "goalRemaining": max(0, target - value) if target is not None else 0,
            "goalUnitOne": translate(unit_one), "goalUnitMany": translate(unit_many),
            "tiers": [{
                "name": translate(TIERS[index]) if len(thresholds) > 1 else translate("Earned"),
                "target": threshold, "earned": index <= tier,
            } for index, threshold in enumerate(thresholds)],
        })
    return items


def _achievement_document(items, dark=False, translate=lambda text: text,
                          title=None, gallery=False):
    """Render the real badge card with synthetic data for the developer console."""
    html_path = Path(__file__).resolve().parent / 'gamification_web' / 'sidebar.html'
    document = html_path.read_text(encoding='utf-8')
    payload = {
        "items": items,
        "labels": {
            "title": title or translate("Achievements"),
            "hint": translate("Select a badge to see your progress."),
            "locked": translate("Not earned yet"),
            "close": translate("Close"),
            "value": translate("Recorded progress: {}"),
            "next": translate("Next stage: {}"),
            "remaining": translate("Still needed: {}"),
            "complete": translate("All stages earned"),
            "permanent": translate("This achievement is yours to keep."),
            "nextGoal": translate("Your next badge"),
            "goalOne": translate("One more {} to reach {}."),
            "goalMany": translate("{} more {} to reach {}."),
        },
        "dark": bool(dark),
        "gallery": bool(gallery),
    }
    encoded = json.dumps(payload, ensure_ascii=False).replace('</', '<\\/')
    script = f"""<script>
      (function(payload) {{
        document.documentElement.classList.toggle('dark', payload.dark);
        document.body.classList.toggle('dark', payload.dark);
        // Extract only the badge card, including when the live sidebar uses tabs.
        document.getElementById('wrap').replaceChildren(document.getElementById('achievementsCard'));
        renderAchievements(payload.items, payload.labels);
        if (payload.gallery) {{
          document.getElementById('achievementCount').hidden = true;
          document.getElementById('achievementGoal').hidden = true;
          document.getElementById('achievementHint').hidden = true;
          document.getElementById('achievementDetail').hidden = true;
          document.querySelectorAll('.achievement-button').forEach(function(button) {{
            button.tabIndex = -1;
            button.style.pointerEvents = 'none';
            button.setAttribute('aria-expanded', 'false');
          }});
        }}
        document.body.classList.add('ready');
      }})({encoded});
    </script>"""
    return document.replace('</body>', script + '</body>')


def _achievement_preview_document(scenario, dark=False, translate=lambda text: text):
    return _achievement_document(
        _achievement_preview_items(scenario, translate), dark, translate)


def _achievement_gallery_document(stage, dark=False, translate=lambda text: text):
    stage_label = translate({
        "locked": "Locked", "bronze": "Bronze", "silver": "Silver",
        "gold": "Gold", "diamond": "Diamond",
    }[stage])
    return _achievement_document(
        _achievement_gallery_items(stage, translate), dark, translate,
        title=translate("Badge gallery: {}").format(stage_label), gallery=True)


def unlock():
    global enabled
    enabled = True
    import sys
    package = sys.modules.get(__package__)
    if package and hasattr(package, '_add_menus'):
        package._add_menus()




def open_console(parent=None):
    if not enabled:
        return
    from aqt import mw
    from aqt.qt import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel,
                        QComboBox, QSpinBox, QCheckBox, QPushButton, QUrl, QTabWidget, QWidget)
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    from .gamification import RANKS
    from .locales import _
    from .celebration_preview import render_preview
    from .theme import palette

    dialog = QDialog(parent or mw)
    dialog.setWindowTitle(_('Developer console'))
    dialog.resize(620, 830)
    dialog.setMinimumSize(420, 550)
    outer = QVBoxLayout(dialog)
    tabs = QTabWidget(dialog)
    outer.addWidget(tabs)
    from .diagnostics_ui import build_panel
    tabs.addTab(build_panel(dialog), _('Diagnose'))
    from .dashboard_demo import build_panel as build_dashboard_demo_panel
    tabs.addTab(build_dashboard_demo_panel(dialog), 'Dashboard Demo')
    preview_panel = QWidget(dialog)
    tabs.addTab(preview_panel, _('Previews'))
    layout = QVBoxLayout(preview_panel)
    hint = QLabel(_('Preview only. Your profile stays unchanged.'))
    hint.setWordWrap(True)
    layout.addWidget(hint)
    form = QFormLayout()
    kind = QComboBox()
    for label, value in [
            ('Rank up', 'rank'), ('Level up', 'level'), ('Daily Challenge', 'challenge'),
            ('Badge: nearby goal', 'achievement_near'),
            ('Badge: active comeback', 'achievement_comeback'),
            ('Badge: stage change', 'achievement_tier'),
            ('Badge: all complete', 'achievement_complete'),
            ('Badge gallery', 'achievement_gallery')]:
        kind.addItem(_(label), value)
    badge_stage = QComboBox()
    for label, value in [('Locked', 'locked'), ('Bronze', 'bronze'),
                         ('Silver', 'silver'), ('Gold', 'gold'),
                         ('Diamond', 'diamond')]:
        badge_stage.addItem(_(label), value)
    old, new = QComboBox(), QComboBox()
    for rank in RANKS:
        label = f"{rank['level']} · {_(rank['name']).replace('<br>', ' ')}"
        old.addItem(label)
        new.addItem(label)
    old.setCurrentIndex(9)
    new.setCurrentIndex(10)
    number = QSpinBox()
    number.setRange(1, 10000)
    number.setValue(50)
    combined = QCheckBox(_('Also show a completed challenge'))
    dark = QCheckBox(_('Dark preview'))
    try:
        from .sidebar import _is_night
        dark.setChecked(_is_night())
    except Exception:
        pass
    reduced = QCheckBox(_('Reduced motion'))
    form.addRow(_('Preview'), kind)
    form.addRow(_('Previous rank'), old)
    form.addRow(_('New rank'), new)
    form.addRow(_('Level'), number)
    form.addRow(_('Badge stage'), badge_stage)
    layout.addLayout(form)
    layout.addWidget(combined)
    row = QHBoxLayout()
    row.addWidget(dark)
    row.addWidget(reduced)
    replay = QPushButton(_('Replay'))
    row.addWidget(replay)
    layout.addLayout(row)
    web = None  # Diagnostics alone must not create another Chromium view.
    close = QPushButton(_('Close'))
    close.clicked.connect(dialog.reject)
    layout.addWidget(close)

    def preview():
        nonlocal web
        if tabs.currentWidget() is not preview_panel:
            return
        if web is None:
            web = QWebEngineView(preview_panel)
            web.settings().setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
            layout.insertWidget(layout.count() - 1, web, 1)
        mode = kind.currentData()
        achievement_mode = str(mode).startswith('achievement_')
        gallery_mode = mode == 'achievement_gallery'
        old.setEnabled(mode == 'rank')
        new.setEnabled(mode == 'rank')
        number.setEnabled(mode == 'level')
        badge_stage.setEnabled(gallery_mode)
        combined.setEnabled(not achievement_mode and mode != 'challenge')
        reduced.setEnabled(not achievement_mode)
        if achievement_mode:
            if gallery_mode:
                content = _achievement_gallery_document(
                    badge_stage.currentData(), dark=dark.isChecked(), translate=_)
            else:
                scenario = str(mode).removeprefix('achievement_')
                content = _achievement_preview_document(
                    scenario, dark=dark.isChecked(), translate=_)
            base = Path(__file__).resolve().parent / 'gamification_web'
            web.setHtml(content, QUrl.fromLocalFile(str(base) + '/'))
            return
        events = {}
        if mode == 'rank':
            before, after = RANKS[old.currentIndex()], RANKS[new.currentIndex()]
            events['rank'] = {'old_name':before['name'], 'new_name':after['name'],
                'old_image':before['image'].replace('.gif', '.png'),
                'new_image':after['image'].replace('.gif', '.png'), 'level':after['level']}
        elif mode == 'level':
            events['level'] = {'new':number.value()}
        if mode == 'challenge' or combined.isChecked():
            events['challenge'] = {'text':_('Review {} cards today.').format(50), 'xp':195}
        colors = palette(dark.isChecked())
        content = render_preview(events, dark=dark.isChecked(),
            accent=colors.get('blue', '#397cf6'), reduced_motion=reduced.isChecked(), translate=_)
        web.setHtml(content, QUrl.fromLocalFile(str(Path(__file__).resolve().parent) + '/'))

    replay.clicked.connect(preview)
    for combo in (kind, old, new, badge_stage):
        combo.currentIndexChanged.connect(preview)
    number.valueChanged.connect(preview)
    for checkbox in (combined, dark, reduced):
        checkbox.toggled.connect(preview)
    tabs.currentChanged.connect(lambda _index: preview())
    dialog.exec()
    dialog.deleteLater()
