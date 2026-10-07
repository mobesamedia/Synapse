# FreeMap icons

Open **+ → Icons**. The picker contains 208 curated Lucide motifs in seven
clickable categories: Medicine, Science, Learning, People & Communication,
Planning, Everyday, and Symbols. Names, categories and search vocabulary are
English. A translated hint explicitly asks the user to search in English.

Category words (including medical/medicine/healthcare), aliases, upstream tags,
curated subject terms, prefixes and single-edit typos are searched locally.
Category selection intersects the query. Exact names rank ahead of broader tags.
No cloud search, external fonts, network requests or account is required.

The picker offers a color before insertion. Selected canvas icons expose Color
and Change icon in the object toolbar. Icons use actual SVG, retain sharp edges
when scaled, resize proportionally, rotate, attach to arrows, support Anki links,
and participate in normal undo/redo, duplicate and clipboard workflows.

## Portability and storage

Each icon object has `kind: icon` and a document-local `icon` reference. The map’s
`iconAssets` dictionary stores each SVG definition once as a name and a list of
allowed primitive nodes/attributes. No arbitrary SVG markup is interpreted.
The matching license text is in `iconLicense`. This data lives in the existing
profile SQLite document, with no separate profile asset files for icons.

Native and browser JSON exports include only the used definitions, plus license
notices. Geometry and color import without the bundled catalog being present.
Duplicate instances share a definition; clipboard transfers between maps bring
needed definitions and disambiguate key collisions. Replacing an icon preserves
its geometry and begins with its current color. Unused definitions are omitted
from export. Export/import still needs a SynapsePro version supporting icon
objects; older versions reject the new object kind instead of silently dropping
it. Existing maps without icons keep their current version/schema compatibility.

## Source and build

The official Lucide SVGs and metadata were downloaded from the pinned commit in
`web_roadmap/icons/SOURCE.md`. `LICENSE.txt` includes the ISC/MIT notices.
The runtime uses `catalog.js`; `selection.json` is the editable curation source.
Rebuild with `scripts/build_map_icons.py` and that official source archive.
Neither building nor runtime executes files from the source archive.

Geometry is allowlisted in both `workspace_icons.py` and `web_roadmap/icons.js`.
Limits: 512 definitions per map, 64 primitives per icon, 32,000 attribute
characters per icon, 16,000 characters of license notices. Scripts, links,
images, event handlers, external URLs and arbitrary style attributes are rejected.

Tests: `tests/test_workspace_icons.py`, `tests/web_free_map_icons.cjs` and
`tests/qt_roadmap_lifecycle.py` (native file export/import in a temporary profile).
