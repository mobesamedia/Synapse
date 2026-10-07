"""Bounded persistence, failure containment and recovery; no Anki profile used."""
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('diagnostics', Path(__file__).resolve().parents[1] / 'diagnostics.py')
diag = importlib.util.module_from_spec(spec); spec.loader.exec_module(diag)

class FakeSampler:
    def sample(self, pids):
        return {'main_rss': 1234, 'observed_rss_sum': 2345}

class DiagnosticsTests(unittest.TestCase):
    def wait(self, condition):
        end = time.monotonic() + 4
        while not condition() and time.monotonic() < end: time.sleep(.01)
        self.assertTrue(condition())

    def recorder(self, root, **kwargs):
        rec = diag.Recorder(root, sampler=FakeSampler(), interval=.03, **kwargs)
        self.addCleanup(lambda: (rec.stop(), rec.thread and rec.thread.join(3)))
        rec.start(); self.wait(lambda: rec.snapshot().get('samples', 0) > 0)
        return rec

    def test_persistence_and_privacy(self):
        with tempfile.TemporaryDirectory() as root:
            rec = self.recorder(root)
            rec.record('browser.renderer_terminated', exit_code=139, status=2,
                       url='https://secret.example/token', text='private', ms=float('nan'))
            rec.record('https://secret.example')
            rec.record('browser.load_finished', ok=False)
            rec.stop(); rec.thread.join(3)
            data = diag.saved_sessions(root)[0][1]
            self.assertEqual(data['state'], 'stopped')
            self.assertEqual(data['renderer_terminations'], 1)
            self.assertEqual(data['failed_loads'], 1)
            content = ''.join(p.read_text() for p in rec.session_path.iterdir())
            self.assertNotIn('secret', content); self.assertNotIn('private', content)
            self.assertNotIn('NaN', content)

    def test_rotation_retains_summary_and_bounds_disk(self):
        with tempfile.TemporaryDirectory() as root, patch.object(diag, 'MAX_BYTES', 400):
            rec = self.recorder(root)
            for i in range(100): rec.record('browser.back', index=i)
            rec.stop(); rec.thread.join(3)
            files = list(rec.session_path.glob('events-*.jsonl'))
            self.assertLessEqual(len(files), diag.SEGMENTS)
            self.assertLessEqual(sum(p.stat().st_size for p in files), 1200)
            self.assertLessEqual(len(rec.snapshot()['recent_events']), 40)

    def test_queue_overload_and_invalid_payload_are_safe(self):
        rec = diag.Recorder('/not-used')
        for _ in range(2000): rec.record('test.event', value=1)
        rec.record(None); rec.record('test.event', value=object())
        self.assertLessEqual(rec.events.qsize(), 512)
        self.assertGreater(rec.dropped, 0)

    def test_disk_failure_is_contained(self):
        with tempfile.TemporaryDirectory() as root:
            bad = Path(root) / 'file'; bad.write_text('not a directory')
            rec = diag.Recorder(bad, sampler=FakeSampler()); rec.start(); rec.thread.join(3)
            self.assertEqual(rec.snapshot()['state'], 'error')
            rec.record('browser.back')  # Must remain harmless after failure.

    def test_sampling_failure_does_not_stop_events(self):
        with tempfile.TemporaryDirectory() as root:
            rec = self.recorder(root)
            rec.sampler.sample = lambda pids: (_ for _ in ()).throw(OSError('secret'))
            self.wait(lambda: 'sampling_error' in rec.snapshot())
            rec.record('user.observation'); rec.stop(); rec.thread.join(3)
            self.assertEqual(rec.snapshot()['state'], 'stopped')
            self.assertEqual(rec.snapshot()['sampling_error'], 'OSError')

    def test_retention_ignores_unrelated_folders_and_symlinks(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
            for i in range(7):
                folder = Path(root) / ('session-20260101-00000%d-abcdef01' % i)
                folder.mkdir(); (folder / 'summary.json').write_text('{}')
            keep = Path(root) / 'user-data'; keep.mkdir()
            link = Path(root) / 'session-20250101-000000-abcdef01'; link.symlink_to(other)
            rec = self.recorder(root); rec.stop(); rec.thread.join(3)
            self.assertTrue(keep.exists()); self.assertTrue(link.is_symlink())
            self.assertEqual(len(diag.saved_sessions(root)), 5)

    def test_unfinished_session_survives_next_recording(self):
        with tempfile.TemporaryDirectory() as root:
            folder = Path(root) / 'session-20260101-000000-abcdef01'; folder.mkdir()
            (folder / 'summary.json').write_text(json.dumps({'state': 'recording', 'samples': 7}))
            rec = self.recorder(root); rec.stop(); rec.thread.join(3)
            saved = diag.saved_sessions(root)
            self.assertTrue(any(data.get('state') == 'recording' and data['samples'] == 7 for _, data in saved))

    def test_heartbeat_gap_survives_stop(self):
        with tempfile.TemporaryDirectory() as root:
            rec = self.recorder(root)
            rec.last_heartbeat = time.monotonic() - 5
            rec.heartbeat(); rec.stop(); rec.thread.join(3)
            self.assertGreaterEqual(rec.snapshot()['max_heartbeat_gap_ms'], 3900)

    def test_write_failure_during_recording_is_contained(self):
        with tempfile.TemporaryDirectory() as root:
            rec = self.recorder(root)
            with patch.object(diag, '_atomic', side_effect=OSError('private path')):
                self.wait(lambda: rec.snapshot()['state'] == 'error')
            self.assertEqual(rec.snapshot()['error'], 'OSError')
            self.assertNotIn('private', json.dumps(rec.snapshot()))

    def test_abrupt_process_exit_keeps_flushed_records(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as root:
            code = """import sys, time, os
sys.path.insert(0, sys.argv[1])
import diagnostics
rec = diagnostics.Recorder(sys.argv[2], interval=.05)
rec.start()
rec.record('user.observation')
end = time.monotonic() + 5
while not rec.snapshot().get('recent_events') and time.monotonic() < end:
    time.sleep(.02)
os._exit(17)
"""
            result = subprocess.run([sys.executable, '-c', code, str(Path(diag.__file__).parent), root], timeout=8)
            self.assertEqual(result.returncode, 17)
            saved = diag.saved_sessions(root)
            self.assertEqual(saved[0][1]['state'], 'recording')
            self.assertTrue(any(e['event'] == 'user.observation' for e in saved[0][1]['recent_events']))

    def test_duration_limit_stops_cleanly(self):
        with tempfile.TemporaryDirectory() as root, patch.object(diag, 'MAX_DURATION', .05):
            rec = self.recorder(root)
            self.wait(lambda: rec.snapshot()['state'] == 'stopped')
            self.assertEqual(rec.snapshot()['stop_reason'], 'time_limit')

    def test_real_sampler_can_measure_this_process(self):
        result = diag.Sampler().sample([])
        self.assertGreater(result['main_rss'], 0)
        self.assertIn(result['scope'], ('main_and_children', 'main_and_registered_renderers'))

if __name__ == '__main__': unittest.main()
