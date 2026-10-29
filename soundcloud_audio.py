"""Widget-scoped native HLS playback for Chromium builds without AAC.

The official SoundCloud widget still authorizes streams and owns its UI. Audio
uses a separate instance of Anki's bundled mpv, never Anki's review audio queue.
No stream-resolution API, external browser, codec installation or data migration.
"""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path
import re
import secrets
import shutil
from urllib.parse import urlsplit

from aqt.mpv import MPVBase
from aqt.sound import _packagedCmd
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWebEngineCore import QWebEngineScript


def is_soundcloud_stream(url):
    """Only accept HTTPS HLS streams on SoundCloud's actual media CDNs."""
    if not isinstance(url, str) or len(url) > 16384 or any(c in url for c in "\r\n\t"):
        return False
    try:
        parsed = urlsplit(url)
        host = (parsed.hostname or "").lower()
        return (parsed.scheme == "https" and not parsed.username and not parsed.password
                and parsed.port in (None, 443) and parsed.path.endswith(".m3u8")
                and any(host == domain or host.endswith("." + domain)
                        for domain in ("sndcdn.com", "soundcloud.cloud")))
    except ValueError:
        return False


class _AudioProcess(MPVBase):
    # Keep options compatible with the older mpv shipped by some Anki builds.
    # No user scripts/config and no video window or global media key ownership.
    default_argv = ['--idle=yes', '--no-terminal', '--force-window=no',
                    '--audio-display=no', '--keep-open=no', '--no-config',
                    '--vid=no', '--pause=yes', '--input-media-keys=no']

    def __init__(self, executable, environment):
        self.executable, self.popenEnv = executable, environment
        super().__init__(window_id=None, debug=False)

    def command(self, *arguments):
        return self._send_request({'command': list(arguments)}, timeout=.5)

    def _prepare_socket(self):
        # Anki's default Windows pipe name uses only the host PID. Reusing it
        # would collide with review audio (and other preloaded music elements).
        if os.name == 'nt':
            self._sock_filename = 'synapse-sc-%s-%s' % (os.getpid(), secrets.token_hex(12))
        else:
            super()._prepare_socket()


@dataclass
class _Stream:
    process: _AudioProcess
    url: str
    duration: float = 0
    position: float = 0
    volume: float = 1
    muted: bool = False
    playing: bool = False
    failed: bool = False


