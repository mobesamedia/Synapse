"""Validated Deck Overview preferences and read-only deck statistics."""
import time
import re
from datetime import datetime, timedelta

PREFIX = 'deck_overview_'
DEFAULTS = {
    PREFIX+'layout': 'classic', PREFIX+'brainstorm': True,
    PREFIX+'title_color_mode': 'primary', PREFIX+'title_color': '#577B9A',
    PREFIX+'indicators_all': False, PREFIX+'retention_days': 30, PREFIX+'green': 85, PREFIX+'orange': 70,
}
CHOICES = {
    PREFIX+'title_color_mode': [('primary','Use primary color'),('custom','Custom color')],
    PREFIX+'layout': [('classic','Classic'),('focus','Focus'),('overview','Overview')],
    PREFIX+'retention_days': [(7,'Last 7 days'),(30,'Last 30 days'),(0,'All time')],
}
LABELS = {
    'title_color_mode':'Deck name color', 'title_color':'Custom deck name color',
    'layout':'Layout', 'brainstorm':'Brainstorm Cloud', 'retention_days':'Period',
    'indicators_all':'Show indicators in Deck Browser for all decks', 'green':'Green from (%)', 'orange':'Orange from (%)',
}


def normalize(settings):
    result = dict(DEFAULTS)
    for key, default in DEFAULTS.items():
        value = settings.get(key, default)
        if key == PREFIX+"brainstorm" and isinstance(value, str):
            value = value != "hidden"
        if key == PREFIX+'title_color':
            if isinstance(value, str) and re.fullmatch(r'#[0-9a-fA-F]{6}', value):
                result[key] = value
        elif type(default) is bool:
            result[key] = value if type(value) is bool else default
        elif key in CHOICES:
            if value in [choice[0] for choice in CHOICES[key]]:
                result[key] = value
        else:
            try:
                result[key] = max(1 if key.endswith('green') else 0, min(100 if key.endswith('green') else 99, int(value)))
            except (ValueError, TypeError, OverflowError):
                pass
    result[PREFIX+'orange'] = min(result[PREFIX+'orange'], result[PREFIX+'green'] - 1)
    return result


def indicator(successes, reviews, settings):
    if reviews < 20:
        return 'neutral'
    percentage = 100 * successes / reviews
    if percentage >= settings[PREFIX+'green']:
        return 'green'
    return 'orange' if percentage >= settings[PREFIX+'orange'] else 'red'


def payload(settings, translate):
    fields = []
    for key, default in DEFAULTS.items():
        item = {'key':key,'label':translate(LABELS[key[len(PREFIX):]]),
                'type':'color' if key == PREFIX+'title_color' else 'boolean' if type(default) is bool else 'choice' if key in CHOICES else 'number'}
        if key in CHOICES:
            item['choices'] = [{'value':v,'label':translate(label)} for v,label in CHOICES[key]]
        fields.append(item)
    return {'fields':fields, 'config':normalize(settings), 'labels':{
        'appearance':translate('Appearance'), 'periodHelp':translate('Period for the retention rate. The smiley uses the last 30 days; the graph shows the last 14 days.'),
        'indicator':translate('Recall indicator'),
        'indicatorHelp':translate('Off: enable individual decks via the smiley. On: show all eligible decks. Auto requires 20 review answers in the last 30 days. Manual smileys appear immediately.'),
        'hint':translate('The smiley reflects remembered review answers over 30 days, not effort. With green at 85 and orange at 70: 90% is green, 80% orange, 60% red. Lower the thresholds for a more forgiving indicator. Fewer than 20 answers are not rated.'),
        'help':translate('How to set the smiley'),
        'validation':translate('The green threshold must be higher than the orange threshold.'),
    }}


