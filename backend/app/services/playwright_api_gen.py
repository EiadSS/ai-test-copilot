from __future__ import annotations

import io
import json
import re
import zipfile
from datetime import datetime
from typing import Any


def _safe_slug(s: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9-_ ]+", "", s).strip().lower()
    s = re.sub(r"\s+", "-", s)
    return s or "project"


def _pick_tests(plan: dict) -> list[dict]:
    tests = plan.get("tests") or []
    out = []
    for t in tests:
        ttype = (t.get("type") or "").lower()
        if ttype == "api":
            out.append(t)
    # If model didn’t label types well, fall back to any tests mentioning endpoints
    if not out:
        for t in tests:
            blob = " ".join((t.get("steps") or []) + (t.get("title") or "").split())
            if re.search(r"\b(GET|POST|PATCH|PUT|DELETE)\s+\/", blob):
                out.append(t)
    return out


def _infer_endpoint(test: dict) -> tuple[str, str] | None:
    # Try to find "METHOD /path" from steps/title
    text = " ".join([test.get("title", "")] + (test.get("steps") or []))
    m = re.search(r"\b(GET|POST|PATCH|PUT|DELETE)\s+(\/[A-Za-z0-9\/\-_{}]+)", text)
    if m:
        return m.group(1), m.group(2)
    # Heuristic by keywords
    title = (test.get("title") or "").lower()
    if "register" in title or "sign up" in title:
        return "POST", "/auth/register"
    if "login" in title or "log in" in title:
        return "POST", "/auth/login"
    if "profile" in title or "me" in title:
        return "GET", "/me"
    if "update" in title and ("profile" in title or "me" in title):
        return "PATCH", "/me"
    if "logout" in title or "log out" in title:
        return "POST", "/auth/logout"
    return None


def _infer_payload(method: str, path: str, test: dict) -> dict | None:
    title = (test.get("title") or "").lower()
    # basic realistic defaults
    if method == "POST" and path == "/auth/register":
        pw = "Password123!"
        if "short" in title or "8" in title:
            pw = "short"
        email = "user@example.com"
        if "invalid email" in title or "invalid" in title and "email" in title:
            email = "not-an-email"
        return {"email": email, "password": pw}
    if method == "POST" and path == "/auth/login":
        pw = "Password123!"
        if "short" in title or "8" in title:
            pw = "short"
        email = "user@example.com"
        if "invalid email" in title or ("invalid" in title and "email" in title):
            email = "not-an-email"
        return {"email": email, "password": pw}
    if method == "PATCH" and path == "/me":
        return {"name": "Eiad", "bio": "Hello", "avatarUrl": "https://example.com/a.png"}
    return None


def generate_playwright_api_tests_zip(plan: dict, project_name: str = "AI Test Copilot") -> bytes:
    slug = _safe_slug(project_name)
    api_tests = _pick_tests(plan)

    # --- Files we will generate ---
    package_json = {
        "name": f"{slug}-playwright-api-tests",
        "private": True,
        "version": "0.1.0",
        "scripts": {
            "test": "playwright test",
            "test:headed": "playwright test --headed",
        },
        "devDependencies": {
            "@playwright/test": "^1.50.0"
        }
    }

    playwright_config = """\
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  retries: 1,
  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
  },
});
"""

    readme = f"""\
    # Playwright API Tests (generated)

    This folder was generated from a test plan.

    ## Setup
    ```bash
    npm install
    npx playwright install
    ```
"""

    # Generate one spec file with multiple tests (simple MVP)
    lines: list[str] = []
    lines.append("import { test, expect } from '@playwright/test';")
    lines.append("")
    lines.append("function authHeaders() {")
    lines.append("  const t = process.env.AUTH_TOKEN;")
    lines.append("  return t ? { Authorization: `Bearer ${t}` } : {};")
    lines.append("}")
    lines.append("")

    if not api_tests:
        lines.append("test('No API tests found in plan', async () => {")
        lines.append("  expect(true).toBeTruthy();")
        lines.append("});")
    else:
        for t in api_tests:
            tid = (t.get("id") or "T000").strip()
            title = (t.get("title") or "Untitled").strip().replace("'", "\\'")
            method_path = _infer_endpoint(t)
            method, path = method_path if method_path else ("GET", "/")
            payload = _infer_payload(method, path, t)
            expected = t.get("expected") or []
            steps = t.get("steps") or []

            lines.append(f"test('{tid} - {title}', async ({{ request }}) => {{")
            lines.append("  const headers = { ...authHeaders() };")
            if method in ("POST", "PUT", "PATCH") and payload is not None:
                lines.append(
                    f"  const resp = await request.{method.lower()}('{path}', {{ headers, data: {json.dumps(payload)} }});"
                )
            else:
                lines.append(f"  const resp = await request.{method.lower()}('{path}', {{ headers }});")

            blob = " ".join([title.lower()] + [str(x).lower() for x in expected] + [str(x).lower() for x in steps])
            if "401" in blob or "unauthor" in blob or "invalid token" in blob:
                lines.append("  expect(resp.status()).toBe(401);")
            elif "rate limit" in blob or "429" in blob:
                lines.append("  expect([200, 201, 204, 429]).toContain(resp.status());")
            else:
                lines.append("  expect(resp.ok()).toBeTruthy();")

            lines.append("});")
            lines.append("")

    spec_ts = "\\n".join(lines)

    # --- Zip it ---
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        root = f"{slug}-playwright-api-tests"
        z.writestr(f"{root}/package.json", json.dumps(package_json, indent=2))
        z.writestr(f"{root}/playwright.config.ts", playwright_config)
        z.writestr(f"{root}/README.md", readme)
        z.writestr(f"{root}/tests/api.spec.ts", spec_ts)
        z.writestr(f"{root}/generated_at.txt", datetime.utcnow().isoformat() + "Z")

    return buf.getvalue()