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

    horometro_base = int(
        maquinaria.horometro_actual or 0
    )

    frecuencia_horas = data.get('frecuencia_horas')

    if not frecuencia_horas:
        return jsonify({
            "error": "frecuencia_horas es requerida"
        }), 400

    mpi = MaquinariaPlanItem(
        maquinaria_id=maquinaria.id,

        plan_item_id=data.get('plan_item_id'),

        frecuencia_horas=int(frecuencia_horas),

        alerta_horas=int(
            data.get('alerta_horas', 20)
        ),

        horas_base=horometro_base,

        ultima_horas=horometro_base,

        ultima_fecha=date.today(),

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
# =========================================
# COMPLETAR MANTENIMIENTO
# =========================================
@maquinaria_plan_bp.route(
    '/maquinaria/plan/<int:id>/completar',
    methods=['PUT']
)
def completar(id):

    mpi = MaquinariaPlanItem.query.get_or_404(id)

    maquinaria = Maquinaria.query.get_or_404(
        mpi.maquinaria_id
    )

    # =========================================
    # DATOS RECIBIDOS
    # =========================================

    data = request.get_json() or {}

    horas_programadas = data.get(
        'horas_programadas'
    )

    # =========================================
    # VALIDAR HORAS PROGRAMADAS
    # =========================================

    if horas_programadas is None:

        # Si no viene desde frontend,
        # buscamos la primera ocurrencia pendiente
        ocurrencias = mpi.calcular_ocurrencias()

        realizadas = {
            m.horas_programadas
            for m in MaquinariaMantenimiento.query.filter_by(
                maquinaria_id=mpi.maquinaria_id,
                maquinaria_plan_item_id=mpi.id,
                completado=True
            ).all()
            if m.horas_programadas is not None
        }

        pendientes = [
            h for h in ocurrencias
            if h not in realizadas
        ]

        if not pendientes:

            return jsonify({
                "error": "No hay ocurrencias pendientes para completar"
            }), 400

        horas_programadas = pendientes[0]

    horas_programadas = int(horas_programadas)

    # =========================================
    # VALIDAR QUE LA OCURRENCIA PERTENEZCA AL PLAN
    # =========================================

    ocurrencias = mpi.calcular_ocurrencias()

    if horas_programadas not in ocurrencias:

        return jsonify({
            "error": (
                "La hora programada no corresponde "
                "a una ocurrencia válida del plan"
            )
        }), 400

    # =========================================
    # VERIFICAR SI YA FUE COMPLETADA
    # =========================================

    existente = MaquinariaMantenimiento.query.filter_by(
        maquinaria_id=mpi.maquinaria_id,
        maquinaria_plan_item_id=mpi.id,
        horas_programadas=horas_programadas,
        completado=True
    ).first()

    if existente:

        return jsonify({
            "error": "Esta ocurrencia ya fue completada",
            "mantenimiento": existente.to_dict()
        }), 409

    # =========================================
    # HORAS REALES
    # =========================================

    horas_actuales = (
        maquinaria.horometro_actual or 0
    )

    # =========================================
    # CREAR MANTENIMIENTO
    # =========================================

    mantenimiento = MaquinariaMantenimiento(

        maquinaria_id=mpi.maquinaria_id,

        maquinaria_plan_item_id=mpi.id,

        plan_item_id=mpi.plan_item_id,

        fecha=date.today(),

        # Horas reales en las que se hizo
        horas=horas_actuales,

        # Horas en las que estaba programado
        horas_programadas=horas_programadas,

        tipo=(
            mpi.plan_item.tipo
            if mpi.plan_item
            else None
        ),

        completado=True
    )

    db.session.add(mantenimiento)

    # =========================================
    # ACTUALIZAR ÚLTIMA EJECUCIÓN
    # =========================================

    mpi.ultima_horas = horas_actuales
    mpi.ultima_fecha = date.today()

    # IMPORTANTE:
    # NO modificar horas_base
    #
    # horas_base sigue siendo la hora
    # desde la cual nació el plan.

    db.session.commit()

    # =========================================
    # RESPUESTA
    # =========================================

    return jsonify({
        "message": "Mantenimiento registrado",
        "mantenimiento": mantenimiento.to_dict()
    }), 201