def collect_stats(col, deck_id, settings, now=None):
    opts = normalize(settings)
    now = time.time() if now is None else now
    dids = list(col.decks.deck_and_child_ids(deck_id))
    placeholders = ','.join('?' for _ in dids)
    row = col.db.first(
        f'SELECT count(*), sum(lapses>=8), sum(ivl>=21), sum(queue=2), '
        f'sum(queue IN (1,3)), sum(queue=0) FROM cards WHERE did IN ({placeholders})', *dids)
    total, hard, mature, review, learn, new = [int(value or 0) for value in row]
    active = review + learn + new
    days = opts[PREFIX+'retention_days']
    cutoff = int((now-days*86400)*1000) if days else 0
    recent = int((now-30*86400)*1000)
    end = int(now*1000)
    query = f'FROM revlog WHERE cid IN (SELECT id FROM cards WHERE did IN ({placeholders})) AND ease>0 AND id<=?'
    row = col.db.first(
        'SELECT sum(CASE WHEN id>=? THEN ease>1 ELSE 0 END), sum(id>=?), '
        'sum(CASE WHEN id>=? AND type=1 THEN ease>1 ELSE 0 END), sum(id>=? AND type=1) '
        + query, cutoff, cutoff, recent, recent, *dids, end)
    success, answers, recalled, reviews = [int(value or 0) for value in row]
    state = indicator(recalled, reviews, opts)
    # Scheduler counts respect the selected deck, its children and daily limits.
    today_counts = None
    if opts[PREFIX+'layout']=='focus':
        today_counts = tuple(int(n) for n in col.sched.counts())
    history = []
    if opts[PREFIX+'layout']=='overview':
        rollover = max(0,min(23,int(col.conf.get('rollover',4))))
        today = (datetime.fromtimestamp(now)-timedelta(hours=rollover)).date()
        first = today-timedelta(days=13)
        start = int((datetime.combine(first,datetime.min.time())+timedelta(hours=rollover)).timestamp()*1000)
        rows = col.db.all("SELECT strftime('%Y-%m-%d',id/1000,'unixepoch','localtime',?), count(*) " + query + ' AND id>=? GROUP BY 1', f'-{rollover} hours', *dids, end, start)
        counts = dict(rows)
        history = [(str(first+timedelta(days=i)), counts.get(str(first+timedelta(days=i)),0)) for i in range(14)]
    return dict(total=total,hard=hard,learned=mature,review_p=int(review/active*100) if active else 0,
                learn_p=int(learn/active*100) if active else 0,new_p=int(new/active*100) if active else 0,
                ret_p=round(success/answers*100) if answers else None,
                indicator=state,indicator_p=int(recalled/reviews*1000)/10 if reviews else None,
                indicator_reviews=reviews,today=today_counts,history=history,
                diff_img={'green':'easy.png','orange':'medium.png','red':'hard.png','neutral':'medium.png'}[state])

SMILEY_KEY = 'synapsepro_deck_smileys'
SMILEY_IMAGES = {'green':'easy.png', 'orange':'medium.png', 'red':'hard.png'}


def smiley_choice(col, deck_id):
    values = col.get_config(SMILEY_KEY, default={})
    value = values.get(str(deck_id)) if isinstance(values, dict) else None
    return value if value in SMILEY_IMAGES else 'auto'


def set_smiley_choice(col, deck_id, choice):
    if choice not in (*SMILEY_IMAGES, 'auto'):
        raise ValueError('Invalid smiley choice')
    values = col.get_config(SMILEY_KEY, default={})
    values = dict(values) if isinstance(values, dict) else {}
    if choice == 'auto':
        values.pop(str(deck_id), None)
    else:
        values[str(deck_id)] = choice
    col.set_config(SMILEY_KEY, values)

INDICATOR_KEY = 'synapsepro_deck_indicator_visibility'


def indicator_enabled(col, deck_id):
    values = col.get_config(INDICATOR_KEY, default={})
    return isinstance(values, dict) and values.get(str(deck_id)) is True


def set_indicator_enabled(col, deck_id, enabled):
    if type(enabled) is not bool:
        raise ValueError('Invalid indicator visibility')
    values = col.get_config(INDICATOR_KEY, default={})
    values = dict(values) if isinstance(values, dict) else {}
    if enabled:
        values[str(deck_id)] = True
    else:
        values.pop(str(deck_id), None)
    col.set_config(INDICATOR_KEY, values)

