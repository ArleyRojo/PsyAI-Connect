from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect

from app.config import config as Config


class ExtensionsInitializer:
    def __init__(self):
        self.cors = CORS()
        self.csrf = CSRFProtect()

    def init_app(self, app):
        app.secret_key = Config.SECRET_KEY

        self.cors.init_app(app, supports_credentials=True, origins=Config.CORS_ORIGINS)

        Limiter(app=app, key_func=get_remote_address, storage_uri=Config.RATELIMIT_STORAGE_URI)
        self.csrf.init_app(app)

        if not Config.WTF_CSRF_ENABLED:
            self.csrf.exempt(lambda: True)

        def get_limiter():
            limiters = app.extensions.get("limiter", set())
            return next(iter(limiters)) if limiters else None

        app.get_limiter = get_limiter


extensions = ExtensionsInitializer()
cors = extensions.cors
csrf = extensions.csrf
init_extensions = extensions.init_app
