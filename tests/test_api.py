import pytest
from app import app, driver, DATABASE

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_login_page(client):
    response = client.get('/login')
    assert response.status_code == 200

def test_database_connection():
    with driver.session(database=DATABASE) as sess:
        result = sess.run("RETURN 1 AS val").single()
        assert result['val'] == 1