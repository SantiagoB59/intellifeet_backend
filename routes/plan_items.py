from flask import Blueprint, request, jsonify

from models import (
    db,
    PlanItem,
    PlanItemActividad
)


plan_items_bp = Blueprint(
    'plan_items',
    __name__
)


# =========================================================
# LISTAR
# =========================================================

@plan_items_bp.route(
    '/plan-items',
    methods=['GET']
)
def listar_plan_items():

    items = PlanItem.query.order_by(
        PlanItem.id.desc()
    ).all()

    return jsonify([
        i.to_dict()
        for i in items
    ])


# =========================================================
# OBTENER UNO
# =========================================================

@plan_items_bp.route(
    '/plan-items/<int:id>',
    methods=['GET']
)
def obtener_plan_item(id):

    item = PlanItem.query.get_or_404(id)

    return jsonify(
        item.to_dict()
    )


# =========================================================
# CREAR
# =========================================================

@plan_items_bp.route(
    '/plan-items',
    methods=['POST']
)
def crear_plan_item():

    data = request.get_json() or {}

    # =====================================================
    # DATOS PRINCIPALES
    # =====================================================

    tipo_activo = data.get(
        'tipo_activo',
        'VEHICULO'
    )

    tipo_control = data.get(
        'tipo_control',
        'KM'
    )

    # =====================================================
    # VALIDACIONES
    # =====================================================

    if not data.get('sistema'):
        return jsonify({
            "error": "sistema es requerido"
        }), 400

    if not data.get('nombre'):
        return jsonify({
            "error": "nombre es requerido"
        }), 400

    if tipo_activo not in [
        'VEHICULO',
        'MAQUINARIA'
    ]:
        return jsonify({
            "error": "tipo_activo inválido"
        }), 400

    # =====================================================
    # VALIDAR TIPO DE CONTROL
    # =====================================================

    if tipo_activo == 'VEHICULO':

        if tipo_control not in [
            'KM',
            'DIAS'
        ]:
            return jsonify({
                "error": (
                    "Para vehículos el tipo de control "
                    "debe ser KM o DIAS"
                )
            }), 400

    if tipo_activo == 'MAQUINARIA':

        if tipo_control != 'HORAS':
            return jsonify({
                "error": (
                    "Para maquinaria el tipo de control "
                    "debe ser HORAS"
                )
            }), 400

    # =====================================================
    # CREAR PLAN ITEM
    # =====================================================

    item = PlanItem(

        sistema=data.get(
            'sistema'
        ),

        nombre=data.get(
            'nombre'
        ),

        descripcion=data.get(
            'descripcion'
        ),

        tipo_mantenimiento=data.get(
            'tipo_mantenimiento',
            'PREVENTIVO'
        ),

        tipo_activo=tipo_activo,

        tipo_control=tipo_control,

        frecuencia_valor=data.get(
            'frecuencia_valor'
        ),

        alerta_valor=data.get(
            'alerta_valor'
        ),

        obligatorio=data.get(
            'obligatorio',
            True
        ),

        activo=data.get(
            'activo',
            True
        )
    )

    db.session.add(item)

    # =====================================================
    # ACTIVIDADES DE MAQUINARIA
    # =====================================================

    actividades = data.get(
        'actividades',
        []
    )

    if tipo_activo == 'MAQUINARIA':

        for index, actividad in enumerate(
            actividades,
            start=1
        ):

            if not isinstance(
                actividad,
                dict
            ):
                continue

            nombre_actividad = (
                actividad.get('nombre')
            )

            if not nombre_actividad:
                continue

            nueva_actividad = PlanItemActividad(

                nombre=nombre_actividad,

                descripcion=actividad.get(
                    'descripcion'
                ),

                obligatorio=actividad.get(
                    'obligatorio',
                    True
                ),

                orden=actividad.get(
                    'orden',
                    index
                ),

                activo=actividad.get(
                    'activo',
                    True
                )
            )

            item.actividades.append(
                nueva_actividad
            )

    # =====================================================
    # GUARDAR
    # =====================================================

    db.session.commit()

    return jsonify(
        item.to_dict()
    ), 201


