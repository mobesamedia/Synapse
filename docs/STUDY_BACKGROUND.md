# Optional study background

Appearance → Custom Background → Show while studying uses the profile's existing wallpaper. Off by default; review-specific defaults are 20% intensity and 8 px blur. Turning the main custom-background switch off also disables the study background.

The activation dialog explains card-template interactions before enabling the option. Escape/Cancel leaves it disabled. Settings are committed with Save Settings. Intensity and blur have a local preview and remain independent of dashboard values.

The reviewer receives a cached, pre-blurred JPEG as a CSS background with a white/light-mode or dark-grey/dark-mode wash baked into the bitmap. A single image layer prevents card CSS from exposing an unwashed strip. No CSS filter is applied to card contents. Cache identity includes profile path, nanosecond mtime, file size, blur, intensity and light/dark mode; profile cleanup releases it. The card question/answer and note templates are never edited. A normal body selector deliberately allows card-template backgrounds to override the image. Editors, card previews and answer controls do not receive this style.

Validation: tests/qt_review_background.py generates a fixture in /tmp for tests/web_review_background.cjs. These cover opt-in, blur cache reuse, intensity endpoints, light/dark wash, state scoping, disabling, Anki reviewer CSS, custom-template precedence, inline-style restoration, settings confirmation/cancel, and persistence payloads.
