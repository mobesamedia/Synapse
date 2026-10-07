"""Optional dots beside Anki's deck settings controls, with one batched query."""
import re
import time
from html import escape, unescape
from . import deck_overview_options as options

OPTS = re.compile(r'(<td\b[^>]*>)(?:(?!</td>).)*?opts\s*:\s*(\d+)(?:(?!</td>).)*?</td>', re.S | re.I)


DOT = re.compile(r'<span\b[^>]*class=["\']sp-deck-indicator(?:-slot)?["\'][^>]*>.*?</span>', re.S | re.I)
ANCHOR = re.compile(r'<a\b[^>]*>', re.S | re.I)


def add_style(tag, declarations):
    """Extend an existing style attribute instead of producing duplicate attributes."""
    style = re.search(r'\bstyle\s*=\s*(["\'])(.*?)\1', tag, re.S | re.I)
    if style:
        if declarations in unescape(style.group(2)):
            return tag
        value = unescape(style.group(2)).rstrip(';') + ';' + declarations
        return tag[:style.start()] + 'style="' + escape(value, quote=True) + '"' + tag[style.end():]
    return tag[:-1] + ' style="' + declarations + '">'


def render(tree, col, settings, translate):
    tree = DOT.sub("", tree)
    enabled = col.get_config(options.INDICATOR_KEY, default={})
    enabled = enabled if isinstance(enabled, dict) else {}
    opts = options.normalize(settings)
    show_all = opts['deck_overview_indicators_all']
    if not show_all and not any(v is True for v in enabled.values()):
        return tree
    candidates = {int(m.group(2)) for m in OPTS.finditer(tree)
                  if show_all or enabled.get(m.group(2)) is True}
    if not candidates:
        return tree
    now = int(time.time()*1000)
    # Aggregate once even when a collection contains hundreds of visible decks.
    rows = col.db.all('SELECT c.did, count(*), sum(r.ease>1) FROM revlog r '
                      'JOIN cards c ON c.id=r.cid WHERE r.type=1 AND r.ease>0 '
                      'AND r.id>=? AND r.id<=? GROUP BY c.did', now-30*86400000, now)
    counts = {did:(n,ok) for did,n,ok in rows}
    states = {}
    for did in candidates:
        state = options.smiley_choice(col, did)
        if state != 'auto':
            states[did] = state
            continue
        n = ok = 0
        for child in col.decks.deck_and_child_ids(did):
            child_n, child_ok = counts.get(child,(0,0))
            n += child_n; ok += child_ok
        if n < 20:
            continue
        states[did] = options.indicator(ok,n,opts)
    if not states:
        return tree
    def decorate(match):
        cell = match.group(0)
        state = states.get(int(match.group(2)))
        slot_style = 'display:inline-block;width:6px;height:6px;margin-inline-end:9px;vertical-align:middle;'
        if state:
            color = {'green':'#4caf6e','orange':'#dc963c','red':'#e05c5c'}[state]
            label = translate({'green':'Confident','orange':'Still practicing','red':'Needs work'}[state])
            dot = f'<span class="sp-deck-indicator" role="img" aria-label="{escape(label)}" title="{escape(label)}" style="{slot_style}border-radius:50%;background:{color};visibility:visible;opacity:1;"></span>'
        else:
            dot = f'<span class="sp-deck-indicator-slot" aria-hidden="true" style="{slot_style}visibility:hidden;"></span>'
        # Keep the original gear anchor as a direct child. Some deck-browser
        # add-ons make it display:flex, which otherwise puts the dot on a new line.
        anchor = next((m for m in ANCHOR.finditer(cell) if re.search(r'opts\s*:',m.group(0))), None)
        if not anchor:
            return cell
        tag = add_style(anchor.group(0), 'display:inline-flex!important;vertical-align:middle;align-items:center;justify-content:center;width:20px;height:20px;padding:0;margin:0;line-height:0;')
        cell = cell[:anchor.start()] + dot + tag + cell[anchor.end():]
        cell = re.sub(r'<img\b[^>]*>', lambda m: add_style(m.group(0), 'padding:0;margin:0;width:16px;height:16px;display:block;'), cell, flags=re.I)
        opening = match.group(1)
        return add_style(opening, 'white-space:nowrap;min-width:35px;text-align:center;vertical-align:middle;line-height:0;') + cell[len(opening):]

    return OPTS.sub(decorate,tree)
