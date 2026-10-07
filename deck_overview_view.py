"""Original Deck Overview presentation with three fixed layouts."""
from html import escape
import re

EXTRA_CSS = '''<style>html:has(#overview-wrapper),body:has(#overview-wrapper){margin:0!important;padding:0!important;}
#overview-wrapper{box-sizing:border-box;padding:24px 12px;min-height:100vh;}
#overview-wrapper #custom-dashboard{margin:0;}
#custom-dashboard * {box-sizing:border-box;}
#custom-dashboard .white-box {position:relative;}
#custom-dashboard .deck-header h1 {overflow-wrap:anywhere;}
#custom-dashboard .deck-controls {position:absolute;right:14px;top:14px;}
#custom-dashboard .deck-control {width:24px;height:24px;border:0;border-radius:50%;background:var(--progress-bg);color:var(--text-sub);padding:0;cursor:pointer;display:grid;place-items:center;}
#custom-dashboard .deck-control {appearance:none;box-shadow:none;line-height:1;min-width:0;min-height:0;}
#custom-dashboard .deck-control svg {width:14px;height:14px;display:block;margin:0;}
#custom-dashboard button:focus-visible {outline:2px solid var(--accent-color);outline-offset:3px;}
#custom-dashboard .widget {font:inherit;}
#custom-dashboard .progress-row-label {width:92px;text-align:left;}
#custom-dashboard .diff-container {padding:0;flex:0 0 86px;width:86px;height:86px;align-self:center;}
#custom-dashboard .diff-container.unrated img {opacity:.45;}
#custom-dashboard .focus-summary {display:flex;align-items:center;justify-content:center;gap:28px;width:100%;}
#custom-dashboard .focus-ring {width:138px;height:138px;flex-shrink:0;}
#custom-dashboard .focus-ring .ring-total {fill:var(--text-main);font-size:25px;font-weight:600;}
#custom-dashboard .focus-ring .ring-caption {fill:var(--text-sub);font-size:10px;}
#custom-dashboard .today-counts {display:grid;gap:13px;min-width:110px;}
#custom-dashboard .today-counts div {display:flex;justify-content:space-between;gap:20px;align-items:center;font-size:12px;color:var(--text-sub);}
#custom-dashboard .today-counts strong {font-size:14px;font-weight:600;color:var(--text-main);}
#custom-dashboard .today-counts span::before {content:'';display:inline-block;width:6px;height:6px;border-radius:50%;margin-right:7px;background:var(--count-color);}
#custom-dashboard .today-counts .new {--count-color:#4a9eff;}
#custom-dashboard .today-counts .learn {--count-color:#e05c5c;}
#custom-dashboard .today-counts .due {--count-color:#4caf6e;}
#custom-dashboard.layout-focus {max-width:350px;}
#custom-dashboard.layout-focus .white-box {padding:24px 20px;}
#custom-dashboard.layout-focus .deck-header {width:100%;padding:0 22px;}
#custom-dashboard.layout-focus .deck-header h1 {font-size:26px;line-height:1.2;color:var(--text-main);}
#custom-dashboard.layout-focus .deck-header p {font-size:13px;margin:6px 0 18px;}
#custom-dashboard.layout-focus .button-container {margin-top:18px;width:100%;}
#custom-dashboard.layout-classic .deck-header h1,#custom-dashboard.layout-overview .deck-header h1 {color:var(--deck-title-color,var(--accent-color));}
#custom-dashboard.layout-overview {margin:20px 0;}
#custom-dashboard.layout-overview .deck-header p {margin-bottom:18px;}
#custom-dashboard.layout-overview .white-box {padding-top:24px;padding-bottom:24px;}
#custom-dashboard.layout-overview .progress-stack {margin-bottom:18px;}
#custom-dashboard.layout-overview .hint-text {margin-top:10px;}
#custom-dashboard.layout-overview .button-container {margin-top:18px;}
#custom-dashboard .history-panel {margin:14px 0 0;width:100%;text-align:left;}
#custom-dashboard .history-panel h2 {font-size:13px;font-weight:500;color:var(--text-sub);margin:0 0 8px;}
#custom-dashboard .history-line {width:100%;height:76px;display:block;overflow:visible;}
#custom-dashboard .history-empty {font-size:12px;color:var(--text-sub);margin:8px 0 0;}
#custom-dashboard .history-caption {display:flex;justify-content:space-between;color:var(--text-sub);font-size:11px;margin-top:8px;}
#custom-dashboard .widget,#custom-dashboard .diff-container,#custom-dashboard .start-btn {
 background:var(--surface-color)!important;border:1px solid color-mix(in srgb,var(--text-sub) 60%,var(--surface-color))!important;
 color:var(--text-main)!important;box-shadow:none!important;transform:none!important;
 transition:background-color .15s;}
#custom-dashboard .widget:hover,#custom-dashboard .diff-container:hover,#custom-dashboard .start-btn:hover,
#custom-dashboard .widget.active,#custom-dashboard .diff-container.active {background:var(--widget-bg)!important;}
#custom-dashboard .start-btn {background:var(--accent-color)!important;color:#fff!important;border-color:var(--accent-color)!important;}
#custom-dashboard .start-btn:hover {background:var(--accent-color)!important;filter:brightness(.94);}
#custom-dashboard .smiley-choices {display:flex;justify-content:center;gap:10px;flex-wrap:wrap;margin-top:14px;}
#custom-dashboard .smiley-choice {border:1px solid var(--border-color);border-radius:10px;background:var(--surface-color);color:var(--text-main);padding:8px 12px;cursor:pointer;}
#custom-dashboard .smiley-choice:hover {background:var(--widget-bg);}
#custom-dashboard .smiley-choice[aria-pressed="true"] {border-color:var(--accent-color);background:var(--widget-bg);}
#custom-dashboard .smiley-choice img {width:32px;height:32px;display:block;}
@media(max-width:650px){
 #custom-dashboard {width:calc(100% - 24px);margin:24px 0;}
 #custom-dashboard .deck-header h1 {font-size:28px;}
 #custom-dashboard .white-box {padding:40px 14px 24px;}
 #custom-dashboard .widgets-row {flex-wrap:wrap;gap:8px;}
 #custom-dashboard .history-line text {font-size:20px;}
 #custom-dashboard .widget {min-width:120px;}
 #custom-dashboard .button-container {flex-wrap:wrap;}
 #custom-dashboard .btn {padding:10px 20px;max-width:100%;white-space:normal;}
}
@media(max-width:380px){#custom-dashboard .focus-ring {width:112px;height:112px;}#custom-dashboard .focus-summary {gap:14px;}#custom-dashboard .today-counts {min-width:95px;}}
</style>'''


