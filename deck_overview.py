# -*- coding: utf-8 -*-

import json
import os
import re
from collections import Counter
from . import deck_overview_options as overview_options
from .deck_overview_view import render_dashboard, EXTRA_CSS
from aqt import mw
from aqt.gui_hooks import webview_will_set_content, webview_did_receive_js_message
from aqt.overview import Overview
from aqt.utils import tooltip
import aqt

try:
    from .locales import _
except ImportError:
    def _(text):  # type: ignore
        return text

# --- Night Mode Detection ---
is_night_mode = False
try:
    if mw and mw.pm.night_mode():
        is_night_mode = True
except Exception:
    pass

try:
    from .theme import palette as _palette, FONT_FAMILY as _FONT_FAMILY
except ImportError:
    def _palette(night): return {"blue": "#0071D3", "blue_bright": "#4da3ff" if night else "#007AFF", "surface": "#212121" if night else "#ffffff", "bg": "#191919" if night else "#F5F5F7", "text": "#e0e0e0" if night else "#1d1d1f", "text_muted": "#aaaaaa" if night else "#86868b", "grey_light": "#333333" if night else "#e5e5e5", "grey_mid": "#444444" if night else "#d1d1d6"}  # type: ignore
    _FONT_FAMILY = "sans-serif"

ADDON_PACKAGE = __name__.split('.')[0]

current_settings = {}

# Guard so the webview hooks are registered only once, even if
# init_deck_overview() runs again on a profile switch.
_hooks_registered = False

def update_settings(settings):
    """Wird von __init__.py aufgerufen, um die Einstellungen zu synchronisieren."""
    global current_settings
    current_settings = settings

def get_media_url(filename):
    return f"/_addons/{ADDON_PACKAGE}/media/{filename}"

# --- BRAINSTORMING LOGIK & STOPWORDS ---
STOPWORDS = set([
    # HTML & System
    "nbsp", "amp", "quot", "lt", "gt", "div", "br", "span", "font", "style", "color",
    
    # Deutsch
    "welche", "welcher", "welches", "was", "wie", "wann", "warum", "wo", "wer", "ist", "sind",
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "einem", "einen", "eines",
    "und", "oder", "aber", "bei", "mit", "von", "für", "auf", "aus", "zu", "zur", "zum", "im", "in",
    "an", "als", "auch", "sich", "es", "wird", "werden", "kann", "können", "hat", "haben", "nach",
    "durch", "man", "liegt", "kommt", "führt", "gehören", "zählen", "dieser", "diese", "dieses",
    "dass", "um", "nicht", "nur", "noch", "mehr", "weniger", "gibt", "über", "unter", "zwischen",
    "dann", "wenn", "welchen", "dabei", "daher", "dazu", "darauf", "daraus", "damit", "sehr",
    "häufig", "oft", "immer", "alle", "alles", "kein", "keine", "bzw", "vgl", "etwa", "ihre", "sein",
    "seine", "deshalb", "wegen", "beim", "vom", "bis", "sowie", "dort", "hier",
    
    # Englisch
    "the", "be", "to", "of", "and", "a", "in", "that", "have", "i", "it", "for", "not", "on", "with",
    "he", "as", "you", "do", "at", "this", "but", "his", "by", "from", "they", "we", "say", "her",
    "she", "or", "an", "will", "my", "one", "all", "would", "there", "their", "what", "so", "up",
    "out", "if", "about", "who", "get", "which", "go", "me", "when", "make", "can", "like", "time",
    "no", "just", "him", "know", "take", "people", "into", "year", "your", "good", "some", "could",
    "them", "see", "other", "than", "then", "now", "look", "only", "come", "its", "over", "think",
    "also", "back", "after", "use", "two", "how", "our", "work", "first", "well", "way", "even",
    "new", "want", "because", "any", "these", "give", "day", "most", "us", "are", "was", "were",
    
    # Spanisch
    "el", "la", "los", "las", "un", "una", "unos", "unas", "y", "o", "pero", "si", "no", "en", "de",
    "a", "por", "para", "con", "sin", "sobre", "entre", "su", "sus", "mi", "mis", "tu", "tus", "te",
    "se", "lo", "le", "al", "del", "que", "cual", "cuales", "quien", "quienes", "este", "esta",
    "estos", "estas", "ese", "esa", "esos", "esas", "aquel", "aquella", "aquellos", "aquellas",
    "yo", "tú", "él", "ella", "nosotros", "nosotras", "vosotros", "vosotras", "ellos", "ellas",
    "me", "nos", "os", "muy", "mucho", "muchos", "mucha", "muchas", "poco", "pocos", "poca", "pocas",
    "más", "menos", "todo", "todos", "toda", "todas", "nada", "algo", "ser", "es", "son", "era",
    "eran", "fui", "fue", "estar", "está", "están", "estaba", "estaban", "tener", "tiene", "tienen",
    "tenía", "tenían", "hacer", "hace", "hacen", "hacía", "hacían", "ir", "voy", "va", "van",
    "iba", "iban"
])

