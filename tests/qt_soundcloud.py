"""Live official SoundCloud widget, actual Qt audio, isolated temporary profile.

Run explicitly with Anki's Python: this integration test needs network/audio.
It never opens or reads a real Anki collection or browser profile.
"""
import copy
import importlib
import json
import sys
import tempfile
import time
import types
from pathlib import Path

import aqt
from aqt.qt import QApplication, QMainWindow, QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWebEngineCore import QWebEngineScript

ROOT = Path(__file__).resolve().parents[1]
app = QApplication(['soundcloud-integration-test'])
app.setQuitOnLastWindowClosed(False)
pkg = types.ModuleType('soundcloud_fixture')
pkg.__path__ = [str(ROOT)]
sys.modules[pkg.__name__] = pkg
constants = types.ModuleType(pkg.__name__ + '.constants')
constants.addon_path = str(ROOT)
constants.icons_folder = None
constants.ADDON_NAME_LAUNCHER = 'SoundCloudTest'
sys.modules[constants.__name__] = constants
locales = types.ModuleType(pkg.__name__ + '.locales')
locales._ = lambda text: text
sys.modules[locales.__name__] = locales


def wait(predicate, description, timeout=40):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if predicate():
            return
        time.sleep(.02)
    raise AssertionError('Timed out: ' + description)


