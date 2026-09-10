import ast
import hmac
import os
from pathlib import Path
import unittest
from unittest.mock import patch


def security_functions():
    path = Path(__file__).resolve().parents[1] / "easy_xt/data_service/server.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {"_is_loopback_host", "_configured_token", "_token_is_valid", "_validate_bind_security"}
    nodes = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
    scope = {"os": os, "hmac": hmac}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), scope)
    return scope


class DataNodeSecurityTest(unittest.TestCase):
    def test_loopback_does_not_need_token(self):
        server = security_functions()
        with patch.dict(os.environ, {"EASYXT_DATA_SERVICE_TOKEN": ""}, clear=False):
            server["_validate_bind_security"]("127.0.0.1")

    def test_remote_bind_requires_token(self):
        server = security_functions()
        with patch.dict(os.environ, {"EASYXT_DATA_SERVICE_TOKEN": ""}, clear=False):
            with self.assertRaisesRegex(RuntimeError, "EASYXT_DATA_SERVICE_TOKEN"):
                server["_validate_bind_security"]("100.79.82.1")

    def test_bearer_token_must_match_exactly(self):
        server = security_functions()
        self.assertTrue(server["_token_is_valid"]("Bearer example", "example"))
        self.assertFalse(server["_token_is_valid"]("Bearer wrong", "example"))
        self.assertFalse(server["_token_is_valid"]("example", "example"))


if __name__ == "__main__":
    unittest.main()
