"""Opt-in, local diagnostics. No Qt objects or collection access in the worker.

Feature hooks must pass only fixed event names and numeric/boolean fields. Never
pass page text, URLs, user input, exception messages or filesystem paths.
"""
from __future__ import annotations

import json
import math
import os
import platform
import queue
import re
import shutil
import subprocess
import threading
import time
import uuid
from collections import deque
from pathlib import Path

INTERVAL = 5.0
MAX_BYTES = 2 * 1024 * 1024
SEGMENTS = 3
KEEP_SESSIONS = 5
MAX_DURATION = 8 * 60 * 60
FIELDS = {"pid", "ok", "visible", "status", "exit_code", "index", "count", "ms", "value"}
NAME = re.compile(r"^[a-z][a-z0-9_.]{0,63}$")
SESSION = re.compile(r"^session-[0-9]{8}-[0-9]{6}-[a-f0-9]{8}$")


def _atomic(path, data):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(data, handle, ensure_ascii=False, allow_nan=False)
        handle.flush()
    os.replace(temporary, path)


def _rss(pids):
    """Dependency-free current RSS, not historical peak. Worker thread only."""
    result = {}
    if os.name == 'nt':
        import ctypes as c
        from ctypes import wintypes as w
        class Counters(c.Structure):
            _fields_ = [('cb', w.DWORD), ('faults', w.DWORD)] + [
                (name, c.c_size_t) for name in ('peak', 'rss', 'pp', 'p', 'np', 'n', 'page', 'peakpage')]
        kernel = c.WinDLL('kernel32', use_last_error=True)
        psapi = c.WinDLL('psapi', use_last_error=True)
        kernel.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        kernel.OpenProcess.restype = w.HANDLE
        kernel.CloseHandle.argtypes = [w.HANDLE]
        psapi.GetProcessMemoryInfo.argtypes = [w.HANDLE, c.POINTER(Counters), w.DWORD]
        for pid in pids:
            handle = kernel.OpenProcess(0x1000, False, pid)
            if handle:
                try:
                    info = Counters(); info.cb = c.sizeof(info)
                    if psapi.GetProcessMemoryInfo(handle, c.byref(info), info.cb):
                        result[pid] = int(info.rss)
                finally:
                    kernel.CloseHandle(handle)
    elif platform.system() == 'Linux':
        for pid in pids:
            try:
                result[pid] = int(Path('/proc', str(pid), 'statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
            except (OSError, ValueError, IndexError):
                pass
    else:
        # No shell, no command lines/environment collected, strict timeout.
        output = subprocess.run(['/bin/ps', '-o', 'pid=,rss=', '-p', ','.join(map(str, pids))],
                                capture_output=True, text=True, timeout=1, check=False)
        for line in output.stdout.splitlines():
            parts = line.split()
            if len(parts) == 2:
                result[int(parts[0])] = int(parts[1]) * 1024
    return result


def _system_memory():
    """Best-effort available memory; macOS value is explicitly an estimate."""
    if os.name == 'nt':
        import ctypes as c
        class Memory(c.Structure):
            _fields_ = [('length', c.c_ulong), ('load', c.c_ulong)] + [
                (name, c.c_ulonglong) for name in ('total', 'available', 'page_total', 'page_free', 'virtual_total', 'virtual_free', 'extended')]
        memory = Memory(); memory.length = c.sizeof(memory)
        if c.windll.kernel32.GlobalMemoryStatusEx(c.byref(memory)):
            return memory.available, memory.total, 'os_available'
    elif platform.system() == 'Linux':
        values = {}
        for line in Path('/proc/meminfo').read_text().splitlines():
            key, value = line.split(':', 1)
            values[key] = int(value.strip().split()[0]) * 1024
        return values.get('MemAvailable'), values.get('MemTotal'), 'os_available'
    elif platform.system() == 'Darwin':
        import ctypes as c
        libc = c.CDLL('/usr/lib/libSystem.B.dylib')
        total = c.c_uint64(); size = c.c_size_t(c.sizeof(total))
        if libc.sysctlbyname(b'hw.memsize', c.byref(total), c.byref(size), None, 0) != 0:
            return None, None, 'unavailable'
        output = subprocess.run(['/usr/bin/vm_stat'], capture_output=True, text=True, timeout=1, check=False).stdout
        page = re.search(r'page size of (\d+) bytes', output)
        counts = dict(re.findall(r'^(Pages [^:]+):\s+(\d+)\.', output, re.M))
        if page and 'Pages free' in counts:
            available = sum(int(counts.get(key, 0)) for key in ('Pages free', 'Pages inactive', 'Pages speculative')) * int(page.group(1))
            return available, total.value, 'free_inactive_speculative_estimate'
    return None, None, 'unavailable'


def _mac_process_memory(pids):
    output = subprocess.run(['/bin/ps', '-axo', 'pid=,ppid=,rss='],
                            capture_output=True, text=True, timeout=1, check=False).stdout
    rows = []
    for line in output.splitlines()[:16384]:
        parts = line.split()
        if len(parts) == 3:
            rows.append(tuple(map(int, parts)))
    selected = set(pids)
    for _ in range(8):
        before = len(selected)
        for pid, parent, _rss_value in rows:
            if parent in selected and len(selected) < 65:
                selected.add(pid)
        if len(selected) == before: break
    return {pid: rss * 1024 for pid, _parent, rss in rows if pid in selected}


class Sampler:
    def __init__(self):
        try:
            import psutil
            self.psutil = psutil
        except Exception:
            self.psutil = None
        self.previous = None

    def sample(self, renderer_pids):
        now = time.monotonic()
        cpu = os.times()
        cpu_time = cpu.user + cpu.system
        main_cpu = None
        if self.previous:
            main_cpu = round(max(0, (cpu_time - self.previous[1]) / max(.001, now - self.previous[0]) * 100), 1)
        self.previous = (now, cpu_time)
        pids = {os.getpid()} | {p for p in renderer_pids if p > 0}
        available = total = None
        memory_source = 'unavailable'
        scope = 'main_and_registered_renderers'
        rss = {}
        if self.psutil:
            try:
                # Limit enumeration; never collect names, cmdlines or environment.
                children = self.psutil.Process().children(recursive=True)[:64]
                pids.update(p.pid for p in children)
                scope = 'main_and_children'
            except Exception:
                pass
            for pid in sorted(pids)[:65]:
                try:
                    rss[pid] = self.psutil.Process(pid).memory_info().rss
                except Exception:
                    pass
            try:
                memory = self.psutil.virtual_memory()
                available, total = memory.available, memory.total
                memory_source = 'psutil_available'
            except Exception:
                pass
        else:
            try:
                if platform.system() == 'Darwin':
                    rss = _mac_process_memory(pids)
                    scope = 'main_and_children'
                else:
                    rss = _rss(sorted(pids)[:65])
            except Exception:
                scope = 'memory_measurement_unavailable'
        if available is None:
            try:
                available, total, memory_source = _system_memory()
            except Exception:
                pass
        return {'main_rss': rss.get(os.getpid()), 'observed_rss_sum': sum(rss.values()) if rss else None,
                'renderer_rss_sum': sum(rss[p] for p in set(renderer_pids) if p in rss) if any(p in rss for p in renderer_pids) else None,
                'processes_measured': len(rss), 'main_cpu_percent': main_cpu,
                'system_available': available, 'system_total': total, 'system_memory_source': memory_source, 'scope': scope}


class Recorder:
    def __init__(self, root, metadata=None, sampler=None, interval=INTERVAL):
        self.root = Path(root)
        self.metadata = metadata or {}
        self.sampler = sampler
        self.interval = max(.02, interval)
        self.events = queue.Queue(maxsize=512)
        self.stop_requested = threading.Event()
        self.lock = threading.Lock()
        self.thread = None
        self.reason = 'user'
        self.summary = {'state': 'idle'}
        self.renderers = {}
        self.dropped = 0
        self.session_path = None
        self.last_heartbeat = time.monotonic()
        self.started = self.last_heartbeat

    def start(self):
        if self.thread is not None:
            return
        with self.lock:
            self.summary = {'state': 'starting'}
        self.thread = threading.Thread(target=self._run, name='SynapsePro diagnostics', daemon=True)
        self.thread.start()

    def stop(self, reason='user'):
        self.reason = reason if reason in ('user', 'profile_closed', 'app_exit', 'time_limit') else 'user'
        self.stop_requested.set()

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.summary))

    def record(self, event, **fields):
        try:
            if self.stop_requested.is_set() or not NAME.fullmatch(event):
                return
            data = {key: val for key, val in fields.items() if key in FIELDS
                    and type(val) in (int, float, bool) and math.isfinite(val)}
            item = {'time': time.time(), 'elapsed': round(time.monotonic() - self.started, 3),
                    'event': event, **data}
            self.events.put_nowait(item)
        except queue.Full:
            self.dropped += 1
        except Exception:
            pass

    def heartbeat(self):
        now = time.monotonic()
        gap = max(0, round((now - self.last_heartbeat - 1) * 1000))
        self.last_heartbeat = now
        if gap >= 1000:
            self.record('app.heartbeat_gap', ms=gap)

    def renderer(self, key, pid):
        with self.lock:
            if pid > 0:
                self.renderers[key] = int(pid)
            else:
                self.renderers.pop(key, None)

    def _run(self):
        handle = None
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            sessions = sorted(p for p in self.root.iterdir() if SESSION.fullmatch(p.name) and p.is_dir() and not p.is_symlink())
            for old in sessions[:max(0, len(sessions) - KEEP_SESSIONS + 1)]:
                shutil.rmtree(old)
            name = time.strftime('session-%Y%m%d-%H%M%S-') + uuid.uuid4().hex[:8]
            self.session_path = self.root / name
            self.session_path.mkdir(mode=0o700)
            self.started = time.monotonic()
            self.last_heartbeat = self.started
            sampler = self.sampler or Sampler()
            summary = {'schema': 1, 'session': name, 'state': 'recording', 'started_at': time.time(),
                       'metadata': self.metadata, 'samples': 0, 'renderer_terminations': 0,
                       'failed_loads': 0, 'max_heartbeat_gap_ms': 0, 'main_rss_peak': 0,
                       'observed_rss_peak': 0, 'dropped_events': 0, 'recent_events': []}
            recent = deque(maxlen=40)
            index = size = 0
            def write(item):
                nonlocal handle, index, size
                line = json.dumps(item, ensure_ascii=False, allow_nan=False) + '\n'
                if handle is None or size + len(line.encode('utf-8')) > MAX_BYTES:
                    if handle:
                        handle.close(); index += 1
                    handle = (self.session_path / ('events-%06d.jsonl' % index)).open('w', encoding='utf-8')
                    size = 0
                    expired = self.session_path / ('events-%06d.jsonl' % (index - SEGMENTS))
                    if expired.exists(): expired.unlink()
                handle.write(line); handle.flush()
                size += len(line.encode('utf-8'))
            write({'event': 'session.started', 'time': time.time(), 'metadata': self.metadata})
            next_sample = 0
            _atomic(self.session_path / 'summary.json', summary)
            while True:
                for _unused in range(100):
                    try:
                        item = self.events.get_nowait()
                    except queue.Empty:
                        break
                    write(item)
                    recent.append(item)
                    if item['event'] == 'app.heartbeat_gap':
                        summary['max_heartbeat_gap_ms'] = max(summary['max_heartbeat_gap_ms'], item.get('ms', 0))
                    if item['event'].endswith('.renderer_terminated'):
                        summary['renderer_terminations'] += 1
                    if item['event'].endswith('.load_finished') and item.get('ok') is False:
                        summary['failed_loads'] += 1
                now = time.monotonic()
                if now >= next_sample and not self.stop_requested.is_set():
                    with self.lock:
                        pids = list(self.renderers.values())
                    try:
                        metrics = sampler.sample(pids)
                        summary.pop('sampling_error', None)
                    except Exception as exc:
                        metrics = {}
                        summary['sampling_error'] = type(exc).__name__
                    gap = max(0, round((now - self.last_heartbeat - 1) * 1000))
                    summary['max_heartbeat_gap_ms'] = max(summary['max_heartbeat_gap_ms'], gap)
                    metrics['heartbeat_gap_ms'] = gap
                    summary['samples'] += 1
                    summary['latest'] = metrics
                    if metrics.get('main_rss') is not None:
                        summary.setdefault('main_rss_first', metrics['main_rss'])
                    summary['main_rss_peak'] = max(summary['main_rss_peak'], metrics.get('main_rss') or 0)
                    summary['observed_rss_peak'] = max(summary['observed_rss_peak'], metrics.get('observed_rss_sum') or 0)
                    write({'event': 'performance.sample', 'time': time.time(), **metrics})
                    next_sample = now + self.interval
                summary['updated_at'] = time.time()
                summary['duration_seconds'] = round(now - self.started)
                summary['dropped_events'] = self.dropped
                summary['recent_events'] = list(recent)
                if now - self.started >= MAX_DURATION:
                    self.stop('time_limit')
                if self.stop_requested.is_set() and self.events.empty():
                    summary['state'] = 'stopped'
                    summary['stop_reason'] = self.reason
                    write({'event': 'session.stopped', 'time': time.time(), 'reason': self.reason})
                _atomic(self.session_path / 'summary.json', summary)
                with self.lock:
                    self.summary = dict(summary)
                if summary['state'] == 'stopped':
                    break
                # Wake on stop; bounded producer queue prevents memory growth.
                self.stop_requested.wait(.5)
        except Exception as exc:
            self.stop_requested.set()
            with self.lock:
                self.summary = {**self.summary, 'state': 'error', 'error': type(exc).__name__}
        finally:
            if handle:
                try: handle.close()
                except Exception: pass


