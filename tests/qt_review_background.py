"""Temporary-profile renderer checks. Never opens the user's collection."""
import base64, importlib, json, re, sys, tempfile, types
from pathlib import Path
import aqt
from aqt.qt import QApplication, QMainWindow, QWidget, QPixmap, QColor
from aqt.theme import theme_manager
app = QApplication(['review-background-test'])
root = Path(__file__).resolve().parents[1]
pkg = types.ModuleType('background_fixture'); pkg.__path__ = [str(root)]; sys.modules[pkg.__name__] = pkg
locales = types.ModuleType(pkg.__name__ + '.locales'); locales._ = lambda s:s; sys.modules[locales.__name__] = locales
with tempfile.TemporaryDirectory() as tmp:
    mw=QMainWindow(); mw.setCentralWidget(QWidget()); mw.resize(900,700)
    mw.pm=types.SimpleNamespace(profileFolder=lambda:tmp,night_mode=lambda:False)
    mw.state='review'; mw.web=types.SimpleNamespace(eval=lambda script:None)
    aqt.mw=mw
    bg=importlib.import_module(pkg.__name__+'.custom_background')
    Path(bg.image_path()).parent.mkdir(parents=True)
    pixmap=QPixmap(300,200);pixmap.fill(QColor('#a54768'));assert pixmap.save(bg.image_path())
    bg._settings={'custom_background_enabled':True}
    assert bg.reviewer_background_css()==''
    bg._settings['custom_background_review_enabled']=True
    light=bg.reviewer_background_css()
    def pixel(css, x=150, y=100):
        data=base64.b64decode(re.search(r'base64,([^"]+)', css)[1])
        image=QPixmap();assert image.loadFromData(data)
        return image.toImage().pixelColor(x,y)
    assert 'linear-gradient' not in light
    assert pixel(light).red()>230 and pixel(light).green()>210
    cache=bg._review_cache
    assert bg.reviewer_background_css()==light and bg._review_cache is cache
    theme_manager.night_mode=True
    dark=bg.reviewer_background_css()
    assert pixel(dark).red()<65 and pixel(dark).green()<50
    assert pixel(dark,150,199).red()<65
    theme_manager.night_mode=False
    assert bg.reviewer_background_css()==light
    cache=bg._review_cache
    bg._settings['custom_background_review_intensity']=0
    assert pixel(bg.reviewer_background_css()).red()>=254
    bg._settings['custom_background_review_intensity']=100
    assert abs(pixel(bg.reviewer_background_css()).red()-165)<4
    bg._settings['custom_background_review_blur']=12
    bg.reviewer_background_css();assert bg._review_cache is not cache
    scripts=[]
    mw.web.eval=scripts.append
    bg._sync_reviewer_background()
    assert 'data:image/jpeg;base64,' in scripts[-1]
    mw.state='deckBrowser'
    count=len(scripts);bg._sync_reviewer_background();assert len(scripts)==count
    mw.state='review'
    bg._settings['custom_background_review_enabled']=False
    assert bg.reviewer_background_css()==''
    from aqt.mediasrv import _builtin_data
    reviewer_css = _builtin_data('data/web/css/reviewer.css').decode()
    bg._sync_reviewer_background()
    assert 'const css="";' in scripts[-1]
    # Export generated styles for the browser's real CSS cascade tests.
    Path('/tmp/synapse-review-background-fixture.json').write_text(json.dumps({
        'css':light,'reviewerCss':reviewer_css,'darkCss':dark,'on':bg.canvas_script(True),'off':bg.canvas_script(False)}))
    print('PASS default off, cached blur, intensity limits, disabling, local image')
