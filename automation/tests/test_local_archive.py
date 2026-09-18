import io
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.path.insert(0, str(Path(__file__).parents[1]))
import local_archive as local
from newsapi_fetch import REPO, seal
from cryptography.fernet import Fernet


class LocalArchiveTests(unittest.TestCase):
    def setUp(self):
        self.key = Fernet.generate_key()
        self.batch = dict(version=1, repository=REPO, run_id="test", requests=1,
                          outstanding_windows=0, coverage_status="complete_requested_windows")

    def archive(self, member="batch.enc"):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as z:
            z.writestr(member, seal(self.batch, self.key))
        return buffer.getvalue()

    def test_archive_validation(self):
        cipher, batch = local.read_batch(self.archive(), self.key)
        self.assertEqual(batch, self.batch)
        self.assertNotIn(b"coverage_status", cipher)
        with self.assertRaises(ValueError):
            local.read_batch(self.archive("../batch.enc"), self.key)

    @unittest.skipUnless(os.name == "nt", "Windows DPAPI only")
    def test_dpapi_roundtrip(self):
        protected = local.protect(self.key)
        self.assertNotEqual(protected, self.key)
        self.assertEqual(local.protect(protected, decrypt=True), self.key)

    def test_download_receipt_makes_rerun_idempotent(self):
        metadata = [dict(id=123, name="newsapi-batch-test", expired=False, created_at="2026-09-18T00:00:00Z")]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_path = root / "key.dpapi"
            key_path.write_bytes(b"fake protected key")
            with patch.object(local, "protect", return_value=self.key), \
                 patch.object(local, "artifact_list", return_value=metadata), \
                 patch.object(local, "gh_bytes", return_value=self.archive()) as fetch, \
                 patch("builtins.print"):
                self.assertEqual(local.download(key_path, root / "out"), 0)
                self.assertEqual(local.download(key_path, root / "out"), 0)
                self.assertEqual(fetch.call_count, 1)
                self.assertTrue((root / "out/123/batch.json").exists())
                self.assertTrue((root / "out/123/receipt.json").exists())


if __name__ == "__main__":
    unittest.main()
