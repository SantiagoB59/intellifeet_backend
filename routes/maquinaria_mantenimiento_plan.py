from flask import Blueprint, request, jsonify
from models import (
    db,
    Maquinaria,
    MaquinariaPlanItem,
    PlanItem,
    MaquinariaMantenimiento
)

from datetime import date

maquinaria_plan_bp = Blueprint(
    'maquinaria_plan',
    __name__
)

# =========================================
# CREAR PLAN
# =========================================
@maquinaria_plan_bp.route(
    '/maquinaria/<int:maquinaria_id>/plan',
    methods=['POST']
)
def crear_plan(maquinaria_id):

    data = request.get_json()

    maquinaria = Maquinaria.query.get_or_404(maquinaria_id)

    mpi = MaquinariaPlanItem(
        maquinaria_id=maquinaria.id,
        plan_item_id=data.get('plan_item_id'),

        frecuencia_horas=data.get('frecuencia_horas'),

        alerta_horas=data.get('alerta_horas', 20),

        activo=True
    )

    db.session.add(mpi)
    db.session.commit()

    return jsonify(mpi.to_dict()), 201


# =========================================
# OBTENER PLANES
# =========================================
@maquinaria_plan_bp.route(
    '/maquinaria/<int:maquinaria_id>/plan',
    methods=['GET']
)
def obtener_planes(maquinaria_id):

    items = MaquinariaPlanItem.query.filter_by(
        maquinaria_id=maquinaria_id,
        activo=True
    ).all()

    return jsonify([
        i.to_dict()
        for i in items
    ])


# =========================================
# ALERTAS
# =========================================
@maquinaria_plan_bp.route(
    '/maquinaria/alertas',
    methods=['GET']
)
def alertas():

    items = MaquinariaPlanItem.query.filter_by(
        activo=True
    ).all()

    response = []

    for i in items:

        restantes = i.calcular_horas_restantes()

        if restantes is None:
            continue

        if restantes <= i.alerta_horas:

            response.append({
                "maquinaria_id": i.maquinaria_id,

                "codigo": (
                    i.maquinaria.codigo
                    if i.maquinaria else None
                ),

                "estado": i.calcular_estado(),

                "horometro_actual": (
                    i.maquinaria.horometro_actual
                    if i.maquinaria else 0
                ),

                "horas_programadas": i.calcular_horas_programadas(),

                "horas_restantes": restantes,

                "plan_item": (
                    i.plan_item.to_dict()
                    if i.plan_item else None
                )
            })

    return jsonify(response)


# =========================================
# COMPLETAR MANTENIMIENTO
# =========================================
@maquinaria_plan_bp.route(
    '/maquinaria/plan/<int:id>/completar',
    methods=['PUT']
)
def completar(id):

    mpi = MaquinariaPlanItem.query.get_or_404(id)

    maquinaria = Maquinaria.query.get(
        mpi.maquinaria_id
    )

    horas_actuales = maquinaria.horometro_actual or 0

    mantenimiento = MaquinariaMantenimiento(
        maquinaria_id=mpi.maquinaria_id,

        maquinaria_plan_item_id=mpi.id,

        plan_item_id=mpi.plan_item_id,

        fecha=date.today(),

        horas=horas_actuales,

        tipo=mpi.plan_item.tipo
    )

    db.session.add(mantenimiento)

    # 🔥 ACTUALIZAR CICLO
    mpi.ultima_horas = horas_actuales
    mpi.ultima_fecha = date.today()

    db.session.commit()

    return jsonify({
        "message": "Mantenimiento registrado"
    })