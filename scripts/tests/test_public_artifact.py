"""Public staging and transfer boundary regressions using small local fixtures."""
import importlib.util
import tempfile
import tarfile
import unittest
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "public_artifact", Path(__file__).resolve().parents[1] / "public-artifact.py")
artifact = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifact)
COMMIT = "a" * 40


class PublicArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "source"
        self.output = Path(self.temp.name) / "public"
        self.source.mkdir()
        for name in artifact.ROOT_FILES | {".well-known/security.txt"}:
            self.write(name, "public")
        self.write(".nojekyll", "")
        self.write("CNAME", "glee-fully.tools\n")
        self.write("index.html", '<a href="/search/">Search</a><script src="/assets/js/app.js"></script>')
        self.write("search/index.html", '<h1>Search</h1>')
        self.write("assets/js/app.js", "// public runtime")
        self.write("site.webmanifest", '{"icons": []}')
        self.write("sitemap.xml", '<urlset><url><loc>https://glee-fully.tools/</loc></url></urlset>')
        self.write("sw.js", 'const PRECACHE_URLS = ["/", "/search/"];')
        self.write("assets/data/search-index.json", '[]')

    def write(self, name, value):
        path = self.source / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value, encoding="utf-8")

    def stage(self):
        artifact.stage(self.source, self.output, {"commit": COMMIT})

    def test_only_reviewed_public_inventory_is_staged(self):
        for private in ["README.md", "assets/templates/template--homepage.html",
                        "brand-styles/profiles/glee-fully.yaml", "assets/data/private.json",
                        "assets/downloads/.gitkeep", "assets/js/.secret.js"]:
            self.write(private, "development")
        self.stage()
        self.assertTrue((self.output / ".well-known/security.txt").is_file())
        self.assertTrue((self.output / ".nojekyll").is_file())
        self.assertFalse((self.output / "assets/templates").exists())
        self.assertFalse((self.output / "assets/data/private.json").exists())
        artifact.verify(self.source, self.output, COMMIT)

    def test_transfer_cannot_silently_drop_required_hidden_files(self):
        self.stage()
        (self.output / ".well-known/security.txt").unlink()
        with self.assertRaisesRegex(ValueError, "security.txt"):
            artifact.verify(self.source, self.output, COMMIT)

    def test_transfer_tampering_and_added_hidden_files_are_rejected(self):
        self.stage()
        (self.output / ".env").write_text("unexpected")
        with self.assertRaisesRegex(ValueError, "env"):
            artifact.verify(self.source, self.output, COMMIT)
        (self.output / ".env").unlink()
        (self.output / "index.html").write_text("changed after validation")
        with self.assertRaisesRegex(ValueError, "index.html"):
            artifact.verify(self.source, self.output, COMMIT)

    def test_missing_staged_local_resource_fails(self):
        self.write("index.html", '<img src="/assets/img/missing.svg">')
        with self.assertRaisesRegex(ValueError, "missing.svg"):
            self.stage()

    def test_source_links_to_excluded_development_content_fail(self):
        self.write("README.md", "development")
        self.write("index.html", '<a href="/README.md">Unreviewed download</a>')
        with self.assertRaisesRegex(ValueError, "README.md"):
            self.stage()

    def test_wrong_provenance_commit_is_rejected(self):
        self.stage()
        with self.assertRaisesRegex(ValueError, "commit"):
            artifact.verify(self.source, self.output, "b" * 40)

    def test_empty_hidden_directory_is_rejected(self):
        self.stage()
        (self.output / ".unexpected").mkdir()
        with self.assertRaisesRegex(ValueError, "unexpected"):
            artifact.verify(self.source, self.output, COMMIT)

    def test_both_workflow_upload_boundaries_preserve_reviewed_hidden_files(self):
        workflow = (Path(__file__).resolve().parents[2] / ".github/workflows/pages.yml").read_text()
        for title in ["Upload artifact from validated commit", "Prepare Pages upload"]:
            step = workflow.split("- name: " + title, 1)[1].split("- name:", 1)[0]
            self.assertIn("include-hidden-files: true", step)
            self.assertIn("${{ runner.temp }}/glee-public-site", step)

    def test_stage_refuses_existing_content(self):
        self.output.mkdir()
        (self.output / "keep.txt").write_text("preserve me")
        with self.assertRaisesRegex(ValueError, "empty"):
            self.stage()
        self.assertTrue((self.output / "keep.txt").is_file())

    def test_pages_archive_preserves_hidden_files_and_rejects_missing_security(self):
        self.stage()
        package = Path(self.temp.name) / "artifact.tar"
        with tarfile.open(package, "w") as archive:
            archive.add(self.output, arcname=".")
        result = artifact.verify_tar(self.source, self.output, COMMIT, package)
        self.assertTrue(result["pages_archive_verified"])
        with tarfile.open(package, "w") as archive:
            for path in self.output.rglob("*"):
                if path.is_file() and path.name != "security.txt":
                    archive.add(path, arcname=path.relative_to(self.output).as_posix())
        with self.assertRaisesRegex(ValueError, "security.txt"):
            artifact.verify_tar(self.source, self.output, COMMIT, package)

    def test_symbolic_links_cannot_escape_public_source(self):
        target = self.source / "assets/js/external.js"
        try:
            target.symlink_to(self.source / "README.md")
        except OSError:
            self.skipTest("host does not allow creating test symlinks")
        with self.assertRaisesRegex(ValueError, "link|reparse"):
            self.stage()

    def test_pages_archive_rejects_unsafe_and_unexpected_directories(self):
        self.stage()
        package = Path(self.temp.name) / "artifact.tar"
        for name in ("../outside-staging", "/outside-staging", "unexpected-directory", ".unreviewed"):
            with self.subTest(directory=name):
                with tarfile.open(package, "w") as archive:
                    archive.add(self.output, arcname=".")
                    directory = tarfile.TarInfo(name)
                    directory.type = tarfile.DIRTYPE
                    archive.addfile(directory)
                with self.assertRaisesRegex(ValueError, "unsafe|unexpected"):
                    artifact.verify_tar(self.source, self.output, COMMIT, package)


if __name__ == "__main__":
    unittest.main()
