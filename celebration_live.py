"""Dashboard celebrations sharing the approved preview renderer."""
import html
from .celebration_preview import render_preview
from .locales import _
from .theme import palette


def select_events(events, settings):
    if not settings.get("gamification_popups_enabled", True):
        return {}
    return {key: value for key, value in events.items()
            if key in ("rank", "level", "challenge")
            and settings.get("gamification_popup_" + key, key != "level")}


def render_celebration_modal(events):
    if not events:
        return ""
    from aqt import mw
    from aqt.theme import theme_manager
    package = mw.addonManager.addonFromModule(__name__)
    copied = {key: dict(value) for key, value in events.items()}
    if copied.get("rank"):
        for key in ("old_image", "new_image"):
            copied["rank"][key] = str(copied["rank"].get(key) or "").replace(".gif", ".png")
    document = render_preview(copied, dark=theme_manager.night_mode, live=True,
                              accent=palette(theme_manager.night_mode)["blue"],
                              translate=_, image_url=lambda name: f"/_addons/{package}/media/{name}")
    return ('<iframe id="synapse-celebration-frame" title="' + html.escape(_("Celebration"), quote=True)
            + '" style="position:fixed;inset:0;width:100%;height:100%;border:0;z-index:10001" srcdoc="'
            + html.escape(document, quote=True) + '"></iframe>' + '''<script>
    (function(){
      if(window.synapseCelebrationCleanup)window.synapseCelebrationCleanup();
      const frame=document.getElementById('synapse-celebration-frame'),previous=document.activeElement;
      const siblings=[...document.body.children].filter(el=>el!==frame && !el.contains(frame));
      const states=siblings.map(el=>[el,el.inert]);siblings.forEach(el=>el.inert=true);
      function cleanup(){window.removeEventListener('message',receive);states.forEach(([el,state])=>el.inert=state);window.synapseCelebrationCleanup=null;}
      function receive(event){
        if(event.source!==frame.contentWindow)return;
        if(!['synapse-celebration-close','synapse-celebration-settings'].includes(event.data))return;
        cleanup();frame.remove();if(previous&&previous.isConnected)previous.focus();
        if(event.data==='synapse-celebration-settings')pycmd('pycmd:synapsepro:celebration_settings');
      }
      window.addEventListener('message',receive);window.synapseCelebrationCleanup=cleanup;
    })();</script>''')