class SoundCloudNativeAudio(QObject):
    """A bounded set of independent audio elements for one SoundCloud view."""
    MAX_ELEMENTS = 4

    def __init__(self, page):
        super().__init__(page)
        self.page = page
        self.token = secrets.token_hex(24)
        self.session = None
        self.elements = {}
        command, self.environment = _packagedCmd(['mpv'])
        self.executable = command[0]
        self.enabled = bool(shutil.which(self.executable))
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._poll)
        if self.enabled:
            script = QWebEngineScript()
            script.setName('SynapsePro SoundCloud native HLS audio')
            script.setInjectionPoint(QWebEngineScript.InjectionPoint.DocumentCreation)
            script.setWorldId(QWebEngineScript.ScriptWorldId.MainWorld)
            script.setRunsOnSubFrames(True)
            source = Path(__file__).with_name('soundcloud_native_audio.js').read_text(encoding='utf-8')
            script.setSourceCode(source.replace('__SYNAPSE_AUDIO_TOKEN__', json.dumps(self.token)))
            # Page-scoped scripts do not reliably reach cross-origin renderer
            # processes in newer Qt builds. This dedicated music profile serves
            # only the player views; the script itself is restricted to the
            # official widget's exact host/path and leaves every other frame alone.
            profile = page.profile()
            profile.scripts().insert(script)
            def remove_script():
                try:
                    profile.scripts().remove(script)
                except RuntimeError:
                    pass  # The profile may already be gone during app shutdown.
            page.destroyed.connect(remove_script)
            page.loadStarted.connect(self.reset)
        # Also reap processes when the view is destroyed outside normal profile
        # cleanup. The closure only needs the dictionary, not a living QObject.
        elements = self.elements
        def close_processes():
            for stream in list(elements.values()):
                try:
                    stream.process.close()
                except Exception:
                    pass
            elements.clear()
        page.destroyed.connect(close_processes)

    def _send(self, element_id, event, **values):
        if element_id not in self.elements:
            return
        payload = dict(type='synapse-native-audio', token=self.token, session=self.session,
                       id=element_id, event=event, **values)
        self.page.runJavaScript(
            "(function(){var f=document.getElementById('scplayer');"
            "if(f&&f.contentWindow)f.contentWindow.postMessage(%s,'https://w.soundcloud.com');})();"
            % json.dumps(payload))

    def _dispose(self, element_id):
        stream = self.elements.pop(element_id, None)
        if stream:
            try:
                stream.process.close()
            except Exception:
                pass

    def reset(self):
        self.timer.stop()
        self.session = None
        for element_id in list(self.elements):
            self._dispose(element_id)

    def pause_all(self):
        for key, stream in list(self.elements.items()):
            self._command(key, stream, 'set_property', 'pause', True)
            stream.playing = False

    def _command(self, key, stream, *arguments):
        try:
            return stream.process.command(*arguments)
        except Exception:
            stream.failed = True
            stream.playing = False
            self._send(key, 'error')
            return None

    def _poll(self):
        # MPVBase's reader thread queues events. Drain them on Qt's GUI thread;
        # no blocking media/property polling and no JS from a worker thread.
        for key, stream in list(self.elements.items()):
            if stream.failed:
                continue
            if not stream.process.is_running():
                stream.failed = True
                stream.playing = False
                self._send(key, 'error')
                continue
            for _ in range(100):
                event = stream.process._get_event()
                if event is None:
                    break
                if event.get('event') == 'property-change':
                    name, value = event.get('name'), event.get('data')
                    if name == 'duration' and isinstance(value, (int, float)) and math.isfinite(value) and value > 0:
                        stream.duration = value
                        self._send(key, 'metadata', duration=value)
                    elif name == 'time-pos' and isinstance(value, (int, float)) and math.isfinite(value):
                        stream.position = value
                        self._send(key, 'position', position=value)
                    elif name == 'pause' and isinstance(value, bool):
                        stream.playing = not value
                        self._send(key, 'pause' if value else 'playing')
                    elif name == 'demuxer-cache-state' and isinstance(value, dict):
                        ranges = value.get('seekable-ranges', [])
                        self._send(key, 'buffer', ranges=[[item['start'], item['end']] for item in ranges
                            if isinstance(item, dict) and isinstance(item.get('start'), (int, float))
                            and isinstance(item.get('end'), (int, float))
                            and math.isfinite(item['start']) and math.isfinite(item['end'])])
                elif event.get('event') == 'end-file':
                    stream.playing = False
                    if event.get('reason') == 'eof':
                        self._send(key, 'ended')
                    elif event.get('reason') == 'error':
                        stream.failed = True
                        self._send(key, 'error')

    def handle_message(self, data):
        if not self.enabled or not isinstance(data, dict) or data.get('token') != self.token:
            return
        command, session = data.get('command'), data.get('session')
        if command == 'init':
            if isinstance(session, str) and re.fullmatch(r'[a-fA-F0-9-]{36}', session):
                self.reset()
                self.session = session
            return
        if not self.session or session != self.session:
            return
        key = data.get('id')
        if type(key) is not int or not 0 < key < 1000000:
            return
        if command == 'dispose':
            self._dispose(key)
            return
        if command == 'load':
            if not is_soundcloud_stream(data.get('url')):
                return
            if key not in self.elements and len(self.elements) >= self.MAX_ELEMENTS:
                return
            self._dispose(key)
            try:
                stream = _Stream(_AudioProcess(self.executable, self.environment), data['url'])
            except Exception:
                # Let the element's pending play fail through its normal HTML
                # media error path; do not expose signed URLs in diagnostics.
                self.elements[key] = _Stream(None, data['url'], failed=True)
                self._send(key, 'error')
                return
            self.elements[key] = stream
            for index, property_name in enumerate(('duration', 'time-pos', 'pause', 'demuxer-cache-state')):
                self._command(key, stream, 'observe_property', index, property_name)
            self._volume(key, stream, data)
            self._command(key, stream, 'loadfile', stream.url, 'replace')
            self.timer.start()
            return
        stream = self.elements.get(key)
        if not stream or stream.failed:
            return
        if command == 'play':
            for other_key, other in list(self.elements.items()):
                if other is not stream and other.playing:
                    self._command(other_key, other, 'set_property', 'pause', True)
            self._command(key, stream, 'set_property', 'pause', False)
        elif command == 'pause':
            self._command(key, stream, 'set_property', 'pause', True)
            self._send(key, 'pause')
        elif command == 'reload':
            self._command(key, stream, 'loadfile', stream.url, 'replace')
        elif command == 'seek':
            position = data.get('position')
            if isinstance(position, (int, float)) and math.isfinite(position) and 0 <= position <= 604800:
                self._command(key, stream, 'seek', position, 'absolute+exact')
        elif command == 'volume':
            self._volume(key, stream, data)

    def _volume(self, key, stream, data):
        volume = data.get('volume', 1)
        if isinstance(volume, (int, float)) and math.isfinite(volume):
            stream.volume = max(0, min(1, volume))
            self._command(key, stream, 'set_property', 'volume', stream.volume * 100)
        stream.muted = bool(data.get('muted', False))
        self._command(key, stream, 'set_property', 'mute', stream.muted)
