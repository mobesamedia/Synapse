# Embedded SoundCloud playback

Some Anki QtWebEngine builds do not decode AAC in HTML audio or Media Source
Extensions, while Anki’s bundled mpv audio engine can decode it.
SoundCloud now supplies AAC/HLS streams. In that combination the official widget
loads and accepts Play, then immediately stops or skips through the playlist.

`soundcloud_audio.py` installs `soundcloud_native_audio.js` on the SoundCloud
WebView only. When Chromium has no AAC decoder and Anki’s mpv is available, the adapter
presents SoundCloud’s native HLS media environment and delegates that widget’s
HTML audio elements to a separate mpv instance. QtMultimedia was also tested,
but its HLS playback stalled after large seeks; mpv correctly reaches the end
of the same stream after seeking. The iOS Safari user-agent inside
the widget is necessary for SoundCloud to select its native HLS controller.
The host page, the music UI and other WebViews keep their actual browser identity.
Browsers with AAC support use the original widget audio without modification.

The official widget still selects tracks, obtains authorized streaming URLs,
handles playlists, and supplies metadata and controls through its Widget API.
The adapter uses HTML media properties/events rather than SoundCloud DOM
selectors or private stream-resolution endpoints. Only HTTPS `.m3u8` sources
on SoundCloud's media CDNs are accepted by the native side. No media is saved
by the adapter, no codec/browser binaries are installed, and saved URLs, local
music, notebook data, and login profiles are not migrated or cleared.

Native commands carry a per-view token and per-frame session. A fresh iframe
disposes old players; queued callbacks from old players cannot affect a new
session. Only one native audio element plays at a time, and changing to Local
or closing the Anki profile stops/pauses native playback as appropriate. Hiding
the music window continues playback. The host restores the chosen volume when
Widget.load replaces its iframe.

Validation:

- `python3 -m unittest tests.test_soundcloud_audio`: stream URL validation.
- `node tests/web_soundcloud_audio.cjs`: synthetic HTML media events, controls,
  stale sessions, source disposal, and unchanged behavior with browser AAC.
- `tests/qt_soundcloud.py`, explicitly run with Anki's Python: live official
  widget and real native mpv audio in a temporary profile. Covers both Play buttons,
  actual playback progress, pause, seek, volume, playlists, automatic track
  advance, reload, hide/show, and switching modes. Requires network/audio.

The workaround depends on SoundCloud retaining its native HLS playback path and
on Anki’s installed mpv supporting AAC/HLS. If SoundCloud changes
that path, rerun the live test before changing the adapter. Do not restore the
old MP3 endpoints or replace Anki's Qt libraries as a workaround.

## Qt cross-origin frame compatibility (1.6.5)

The adapter script is registered on the dedicated music profile, rather than only on the host page. With the tested newer Qt build, page-only scripts reached the local host but did not execute in the cross-origin SoundCloud renderer, leaving AAC playback inactive. The script still exits immediately outside the exact `w.soundcloud.com/player/` frame and the profile is used only by the music views. Destroying the owning SoundCloud page removes its script from the profile. No login cookies or saved tracks are cleared.

On 2026-10-28 the full official-widget live test passed in Anki 26.9.3 on macOS, including both Play buttons, progress, pause, seek, volume retention, next/previous tracks, station changes, automatic advancement, reload, hide/show, switching to local music, and unchanged saved synthetic data. The test-only widget click listener also uses profile registration so it reaches that same cross-origin renderer.
