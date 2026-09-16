"""Static publication boundary tests. Fixtures never enter a deployable build."""

from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tarfile
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location(
    "pages", Path(__file__).parents[1] / "pages.py"
)
pages = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pages)


def fixture(directory):
    directory = Path(directory)
    (directory / "assets").mkdir(exist_ok=True)
    catalog = pages.read_json(pages.ROOT / "modeling/catalog.json")
    snapshot = {
        "schema_version": 1,
        "generated_at": "2026-03-10T12:00:00Z",
        "catalog": {key: catalog[key] for key in ("teams", "components")}
        | {"season": 2026},
        "versions": {},
    }
    assets = {}
    for key, filename in pages.ASSETS.items():
        # Validation fixtures cover transport/headers, not Blender geometry acceptance.
        payload = (
            (struct.pack("<4sII", b"glTF", 2, 24) + bytes(12))
            if key == "glb"
            else (
                b"\x89PNG\r\n\x1a\n"
                + struct.pack(">I", 13)
                + b"IHDR"
                + struct.pack(
                    ">II",
                    *((1920, 1080) if key.startswith("preview_") else (3840, 2160)),
                )
            )
        )
        digest = hashlib.sha256(payload).hexdigest()
        relative = f"assets/{digest}{Path(filename).suffix}"
        (directory / relative).write_bytes(payload)
        assets[key] = {
            "url": relative,
            "filename": filename,
            "sha256": digest,
            "bytes": len(payload),
        }
    for team in pages.TEAMS:
        snapshot["versions"][team] = [
            {
                "id": f"{team}-baseline",
                "team_key": team,
                "season": 2026,
                "label": "Synthetic fixture",
                "status": "published",
                "published_at": "2026-03-10T12:00:00Z",
                "is_current": True,
                "as_of": "2026-03-01T12:00:00Z",
                "evidence_cutoff": "2026-03-09T12:00:00Z",
                "parent_id": None,
                "reverts_to_id": None,
                "configuration_event": "Fixture",
                "configuration_kind": "baseline",
                "notes": "Test",
                "component_revisions": {},
                "visual_review": dict.fromkeys(pages.VIEWS, True)
                | {
                    "notes": "Synthetic test approval, never an actual car review.",
                    "reference_urls": ["https://example.com/reference"],
                },
                "manifest": {
                    "assets": deepcopy(assets),
                    "sources": [],
                    "changes": [],
                    "components": {},
                    "component_hashes": {},
                    "no_new_modeled_change": False,
                    "reconstruction_notice": "Test only",
                },
            }
        ]
    pages.write_json(directory / "index.json", snapshot)
    return snapshot


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.directory = Path(self.temporary.name) / "archive"
        self.directory.mkdir()
        self.snapshot = fixture(self.directory)

    def tearDown(self):
        self.temporary.cleanup()

    def save(self):
        pages.write_json(self.directory / "index.json", self.snapshot)

    def test_valid_history_deduplicates_assets_and_preserves_rollback_pointer(self):
        newer = deepcopy(self.snapshot["versions"]["ferrari"][0])
        newer.update(
            id="ferrari-annotation", parent_id="ferrari-baseline", is_current=False
        )
        newer["manifest"]["no_new_modeled_change"] = True
        self.snapshot["versions"]["ferrari"].insert(0, newer)
        self.save()
        result = pages.validate(self.directory, require_baselines=True)
        self.assertEqual(result["versions"], 3)
        self.assertEqual(result["unique_assets"], 3)

    def test_draft_and_unreviewed_versions_cannot_deploy(self):
        version = self.snapshot["versions"]["ferrari"][0]
        for field, bad in [
            ("status", "ready"),
            ("published_at", None),
            ("visual_review", {}),
        ]:
            with self.subTest(field=field):
                old = version[field]
                version[field] = bad
                self.save()
                with self.assertRaises(ValueError):
                    pages.validate(self.directory, True)
                version[field] = old

    def test_empty_archive_can_preview_but_cannot_replace_live_site(self):
        for path in (self.directory / "assets").iterdir():
            path.unlink()
        self.snapshot["versions"] = {team: [] for team in pages.TEAMS}
        self.save()
        self.assertEqual(pages.validate(self.directory)["versions"], 0)
        with self.assertRaisesRegex(
            ValueError, "existing Pages deployment must stay live"
        ):
            pages.validate(self.directory, True)

    def test_missing_history_duplicate_ids_and_current_pointer_are_rejected(self):
        version = self.snapshot["versions"]["ferrari"][0]
        for field, bad in [
            ("parent_id", "missing"),
            ("reverts_to_id", "missing"),
            ("is_current", False),
            ("team_key", "mercedes"),
        ]:
            with self.subTest(field=field):
                old = version[field]
                version[field] = bad
                self.save()
                with self.assertRaises(ValueError):
                    pages.validate(self.directory)
                version[field] = old
        self.snapshot["versions"]["ferrari"].append(deepcopy(version))
        self.save()
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            pages.validate(self.directory)

    def test_checksum_corruption_is_rejected(self):
        path = next((self.directory / "assets").glob("*.glb"))
        data = bytearray(path.read_bytes())
        data[-1] = 1
        path.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "checksum"):
            pages.validate(self.directory)

    def test_missing_asset_and_unexpected_private_files_are_rejected(self):
        private = self.directory / ".env"
        private.write_text("private fixture")
        with self.assertRaisesRegex(ValueError, "Unexpected files"):
            pages.validate(self.directory)
        private.unlink()
        next((self.directory / "assets").iterdir()).unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            pages.validate(self.directory)

    def test_asset_paths_cannot_escape_the_archive(self):
        self.snapshot["versions"]["ferrari"][0]["manifest"]["assets"]["glb"][
            "url"
        ] = "../../.env"
        self.save()
        with self.assertRaisesRegex(ValueError, "asset path"):
            pages.validate(self.directory)

    def test_export_schema_excludes_private_fields_and_editable_scene(self):
        version = self.snapshot["versions"]["ferrari"][0]
        version["private_token"] = "NEVER_EXPORT"
        version["visual_review"]["private_log"] = "NEVER_EXPORT"
        version["manifest"]["sources"] = [
            {
                "id": "source",
                "text": "NEVER_EXPORT",
                "pages": [{"text": "NEVER_EXPORT"}],
            }
        ]
        version["manifest"]["assets"]["scene"] = {
            "filename": "source.blend",
            "url": "NEVER_EXPORT",
        }
        exported = pages.public_version(version)
        self.assertNotIn("NEVER_EXPORT", json.dumps(exported))
        self.assertEqual(set(exported["manifest"]["assets"]), set(pages.ASSETS))
        version["status"] = "ready"
        with self.assertRaisesRegex(ValueError, "Only published"):
            pages.public_version(version)

    def test_oversized_archives_are_rejected(self):
        with patch.object(pages, "MAX_ARCHIVE_BYTES", 1):
            with self.assertRaisesRegex(ValueError, "850 MiB"):
                pages.validate(self.directory)

    def test_tar_path_traversal_links_duplicates_and_devices_are_rejected(self):
        for name, kind in [
            ("../.env", tarfile.REGTYPE),
            ("index.json", tarfile.SYMTYPE),
            ("index.json", tarfile.CHRTYPE),
        ]:
            with self.subTest(name=name, kind=kind):
                bundle = Path(self.temporary.name) / "bad.tar.gz"
                with tarfile.open(bundle, "w:gz") as archive:
                    item = tarfile.TarInfo(name)
                    item.type = kind
                    archive.addfile(item)
                with tempfile.TemporaryDirectory() as out:
                    with self.assertRaisesRegex(ValueError, "Unsafe"):
                        pages.unpack(bundle, out)

    def test_export_and_bundle_roundtrip_use_public_endpoints_and_preserve_history(
        self,
    ):
        def get(url):
            if url.endswith("/catalog"):
                return self.snapshot["catalog"]
            team = "ferrari" if "/ferrari/" in url else "mercedes"
            return self.snapshot["versions"][team]

        def download(url, destination):
            self.assertIn("/api/v1/releases/", url)
            filename = url.rsplit("/", 1)[1]
            asset = next(
                a
                for a in self.snapshot["versions"]["ferrari"][0]["manifest"][
                    "assets"
                ].values()
                if a["filename"] == filename
            )
            Path(destination).write_bytes((self.directory / asset["url"]).read_bytes())

        output = Path(self.temporary.name) / "pages-archive.tar.gz"
        with patch.object(pages, "get_json", get), patch.object(
            pages, "download", download
        ):
            result = pages.export("http://127.0.0.1:3000", output)
        self.assertEqual(result["versions"], 2)
        with tempfile.TemporaryDirectory() as out:
            self.assertEqual(pages.unpack(output, out)["versions"], 2)
            pages.validate(out, True)
        with self.assertRaisesRegex(ValueError, "exists"):
            pages.export("http://127.0.0.1:3000", output)

    def test_failed_export_preserves_existing_output(self):
        output = Path(self.temporary.name) / "snapshot.tar.gz"
        output.write_bytes(b"previous snapshot")
        with self.assertRaises(ValueError):
            pages.export("http://127.0.0.1:3000", output)
        self.assertEqual(output.read_bytes(), b"previous snapshot")


if __name__ == "__main__":
    unittest.main()
