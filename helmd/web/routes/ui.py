from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head><meta charset="utf-8"><title>helmd</title></head>
<body>
<h1>helmd dashboard</h1>
<ul>
  <li><a href="/status">/status</a></li>
  <li><a href="/profiles">/profiles</a></li>
</ul>
</body>
</html>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(content=_DASHBOARD_HTML)
