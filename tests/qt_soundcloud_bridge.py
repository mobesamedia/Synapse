"""Native bridge lifecycle with actual Qt objects and fake audio processes.

No network or audio. Run with Anki's Python, without a user profile.
"""
from collections import deque
import importlib
from pathlib import Path
import sys
import types
from unittest.mock import patch

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QCoreApplication, QEvent
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineProfile
from aqt.mpv import MPVBase

app = QApplication(['soundcloud-bridge-test'])
pkg = types.ModuleType('soundcloud_bridge_fixture')
pkg.__path__ = [str(Path(__file__).resolve().parents[1])]
sys.modules[pkg.__name__] = pkg
audio = importlib.import_module(pkg.__name__ + '.soundcloud_audio')


class Process:
    instances = []
    def __init__(self, *_):
        self.commands, self.events, self.closed = [], deque(), False
        self.instances.append(self)
    def command(self, *args): self.commands.append(args)
    def _get_event(self): return self.events.popleft() if self.events else None
    def is_running(self): return not self.closed
    def close(self): self.closed = True


original_options = list(MPVBase.default_argv)
profile = QWebEngineProfile()
page = QWebEnginePage(profile)
bridge = audio.SoundCloudNativeAudio(page)
if bridge.enabled:
    assert any(script.name() == 'SynapsePro SoundCloud native HLS audio'
               for script in profile.scripts().toList())
    assert not any(script.name() == 'SynapsePro SoundCloud native HLS audio'
                   for script in page.scripts().toList())
session = '12345678-1234-1234-1234-123456789abc'
url = 'https://playback.media-streaming.soundcloud.cloud/test/playlist.m3u8'


def message(command, key=1, **values):
    return dict(token=bridge.token, session=session, command=command, id=key) | values


with patch.object(audio, '_AudioProcess', Process):
    bridge.handle_message(message('init'))
    bridge.handle_message(message('load', url=url, token='wrong'))
    bridge.handle_message(message('load', url=url, session='stale'))
    bridge.handle_message(message('load', url='file:///tmp/should-not-play.m3u8'))
    assert not bridge.elements and not Process.instances
    bridge.handle_message(message('load', url=url))
    first = Process.instances[0]
    assert any(cmd[:2] == ('loadfile', url) for cmd in first.commands)
    first.events.append({'event': 'property-change', 'name': 'duration', 'data': 30})
    first.events.append({'event': 'property-change', 'name': 'time-pos', 'data': 3})
    first.events.append({'event': 'property-change', 'name': 'pause', 'data': False})
    bridge._poll()
    assert bridge.elements[1].playing and bridge.elements[1].position == 3
    for key in range(2, 7): bridge.handle_message(message('load', key, url=url))
    assert len(bridge.elements) == bridge.MAX_ELEMENTS
    assert len(Process.instances) == bridge.MAX_ELEMENTS
    bridge.handle_message(message('pause'))
    assert first.commands[-1] == ('set_property', 'pause', True)
    bridge.handle_message(message('seek', position=12))
    assert first.commands[-1] == ('seek', 12, 'absolute+exact')
    bridge.handle_message(message('init', session='abcdefab-1234-1234-1234-123456789abc'))
    assert not bridge.elements and all(process.closed for process in Process.instances)
    bridge.handle_message(message('load', url=url))  # old frame cannot recreate audio
    assert not bridge.elements
    bridge.reset()

# Windows music processes must not reuse Anki's PID-only review-audio pipe.
with patch.object(audio.os, 'name', 'nt'):
    first = object.__new__(audio._AudioProcess)
    second = object.__new__(audio._AudioProcess)
    first._prepare_socket()
    second._prepare_socket()
    assert first._sock_filename != second._sock_filename
    assert first._sock_filename.startswith('synapse-sc-')
assert MPVBase.default_argv == original_options
page.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
assert not any(script.name() == 'SynapsePro SoundCloud native HLS audio'
               for script in profile.scripts().toList()), 'Destroyed views must remove their token-bearing profile script'
profile.deleteLater()
QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
print('PASS native process bounds, token/session validation, allowed streams, event delivery, controls, cleanup, isolated Windows pipes, unchanged Anki mpv defaults')
