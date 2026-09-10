import ast
from datetime import datetime
from pathlib import Path
from types import ModuleType
import unittest
from unittest.mock import Mock, patch
import pandas as pd


class ImportRangeTest(unittest.TestCase):
    def run_import(self, write_error=None):
        path = Path(__file__).resolve().parents[1] / 'gui_app/widgets/local_data_manager_widget.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                  and n.name == 'run_datadir_daily_import')
        scope = dict(pd=pd, datetime=datetime, get_default_db_path=lambda: 'test')
        exec(compile(ast.Module(body=[fn], type_ignores=[]), str(path), 'exec'), scope)
        reader = Mock()
        reader.read_daily_data.return_value = pd.DataFrame([
            dict(time=pd.Timestamp(day), open=10, high=11, low=9, close=10,
                 volume=100, amount=1000)
            for day in ('2025-09-01', '2025-09-02', '2025-09-03')])
        manager = Mock()
        manager.insert_dataframe.side_effect = write_error or (lambda df, *a, **kw: len(df))
        local = ModuleType('core.qmt_local_reader')
        local.QMTLocalReader = Mock(return_value=reader)
        pool = ModuleType('data_manager.duckdb_connection_pool')
        pool.get_db_manager = lambda path: manager
        router = ModuleType('data_manager.source_router')
        router.STOCK_PREFIXES_BY_MARKET = {}
        router._filter_datadir_codes = Mock(side_effect=AssertionError('must not scan market'))
        with patch.dict('sys.modules', {m.__name__: m for m in (local, pool, router)}):
            result = scope['run_datadir_daily_import'](
                ['600519.SH'], '2025-09-02', '2025-09-02', 'unused',
                Mock(), Mock(), lambda: True)
        return result, manager

    def test_only_requested_date_and_symbol_written(self):
        result, manager = self.run_import()
        df = manager.insert_dataframe.call_args.args[0]
        self.assertEqual(df.date.tolist(), ['2025-09-02'])
        self.assertEqual(df.stock_code.tolist(), ['600519.SH'])
        self.assertEqual(result['record_count'], 1)
        self.assertEqual(result['success'], 1)
        self.assertEqual(manager.insert_dataframe.call_args.kwargs['conflict_handling'], 'ignore')

    def test_failed_save_never_reports_success(self):
        result, _ = self.run_import(RuntimeError('locked'))
        self.assertEqual((result['success'], result['failed'], result['record_count']), (0, 1, 0))
        self.assertIn('600519.SH', result['failed_list'][0])


if __name__ == '__main__':
    unittest.main()
