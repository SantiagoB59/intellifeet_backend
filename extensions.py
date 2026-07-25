from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_mail import Mail

mail = Mail()
db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
