"""Isolated regression tests for the selected student-management snapshot.

Uses only stdlib unittest as the test framework. Requests are executed inside
the process through ASGI; no listening server or network client is created.
"""
import argparse
import asyncio
import contextlib
import importlib.abc
import io
import json
from pathlib import Path
import socket
import sys
import traceback
import unittest


def redact(value):
    if isinstance(value, dict):
        return {key: ('[synthetic credential redacted]' if 'password' in key.lower()
                      else redact(item)) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


class BlockOriginalConfiguration(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname in {'settings', 'main'}:
            raise ImportError('Original application configuration is blocked in isolated tests')
        return None


sys.meta_path.insert(0, BlockOriginalConfiguration())


async def asgi_request(app, method, path, payload=None, query=''):
    encoded = b'' if payload is None else json.dumps(payload).encode('utf-8')
    scope = {
        'type': 'http', 'asgi': {'version': '3.0', 'spec_version': '2.3'},
        'http_version': '1.1', 'method': method, 'scheme': 'http',
        'path': path, 'raw_path': path.encode('ascii'),
        'query_string': query.encode('ascii'), 'root_path': '',
        'headers': [(b'host', b'isolated.test'),
                    (b'content-type', b'application/json'),
                    (b'content-length', str(len(encoded)).encode('ascii'))],
        'client': ('test-client', 1), 'server': ('isolated.test', 80),
    }
    events = []
    delivered = False

    async def receive():
        nonlocal delivered
        if not delivered:
            delivered = True
            return {'type': 'http.request', 'body': encoded, 'more_body': False}
        return {'type': 'http.disconnect'}

    async def send(message):
        events.append(message)

    app_error = None
    try:
        await app(scope, receive, send)
    except Exception as exc:
        if not any(event['type'] == 'http.response.start' for event in events):
            raise
        # Starlette can re-raise after its configured error response is sent.
        app_error = type(exc).__name__
    start = next(event for event in events if event['type'] == 'http.response.start')
    body = b''.join(event.get('body', b'') for event in events
                    if event['type'] == 'http.response.body')
    result = {'status': start['status'], 'body': json.loads(body.decode('utf-8'))}
    if app_error:
        result['application_exception_after_response'] = app_error
    return result


class StudentSystemTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.evidence = []
        self._original_connect = socket.socket.connect
        self._original_connect_ex = socket.socket.connect_ex
        self._original_create_connection = socket.create_connection

        def network_blocked(*args, **kwargs):
            raise RuntimeError('Network connections are disabled for isolated tests')

        socket.socket.connect = network_blocked
        socket.socket.connect_ex = network_blocked
        socket.create_connection = network_blocked
        from fastapi import FastAPI
        from tortoise import Tortoise
        from models import Major, Clazz, Admin
        from api import api_router
        from common.exception_handler import setup_exceptions
        self.Tortoise, self.Major, self.Clazz, self.Admin = Tortoise, Major, Clazz, Admin
        await Tortoise.init(db_url='sqlite://:memory:', modules={'models': ['models']})
        await Tortoise.generate_schemas()
        self.app = FastAPI()
        self.app.include_router(api_router)
        setup_exceptions(self.app)

    async def asyncTearDown(self):
        try:
            if hasattr(self, 'Tortoise'):
                await self.Tortoise.close_connections()
        finally:
            socket.socket.connect = self._original_connect
            socket.socket.connect_ex = self._original_connect_ex
            socket.create_connection = self._original_create_connection

    async def request(self, method, path, payload=None, query=''):
        response = await asgi_request(self.app, method, path, payload, query)
        self.evidence.append(redact({'method': method, 'path': path, 'query': query,
                                     'request': payload, 'response': response}))
        self.assertEqual(response['status'], 200, 'This application uses HTTP 200 plus a business code')
        return response['body']

    async def stored(self, table, columns='id,no,name,college'):
        # Table and column identifiers are controlled test literals, never inputs.
        rows = await self.Tortoise.get_connection('default').execute_query_dict(
            f'SELECT {columns} FROM {table} ORDER BY id')
        self.evidence.append({'database_check': {'backend': 'temporary SQLite',
                                                'table': table, 'rows': redact(rows)}})
        return rows

    async def seed_major(self, code='QA-MAJOR-A', name='QA Major A'):
        result = await self.request('POST', '/major/add',
                                    {'no': code, 'name': name, 'college': 'QA College'})
        self.assertEqual(result['code'], '200')
        row = await self.Major.get(no=code)
        return row

    async def test_major_create_query_and_database_consistency(self):
        """Valid create and query must agree with stored data."""
        row = await self.seed_major()
        result = await self.request('GET', f'/major/selectById/{row.id}')
        self.assertEqual(result['code'], '200')
        self.assertEqual(result['data']['no'], 'QA-MAJOR-A')
        self.assertEqual(result['data']['name'], 'QA Major A')
        rows = await self.stored('major')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], result['data']['name'])

    async def test_duplicate_major_create_is_rejected_without_extra_row(self):
        """The existing create rule rejects a repeated major code."""
        await self.seed_major()
        result = await self.request('POST', '/major/add',
                                    {'no': 'QA-MAJOR-A', 'name': 'Repeated', 'college': 'QA College'})
        self.assertEqual(result['code'], '500')
        self.assertEqual(result['msg'], '专业代码重复')
        self.assertEqual(len(await self.stored('major')), 1)

    async def test_major_update_same_code_changes_name(self):
        """Editing a name without changing its own unique code must be allowed."""
        row = await self.seed_major()
        result = await self.request('PUT', '/major/update',
                                    {'id': row.id, 'no': row.no, 'name': 'QA Major Renamed',
                                     'college': 'QA College'})
        rows = await self.stored('major')
        self.assertEqual(result['code'], '200', 'Updating an existing major must not collide with itself')
        self.assertEqual(rows[0]['name'], 'QA Major Renamed')

    async def test_major_update_to_another_record_code_is_rejected(self):
        """The self-update fix must keep rejecting another record's major code."""
        first = await self.seed_major()
        second = await self.seed_major('QA-MAJOR-B', 'QA Major B')
        result = await self.request('PUT', '/major/update',
                                    {'id': second.id, 'no': first.no, 'name': 'Invalid Duplicate',
                                     'college': 'QA College'})
        self.assertEqual(result['code'], '500')
        rows = await self.stored('major')
        self.assertEqual([row['no'] for row in rows], ['QA-MAJOR-A', 'QA-MAJOR-B'])

    async def test_class_creation_preserves_major_relationship(self):
        """Class majorId must be stored as the correct major_id and exposed in pagination."""
        major = await self.seed_major()
        result = await self.request('POST', '/clazz/add',
                                    {'no': 'QA-CLASS-A', 'name': 'QA Class A',
                                     'teacher': 'QA Teacher', 'majorId': major.id})
        self.assertEqual(result['code'], '200')
        rows = await self.stored('clazz', 'id,no,name,major_id')
        self.assertEqual(rows[0]['major_id'], major.id)
        result = await self.request('GET', '/clazz/selectPage', query='pageNum=1&pageSize=10')
        self.assertEqual(result['code'], '200')
        self.assertEqual(result['data']['total'], 1)
        self.assertEqual(result['data']['list'][0]['majorId'], major.id)
        self.assertEqual(result['data']['list'][0]['majorName'], major.name)

    async def test_invalid_class_id_has_business_validation_error(self):
        """A non-integer path parameter must return the configured validation response."""
        result = await self.request('GET', '/clazz/selectById/not-an-integer')
        self.assertEqual(result['code'], '500')
        self.assertEqual(result['msg'], '请求参数错误')
        self.assertEqual(await self.Clazz.all().count(), 0)

    async def test_class_update_without_id_is_rejected(self):
        """Missing ID must not produce a successful class update."""
        result = await self.request('PUT', '/clazz/update',
                                    {'no': 'QA-CLASS-A', 'name': 'No ID'})
        self.assertEqual(result['code'], '500')
        self.assertEqual(result['msg'], '缺少参数ID')
        self.assertEqual(await self.Clazz.all().count(), 0)

    async def test_login_unknown_admin_is_rejected(self):
        """An unknown administrator account must not authenticate."""
        result = await self.request('POST', '/login',
                                    {'username': 'qa-does-not-exist', 'password': 'synthetic-only',
                                     'role': '管理员'})
        self.assertEqual(result['code'], '500')
        self.assertEqual(result['msg'], '账号或密码错误')

    async def test_login_unsupported_role_is_rejected(self):
        """An unsupported role must not bypass the only implemented account check."""
        result = await self.request('POST', '/login',
                                    {'username': 'qa-does-not-exist', 'password': 'synthetic-only',
                                     'role': 'QA-UNSUPPORTED-ROLE'})
        self.assertEqual(result['code'], '500', 'An unsupported role must not receive login success')


class RecordingResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []

    def _record(self, test, status, err=None):
        row = {'name': test._testMethodName, 'purpose': test.shortDescription(),
               'status': status, 'evidence': getattr(test, 'evidence', [])}
        if err:
            row['failure_type'] = err[0].__name__
            row['message'] = str(err[1])
        self.records.append(redact(row))

    def addSuccess(self, test):
        super().addSuccess(test)
        self._record(test, 'passed')

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._record(test, 'assertion_failed', err)

    def addError(self, test, err):
        super().addError(test, err)
        self._record(test, 'execution_error', err)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True)
    parser.add_argument('--result', required=True)
    args = parser.parse_args()
    snapshot = Path(args.snapshot).resolve()
    sys.path.insert(0, str(snapshot))
    stream, application_stdout = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(application_stdout), contextlib.redirect_stderr(application_stdout):
        suite = unittest.defaultTestLoader.loadTestsFromTestCase(StudentSystemTests)
        result = unittest.TextTestRunner(stream=stream, verbosity=2,
                                        resultclass=RecordingResult).run(suite)
    payload = {
        'snapshot': snapshot.name, 'framework': 'Python stdlib unittest',
        'transport': 'in-process ASGI caller; no server or network client',
        'database': 'new SQLite in-memory database for each test',
        'tests_run': result.testsRun, 'passed': sum(row['status']=='passed' for row in result.records),
        'assertion_failures': len(result.failures), 'execution_errors': len(result.errors),
        'tests': result.records,
        'original_main_or_settings_imported': any(name in sys.modules for name in ['main', 'settings']),
        'runner_log': 'See named test records and assertion messages; machine-specific tracebacks are omitted.',
        'application_log': 'Runtime stdout and stderr are omitted from portable results to avoid embedding local machine paths.',
    }
    Path(args.result).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: payload[key] for key in ['tests_run','passed','assertion_failures','execution_errors']},ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