def get_marked_words(text):
    words = []
    # Explicit formatting tags: <b>, <strong>, <u>
    marked_blocks = re.findall(
        r'<(?:b|strong|u)[^>]*>(.*?)</(?:b|strong|u)>',
        text, flags=re.IGNORECASE | re.DOTALL)

    # Style-based bold/underline: <span style="font-weight: bold/700">,
    # text-decoration: underline etc. Older Anki versions, mobile clients,
    # imports and pasted content store formatting this way — without this,
    # marked words in EXISTING decks are silently missed.
    styled_blocks = [
        m[1] for m in re.findall(
            r'<(span|font|div)[^>]*style\s*=\s*["\'][^"\']*'
            r'(?:font-weight\s*:\s*(?:bold|bolder|[6-9]00)'
            r'|text-decoration[^"\';]*underline)'
            r'[^"\']*["\'][^>]*>(.*?)</\1>',
            text, flags=re.IGNORECASE | re.DOTALL)
    ]

    cloze_blocks = re.findall(r'\{\{c\d+::(.*?)(?:::.*?)?\}\}', text, flags=re.DOTALL)

    all_blocks = marked_blocks + styled_blocks + cloze_blocks

    for block in all_blocks:
        clean_text = re.sub(r'<[^>]+>', '', block)
        clean_text = re.sub(r'&[a-zA-Z0-9#]+;', ' ', clean_text)
        # [^\W\d_] = any Unicode letter — covers á é í ó ú ñ ç ø ā … instead
        # of only ASCII + German umlauts (Spanish/French/etc. words were
        # previously dropped or truncated).
        tokens = re.findall(r'\b[^\W\d_]+(?:-[^\W\d_]+)*\b', clean_text)

        for t in tokens:
            if len(t) > 2 and t.lower() not in STOPWORDS:
                words.append(t.capitalize())
    return words

def process_deck_words_background(notes_flds):
    """Diese Funktion läuft im Hintergrund. Die DB-Abfrage ist bereits im Haupt-Thread passiert."""
    all_words = []
    for flds_str in notes_flds:
        text = flds_str.replace('\x1f', ' ')
        words = get_marked_words(text)
        all_words.extend(words)
        
    word_counts = Counter(all_words)
    top_words = word_counts.most_common(120) 
    
    return json.dumps(top_words, ensure_ascii=False)

def on_brainstorm_finished(future, expected_deck_id=None):
    """Wird aufgerufen, sobald der Hintergrund-Task fertig ist."""
    try:
        if (not mw or not mw.col or mw.state != "overview"
                or not getattr(mw, "overview", None)
                or not overview_options.normalize(current_settings)["deck_overview_brainstorm"]
                or (expected_deck_id is not None
                    and mw.col.decks.current().get("id") != expected_deck_id)):
            return
    except Exception:
        return
    try:
        words_json = future.result()
        mw.overview.web.eval(f"renderWordCloud({words_json});")
    except Exception as e:
        print(f"Brainstorm Error: {e}")
        mw.overview.web.eval("renderWordCloud([]);")

# --- THEMES & STYLES ---

