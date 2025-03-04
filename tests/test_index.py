from http import HTTPStatus


def test_index_web_ui_return_200(client):
    assert client.get('/').status_code == HTTPStatus.OK
