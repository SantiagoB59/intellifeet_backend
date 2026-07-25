from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from models import (
    db,
    Mantenimiento,
    MaquinariaMantenimiento,
    Vehiculo,
    Maquinaria,
    PlanItem,
    VehiculoPlanItem,
    MaquinariaPlanItem
)
from models import Alerta

from sqlalchemy import desc

from datetime import datetime
from sockets.socket_handler import socketio
import os
import uuid

mantenimientos_bp = Blueprint('mantenimientos', __name__)

# ==========================
# CONFIG
# ==========================
UPLOAD_FOLDER = 'uploads/mantenimientos'

ALLOWED_EXTENSIONS = {
    'png',
    'jpg',
    'jpeg',
    'pdf'
}

# ==========================
# HELPERS
# ==========================
def allowed_file(filename):

    return (
        '.' in filename
        and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ==========================
# HISTORIAL POR VEHICULO
# ==========================
@mantenimientos_bp.route(
    '/vehiculo-plan/<int:vehiculo_id>',
    methods=['GET']
)
def plan_por_vehiculo(vehiculo_id):

    vehiculo = Vehiculo.query.get_or_404(vehiculo_id)

    items = (
        VehiculoPlanItem.query
        .filter_by(
            vehiculo_id=vehiculo_id,
            activo=True
        )
        .all()
    )

    resultado = []

    for item in items:

        plan_item = PlanItem.query.get(item.plan_item_id)

        # últimos mantenimientos de ese item
        ultimo_mantenimiento = (
            Mantenimiento.query
            .filter_by(
                vehiculo_id=vehiculo_id,
                plan_item_id=item.plan_item_id
            )
            .order_by(Mantenimiento.fecha.desc())
            .first()
        )

        resultado.append({
            "vehiculo": {
                "id": vehiculo.id,
                "placa": vehiculo.placa
            },
            "vehiculo_plan_item_id": item.id,

            "plan_item": {
                "id": plan_item.id if plan_item else None,
                "nombre": plan_item.nombre if plan_item else None,
                "descripcion": plan_item.descripcion if plan_item else None,
                "tipo_mantenimiento": plan_item.tipo_mantenimiento if plan_item else None,
                "tipo_control": plan_item.tipo_control if plan_item else None,
                "frecuencia_valor": plan_item.frecuencia_valor if plan_item else None
            },

            "ultimo_mantenimiento": (
                ultimo_mantenimiento.to_dict()
                if ultimo_mantenimiento
                else None
            ),

            "ultimo_km": item.ultimo_km,
            "ultima_fecha": item.ultima_fecha,
            "estado": item.calcular_estado() if hasattr(item, "calcular_estado") else None
        })

    return jsonify(resultado)

# ==========================
# LISTAR
# ==========================
@mantenimientos_bp.route('', methods=['GET'])
def listar():

    placa = request.args.get('placa', '').strip()

    tipo = request.args.get('tipo')

    desde = request.args.get('desde')

    hasta = request.args.get('hasta')

    # JOIN con Vehiculo
    query = (
        Mantenimiento.query
        .join(Mantenimiento.vehiculo)
        )

    if placa:
        query = query.filter(
            Vehiculo.placa.ilike(f'%{placa}%')
        )

    if tipo:
        query = query.filter(
            Mantenimiento.tipo == tipo
        )

    if desde:
        query = query.filter(
            Mantenimiento.fecha >= desde
        )

    if hasta:
        query = query.filter(
            Mantenimiento.fecha <= hasta
        )
    mantenimientos = (
        query
        .order_by(Mantenimiento.fecha.desc())
        .all()
    )

    return jsonify([m.to_dict() for m in mantenimientos])
# ==========================
# CREAR
# ==========================
@mantenimientos_bp.route('', methods=['POST'])
def crear():

    # =====================================
    # FORM DATA
    # =====================================
    vehiculo_id = request.form.get(
        'vehiculo_id',
        type=int
    )

    vehiculo_plan_item_id = request.form.get(
        'vehiculo_plan_item_id',
        type=int
    )

    km = request.form.get(
        'km',
        type=int
    )
    if km is None:
        km = vehiculo.km_estimado

    fecha = request.form.get('fecha')

    tipo = request.form.get('tipo')

    proveedor = request.form.get('proveedor')

    observaciones = request.form.get('observaciones')

    costo = request.form.get(
        'costo',
        type=float
    )

    lugar = request.form.get('lugar')

    responsable = request.form.get('responsable')

    # =====================================
    # VALIDACIONES
    # =====================================
    if not vehiculo_id:

        return jsonify({
            "error": "vehiculo_id requerido"
        }), 400

    if not vehiculo_plan_item_id:

        return jsonify({
            "error": "vehiculo_plan_item_id requerido"
        }), 400

    if km is None:

        return jsonify({
            "error": "km requerido"
        }), 400

    # =====================================
    # VEHICULO
    # =====================================
    vehiculo = Vehiculo.query.get_or_404(
        vehiculo_id
    )

    # =====================================
    # VALIDAR PLAN VEHICULO
    # =====================================
    vpi = VehiculoPlanItem.query.get(
        vehiculo_plan_item_id
    )

    if not vpi:

        return jsonify({
            "error": "Plan del vehículo no existe"
        }), 404

    # =====================================
    # SUBIR SOPORTE
    # =====================================
    soporte_path = None

    if 'soporte' in request.files:

        file = request.files['soporte']

        if file and allowed_file(file.filename):

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )

            extension = (
                file.filename
                .rsplit('.', 1)[1]
                .lower()
            )

            filename = (
                f"{uuid.uuid4()}.{extension}"
            )

            filepath = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            file.save(filepath)

