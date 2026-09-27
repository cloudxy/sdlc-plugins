#!/usr/bin/env python3
"""Grok (xAI) subscription authorization for this plugin — OAuth 2.0 device flow, no API key required.

  python3 scripts/grok/auth.py login [--no-browser]   # you do this once, in your own terminal
  python3 scripts/grok/auth.py status [--json]        # logged in / expired / not logged in — never prints a token
  python3 scripts/grok/auth.py whoami                 # the account behind the credentials (masked)
  python3 scripts/grok/auth.py logout                 # revoke at xAI, then delete the file
  python3 scripts/grok/auth.py --self-test            # offline, fake transport

The login binds this plugin to YOUR Grok subscription (SuperGrok / X Premium+): the browser step happens on
accounts.x.ai, and what lands on disk is a refreshable token, not a password. Endpoints come from OIDC discovery
at https://auth.x.ai/.well-known/openid-configuration and are rejected unless they are https on x.ai / *.x.ai.

Credentials: ${SDLC_GROK_CREDENTIALS:-~/.sdlc/grok/credentials.json}, file 0600 in a 0700 directory — outside this
repository and outside any project, so a credential can never be committed. This plugin never reads the host's own
credentials; authorization is what you granted it here, explicitly.

No subcommand prints an access or refresh token, and none is written into any artifact or evidence file. Callers
inside the plugin import this module and ask for `get_bearer()`, which keeps the token in the process.

Access tokens live ~15 minutes and xAI rotates the refresh token on every refresh, so a refresh takes an flock,
re-reads the file (a sibling hat may have just refreshed) and replaces it atomically.

Fallback: with XAI_API_KEY set, `get_bearer()` can return that key instead (auth_mode "api-key"). It is needed
because xAI gates the OAuth API surface by subscription tier and may answer 403 to an otherwise valid login.

Exit codes: 0 ok · 1 failure · 2 usage or environment · 3 not authorized (with the command to fix it).
"""
from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

ISSUER = "https://auth.x.ai"
DISCOVERY_URL = ISSUER + "/.well-known/openid-configuration"
CLIENT_ID = os.environ.get("SDLC_GROK_CLIENT_ID") or "b1a00492-073a-47ea-816f-4c329264a828"
SCOPE = "openid profile email offline_access grok-cli:access api:access"
DEVICE_GRANT = "urn:ietf:params:oauth:grant-type:device_code"
API_BASE = os.environ.get("SDLC_GROK_API_BASE") or "https://api.x.ai/v1"
ALLOWED_HOST_SUFFIX = ".x.ai"
ALLOWED_HOST = "x.ai"
USER_AGENT = "sdlc-workflow/grok-auth"
REFRESH_SKEW = 60          # refresh this many seconds before expiry
FILE_VERSION = 1

OK, FAIL, USAGE, UNAUTHORIZED = 0, 1, 2, 3

# Tests inject a callable here: TRANSPORT(method, url, body: dict|None, headers: dict) -> (status, dict).
TRANSPORT = None


class AuthError(Exception):
    """Something went wrong that the user has to act on; str() is the message to print."""

    def __init__(self, message: str, code: int = FAIL):
        super().__init__(message)
        self.code = code


def redact(value: object) -> str:
    """Tokens and device codes are never printed; their length is enough to debug with."""
    if value is None:
        return "<none>"
    return f"<redacted len={len(str(value))}>"


def mask(value: str) -> str:
    """Masked identity for humans: keep enough to recognize the account, not enough to reuse."""
    if not value:
        return "<none>"
    if "@" in value:
        name, _, domain = value.partition("@")
        head = name[:2] if len(name) > 2 else name[:1]
        return f"{head}***@{domain}"
    return value[:4] + "***" if len(value) > 6 else "***"


# ---------- paths ----------

def state_home() -> str:
    return os.environ.get("SDLC_GROK_HOME") or os.path.join(os.path.expanduser("~"), ".sdlc", "grok")


def credentials_path() -> str:
    explicit = os.environ.get("SDLC_GROK_CREDENTIALS")
    return explicit if explicit else os.path.join(state_home(), "credentials.json")


def probe_cache_path() -> str:
    return os.path.join(os.path.dirname(credentials_path()) or ".", "probe.json")


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, mode=0o700, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except OSError:
        pass


# ---------- http ----------

