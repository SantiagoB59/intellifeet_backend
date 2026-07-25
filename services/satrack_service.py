from models import Vehiculo, VehiculoTracking, VehiculoUbicacionActual
from extensions import db

from datetime import datetime, timedelta

import requests
import time

from dotenv import load_dotenv
import os

load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTH_URL = os.getenv("AUTH_URL")
API_URL = os.getenv("API_URL")


TOKEN = None
TOKEN_EXP = 0




# =========================================
# 🔐 TOKEN
# =========================================
def obtener_token():

    global TOKEN, TOKEN_EXP

    if TOKEN and time.time() < TOKEN_EXP:
        return TOKEN

    res = requests.post(
        AUTH_URL,
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "grant_type": "client_credentials"
        },
        timeout=30
    )

    if res.status_code != 200:
        raise Exception(
            f"Error autenticando SATRACK: {res.text}"
        )

    data = res.json()

    TOKEN = data["access_token"]
    TOKEN_EXP = time.time() + data["expires_in"] - 60

    return TOKEN


# =========================================
# 📦 CHUNKS
# =========================================
def chunk_list(lst, size=20):

    for i in range(0, len(lst), size):
        yield lst[i:i + size]


# =========================================
# 🧠 PARSE FECHA
# =========================================
def parse_fecha(fecha):

    if not fecha:
        return None

    try:

        return datetime.fromisoformat(
            fecha.replace("Z", "")
        )

    except Exception:

        return None

# =========================================
# 📡 OBTENER EVENTOS
# =========================================
def obtener_eventos():

    token = obtener_token()

    # =====================================
    # 🚗 GPS IDS VÁLIDOS
    # =====================================
    gps_ids = db.session.query(
        Vehiculo.gps_id
    ).filter(
        Vehiculo.gps_id.isnot(None),
        Vehiculo.gps_id != ""
    ).all()

    service_codes = [
        v[0].strip()
        for v in gps_ids
        if v[0]
    ]

    if not service_codes:

        print("⚠️ No hay GPS IDs")
        return []

    print(f"🚗 Vehículos GPS: {len(service_codes)}")

    # =====================================
    # ⏱ RANGO DE FECHAS
    # =====================================
    end = datetime.utcnow()

    ultima_fecha = db.session.query(
        db.func.max(VehiculoUbicacionActual.fecha_gps)).scalar()
    if ultima_fecha:
    # un minuto de traslape por seguridad
        start = ultima_fecha - timedelta(minutes=1)
    else:
        start = end - timedelta(minutes=30)

    # Cuando tengas ConfiguracionSistema sería:
    #
    # config = ConfiguracionSistema.query.first()
    #
    # if config and config.ultima_sync_satrack:
    #     start = config.ultima_sync_satrack
    # else:
    #     start = end - timedelta(minutes=10)

    all_events = []

    # =====================================
    # 📦 CONSULTA POR LOTES
    # =====================================
    for chunk in chunk_list(service_codes, 20):

        try:

            codes_str = ",".join(
                f'"{c}"'
                for c in chunk
            )

            query = f"""
            {{
              byDate(
                serviceCode:[{codes_str}],
                currentPage:1,
                itemsPerPage:500,
                initialDate:"{start.strftime('%Y/%m/%d %H:%M:%S')}",
                endDate:"{end.strftime('%Y/%m/%d %H:%M:%S')}",
                eventCodes:[]
              ){{
                events{{
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
                }}
              }}
            }}
            """

            print("\n========================")
            print("📡 CONSULTANDO SATRACK")
            print("========================")
            print(f"🚗 GPS CHUNK: {chunk}")
            print()

            res = requests.post(
                API_URL,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json"
                },
                json={"query": query},
                timeout=60
            )

            print("STATUS:", res.status_code)

            if res.status_code != 200:

                print("❌ ERROR SATRACK")
                print(res.text)

                continue

            response_json = res.json()

            events = (
                response_json
                .get("data", {})
                .get("byDate", {})
                .get("events", [])
            )

            print(f"✅ Eventos recibidos: {len(events)}")

            all_events.extend(events)

        except Exception as e:

            print("❌ Error consultando SATRACK:", e)

    # =====================================
    # 🚗 SOLO EL EVENTO MÁS NUEVO
    # DE CADA VEHÍCULO
    # =====================================
    ultimos_eventos = {}

    for evento in all_events:

        gps_id = evento.get("serviceCode")

        fecha = parse_fecha(
            evento.get("recordDate")
        )

        if not gps_id or not fecha:
            continue

        evento_guardado = ultimos_eventos.get(gps_id)

        if (
            evento_guardado is None
            or fecha >
               parse_fecha(
                   evento_guardado.get("recordDate")
               )
        ):
            ultimos_eventos[gps_id] = evento

    eventos_finales = list(
        ultimos_eventos.values()
    )

    print(
        f"\n🚗 Eventos finales: {len(eventos_finales)}"
    )

    return eventos_finales

# # =========================================
# # 🔄 SINCRONIZAR
# # =========================================
# def sincronizar_satrack():

#     eventos = obtener_eventos()

#     if not eventos:

#         print("⚠️ No llegaron eventos")

#         return []

#     # =====================================
#     # 🚗 TOMAR SOLO EL EVENTO MÁS NUEVO
#     # DE CADA VEHÍCULO
#     # =====================================
#     ultimos_eventos = {}

#     for evento in eventos:

#         gps_id = evento.get("serviceCode")

#         fecha = parse_fecha(
#             evento.get("recordDate")
#         )

#         if not gps_id or not fecha:
#             continue

#         if (
#             gps_id not in ultimos_eventos
#             or fecha >
#                parse_fecha(
#                    ultimos_eventos[gps_id]["recordDate"]
#                )
#         ):
#             ultimos_eventos[gps_id] = evento