# Guardar la ruta para la web, no la del sistema operativo
            soporte_path = f"uploads/mantenimientos/{filename}"

    # =====================================
    # CREAR
    # =====================================
    mantenimiento = Mantenimiento(

        vehiculo_id=vehiculo.id,

        vehiculo_plan_item_id=vpi.id,

        plan_item_id=vpi.plan_item_id,

        fecha=datetime.strptime(
            fecha,
            '%Y-%m-%d'
        ).date() if fecha else None,

        km=km,

        tipo=tipo,

        proveedor=proveedor,

        observaciones=observaciones,

        soporte=soporte_path,

        costo=costo,

        lugar=lugar,

        responsable=responsable,

        completado=True
    )

    db.session.add(mantenimiento)
    # =====================================
# RECALIBRAR KILOMETRAJE DEL VEHÍCULO
# =====================================
    if abs(km - vehiculo.km_estimado) > 5:

        vehiculo.km_base_control = km
        vehiculo.km_gps_inicial = vehiculo.km_gps
# =====================================
# ACTUALIZAR PLAN
# =====================================

    vpi.ultimo_km = km
    vpi.ultima_fecha = mantenimiento.fecha

# =====================================
# RESOLVER ALERTAS DEL ITEM EJECUTADO
# =====================================

    alertas = Alerta.query.filter(
        Alerta.tipo == 'MANTENIMIENTO',
        Alerta.estado == 'ACTIVA',
        Alerta.vehiculo_plan_item_id == vpi.id
    ).all()

    for alerta in alertas:

        alerta.estado = 'RESUELTA'
        alerta.fecha_resolucion = datetime.utcnow()
        alerta.mantenimiento_id = mantenimiento.id

    db.session.commit()

# =====================================
# SOCKET TIEMPO REAL
# =====================================

    for alerta in alertas:

        socketio.emit(
            'alerta_resuelta',
            alerta.to_dict()
        )

    return jsonify(
        mantenimiento.to_dict()
    ), 201
# ==========================
# OBTENER
# ==========================
@mantenimientos_bp.route('/<int:id>', methods=['GET'])
def obtener(id):

    mantenimiento = (
        Mantenimiento.query
        .get_or_404(id)
    )

    return jsonify(
        mantenimiento.to_dict()
    )

# ==========================
# ACTUALIZAR
# ==========================
@mantenimientos_bp.route('/<int:id>', methods=['PUT'])
def actualizar(id):

    mantenimiento = (
        Mantenimiento.query
        .get_or_404(id)
    )

    data = request.get_json()

    for key, value in data.items():

        setattr(
            mantenimiento,
            key,
            value
        )

    db.session.commit()

    return jsonify(
        mantenimiento.to_dict()
    )

# ==========================
# ELIMINAR
# ==========================
@mantenimientos_bp.route('/<int:id>', methods=['DELETE'])
def eliminar(id):

    mantenimiento = (
        Mantenimiento.query
        .get_or_404(id)
    )

    db.session.delete(mantenimiento)

    db.session.commit()

    return jsonify({
        "message": "Eliminado correctamente"
    })

