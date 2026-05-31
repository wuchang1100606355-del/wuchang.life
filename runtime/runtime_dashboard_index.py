from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def dashboard():

    return """
    <html>
    <body style="background:#0b1020;color:white;font-family:Arial;padding:30px">

    <h1>Taiji Cognitive Runtime</h1>

    <p><a href="http://127.0.0.1:8081">Gateway :8081</a></p>

    <p><a href="http://127.0.0.1:8091/runtime/health">Runtime API :8091</a></p>

    <p><a href="http://127.0.0.1:8095/runtime/status">Status API :8095</a></p>

    <p><a href="http://127.0.0.1:9101/metrics">Metrics API :9101</a></p>

    <p><a href="http://127.0.0.1:9111/events">Event Stream :9111</a></p>

    </body>
    </html>
    """
