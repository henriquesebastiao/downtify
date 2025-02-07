from functools import lru_cache

from fastapi import Depends, FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from spotdl import Spotdl
from spotdl.types.options import DownloaderOptions
from starlette.requests import Request

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/assets", StaticFiles(directory="assets"), name="assets")
templates = Jinja2Templates(directory='templates')
DOWNLOADER_OPTIONS: DownloaderOptions = {
    'output': './downloads/{artists} - {title}.{output-ext}',
}


@lru_cache(maxsize=1)
def get_spotdl():
    return Spotdl(
        client_id='5f573c9620494bae87890c0f08a60293',
        client_secret='212476d9b0f3472eaa762d90b19b0ba8',
        downloader_settings=DOWNLOADER_OPTIONS,
    )


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/download/')
async def download(
    spotdlc: Spotdl = Depends(get_spotdl), url: str = Form(...)
):
    songs = spotdlc.search([url])
    results = spotdlc.download_songs(songs)

    if results:
        return {'message': 'Download concluído'}
    return {'error': 'Erro ao baixar música'}
