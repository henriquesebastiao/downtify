import os
import subprocess

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/assets', StaticFiles(directory='assets'), name='assets')
templates = Jinja2Templates(directory='templates')


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/download/', response_class=HTMLResponse)
def download(url: str = Form(...)):
    command = [
        'spotdl',
        url,
        '--output',
        os.getenv(
            'OUTPUT_PATH',
            default='/downloads/{artists} - {title}.{output-ext}',
        ),
    ]
    try:
        subprocess.run(command, capture_output=True, text=True, check=False)
    except Exception as error:
        return f"""
    <div>
        <button type="submit" class="btn btn-lg btn-light fw-bold border-white button mx-auto" id="button-download" style="display: block;"><i class="fa-solid fa-down-long"></i></button>
        <div class="alert alert-danger mx-auto" id="success-card" style="display: none;">
            <strong>Error: {error}</strong>
        </div>
    </div>
    """

    return """
    <div>
        <button type="submit" class="btn btn-lg btn-light fw-bold border-white button mx-auto" id="button-download" style="display: block;"><i class="fa-solid fa-down-long"></i></button>
        <div class="alert alert-success mx-auto success-card" id="success-card" style="display: none;">
            <strong>Download completed!</strong>
        </div>
    </div>
    """
