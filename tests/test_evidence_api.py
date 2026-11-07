"""HTTP regression tests against temporary synthetic evidence, without a server."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from tools.api.app import main


class EvidenceApiTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        data_patch = patch.object(main, "DATA_ROOT", self.root)
        data_patch.start()
        self.addCleanup(data_patch.stop)
        self.client = TestClient(main.app)
        self.addCleanup(self.client.close)

    def write_json(self, relative, value):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_health_needs_no_evidence_files(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "healthy",
            "service": "noir-devops-incident-intelligence-tools",
        })

    def test_incident_is_selected_by_id(self):
        expected = {"incident_id": "INC-TEST", "title": "Synthetic failure"}
        self.write_json("incidents/INC-TEST/incident.json", expected)
        self.write_json("incidents/OTHER/incident.json", {"incident_id": "OTHER"})
        response = self.client.get("/incidents/INC-TEST")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_observability_evidence_is_selected_by_incident(self):
        expected = {"incident_id": "INC-TEST", "signals": ["synthetic timeout"]}
        self.write_json("logs/INC-TEST/observability.json", expected)
        response = self.client.get("/observability/INC-TEST")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_release_evidence_matches_requested_version(self):
        expected = {"current_version": "v2.8.4", "changes": ["synthetic change"]}
        self.write_json("repositories/noir-operations/release-v2.8.4.json", expected)
        response = self.client.get("/repository/releases/v2.8.4")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_unsupported_release_returns_404(self):
        self.write_json("repositories/noir-operations/release-v2.8.4.json", {"current_version": "v2.8.4"})
        response = self.client.get("/repository/releases/v0.0.0")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "No repository evidence found for release v0.0.0.")

    def test_historical_evidence_round_trip(self):
        expected = {"incidents": [{"incident_id": "HISTORY-TEST"}]}
        self.write_json("knowledge/historical-incidents.json", expected)
        response = self.client.get("/knowledge/historical-incidents")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), expected)

    def test_runbook_preserves_utf8_markdown(self):
        path = self.root / "knowledge/database-troubleshooting.md"
        path.parent.mkdir(parents=True)
        text = "# Synthetic runbook\nCheck café service connections.\n"
        path.write_text(text, encoding="utf-8")
        response = self.client.get("/knowledge/database-troubleshooting")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "title": "Database Connection Troubleshooting Runbook", "content": text,
        })

    def test_missing_json_evidence_returns_404(self):
        for route, filename in (
            ("/incidents/MISSING", "incident.json"),
            ("/observability/MISSING", "observability.json"),
            ("/repository/releases/v2.8.4", "release-v2.8.4.json"),
            ("/knowledge/historical-incidents", "historical-incidents.json"),
        ):
            with self.subTest(route=route):
                response = self.client.get(route)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["detail"], f"Evidence file not found: {filename}")

    def test_invalid_json_evidence_returns_controlled_500(self):
        for relative, route in (
            ("incidents/INC-TEST/incident.json", "/incidents/INC-TEST"),
            ("logs/INC-TEST/observability.json", "/observability/INC-TEST"),
            ("repositories/noir-operations/release-v2.8.4.json", "/repository/releases/v2.8.4"),
            ("knowledge/historical-incidents.json", "/knowledge/historical-incidents"),
        ):
            with self.subTest(route=route):
                path = self.write_json(relative, {})
                path.write_text("{invalid", encoding="utf-8")
                response = self.client.get(route)
                self.assertEqual(response.status_code, 500)
                self.assertEqual(response.json()["detail"], f"Invalid JSON evidence file: {path.name}")

    def test_missing_runbook_returns_404(self):
        response = self.client.get("/knowledge/database-troubleshooting")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Database troubleshooting runbook not found.")

    def test_bundled_data_is_not_used_when_fixture_is_missing(self):
        # INC-1042 exists in the repository; an isolated test must not fall back to it.
        self.assertEqual(self.client.get("/incidents/INC-1042").status_code, 404)

    def test_evidence_routes_reject_post(self):
        response = self.client.post("/incidents/INC-TEST", json={"title": "not written"})
        self.assertEqual(response.status_code, 405)
        self.assertFalse((self.root / "incidents").exists())


if __name__ == "__main__":
    unittest.main()
