
from flask_socketio import SocketIO
from services.satrack_service import obtener_vehiculos
from models import Vehiculo, VehiculoTracking, VehiculoUbicacionActual
from extensions import db
from datetime import datetime
import threading
import time

# =========================================
# 🔥 SOCKET GLOBAL
# =========================================
socketio = SocketIO(cors_allowed_origins="*")

# =========================================
# 🧠 HELPERS
# =========================================
def parse_fecha(fecha_str):
    if not fecha_str:
        return None
    try:
        return datetime.fromisoformat(fecha_str.replace("Z", ""))
    except:
        return None


def procesar_vehiculo(v):
    """
    Procesa un vehículo del API y actualiza BD
    """
    if not isinstance(v, dict):
        return None

    gps_id = v.get("serviceCode")
    if not gps_id:
        return None

    vehiculo = Vehiculo.query.filter_by(gps_id=gps_id).first()
    if not vehiculo:
        return None

    fecha_gps = parse_fecha(v.get("recordDate"))

    # ==========================
    # 📜 HISTÓRICO
    # ==========================
    tracking = VehiculoTracking(
        vehiculo_id=vehiculo.id,
        gps_id=gps_id,
        latitude=v.get("latitude"),
        longitude=v.get("longitude"),
        speed=v.get("speed", 0),
        ignition=bool(v.get("ignition", 0)),
        direccion=v.get("direction"),
        ciudad=v.get("town"),
        evento=v.get("description"),
        fecha_gps=fecha_gps
    )
    db.session.add(tracking)

    # ==========================
    # 📍 TIEMPO REAL
    # ==========================
    ubicacion = VehiculoUbicacionActual.query.filter_by(
        vehiculo_id=vehiculo.id
    ).first()

    if not ubicacion:
        ubicacion = VehiculoUbicacionActual(
            vehiculo_id=vehiculo.id
        )
        db.session.add(ubicacion)

    ubicacion.gps_id = gps_id
    ubicacion.latitude = v.get("latitude")
    ubicacion.longitude = v.get("longitude")
    ubicacion.speed = v.get("speed", 0)
    ubicacion.ignition = bool(v.get("ignition", 0))
    ubicacion.direccion = v.get("direction")
    ubicacion.ciudad = v.get("town")
    ubicacion.direccion_texto = v.get("address")
    ubicacion.evento = v.get("description")
    ubicacion.fecha_gps = fecha_gps

    return {
        "vehiculo_id": vehiculo.id,
        "gps_id": gps_id,
        "latitude": ubicacion.latitude,
        "longitude": ubicacion.longitude,
        "speed": ubicacion.speed,
        "ignition": ubicacion.ignition,
        "evento": ubicacion.evento
    }


# =========================================
# 🔄 WORKER
# =========================================
def worker(app):
    with app.app_context():
        while True:
            try:
                data = obtener_vehiculos()
                actualizados = []

                for v in data:
                    result = procesar_vehiculo(v)
                    if result:
                        actualizados.append(result)

                # 🔥 UN SOLO COMMIT (clave performance)
                db.session.commit()

                # 🔥 SOLO emitir lo válido
                if actualizados:
                    socketio.emit("vehiculos", actualizados)

                print(f"🚗 Actualizados: {len(actualizados)}")

            except Exception as e:
                print("❌ Error worker:", e)
                db.session.rollback()

            time.sleep(30)


# =========================================
# 🚀 INICIAR WORKER (SAFE)
# =========================================
_worker_started = False

def iniciar_worker(app):
    global _worker_started

    if _worker_started:
        return

    thread = threading.Thread(target=worker, args=(app,))
    thread.daemon = True
    thread.start()

    _worker_started = True