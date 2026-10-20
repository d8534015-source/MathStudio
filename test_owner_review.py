"""Packaging-only regressions; fixtures never touch an installed OWNER."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import owner_review as review


class OwnerReviewTests(unittest.TestCase):
    def test_environment_does_not_inherit_production_configuration(self):
        with mock.patch.dict(os.environ, {'MATH_DATA': 'production', 'MATH_CONFIG': 'secret',
                    'MATH_ARGOS_HOME': 'production', 'CLOUDFLARE_TURN_API_TOKEN': 'secret',
                    'MATH_R2_SECRET_ACCESS_KEY': 'secret', 'PUBLIC_ORIGIN': 'https://production',
                    'PYTHONPATH': 'production'}):
            state = Path('/isolated/review')
            env = review.environment(state)
        self.assertEqual(env['MATH_DATA'], str(state/'data'))
        self.assertEqual(env['MATH_ARGOS_HOME'], str(state/'translation'))
        self.assertEqual(env['PORT'], '5063')
        self.assertEqual(env['BIND_HOST'], '127.0.0.1')
        for key in ('CLOUDFLARE_TURN_API_TOKEN', 'MATH_R2_SECRET_ACCESS_KEY', 'PYTHONPATH'):
            self.assertNotIn(key, env)

    def test_local_copy_excludes_archives_caches_and_leaves_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); source = root/'installed'; destination = root/'review'
            for name in ('runtime/Scripts/python.exe', 'packages/en_zh/model/model.bin',
                         'installation.json', 'downloads/en.argosmodel', 'cache/private.txt'):
                path = source/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'synthetic')
            before = {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()}
            review.copy_models(source, destination)
            self.assertEqual(set(p.name for p in destination.iterdir()), {'runtime', 'packages', 'installation.json'})
            self.assertEqual(before, {str(p.relative_to(source)): p.read_bytes() for p in source.rglob('*') if p.is_file()})
            with self.assertRaises(FileExistsError): review.copy_models(source, destination)
            with self.assertRaises(RuntimeError): review.copy_models(source, source/'nested')
            (source/'.setup.lock').touch()
            with self.assertRaises(RuntimeError): review.copy_models(source, root/'another')

    def test_start_refuses_busy_review_port_before_starting_server(self):
        with tempfile.TemporaryDirectory() as directory:
            state = Path(directory); (state/'review-ready.json').write_text('{}')
            with mock.patch.object(review.socket, 'socket') as socket, mock.patch.object(review, 'run') as run:
                socket.return_value.__enter__.return_value.bind.side_effect = OSError('busy')
                with self.assertRaisesRegex(RuntimeError, '5063'): review.start(state)
                run.assert_not_called()

    def test_launcher_references_are_present(self):
        for name, action in [('REVIEW OWNER SETUP.bat', 'setup'), ('REVIEW OWNER START.bat', 'start')]:
            self.assertIn('py -3.13 owner_review.py '+action, (review.ROOT/name).read_text())
        self.assertTrue((review.ROOT/'server.py').is_file())


if __name__ == '__main__': unittest.main()