def _build_overview_style(night: bool) -> str:
    c = _palette(night)
    return f"""
    --surface-color: {c['surface']};
    --text-main: {c['text']};
    --text-sub: {c['text_muted']};
    --border-color: {c['grey_light']};
    --accent-color: {c['blue']};
    --progress-bg: {c['grey_light']};
    --progress-border: {c['grey_mid']};
    --widget-bg: {c['bg']};
    --widget-hover: {c['surface']};
    --shadow: {'0 4px 12px rgba(0,0,0,0.3)' if night else '0 4px 12px rgba(0,0,0,0.05)'};
    --header-color: {c['text']};
"""

def get_style():
    is_night = mw.pm.night_mode()
    active_vars = _build_overview_style(is_night)

    return f"""
<style>
    :root {{ {active_vars} }}
    
    /* GANZ WICHTIG FÜR CSS-LEAK: Styles sind jetzt im Body gekapselt und stören nicht mehr */
    .overview-container, .bottom, #overview, .toolbar, .main {{ display: none !important; }}
    
    #overview-wrapper {{
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
        display: flex; justify-content: center; align-items: center; min-height: 100vh;
        margin: 0; color: var(--text-main); -webkit-user-select: none; overflow-x: hidden;
        transition: color 0.3s;
        background-color: transparent;
    }}
    
    #custom-dashboard {{ text-align: center; width: 90%; max-width: 850px; margin: 40px 0; }}
    .deck-header h1 {{ font-size: 42px; font-weight: 600; margin: 0; color: var(--header-color); }}
    .deck-header p {{ font-size: 16px; color: var(--text-sub); margin: 8px 0 30px 0; }}
    .white-box {{
        background: var(--surface-color); border-radius: 24px; padding: 40px;
        display: flex; flex-direction: column; align-items: center;
        border: 1px solid var(--border-color);
        transition: background-color 0.3s, border-color 0.3s, box-shadow 0.3s;
    }}
    .progress-label {{ font-size: 13px; color: var(--text-sub); font-weight: 500; margin-bottom: 10px; }}
    .progress-stack {{ width: 100%; margin-bottom: 30px; display: flex; flex-direction: column; gap: 7px; }}
    .progress-row {{ display: flex; align-items: center; gap: 10px; }}
    .progress-row-label {{ font-size: 12px; color: var(--text-sub); font-weight: 500; width: 46px; text-align: right; flex-shrink: 0; }}
    .progress-row-pct {{ font-size: 12px; color: var(--text-sub); font-weight: 600; width: 30px; text-align: right; flex-shrink: 0; }}
    .progress-outer {{ flex: 1; background: var(--progress-bg); border: 1px solid var(--progress-border); border-radius: 20px; padding: 3px; box-sizing: border-box; }}
    .progress-inner {{ width: 100%; height: 10px; border-radius: 8px; overflow: hidden; }}
    .progress-bar-fill {{ height: 100%; width: 0%; border-radius: 8px; transition: width 1s cubic-bezier(0.22, 1, 0.36, 1); }}
    .bar-green {{ background-color: #4caf6e; }}
    .bar-red   {{ background-color: #e05c5c; }}
    .bar-blue  {{ background-color: #4a9eff; }}
    .widgets-row {{ display: flex; justify-content: space-between; align-items: stretch; width: 100%; gap: 15px; }}
    .widget {{ background: var(--widget-bg); border: 1px solid transparent; border-radius: 18px; padding: 15px; flex: 1; display: flex; flex-direction: column; align-items: center; cursor: pointer; transition: transform 0.15s, background 0.15s, border-color 0.3s; }}
    .widget:hover {{ background: var(--widget-hover); border-color: var(--border-color); }}
    .widget.active {{ border-color: var(--accent-color); background: var(--widget-hover); }}
    .widget-header {{ display: flex; align-items: center; gap: 6px; margin-bottom: 6px; }}
    .widget-header img {{ width: 14px; height: 14px; opacity: 0.7; }}
    .widget-header span {{ font-size: 13px; color: var(--text-sub); font-weight: 500; }}
    .widget-val {{ font-size: 28px; font-weight: 700; color: var(--text-main); }}
    .diff-container {{ width: 80px; display: flex; justify-content: center; align-items: center; background: var(--widget-bg); border: 1px solid transparent; border-radius: 18px; cursor: pointer; transition: transform 0.15s, background 0.15s; }}
    .diff-container:hover {{ background: var(--widget-hover); border-color: var(--border-color); }}
    .diff-container.active {{ border-color: var(--accent-color); background: var(--widget-hover); }}
    .diff-container img {{ width: 50px; height: 50px; }}
    .info-panel {{ width: 100%; height: 0; opacity: 0; overflow: hidden; transition: all 0.3s ease; text-align: center; color: var(--text-sub); font-size: 14px; border-top: 1px solid transparent; }}
    .info-panel.visible {{ height: auto; opacity: 1; padding-top: 20px; margin-top: 20px; border-top-color: var(--border-color); }}
    .hint-text {{ margin-top: 15px; font-size: 12px; color: var(--text-sub); opacity: 0.6; }}
    .hint-text.hidden {{ display: none; }}
    .button-container {{ margin-top: 30px; display: flex; gap: 15px; justify-content: center; }}
    .btn {{ -webkit-appearance: none !important; appearance: none !important; border: none !important; padding: 10px 40px; border-radius: 5px; font-size: 14px; font-weight: 600; cursor: pointer; transition: background-color 0.1s ease, transform 0.1s ease; }}
    .start-btn {{ background-color: var(--widget-bg) !important; color: var(--text-main) !important; border: 1px solid var(--border-color) !important; }}
    .start-btn:hover {{ background-color: var(--widget-hover) !important; color: var(--text-main) !important; border-color: var(--accent-color) !important; }}
    .start-btn:active {{ background-color: var(--widget-hover) !important; color: var(--text-main) !important; border-color: var(--accent-color) !important; }}
    .brainstorm-btn {{ background-color: var(--widget-bg) !important; color: var(--text-main) !important; border: 1px solid var(--border-color) !important; }}
    .brainstorm-btn:hover:not(:disabled) {{ background-color: var(--widget-hover) !important; border-color: var(--accent-color) !important; }}
    .brainstorm-btn:disabled {{ opacity: 0.6; cursor: not-allowed; }}
    #wordcloud-container {{ width: 100%; height: 0; opacity: 0; overflow: hidden; transition: opacity 0.4s ease, margin-top 0.4s ease; margin-top: 0; border-radius: 18px; background: var(--widget-bg); position: relative; display: flex; flex-direction: column; align-items: center; }}
    #wordcloud-container.visible {{ height: auto; opacity: 1; margin-top: 20px; border: 1px solid var(--border-color); padding: 20px; box-sizing: border-box; }}
    #cloud-canvas {{ display: block; margin: 0 auto; }}
    .cloud-description {{ font-size: 12px; color: var(--text-sub); margin-top: 15px; text-align: center; width: 100%; }}
    #cloud-overlay {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; background: var(--widget-bg); z-index: 10; display: flex; flex-direction: column; justify-content: center; align-items: center; border-radius: 18px; transition: opacity 0.3s ease; }}
    .spinner {{ border: 3px solid var(--progress-border); border-top: 3px solid var(--accent-color); border-radius: 50%; width: 24px; height: 24px; animation: spin 1s linear infinite; margin-bottom: 12px; }}
    @keyframes spin {{ 0% {{ transform: rotate(0deg); }} 100% {{ transform: rotate(360deg); }} }}
    #cloud-loading-text {{ font-size: 13px; color: var(--text-sub); font-weight: 500; }}
</style>
"""

