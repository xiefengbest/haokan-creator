import unittest

from creator_publish.redact import scrub_text
from scripts.check_public_repo import collect, scan_text


class PublicRepoTests(unittest.TestCase):
    def test_current_repo_is_clean(self):
        self.assertEqual(collect(), [])

    def test_filled_setting_is_rejected_without_echoing_it(self):
        secret = "filled-secret-value"
        problems = scan_text("sample.env", f"CREATOR_SIGN_KEY={secret}\n")
        self.assertEqual(problems, ["sample.env: 敏感配置写了具体值"])
        self.assertNotIn(secret, "\n".join(problems))

    def test_sample_phone_is_allowed(self):
        self.assertEqual(scan_text("readme", "13800138000"), [])

    def test_errors_hide_addresses_and_secrets(self):
        hidden = "https://secret.example/path"
        text = scrub_text(f"失败 {hidden} password=abc")
        self.assertNotIn(hidden, text)
        self.assertNotIn("abc", text)
        self.assertIn("（地址已隐藏）", text)

    def test_other_phone_is_rejected_without_echoing_it(self):
        phone = "139" + "00001111"
        problems = scan_text("note", phone)
        self.assertEqual(problems, ["note: 含有示例以外的手机号"])
        self.assertNotIn(phone, problems[0])


if __name__ == "__main__":
    unittest.main()
