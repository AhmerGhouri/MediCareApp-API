"""Dependency-free handler tests; no app import, scheduler, Oracle or SMTP calls.
Run: python3 -B -m unittest discover -s tests -v
These isolate function bodies with fake dependencies, not ASGI integration.
"""
import ast
import asyncio
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HTTPException(Exception):
    def __init__(self, status_code, detail, headers=None):
        self.status_code, self.detail, self.headers = status_code, detail, headers

class DB:
    def __init__(self, allowed=True):
        self.allowed = allowed
    def execute(self, *args, **kwargs):
        return self
    def mappings(self):
        return self
    def all(self):
        return []
    def fetchone(self):
        return (1,) if self.allowed else None

def load_handler(file, name):
    tree = ast.parse((ROOT / file).read_text())
    node = next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == name)
    node.decorator_list = []
    node.returns = None
    node.args.defaults = []
    for arg in node.args.args:
        arg.annotation = None
    module = ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))
    scope = dict(text=lambda sql: sql, HTTPException=HTTPException,
                 JSONResponse=lambda **kwargs: kwargs, date=date, datetime=datetime)
    exec(compile(module, str(ROOT / file), "exec"), scope)
    return scope[name]

class ResponseTests(unittest.TestCase):
    def test_nine_empty_collections(self):
        cases = {
            "get_lab_reports": "reports", "get_radiology_reports": "reports",
            "get_inpatient_history": "inpatienthistory",
            "get_consultation_history": "consultationshistory",
            "get_upcomingappointments": "appointments",
            "get_todaysclinic": "consultations", "get_consultants": None,
            "get_appointments": "appointments", "get_combinelabreports": None,
        }
        for name, key in cases.items():
            with self.subTest(handler=name):
                fn = load_handler("app/routers/patient_router.py", name)
                args = dict(db=DB(), current_user=SimpleNamespace(mob="test"),
                            opat_id="test", consl_id="test", app_date="2026-09-22")
                result = fn(**{k: args[k] for k in fn.__code__.co_varnames[:fn.__code__.co_argcount]})
                self.assertEqual(result[key] if key else result, [])

    def test_consultation_access_denial_is_not_empty_success(self):
        fn = load_handler("app/routers/patient_router.py", "get_consultation_history")
        with self.assertRaises(HTTPException) as caught:
            fn("test", DB(allowed=False), SimpleNamespace(mob="test"))
        self.assertEqual(caught.exception.status_code, 404)

    def test_http_envelope_preserves_auth_headers(self):
        fn = load_handler("app/main.py", "http_exception_handler")
        result = asyncio.run(fn(None, HTTPException(401, "Sign in", {"WWW-Authenticate": "Bearer"})))
        self.assertEqual(result["status_code"], 401)
        self.assertEqual(result["content"]["code"], "AUTHENTICATION_REQUIRED")
        self.assertEqual(result["headers"], {"WWW-Authenticate": "Bearer"})

    def test_structured_error_and_sanitized_server_error(self):
        fn = load_handler("app/main.py", "http_exception_handler")
        result = asyncio.run(fn(None, HTTPException(409, {"code": "ACCOUNT_EXISTS", "message": "Already registered"})))
        self.assertEqual(result["content"]["code"], "ACCOUNT_EXISTS")
        result = asyncio.run(fn(None, HTTPException(500, "private SQL details")))
        self.assertNotIn("private", str(result))

    def test_validation_never_echoes_input(self):
        fn = load_handler("app/main.py", "validation_exception_handler")
        error = SimpleNamespace(errors=lambda: [
            {"loc": ("body", "password"), "input": "private-secret", "ctx": {"private": "secret"}},
            {"loc": ("body", "private-field"), "input": "private-value"},
        ])
        result = asyncio.run(fn(None, error))
        self.assertEqual(result["content"]["errors"], {"password": "Please check this field."})
        self.assertNotIn("private", str(result))

    def test_all_backend_python_parses(self):
        for path in (ROOT / "app").rglob("*.py"):
            ast.parse(path.read_text(), filename=str(path))

if __name__ == "__main__":
    unittest.main()