def get_script(stats=None):
    js_url = get_media_url("wordcloud2.min.js")
    # Pre-compute translated JS labels. Escape double quotes so they're safe inside "..." JS strings.
    def _js(s: str) -> str:
        return s.replace("\\", "\\\\").replace('"', '\\"')
    opts = overview_options.normalize(current_settings)
    days = opts['deck_overview_retention_days']
    lbl_retention_info = _js(_("Remembered answers across all learning and review steps. Period: {}.").format(_("All time") if not days else _("Last {} days").format(days)))
    lbl_hard_info      = _js(_("Hard cards are cards you have forgotten 8 or more times."))
    lbl_show_hard      = _js(_("Show Hard Cards"))
    lbl_learned_info   = _js(_("Mature cards have an interval of at least 21 days. They still need reviews."))
    lbl_diff_info = _js(_("Remembered review answers in the last 30 days; Again counts as forgotten. Green from {}%, orange from {}%, red below. Neutral until 20 reviews. This describes recent recall, not effort or ability.").format(opts['deck_overview_green'], opts['deck_overview_orange']))
    lbl_analyzing      = _js(_("Analyzing..."))
    lbl_no_marked      = _js(_("No marked words found."))
    lbl_wc_missing     = _js(_("Error: wordcloud2.min.js missing in 'media' folder."))
    lbl_brainstorm_btn = _js(_("Deck Brainstorm Cloud"))
    return f"""
<script src="{js_url}"></script>
<script>
    const LBL_RETENTION_INFO = "{lbl_retention_info}";
    const LBL_HARD_INFO      = "{lbl_hard_info}";
    const LBL_SHOW_HARD      = "{lbl_show_hard}";
    const LBL_LEARNED_INFO   = "{lbl_learned_info}";
    const LBL_DIFF_INFO      = "{lbl_diff_info}";
    const LBL_ANALYZING      = "{lbl_analyzing}";
    const LBL_NO_MARKED      = "{lbl_no_marked}";
    const LBL_WC_MISSING     = "{lbl_wc_missing}";
    const LBL_BRAINSTORM_BTN = "{lbl_brainstorm_btn}";

    document.addEventListener('keydown', function(event) {{
        if(event.code !== 'Space' || event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) return;
        if(!document.getElementById('custom-dashboard')) return;
        if(event.target.closest('input,textarea,select,button,a,summary,[contenteditable="true"],[role="dialog"]')) return;
        event.preventDefault();event.stopImmediatePropagation();
        if(!event.repeat) pycmd('start_study');
    }}, true);

    function setDeckIndicator(input, deckId) {{
        const stored = document.getElementById('smiley-picker').content.querySelector('input');
        stored.toggleAttribute('checked', input.checked);
        pycmd('deck_indicator:' + deckId + ':' + (input.checked ? '1' : '0'));
    }}

    function toggleInfo(type) {{
        const panel = document.getElementById('info-panel');
        const content = document.getElementById('info-content');
        const hint = document.getElementById('hint-text');
        const widgets = document.querySelectorAll('.widget');
        const diff = document.querySelector('.diff-container');

        widgets.forEach(w => w.classList.remove('active'));
        if(diff)diff.classList.remove('active');

        let text = ""; let html = ""; let activeEl = null;

        if (type === 'retention') {{ text = LBL_RETENTION_INFO; activeEl = document.querySelector('[data-info="retention"]'); }}
        else if (type === 'hard') {{ text = LBL_HARD_INFO; html = "<br><button class='brainstorm-btn btn' style='margin-top:10px; padding: 6px 16px;' onclick='pycmd(\\\"browse_hard\\\")'>" + LBL_SHOW_HARD + "</button>"; activeEl = document.querySelector('[data-info="hard"]'); }}
        else if (type === 'learned') {{ text = LBL_LEARNED_INFO; activeEl = document.querySelector('[data-info="learned"]'); }}
        else if (type === 'diff') {{ text = LBL_DIFF_INFO; html = document.getElementById('smiley-picker').innerHTML; activeEl = diff; }}

        if (panel.classList.contains('visible') && content.dataset.type === type) {{
            panel.classList.remove('visible'); hint.classList.remove('hidden');
        }} else {{
            content.innerHTML = text + html; content.dataset.type = type;
            panel.classList.add('visible'); hint.classList.add('hidden');
            if(activeEl) activeEl.classList.add('active');
        }}
    }}

    function triggerBrainstorm() {{
        document.querySelectorAll('.deck-menu[open]').forEach(menu=>menu.open=false);
        const container = document.getElementById('wordcloud-container');
        const overlay = document.getElementById('cloud-overlay');
        const btn = document.getElementById('brainstorm-btn');

        if (container.classList.contains('visible')) {{
            container.classList.remove('visible'); return;
        }}

        container.classList.add('visible');
        overlay.style.display = 'flex';
        overlay.style.opacity = '1';
        btn.disabled = true;
        btn.innerText = LBL_ANALYZING;

        // Signal an Python, den Hintergrund-Prozess zu starten
        pycmd('brainstorm');
    }}

    function renderWordCloud(wordData) {{
        const overlay = document.getElementById('cloud-overlay');
        const btn = document.getElementById('brainstorm-btn');

        if (!overlay || !btn) return;
        if (!wordData || wordData.length === 0) {{
            document.getElementById('cloud-loading-text').innerText = LBL_NO_MARKED;
            document.querySelector('.spinner').style.display = 'none';
            btn.disabled = false;
            btn.innerText = LBL_BRAINSTORM_BTN;
            return;
        }}

        // Prüfen, ob WordCloud verfügbar ist (Falls Datei fehlt)
        if (typeof WordCloud === 'undefined') {{
            document.getElementById('cloud-loading-text').innerText = LBL_WC_MISSING;
            document.querySelector('.spinner').style.display = 'none';
            return;
        }}

        const canvas = document.getElementById('cloud-canvas');
        const container = document.getElementById('wordcloud-container');
        
        canvas.addEventListener('wordcloudstop', function() {{
            overlay.style.opacity = '0';
            setTimeout(() => {{ overlay.style.display = 'none'; }}, 300);
            btn.disabled = false;
            btn.innerText = LBL_BRAINSTORM_BTN;
        }});
        
        const dpr = window.devicePixelRatio || 1;
        const logicalWidth = container.clientWidth - 40; 
        const logicalHeight = Math.max(250, logicalWidth * 0.55); 
        
        canvas.width = logicalWidth * dpr;
        canvas.height = logicalHeight * dpr;
        canvas.style.width = logicalWidth + 'px';
        canvas.style.height = logicalHeight + 'px';

        const maxCount = Math.max(...wordData.map(w => w[1]));
        const minCount = Math.min(...wordData.map(w => w[1]));
        const minSize = 12 * dpr;
        const maxSize = 60 * dpr;

        function getBlueShade() {{
            const h = 200 + Math.random() * 15;
            const s = 80 + Math.random() * 20;
            const l = 30 + Math.random() * 35;
            return `hsl(${{h}}, ${{s}}%, ${{l}}%)`;
        }}

        WordCloud(canvas, {{
            list: wordData,
            fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            fontWeight: 600, minRotation: 0, maxRotation: 0, rotateRatio: 0, 
            color: getBlueShade, backgroundColor: 'transparent', wait: 10, shape: 'square',
            gridSize: Math.max(4, Math.round((8 * canvas.width) / 1024)), 
            weightFactor: function (size) {{
                if (maxCount === minCount) return (maxSize + minSize) / 2;
                return minSize + ((size - minCount) / (maxCount - minCount)) * (maxSize - minSize);
            }},
            shrinkToFit: true, drawOutOfBound: false
        }});
    }}
</script>
"""

