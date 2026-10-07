# Local diagnostics

Open the existing developer console and select **Diagnose**. Click **Aufnahme
starten**, close the console and use Anki normally. Reopen the console to inspect
this session, mark an observation, stop recording or select an older session.
Export a finished/interrupted session as ZIP for support. Export does not upload
anything. Existing preview tools are on the **Previews** tab; preview HTML is
loaded only after that tab is selected.

Recording is opt-in each time, independent of the dialog, and stops on profile
close or application exit (best effort), explicit stop, an internal write error,
or after eight hours. It does not restart automatically after an Anki restart.
Old recordings remain available under the active profile's
`SynapsePro_Data/diagnostics`. The newest five session folders are retained,
each with at most three 2 MiB event segments plus a small summary. Starting a new
session removes the oldest recordings above this limit. Only recorder-owned
session folders are considered; symlinks are not followed for retention.

## Measurements and interpretation

- Every five seconds: Anki's current RSS and CPU, observed process RSS sum,
  registered browser-renderer RSS and available system RAM where supported.
- psutil, if already installed, supplies child-process and system measurements.
  No package is downloaded. Built-in fallbacks use Windows APIs, Linux `/proc`,
  or macOS `ps`/`vm_stat`. The macOS fallback also samples child processes;
  Windows/Linux without psutil only sample the main process and registered
  renderers. Other WebEngine/GPU processes may therefore be missing.
- macOS available RAM is explicitly an estimate (free + inactive + speculative
  pages), not a measurement of memory pressure. RSS sums can double-count shared
  memory. CPU is for the Anki process, with one core equal to 100%.
- GUI heartbeat gaps are recorded, including gaps detected when the GUI resumes.
  Standby, system load and debugging can also produce gaps.
- Browser load/navigation events, Back/Forward/Reload button presses, visibility,
  renderer PID changes and renderer termination status/exit code are recorded.
  Failed loads can mean cancelled navigation, not a crash.
- No full URLs, domains, page text, search phrases, cards, credentials, process
  command lines or exception messages are collected. Only fixed event names,
  allowlisted numeric/boolean fields and basic runtime versions are saved.

A session with no final stop marker is labelled **Ende unbekannt**, never a
confirmed crash. Flushed events survive an abrupt process exit; the last queued
fraction of a second and writes not persisted by the OS may be lost. Logging
cannot survive every disk failure, power loss or native crash. There is no
native crash dump capture, automatic repair, cache clearing, process killing,
network telemetry or global replacement of Qt/Python exception handlers.
Native Anki crashes may still require an OS crash report.

## Extension and safety boundaries

`diagnostics.record('feature.fixed_event', ok=True, value=123)` is a no-throw,
nonblocking entry point, inert when recording is off. Names must be static code
identifiers, never user data. Allowed fields: pid, ok, visible, status,
exit_code, index, count, ms, value. Text payloads and non-finite numbers are
rejected. Queue capacity is 512; overflow is counted rather than blocking UI.

Call `attach_webview(view)` on the GUI thread to observe another WebView. It is
idempotent, avoids retaining the view in callbacks, and removes renderer
registrations on destruction. The worker never touches Qt objects or the Anki
collection. Filesystem and measurement failures stay in the worker; write
failures halt diagnostics, not Anki. External sampling commands have a one-second
timeout and use no shell. There are no GUI-thread joins on shutdown.

## Verification

`python3 -m unittest discover -s tests -p test_diagnostics.py -v`

`tests/qt_diagnostics.py` runs in Anki's installed Python/Qt environment, using
synthetic HTML and a temporary profile. It checks start, console close/reopen,
real Qt signal connections, duplicate attachment, view destruction, and ZIP
export. Renderer termination is simulated by emitting the Qt signal; this does
not intentionally crash Chromium. Windows/Linux native fallbacks require tests
on those platforms before claiming platform-specific validation.
