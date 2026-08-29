def test_application_factory_registers_web_routes(app):
    endpoints = {rule.endpoint for rule in app.url_map.iter_rules()}

    assert 'web.select_parameters' in endpoints
    assert 'web.calculate' in endpoints


def test_home_page_is_available(client):
    response = client.get('/')

    assert response.status_code == 200


def test_calculation_endpoint_rejects_zero_values(client):
    response = client.get('/calculate?cutting_speed=0&feed_per_tooth=0')

    assert response.status_code == 400
    assert response.get_json()['error']