def get_stats(deck_id):
    stats = overview_options.collect_stats(mw.col, deck_id, current_settings)
    choice = overview_options.smiley_choice(mw.col, deck_id)
    stats.update(deck_id=deck_id, smiley_choice=choice, indicator_enabled=overview_options.indicator_enabled(mw.col, deck_id))
    stats['indicators_all'] = overview_options.normalize(current_settings)['deck_overview_indicators_all']
    if choice != 'auto':
        stats['diff_img'] = overview_options.SMILEY_IMAGES[choice]
    return stats


def on_message(handled, msg, ctx):
    if not isinstance(ctx, Overview):
        return handled
    if msg.startswith("deck_indicator:"):
        try:
            _, deck_id, enabled = msg.split(":")
            deck_id = int(deck_id)
            if mw.state != "overview" or mw.col.decks.current()['id'] != deck_id or enabled not in ('0','1'):
                return (True, None)
            overview_options.set_indicator_enabled(mw.col, deck_id, enabled == '1')
        except Exception:
            tooltip(_("Could not save the setting. Please try again."))
            mw.overview.refresh()
        return (True, None)
    if msg.startswith("deck_smiley:"):
        try:
            _, deck_id, choice = msg.split(":")
            deck_id = int(deck_id)
            if mw.state != "overview" or mw.col.decks.current()['id'] != deck_id:
                return (True, None)
            overview_options.set_smiley_choice(mw.col, deck_id, choice)
            mw.overview.refresh()
        except Exception:
            tooltip(_("Could not save the smiley. Please try again."))
        return (True, None)
    if msg == "deck_overview_settings":
        from . import show_settings_dialog
        mw.progress.single_shot(0, lambda: show_settings_dialog(initial_page="deck"))
        return (True, None)
    if msg == "start_study":
        if mw.state != "overview":
            return (True, None)
        mw.col.startTimebox()
        mw.moveToState("review")
        return (True, None)
    elif msg == "browse_hard":
        deck = mw.col.decks.current()
        query = f'"deck:{deck["name"]}" prop:lapses>=8'
        browser = aqt.dialogs.open("Browser", mw)
        browser.setFilter(query)
        return (True, None)
    elif msg == "brainstorm":
        if not overview_options.normalize(current_settings)["deck_overview_brainstorm"]:
            return (True, None)
        deck = mw.col.decks.current()
        if deck:
            # DB query must run on the main thread.
            dids = mw.col.decks.deck_and_child_ids(deck['id'])
            ids_str = ",".join(str(i) for i in dids)
            # Bound both note count and field length; the DB query runs on the
            # UI thread and an unbounded large deck can otherwise freeze Anki.
            query = (f"select substr(flds, 1, 10000) from notes where id in "
                     f"(select distinct nid from cards where did in ({ids_str})) LIMIT 2000")
            notes_flds = mw.col.db.list(query)
            
            # FIX: Nur die Text-Bearbeitung an den Hintergrund-Task geben
            mw.taskman.run_in_background(
                lambda: process_deck_words_background(notes_flds),
                lambda future, did=deck['id']: on_brainstorm_finished(future, did)
            )
        return (True, None)
    return handled

