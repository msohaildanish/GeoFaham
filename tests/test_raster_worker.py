"""Real-process checks for raster timeout/cancellation and successful export."""
import asyncio
import multiprocessing
import tempfile
import unittest
from pathlib import Path

import rasterio

from agents.core.config import AgentsConfig, ConfigProvider
from agents.core.types import GeoFahamToolResponse
from agents.raster_ops_agent.tools import execute_custom_raster_code
from agents.shared.responses import validate_response_artifacts


class RasterWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_success_returns_statistics_and_persistent_raster_artifact(self):
        with tempfile.TemporaryDirectory() as folder:
            config = AgentsConfig(); config.paths.base_dir = Path(folder)
            with ConfigProvider.override(config):
                stats = GeoFahamToolResponse.model_validate_json(await execute_custom_raster_code(
                    "result = {'mean': 0.5, 'count': 2}", 'test', False, 'statistics'))
                self.assertEqual(stats.data, [{'mean':.5, 'count':2}])
                self.assertEqual(stats.data_type, 'stats')
                layer = GeoFahamToolResponse.model_validate_json(await execute_custom_raster_code(
                    "result = xr.DataArray(np.arange(4, dtype='float32').reshape(2,2), "
                    "dims=('y','x'), coords={'y':[1.5,0.5], 'x':[0.5,1.5]}).rio.write_crs(4326)",
                    'test layer', True, 'raster'))
                self.assertEqual(layer.type, 'layer', layer.error_message)
                validate_response_artifacts(layer)
                self.assertTrue(Path(layer.artifact.path).is_relative_to(Path(folder)))
                with rasterio.open(layer.artifact.path) as ds:
                    self.assertEqual(ds.read(1).sum(),6)

    async def test_infinite_generated_code_is_stopped_at_timeout_and_next_call_works(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder)/'started.npy'
            config = AgentsConfig(); config.paths.base_dir = Path(folder)
            config.query.raster_timeout_seconds = 12
            before = {p.pid for p in multiprocessing.active_children()}
            with ConfigProvider.override(config):
                response = GeoFahamToolResponse.model_validate_json(await execute_custom_raster_code(
                    f"np.save({str(marker)!r}, np.array([1]))\nwhile True:\n    pass",
                    'timeout test', False, 'statistics'))
                self.assertTrue(marker.exists(), 'Worker must have reached generated code')
                self.assertEqual(response.type, 'error')
                self.assertEqual(response.metadata['error_type'], 'timeout')
                self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)
                recovered = GeoFahamToolResponse.model_validate_json(await execute_custom_raster_code(
                    "result = {'count': 1}", 'after timeout', False, 'statistics'))
                self.assertEqual(recovered.data, [{'count':1}])

    async def test_cancel_stops_running_generated_code_and_reaps_the_process(self):
        with tempfile.TemporaryDirectory() as folder:
            marker = Path(folder)/'started.npy'
            config = AgentsConfig(); config.paths.base_dir = Path(folder)
            before = {p.pid for p in multiprocessing.active_children()}
            with ConfigProvider.override(config):
                task = asyncio.create_task(execute_custom_raster_code(
                    f"np.save({str(marker)!r}, np.array([1]))\nwhile True:\n    pass",
                    'cancel test', False, 'statistics'))
                try:
                    async with asyncio.timeout(15):
                        while not marker.exists() and not task.done():
                            await asyncio.sleep(.05)
                    self.assertTrue(marker.exists(), 'Worker must have reached generated code')
                finally:
                    task.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await asyncio.wait_for(task, 4)
                self.assertEqual({p.pid for p in multiprocessing.active_children()}, before)


if __name__ == '__main__':
    unittest.main()
