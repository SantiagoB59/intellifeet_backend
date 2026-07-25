from flask import Blueprint, request, jsonify
from models import (
    Vehiculo,
    VehiculoDocumento,
    DocumentoTipo,
    TipoVehiculo,
    VehiculoCampoValor, TipoVehiculoCampo, 
)
from models import VehiculoUbicacionActual
# from services.satrack_service import sincronizar_satrack
from extensions import db
import os
import uuid
import json
from sqlalchemy import or_

from datetime import date, timedelta

vehiculos_bp = Blueprint('vehiculos', __name__)

UPLOAD_FOLDER = 'uploads/vehiculos'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}


# ==========================
# HELPERS
# ==========================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def guardar_imagen(file):
    if not file or not allowed_file(file.filename):
        return None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4()}.{ext}"

    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    return f"/uploads/vehiculos/{filename}"


# ==========================
# LISTAR VEHÍCULOS
# ==========================
@vehiculos_bp.route('/', methods=['GET'])
def listar():
    estado = request.args.get('estado')
    tipo = request.args.get('tipo_vehiculo_id')  # 🔥 alineado con Angular
    search = request.args.get('search')

    query = Vehiculo.query

    # 🔥 soft delete: solo activos
    query = query.filter(Vehiculo.activo.is_(True))

    # filtro por estado
    if estado:
        query = query.filter(Vehiculo.estado == estado)

    # filtro por tipo
    if tipo:
        try:
            query = query.filter(Vehiculo.tipo_vehiculo_id == int(tipo))
        except ValueError:
            pass  # evita crash si llega algo inválido

    # búsqueda por placa (case-insensitive recomendado)
    if search:
        search = search.strip()
        query = query.filter(Vehiculo.placa.ilike(f"%{search}%"))

    vehiculos = query.all()

    return jsonify([v.to_dict() for v in vehiculos])

# ==========================
# OBTENER VEHÍCULO
# ==========================
@vehiculos_bp.route('/<placa>', methods=['GET'])
def obtener(placa):

    v = Vehiculo.query.filter_by(placa=placa).first_or_404()

    # ==========================
    # DOCUMENTOS
    # ==========================
    documentos = VehiculoDocumento.query.filter_by(
        vehiculo_id=v.id
    ).all()

    documentos_data = [
        {
            "documento_tipo_id": d.documento_tipo_id,
            "numero": d.numero,
            "fecha_expedicion": str(d.fecha_expedicion) if d.fecha_expedicion else None,
            "fecha_vencimiento": str(d.fecha_vencimiento) if d.fecha_vencimiento else None,
            "archivo_url": d.archivo_url
        }
        for d in documentos
    ]

    # ==========================
    # CAMPOS DINÁMICOS
    # ==========================
    campos = VehiculoCampoValor.query.filter_by(
        vehiculo_id=v.id
    ).all()

    campos_data = [
        {
            "campo_id": c.campo_id,
            "nombre": c.campo.nombre_campo if c.campo else None,
            "tipo": c.campo.tipo_dato if c.campo else None,
            "valor": c.valor
        }
        for c in campos
    ]

    # ==========================
    # RESPUESTA FINAL
    # ==========================
    data = v.to_dict()

    data["documentos"] = documentos_data
    data["campos_dinamicos"] = campos_data

    return jsonify(data)