def pump(seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(.02)


def js(page, code):
    result = []
    page.runJavaScript(code, result.append)
    wait(lambda: bool(result), 'JavaScript callback', 5)
    return result[0]


with tempfile.TemporaryDirectory(prefix='synapse-soundcloud-') as temporary:
    config = {
        'synapse_music_state': {'mode': 'soundcloud', 'scVol': 28, 'vol': 17},
        'synapse_music_sc_custom_urls': ['https://soundcloud.com/example/saved-custom-track'],
        'synapse_user_tracks': [{'file': 'original.mp3', 'title': 'My saved track'}],
        'unrelated_notebook': {'html': '<h2>Keep exactly</h2><p><b>Original</b></p>'},
    }
    saved = copy.deepcopy(config)
    class Collection:
        def get_config(self, key, default=None): return copy.deepcopy(config.get(key, default))
        def set_config(self, key, value): config[key] = copy.deepcopy(value)

    host = QMainWindow()
    host.pm = types.SimpleNamespace(profileFolder=lambda: temporary, night_mode=lambda: False)
    host.col = Collection()
    aqt.mw = host
    music = importlib.import_module(pkg.__name__ + '.background_music')
    music.MiniMusicPlayer._fetch_sc_artwork = lambda *_: None
    window = music._ensure_window()
    try:
        window.show()
        native = window._sc_page._native_sc_audio
        assert native.enabled, 'Ankis bundled mpv is needed for this regression test'
        wait(lambda: window._ui_ready and window._sc_boot_done, 'official widget ready')
        assert not window._sc_playing and not native.elements, 'Do not autoplay on opening'
        original_title = window._sc_now
        wait(lambda: 'Nymano' in window._sc_now, 'first track metadata')
        original_title = window._sc_now

        # Click the actual upper button through Qt's mouse event handling.
        box = js(window._ui_page, "JSON.stringify((function(){var r=document.getElementById('sc-play').getBoundingClientRect();return {x:r.x+r.width/2,y:r.y+r.height/2};})())")
        point = json.loads(box)
        QTest.mouseClick(window.ui_view.focusProxy(), Qt.MouseButton.LeftButton,
                         pos=QPoint(round(point['x']), round(point['y'])))
        def playing():
            return any(stream.playing and stream.position > .75 for stream in native.elements.values())
        wait(playing, 'upper Play starts real native audio')
        wait(lambda: window._sc_playing, 'UI shows playing')
        assert all(not stream.failed for stream in native.elements.values())
        window._sc_js('scPause();')
        wait(lambda: not window._sc_playing, 'pause')
        wait(lambda: all(not stream.playing for stream in native.elements.values()), 'native pause state')

        # Exercise the orange button inside the real cross-origin widget.
        # This test-only script has no part in the production player adapter.
        click = QWebEngineScript()
        click.setName('SoundCloud integration test click')
        click.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
        click.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentReady)
        click.setRunsOnSubFrames(True)
        click.setSourceCode("""if(location.hostname==='w.soundcloud.com'){
          window.addEventListener('message',function(e){if(e.source===parent&&e.data==='soundcloud-test-click'){
            var button=document.querySelector('.playButton');
            console.log('SCBRIDGE:'+JSON.stringify({type:'qa',found:!!button,
              buttons:Array.from(document.querySelectorAll('[role=button],button')).slice(0,8).map(b=>b.outerHTML.slice(0,250))}));
            if(button)button.click();
          }});
        }""")
        # Like the production adapter, this listener must reach the widget's
        # cross-origin renderer on newer Qt versions.
        window._sc_page.profile().scripts().insert(click)
        qa = []
        original_callback = window._sc_page._on_message
        window._sc_page._on_message = lambda data: qa.append(data) if data.get('type')=='qa' else original_callback(data)
        # Qt snapshots injected scripts at top-level navigation. Reload this
        # isolated view once to install the test listener in its child frame.
        previous_session = native.session
        window.sc_view.reload()
        wait(lambda: not native.elements, 'reload releases old audio')
        wait(lambda: native.session and native.session != previous_session, 'new audio session')
        wait(lambda: js(window._sc_page, '!!window._widgetReady'), 'widget reload')
        js(window._sc_page, "document.getElementById('scplayer').contentWindow.postMessage('soundcloud-test-click','https://w.soundcloud.com')")
        wait(lambda: bool(qa), 'widget click listener installed')
        assert qa[0]['found'], qa[0]
        wait(playing, 'orange widget Play starts real audio')
        window.grab().save('/tmp/synapse-soundcloud-native-player.png')
        window._sc_js('widget.seekTo(15000);')
        wait(lambda: any(stream.position >= 14.5 for stream in native.elements.values()), 'seek')
        wait(lambda: any(stream.position > 15.5 for stream in native.elements.values()), 'audio continues after seek')
        window._on_ui_message({'a': 'scVolume', 'v': 23})
        wait(lambda: any(abs(stream.volume - .23) < .01 for stream in native.elements.values()), 'volume')
        window._sc_js('scNext();')
        wait(lambda: window._sc_now != original_title and 'Philanthrope' in window._sc_now, 'next track')
        wait(playing, 'next track plays')
        window._sc_js('scPrev();')
        wait(lambda: window._sc_now == original_title, 'previous track')
        wait(playing, 'previous track plays')
        assert window._set_sc_url(music.SC_STATIONS[1][1])
        wait(lambda: window._sc_now != original_title, 'different station metadata')
        wait(playing, 'different station plays with a new iframe session')
        assert window._set_sc_url(music.DEFAULT_SC_URL)
        wait(lambda: window._sc_now == original_title, 'original station metadata')
        wait(playing, 'original station resumes')
        assert all(abs(stream.volume - .23) < .01 for stream in native.elements.values()), 'Volume survives station changes'
        duration = max(stream.duration * 1000 for stream in native.elements.values())
        window._sc_js('widget.seekTo(%s);' % (duration - 1500))
        wait(lambda: 'Philanthrope' in window._sc_now, 'playlist advances at end of track')
        wait(playing, 'automatic next track plays')
        window.hide()
        pump(1)
        assert playing(), 'Music continues while the window is hidden'
        window.show()
        window._set_mode('local')
        wait(lambda: all(not stream.playing for stream in native.elements.values()), 'switching to local pauses SoundCloud')
        window._set_mode('soundcloud')
        pump(.5)
        assert not window._sc_playing, 'Changing modes must not restart audio'
        assert config['synapse_music_sc_custom_urls'] == saved['synapse_music_sc_custom_urls']
        assert config['synapse_user_tracks'] == saved['synapse_user_tracks']
        assert config['unrelated_notebook'] == saved['unrelated_notebook']
        print('PASS official SoundCloud widget: upper/orange Play, AAC audio progress, pause, seek, retained volume, next/previous, station changes, end-of-track advance, reload, hide/show, mode switch, saved data unchanged', flush=True)
    finally:
        music.cleanup_music_player()
        app.sendPostedEvents(None, 0)
        pump(.3)
        host.close()
