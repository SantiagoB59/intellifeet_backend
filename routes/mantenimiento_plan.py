from flask import Blueprint, request, jsonify
from models import (
    db,
    Vehiculo,
    VehiculoPlanItem,
    PlanItem,
    Mantenimiento
)

from datetime import date

mantenimiento_plan_bp = Blueprint(
    'mantenimiento_plan',
    __name__
)

# =========================================
# 📌 1. CREAR PLAN VEHÍCULO
# =========================================
@mantenimiento_plan_bp.route(
    '/vehiculos/<int:vehiculo_id>/plan',
    methods=['POST']
)
def crear_plan_vehiculo(vehiculo_id):

    data = request.get_json()

    vehiculo = Vehiculo.query.get_or_404(
        vehiculo_id
    )
    
    # =====================================
# 🔥 INICIALIZAR CONTROL GPS
# =====================================

    if vehiculo.km_base_control is None:
        vehiculo.km_base_control = vehiculo.km_actual or 0

    if vehiculo.km_gps_inicial is None:
        vehiculo.km_gps_inicial = vehiculo.km_gps or 0

    plan_item_id = data.get('plan_item_id')

    if not plan_item_id:
        return jsonify({
            "error": "plan_item_id requerido"
        }), 400

    plan_item = PlanItem.query.get_or_404(
        plan_item_id
    )

    vpi = VehiculoPlanItem(

        vehiculo_id=vehiculo.id,

        plan_item_id=plan_item.id,

        tipo_control=(
            data.get('tipo_control')
            or plan_item.tipo_control
        ),

        frecuencia_valor=(
            data.get('frecuencia_valor')
            or plan_item.frecuencia_valor
        ),

        alerta_valor=(
            data.get('alerta_valor')
            or plan_item.alerta_valor
        ),

        ultimo_km=(
            vehiculo.km_actual or 0
        ),
        ultima_fecha=date.today(),

        activo=True
    )

    db.session.add(vpi)
    db.session.commit()

    return jsonify(
        vpi.to_dict()
    ), 201


# =========================================
# 📌 2. OBTENER PLAN VEHÍCULO
# =========================================
@mantenimiento_plan_bp.route(
    '/vehiculos/<int:vehiculo_id>/plan',
    methods=['GET']
)
def get_plan_vehiculo(vehiculo_id):

    Vehiculo.query.get_or_404(
        vehiculo_id
    )

    items = VehiculoPlanItem.query.filter_by(
        vehiculo_id=vehiculo_id,
        activo=True
    ).all()

    return jsonify([
        i.to_dict()
        for i in items
    ])


# =========================================
# 📌 3. ALERTAS
# =========================================
@mantenimiento_plan_bp.route(
    '/mantenimientos/alertas',
    methods=['GET']
)
def alertas():

    items = VehiculoPlanItem.query.filter_by(
        activo=True
    ).all()

    alertas = []

    for item in items:

        estado = item.calcular_estado()

        if estado in ['PENDIENTE', 'VENCIDO']:

            data = item.to_dict()

            alertas.append({

                "vehiculo_id": item.vehiculo_id,

                "placa": (
                    item.vehiculo.placa
                    if item.vehiculo else None
                ),

                "estado": estado,

                "tipo_control": item.tipo_control,

                "restante": data.get(
                    'restante'
                ),

                "programado": data.get(
                    'programado'
                ),

                "plan_item": data.get(
                    'plan_item'
                )
            })

    return jsonify(alertas)


# =========================================
# 📌 4. COMPLETAR MANTENIMIENTO
# =========================================
@mantenimiento_plan_bp.route(
    '/plan/<int:id>/completar',
    methods=['PUT']
)
def completar(id):

    vpi = VehiculoPlanItem.query.get_or_404(
        id
    )

    vehiculo = Vehiculo.query.get(
        vpi.vehiculo_id
    )

    km_actual = (
        vehiculo.km_actual or 0
    )

    mantenimiento = Mantenimiento(

        vehiculo_id=vpi.vehiculo_id,

        plan_item_id=vpi.plan_item_id,

        vehiculo_plan_item_id=vpi.id,

        fecha=date.today(),

        km=km_actual,

        tipo=(
            vpi.plan_item.tipo_mantenimiento
            if vpi.plan_item else None
        )
    )

    db.session.add(
        mantenimiento
    )

    # =====================================
    # 🔥 REINICIAR CICLO
    # =====================================

    if vpi.tipo_control == 'KM':
        vpi.ultimo_km = km_actual

    if vpi.tipo_control == 'DIAS':
        vpi.ultima_fecha = date.today()

    db.session.commit()

    return jsonify({
        "msg": "Mantenimiento registrado correctamente"
    })


# =========================================
# 📌 5. PLAN ITEMS CATÁLOGO
# =========================================
@mantenimiento_plan_bp.route(
    '/plan-items',
    methods=['GET']
)
def get_plan_items():

    items = PlanItem.query.filter_by(
        activo=True
    ).all()

    return jsonify([{

        "id": i.id,

        "sistema": i.sistema,

        "nombre": i.nombre,

        "descripcion": i.descripcion,

        "tipo_mantenimiento": (
            i.tipo_mantenimiento
        ),

        "tipo_control": (
            i.tipo_control
        ),

        "frecuencia_valor": (
            i.frecuencia_valor
        ),

        "alerta_valor": (
            i.alerta_valor
        ),

        "obligatorio": (
            i.obligatorio
        )

    } for i in items])