"""The deferred social feature must not enter the runtime or release package."""
import ast
import os
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class FriendsArchiveTests(unittest.TestCase):
    def test_no_active_social_imports_or_callbacks(self):
        forbidden = {'friends', 'friends_core', 'friends_text', 'friends_config'}
        for path in ROOT.glob('*.py'):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    self.assertNotIn(node.module, forbidden, str(path))
                elif isinstance(node, ast.Import):
                    for name in node.names:
                        self.assertNotIn(name.name, forbidden, str(path))
        for filename in ('sidebar.py', 'developer_console.py', '__init__.py'):
            text = (ROOT / filename).read_text()
            for hook in ('get_controller', 'preview_friends', 'update_friends', 'friends_session_finished', 'armFriendsCheers'):
                self.assertNotIn(hook, text, filename)

    def test_release_excludes_archive_and_keeps_shared_styles(self):
        spec = importlib.util.spec_from_file_location('release_packaging', ROOT/'scripts/package_addon.py')
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        names = {str(relative) for _, relative in module.release_files()}
        self.assertTrue({'__init__.py','manifest.json','gamification_web/progress.css','gamification_web/settings.js'} <= names)
        self.assertFalse(any('archived_features' in name or 'friends' in name or name.startswith('supabase/') for name in names if name.endswith(('.py','.js','.css','.sql','.ts'))))
        html = (ROOT/'gamification_web/sidebar.html').read_text()
        for removed in ('friendsSummary','friendsOverlay','cheersOverlay','friends.js','friends.css'):
            self.assertNotIn(removed, html)
        self.assertIn('href="progress.css"', html)

    def test_archive_preserves_source_backend_and_restore_instructions(self):
        archive = Path(os.environ.get('SYNAPSE_FRIENDS_ARCHIVE', str(ROOT/'archived_features/friends')))
        if not archive.is_dir() and not os.environ.get('SYNAPSE_FRIENDS_ARCHIVE'):
            archive = ROOT.parent/'Archived Features/friends'
        for filename in ('source/friends.py','source/friends_core.py','source/gamification_web/friends.js',
                         'source/supabase/functions/friends/index.ts','source/supabase/migrations/202609230001_friends.sql',
                         'source/supabase/migrations/202609250001_cheers.sql','RESTORE_INTEGRATION.patch','translations.json','README.md'):
            self.assertTrue((archive/filename).is_file(), filename)
        self.assertIn('FRIENDS_ENABLED = False', (archive/'source/friends_config.py').read_text())

if __name__ == '__main__':
    unittest.main()
