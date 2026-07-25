# import math
# from models import Vehiculo, VehiculoTracking
# from extensions import db
# from datetime import datetime


# # ==========================
# # DISTANCIA HAVERSINE
# # ==========================
# def haversine(lat1, lon1, lat2, lon2):
#     R = 6371  # km

#     dlat = math.radians(lat2 - lat1)
#     dlon = math.radians(lon2 - lon1)

#     a = (
#         math.sin(dlat / 2) ** 2 +
#         math.cos(math.radians(lat1)) *
#         math.cos(math.radians(lat2)) *
#         math.sin(dlon / 2) ** 2
#     )

#     c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

#     return R * c


# # ==========================
# # PROCESAR GPS
# # ==========================
# def procesar_gps(vehiculo_id, latitude, longitude, speed=0, ignition=0, fecha_gps=None):

#     vehiculo = Vehiculo.query.get(vehiculo_id)
#     if not vehiculo:
#         return None

#     # 1. obtener último punto
#     ultimo = VehiculoTracking.query.filter_by(
#         vehiculo_id=vehiculo_id
#     ).order_by(
#         VehiculoTracking.fecha_gps.desc()
#     ).first()

#     distancia = 0

#     # 2. calcular distancia si existe punto anterior
#     if ultimo and ultimo.latitude and ultimo.longitude:
#         distancia = haversine(
#             float(ultimo.latitude),
#             float(ultimo.longitude),
#             float(latitude),
#             float(longitude)
#         )

#         # 🚨 FILTRO ANTI GPS ERROR
#         if distancia > 2:  # más de 2 km entre 1 evento suele ser ruido
#             # opcional: bajar umbral según tu negocio
#             pass
#         else:
#             vehiculo.km_gps = (vehiculo.km_gps or 0) + distancia

#     # 3. guardar tracking
#     tracking = VehiculoTracking(
#         vehiculo_id=vehiculo_id,
#         latitude=latitude,
#         longitude=longitude,
#         speed=speed,
#         ignition=ignition,
#         fecha_gps=fecha_gps or datetime.utcnow()
#     )

#     db.session.add(tracking)

#     # 4. actualizar vehículo
#     vehiculo.km_actual = vehiculo.km_gps

#     db.session.commit()

#     return {
#         "vehiculo_id": vehiculo_id,
#         "km_sumado": distancia,
#         "km_total": vehiculo.km_gps
#     }

# from models import Vehiculo, VehiculoTracking, VehiculoUbicacionActual
# from extensions import db
# from datetime import datetime, timedelta
# import requests
# import time

# # =========================================
# # 🔐 CONFIG
# # =========================================
# TOKEN = None
# TOKEN_EXP = 0

# CLIENT_ID = "external-client-transmenaycarga02"
# CLIENT_SECRET = "8KWDOIYEyHaFhNkZkl8lgZ38ZnynzHYn"

# AUTH_URL = "https://externalsecurityapi.satrack.com/api/v1/Keycloak/authenticate"
# API_URL = "https://locationintegrationapi.satrack.com/api/location"


# # =========================================
# # 🔐 TOKEN
# # =========================================
# def obtener_token():
#     global TOKEN, TOKEN_EXP

#     if TOKEN and time.time() < TOKEN_EXP:
#         return TOKEN

#     res = requests.post(
#         AUTH_URL,
#         data={
#             "client_id": CLIENT_ID,
#             "client_secret": CLIENT_SECRET,
#             "grant_type": "client_credentials"
#         }
#     )

#     data = res.json()

#     TOKEN = data["access_token"]
#     TOKEN_EXP = time.time() + data["expires_in"] - 60

#     return TOKEN


# # =========================================
# # 📦 CHUNK
# # =========================================
# def chunk_list(lst, size=20):
#     for i in range(0, len(lst), size):
#         yield lst[i:i + size]


# # =========================================
# # 📡 OBTENER DATOS
# # =========================================
# def obtener_vehiculos():
#     token = obtener_token()

#     vehiculos = Vehiculo.query.with_entities(Vehiculo.gps_id).all()
#     service_codes = [v.gps_id for v in vehiculos if v.gps_id]

#     end = datetime.utcnow()
#     start = end - timedelta(days=5)

#     all_events = []

#     for chunk in chunk_list(service_codes, 20):

#         codes_str = ",".join([f'"{c}"' for c in chunk])

