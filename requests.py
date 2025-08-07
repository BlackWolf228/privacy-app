import json
from urllib import request as _request, error as _error


class Response:
    def __init__(self, resp):
        self._resp = resp
        self.status_code = getattr(resp, "status", getattr(resp, "code", 200))

    def json(self):
        data = self._resp.read().decode()
        return json.loads(data) if data else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise _error.HTTPError(
                self._resp.geturl(),
                self.status_code,
                self._resp.reason,
                self._resp.headers,
                None,
            )


def request(method, url, headers=None, data=None):
    req = _request.Request(
        url,
        data=data.encode() if isinstance(data, str) else data,
        headers=headers or {},
        method=method,
    )
    resp = _request.urlopen(req)
    return Response(resp)