#     eventos = list(
#         ultimos_eventos.values()
#     )

#     print(
#         f"🚗 Eventos finales a procesar: {len(eventos)}"
#     )

#     # =====================================
#     # 🚗 VEHÍCULOS
#     # =====================================
#     vehiculos = Vehiculo.query.all()

#     vehiculos_map = {
#         v.gps_id: v
#         for v in vehiculos
#         if v.gps_id
#     }

#     # =====================================
#     # 📍 UBICACIONES
#     # =====================================
#     ubicaciones = VehiculoUbicacionActual.query.all()

#     ubicaciones_map = {
#         u.vehiculo_id: u
#         for u in ubicaciones
#     }

#     # =====================================
#     # 🧠 CACHE DUPLICADOS
#     # =====================================
#     fechas_cache = set()

#     # =====================================
#     # 📦 BULK INSERT
#     # =====================================
#     nuevos_trackings = []

#     actualizados = []

#     # =====================================
#     # 🔄 RECORRER EVENTOS
#     # =====================================
#     for data in eventos:

#         try:

#             if not isinstance(data, dict):
#                 continue

#             gps_id = data.get("serviceCode")

#             if not gps_id:
#                 continue

#             vehiculo = vehiculos_map.get(gps_id)

#             if not vehiculo:
#                 continue

#             fecha_gps = parse_fecha(
#                 data.get("recordDate")
#             )

#             if not fecha_gps:
#                 continue

#             # =================================
#             # ⛔ DUPLICADOS MEMORIA
#             # =================================
#             cache_key = f"{vehiculo.id}_{fecha_gps}"

#             if cache_key in fechas_cache:
#                 continue

#             fechas_cache.add(cache_key)

#             # =================================
#             # 📊 DATOS
#             # =================================
#             speed = float(data.get("speed") or 0)

#             ignition = bool(
#                 data.get("ignition", 0)
#             )

#             descripcion = (
#                 data.get("description") or ""
#             )

#             # =================================
#             # ⛔ IGNORAR EVENTOS BASURA
#             # =================================
#             if (
#                 speed == 0
#                 and ignition is False
#                 and "Tiempo Vehículo apagado" in descripcion
#             ):
#                 continue

#             # =================================
#             # 🚗 ODOMETRO SATRACK
#             # =================================
#             odometro_api = data.get("odometer")

#             try:
#                 odometro_api = float(
#                     odometro_api
#                 )
#             except Exception:
#                 odometro_api = None

#             if odometro_api is not None:

#                 print(
#                     f"🚗 {vehiculo.placa} | "
#                     f"Fecha GPS: {fecha_gps} | "
#                     f"Odómetro: {odometro_api}"
#                 )

#                 # último odómetro GPS
#                 vehiculo.km_gps = odometro_api

#                 # primera lectura GPS
#                 if vehiculo.km_gps_inicial is None:
#                     vehiculo.km_gps_inicial = odometro_api

#             # =================================
#             # 🧾 TRACKING
#             # =================================
#             tracking = VehiculoTracking(
#                 vehiculo_id=vehiculo.id,
#                 gps_id=gps_id,
#                 latitude=data.get("latitude"),
#                 longitude=data.get("longitude"),
#                 speed=speed,
#                 ignition=ignition,
#                 direccion=data.get("direction"),
#                 ciudad=data.get("town"),
#                 evento=descripcion,
#                 fecha_gps=fecha_gps,
#                 odometro=odometro_api,
#                 created_at=datetime.utcnow()
#             )

#             nuevos_trackings.append(
#                 tracking
#             )

#             # =================================
#             # 📍 UBICACIÓN ACTUAL
#             # =================================
#             ubicacion = ubicaciones_map.get(
#                 vehiculo.id
#             )

#             if not ubicacion:

#                 ubicacion = VehiculoUbicacionActual(
#                     vehiculo_id=vehiculo.id
#                 )

#                 db.session.add(ubicacion)

#                 ubicaciones_map[
#                     vehiculo.id
#                 ] = ubicacion

#             nueva_lat = data.get("latitude")
#             nueva_lon = data.get("longitude")

#             cambio = (
#                 ubicacion.latitude != nueva_lat
#                 or ubicacion.longitude != nueva_lon
#                 or ubicacion.fecha_gps != fecha_gps
#             )

#             if cambio:

#                 ubicacion.gps_id = gps_id
#                 ubicacion.latitude = nueva_lat
#                 ubicacion.longitude = nueva_lon
#                 ubicacion.speed = speed
#                 ubicacion.ignition = ignition
#                 ubicacion.direccion = data.get("direction")
#                 ubicacion.ciudad = data.get("town")
#                 ubicacion.direccion_texto = data.get("address")
#                 ubicacion.evento = descripcion
#                 ubicacion.fecha_gps = fecha_gps
#                 ubicacion.updated_at = datetime.utcnow()

#             actualizados.append({
#                 "vehiculo_id": vehiculo.id,
#                 "gps_id": gps_id,
#                 "km_gps": vehiculo.km_gps
#             })

#         except Exception as e:

#             print(
#                 "❌ Error procesando:",
#                 e
#             )

#     # =====================================
#     # 🚀 GUARDAR
#     # =====================================
#     try:

#         if nuevos_trackings:

#             db.session.bulk_save_objects(
#                 nuevos_trackings
#             )

#         db.session.commit()

#         print(
#             f"\n🚗 VEHÍCULOS ACTUALIZADOS: {len(actualizados)}"
#         )

#         print(
#             f"📦 TRACKINGS INSERTADOS: {len(nuevos_trackings)}"
#         )

#     except Exception as e:

#         db.session.rollback()

#         print(
#             "❌ Error commit:",
#             e
#         )

#     return actualizados