# ==========================
# CREAR VEHÍCULO
# ==========================
@vehiculos_bp.route('/', methods=['POST'])
def crear():
    data = dict(request.form)
    file = request.files.get('foto')

    # ==========================
    # VALIDACIONES BÁSICAS
    # ==========================
    if not data.get('placa'):
        return jsonify({"error": "placa requerida"}), 400

    if Vehiculo.query.filter_by(placa=data['placa']).first():
        return jsonify({"error": "Ya existe"}), 400

    # ==========================
    # TIPO VEHÍCULO
    # ==========================
    tipo_id = int(data.get('tipo_vehiculo_id')) if data.get('tipo_vehiculo_id') else None
    data['tipo_vehiculo_id'] = tipo_id

    # ==========================
    # JSON SAFE PARSING
    # ==========================
    try:
        documentos = json.loads(data.pop('documentos', '[]'))
    except:
        documentos = []

    try:
        campos = json.loads(data.pop('campos_dinamicos', '[]'))
    except:
        campos = []

    # ==========================
    # NORMALIZAR CAMPOS NUMÉRICOS DEL MODELO
    # (🔥 IMPORTANTE para km_actual)
    # ==========================
    if 'km_actual' in data:
        try:
            data['km_actual'] = int(data['km_actual'])
        except:
            return jsonify({
                "error": "km_actual debe ser numérico"
            }), 400

    # ==========================
    # CREAR VEHÍCULO
    # ==========================
    columnas_validas = Vehiculo.__table__.columns.keys()

    v = Vehiculo(**{
        k: v for k, v in data.items() if k in columnas_validas
    })
    
    # ==========================
    # PRÓXIMA VERIFICACIÓN KM
    # =========================
    from datetime import date, timedelta

    v.fecha_proxima_verificacion = (
        date.today() + timedelta(days=15)
    )

    v.requiere_verificacion_km = False

    # ==========================
    # IMAGEN
    # ==========================
    foto_url = guardar_imagen(file)
    if foto_url:
        v.foto_url = foto_url

    db.session.add(v)
    db.session.flush()

    # ==========================
    # DOCUMENTOS
    # ==========================
    for doc in documentos:
        if not isinstance(doc, dict):
            continue

        db.session.add(VehiculoDocumento(
            vehiculo_id=v.id,
            documento_tipo_id=doc.get('documento_tipo_id'),
            numero=doc.get('numero'),
            fecha_expedicion=doc.get('fecha_expedicion'),
            fecha_vencimiento=doc.get('fecha_vencimiento'),
            archivo_url=doc.get('archivo_url')
        ))

    # ==========================
    # CAMPOS DINÁMICOS (VALIDADOS)
    # ==========================
    for campo in campos:
        if not isinstance(campo, dict):
            continue

        nombre = campo.get('nombre')
        valor = campo.get('valor')

        if not nombre:
            continue

        campo_def = TipoVehiculoCampo.query.filter_by(
            tipo_vehiculo_id=tipo_id,
            nombre_campo=nombre
        ).first()

        if not campo_def:
            continue

        # 🔥 VALIDACIÓN POR TIPO
        if campo_def.tipo_dato == 'number':
            try:
                valor = int(valor)   # 👉 usa float(valor) si luego quieres decimales
            except:
                return jsonify({
                    "error": f"El campo '{nombre}' debe ser numérico"
                }), 400

        elif campo_def.tipo_dato == 'date':
            try:
                from datetime import datetime
                valor = datetime.strptime(valor, "%Y-%m-%d").date()
            except:
                return jsonify({
                    "error": f"El campo '{nombre}' debe ser una fecha válida"
                }), 400

        elif campo_def.tipo_dato == 'text':
            valor = str(valor).strip()

        db.session.add(VehiculoCampoValor(
            vehiculo_id=v.id,
            campo_id=campo_def.id,
            valor=str(valor)  # 👈 sigues guardando como string
        ))

    db.session.commit()

    return jsonify(v.to_dict()), 201

