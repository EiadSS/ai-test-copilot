import json
from pathlib import Path

from app.services.playwright_api_gen import generate_playwright_api_tests_zip

plan = json.loads(Path("demo/test_plan.json").read_text(encoding="utf-8"))
zip_bytes = generate_playwright_api_tests_zip(plan, project_name="demo-project")

Path("pw.zip").write_bytes(zip_bytes)
print("wrote pw.zip", len(zip_bytes))