def saved_sessions(root):
    result = []
    try:
        for folder in sorted(Path(root).iterdir(), reverse=True):
            if not SESSION.fullmatch(folder.name) or folder.is_symlink(): continue
            path = folder / 'summary.json'
            try:
                if path.stat().st_size > 128 * 1024: continue
                value = json.loads(path.read_text(encoding='utf-8'))
                if isinstance(value, dict): result.append((folder, value))
            except (OSError, ValueError):
                continue
            if len(result) >= KEEP_SESSIONS: break
    except OSError:
        pass
    return result


_recorder = None
_timer = None


def root_path():
    from aqt import mw
    folder = mw.pm.profileFolder() if mw and mw.pm else None
    if not folder: raise RuntimeError('No active profile')
    return Path(folder) / 'SynapsePro_Data' / 'diagnostics'


def record(event, **fields):
    """No-throw extension point for other features; inert until explicitly started."""
    try:
        if _recorder is not None: _recorder.record(event, **fields)
    except Exception:
        pass


def stop(reason='user'):
    try:
        if _timer is not None: _timer.stop()
        if _recorder is not None: _recorder.stop(reason)
    except Exception:
        pass


def start():
    global _recorder, _timer
    try:
        if _recorder and _recorder.thread and _recorder.thread.is_alive():
            return False
        import anki
        from aqt import mw
        from aqt.qt import QTimer, qVersion, PYQT_VERSION_STR
        metadata = {'anki': str(getattr(anki, 'version', 'unknown')), 'qt': qVersion(),
                    'pyqt': PYQT_VERSION_STR, 'python': platform.python_version(),
                    'os': platform.system(), 'os_release': platform.release(), 'architecture': platform.machine()}
        try:
            from PyQt6.QtWebEngineCore import qWebEngineChromiumVersion
            metadata['chromium'] = qWebEngineChromiumVersion()
        except Exception:
            pass
        try:
            metadata['addon'] = json.loads((Path(__file__).parent / 'manifest.json').read_text())['human_version']
        except Exception:
            pass
        _recorder = Recorder(root_path(), metadata)
        if _timer is None:
            _timer = QTimer(mw)
            _timer.setInterval(1000)
            _timer.timeout.connect(_heartbeat)
            mw.app.aboutToQuit.connect(lambda: stop('app_exit'))
        _recorder.start()
        _timer.start()
        # Attach also when the browser was opened before recording began.
        from . import website_sidebar
        if website_sidebar.sidebar_webview is not None:
            attach_webview(website_sidebar.sidebar_webview)
        return True
    except Exception:
        stop()
        return False


