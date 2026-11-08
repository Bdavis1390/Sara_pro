import unittest

from ws_cae.continuity_validation import valid_content_id, valid_date, valid_datetime


class ContinuityValidationTests(unittest.TestCase):
    def test_content_id_requires_lowercase_hex(self):
        lower = "sha256:" + ("ab" * 32)
        upper = "sha256:" + ("AB" * 32)
        self.assertTrue(valid_content_id(lower))
        self.assertFalse(valid_content_id(upper))

    def test_calendar_date_is_real(self):
        self.assertTrue(valid_date("2026-09-13"))
        self.assertFalse(valid_date("2026-99-99"))
        self.assertFalse(valid_date("2026-02-30"))

    def test_datetime_requires_timezone(self):
        self.assertTrue(valid_datetime("2026-09-13T23:00:00Z"))
        self.assertTrue(valid_datetime("2026-09-13T19:00:00-04:00"))
        self.assertFalse(valid_datetime("2026-09-13T23:00:00"))
        self.assertFalse(valid_datetime("not-a-time"))


if __name__ == "__main__":
    unittest.main()
