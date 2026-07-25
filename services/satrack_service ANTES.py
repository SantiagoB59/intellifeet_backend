
from models import Vehiculo, VehiculoTracking, VehiculoUbicacionActual
from services.kilometraje_service import haversine
from extensions import db
from datetime import datetime
import requests
import time

# =========================================
# 🔐 CONFIG
# =========================================
TOKEN = None
TOKEN_EXP = 0

CLIENT_ID = "external-client-transmenaycarga02"
CLIENT_SECRET = "8KWDOIYEyHaFhNkZkl8lgZ38ZnynzHYn"

AUTH_URL = "https://externalsecurityapi.satrack.com/api/v1/Keycloak/authenticate"
API_URL = "https://locationintegrationapi.satrack.com/api/location"


# =========================================
# 🔐 TOKEN
# =========================================
def obtener_token():
    global TOKEN, TOKEN_EXP

    if TOKEN and time.time() < TOKEN_EXP:
        return TOKEN

    print("🔄 Generando nuevo token...")

    res = requests.post(
        AUTH_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials"
        }
    )

    data = res.json()

    TOKEN = data["access_token"]
    TOKEN_EXP = time.time() + data["expires_in"] - 60

    return TOKEN


# =========================================
# 📡 OBTENER GPS
# =========================================
def obtener_vehiculos():
    token = obtener_token()

    res = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={
            "query": """
            {
              last(serviceCodes:[]){
                serviceCode
                latitude
                longitude
                speed
                ignition
                address
                town
                direction
                recordDate
                description
                odometer
              }
            }
            """
        }
    )

    if res.status_code != 200:
        print("❌ Error API:", res.text)
        return []

    return res.json().get("data", {}).get("last", [])


# =========================================
# 🧠 HELPERS
# =========================================
def parse_fecha(fecha):
    if not fecha:
        return None
    try:
        return datetime.fromisoformat(fecha.replace("Z", ""))
    except:
        return None


# =========================================
# 🚗 PROCESAR GPS
# =========================================
def procesar_gps(data):
    if not isinstance(data, dict):
        return None

    gps_id = data.get("serviceCode")
    if not gps_id:
        return None

    vehiculo = Vehiculo.query.filter_by(gps_id=gps_id).first()
    if not vehiculo:
        return None

    fecha_gps = parse_fecha(data.get("recordDate"))

    # ==========================
    # 📍 ÚLTIMO TRACKING
    # ==========================
    ultimo = VehiculoTracking.query.filter_by(
        vehiculo_id=vehiculo.id
    ).order_by(VehiculoTracking.fecha_gps.desc()).first()

    # ==========================
    # ⛔ EVITAR DUPLICADOS
    # ==========================
    if ultimo and ultimo.fecha_gps and fecha_gps:
        diff = abs((fecha_gps - ultimo.fecha_gps).total_seconds())
        if diff < 10:
            return None

    # ==========================
    # 🧾 NUEVO TRACKING
    # ==========================
    nuevo = VehiculoTracking(
        vehiculo_id=vehiculo.id,
        gps_id=gps_id,
        latitude=data.get("latitude"),
        longitude=data.get("longitude"),
        speed=data.get("speed", 0),
        ignition=bool(data.get("ignition", 0)),
        direccion=data.get("direction"),
        ciudad=data.get("town"),
        evento=data.get("description"),
        fecha_gps=fecha_gps
    )
    db.session.add(nuevo)

    # ==========================
# 📏 ODOMETRO SATRACK
# ==========================

    odometro = data.get("odometer")

    if odometro is not None:

        vehiculo.km_gps = float(odometro)

    # Primera sincronización GPS
        if vehiculo.km_gps_inicial is None:
            vehiculo.km_gps_inicial = float(odometro)
    # ==========================
    # 📍 UBICACIÓN ACTUAL
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
    ubicacion.latitude = data.get("latitude")
    ubicacion.longitude = data.get("longitude")
    ubicacion.speed = data.get("speed", 0)
    ubicacion.ignition = bool(data.get("ignition", 0))
    ubicacion.direccion = data.get("direction")
    ubicacion.ciudad = data.get("town")
    ubicacion.direccion_texto = data.get("address")
    ubicacion.evento = data.get("description")
    ubicacion.fecha_gps = fecha_gps

    return {
        "vehiculo_id": vehiculo.id,
        "gps_id": gps_id,
        "lat": ubicacion.latitude,
        "lng": ubicacion.longitude,
        "speed": ubicacion.speed,
        "km_actual": vehiculo.km_actual
    }


# =========================================
# 🔄 SINCRONIZAR
# =========================================
def sincronizar_satrack():
    data = obtener_vehiculos()

    actualizados = []

    for v in data:
        try:
            res = procesar_gps(v)
            if res:
                actualizados.append(res)
        except Exception as e:
            print("❌ Error procesando GPS:", e)

    # 🔥 UN SOLO COMMIT (clave)
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        print("❌ Error commit:", e)

    print(f"🚗 Vehículos procesados: {len(actualizados)}")

    return actualizados