# ==========================
# VEHICULOS SIMPLE
# ==========================
@mantenimientos_bp.route(
    '/vehiculos-simple',
    methods=['GET']
)
def vehiculos_simple():

    vehiculos = Vehiculo.query.all()

    return jsonify([
        {
            "id": v.id,
            "placa": v.placa,
            "marca": v.marca,
            "modelo": v.modelo,
            "tipo": (
                v.tipo_vehiculo.nombre
                if v.tipo_vehiculo
                else None
            ),
            "km_estimado": v.km_estimado,
        "km_total": v.km_total,
        "km_gps": v.km_gps
        }
        for v in vehiculos
    ])

# ==========================
# PLAN ITEMS
# ==========================
@mantenimientos_bp.route(
    '/plan-items',
    methods=['GET']
)
def plan_items():

    items = PlanItem.query.all()

    return jsonify([
        p.to_dict()
        for p in items
    ])




# =========================
# MAQUINARIA MANTENIMIENTO
# =========================

@mantenimientos_bp.route(
    '/maquinaria-plan/<int:maquinaria_id>',
    methods=['GET']
)
def plan_por_maquinaria(maquinaria_id):

    maquinaria = Maquinaria.query.get_or_404(maquinaria_id)

    items = (
        MaquinariaPlanItem.query
        .filter_by(
            maquinaria_id=maquinaria_id,
            activo=True
        )
        .all()
    )

    resultado = []

    for item in items:

        ultimo = (
            MaquinariaMantenimiento.query
            .filter_by(
                maquinaria_id=maquinaria_id,
                plan_item_id=item.plan_item_id
            )
            .order_by(
                MaquinariaMantenimiento.fecha.desc()
            )
            .first()
        )

        resultado.append({
            "maquinaria": {
                "id": maquinaria.id,
                "codigo": maquinaria.codigo
            },
            "maquinaria_plan_item_id": item.id,
            "plan_item": item.plan_item.to_dict(),
            "ultimo_mantenimiento": (
                ultimo.to_dict()
                if ultimo else None
            ),
            "ultima_horas": item.ultima_horas,
            "estado": item.calcular_estado()
        })

    return jsonify(resultado)


# ==========================
# CREAR MANTENIMIENTO MAQUINARIA
# ==========================
@mantenimientos_bp.route('/maquinaria', methods=['POST'])
def crear_maquinaria():

    # =====================================
    # FORM DATA
    # =====================================
    maquinaria_id = request.form.get(
        'maquinaria_id',
        type=int
    )

    maquinaria_plan_item_id = request.form.get(
        'maquinaria_plan_item_id',
        type=int
    )

    horas = request.form.get(
        'horas',
        type=int
    )

    fecha = request.form.get('fecha')

    tipo = request.form.get('tipo')

    proveedor = request.form.get('proveedor')

    observaciones = request.form.get('observaciones')

    costo = request.form.get(
        'costo',
        type=float
    )

    lugar = request.form.get('lugar')

    responsable = request.form.get('responsable')

    # =====================================
    # VALIDACIONES
    # =====================================
    if not maquinaria_id:

        return jsonify({
            "error": "maquinaria_id requerido"
        }), 400

    if not maquinaria_plan_item_id:

        return jsonify({
            "error": "maquinaria_plan_item_id requerido"
        }), 400

    # =====================================
    # MAQUINARIA
    # =====================================
    maquinaria = Maquinaria.query.get_or_404(
        maquinaria_id
    )

    if horas is None:
        horas = maquinaria.horometro_actual

    # =====================================
    # PLAN
    # =====================================
    mpi = MaquinariaPlanItem.query.get_or_404(
        maquinaria_plan_item_id
    )

    # =====================================
    # SUBIR SOPORTE
    # =====================================
    soporte_path = None

    if 'soporte' in request.files:

        file = request.files['soporte']

        if file and allowed_file(file.filename):

            os.makedirs(
                UPLOAD_FOLDER,
                exist_ok=True
            )

            extension = (
                file.filename
                .rsplit('.', 1)[1]
                .lower()
            )

            filename = f"{uuid.uuid4()}.{extension}"

            filepath = os.path.join(
                UPLOAD_FOLDER,
                filename
            )

            file.save(filepath)

            soporte_path = (
                f"uploads/mantenimientos/{filename}"
            )

    # =====================================
    # CREAR MANTENIMIENTO
    # =====================================
    mantenimiento = MaquinariaMantenimiento(

        maquinaria_id=maquinaria.id,

        maquinaria_plan_item_id=mpi.id,

        plan_item_id=mpi.plan_item_id,

        fecha=datetime.strptime(
            fecha,
            "%Y-%m-%d"
        ).date() if fecha else None,

        horas=horas,

        tipo=tipo,

        proveedor=proveedor,

        observaciones=observaciones,

        soporte=soporte_path,
        costo=costo,

        lugar=lugar,

        responsable=responsable,
        
        completado=True
    )

    db.session.add(mantenimiento)

    # =====================================
    # ACTUALIZAR PLAN
    # =====================================
    mpi.ultima_horas = horas
    mpi.ultima_fecha = mantenimiento.fecha
    maquinaria.horometro_actual = horas
    
    # =====================================
