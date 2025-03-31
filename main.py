import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field
from spotdl import Spotdl
from spotdl.types.options import DownloaderOptions
from starlette.requests import Request

load_dotenv()

DESCRIPTION = """
Download Spotify music with album art and metadata.

With Downtify you can download Spotify musics containing album art, track names, album title and other metadata about the songs.
"""


class Message(BaseModel):
    message: str = Field(examples=['Download sucessful'])


app = FastAPI(
    title='Downtify',
    version='0.3.2',
    description=DESCRIPTION,
    contact={
        'name': 'Downtify',
        'url': 'https://github.com/henriquesebastiao/downtify',
        'email': 'contato@henriquesebastiao.com',
    },
    terms_of_service='https://github.com/henriquesebastiao/downtify/',
)


app.mount('/static', StaticFiles(directory='static'), name='static')
app.mount('/assets', StaticFiles(directory='assets'), name='assets')

if not os.path.exists('/downloads'):
    os.makedirs('/downloads')

app.mount('/downloads', StaticFiles(directory='/downloads'), name='downloads')
templates = Jinja2Templates(directory='templates')

DOWNLOADER_OPTIONS: DownloaderOptions = {
    'output': os.getenv(
        'OUTPUT_PATH', default='/downloads/{artists} - {title}.{output-ext}'
    ),
    'ffmpeg': '/downtify/ffmpeg',
}


@lru_cache(maxsize=1)
def get_spotdl():
    return Spotdl(
        client_id=os.getenv(
            'CLIENT_ID', default='5f573c9620494bae87890c0f08a60293'
        ),
        client_secret=os.getenv(
            'CLIENT_SECRET', default='212476d9b0f3472eaa762d90b19b0ba8'
        ),
        downloader_settings=DOWNLOADER_OPTIONS,
    )


def get_downloaded_files() -> str:
    download_path = '/downloads'
    try:
        files = os.listdir(download_path)
        file_links = [
            f'<li class="list-group-item"><a href="/downloads/{file}">{file}</a></li>'
            for file in files
        ]
        files = (
            ''.join(file_links)
            if file_links
            else '<li class="list-group-item">No files found.</li>'
        )
    except Exception as e:
        files = f'<li class="list-group-item text-danger">Error: {str(e)}</li>'

    return files


@app.get(
    '/',
    response_class=HTMLResponse,
    tags=['Web UI'],
    summary='Application web interface',
)
def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post(
    '/download-web/',
    response_class=HTMLResponse,
    tags=['Downloader'],
    summary='Download one or more songs from a playlist via the WEB interface',
)
def download_web_ui(
    spotdlc: Spotdl = Depends(get_spotdl),
    url: str = Form(...),
):
    """
    You can download a single song or all the songs in a playlist, album, etc.

    - **url**: URL of the song or playlist to download.

    ### Responses

    - `200` - Download successful.
    """
    try:
        songs = spotdlc.search([url])
        spotdlc.download_songs(songs)
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


@app.post(
    '/download/',
    response_class=JSONResponse,
    response_model=Message,
    tags=['Downloader'],
    summary='Download a song or songs from a playlist',
)
def download(
    url: str,
    spotdlc: Spotdl = Depends(get_spotdl),
):
    """
    You can download a single song or all the songs in a playlist, album, etc.

    - **url**: URL of the song or playlist to download.

    ### Responses

    - `200` - Download successful.
    """
    try:
        songs = spotdlc.search([url])
        spotdlc.download_songs(songs)
        return {'message': 'Download sucessful'}
    except Exception as error:  # pragma: no cover
        return {'detail': error}


@app.get(
    '/list',
    response_class=HTMLResponse,
    tags=['Web UI'],
    summary='List downloaded files',
)
def list_downloads_page(request: Request):
    files = get_downloaded_files()
    return templates.TemplateResponse(
        'list.html', {'request': request, 'files': files}
    )


@app.get(
    '/list-items',
    response_class=HTMLResponse,
    tags=['Web UI'],
    summary='Returns downloaded files to list',
)
def list_items_of_downloads_page():
    files = get_downloaded_files()
    return files
