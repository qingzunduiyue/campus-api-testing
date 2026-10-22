from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from uuid import uuid4
from urllib.request import Request, build_opener, ProxyHandler
urlopen = build_opener(ProxyHandler({})).open
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / 'project' / 'backend'

class RunningServer:
    def __init__(self, module, extra_env):
        self.temp = tempfile.TemporaryDirectory()
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            self.port = probe.getsockname()[1]
        self.url = f'http://127.0.0.1:{self.port}'
        self.shutdown_token = uuid4().hex
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8', QA_SHUTDOWN_TOKEN=self.shutdown_token, **extra_env)
        if module == 'main:app':
            env['DATABASE_URL'] = 'sqlite://' + (Path(self.temp.name) / 'demo.sqlite3').as_posix()
            env['UPLOAD_DIR'] = str(Path(self.temp.name) / 'uploads')
        self.log = open(Path(self.temp.name) / 'server.log', 'w+', encoding='utf-8', errors='replace')
        self.process = subprocess.Popen([sys.executable, '-B', str(ROOT / 'test_server.py'), module, str(self.port)], cwd=BACKEND, env=env,
            stdout=self.log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        try:
            for _ in range(200):
                if self.process.poll() is not None:
                    self.log.seek(0)
                    raise RuntimeError(self.log.read())
                try:
                    with urlopen(self.url + '/openapi.json', timeout=1) as response:
                        if response.status == 200:
                            return
                except (URLError, OSError):
                    time.sleep(0.1)
            raise RuntimeError('Local application did not become ready')
        except BaseException:
            self.close()
            raise

    def request(self, path, data=None, method=None, headers=None, raw=None):
        if raw is None and data is not None:
            raw = json.dumps(data).encode('utf-8')
        headers = headers or {'Content-Type': 'application/json'}
        request = Request(self.url + path, data=raw, method=method, headers=headers)
        try:
            response = urlopen(request, timeout=20)
        except HTTPError as error:
            response = error
        with response:
            payload = response.read()
            if 'application/json' in response.headers.get('Content-Type', ''):
                payload = json.loads(payload)
            return response.status, payload

    def close(self):
        if hasattr(self, 'process') and self.process.poll() is None:
            try:
                self.request('/__qa_shutdown__', method='POST', raw=b'',
                    headers={'X-QA-Shutdown': self.shutdown_token})
                self.process.wait(timeout=15)
            except (OSError, subprocess.TimeoutExpired):
                self.process.terminate()
                self.process.wait(timeout=5)
                raise
        self.log.close()
        self.temp.cleanup()

class ApplicationSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = RunningServer('main:app', {'SEED_DEMO': 'true'})

    @classmethod
    def tearDownClass(cls):
        cls.server.close()

    def call(self, path, data=None, method=None):
        status, payload = self.server.request(path, data, method)
        self.assertEqual(status, 200, payload)
        return payload

    def test_01_startup_seed_and_login(self):
        health = self.call('/')
        self.assertEqual(health['data']['mode'], 'local-demo')
        good = self.call('/login', {'username': 'demo_admin', 'password': 'Demo12345!', 'role': '管理员'})
        self.assertEqual(good['code'], '200')
        self.assertIsInstance(good['data']['id'], int)
        bad = self.call('/login', {'username': 'missing', 'password': 'missing', 'role': 'unsupported'})
        self.assertEqual(bad['code'], '500')

    def test_02_registration_password_change_and_login(self):
        account = {'username': 'qa_registered', 'password': 'Synthetic123!', 'role': '管理员'}
        self.assertEqual(self.call('/register', account)['code'], '200')
        self.assertEqual(self.call('/register', account)['code'], '500')
        logged = self.call('/login', account)['data']
        self.assertEqual(self.call('/updatePassword', {**logged, 'newPassword': 'Synthetic456!'}, 'PUT')['code'], '200')
        self.assertEqual(self.call('/login', account)['code'], '500')
        self.assertEqual(self.call('/login', {**account, 'password': 'Synthetic456!'})['code'], '200')

    def test_03_major_class_create_update_query_delete(self):
        major = {'no': 'QA-HTTP', 'name': 'HTTP专业', 'college': '测试学院'}
        self.assertEqual(self.call('/major/add', major)['code'], '200')
        found = self.call('/major/selectPage?name=HTTP')['data']['list']
        self.assertEqual(len(found), 1)
        saved = found[0]
        self.assertEqual(self.call('/major/update', {**saved, 'name': 'HTTP已更新'}, 'PUT')['code'], '200')
        self.assertEqual(self.call('/major/selectById/' + str(saved['id']))['data']['name'], 'HTTP已更新')
        self.assertEqual(self.call('/clazz/add', {'no': 'QA-CLASS', 'name': 'HTTP测试班', 'teacher': '示例教师', 'majorId': saved['id']})['code'], '200')
        clazz = self.call('/clazz/selectPage?name=HTTP')['data']['list'][0]
        self.assertEqual(clazz['majorId'], saved['id'])
        self.assertEqual(clazz['majorName'], 'HTTP已更新')
        self.assertEqual(self.call('/clazz/delete/' + str(clazz['id']), method='DELETE')['code'], '200')
        self.assertEqual(self.call('/major/delete/' + str(saved['id']), method='DELETE')['code'], '200')
        self.assertEqual(self.call('/major/selectPage?name=HTTP')['data']['total'], 0)

    def test_04_file_upload_and_download(self):
        boundary = 'qa-synthetic-boundary'
        body = (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="sample.txt"\r\nContent-Type: text/plain\r\n\r\nSYNTHETIC UPLOAD\r\n--{boundary}--\r\n').encode()
        status, payload = self.server.request('/files/upload', method='POST', raw=body,
            headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        self.assertEqual(status, 200)
        self.assertEqual(payload['code'], '200')
        self.assertTrue(payload['data'].startswith(self.server.url + '/files/download/'))
        with urlopen(payload['data'], timeout=5) as response:
            self.assertEqual(response.read(), b'SYNTHETIC UPLOAD')

    def test_05_request_validation_in_real_server(self):
        status, payload = self.server.request('/clazz/selectById/not-an-integer')
        self.assertEqual(status, 200)
        self.assertEqual(payload['code'], '500')

if __name__ == '__main__':
    unittest.main(verbosity=2)