# ==========================
# ACTUALIZAR VEHÍCULO
# ==========================
@vehiculos_bp.route('/<placa>', methods=['PUT'])
def actualizar(placa):
    v = Vehiculo.query.filter_by(placa=placa).first_or_404()

    data = dict(request.form)
    file = request.files.get('foto')

    # ==========================
    # TIPO
    # ==========================
    tipo_id = int(data.get('tipo_vehiculo_id')) if data.get('tipo_vehiculo_id') else v.tipo_vehiculo_id
    data['tipo_vehiculo_id'] = tipo_id

    # ==========================
    # SAFE JSON
    # ==========================
    try:
        documentos = json.loads(data.pop('documentos', '[]'))
    except:
        documentos = []

    try:
        campos = json.loads(data.pop('campos_dinamicos', '[]'))
    except:
        campos = []

    # ==========================
    # UPDATE CAMPOS MODELO
    # ==========================
    columnas_validas = Vehiculo.__table__.columns.keys()

    for key, value in data.items():
        if key in columnas_validas:
            setattr(v, key, value)

    # ==========================
    # IMAGEN
    # ==========================
    if file:
        if v.foto_url:
            old_path = v.foto_url.replace('/uploads/', 'uploads/')
            if os.path.exists(old_path):
                os.remove(old_path)

        v.foto_url = guardar_imagen(file)

    # ==========================
    # DOCUMENTOS
    # ==========================
    VehiculoDocumento.query.filter_by(vehiculo_id=v.id).delete()

    for doc in documentos:
        if not isinstance(doc, dict):
            continue

        db.session.add(VehiculoDocumento(
            vehiculo_id=v.id,
            documento_tipo_id=doc.get('documento_tipo_id'),
            numero=doc.get('numero'),
            fecha_expedicion=doc.get('fecha_expedicion'),
            fecha_vencimiento=doc.get('fecha_vencimiento'),
            archivo_url=doc.get('archivo_url')
        ))

    # ==========================
    # CAMPOS DINÁMICOS (VALIDADOS)
    # ==========================
    VehiculoCampoValor.query.filter_by(vehiculo_id=v.id).delete()

    for campo in campos:
        if not isinstance(campo, dict):
            continue

        nombre = campo.get('nombre')
        valor = campo.get('valor')

        if not nombre:
            continue

        campo_def = TipoVehiculoCampo.query.filter_by(
            tipo_vehiculo_id=tipo_id,
            nombre_campo=nombre
        ).first()

        if not campo_def:
            continue

        # 🔥 VALIDACIÓN POR TIPO
        if campo_def.tipo_dato == 'number':
            try:
                valor = int(valor)
            except:
                return jsonify({
                    "error": f"El campo '{nombre}' debe ser numérico"
                }), 400

        elif campo_def.tipo_dato == 'date':
            try:
                from datetime import datetime
                valor = datetime.strptime(valor, "%Y-%m-%d").date()
            except:
                return jsonify({
                    "error": f"El campo '{nombre}' debe ser una fecha válida"
                }), 400

        elif campo_def.tipo_dato == 'text':
            valor = str(valor).strip()

        db.session.add(VehiculoCampoValor(
            vehiculo_id=v.id,
            campo_id=campo_def.id,
            valor=str(valor)  # sigues guardando como string
        ))

    db.session.commit()

    return jsonify(v.to_dict())
# ==========================
# ELIMINAR VEHÍCULO
# ==========================
@vehiculos_bp.route('/<placa>', methods=['DELETE'])
def eliminar(placa):
    v = Vehiculo.query.filter_by(placa=placa).first_or_404()

    # 🔥 SOFT DELETE
    if v.activo == 0:
        return jsonify({"message": "El vehículo ya está desactivado"}), 400

    v.activo = 0

    db.session.commit()

    return jsonify({"message": "Vehículo desactivado correctamente"})
# ==========================
# STATS
# ==========================
@vehiculos_bp.route('/stats', methods=['GET'])
def stats():
    total = Vehiculo.query.filter_by(activo=True).count()
    operativos = Vehiculo.query.filter_by(estado='OPERATIVO', activo=True).count()
    taller = Vehiculo.query.filter_by(estado='TALLER', activo=True).count()
    inactivos = Vehiculo.query.filter_by(estado='INACTIVO', activo=True).count()

    return jsonify({
        "total": total,
        "operativos": operativos,
        "en_taller": taller,
        "inactivos": inactivos
    })


