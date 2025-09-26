import asyncio

class FakeSession:
    def __init__(self, statuses):
        self.statuses = statuses
        self.calls = 0
    
    class _Resp:
        def __init__(self, status):
            self.status = status
            self.headers = {}
            self.url = 'http://fake'
        async def text(self):
            return '{"ok": true}' if self.status == 200 else '{"error":"unauthorized"}'
        async def __aenter__(self):
            return self
        async def __aexit__(self, exc_type, exc, tb):
            return False
    
    def post(self, url, json=None, headers=None):
        status = self.statuses[self.calls] if self.calls < len(self.statuses) else 200
        self.calls += 1
        return self._Resp(status)

class FakeAuthService:
    def __init__(self):
        self.invalidate_count = 0
        self.refresh_count = 0
        self._token = 'initial'
        self._gave_new = False
    def invalidate_token(self):
        self.invalidate_count += 1
        self._token = None
    def refresh_token(self):
        self.refresh_count += 1
        if not self._gave_new:
            self._gave_new = True
            self._token = 'new_token'
            return self._token
        return self._token

async def run_test():
    from services.uploader_service import UploaderService, UploadState
    # Simula primeira chamada 401, segunda 200 após refresh
    session = FakeSession([401, 200])
    svc = UploaderService(
        file_path='fake.csv',
        auth_token='expired',
        endpoint_url='http://fake',
        logger=print,
        save_json_enabled=False,
        auth_service=FakeAuthService(),
        max_token_retries=1
    )
    # Ajustar estado para RUNNING e total
    svc.state = UploadState.RUNNING
    svc.total_rows = 1
    # Chamada
    await svc._send_row(session, {'a':1}, asyncio.Semaphore(1), 1, 1)

if __name__ == '__main__':
    asyncio.run(run_test())
