def test_health_endpoint_returns_service_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai-image-upscale-api"}
