import os

import pytest
from fastapi.testclient import TestClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from main import app


@pytest.fixture(scope='session', autouse=True)
def create_downloads_folder():
    os.makedirs('./downloads', exist_ok=True)


@pytest.fixture(scope='session', autouse=True)
def app_container():
    with (
        DockerContainer('downtify-test:latest')
        .with_exposed_ports(8000)
        .with_volume_mapping('downloads', '/downloads')
        .with_bind_ports(8000, 8000) as container
    ):
        wait_for_logs(
            container=container,
            predicate='Uvicorn running on',
            timeout=30,
            interval=1,
        )


@pytest.fixture
def client():
    with TestClient(app=app, base_url='http://localhost:8000') as test_client:
        yield test_client

    test_client.close()
