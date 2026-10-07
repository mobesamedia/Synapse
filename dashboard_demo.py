"""Ephemeral dashboard display values. No collection writes, hooks or persistence."""
from copy import deepcopy
from datetime import date, timedelta

_state = None
_owner = None
DEFAULTS = dict(level=55, streak=12, remaining=2800, challenge=0, progress=60,
                claimed=False, fact_theme="Medical", fact_index=0,
                consistency="varied", efficiency=75, accuracy=90, retention=92, new_cards=35)


def stop():
    global _state, _owner
    _state = _owner = None


def current(collection):
    if _owner is not collection:
        stop()
    return deepcopy(_state)


def start(collection, values):
    global _state, _owner
    if collection is None:
        raise ValueError("Open an Anki profile first.")
    clean = dict(DEFAULTS)
    for key, maximum in (("level", 100), ("streak", 9999), ("remaining", 2000000000),
                         ("challenge", 1000), ("progress", 100), ("fact_index", 100000),
                         ("efficiency", 200), ("accuracy", 100), ("retention", 100), ("new_cards", 100)):
        clean[key] = max(1 if key == "level" else 0, min(maximum, int(values.get(key, clean[key]))))
    clean["claimed"] = bool(values.get("claimed", False))
    for key, options in (("fact_theme", ("Medical", "Law", "General", "Countries")),
                         ("consistency", ("varied", "paused", "steady"))):
        if values.get(key) in options:
            clean[key] = values[key]
    _state, _owner = clean, collection


def counts(preset, days, today=None):
    today = today or date.today()
    anchors = {
        "varied": [220, 280, 190, 65, 110, 145, 80, 45, 170, 310],
        "paused": [200, 270, 240, 290, 220, 170, 0, 0, 0, 0],
        "steady": [70, 90, 65, 120, 95, 150, 125, 165, 155, 185],
    }[preset]
    result = {}
    for i in range(days):
        pos = i * (len(anchors)-1) / max(1, days-1)
        left = int(pos); right = min(left+1, len(anchors)-1)
        result[(today-timedelta(days=days-1-i)).isoformat()] = round(
            anchors[left] + (anchors[right]-anchors[left]) * (pos-left))
    return result


def statistics(values, days=7, chart_days=30):
    from .statistics_widget import _build_mini_chart
    chart_days = chart_days if chart_days in (7, 30, 365) else 30
    today = date.today()
    return dict(chart_html=_build_mini_chart(chart_days, counts(values["consistency"], chart_days, today), today),
                efficiency_raw=values["efficiency"], accuracy_raw=values["accuracy"],
                retention_percent=values["retention"], new_cards_percent=values["new_cards"],
                days_scope=days, chart_days=chart_days)


class DisplayGamification:
    """Only the read-only interface required by the two dashboard renderers."""
    def __init__(self, values):
        from .gamification import GamificationManager, DAILY_CHALLENGES, CHALLENGE_TEXT_TEMPLATES
        from .locales import _
        self.values = deepcopy(values)
        self._renderer = GamificationManager
        self.challenge = DAILY_CHALLENGES[min(values["challenge"], len(DAILY_CHALLENGES)-1)]
        self.challenge_text = _(CHALLENGE_TEXT_TEMPLATES[self.challenge["type"]]).format(self.challenge["target"])
        self.needed = self.get_xp_for_level(self.get_level())
        self.remaining = min(values["remaining"], self.needed)
        self.data = {"xp": self.needed-self.remaining}
    def get_level(self): return self.values["level"]
    def get_streak(self): return self.values["streak"]
    def get_xp_for_level(self, level): return self._renderer.get_xp_for_level(self, level)
    def get_rank_name(self): return self._renderer.get_rank_info_for_level(self, self.get_level())["name"]
    def get_current_challenge(self): return self.challenge_text, None
    def get_challenge_progress(self):
        target=self.challenge["target"]
        return (target if self.values["claimed"] else round(target*self.values["progress"]/100)), target
    def is_challenge_completed_today(self): return self.values["claimed"]
    def get_daily_challenge_xp(self): return 100
    def get_remaining_xp(self): return self.remaining
    def get_progress_percentage(self): return 100*(self.needed-self.remaining)/max(1,self.needed)
    def render_widgets_html(self): return self._renderer.render_widgets_html(self)


