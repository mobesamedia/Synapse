"""Package runtime files only; archived features must never ship in an update."""
from pathlib import Path
import argparse
import zipfile

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {'archived_features', '.git', '.agents', '.codex', '__pycache__',
                 'tests', 'docs', 'scripts', 'output', 'node_modules', '.pytest_cache',
                 'ai_v2_profile', 'website_web_profile', 'music_web_profile',
                 'mindmap_web_data', 'SynapsePro_Data', '__MACOSX'}
EXCLUDED_FILES = {'_secrets.py', 'addon_settings.json', 'study_plan_config.json',
                  'ai_secrets.json', 'meta.json', 'Icon\r'}

def release_files(root=ROOT):
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in EXCLUDED_DIRS or part.startswith('.') for part in relative.parts):
            continue
        if path.is_symlink() or not path.is_file():
            continue
        if path.name in EXCLUDED_FILES or path.name.endswith(('_backup.json', '_recovery.json', '_backup.json.tmp', '_recovery.json.tmp')):
            continue
        if '.pre-block-ui-v1.json' in path.name or '.pre-hierarchy-v1.json' in path.name:
            continue
        if path.suffix in {'.sqlite', '.sqlite3', '.db'} or path.name.endswith(('-wal', '-shm', '-journal')):
            continue
        if path.suffix in {'.pyc', '.pyo', '.ankiaddon', '.zip'}:
            continue
        yield path, relative

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='New .ankiaddon file (existing files are not overwritten)')
    args = parser.parse_args()
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
        for path, relative in release_files():
            archive.write(path, str(relative))
    print(args.output)

if __name__ == '__main__':
    main()
