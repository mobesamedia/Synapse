"""Dashboard surface opacity and explicitly enabled, bounded backdrop blur."""
import math


def surface_opacity(value=100):
    try:
        number = float(value)
        if not math.isfinite(number):
            return 100
        return max(0, min(100, round(number)))
    except (TypeError, ValueError, OverflowError):
        return 100


def glass_strength(value=6):
    try:
        number = float(value)
        if not math.isfinite(number):
            return 6
        return max(2, min(16, round(number)))
    except (TypeError, ValueError, OverflowError):
        return 6


def shadow_strength(value=0):
    try:
        number = float(value)
        return max(0, min(100, round(number))) if math.isfinite(number) else 0
    except (TypeError, ValueError, OverflowError):
        return 0


def dashboard_surface_css(value=100, glass_enabled=False, strength=6, shadow=0, enabled=True):
    # Keep saved customization values, but render the original surfaces when off.
    if enabled is False:
        return ""
    opacity = surface_opacity(value)
    shadow = shadow_strength(shadow)
    if opacity == 100 and shadow == 0:
        return ""
    glass_css = ''
    if glass_enabled is True and opacity < 100:
        radius = glass_strength(strength)
        glass_css = f'''
        @supports (backdrop-filter: blur(1px)) {{
          body.deckbrowser .daily-widget,
          body.deckbrowser .gamewidget,
          body.deckbrowser .stats-widget-container,
          body.deckbrowser .deadline-bar-container,
          body.deckbrowser .sp-min-box,
          body.deckbrowser .decks-container,
          body.deckbrowser > center > table {{backdrop-filter:blur({radius}px);}}
        }}
        '''
    effects = surface_effects_css()
    glass = 'var(--sp-glass-rim)' if glass_enabled is True and opacity < 100 else '0 0 0 transparent'
    return f'''<style id="synapse-dashboard-surface-opacity">
    {effects}
    body.deckbrowser {{ --sp-shadow-alpha: {shadow * 0.0018:.4f}; }}
    body.deckbrowser.night_mode {{ --sp-shadow-alpha: {shadow * 0.0036:.4f}; }}
    body.deckbrowser .daily-widget,
    body.deckbrowser .gamewidget,
    body.deckbrowser .stats-widget-container,
    body.deckbrowser .deadline-bar-container,
    body.deckbrowser .sp-min-box,
    body.deckbrowser .decks-container,
    body.deckbrowser > center > table {{
      box-shadow: {glass}, 0 5px 18px rgba(0,0,0,var(--sp-shadow-alpha)) !important;
    }}
    body.deckbrowser .daily-widget,
    body.deckbrowser .gamewidget,
    body.deckbrowser .stats-widget-container,
    body.deckbrowser .deadline-bar-container {{
      background-color:color-mix(in srgb, var(--stat-bg) {opacity}%, transparent) !important;
    }}
    body.deckbrowser .sp-min-box {{
      background-color:color-mix(in srgb, var(--sp-min-surface) {opacity}%, transparent) !important;
    }}
    body.deckbrowser .decks-container,
    body.deckbrowser > center > table {{
      background-color:color-mix(in srgb, var(--medical-bg-paper) {opacity}%, transparent) !important;
    }}
    /* The wrapper supplies the surface once; an inner table must not add an
       opaque layer. Row hover and selection indicators remain untouched. */
    body.deckbrowser .decks-container table {{background-color:transparent !important;}}
    {glass_css}
    </style>'''


def glass_backdrop_html(image_uri, geometry, overlay=0, position='center'):
    """Mirror the native wallpaper within Chromium, aligned to its Qt canvas."""
    import json
    payload = json.dumps({'image': image_uri, 'geometry': geometry,
                          'overlay': max(0, min(70, int(overlay))),
                          'position': position if position in ('top', 'center', 'bottom') else 'center'}).replace('</', '<\\/')
    return '''<script>(function(data){
      if(!window.CSS || !CSS.supports('backdrop-filter','blur(1px)'))return;
      const layer=document.createElement('div');layer.id='synapse-glass-wallpaper';layer.setAttribute('aria-hidden','true');
      Object.assign(layer.style,{position:'fixed',zIndex:'-1',pointerEvents:'none',backgroundRepeat:'no-repeat',backgroundSize:'cover',backgroundPosition:'center '+data.position});
      layer.style.backgroundImage='linear-gradient(rgba(0,0,0,'+(data.overlay/100)+'),rgba(0,0,0,'+(data.overlay/100)+')),url("'+data.image+'")';
      document.body.prepend(layer);
      window.__synapseSyncGlassBackdrop=function(geometry){
        data.geometry=geometry;const scale=window.innerWidth/Math.max(1,geometry.viewWidth);
        layer.style.left=(-geometry.x*scale)+'px';layer.style.top=(-geometry.y*scale)+'px';
        layer.style.width=(geometry.width*scale)+'px';layer.style.height=(geometry.height*scale)+'px';
      };
      window.__synapseSyncGlassBackdrop(data.geometry);
      window.addEventListener('resize',()=>window.__synapseSyncGlassBackdrop(data.geometry));
    })(''' + payload + ''');</script>'''


def deck_list_width_css(wide=True):
    if wide is not False:
        return ''
    return '''<style id="synapse-compact-deck-list">
    body.deckbrowser.deckbrowser:not(.synapse-minimal-dashboard) .decks-container,
    body.deckbrowser.deckbrowser:not(.synapse-minimal-dashboard) > center > table {
      width:min(600px,calc(100vw - 48px)) !important;
      min-width:0 !important;max-width:600px !important;
    }
    body.deckbrowser.deckbrowser:not(.synapse-minimal-dashboard) .decks-container table {
      width:100% !important;min-width:0 !important;max-width:100% !important;
    }
    </style>'''


def surface_effects_css():
    """Static material highlights, shared by dashboard and settings preview."""
    return """
    :root { --sp-glass-rim: inset 0 1px 0 rgba(255,255,255,.8),
      inset 1px 0 0 rgba(255,255,255,.3), inset 0 -1px 0 rgba(0,0,0,.08),
      inset 0 0 10px rgba(255,255,255,.2); }
    body.night_mode, html.dark, body.dark { --sp-glass-rim:
      inset 0 1px 0 rgba(220,220,220,.26), inset 1px 0 0 rgba(220,220,220,.1),
      inset 0 -1px 0 rgba(0,0,0,.28), inset 0 0 10px rgba(210,210,210,.07); }
    """
