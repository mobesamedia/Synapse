"""Read-only celebration design preview. Never consumes real achievement events."""
import html
import json
from pathlib import Path


def render_preview(events, *, dark=False, accent="#397cf6", reduced_motion=False,
                   translate=lambda text: text, live=False, image_url=None):
    def text(value):
        return html.escape(str(value), quote=True)

    def image(filename):
        # Only bundled rank images, never arbitrary paths or remote URLs.
        name = Path(str(filename or "")).name
        path = Path(__file__).resolve().parent / "media" / name
        return (image_url(name) if image_url else path.as_uri()) if name.startswith("rang") and name.endswith(".png") and path.is_file() else ""

    rank, level, challenge = (events.get(key) for key in ("rank", "level", "challenge"))
    stage = ""
    heading_in_stage = False
    if rank:
        old = image(rank.get("old_image"))
        new = image(rank.get("new_image"))
        title = text(translate(rank.get("new_name", "")).replace("<br>", " "))
        subtitle = text(translate("Level {} reached").format(rank.get("level", "")))
        eyebrow = text(translate("New rank unlocked"))
        stage = f'''<div class="stage {'has-old' if old else ''}">
          <div class="aura"></div><div class="orbit"></div>
          {f'<div class="old"><img src="{text(old)}" alt=""><span>{text(translate(rank.get("old_name", "")).replace("<br>", " "))}</span></div>' if old else ''}
          <img class="new" src="{text(new)}" alt="">
          <span class="spark s1">✦</span><span class="spark s2">✧</span>
          <span class="spark s3">◆</span><span class="spark s4">✦</span>
        </div>'''
    elif level:
        title = text(level.get("new", ""))
        subtitle = text(translate("Your learning is paying off."))
        eyebrow = text(translate("Level Up!"))
        heading_in_stage = True
        stage = f'''<div class="stage milestone level-milestone">
          <div class="milestone-disc"></div><div class="milestone-ring"></div>
          <h1 id="title" class="level-number" aria-label="{text(translate('Level {} reached').format(level.get('new', '')))}">{title}</h1>
          <span class="mini-spark left" aria-hidden="true">✦</span><span class="mini-spark right" aria-hidden="true">◆</span>
        </div>'''
    else:
        title = text(translate("Goal achieved!"))
        subtitle = text((challenge or {}).get("text", ""))
        eyebrow = text(translate("Daily Challenge"))
        stage = '''<div class="stage milestone challenge-milestone">
          <div class="milestone-disc"></div>
          <svg class="goal-mark" viewBox="0 0 120 120" aria-hidden="true">
            <circle class="goal-track" cx="60" cy="60" r="44"/>
            <circle class="goal-ring" cx="60" cy="60" r="44" pathLength="1"/>
            <path class="goal-check" d="M39 60l14 14 29-30" pathLength="1"/>
          </svg>
          <span class="mini-spark left" aria-hidden="true">✦</span><span class="mini-spark right" aria-hidden="true">✧</span>
        </div>'''
    extra = ""
    if challenge:
        reward = text(translate("+{} XP claimed." if challenge.get("claimed") else "Claim your +{} XP in the sidebar.").format(challenge.get("xp", 0)))
        extra = '<div class="extra">' + (text(translate("Daily Challenge completed!")) + '<br>' if rank or level else '') + reward + '</div>'
    # Accent is a theme value, validated before placing it into CSS.
    import re
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", accent):
        accent = "#397cf6"
    settings = json.dumps({"dark": bool(dark), "reduced": bool(reduced_motion), "live": bool(live)})
    document = '''<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    :root{color-scheme:light;--bg:#edf0f5;--surface:#fffdfa;--text:#242737;--muted:#646979;--border:#dedfe7;--halo:ACCENT18;--accent:ACCENT}
    html.dark{color-scheme:dark;--bg:#2c2c2c;--surface:#252525;--text:#ffffff;--muted:#b0b0b0;--border:#414141;--halo:ACCENT28}
    *{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .preview-label{text-align:center;color:var(--muted);font-size:11px;margin:18px 16px;line-height:1.5}
    #preview{min-height:calc(100vh - 70px);display:flex;align-items:center;justify-content:center;padding:12px 18px 25px}
    .card{position:relative;width:360px;max-width:100%;border:1px solid var(--border);border-radius:22px;padding:28px 24px 21px;text-align:center;background:var(--surface);box-shadow:0 12px 35px #00000018}
    .close{position:absolute;right:10px;top:9px;width:32px;height:32px;font-size:24px;background:none;border:0;color:var(--muted);cursor:pointer;border-radius:8px}
    .eyebrow{font-size:11px;letter-spacing:.13em;text-transform:uppercase;color:var(--muted);margin:5px 20px 12px}
    .stage{position:relative;height:176px;width:100%;margin:0 auto 8px}
    .new{position:absolute;width:112px;height:112px;object-fit:contain;left:50%;top:28px;transform:translateX(-50%);animation:reveal 1.7s both}
    .has-old .new{left:66%}
    .old{position:absolute;width:88px;left:20%;top:37px;transform:translateX(-50%);animation:evolve 1.7s both}
    .old img{display:block;width:72px;height:72px;object-fit:contain;margin:auto;opacity:.48;animation:oldImage 1.7s both}
    .old span{font-size:10px;line-height:1.25;display:block;color:var(--muted);margin-top:6px;animation:label 1.7s both}
    .aura{position:absolute;width:142px;height:142px;left:50%;top:14px;border-radius:50%;background:var(--halo);transform:translateX(-50%);animation:aura 1.7s both}
    .has-old .aura,.has-old .orbit{left:66%}
    .orbit{position:absolute;left:50%;top:7px;width:156px;height:156px;border:2px solid var(--accent);border-radius:50%;transform:translateX(-50%);opacity:0;animation:orbit 1.7s both}
    .spark{position:absolute;color:#c59739;animation:spark 1.7s both;pointer-events:none}
    .s1{left:36%;top:23px;font-size:20px}.s2{right:0;top:66px;font-size:25px}.s3{left:43%;bottom:15px;font-size:10px;color:var(--accent)}.s4{right:5%;top:5px;font-size:12px;color:var(--accent)}
    h1{font-size:25px;line-height:1.2;letter-spacing:-.025em;margin:9px 0 8px;overflow-wrap:anywhere}
    .subtitle{font-size:14px;color:var(--muted);line-height:1.5;margin:0 0 20px}
    .extra{border-top:1px solid var(--border);font-size:12px;line-height:1.5;padding-top:12px;margin-bottom:16px}.extra span{color:var(--muted)}
    .milestone{height:154px;margin:10px auto 18px;max-width:230px;display:grid;place-items:center}
    .milestone-disc{position:absolute;width:126px;height:126px;border-radius:50%;background:var(--halo);animation:milestoneDisc .8s both}
    .milestone-ring{position:absolute;width:140px;height:140px;border:2px solid var(--accent);border-radius:50%;opacity:0;animation:milestoneRing 1s both}
    .level-number{position:relative;margin:0;font-size:58px;font-weight:750;line-height:1.1;color:var(--accent);letter-spacing:-.04em;animation:levelLift .85s both;font-variant-numeric:tabular-nums}
    .mini-spark{position:absolute;font-size:18px;color:#c59739;animation:smallSpark .95s both}
    .mini-spark.left{left:14px;top:30px}.mini-spark.right{right:15px;bottom:32px;font-size:13px;color:var(--accent)}
    .goal-mark{position:relative;width:120px;height:120px;overflow:visible}
    .goal-track,.goal-ring,.goal-check{fill:none;stroke:var(--accent);stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
    .goal-track{opacity:.13}.goal-ring{transform:rotate(-90deg);transform-origin:60px 60px;stroke-dasharray:1;stroke-dashoffset:0;animation:goalDraw .6s ease-out both}
    .goal-check{stroke-width:6;stroke-dasharray:1;stroke-dashoffset:0;animation:goalDraw .35s .4s ease-out both}
    @keyframes levelLift{0%{opacity:0;transform:translateY(12px) scale(.84)}65%{opacity:1;transform:translateY(-3px) scale(1.06)}100%{opacity:1;transform:none}}
    @keyframes milestoneDisc{0%{opacity:0;transform:scale(.85)}100%{opacity:1;transform:none}}
    @keyframes milestoneRing{0%{opacity:0;transform:scale(.8)}40%{opacity:.4}100%{opacity:0;transform:scale(1.15)}}
    @keyframes smallSpark{0%,35%{opacity:0;transform:scale(.4) translateY(5px)}75%{opacity:1;transform:scale(1.1)}100%{opacity:.75;transform:none}}
    @keyframes goalDraw{from{stroke-dashoffset:1}to{stroke-dashoffset:0}}
    .continue{display:block;width:100%;border:0;border-radius:11px;padding:12px;background:var(--accent);color:white;font-family:inherit;font-size:14px;font-weight:600;cursor:pointer}
    .settings{display:block;margin:14px auto 0;background:none;border:0;font:inherit;font-size:11px;color:var(--muted);cursor:pointer;text-decoration:underline;text-underline-offset:3px}
    button:focus-visible{outline:2px solid var(--accent);outline-offset:3px}
    #closed{display:none;text-align:center;padding:30px;color:var(--muted);line-height:1.6}
    @keyframes evolve{0%,25%{left:50%;transform:translateX(-50%) scale(1.35);filter:brightness(1.2)}65%,100%{left:20%;transform:translateX(-50%) scale(1);filter:none}}
    @keyframes label{0%,55%{opacity:0}100%{opacity:1}}
    @keyframes oldImage{0%,25%{opacity:1}100%{opacity:.48}}
    @keyframes reveal{0%,35%{opacity:0;transform:translateX(-50%) scale(.65)}65%{opacity:1;transform:translateX(-50%) scale(1.08)}85%,100%{opacity:1;transform:translateX(-50%) scale(1)}}
    @keyframes aura{0%,25%{opacity:0;transform:translateX(-50%) scale(.6)}65%,100%{opacity:1;transform:translateX(-50%) scale(1)}}
    @keyframes orbit{0%,20%{opacity:0;transform:translateX(-50%) scale(1.1)}35%{opacity:.7;transform:translateX(-50%) scale(.65)}75%,100%{opacity:0;transform:translateX(-50%) scale(1.2)}}
    @keyframes spark{0%,40%{opacity:0;transform:scale(.5)}70%{opacity:1;transform:scale(1.1)}100%{opacity:.75;transform:scale(1)}}
    html.reduced .stage *{animation:none!important}.reduced .orbit{display:none}
    @media(prefers-reduced-motion:reduce){.stage *{animation:none!important}.orbit{display:none}}
    @media(max-width:340px){.card{padding:25px 16px 18px}.new{width:96px;height:96px;top:35px}.aura{width:122px;height:122px;top:22px}.old{width:66px}.old img{width:58px;height:58px}.s2{right:-4px}h1{font-size:22px}}
    html.live,html.live body{background:transparent}html.live .preview-label{display:none}html.live #preview{min-height:100vh;padding:16px}
    </style><script>const options=OPTIONS;document.documentElement.classList.toggle('live',options.live);document.documentElement.classList.toggle('dark',options.dark);document.documentElement.classList.toggle('reduced',options.reduced);</script>
    </head><body><p class="preview-label">PREVIEW_LABEL</p>
    <main id="preview"><section class="card" role="dialog" aria-modal="true" aria-labelledby="title">
    <button class="close" aria-label="CLOSE">×</button><div class="eyebrow">EYEBROW</div>STAGE
    HEADING<p class="subtitle">SUBTITLE</p>EXTRA
    <button class="continue">CONTINUE</button><button class="settings">SETTINGS</button>
    </section></main><p id="closed">CLOSED</p>
    <script>
    const root=document.getElementById('preview');
    function closePreview(){if(options.live){parent.postMessage('synapse-celebration-close','*');return}root.style.display='none';document.getElementById('closed').style.display='block'}
    document.querySelector('.close').onclick=closePreview;document.querySelector('.continue').onclick=closePreview;
    document.querySelector('.settings').onclick=function(){if(options.live){parent.postMessage('synapse-celebration-settings','*');return}document.querySelector('.preview-label').textContent=SETTINGS_HINT};
    document.addEventListener('keydown',function(e){
      if(e.key==='Escape'){e.preventDefault();closePreview()}
      if(e.key==='Tab' && root.style.display!=='none'){
        const buttons=[...root.querySelectorAll('button')],i=buttons.indexOf(document.activeElement);
        if(e.shiftKey && i<=0){e.preventDefault();buttons.at(-1).focus()}
        else if(!e.shiftKey && (i===buttons.length-1||i===-1)){e.preventDefault();buttons[0].focus()}
      }
    });document.querySelector('.continue').focus({preventScroll:true});
    </script></body></html>'''
    replacements = {"ACCENT":accent, "ACCENT18":accent + "18", "ACCENT28":accent + "28", "OPTIONS":settings,
        "PREVIEW_LABEL":text(translate("Preview only. Your profile stays unchanged.")),
        "CLOSE":text(translate("Close")), "EYEBROW":eyebrow, "STAGE":stage,
        "HEADING":"" if heading_in_stage else f'<h1 id="title">{title}</h1>', "SUBTITLE":subtitle, "EXTRA":extra,
        "CONTINUE":text(translate("Continue")), "SETTINGS":text(translate("Celebration settings")),
        "CLOSED":text(translate("Preview closed. Use Replay to show it again.")),
        "SETTINGS_HINT":json.dumps(translate("Preview only. Celebration preferences will be connected when this design is adopted."))}
    # One substitution pass avoids interpreting user-visible text as tokens.
    return re.sub(r"\b(" + "|".join(sorted(replacements, key=len, reverse=True)) + r")\b",
                  lambda match: replacements[match.group()], document)