# =========================================================
# ACTUALIZAR
# =========================================================

@plan_items_bp.route(
    '/plan-items/<int:id>',
    methods=['PUT']
)
def actualizar_plan_item(id):

    item = PlanItem.query.get_or_404(
        id
    )

    data = request.get_json() or {}

    # =====================================================
    # DATOS PRINCIPALES
    # =====================================================

    nuevo_tipo_activo = data.get(
        'tipo_activo',
        item.tipo_activo
    )

    nuevo_tipo_control = data.get(
        'tipo_control',
        item.tipo_control
    )

    # =====================================================
    # VALIDACIONES
    # =====================================================

    if nuevo_tipo_activo not in [
        'VEHICULO',
        'MAQUINARIA'
    ]:
        return jsonify({
            "error": "tipo_activo inválido"
        }), 400

    if nuevo_tipo_activo == 'VEHICULO':

        if nuevo_tipo_control not in [
            'KM',
            'DIAS'
        ]:
            return jsonify({
                "error": (
                    "Para vehículos el tipo de control "
                    "debe ser KM o DIAS"
                )
            }), 400

    if nuevo_tipo_activo == 'MAQUINARIA':

        if nuevo_tipo_control != 'HORAS':
            return jsonify({
                "error": (
                    "Para maquinaria el tipo de control "
                    "debe ser HORAS"
                )
            }), 400

    # =====================================================
    # ACTUALIZAR CAMPOS
    # =====================================================

    item.sistema = data.get(
        'sistema',
        item.sistema
    )

    item.nombre = data.get(
        'nombre',
        item.nombre
    )

    item.descripcion = data.get(
        'descripcion',
        item.descripcion
    )

    item.tipo_mantenimiento = data.get(
        'tipo_mantenimiento',
        item.tipo_mantenimiento
    )

    item.tipo_activo = nuevo_tipo_activo

    item.tipo_control = nuevo_tipo_control

    item.frecuencia_valor = data.get(
        'frecuencia_valor',
        item.frecuencia_valor
    )

    item.alerta_valor = data.get(
        'alerta_valor',
        item.alerta_valor
    )

    item.obligatorio = data.get(
        'obligatorio',
        item.obligatorio
    )

    if 'activo' in data:

        item.activo = data.get(
            'activo'
        )

    # =====================================================
    # ACTIVIDADES
    # =====================================================

    if nuevo_tipo_activo == 'MAQUINARIA':

        actividades = data.get(
            'actividades',
            []
        )

        # ---------------------------------------------
        # ELIMINAMOS LAS ACTIVIDADES ACTUALES
        # ---------------------------------------------

        item.actividades.clear()

        # ---------------------------------------------
        # CREAMOS LAS NUEVAS
        # ---------------------------------------------

        for index, actividad in enumerate(
            actividades,
            start=1
        ):

            if not isinstance(
                actividad,
                dict
            ):
                continue

            nombre_actividad = (
                actividad.get('nombre')
            )

            if not nombre_actividad:
                continue

            nueva_actividad = PlanItemActividad(

                nombre=nombre_actividad,

                descripcion=actividad.get(
                    'descripcion'
                ),

                obligatorio=actividad.get(
                    'obligatorio',
                    True
                ),

                orden=actividad.get(
                    'orden',
                    index
                ),

                activo=actividad.get(
                    'activo',
                    True
                )
            )

            item.actividades.append(
                nueva_actividad
            )

    else:

        # =================================================
        # SI CAMBIA A VEHÍCULO
        # NO DEBE CONSERVAR ACTIVIDADES
        # =================================================

        item.actividades.clear()

    # =====================================================
    # GUARDAR
    # =====================================================

    db.session.commit()

    return jsonify(
        item.to_dict()
    )


# =========================================================
# ELIMINAR
# =========================================================

@plan_items_bp.route(
    '/plan-items/<int:id>',
    methods=['DELETE']
)
def eliminar_plan_item(id):

    item = PlanItem.query.get_or_404(
        id
    )

    item.activo = False

    db.session.commit()

    return jsonify({
        "msg": "Plan eliminado"
    })