def _heartbeat():
    try:
        if _recorder is not None and not _recorder.stop_requested.is_set():
            _recorder.heartbeat()
        elif _timer is not None:
            _timer.stop()
    except Exception:
        pass


def attach_webview(view):
    """GUI-thread-only setup. Callbacks never access a possibly destroyed view."""
    try:
        key = id(view)
        def pid_changed(pid):
            try:
                if _recorder is not None: _recorder.renderer(key, int(pid))
                record('browser.renderer_pid', pid=int(pid))
            except Exception: pass
        page = view.page()
        pid_changed(page.renderProcessPid())
        record('browser.state', visible=bool(view.isVisible()), count=page.history().count(), index=page.history().currentItemIndex())
        record('browser.cache_limit', value=page.profile().httpCacheMaximumSize())
        if getattr(view, '_synapse_diagnostics_attached', False): return
        view._synapse_diagnostics_attached = True
        view.page().renderProcessPidChanged.connect(pid_changed)
        view.destroyed.connect(lambda *args: pid_changed(0))
        view.loadStarted.connect(lambda: record('browser.load_started'))
        view.loadFinished.connect(lambda ok: record('browser.load_finished', ok=bool(ok)))
        view.urlChanged.connect(lambda _url: record('browser.url_changed'))
        def terminated(status, code):
            try:
                record('browser.renderer_terminated', status=int(status.value), exit_code=int(code))
                pid_changed(0)
            except Exception: pass
        view.renderProcessTerminated.connect(terminated)
        def navigation(request):
            try:
                record('browser.navigation', value=int(request.navigationType().value))
            except Exception: pass
        view.page().navigationRequested.connect(navigation)
        view.page().visibleChanged.connect(lambda visible: record('browser.visible', visible=bool(visible)))
        record('browser.attached')
    except Exception:
        pass
