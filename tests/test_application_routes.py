# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

"""Application routes retained when integrating agent workflows."""

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.routes import reset
import server


class ApplicationRouteTests(unittest.TestCase):
    def test_frontend_configuration_keeps_the_deployment_maps_key(self):
        with patch.dict("os.environ", {"AZURE_MAPS_KEY": "test-maps-key"}):
            with TestClient(server.app) as client:
                response = client.get("/api/config")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), {"azureMapsKey": "test-maps-key"})
                self.assertEqual(client.get("/").status_code, 200)
                self.assertEqual(client.get("/frontend/js/app.js").status_code, 200)

    def test_server_mounts_reset_without_the_old_debug_routes(self):
        routes = {getattr(route, "path", None): route for route in server.app.routes}
        self.assertIs(routes["/api/reset"].endpoint, reset.reset_application)
        self.assertNotIn("/api/save-benchmark-gt", routes)
        self.assertNotIn("/api/test-raster", routes)