# ==========================
# ACTUALIZAR KM
# ==========================
@vehiculos_bp.route('/<placa>/km', methods=['PATCH'])
def actualizar_km(placa):
    v = Vehiculo.query.filter_by(placa=placa).first_or_404()

    km = request.args.get('km', type=int)

    if km is None:
        return jsonify({"error": "km requerido"}), 400

    # ==========================
    # Kilometraje ingresado
    # ==========================
    v.km_actual = km

    # ==========================
    # RECALIBRAR EL SISTEMA
    # ==========================
    if (
        v.km_gps is not None and
        v.km_gps_inicial is not None and
        v.km_base_control is not None
    ):
        v.km_base_control = km
        v.km_gps_inicial = v.km_gps

    # ==========================
    # Cerrar la verificación
    # ==========================
    v.requiere_verificacion_km = False

    v.fecha_ultima_verificacion = date.today()

    v.fecha_proxima_verificacion = (
        date.today() + timedelta(days=15)
    )

    db.session.commit()

    return jsonify(v.to_dict())


# ==========================
# TIPOS VEHÍCULO
# ==========================
@vehiculos_bp.route('/tipos_vehiculo', methods=['GET'])
def listar_tipos():
    tipos = TipoVehiculo.query.all()

    return jsonify([
        {"id": t.id, "nombre": t.nombre}
        for t in tipos
    ])


# ==========================
# TRACTOMULA (PADRE-HIJO)
# ==========================
# @vehiculos_bp.route('/tractomula', methods=['POST'])
# def crear_tractomula():
#     data = request.json

#     cabezote = Vehiculo(**data['cabezote'])
#     trailer = Vehiculo(**data['trailer'])

#     db.session.add(cabezote)
#     db.session.flush()

#     db.session.add(trailer)
#     db.session.flush()

#     db.session.add(VehiculoComponente(
#         vehiculo_padre_id=cabezote.id,
#         vehiculo_hijo_id=trailer.id,
#         tipo_componente='TRAILER'
#     ))

#     db.session.commit()

#     return jsonify({"ok": True})

@vehiculos_bp.route('/tipos_vehiculo/<int:tipo_id>/campos', methods=['GET'])
def campos_por_tipo(tipo_id):


    campos = TipoVehiculoCampo.query.filter_by(
        tipo_vehiculo_id=tipo_id
    ).all()

    return jsonify([
        {
            "id": c.id,
            "nombre_campo": c.nombre_campo,
            "tipo_dato": c.tipo_dato,
            "obligatorio": c.requerido
        }
        for c in campos
    ])
    
    
@vehiculos_bp.route('/documentos_tipo', methods=['GET'])
def documentos_tipo():

    documentos = DocumentoTipo.query.all()

    return jsonify([
        {
            "id": d.id,
            "nombre": d.nombre
        }
        for d in documentos
    ])
    
@vehiculos_bp.route('/documentos', methods=['GET'])
def documentos():

    tipo_id = request.args.get('tipo_vehiculo_id', type=int)

    if not tipo_id:
        return jsonify([])

    tipo = TipoVehiculo.query.get(tipo_id)

    # 🚫 Si NO es automotor → no tiene documentos
    if not tipo or not tipo.es_automotor:
        return jsonify([])

    # ✅ Si es automotor → trae documentos globales
    documentos = DocumentoTipo.query.all()

    return jsonify([
        {
            "id": d.id,
            "nombre": d.nombre,
            "requiere_numero": getattr(d, 'requiere_numero', True)
        }
        for d in documentos
    ])
