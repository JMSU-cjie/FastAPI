from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
from pathlib import Path
from baw.goods import app, init_db

STATIC_DIR = Path(__file__).parent / "static"

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/")
async def root():
    return RedirectResponse(url="/static/login.html")

if __name__ == "__main__":
    init_db()
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