#         query = f"""
#         {{
#           byDate(
#             serviceCode:[{codes_str}],
#             currentPage:1,
#             itemsPerPage:500,
#             initialDate:"{start.strftime('%Y/%m/%d %H:%M:%S')}",
#             endDate:"{end.strftime('%Y/%m/%d %H:%M:%S')}",
#             eventCodes:[]
#           ){{
#             events{{
#               serviceCode
#               latitude
#               longitude
#               speed
#               ignition
#               address
#               town
#               direction
#               recordDate
#               description
#               odometer
#             }}
#           }}
#         }}
#         """

#         res = requests.post(
#             API_URL,
#             headers={
#                 "Authorization": f"Bearer {token}",
#                 "Content-Type": "application/json"
#             },
#             json={"query": query}
#         )

#         if res.status_code != 200:
#             print("❌ Error API:", res.text)
#             continue

#         events = res.json().get("data", {}).get("byDate", {}).get("events", [])
#         all_events.extend(events)

#     return all_events


# # =========================================
# # 🧠 FECHA
# # =========================================
# def parse_fecha(fecha):
#     if not fecha:
#         return None
#     try:
#         return datetime.fromisoformat(fecha.replace("Z", ""))
#     except:
#         return None


# # =========================================
# # 🚗 PROCESAR GPS (ODÓMETRO REAL → km_gps)
# # =========================================
# def procesar_gps(data):

#     if not isinstance(data, dict):
#         return None

#     gps_id = data.get("serviceCode")
#     if not gps_id:
#         return None

#     vehiculo = Vehiculo.query.filter_by(gps_id=gps_id).first()
#     if not vehiculo:
#         return None

#     fecha_gps = parse_fecha(data.get("recordDate"))

#     # =====================================
#     # ⛔ DUPLICADOS
#     # =====================================
#     ultimo = VehiculoTracking.query.filter_by(
#         vehiculo_id=vehiculo.id
#     ).order_by(VehiculoTracking.fecha_gps.desc()).first()

#     if ultimo and ultimo.fecha_gps and fecha_gps:
#         if abs((fecha_gps - ultimo.fecha_gps).total_seconds()) < 10:
#             return None

#     # =====================================
#     # 🚗 ODOMETRO REAL → km_gps (CORRECTO)
#     # =====================================
#     odometro_api = data.get("odometer")

#     if odometro_api is not None:
#         try:
#             odometro_api = float(odometro_api)
#         except:
#             odometro_api = None

#         if odometro_api is not None:
#             if vehiculo.km_gps is None:
#                 vehiculo.km_gps = odometro_api
#             else:
#                 if odometro_api > vehiculo.km_gps:
#                     vehiculo.km_gps = odometro_api

#     # =====================================
#     # 🧾 TRACKING
#     # =====================================
#     nuevo = VehiculoTracking(
#         vehiculo_id=vehiculo.id,
#         gps_id=gps_id,
#         latitude=data.get("latitude"),
#         longitude=data.get("longitude"),
#         speed=data.get("speed", 0),
#         ignition=bool(data.get("ignition", 0)),
#         direccion=data.get("direction"),
#         ciudad=data.get("town"),
#         evento=data.get("description"),
#         fecha_gps=fecha_gps
#     )

#     db.session.add(nuevo)

#     # =====================================
#     # 📍 UBICACIÓN ACTUAL
#     # =====================================
#     ubicacion = VehiculoUbicacionActual.query.filter_by(
#         vehiculo_id=vehiculo.id
#     ).first()

#     if not ubicacion:
#         ubicacion = VehiculoUbicacionActual(vehiculo_id=vehiculo.id)
#         db.session.add(ubicacion)

#     ubicacion.gps_id = gps_id
#     ubicacion.latitude = data.get("latitude")
#     ubicacion.longitude = data.get("longitude")
#     ubicacion.speed = data.get("speed", 0)
#     ubicacion.ignition = bool(data.get("ignition", 0))
#     ubicacion.direccion = data.get("direction")
#     ubicacion.ciudad = data.get("town")
#     ubicacion.direccion_texto = data.get("address")
#     ubicacion.evento = data.get("description")
#     ubicacion.fecha_gps = fecha_gps

#     return {
#         "vehiculo_id": vehiculo.id,
#         "gps_id": gps_id,
#         "km_gps": vehiculo.km_gps,
#         "odometer": odometro_api
#     }


# # =========================================
# # 🔄 SINCRONIZAR
# # =========================================
# def sincronizar_satrack():
#     data = obtener_vehiculos()

#     actualizados = []

#     for v in data:
#         try:
#             r = procesar_gps(v)
#             if r:
#                 actualizados.append(r)
#         except Exception as e:
#             print("❌ Error:", e)

#     try:
#         db.session.commit()
#     except Exception as e:
#         db.session.rollback()
#         print("❌ Error commit:", e)

#     return actualizados