def build_panel(dialog):
    from aqt import mw
    from aqt.qt import QWidget, QVBoxLayout, QFormLayout, QLabel, QSpinBox, QComboBox, QCheckBox, QPushButton, QScrollArea
    from .gamification import RANKS, DAILY_CHALLENGES, CHALLENGE_TEXT_TEMPLATES
    from . import daily_widgets
    from .locales import _
    owner = mw.col
    values = current(owner) or dict(DEFAULTS)
    panel=QWidget(dialog); outer=QVBoxLayout(panel)
    hint=QLabel(_("Temporary display only. No learning data is changed or saved. Close the console to view the dashboard; reopen this tab to end the demo."))
    hint.setWordWrap(True);outer.addWidget(hint)
    status=QLabel(_("Demo active") if current(owner) else _("Demo inactive"));outer.addWidget(status)
    scroll=QScrollArea();scroll.setWidgetResizable(True);outer.addWidget(scroll)
    body=QWidget();scroll.setWidget(body);form=QFormLayout(body)
    controls={}
    def number(key,label,minimum,maximum):
        field=QSpinBox();field.setRange(minimum,maximum);field.setValue(values[key])
        form.addRow(_(label),field);controls[key]=field
        return field
    level=number("level","Level",1,100);rank=QLabel();form.addRow(_("Rank"),rank)
    remaining=number("remaining","XP to next level",0,2000000000)
    def sync_rank():
        rank.setText(_(next(r for r in reversed(RANKS) if r["level"]<=level.value())["name"]).replace("<br>"," "))
        snapshot=dict(values,level=level.value())
        remaining.setMaximum(min(2000000000,DisplayGamification(snapshot).needed))
    level.valueChanged.connect(sync_rank);sync_rank()
    number("streak","Streak (days)",0,9999)
    challenge=QComboBox()
    for item in DAILY_CHALLENGES:
        challenge.addItem(_(CHALLENGE_TEXT_TEMPLATES[item["type"]]).format(item["target"]))
    challenge.setCurrentIndex(values["challenge"]);form.addRow(_("Daily Challenge"),challenge)
    number("progress","Challenge progress (%)",0,100)
    claimed=QCheckBox(_("Completed and XP claimed"));claimed.setChecked(values["claimed"]);form.addRow("",claimed)
    category=QComboBox()
    for key in ["Medical","Law","General","Countries"]: category.addItem(_(key),key)
    category.setCurrentIndex(category.findData(values["fact_theme"]));form.addRow(_("Fact category"),category)
    fact=QComboBox();fact.setMinimumContentsLength(22)
    fact.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    form.addRow(_("Daily fact"),fact)
    catalog=dict(Medical=daily_widgets.MEDICAL_FACTS,Law=daily_widgets.LAW_FACTS,
                 General=daily_widgets.GENERAL_FACTS,Countries=daily_widgets.COUNTRY_FACTS)
    def fill_facts():
        fact.clear()
        for i,item in enumerate(catalog[category.currentData()]):
            text=_(item.get("text",""));fact.addItem(f"{i+1}. {text[:95]}",i)
        fact.setCurrentIndex(min(values["fact_index"],max(0,fact.count()-1)))
    category.currentTextChanged.connect(fill_facts);fill_facts()
    fact_text=QLabel();fact_text.setWordWrap(True);form.addRow("",fact_text)
    def show_fact():
        items=catalog[category.currentData()]
        fact_text.setText(_(items[max(0,fact.currentIndex())].get("text","")) if items else "")
    fact.currentIndexChanged.connect(show_fact);show_fact()
    curve=QComboBox()
    for label,key in [("Varied — dips and strong comeback","varied"),("Paused — active, then no reviews","paused"),("Steady — gradual improvement","steady")]:
        curve.addItem(_(label),key)
    curve.setCurrentIndex(curve.findData(values["consistency"]));form.addRow(_("Consistency"),curve)
    for key,label,maximum in [("efficiency","Efficiency (%)",200),("accuracy","Accuracy (%)",100),
                              ("retention","Retention (%)",100),("new_cards","New cards (%)",100)]:
        number(key,label,0,maximum)
    def refresh():
        if mw.col is owner:
            if mw.state=="deckBrowser": mw.deckBrowser.refresh()
            else: mw.moveToState("deckBrowser")
    def apply():
        if mw.col is not owner: return
        data={key:field.value() for key,field in controls.items()}
        data.update(challenge=challenge.currentIndex(),claimed=claimed.isChecked(),
                    fact_theme=category.currentData(),fact_index=max(0,fact.currentIndex()),
                    consistency=curve.currentData())
        start(owner,data);refresh();dialog.accept()
    def end():
        stop();refresh();status.setText(_("Demo inactive"))
    apply_button=QPushButton(_("Apply demo and view dashboard"));apply_button.clicked.connect(apply);outer.addWidget(apply_button)
    end_button=QPushButton(_("End dashboard demo"));end_button.clicked.connect(end);outer.addWidget(end_button)
    apply_button.setEnabled(owner is not None)
    return panel