def _request(method: str, url: str, body: dict | None = None, headers: dict | None = None,
             form: bool = True, timeout: int = 30) -> tuple[int, dict]:
    """One place for every call, so tests can replace it and nothing else needs a network."""
    headers = dict(headers or {})
    headers.setdefault("User-Agent", USER_AGENT)
    headers.setdefault("Accept", "application/json")
    if TRANSPORT is not None:
        return TRANSPORT(method, url, body, headers)
    data = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = json.dumps(body).encode()
            headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    opener = urllib.request.build_opener()
    try:
        with opener.open(request, timeout=timeout) as response:
            raw = response.read()
            return response.status, (json.loads(raw) if raw else {})
    except urllib.error.HTTPError as error:               # OAuth errors arrive as 4xx with a JSON body
        raw = error.read()
        try:
            return error.code, json.loads(raw) if raw else {}
        except ValueError:
            return error.code, {"error": "http_error", "error_description": raw[:200].decode("utf-8", "replace")}
    except urllib.error.URLError as error:
        raise AuthError(f"无法连接 {urllib.parse.urlsplit(url).hostname}：{error.reason}", FAIL) from error


def _validate_endpoint(url: str, name: str) -> str:
    """Discovery is a document from the network: only https on x.ai / *.x.ai may become an endpoint we post to."""
    parts = urllib.parse.urlsplit(url or "")
    host = (parts.hostname or "").lower()
    if parts.scheme != "https" or not (host == ALLOWED_HOST or host.endswith(ALLOWED_HOST_SUFFIX)):
        raise AuthError(f"discovery 返回的 {name} 不可信：{url!r}（必须是 https 且属于 x.ai）", FAIL)
    return url


def discover() -> dict:
    status, doc = _request("GET", DISCOVERY_URL, None, {})
    if status != 200 or not isinstance(doc, dict):
        raise AuthError(f"OIDC discovery 失败（HTTP {status}）", FAIL)
    endpoints = {
        "device_authorization_endpoint": _validate_endpoint(doc.get("device_authorization_endpoint"), "device_authorization_endpoint"),
        "token_endpoint": _validate_endpoint(doc.get("token_endpoint"), "token_endpoint"),
    }
    for optional in ("revocation_endpoint", "userinfo_endpoint"):
        if doc.get(optional):
            endpoints[optional] = _validate_endpoint(doc[optional], optional)
    return endpoints


# ---------- credential file ----------

def load() -> dict | None:
    path = credentials_path()
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("access_token") else None