@vehiculos_bp.route('/<placa>', methods=['GET'])
def obtener_por_placa(placa):
    v = Vehiculo.query.filter_by(placa=placa).first_or_404()

    # ==========================
    # 📄 DOCUMENTOS
    # ==========================
    documentos = VehiculoDocumento.query.filter_by(
        vehiculo_id=v.id
    ).all()

    documentos_data = [
        {
            "documento_tipo_id": d.documento_tipo_id,
            "nombre": d.tipo.nombre if d.tipo else None,
            "numero": d.numero,
            "fecha_expedicion": str(d.fecha_expedicion) if d.fecha_expedicion else None,
            "fecha_vencimiento": str(d.fecha_vencimiento) if d.fecha_vencimiento else None,
            "archivo_url": d.archivo_url
        }
        for d in documentos
    ]

    # ==========================
    # 🧩 CAMPOS DINÁMICOS
    # ==========================
    campos = VehiculoCampoValor.query.filter_by(
        vehiculo_id=v.id
    ).all()

    campos_data = {
        c.campo.nombre_campo: c.valor
        for c in campos if c.campo
    }

    # ==========================
    # 🚗 VEHÍCULO COMPLETO
    # ==========================
    data = v.to_dict()

    # 👇 IMPORTANTE: agregar extras
    data["documentos"] = documentos_data
    data["campos_dinamicos"] = campos_data

    return jsonify(data)


@vehiculos_bp.route('/id/<int:id>', methods=['GET'])
def obtener_por_id(id):
    v = Vehiculo.query.get_or_404(id)

    return jsonify(v.to_dict())


# ==============================
# 📍 UBICACIÓN ACTUAL DE VEHÍCULOS
# ==============================
@vehiculos_bp.route('/ubicacion-actual', methods=['GET'])
def ubicacion_actual():
    try:
        ubicaciones = VehiculoUbicacionActual.query.all()

        data = []

        for u in ubicaciones:
            data.append({
                "vehiculo_id": u.vehiculo_id,
                "gps_id": u.gps_id,
                "latitude": u.latitude,
                "longitude": u.longitude,
                "speed": u.speed,
                "ignition": u.ignition,
                "direccion": u.direccion,
                "ciudad": u.ciudad,
                "direccion_texto": u.direccion_texto,
                "evento": u.evento,
                "fecha_gps": u.fecha_gps.isoformat() if u.fecha_gps else None
            })

        return jsonify(data), 200

    except Exception as e:
        return jsonify({
            "error": "Error consultando ubicaciones",
            "detalle": str(e)
        }), 500


# @vehiculos_bp.route('/gps', methods=['POST'])
# def recibir_gps():

#     data = request.json

#     vehiculo_id = data.get('vehiculo_id')
#     latitude = data.get('latitude')
#     longitude = data.get('longitude')
#     speed = data.get('speed', 0)
#     ignition = data.get('ignition', 0)
#     fecha_gps = data.get('fecha_gps')

#     if not vehiculo_id or latitude is None or longitude is None:
#         return jsonify({"error": "datos incompletos"}), 400

#     result = sincronizar_satrack()

#     return jsonify(result), 200


@vehiculos_bp.route(
    '/verificacion-km',
    methods=['GET']
)
def vehiculos_pendientes_verificacion():

    vehiculos = Vehiculo.query.filter_by(
        activo=True,
        requiere_verificacion_km=True
    ).order_by(
        Vehiculo.placa
    ).all()

    return jsonify([
        {
            "id": v.id,
            "placa": v.placa,
            "marca": v.marca,
            "linea": v.linea,
            "modelo": v.modelo,

            "km_actual": v.km_actual,
            "km_estimado": v.km_estimado,

            "fecha_proxima_verificacion":
                str(v.fecha_proxima_verificacion)
                if v.fecha_proxima_verificacion
                else None
        }
        for v in vehiculos
    ])
    
    
# ==========================
# CANTIDAD DE VEHÍCULOS PENDIENTES DE VERIFICACIÓN
# ==========================
@vehiculos_bp.route(
    '/verificacion-km/count',
    methods=['GET']
)
def cantidad_pendientes_verificacion():

    total = Vehiculo.query.filter_by(
        activo=True,
        requiere_verificacion_km=True
    ).count()

    return jsonify({
        "total": total
    })