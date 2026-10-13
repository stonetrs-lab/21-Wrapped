"""Minimal School 21 Open API client, stdlib only."""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

AUTH_URL = ("https://auth.21-school.ru/auth/realms/EduPowerKeycloak"
            "/protocol/openid-connect/token")
API_URL = "https://platform.21-school.ru/services/21-school/api/v1"


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(f"HTTP {status}: {message}")
        self.status = status


def get_token(login, password):
    """Exchanges school credentials for a token payload
    (access_token, expires_in, ...)."""
    body = urllib.parse.urlencode({
        "username": login,
        "password": password,
        "grant_type": "password",
        "client_id": "s21-open-api",
    }).encode()
    request = urllib.request.Request(
        AUTH_URL, data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        raise ApiError(err.code, "login failed, check login/password") from err


class Client:
    """GET-only client. On 429 it waits and also slows down every later
    request, so it settles near the API's real rate limit."""

    def __init__(self, token, delay=0.25, retries=5):
        self.token = token
        self.delay = delay
        self.retries = retries

    def get(self, path, **params):
        query = {k: v for k, v in params.items() if v is not None}
        url = API_URL + path
        if query:
            url += "?" + urllib.parse.urlencode(query)
        request = urllib.request.Request(url, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        })
        for attempt in range(self.retries):
            time.sleep(self.delay)
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.load(response)
            except urllib.error.HTTPError as err:
                if err.code != 429 or attempt == self.retries - 1:
                    raise ApiError(err.code, err.reason) from err
                self.delay = min(max(self.delay * 2, 1.0), 5.0)
                wait = 2 ** attempt
                print(f"\n  rate limited, waiting {wait}s "
                      f"(now {self.delay:.0f}s between calls)", file=sys.stderr)
                time.sleep(wait)
        raise ApiError(429, "rate limited")

    def get_all(self, path, key, page=1000, **params):
        """Follows limit/offset pagination and returns the joined list."""
        items = []
        offset = 0
        while True:
            chunk = self.get(path, limit=page, offset=offset, **params)[key]
            items.extend(chunk)
            offset += page
            if len(chunk) < page:
                break
        return items
