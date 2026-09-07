"""Keep offline-shell source checks aligned with the tested cache helper."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("offline_validator", ROOT / "scripts/validate-site.py")
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)
WORKER = (ROOT / "sw.js").read_text(encoding="utf-8")
REGISTRATION = 'navigator.serviceWorker.register("/sw.js", { scope: "/" });'
FALLBACK_ERROR = "sw.js has no /offline.html navigation fallback"


class OfflineValidationTests(unittest.TestCase):
    def check(self, worker=WORKER, registration=REGISTRATION, offline=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "index.html").write_text("<main>Home</main>")
            if worker is not None:
                (root / "sw.js").write_text(worker, encoding="utf-8")
            if offline:
                (root / "offline.html").write_text("<main>Offline</main>")
            scripts = root / "assets/js"
            scripts.mkdir(parents=True)
            (scripts / "app.js").write_text(registration)
            with patch.object(VALIDATOR, "ROOT", root):
                return VALIDATOR._check_offline_shell()

    def test_current_cache_scoped_helper_fallback_passes(self):
        self.assertEqual(self.check(), [])

    def test_legacy_direct_cache_fallback_still_passes(self):
        self.assertEqual(self.check(WORKER.replace('cachedResponse("/offline.html")',
                                                  'caches.match("/offline.html")')), [])

    def test_precache_entry_alone_does_not_prove_a_navigation_fallback(self):
        changed = WORKER.replace('cachedResponse("/offline.html")', 'undefined')
        self.assertIn(FALLBACK_ERROR, self.check(changed))

    def test_missing_helper_definition_does_not_pass(self):
        changed = WORKER.replace("function cachedResponse(", "function otherResponse(")
        self.assertIn(FALLBACK_ERROR, self.check(changed))

    def test_required_worker_and_offline_files_still_fail(self):
        self.assertIn("sw.js is missing", self.check(worker=None))
        self.assertIn("offline.html is missing", self.check(offline=False))

    def test_registration_and_root_scope_still_fail(self):
        self.assertIn("client runtime does not register /sw.js", self.check(registration=""))
        self.assertIn("client runtime registration is not root-scoped",
                      self.check(registration=REGISTRATION.replace('scope: "/"', 'scope: "/toolbox/"')))

    def test_precache_and_version_checks_still_fail(self):
        cases = [
            (WORKER.replace('  "/offline.html",', ''), "PRECACHE_URLS does not include /offline.html"),
            (WORKER.replace('  "/offline.html",', '  "/offline.html", "https://third.example/a",'),
             "PRECACHE_URLS contains a third-party URL"),
            (WORKER.replace("const PRECACHE_URLS", "const OTHER_URLS"), "sw.js has no PRECACHE_URLS list"),
            (WORKER.replace("glee-fully-shell-v", "unversioned-"), "sw.js cache name is not versioned"),
        ]
        for worker, expected in cases:
            with self.subTest(expected=expected):
                self.assertIn(expected, self.check(worker))


if __name__ == "__main__":
    unittest.main()