def render_dashboard(title, s, options, t, media):
    def text(value): return escape(str(value))
    def label(value): return text(t(value))
    title_color = options.get('deck_overview_title_color', '')
    title_style = (' style="--deck-title-color:'+title_color+'"' if options.get('deck_overview_title_color_mode')=='custom' and re.fullmatch(r'#[0-9a-fA-F]{6}', title_color) else '')
    layout = options['deck_overview_layout']
    cloud = options['deck_overview_brainstorm'] and layout != 'focus'
    header = f'<div class="deck-header"><h1>{text(title)}</h1><p>{text(t("{} Cards").format(s["total"]))}</p></div>'
    gear='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.7 1.7 0 0 0 .34 1.88l.06.06-2.83 2.83-.06-.06a1.7 1.7 0 0 0-1.88-.34 1.7 1.7 0 0 0-1.03 1.56V21h-4v-.08A1.7 1.7 0 0 0 8.97 19.4a1.7 1.7 0 0 0-1.88.34l-.06.06-2.83-2.83.06-.06A1.7 1.7 0 0 0 4.6 15a1.7 1.7 0 0 0-1.56-1.03H3v-4h.08A1.7 1.7 0 0 0 4.6 8.97a1.7 1.7 0 0 0-.34-1.88l-.06-.06L7.03 4.2l.06.06a1.7 1.7 0 0 0 1.88.34A1.7 1.7 0 0 0 10 3.04V3h4v.08a1.7 1.7 0 0 0 1.03 1.52 1.7 1.7 0 0 0 1.88-.34l.06-.06 2.83 2.83-.06.06a1.7 1.7 0 0 0-.34 1.88A1.7 1.7 0 0 0 20.96 10H21v4h-.08A1.7 1.7 0 0 0 19.4 15z"></path></svg>'
    controls = f'<div class="deck-controls"><button class="deck-control" title="{label("Customize Deck Overview")}" aria-label="{label("Customize Deck Overview")}" onclick="pycmd(\'deck_overview_settings\')">{gear}</button></div>'
    if layout == 'focus':
        counts = s['today'] or (0, 0, 0)
        total = sum(counts)
        segments = ''; offset = 0
        for count,color in zip(counts,('#4a9eff','#e05c5c','#4caf6e')):
            share = count/total*100 if total else 0
            if share:
                segments += f'<circle cx="70" cy="70" r="57" fill="none" stroke="{color}" stroke-width="10" pathLength="100" stroke-dasharray="{share} {100-share}" stroke-dashoffset="{-offset}" transform="rotate(-90 70 70)"/>'
            offset += share
        description = ', '.join(t(name)+': '+str(count) for name,count in zip(('New','Learn','Due'),counts))
        ring = f'<svg class="focus-ring" viewBox="0 0 140 140" role="img" aria-label="{text(description)}"><circle cx="70" cy="70" r="57" fill="none" stroke="var(--progress-bg)" stroke-width="10"/>{segments}<text class="ring-total" x="70" y="70" text-anchor="middle">{total}</text><text class="ring-caption" x="70" y="87" text-anchor="middle">{label("Remaining")}</text></svg>'
        content = '<div class="focus-summary">'+ring+'<div class="today-counts">' + ''.join(
            f'<div class="{kind}"><span>{label(name)}</span><strong>{count}</strong></div>'
            for count, name, kind in zip(counts, ('New','Learn','Due'), ('new','learn','due'))) + '</div></div>'
        if not total:
            content += '<p class="history-empty">'+label('No cards waiting right now')+'</p>'

    else:
        content = '<div class="progress-label">'+label('Progress')+'</div><div class="progress-stack">'+''.join(
            f'<div class="progress-row"><span class="progress-row-label">{label(name)}</span><div class="progress-outer"><div class="progress-inner"><div class="progress-bar-fill bar-{color}" style="width:{s[key]}%"></div></div></div><span class="progress-row-pct">{s[key]}%</span></div>'
            for name,color,key in [('Review','green','review_p'),('Learn','red','learn_p'),('New','blue','new_p')])+'</div>'
        content += '<div class="widgets-row">'
        for kind,name,icon,value in [('retention','Retention','retention.png',str(s['ret_p'])+'%' if s['ret_p'] is not None else '—'),('hard','Hard Cards','hardcards.png',s['hard']),('learned','Finished Cards','learned.png',s['learned'])]:
            content += f'<button class="widget" data-info="{kind}" onclick="toggleInfo(\'{kind}\')"><span class="widget-header"><img alt="" src="{text(media(icon))}"><span>{label(name)}</span></span><span class="widget-val">{text(value)}</span></button>'
        unrated = s['indicator'] == 'neutral' and s.get('smiley_choice', 'auto') == 'auto'
        content += f'<button class="diff-container {"unrated" if unrated else ""}" data-info="diff" aria-label="{label("Not enough reviews yet" if unrated else "Recall indicator")}" onclick="toggleInfo(\'diff\')"><img alt="" src="{text(media(s["diff_img"] or "medium.png"))}"></button></div>'
        choices = ''
        for choice, name in [('green','Confident'),('orange','Still practicing'),('red','Needs work'),('auto','Auto')]:
            face = f'<img alt="" src="{text(media({"green":"easy.png","orange":"medium.png","red":"hard.png"}[choice]))}">' if choice != 'auto' else label(name)
            selected = str(s.get('smiley_choice','auto') == choice).lower()
            choices += f'<button class="smiley-choice" data-choice="{choice}" aria-label="{label(name)}" title="{label(name)}" aria-pressed="{selected}" onclick="pycmd(\'deck_smiley:{s.get("deck_id",0)}:{choice}\')">{face}</button>'
        eligible = s.get('smiley_choice', 'auto') != 'auto' or s.get('indicator_reviews', 0) >= 20
        dot_help = (t('Indicator hidden: {}/20 review answers in the last 30 days.').format(s.get('indicator_reviews',0))
                    if not eligible else t('All decks are enabled in Settings.' if s.get('indicators_all') else 'Auto appears after 20 review answers in 30 days. Manual smileys appear immediately.'))
        content += f'<template id="smiley-picker"><p>{label("Choose how you feel about this deck. Your choice stays until you change it or return to Auto.")}</p><div class="smiley-choices">{choices}</div><label class="deck-dot-option" style="display:block;margin-top:16px"><input type="checkbox" {"checked" if s.get("indicator_enabled") or s.get("indicators_all") else ""} {"disabled" if s.get("indicators_all") else ""} onchange="setDeckIndicator(this, {s.get("deck_id",0)})"> {label("Show indicator in Deck Browser for this deck")}</label><p class="history-empty">{text(dot_help)}</p></template>'
        content += f'<div id="hint-text" class="hint-text">{label("Click for details")}</div><div id="info-panel" class="info-panel" role="status"><span id="info-content"></span></div>'
        if layout == 'overview' and s['history']:
            history = s['history']
            maximum = max(1, max(n for _,n in history))
            points = [(24+i*592/max(1,len(history)-1),72-n/maximum*48,day,n) for i,(day,n) in enumerate(history)]
            path = ' '.join(('M' if i==0 else 'L')+f'{x:.2f},{y:.2f}' for i,(x,y,_,_) in enumerate(points))
            dots = ''.join(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="var(--surface-color)" stroke="var(--accent-color)" stroke-width="1.5"><title>{day}: {n}</title></circle>' for x,y,day,n in points)
            description = '; '.join(f'{day}: {n}' for day,n in history)
            grid = ''.join(f'<line x1="24" x2="616" y1="{y}" y2="{y}" stroke="var(--border-color)" stroke-dasharray="3 5"/>' for y in (24,48,72))
            scale = f'<text x="18" y="20" fill="var(--text-sub)" font-size="10">{maximum if any(n for _,n in history) else 0}</text>'
            empty = '<p class="history-empty">'+label('No reviews in the last 14 days')+'</p>' if not any(n for _,n in history) else ''
            content += f'<section class="history-panel"><h2>{label("Reviews · last 14 days")}</h2><svg class="history-line" viewBox="0 0 640 88" preserveAspectRatio="none" role="img" aria-label="{text(description)}">{grid}{scale}<path d="{path}" fill="none" stroke="var(--accent-color)" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>{dots}</svg><div class="history-caption"><span>{history[0][0]}</span><span>{history[-1][0]}</span></div>{empty}</section>'
    cloud_html=''
    if cloud:
        cloud_html=f'<div id="wordcloud-container"><div id="cloud-overlay"><div class="spinner"></div><div id="cloud-loading-text">{label("Generating Brainstorm Cloud...")}</div></div><canvas id="cloud-canvas"></canvas><div class="cloud-description">{label("Displays the most frequent bold, underlined, or cloze terms in this deck.")}</div></div>'

    brainstorm = f'<button id="brainstorm-btn" class="btn brainstorm-btn" onclick="triggerBrainstorm()">{label("Deck Brainstorm Cloud")}</button>' if cloud else ''
    actions = f'<div class="button-container">{brainstorm}<button class="btn start-btn" onclick="pycmd(\'start_study\')">{label("Start Study")}</button></div>'
    if layout == 'focus':
        box = f'<div class="white-box">{controls}{header}{content}{actions}</div>'
        return f'<div id="overview-wrapper"><div id="custom-dashboard" class="layout-focus">{box}</div></div>'
    return f'<div id="overview-wrapper"><div id="custom-dashboard" class="layout-{layout}"{title_style}>{header}<div class="white-box">{controls}{content}{cloud_html}</div>{actions}</div></div>'
