"""Appearance override limited to the SynapsePro browser landing page."""
import json
from urllib.parse import urlsplit


def is_home_url(url):
    parsed = urlsplit(url)
    return (parsed.scheme == 'https' and parsed.hostname in
            ('synapse-pro.de', 'www.synapse-pro.de') and
            parsed.path.rstrip('/') in ('/browser', '/browser.html'))


def home_theme_script(dark):
    colors = {
        'bg': '#2c2c2c' if dark else '#ffffff',
        'card-bg': '#252525' if dark else '#F5F5F7',
        'card-hover': '#414141' if dark else '#EAEAEC',
        'text-primary': '#ffffff' if dark else '#1d1d1f',
        'text-secondary': '#b0b0b0' if dark else '#6e6e73',
        'search-bg': '#414141' if dark else '#F5F5F7',
        'search-icon': '#b0b0b0' if dark else '#8E8E93',
        'chevron': '#7e7e7e' if dark else '#C7C7CC',
        'accent': '#409CFF' if dark else '#0071D3',
        'sep': 'rgba(255,255,255,.09)' if dark else 'rgba(0,0,0,.08)',
        'top-border': 'rgba(255,255,255,.08)' if dark else 'rgba(0,0,0,.08)',
        'search-border': 'rgba(255,255,255,.12)' if dark else 'rgba(0,0,0,.10)',
        'search-focus': 'rgba(64,156,255,.25)' if dark else 'rgba(0,113,211,.35)',
        'tip-bg': 'rgba(64,156,255,.09)' if dark else 'rgba(0,113,211,.06)',
        'tip-border': 'rgba(64,156,255,.22)' if dark else 'rgba(0,113,211,.18)',
    }
    css = 'html,body{' + ''.join('--'+k+':'+v+'!important;' for k,v in colors.items())
    css += 'color-scheme:'+('dark' if dark else 'light')+';}'
    # Check again inside the document: navigation may finish between dispatch
    # and execution. The override must not reach any other origin or path.
    return '''(() => {
      if(location.protocol !== 'https:' ||
         !['synapse-pro.de','www.synapse-pro.de'].includes(location.hostname) ||
         !['/browser','/browser.html'].includes(location.pathname.replace(/\\/+$/, ''))) return;
      let style=document.getElementById('synapse-browser-appearance');
      if(!style){style=document.createElement('style');style.id='synapse-browser-appearance';document.head.appendChild(style);}
      style.textContent=%s;
    })();''' % json.dumps(css)
