import subprocess

from fastapi import FastAPI, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

app = FastAPI()
templates = Jinja2Templates(directory='templates')


def run_spotdl(url: str):
    command = [
        'spotdl',
        url,
        '--output',
        './downloads/{artists} - {title}.{output-ext}',
    ]
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode == 0:
        return {'message': 'Download concluído'}
    return {'error': result.stderr}


@app.get('/', response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})


@app.post('/download/')
async def download(url: str = Form(...)):
    run_spotdl(url)
    return {'message': 'Download concluído'}