def save(creds: dict) -> str:
    """Write-then-rename so a crashed refresh can never leave a half-written credential behind."""
    path = credentials_path()
    _ensure_dir(path)
    handle, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".credentials-")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as out:
            json.dump(creds, out, ensure_ascii=False, indent=1, sort_keys=True)
            out.write("\n")
        os.chmod(tmp, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    return path


def forget() -> bool:
    try:
        os.unlink(credentials_path())
        return True
    except OSError:
        return False


class _Lock:
    """Advisory lock around a refresh: 19 role subagents can run at once, and the refresh token rotates."""

    def __init__(self, path: str):
        self.path = path + ".lock"
        self.handle = None

    def __enter__(self):
        try:
            import fcntl
        except ImportError:                                # non-POSIX: proceed without the lock
            return self
        _ensure_dir(self.path)
        self.handle = open(self.path, "a+")
        try:
            os.chmod(self.path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass
        fcntl.flock(self.handle.fileno(), fcntl.LOCK_EX)
        return self

    def __exit__(self, *_exc):
        if self.handle is not None:
            try:
                import fcntl
                fcntl.flock(self.handle.fileno(), fcntl.LOCK_UN)
            except (ImportError, OSError):
                pass
            self.handle.close()
            self.handle = None
        return False


# ---------- device flow ----------

def _token_error(payload: dict) -> str:
    error = str(payload.get("error") or "unknown_error")
    detail = payload.get("error_description") or payload.get("message")
    return f"{error}: {detail}" if detail else error


def _store_token_response(payload: dict, endpoints: dict, previous: dict | None = None) -> dict:
    now = int(time.time())
    expires_in = int(payload.get("expires_in") or 0)
    refresh = payload.get("refresh_token") or (previous or {}).get("refresh_token")
    creds = {
        "version": FILE_VERSION,
        "provider": "xai",
        "auth_mode": "oauth",
        "issuer": ISSUER,
        "client_id": CLIENT_ID,
        "scope": payload.get("scope") or SCOPE,
        "access_token": payload["access_token"],
        "refresh_token": refresh,
        "expires_at": now + expires_in if expires_in else now,
        "obtained_at": now,
        "token_endpoint": endpoints["token_endpoint"],
    }
    for optional in ("revocation_endpoint", "userinfo_endpoint"):
        if endpoints.get(optional):
            creds[optional] = endpoints[optional]
        elif (previous or {}).get(optional):
            creds[optional] = previous[optional]
    if (previous or {}).get("sub"):
        creds["sub"] = previous["sub"]
    if (previous or {}).get("account"):
        creds["account"] = previous["account"]
    return creds


def login(no_browser: bool = False, sleep=time.sleep, out=sys.stdout) -> dict:
    endpoints = discover()
    status, payload = _request("POST", endpoints["device_authorization_endpoint"],
                               {"client_id": CLIENT_ID, "scope": SCOPE})
    if status != 200 or "device_code" not in payload:
        raise AuthError(f"申请设备码失败（HTTP {status}）：{_token_error(payload)}", FAIL)

    device_code = payload["device_code"]
    user_code = payload.get("user_code", "")
    verification = payload.get("verification_uri_complete") or payload.get("verification_uri") or ""
    interval = max(1, int(payload.get("interval") or 5))
    deadline = time.time() + int(payload.get("expires_in") or 1800)

    print("在浏览器里完成授权（用你的 SuperGrok / X Premium+ 账号）：", file=out)
    print(f"  打开：{verification}", file=out)
    print(f"  验证码：{user_code}", file=out)
    print(f"  设备码：{redact(device_code)}（不显示，也不要转发给任何人）", file=out)
    if not no_browser:
        try:
            webbrowser.open(verification)
        except Exception:                                  # headless machine: the printed URL is the fallback
            pass
    print("等待授权…（Ctrl-C 取消）", file=out)

    while True:
        if time.time() >= deadline:
            raise AuthError("设备码已过期（30 分钟），重新跑 login", FAIL)
        sleep(interval)
        status, payload = _request("POST", endpoints["token_endpoint"],
                                   {"grant_type": DEVICE_GRANT, "device_code": device_code, "client_id": CLIENT_ID})
        error = payload.get("error")
        if status == 200 and payload.get("access_token"):
            creds = _store_token_response(payload, endpoints)
            path = save(creds)
            left = max(0, creds["expires_at"] - int(time.time()))
            print(f"已登录。凭据写到 {path}（0600），access token {left//60} 分钟后自动续。", file=out)
            if not creds.get("refresh_token"):
                print("注意：xAI 没有返回 refresh token，过期后需要重新 login。", file=out)
            return creds
        if error == "authorization_pending":
            continue
        if error == "slow_down":
            interval += 5
            continue
        if error == "access_denied":
            raise AuthError("你在浏览器里拒绝了这次授权", FAIL)
        if error == "expired_token":
            raise AuthError("设备码已过期，重新跑 login", FAIL)
        raise AuthError(f"授权失败（HTTP {status}）：{_token_error(payload)}", FAIL)


def refresh(creds: dict) -> dict:
    """Exchange the refresh token. xAI rotates it, so whatever comes back must be stored."""
    if not creds.get("refresh_token"):
        raise AuthError("凭据里没有 refresh token，重新跑 login", UNAUTHORIZED)
    endpoint = _validate_endpoint(creds.get("token_endpoint") or "", "token_endpoint")
    status, payload = _request("POST", endpoint, {
        "grant_type": "refresh_token",
        "refresh_token": creds["refresh_token"],
        "client_id": creds.get("client_id") or CLIENT_ID,
    })
    if status == 200 and payload.get("access_token"):
        endpoints = {"token_endpoint": endpoint}
        for optional in ("revocation_endpoint", "userinfo_endpoint"):
            if creds.get(optional):
                endpoints[optional] = creds[optional]
        updated = _store_token_response(payload, endpoints, previous=creds)
        save(updated)
        return updated
    if payload.get("error") == "invalid_grant":
        forget()
        raise AuthError("授权已失效（refresh token 被撤销或轮换过期），凭据已清理，重新跑 "
                        "`python3 scripts/grok/auth.py login`", UNAUTHORIZED)
    raise AuthError(f"刷新失败（HTTP {status}）：{_token_error(payload)}", FAIL)


def is_expired(creds: dict, skew: int = REFRESH_SKEW) -> bool:
    return int(creds.get("expires_at") or 0) - skew <= int(time.time())


def api_key() -> str | None:
    key = (os.environ.get("XAI_API_KEY") or "").strip()
    return key or None


def get_bearer(mode: str = "auto") -> tuple[str, str]:
    """Return (bearer, auth_mode) for api.x.ai. Refreshes under a lock when the access token is stale.

    mode: "auto" (OAuth if logged in, else XAI_API_KEY) · "oauth" · "api-key".
    """
    if mode not in ("auto", "oauth", "api-key"):
        raise AuthError(f"未知 auth 模式 {mode!r}（auto|oauth|api-key）", USAGE)
    if mode == "api-key":
        key = api_key()
        if not key:
            raise AuthError("imagery.auth 是 api-key，但环境变量 XAI_API_KEY 没设", UNAUTHORIZED)
        return key, "api-key"

    creds = load()
    if creds is None:
        if mode == "auto" and api_key():
            return api_key(), "api-key"
        raise AuthError("未授权：先跑 `/sdlc-grok login`（或 python3 scripts/grok/auth.py login）", UNAUTHORIZED)
    if is_expired(creds):
        with _Lock(credentials_path()):
            fresh = load() or creds                        # a sibling hat may have refreshed while we waited
            creds = fresh if not is_expired(fresh) else refresh(fresh)
    return creds["access_token"], "oauth"


def force_refresh() -> tuple[str, str]:
    """Reactive path: a 401 from the API means refresh once and retry once."""
    creds = load()
    if creds is None:
        raise AuthError("未授权：先跑 `/sdlc-grok login`", UNAUTHORIZED)
    with _Lock(credentials_path()):
        creds = refresh(load() or creds)
    return creds["access_token"], "oauth"


# ---------- commands ----------

def status_report() -> dict:
    creds = load()
    report: dict = {"credentials_path": credentials_path(), "api_key_env": bool(api_key())}
    if creds is None:
        report.update(state="logged_out", auth_mode="api-key" if api_key() else "none")
        return report
    expires_at = int(creds.get("expires_at") or 0)
    report.update(
        state="expired" if is_expired(creds, 0) else "logged_in",
        auth_mode="oauth",
        scope=creds.get("scope", ""),
        expires_at=expires_at,
        expires_in=max(0, expires_at - int(time.time())),
        refreshable=bool(creds.get("refresh_token")),
        account=mask(creds.get("account") or creds.get("sub") or ""),
    )
    try:                                                   # a credential the group can read is a finding
        mode = stat.S_IMODE(os.stat(credentials_path()).st_mode)
        report["file_mode"] = oct(mode)
        report["file_mode_ok"] = mode == 0o600
    except OSError:
        pass
    return report


def cmd_status(args) -> int:
    report = status_report()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return OK if report["state"] == "logged_in" else UNAUTHORIZED
    if report["state"] == "logged_out":
        if report["api_key_env"]:
            print("未登录订阅授权，但环境变量 XAI_API_KEY 已设 → 可用 api-key 模式出图。")
        else:
            print("未授权。跑 `/sdlc-grok login`（或 python3 scripts/grok/auth.py login）。")
        return UNAUTHORIZED
    minutes = report["expires_in"] // 60
    label = "已登录" if report["state"] == "logged_in" else "access token 已过期（下次调用自动刷新）"
    print(f"{label}｜账号 {report['account']}｜{minutes} 分钟后到期"
          f"｜{'可自动续' if report['refreshable'] else '无 refresh token，过期需重新 login'}")
    print(f"凭据：{report['credentials_path']}（{report.get('file_mode', '?')}）")
    if report.get("file_mode_ok") is False:
        print("警告：凭据文件权限不是 0600，建议 chmod 600。")
    return OK if report["state"] == "logged_in" else OK


def cmd_login(args) -> int:
    login(no_browser=args.no_browser)
    return OK


def cmd_logout(_args) -> int:
    creds = load()
    if creds is None:
        print("本来就没有订阅授权凭据。")
        return OK
    endpoint = creds.get("revocation_endpoint")
    if endpoint:
        for kind in ("refresh_token", "access_token"):
            token = creds.get(kind)
            if not token:
                continue
            try:
                _request("POST", _validate_endpoint(endpoint, "revocation_endpoint"),
                         {"token": token, "token_type_hint": kind, "client_id": creds.get("client_id") or CLIENT_ID})
            except AuthError as error:                     # offline logout still has to delete the file
                print(f"撤销 {kind} 未成功（{error}），继续删除本地凭据。")
    print("已登出，凭据已删除。" if forget() else "凭据文件删除失败，请手动删除。")
    return OK


def cmd_whoami(_args) -> int:
    creds = load()
    if creds is None:
        print("未授权。跑 `/sdlc-grok login`。")
        return UNAUTHORIZED
    endpoint = creds.get("userinfo_endpoint")
    if not endpoint:
        print(f"凭据里没有 userinfo 端点；账号 {mask(creds.get('account') or creds.get('sub') or '')}")
        return OK
    bearer, _mode = get_bearer("oauth")
    status, payload = _request("GET", _validate_endpoint(endpoint, "userinfo_endpoint"), None,
                               {"Authorization": f"Bearer {bearer}"})
    if status != 200:
        print(f"userinfo 失败（HTTP {status}）：{_token_error(payload)}")
        return FAIL
    account = payload.get("email") or payload.get("name") or payload.get("sub") or ""
    creds["sub"] = payload.get("sub", creds.get("sub", ""))
    creds["account"] = account
    save(creds)
    print(f"账号：{mask(account)}｜sub：{mask(str(payload.get('sub', '')))}")
    return OK


# ---------- self-test（离线） ----------

def _self_test() -> int:
    import contextlib
    import io
    import tempfile as tf
    import unittest

    global TRANSPORT
    discovery_doc = {
        "device_authorization_endpoint": "https://auth.x.ai/oauth2/device/code",
        "token_endpoint": "https://auth.x.ai/oauth2/token",
        "revocation_endpoint": "https://auth.x.ai/oauth2/revoke",
        "userinfo_endpoint": "https://auth.x.ai/oauth2/userinfo",
    }

    class FakeXAI:
        """Replays the real device flow: pending, slow_down, then a token; refresh rotates."""

        def __init__(self, script):
            self.script = list(script)
            self.calls = []

        def __call__(self, method, url, body, headers):
            self.calls.append((method, url, dict(body or {})))
            if url == DISCOVERY_URL:
                return 200, dict(discovery_doc)
            if url.endswith("/device/code"):
                return 200, {"device_code": "dev-secret", "user_code": "9M8Y-462S",
                             "verification_uri": "https://accounts.x.ai/oauth2/device",
                             "verification_uri_complete": "https://accounts.x.ai/oauth2/device?user_code=9M8Y-462S",
                             "expires_in": 1800, "interval": 5}
            if url.endswith("/oauth2/token"):
                return self.script.pop(0)
            return 200, {}

    class Tests(unittest.TestCase):
        def setUp(self):
            self.home = tf.TemporaryDirectory()
            self.addCleanup(self.home.cleanup)
            os.environ["SDLC_GROK_CREDENTIALS"] = os.path.join(self.home.name, "grok", "credentials.json")
            self.addCleanup(os.environ.pop, "SDLC_GROK_CREDENTIALS", None)
            os.environ.pop("XAI_API_KEY", None)

        def tearDown(self):
            global TRANSPORT
            TRANSPORT = None

        def test_device_flow_handles_pending_and_slow_down(self):
            global TRANSPORT
            fake = FakeXAI([
                (400, {"error": "authorization_pending"}),
                (400, {"error": "slow_down"}),
                (200, {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 900, "scope": SCOPE}),
            ])
            TRANSPORT = fake
            waits = []
            creds = login(no_browser=True, sleep=waits.append, out=io.StringIO())
            self.assertEqual(creds["access_token"], "at-1")
            self.assertEqual(waits, [5, 5, 10], "slow_down must widen the polling interval")
            self.assertEqual(stat.S_IMODE(os.stat(credentials_path()).st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(os.stat(os.path.dirname(credentials_path())).st_mode), 0o700)

        def test_login_prints_no_secret(self):
            global TRANSPORT
            TRANSPORT = FakeXAI([(200, {"access_token": "at-secret", "refresh_token": "rt-secret", "expires_in": 900})])
            buffer = io.StringIO()
            login(no_browser=True, sleep=lambda _s: None, out=buffer)
            printed = buffer.getvalue()
            self.assertNotIn("at-secret", printed)
            self.assertNotIn("rt-secret", printed)
            self.assertNotIn("dev-secret", printed)

        def test_refresh_stores_rotated_refresh_token(self):
            global TRANSPORT
            TRANSPORT = FakeXAI([(200, {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 900})])
            login(no_browser=True, sleep=lambda _s: None, out=io.StringIO())
            stale = load()
            stale["expires_at"] = int(time.time()) - 10
            save(stale)
            TRANSPORT = FakeXAI([(200, {"access_token": "at-2", "refresh_token": "rt-2", "expires_in": 900})])
            bearer, mode = get_bearer("auto")
            self.assertEqual((bearer, mode), ("at-2", "oauth"))
            self.assertEqual(load()["refresh_token"], "rt-2", "a rotated refresh token must be stored")

        def test_refresh_keeps_old_token_when_none_returned(self):
            global TRANSPORT
            TRANSPORT = FakeXAI([(200, {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 0})])
            login(no_browser=True, sleep=lambda _s: None, out=io.StringIO())
            TRANSPORT = FakeXAI([(200, {"access_token": "at-2", "expires_in": 900})])
            get_bearer("auto")
            self.assertEqual(load()["refresh_token"], "rt-1")

        def test_invalid_grant_clears_credentials(self):
            global TRANSPORT
            TRANSPORT = FakeXAI([(200, {"access_token": "at-1", "refresh_token": "rt-1", "expires_in": 0})])
            login(no_browser=True, sleep=lambda _s: None, out=io.StringIO())
            TRANSPORT = FakeXAI([(400, {"error": "invalid_grant"})])
            with self.assertRaises(AuthError) as caught:
                get_bearer("auto")
            self.assertEqual(caught.exception.code, UNAUTHORIZED)
            self.assertIsNone(load(), "a dead credential must not stay on disk")

        def test_untrusted_discovery_endpoint_is_refused(self):
            global TRANSPORT

            def evil(method, url, body, headers):
                if url == DISCOVERY_URL:
                    return 200, {"device_authorization_endpoint": "https://evil.example/device",
                                 "token_endpoint": "https://auth.x.ai/oauth2/token"}
                return 200, {}

            TRANSPORT = evil
            with self.assertRaises(AuthError):
                login(no_browser=True, sleep=lambda _s: None, out=io.StringIO())

        def test_api_key_fallback_and_modes(self):
            os.environ["XAI_API_KEY"] = "xai-key"
            self.addCleanup(os.environ.pop, "XAI_API_KEY", None)
            self.assertEqual(get_bearer("auto"), ("xai-key", "api-key"))
            self.assertEqual(get_bearer("api-key"), ("xai-key", "api-key"))
            with self.assertRaises(AuthError) as caught:
                get_bearer("oauth")
            self.assertEqual(caught.exception.code, UNAUTHORIZED)

        def test_status_without_credentials_is_unauthorized(self):
            report = status_report()
            self.assertEqual(report["state"], "logged_out")
            self.assertNotIn("access_token", json.dumps(report))

        def test_redaction_never_leaks(self):
            self.assertNotIn("secret", redact("secret-token"))
            self.assertEqual(mask("someone@example.com"), "so***@example.com")

    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(
        unittest.TestLoader().loadTestsFromTestCase(Tests))
    sys.stdout.write(stream.getvalue())
    with contextlib.suppress(Exception):
        TRANSPORT = None
    print("auth self-test: ok" if result.wasSuccessful() else "auth self-test: FAILED")
    return OK if result.wasSuccessful() else FAIL


def main() -> int:
    parser = argparse.ArgumentParser(description="Grok 订阅授权（device flow）", add_help=True)
    parser.add_argument("--self-test", action="store_true", help="离线自检，不联网")
    sub = parser.add_subparsers(dest="command")
    login_parser = sub.add_parser("login", help="用 Grok 订阅账号授权本插件")
    login_parser.add_argument("--no-browser", action="store_true", help="只打印链接，不自动开浏览器")
    login_parser.set_defaults(func=cmd_login)
    status_parser = sub.add_parser("status", help="授权状态（不打印 token）")
    status_parser.add_argument("--json", action="store_true")
    status_parser.set_defaults(func=cmd_status)
    sub.add_parser("logout", help="撤销并删除本地凭据").set_defaults(func=cmd_logout)
    sub.add_parser("whoami", help="凭据对应的账号（脱敏）").set_defaults(func=cmd_whoami)
    args = parser.parse_args()
    if args.self_test:
        return _self_test()
    if not getattr(args, "func", None):
        parser.print_help()
        return USAGE
    try:
        return args.func(args)
    except AuthError as error:
        print(str(error), file=sys.stderr)
        return error.code
    except KeyboardInterrupt:
        print("已取消。", file=sys.stderr)
        return USAGE


if __name__ == "__main__":
    sys.exit(main())
