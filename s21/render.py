"""Bakes the story into the single-file HTML page."""

import html
import json
from pathlib import Path

TEMPLATE = Path(__file__).with_name("template.html")


def render(story, out_path):
    page = TEMPLATE.read_text(encoding="utf-8")
    page = page.replace("__LOGIN__", html.escape(story["login"]))
    # "</" would let a project title close the <script> tag early.
    data = json.dumps(story, ensure_ascii=False).replace("</", "<\\/")
    page = page.replace("/*__STORY__*/", data)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(page, encoding="utf-8")
    return out_path
