import os
import socket
import unittest
from unittest.mock import MagicMock, patch

from app import CVMatchingSystem, CVURLValidationError, app


class SkillMatchingTests(unittest.TestCase):
    def test_job_title_fallback_uses_each_title_word_as_target(self):
        matcher = CVMatchingSystem()
        matcher.job_data = {
            "job_title": "Operator Sablon",
            "required_skill": []
        }
        matcher.target_skills = matcher.get_target_skills()
        matcher.extracted_info["skills"] = ["operator"]

        matcher.skill_matching()
        response = matcher.prepare_response()

        self.assertEqual(matcher.target_skills, ["operator", "sablon"])
        self.assertEqual(response["persentase"], "50.0%")
        self.assertEqual(
            response["skill_required"],
            ["operator", "sablon"]
        )

    def test_job_title_fallback_percentage_cannot_exceed_100(self):
        matcher = CVMatchingSystem()
        matcher.job_data = {
            "job_title": "Operator Sablon",
            "required_skill": []
        }
        matcher.target_skills = matcher.get_target_skills()
        matcher.extracted_info["skills"] = ["operator", "sablon"]

        matcher.skill_matching()

        self.assertEqual(matcher.calculate_percentage(), 100.0)


class CVURLValidationTests(unittest.TestCase):
    def test_rejects_non_https_url(self):
        with self.assertRaises(CVURLValidationError):
            CVMatchingSystem.validate_cv_url(
                "http://project.supabase.co/cv.pdf"
            )

    def test_rejects_host_outside_allowlist(self):
        with self.assertRaises(CVURLValidationError):
            CVMatchingSystem.validate_cv_url(
                "https://example.com/cv.pdf"
            )

    @patch(
        "app.socket.getaddrinfo",
        return_value=[
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("127.0.0.1", 443)
            )
        ]
    )
    def test_rejects_allowed_host_resolving_to_private_ip(self, _mock_dns):
        with self.assertRaises(CVURLValidationError):
            CVMatchingSystem.validate_cv_url(
                "https://project.supabase.co/cv.pdf"
            )

    @patch(
        "app.socket.getaddrinfo",
        return_value=[
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("8.8.8.8", 443)
            )
        ]
    )
    def test_custom_public_host_can_be_configured(self, _mock_dns):
        with patch.dict(
            os.environ,
            {"CV_ALLOWED_HOSTS": "storage.example.com"}
        ):
            result = CVMatchingSystem.validate_cv_url(
                "https://storage.example.com/cv.pdf"
            )

        self.assertEqual(result, "https://storage.example.com/cv.pdf")

    @patch(
        "app.socket.getaddrinfo",
        return_value=[
            (
                socket.AF_INET,
                socket.SOCK_STREAM,
                socket.IPPROTO_TCP,
                "",
                ("8.8.8.8", 443)
            )
        ]
    )
    @patch("app.requests.get")
    def test_rejects_redirect_to_host_outside_allowlist(
        self,
        mock_get,
        _mock_dns
    ):
        response = MagicMock()
        response.is_redirect = True
        response.is_permanent_redirect = False
        response.headers = {"Location": "https://example.com/cv.pdf"}
        response.__enter__.return_value = response
        mock_get.return_value = response
        matcher = CVMatchingSystem()

        result = matcher.download_cv_from_url(
            "https://project.supabase.co/cv.pdf"
        )

        self.assertIsNone(result)
        self.assertEqual(
            matcher.download_error["error_code"],
            "INVALID_CV_URL"
        )
        mock_get.assert_called_once()


class MatchEndpointValidationTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_rejects_invalid_required_skill_type(self):
        response = self.client.post(
            "/api/match",
            json={
                "uri_cv": "https://project.supabase.co/cv.pdf",
                "job_title": "Operator Sablon",
                "required_skill": "Operator"
            }
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json()["error_code"],
            "INVALID_REQUIRED_SKILL"
        )


if __name__ == "__main__":
    unittest.main()
