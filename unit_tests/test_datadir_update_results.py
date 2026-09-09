"""Exercise the GUI worker without importing Qt or connecting to QMT."""
import ast
import builtins
from datetime import datetime, timedelta
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import pandas as pd


def worker_methods():
    path = Path(__file__).resolve().parents[1] / 'gui_app/widgets/local_data_manager_widget.py'
    tree = ast.parse(path.read_text(encoding='utf-8'))
    worker = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                  and n.name == 'DataDownloadThread')
    methods = [n for n in worker.body if isinstance(n, ast.FunctionDef)
               and n.name in ('_update_from_datadir', '_update_data')]
    namespace = dict(datetime=datetime, timedelta=timedelta,
                     get_default_db_path=lambda: 'unused-test-db')
    exec(compile(ast.Module(body=methods, type_ignores=[]), str(path), 'exec'), namespace)
    return namespace


class DatadirResultsTest(unittest.TestCase):
    def run_worker(self, written=1, write_error=None, read_error=None):
        methods = worker_methods()
        manager = Mock()
        manager.execute_read_query.return_value = pd.DataFrame([
            dict(stock_code='600519.SH', latest_date='2025-09-03')])
        manager.insert_dataframe.return_value = written
        manager.insert_dataframe.side_effect = write_error
        reader = Mock()
        reader.read_daily_data.side_effect = read_error
        reader.read_daily_data.return_value = pd.DataFrame([
            dict(time=pd.Timestamp('2025-09-04'), open=10, high=11,
                 low=9, close=10, volume=100, amount=1000)])
        pool = ModuleType('data_manager.duckdb_connection_pool')
        pool.get_db_manager = lambda path: manager
        local = ModuleType('core.qmt_local_reader')
        local.QMTLocalReader = Mock(return_value=reader)
        worker = SimpleNamespace(_is_running=True, log_signal=Mock(),
                                 progress_signal=Mock(), finished_signal=Mock())
        with patch.dict('sys.modules', {pool.__name__: pool, local.__name__: local}):
            methods['_update_from_datadir'](worker, SimpleNamespace(datadir='unused'))
        return worker.finished_signal.emit.call_args.args[0]

    def test_success_requires_confirmed_write(self):
        result = self.run_worker()
        self.assertEqual((result['success'], result['failed']), (1, 0))

    def test_write_exception_is_failure(self):
        result = self.run_worker(write_error=RuntimeError('locked'))
        self.assertEqual((result['success'], result['failed']), (0, 1))
        self.assertEqual(result['failed_list'], ['600519.SH'])

    def test_zero_write_is_failure(self):
        result = self.run_worker(written=0)
        self.assertEqual((result['success'], result['failed']), (0, 1))

    def test_read_exception_is_not_stale_data(self):
        result = self.run_worker(read_error=OSError('invalid DAT'))
        self.assertEqual((result['failed'], result['skipped']), (1, 0))

    def test_big_qmt_route_does_not_import_xtquant(self):
        pool = ModuleType('data_manager.duckdb_connection_pool')
        pool.get_db_manager = Mock()
        router = ModuleType('data_manager.source_router')
        router.DataRoute = SimpleNamespace(BIG_QMT='big', FALLBACK='fallback')
        worker = SimpleNamespace(_probe_route=lambda: SimpleNamespace(mode='big'),
                                 _update_from_datadir=Mock(), error_signal=Mock(),
                                 log_signal=Mock())
        original_import = builtins.__import__

        def guarded_import(name, *args, **kwargs):
            if name == 'xtquant':
                raise AssertionError('Big QMT must not require xtquant')
            return original_import(name, *args, **kwargs)

        methods = worker_methods()
        with patch.dict('sys.modules', {pool.__name__: pool, router.__name__: router}), \
                patch('builtins.__import__', side_effect=guarded_import):
            methods['_update_data'](worker)
        worker._update_from_datadir.assert_called_once()
        worker.error_signal.emit.assert_not_called()


if __name__ == '__main__':
    unittest.main()
