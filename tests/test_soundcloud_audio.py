"""CDN allowlist checks without importing Anki or creating a media player."""
import ast
from pathlib import Path
import unittest
from urllib.parse import urlsplit

source = Path(__file__).resolve().parents[1] / 'soundcloud_audio.py'
tree = ast.parse(source.read_text())
function = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'is_soundcloud_stream')
scope = {'urlsplit': urlsplit}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(source), 'exec'), scope)
allowed = scope['is_soundcloud_stream']


class SoundCloudStreamTests(unittest.TestCase):
    def test_official_signed_hls(self):
        self.assertTrue(allowed('https://playback.media-streaming.soundcloud.cloud/track/aac_160k/id/playlist.m3u8?expires=123&Signature=example'))
        self.assertTrue(allowed('https://cf-hls-media.sndcdn.com/playlist/track/playlist.m3u8'))

    def test_disallow_local_files_and_other_protocols(self):
        for url in ('file:///tmp/audio.m3u8', 'http://cf-hls-media.sndcdn.com/p.m3u8',
                    'ftp://sndcdn.com/p.m3u8', 'data:audio/aac;base64,YQ=='):
            self.assertFalse(allowed(url), url)

    def test_disallow_other_hosts_and_credentials(self):
        for url in ('https://localhost/p.m3u8', 'https://soundcloud.cloud.example.com/p.m3u8',
                    'https://notsndcdn.com/p.m3u8', 'https://user:password@sndcdn.com/p.m3u8',
                    'https://sndcdn.com:8080/p.m3u8', 'https://soundcloud.com/user/track'):
            self.assertFalse(allowed(url), url)

    def test_disallow_malformed_or_oversized_requests(self):
        for url in (None, {}, 1, 'https://[invalid/p.m3u8', 'https://sndcdn.com:p/p.m3u8',
                    'https://sndcdn.com/p.mp3', 'https://sndcdn.com/p.m3u8\n',
                    'https://sndcdn.com/p.m3u8?' + 'x' * 17000):
            self.assertFalse(allowed(url))


if __name__ == '__main__':
    unittest.main()
