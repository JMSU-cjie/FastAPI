from fastapi.staticfiles import StaticFiles
from starlette.responses import RedirectResponse
import os

from baw.goods import app, init_db

init_db()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

@app.get("/")
def root():
    return RedirectResponse(url="/static/login.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