def _session_summary_inner():
    """Self-contained (inline-styled) stats card for the finished session.

    Rendered onto Anki's congrats page, which has none of our CSS variables —
    all colours therefore come inline from the theme palette. Empty string
    when there is no session to summarise.
    """
    try:
        start_ms = getattr(mw, "_sp_session_start_ms", None)
        if not start_ms:
            return ""
        row = mw.col.db.first(
            "SELECT COUNT(*), SUM(time) FROM revlog WHERE id >= ? AND ease > 0",
            int(start_ms),
        )
        count, total_ms = (row or (0, 0))
        count = count or 0
        total_ms = total_ms or 0
        if count <= 0:
            return ""

        # Time as "12m 05s" (or "45s" for very short sessions).
        total_s = int(total_ms / 1000)
        if total_s >= 60:
            time_str = f"{total_s // 60}m {total_s % 60:02d}s"
        else:
            time_str = f"{total_s}s"

        # Display the actual committed award, including any carried fraction.
        # Reconciliation is idempotent; the second render also retries failures.
        gm = getattr(mw, "gamification_manager", None)
        xp_earned = 0
        if gm:
            credited = gm.credit_study_xp(int(start_ms))
            sidebar = getattr(mw, "gamification_sidebar", None)
            if credited and sidebar and sidebar.isVisible():
                sidebar.update_display()
            if getattr(gm, "_study_session_start", None) == int(start_ms):
                xp_earned = getattr(gm, "_study_session_xp", 0)

        night = False
        try:
            night = bool(mw.pm.night_mode())
        except Exception:
            pass
        c = _palette(night)
        bg = c.get("surface", "#2c2c2c" if night else "#ffffff")
        text = c.get("text", "#f5f5f7" if night else "#1d1d1f")
        muted = c.get("text_muted", "#8e8e93")
        border = c.get("grey_mid" if night else "grey_light", "#d1dce5")
        accent = c.get("blue_bright" if night else "blue", "#0071D3")

        remaining_html = ""
        try:
            gm = getattr(mw, "gamification_manager", None)
            remaining = gm.get_remaining_xp() if gm else None
            if isinstance(remaining, int):
                lbl_remaining = _("{} XP to next level").format(f"{remaining:,}")
                remaining_html = f'<span>{lbl_remaining}</span>'
        except Exception:
            pass

        lbl_title = _("Session Summary")
        lbl_cards = _("{} cards").format(count)
        lbl_time = _("in {}").format(time_str)
        lbl_xp = _("+{} XP earned").format(xp_earned)

        return (
            f'<div style="max-width:520px;margin:26px auto 0;padding:14px 20px;'
            f'background:{bg};border:1px solid {border};border-radius:12px;'
            f'text-align:center;box-sizing:border-box;font-family:-apple-system,'
            f'BlinkMacSystemFont,\'Segoe UI\',Roboto,Helvetica,Arial,sans-serif;">'
            f'<div style="font-size:12px;font-weight:600;letter-spacing:0.05em;'
            f'text-transform:uppercase;color:{muted};margin-bottom:8px;">{lbl_title}</div>'
            f'<div style="display:flex;justify-content:center;gap:26px;flex-wrap:wrap;'
            f'font-size:15px;color:{text};">'
            f'<span><b>{lbl_cards}</b> {lbl_time}</span>'
            f'<span style="color:{accent};font-weight:600;">{lbl_xp}</span>'
            f'{remaining_html}'
            f'</div></div>'
        )
    except Exception as e:
        print(f"SynapsePro: session summary error: {e}")
        return ""


