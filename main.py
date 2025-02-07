import os
from functools import lru_cache

from fastapi import Depends, FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from spotdl import Spotdl
from spotdl.types.options import DownloaderOptions
from starlette.requests import Request

app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/assets', StaticFiles(directory='assets'), name='assets')
templates = Jinja2Templates(directory='templates')
DOWNLOADER_OPTIONS: DownloaderOptions = {
    'output': os.getenv(
        'OUTPUT_PATH', default='/downloads/{artists} - {title}.{output-ext}'
    ),
}


@lru_cache(maxsize=1)
def get_spotdl():
    return Spotdl(
        client_id='5f573c9620494bae87890c0f08a60293',
        client_secret='212476d9b0f3472eaa762d90b19b0ba8',
        downloader_settings=DOWNLOADER_OPTIONS,
    )


@app.get('/', response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/download/', response_class=HTMLResponse)
def download(spotdlc: Spotdl = Depends(get_spotdl), url: str = Form(...)):
    songs = spotdlc.search([url])
    spotdlc.download_songs(songs)

    return """
    <button type="submit" class="btn btn-lg btn-light fw-bold border-white button"><i class="fa-solid fa-down-long"></i></button>
    <div class="alert alert-success mx-auto">
        <strong>Download completed!</strong>
    </div>
    """
