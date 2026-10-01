from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_update_player_behaviour():
    response = client.patch("/players/1/behaviour", json={"behaviourId": 1})
    assert response.status_code in [200, 401, 422]