def inject_session_summary_into_congrats():
    """Add the session summary to Anki's congrats page via JS.

    The congrats screen ("Congratulations! You have finished this deck…") is
    an internal Anki TS page that bypasses webview_will_set_content, so the
    card is injected after the fact. The JS double-checks it is really on
    the congrats page and never inserts twice — safe to call speculatively.
    """
    try:
        if not mw or not getattr(mw, "web", None):
            return
        snippet = _session_summary_inner()
        if not snippet:
            return
        js = (
            "(function(){"
            "try{"
            "if(location.href.indexOf('congrats')===-1) return;"
            "var existing=document.getElementById('sp-session-summary');"
            f"if(existing){{existing.innerHTML={json.dumps(snippet)};return;}}"
            "var d=document.createElement('div');"
            "d.id='sp-session-summary';"
            f"d.innerHTML={json.dumps(snippet)};"
            "document.body.insertBefore(d, document.body.firstChild);"
            "}catch(e){}"
            "})();"
        )
        mw.web.eval(js)
    except Exception as e:
        print(f"SynapsePro: congrats summary inject failed: {e}")


def on_overview_render(web, ctx):
    if not current_settings.get("deck_overview_enabled", True): return
    if not isinstance(ctx, Overview): return
    deck = mw.col.decks.current()
    if not deck: return

    try:
        s = get_stats(deck['id'])

        custom_background_override = ""
        if current_settings.get("custom_background_enabled", False):
            try:
                from . import custom_background
                custom_background_available = custom_background.has_image()
            except Exception:
                custom_background_available = False
            if custom_background_available:
                # This hook replaces the whole body after the global theme hook
                # has run. Re-add the state class here and place the override
                # after the linked colour theme so its gradient cannot win.
                canvas_js = custom_background.canvas_script(True)
                custom_background_override = """
                <style id="synapse-overview-custom-background">
                  html:has(body.synapse-custom-background):has(#custom-dashboard),
                  body.synapse-custom-background:has(#custom-dashboard),
                  body.synapse-custom-background #overview-wrapper {
                    background: transparent !important;
                    background-color: transparent !important;
                    background-image: none !important;
                    background-attachment: initial !important;
                  }
                </style>
                """ + (
                    "<script>" + canvas_js
                    + "document.body.classList.add('overview');</script>"
                )

        options = overview_options.normalize(current_settings)
        page_html = (get_style() + EXTRA_CSS
                     + render_dashboard(deck['name'].split('::')[-1], s, options, _, get_media_url)
                     + get_script(s) + custom_background_override)
        web.body = page_html
    except Exception as e:
        print(f"SynapsePro Deck Overview Error: {e}")

def on_deck_browser_render(browser, content):
    try:
        from .deck_browser_indicator import render
        content.tree = render(content.tree, mw.col, current_settings, _)
    except Exception as exc:
        print(f"SynapsePro deck indicator: {exc}")


def init_deck_overview():
    global _hooks_registered
    if _hooks_registered:
        return
    from aqt import gui_hooks
    gui_hooks.deck_browser_will_render_content.append(on_deck_browser_render)
    webview_will_set_content.append(on_overview_render)
    webview_did_receive_js_message.append(on_message)
    _hooks_registered = True
