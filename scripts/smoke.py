"""Check readiness, catalog access and a stored staging observation over HTTP."""
import argparse
import base64
from http.cookiejar import CookieJar
import json
import os
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, HTTPRedirectHandler, Request, build_opener


def require(value, message):
    if not value:
        raise RuntimeError(message)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check(base_url, commit, record, authorization):
    session = build_opener(NoRedirect(), HTTPCookieProcessor(CookieJar()))

    def fetch(path, form=None, client=session):
        body = None if form is None else urlencode(form).encode()
        request = Request(base_url + path, data=body)
        if authorization:
            request.add_unredirected_header("Authorization", authorization)
        return client.open(request, timeout=10)

    for attempt in range(30):
        try:
            with fetch("/health") as response:
                health = json.load(response)
            if health["status"] == "ok" and health["database"] == "reachable" and health["commit"] == commit:
                break
        except (URLError, ValueError):
            pass
        if attempt == 29:
            raise RuntimeError("Health did not report the expected commit and reachable database.")
        time.sleep(4)
    print("PASS health and deployed SHA")

    with fetch("/") as response:
        require(b"Central Library" in response.read(), "Campus catalog is missing.")
    print("PASS catalog entry point")
    if not record:
        return

    route = "/spaces/999"
    with fetch(route) as response:
        page = response.read().decode()
    require("Staging smoke test" in page, "Staging fixture is missing; refusing to write.")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', page)
    require(csrf, "Report form did not expose a CSRF token.")
    with fetch(route + "/live") as response:
        previous = response.read()
    form = {"csrf_token": csrf.group(1), "crowd": "medium", "noise": "moderate"}
    for attempt in range(2):
        try:
            with fetch(route + "/reports", form):
                raise RuntimeError("A successful report must redirect back to its detail page.")
        except HTTPError as error:
            if error.code == 303 and error.headers.get("Location") == route + "#latest":
                error.close()
                break
            if error.code != 429 or attempt:
                raise
            delay = min(61, max(1, int(error.headers.get("Retry-After", "60"))))
            error.close()
            time.sleep(delay)
    fresh_session = build_opener(NoRedirect())
    with fetch(route + "/live", client=fresh_session) as response:
        current = response.read()
    require(current != previous and b"Somewhat busy" in current and b"Some conversation" in current,
            "A second client could not read the newly stored report.")
    print("PASS report stored and visible from a second client")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url")
    parser.add_argument("commit")
    parser.add_argument("--record", action="store_true", help="write only to the staging test fixture")
    parser.add_argument("--authenticated", action="store_true", help="require staging HTTP credentials")
    args = parser.parse_args()
    auth = None
    if args.authenticated:
        auth = "Basic " + base64.b64encode(
            f'{os.environ["SMOKE_USER"]}:{os.environ["SMOKE_PASSWORD"]}'.encode()
        ).decode()
        require(args.url.startswith("https://"), "Staging credentials require an HTTPS URL.")
    check(args.url.rstrip("/"), args.commit, args.record, auth)
