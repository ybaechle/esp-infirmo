"""Exercise the synthetic v0.1 through its public API; never print credentials."""

import argparse
import json
import os
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen


def check(base_url):
    def request(path, method="GET", body=None, token=None, expected=200):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = "Bearer " + token
        req = Request(
            base_url.rstrip("/") + path,
            data=json.dumps(body).encode() if body is not None else None,
            headers=headers,
            method=method,
        )
        try:
            response = urlopen(req, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            if response.status != expected:
                raise RuntimeError(
                    f"{method} {path}: expected {expected}, got {response.status}"
                )
            data = response.read()
            return json.loads(data) if data else None

    login = {
        "email": os.getenv("INFIRMO_DEMO_EMAIL", "demo@infirmo.example"),
        "password": os.getenv("INFIRMO_DEMO_PASSWORD", "Infirmo-demo-2026!"),
    }
    if not login["email"].rsplit("@", 1)[-1].lower().endswith(".example"):
        raise ValueError("Acceptance requires a reserved .example demo identity")
    request("/api/profile", expected=401)
    first = request("/api/auth/login", "POST", login)["access_token"]
    second = None
    original = None
    first_revoked = False
    try:
        profile = request("/api/profile", token=first)
        original = {key: profile[key] for key in ("display_name", "role", "city")}
        changed = dict(
            original,
            display_name="Demo validation T9",
            city="Metz" if original["city"] == "Nancy" else "Nancy",
        )
        request("/api/profile", "PUT", changed, first)
        second = request("/api/auth/login", "POST", login)["access_token"]
        saved = request("/api/profile", token=second)
        if any(saved[key] != value for key, value in changed.items()):
            raise RuntimeError("Profile update did not persist across sessions")
        request("/api/auth/logout", "POST", token=first, expected=204)
        first_revoked = True
        request("/api/profile", token=first, expected=401)
    finally:
        failed = sys.exc_info()[0] is not None
        cleanup_errors = []
        if original is not None:
            try:
                request("/api/profile", "PUT", original, second or first)
            except Exception as error:
                cleanup_errors.append(error)
        for token in (second, None if first_revoked else first):
            if token:
                try:
                    request("/api/auth/logout", "POST", token=token, expected=204)
                except Exception as error:
                    cleanup_errors.append(error)
        if cleanup_errors and not failed:
            raise RuntimeError("Acceptance cleanup failed") from cleanup_errors[0]
    print(
        "PASS: unauthorized access, login, profile update, persistence, logout revocation"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:8080")
    check(parser.parse_args().url)
