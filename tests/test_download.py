from http import HTTPStatus


def test_download_response_is_ok(client, app_container):
    response = client.post(
        '/download/',
        params={
            'url': 'https://open.spotify.com/intl-pt/track/5HjBpej4uHPAX8sMeUFJms?si=15548e42a8674f5c'
        },
    )

    assert response.status_code == HTTPStatus.OK
