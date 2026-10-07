"""Native diagnostics panel: opening this tab does not load preview HTML."""
from __future__ import annotations
import threading
import zipfile
from pathlib import Path

from . import diagnostics as diag
from .locales import _ as tr


def report(data, live=False):
    mib = lambda n: 'unavailable' if n is None else f'{n / 1048576:.1f} MiB'
    state = data.get('state', 'unknown')
    labels = {'recording': 'Recording' if live else 'End unknown — no completion saved',
              'starting': 'Starting recording', 'stopped': 'Recording ended',
              'error': 'Diagnostics stopped after an internal error', 'idle': 'No recording'}
    latest = data.get('latest', {})
    cpu = latest.get('main_cpu_percent')
    cpu_label = 'unavailable' if cpu is None else f'{cpu:.1f} %'
    scope_label = {'main_and_children': 'Anki and child processes',
                   'main_and_registered_renderers': 'Anki and registered browser renderers',
                   'memory_measurement_unavailable': 'RAM-Messung unavailable'}.get(latest.get('scope'), 'not measured yet')
    source_label = {'psutil_available': 'available system memory (psutil)',
                    'os_available': 'Operating system',
                    'free_inactive_speculative_estimate': 'macOS estimate from free, inactive and speculative pages'}.get(latest.get('system_memory_source'), 'unavailable')
    lines = [labels.get(state, state), '', f"Samples: {data.get('samples', 0)} · Duration: {data.get('duration_seconds', 0)} s",
             f"Latest Anki RAM: {mib(latest.get('main_rss'))}",
             f"Initial Anki RAM: {mib(data.get('main_rss_first'))}",
             f"Peak measured Anki RAM: {mib(data.get('main_rss_peak') or None)}",
             f"Recorded process RAM sum: {mib(latest.get('observed_rss_sum'))}",
             f"Peak measured RAM sum: {mib(data.get('observed_rss_peak') or None)}",
             f"Registered browser renderer RAM: {mib(latest.get('renderer_rss_sum'))}",
             f"Measured processes: {latest.get('processes_measured', 0)}",
             f"Anki CPU: {cpu_label} (one core = 100 %)",
             f"Available system RAM: {mib(latest.get('system_available'))}",
             f"Longest observed heartbeat gap: {data.get('max_heartbeat_gap_ms', 0)} ms",
             f"Renderer terminations: {data.get('renderer_terminations', 0)}",
             f"Failed/cancelled loads: {data.get('failed_loads', 0)}",
             f"Events dropped due to overload: {data.get('dropped_events', 0)}", '', 'Interpretation:']
    if state == 'recording' and not live:
        lines.append('• No clean completion: possible crash, forced exit or power loss.')
    if data.get('renderer_terminations'):
        lines.append('• A renderer terminated. Status/exit code are in the event log; this does not prove low memory.')
    available, total = latest.get('system_available'), latest.get('system_total')
    if available is not None and total and available / total < .1:
        lines.append('• Less than 10% system memory was available in the latest sample.')
    if data.get('max_heartbeat_gap_ms', 0) > 2000:
        lines.append('• Delayed GUI heartbeat observed; sleep or high system load may also cause this.')
    if data.get('main_rss_first') and latest.get('main_rss'):
        growth = latest['main_rss'] - data['main_rss_first']
        lines.append(f'• Anki RAM change since start: {growth / 1048576:+.1f} MiB. Growth alone does not prove a memory leak.')
    if data.get('error') or data.get('sampling_error'):
        lines.append('• Diagnostics error: ' + str(data.get('error') or data.get('sampling_error')))
    lines.extend(['• Samples every 5 seconds may miss short peaks. Not all errors can be detected.',
                  '• RSS sums may count shared memory multiple times; they are not exact total usage.',
                  '• Process scope: ' + scope_label + '. Without psutil on Windows/Linux, unregistered helper processes are missing.',
                  '• System memory source: ' + source_label + '.',
                  '• Unavailable measurements do not mean zero usage. Cache size and GPU usage are not measured.',
                  '• A native Anki crash may require additional operating system reports.', '', 'Environment:'])
    for key, value in data.get('metadata', {}).items():
        lines.append(f'{key}: {value}')
    lines.extend(['', 'Recent events (no URLs or page contents):'])
    for item in data.get('recent_events', [])[-25:]:
        extra = ', '.join(f'{k}={v}' for k, v in item.items() if k not in ('event', 'time', 'elapsed'))
        lines.append(f"{item.get('elapsed', 0):.1f}s  {item.get('event', '')}  {extra}")
    return '\n'.join(lines)


