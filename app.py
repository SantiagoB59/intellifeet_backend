# ==============================
# APP PRINCIPAL
# ==============================

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import os

from extensions import db, migrate, jwt
from config import Config

# Blueprints
from routes.auth import auth_bp
from routes.vehiculos import vehiculos_bp
from routes.maquinaria import maquinaria_bp
from routes.mantenimiento import mantenimientos_bp
from routes.mantenimiento_plan import mantenimiento_plan_bp
from routes.maquinaria_mantenimiento_plan import maquinaria_plan_bp
from routes.plan_items import plan_items_bp
from routes.sistemas import sistemas_bp
from routes.alertas import alertas_bp
from routes.viajes import viajes_bp
from routes.reportes import reportes_bp
from routes.importador import importador_bp
from extensions import mail
from routes.test_routes import test_bp
from routes.inspeccion_mensual import inspeccion_mensual_bp
from scheduler import iniciar_scheduler
# from routes.mantenimiento_importar import mantenimiento_importar_bp


# 🔥 sockets
from sockets.socket_handler import socketio, iniciar_worker


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ==============================
    # EXTENSIONES
    # ==============================
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    mail.init_app(app)
    # 🔥 SOCKETIO (después de crear app)
    socketio.init_app(app, cors_allowed_origins="*")

    # ==============================
    # CORS
    # ==============================
    CORS(
        app,
        resources={r"/*": {"origins": "http://localhost:4200"}},
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"]
    )

    # ==============================
    # CARPETAS
    # ==============================
    os.makedirs('uploads/vehiculos', exist_ok=True)

    # ==============================
    # BLUEPRINTS
    # ==============================
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(vehiculos_bp, url_prefix='/api/vehiculos')
    app.register_blueprint(maquinaria_bp, url_prefix='/api/maquinaria')
    app.register_blueprint(mantenimientos_bp, url_prefix='/api/mantenimientos')
    app.register_blueprint(mantenimiento_plan_bp, url_prefix='/api')
    app.register_blueprint(maquinaria_plan_bp, url_prefix='/api')
    app.register_blueprint(plan_items_bp, url_prefix='/api')
    app.register_blueprint(sistemas_bp, url_prefix='/api')
    app.register_blueprint(alertas_bp, url_prefix='/api/alertas')
    app.register_blueprint(viajes_bp, url_prefix="/api/viajes")
    app.register_blueprint(reportes_bp, url_prefix="/api/reportes")
    app.register_blueprint(importador_bp, url_prefix="/api/importador")
    app.register_blueprint(test_bp, url_prefix='/api/test')
    # app.register_blueprint(mantenimiento_importar_bp, url_prefix='/api/mantenimiento_importar')
    app.register_blueprint(inspeccion_mensual_bp, url_prefix='/api/inspeccion_mensual')
    # ==============================
    # SERVIR IMÁGENES
    # ==============================
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory('uploads', filename)

    # ==============================
    # RUTA BASE
    # ==============================
    @app.route('/')
    def index():
        return jsonify({
            "message": "🚛 API Transmena Smart funcionando",
            "status": "ok"
        })

    # ==============================
    # ERRORES
    # ==============================
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Ruta no encontrada"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "Error interno del servidor"}), 500

    # 🔥 CORRECCIÓN AQUÍ (ANTES: iniciar_worker())
    iniciar_worker(app)
    iniciar_scheduler(app)
    return app


# ==============================
# RUN (🔥 CAMBIO CLAVE AQUÍ)
# ==============================
if __name__ == '__main__':
    app = create_app()

    # ❌ NO usar app.run()
    # app.run(debug=True)

    # ✅ USAR SOCKETIO
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)


# instalar para producción: pip install eventlet
# pip install eventlet