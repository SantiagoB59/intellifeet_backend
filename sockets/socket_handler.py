from flask_socketio import SocketIO
from services.satrack_service import obtener_eventos
from models import (
    Vehiculo,
    VehiculoTracking,
    VehiculoUbicacionActual,
)
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


# =========================================
# 🚗 PROCESAR VEHÍCULO
# =========================================
def procesar_vehiculo(v, vehiculos_map, ubicaciones_map):

    if not isinstance(v, dict):
        return None

    gps_id = v.get("serviceCode")

    if not gps_id:
        return None

    # =====================================
    # 🚗 VEHÍCULO (CACHE)
    # =====================================
    vehiculo = vehiculos_map.get(gps_id)

    if not vehiculo:
        return None

    fecha_gps = parse_fecha(
        v.get("recordDate")
    )

    # =====================================
    # 📍 UBICACIÓN (CACHE)
    # =====================================
    ubicacion = ubicaciones_map.get(
        vehiculo.id
    )

    # =====================================
    # ⛔ Evento viejo
    # =====================================
    if (
        ubicacion
        and ubicacion.fecha_gps
        and fecha_gps
        and ubicacion.fecha_gps >= fecha_gps
    ):
        return None

    # =====================================
    # 📏 ODOMETRO
    # =====================================
    odometro = None

    try:
        if v.get("odometer") is not None:
            odometro = float(v.get("odometer"))
    except Exception:
        pass

    if odometro is not None:

        if (
            vehiculo.km_gps is None
            or odometro > vehiculo.km_gps
        ):
            vehiculo.km_gps = odometro

        if vehiculo.km_gps_inicial is None:
            vehiculo.km_gps_inicial = odometro

    # =====================================
    # 📜 HISTÓRICO
    # =====================================
    tracking = VehiculoTracking(
        vehiculo_id=vehiculo.id,
        gps_id=gps_id,
        latitude=v.get("latitude"),
        longitude=v.get("longitude"),
        speed=float(v.get("speed") or 0),
        ignition=bool(v.get("ignition", 0)),
        direccion=v.get("direction"),
        ciudad=v.get("town"),
        evento=v.get("description"),
        fecha_gps=fecha_gps,
        odometro=odometro
    )

    db.session.add(tracking)

    # =====================================
    # 📍 CREAR UBICACIÓN SI NO EXISTE
    # =====================================
    if not ubicacion:

        ubicacion = VehiculoUbicacionActual(
            vehiculo_id=vehiculo.id
        )

        db.session.add(ubicacion)

        # 🔥 guardar también en el cache
        ubicaciones_map[vehiculo.id] = ubicacion

    # =====================================
    # 📍 ACTUALIZAR UBICACIÓN
    # =====================================
    ubicacion.gps_id = gps_id
    ubicacion.latitude = v.get("latitude")
    ubicacion.longitude = v.get("longitude")
    ubicacion.speed = float(v.get("speed") or 0)
    ubicacion.ignition = bool(v.get("ignition", 0))
    ubicacion.direccion = v.get("direction")
    ubicacion.ciudad = v.get("town")
    ubicacion.direccion_texto = v.get("address")
    ubicacion.evento = v.get("description")
    ubicacion.fecha_gps = fecha_gps

    return {
        "vehiculo_id": vehiculo.id,
        "gps_id": gps_id,
        "km_gps": vehiculo.km_gps,
        "latitude": ubicacion.latitude,
        "longitude": ubicacion.longitude,
        "speed": ubicacion.speed,
        "fecha_gps": (
            fecha_gps.isoformat()
            if fecha_gps else None
        )
    }
# =========================================
# 🔄 WORKER
# =========================================
def worker(app):

    with app.app_context():

        while True:

            try:

                eventos = obtener_eventos()

                # =====================================
                # 🚗 CARGAR VEHÍCULOS UNA SOLA VEZ
                # =====================================
                vehiculos = Vehiculo.query.all()

                vehiculos_map = {
                    v.gps_id: v
                    for v in vehiculos
                    if v.gps_id
                }

                # =====================================
                # 📍 CARGAR UBICACIONES UNA SOLA VEZ
                # =====================================
                ubicaciones = VehiculoUbicacionActual.query.all()

                ubicaciones_map = {
                    u.vehiculo_id: u
                    for u in ubicaciones
                }

                actualizados = []

                # =====================================
                # 🔄 PROCESAR EVENTOS
                # =====================================
                for evento in eventos:

                    resultado = procesar_vehiculo(
                        evento,
                        vehiculos_map,
                        ubicaciones_map
                    )

                    if resultado:
                        actualizados.append(resultado)

                # =====================================
                # 💾 GUARDAR TODO DE UNA VEZ
                # =====================================
                db.session.commit()

                # =====================================
                # 📡 ENVIAR SOCKET
                # =====================================
                if actualizados:

                    socketio.emit(
                        "vehiculos",
                        actualizados
                    )

                print(
                    f"✅ Vehículos actualizados: {len(actualizados)}"
                )

            except Exception as e:

                db.session.rollback()

                print(
                    "❌ Error Worker:",
                    e
                )

            time.sleep(30)


# =========================================
# 🚀 INICIAR WORKER
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