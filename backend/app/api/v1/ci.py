from __future__ import annotations

import os
import httpx
from fastapi import APIRouter, HTTPException

router = APIRouter()

@router.post("/projects/{project_id}/ci/run")
def run_ci(project_id: str):
    token = os.getenv("GH_WORKFLOW_TOKEN")
    owner = os.getenv("GH_REPO_OWNER")
    repo = os.getenv("GH_REPO_NAME")
    workflow = os.getenv("GH_WORKFLOW_FILE", "playwright-api-tests.yml")
    ref = os.getenv("GH_WORKFLOW_REF", "main")

    if not token or not owner or not repo:
        raise HTTPException(status_code=500, detail="Missing GH_* env vars (token/owner/repo)")

    url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow}/dispatches"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    payload = {"ref": ref}

    r = httpx.post(url, headers=headers, json=payload, timeout=20.0)
    if r.status_code not in (204, 201):
        raise HTTPException(status_code=500, detail=f"GitHub dispatch failed: {r.status_code} {r.text}")

    return {"ok": True, "dispatched": True, "workflow": workflow, "ref": ref}