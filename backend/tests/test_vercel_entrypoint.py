def test_vercel_entrypoint_exports_the_fastapi_application():
    from api.index import app
    from app.main import app as main_app

    assert app is main_app
