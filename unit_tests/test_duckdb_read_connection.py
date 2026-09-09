import ast
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock


class ReadConnectionTest(unittest.TestCase):
    def make_context(self, connect):
        path = Path(__file__).resolve().parents[1] / 'data_manager/duckdb_connection_pool.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        method = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)
                      and n.name == 'get_read_connection')
        sleep = Mock()
        scope = dict(contextmanager=contextmanager, duckdb=SimpleNamespace(connect=connect),
                     logger=Mock(), time=SimpleNamespace(sleep=sleep))
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), scope)
        manager = SimpleNamespace(duckdb_path='unused', _connection_count=0)
        return scope['get_read_connection'](manager), manager, sleep

    def test_query_lock_error_is_preserved_without_retry(self):
        connection = Mock()
        connect = Mock(return_value=connection)
        ctx, manager, sleep = self.make_context(connect)
        error = RuntimeError('query lock conflict')
        with self.assertRaises(RuntimeError) as caught:
            with ctx:
                raise error
        self.assertIs(caught.exception, error)
        connect.assert_called_once()
        sleep.assert_not_called()
        connection.close.assert_called_once()
        self.assertEqual(manager._connection_count, 0)

    def test_connection_lock_still_retries(self):
        connection = Mock()
        connect = Mock(side_effect=[RuntimeError('database locked'), connection])
        ctx, manager, sleep = self.make_context(connect)
        with ctx as actual:
            self.assertIs(actual, connection)
            self.assertEqual(manager._connection_count, 1)
        self.assertEqual(connect.call_count, 2)
        sleep.assert_called_once()
        self.assertEqual(manager._connection_count, 0)

    def test_close_error_does_not_leak_connection_count(self):
        connection = Mock()
        connection.close.side_effect = OSError('close failed')
        ctx, manager, _ = self.make_context(Mock(return_value=connection))
        with self.assertRaisesRegex(OSError, 'close failed'):
            with ctx:
                pass
        self.assertEqual(manager._connection_count, 0)


if __name__ == '__main__':
    unittest.main()
