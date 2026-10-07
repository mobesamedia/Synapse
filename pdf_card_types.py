"""PDF creator note types, using Anki's stock templates without changing user models."""
import copy
import re

KINDS = {'basic': 0, 'reversed': 1, 'cloze': 4}

def validate(kind, front, back):
    if kind not in KINDS:
        raise ValueError('Unknown card type')
    if kind == 'cloze' and not re.search(r'\{\{c([1-9][0-9]{0,2})::[^{}]+\}\}', front):
        raise ValueError('Add at least one cloze deletion, for example {{c1::answer}}.')
    if kind == 'reversed' and not back.strip():
        raise ValueError('Reversed cards need text on both sides.')

def resolve(col, kind):
    from anki.stdmodels import get_stock_notetypes
    stock = copy.deepcopy(get_stock_notetypes(col)[KINDS[kind]][1](col))
    def signature(model):
        return (model.get('type'), [f['name'] for f in model['flds']],
                [(t['qfmt'], t['afmt']) for t in model['tmpls']])
    wanted = signature(stock)
    for model in col.models.all():
        if signature(model) == wanted:
            return model
    base = 'SynapsePro PDF — ' + {'basic': 'Basic', 'reversed': 'Basic + Reversed', 'cloze': 'Cloze'}[kind]
    name, suffix = base, 2
    while col.models.by_name(name):
        name = f'{base} ({suffix})'
        suffix += 1
    stock['name'] = name
    col.models.add(stock)
    return stock

def card_count(card):
    kind = card.get('type', 'basic')
    if kind == 'reversed':
        return 2
    if kind == 'cloze':
        return len(set(re.findall(r'\{\{c([1-9][0-9]{0,2})::[^{}]+\}\}', card['front'])))
    return 1