def build_panel(parent):
    from aqt.qt import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QPlainTextEdit, QComboBox, QTimer, QFileDialog
    widget = QWidget(parent)
    layout = QVBoxLayout(widget)
    intro = QLabel(tr('Local diagnostics: start recording, close the console and use Anki normally. Samples are taken every 5 seconds for up to 8 hours. Up to 5 recordings with about 6 MiB of events each are kept. No URLs, search text, card contents or automatic uploads. Saved recordings remain available after restarting.'))
    intro.setWordWrap(True)
    layout.addWidget(intro)
    row = QHBoxLayout()
    start = QPushButton(tr('Start recording')); stop = QPushButton(tr('Stop recording'))
    marker = QPushButton(tr('Mark an issue'))
    for button in (start, stop, marker): row.addWidget(button)
    layout.addLayout(row)
    sessions = QComboBox(); layout.addWidget(sessions)
    output = QPlainTextEdit(); output.setReadOnly(True); layout.addWidget(output, 1)
    status = QLabel(); status.setWordWrap(True); layout.addWidget(status)
    export = QPushButton(tr('Export selected recording as ZIP')); layout.addWidget(export)
    export_job = {'thread': None, 'result': None}
    cache = {}

    def refresh():
        try:
            root = diag.root_path()
            recorder = diag._recorder
            live = bool(recorder and recorder.thread and recorder.thread.is_alive() and recorder.root == root)
            chosen = sessions.currentData()
            items = diag.saved_sessions(root)
            if live:
                current = recorder.snapshot()
                current_name = current.get('session', 'current')
                items = [(None, {**current, 'session': current_name})] + [
                    (path, data) for path, data in items if data.get('session') != current_name]
            else:
                current_name = None
            cache.clear()
            sessions.blockSignals(True); sessions.clear()
            for path, data in items:
                name = data.get('session', path.name if path else 'current')
                cache[name] = (path, data, live and name == current_name)
                sessions.addItem(name + (tr(' · recording') if live and name == current_name else ''), name)
            index = sessions.findData(chosen)
            if index >= 0: sessions.setCurrentIndex(index)
            sessions.blockSignals(False)
            start.setEnabled(not (recorder and recorder.thread and recorder.thread.is_alive()))
            stop.setEnabled(live and not recorder.stop_requested.is_set())
            marker.setEnabled(stop.isEnabled())
            show_selected()
            job = export_job['thread']
            if job and not job.is_alive():
                status.setText(export_job['result']); export_job['thread'] = None
            if recorder and recorder.root == root and recorder.snapshot().get('state') == 'error':
                status.setText(tr('Recording stopped: ') + recorder.snapshot().get('error', tr('Error')) + tr('. You can keep using Anki.'))
        except Exception:
            status.setText(tr('Diagnostics are currently unavailable.'))

    def show_selected(*args):
        item = cache.get(sessions.currentData())
        if item:
            path, data, live = item
            output.setPlainText(report(data, live))
            export.setEnabled(not live and path is not None and export_job['thread'] is None)
        else:
            output.setPlainText(tr('No saved recordings yet.')); export.setEnabled(False)

    def begin():
        if diag.start():
            status.setText(tr('Recording started. Closing the console does not stop it.'))
        else:
            status.setText(tr('Could not start recording, or the previous recording is still stopping.'))
        refresh()
        sessions.setCurrentIndex(0)
        show_selected()

    def end():
        diag.stop(); status.setText(tr('Saving recording…')); refresh()

    def mark():
        diag.record('user.observation'); status.setText(tr('Time marked — no content recorded.'))

    def save():
        item = cache.get(sessions.currentData())
        if not item or item[2]: return
        source, data, _ = item
        filename, _ = QFileDialog.getSaveFileName(widget, tr('Export diagnostics'), 'synapse-diagnose.zip', 'ZIP (*.zip)')
        if not filename: return
        # Freeze a bounded snapshot before another recording can prune old sessions.
        try:
            files = {}
            for file in sorted(source.glob('events-*.jsonl'))[-diag.SEGMENTS:] + [source / 'summary.json']:
                if file.is_symlink() or file.stat().st_size > diag.MAX_BYTES + 16384: continue
                files[file.name] = file.read_bytes()
            files['report.txt'] = report(data).encode('utf-8')
        except Exception:
            status.setText(tr('Could not read the recording.')); return
        def write_export():
            try:
                with zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED) as archive:
                    for name, content in files.items(): archive.writestr(name, content)
                export_job['result'] = tr('Export saved. You can share the ZIP with support.')
            except Exception as exc:
                export_job['result'] = tr('Export failed: ') + type(exc).__name__
        export_job['thread'] = threading.Thread(target=write_export, daemon=True)
        export_job['thread'].start(); export.setEnabled(False)
        status.setText(tr('Creating export…'))

    start.clicked.connect(begin); stop.clicked.connect(end); marker.clicked.connect(mark)
    export.clicked.connect(save); sessions.currentIndexChanged.connect(show_selected)
    timer = QTimer(widget); timer.setInterval(2000); timer.timeout.connect(refresh); timer.start()
    refresh()
    return widget