# RESOLVER ALERTAS DEL ITEM EJECUTADO
# =====================================
    alertas = Alerta.query.filter(
        Alerta.tipo == "MANTENIMIENTO",
        Alerta.estado == "ACTIVA",
        Alerta.maquinaria_plan_item_id == mpi.id
    ).all()

    for alerta in alertas:

        alerta.estado = "RESUELTA"
        alerta.fecha_resolucion = datetime.utcnow()
        alerta.maquinaria_mantenimiento_id = mantenimiento.id

    db.session.commit()

# =====================================
# SOCKET TIEMPO REAL
# =====================================
    for alerta in alertas:

        socketio.emit(
            "alerta_resuelta",
            alerta.to_dict()
        )
    return jsonify(
        mantenimiento.to_dict()
    ), 201
    
    
    # ==========================
# MAQUINARIAS SIMPLE
# ==========================
@mantenimientos_bp.route(
    '/maquinarias-simple',
    methods=['GET']
)
def maquinarias_simple():

    maquinarias = (
        Maquinaria.query
        .filter_by(activo=True)
        .all()
    )

    return jsonify([
        {
            "id": m.id,
            "codigo": m.codigo,

            "tipo": (
                m.tipo_maquinaria.nombre
                if m.tipo_maquinaria
                else None
            ),

            "marca": m.marca,
            "modelo": m.modelo,

            "horometro_actual": (
                m.horometro_actual or 0
            ),

            "operador": m.operador,

            "estado": m.estado,

            "gps_id": m.gps_id
        }
        for m in maquinarias
    ])
    
    
# ==========================
# LISTAR MANTENIMIENTOS MAQUINARIA
# ==========================
@mantenimientos_bp.route('/maquinaria', methods=['GET'])
def listar_maquinaria():

    maquinaria_id = request.args.get(
        'maquinaria_id',
        type=int
    )

    tipo = request.args.get('tipo')

    desde = request.args.get('desde')

    hasta = request.args.get('hasta')

    query = MaquinariaMantenimiento.query

    # ==========================
    # FILTROS
    # ==========================
    if maquinaria_id:

        query = query.filter_by(
            maquinaria_id=maquinaria_id
        )

    if tipo:

        query = query.filter_by(
            tipo=tipo
        )

    if desde:

        query = query.filter(
            MaquinariaMantenimiento.fecha >= desde
        )

    if hasta:

        query = query.filter(
            MaquinariaMantenimiento.fecha <= hasta
        )

    mantenimientos = (
        query
        .order_by(
            desc(MaquinariaMantenimiento.fecha)
        )
        .all()
    )

    return jsonify([
        m.to_dict()
        for m in mantenimientos
    ])
    
    
    
# ==========================
# OBTENER MANTENIMIENTO MAQUINARIA
# ==========================
@mantenimientos_bp.route(
    '/maquinaria/<int:id>',
    methods=['GET']
)
def obtener_maquinaria(id):

    mantenimiento = (
        MaquinariaMantenimiento.query
        .get_or_404(id)
    )

    return jsonify(
        mantenimiento.to_dict()
    )
    
    
# ==========================
# ACTUALIZAR MANTENIMIENTO MAQUINARIA
# ==========================
@mantenimientos_bp.route(
    '/maquinaria/<int:id>',
    methods=['PUT']
)
def actualizar_maquinaria(id):

    mantenimiento = (
        MaquinariaMantenimiento.query
        .get_or_404(id)
    )

    data = request.get_json()

    for key, value in data.items():

        setattr(
            mantenimiento,
            key,
            value
        )

    db.session.commit()

    return jsonify(
        mantenimiento.to_dict()
    )
    
    
# ==========================
# ELIMINAR MANTENIMIENTO MAQUINARIA
# ==========================
@mantenimientos_bp.route(
    '/maquinaria/<int:id>',
    methods=['DELETE']
)
def eliminar_maquinaria(id):

    mantenimiento = (
        MaquinariaMantenimiento.query
        .get_or_404(id)
    )

    db.session.delete(mantenimiento)

    db.session.commit()

    return jsonify({
        "message": "Mantenimiento de maquinaria eliminado correctamente"
    })