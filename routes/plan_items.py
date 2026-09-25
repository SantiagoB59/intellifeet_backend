from flask import Blueprint, request, jsonify

from models import (
    db,
    PlanItem,
    PlanItemActividad,
    TipoVehiculo,
    TipoMaquinaria
)


plan_items_bp = Blueprint(
    'plan_items',
    __name__
)


# =========================================================
# LISTAR
# =========================================================

@plan_items_bp.route('/plan-items', methods=['GET'])
def listar_plan_items():

    try:

        # =====================================================
        # PARÁMETROS
        # =====================================================

        tipo_activo = request.args.get('tipo_activo')

        tipo_vehiculo_id = request.args.get(
            'tipo_vehiculo_id',
            type=int
        )

        tipo_maquinaria_id = request.args.get(
            'tipo_maquinaria_id',
            type=int
        )

        print("========================================")
        print("LISTANDO PLAN ITEMS")
        print("tipo_activo:", tipo_activo)
        print("tipo_vehiculo_id:", tipo_vehiculo_id)
        print("tipo_maquinaria_id:", tipo_maquinaria_id)
        print("========================================")

        # =====================================================
        # CONSULTA BASE
        # =====================================================

        query = PlanItem.query.filter(
            PlanItem.activo == True
        )

        # =====================================================
        # VEHÍCULO
        # =====================================================

        if tipo_activo == 'VEHICULO':

            query = query.filter(
                PlanItem.tipo_activo == 'VEHICULO'
            )

            # Si recibimos tipo específico
            if tipo_vehiculo_id is not None:

                query = query.filter(
                    db.or_(
                        PlanItem.tipo_vehiculo_id == tipo_vehiculo_id,
                        PlanItem.tipo_vehiculo_id.is_(None)
                    )
                )

        # =====================================================
        # MAQUINARIA
        # =====================================================

        elif tipo_activo == 'MAQUINARIA':

            query = query.filter(
                PlanItem.tipo_activo == 'MAQUINARIA'
            )

            # Si recibimos tipo específico
            if tipo_maquinaria_id is not None:

                query = query.filter(
                    db.or_(
                        PlanItem.tipo_maquinaria_id == tipo_maquinaria_id,
                        PlanItem.tipo_maquinaria_id.is_(None)
                    )
                )

        # =====================================================
        # SI NO VIENE TIPO
        # =====================================================

        else:

            # Comportamiento anterior:
            # devolver todos los plan items activos.

            pass

        # =====================================================
        # ORDEN
        # =====================================================

        planes = query.order_by(
            PlanItem.sistema.asc(),
            PlanItem.nombre.asc()
        ).all()

        print(
            "PLAN ITEMS ENCONTRADOS:",
            len(planes)
        )

        # =====================================================
        # RESPUESTA
        # =====================================================

        return jsonify([
            plan.to_dict()
            for plan in planes
        ]), 200

    except Exception as e:

        import traceback

        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
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
    
    # =====================================================
    # VALIDAR TIPO ESPECÍFICO DE ACTIVO
    # =====================================================

    tipo_vehiculo_id = data.get(
        'tipo_vehiculo_id'
    )

    tipo_maquinaria_id = data.get(
        'tipo_maquinaria_id'
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

    
        if tipo_activo == 'VEHICULO':

            # Un plan de vehículo no puede tener
            # tipo de maquinaria
            tipo_maquinaria_id = None

            if tipo_vehiculo_id is not None:

                tipo_vehiculo = TipoVehiculo.query.get(
                    tipo_vehiculo_id
                )

                if not tipo_vehiculo:
                    return jsonify({
                        "error": (
                            "El tipo de vehículo "
                            "no existe"
                        )
                    }), 400

        elif tipo_activo == 'MAQUINARIA':

            # Un plan de maquinaria no puede tener
            # tipo de vehículo
            tipo_vehiculo_id = None

            if tipo_maquinaria_id is not None:

                tipo_maquinaria = TipoMaquinaria.query.get(
                    tipo_maquinaria_id
                )

                if not tipo_maquinaria:
                    return jsonify({
                        "error": (
                            "El tipo de maquinaria "
                            "no existe"
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

        tipo_vehiculo_id=tipo_vehiculo_id,

        tipo_maquinaria_id=tipo_maquinaria_id,

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
    # TIPO ESPECÍFICO DE ACTIVO
    # =====================================================

    nuevo_tipo_vehiculo_id = data.get(
        'tipo_vehiculo_id',
        item.tipo_vehiculo_id
    )

    nuevo_tipo_maquinaria_id = data.get(
        'tipo_maquinaria_id',
        item.tipo_maquinaria_id
    )

    # -----------------------------------------------------
    # VEHÍCULO
    # -----------------------------------------------------

    if nuevo_tipo_activo == 'VEHICULO':

        nuevo_tipo_maquinaria_id = None

        if nuevo_tipo_vehiculo_id is not None:

            tipo_vehiculo = TipoVehiculo.query.get(
                nuevo_tipo_vehiculo_id
            )

            if not tipo_vehiculo:
                return jsonify({
                    "error": (
                        "El tipo de vehículo "
                        "no existe"
                    )
                }), 400

    # -----------------------------------------------------
    # MAQUINARIA
    # -----------------------------------------------------

    elif nuevo_tipo_activo == 'MAQUINARIA':

        nuevo_tipo_vehiculo_id = None

        if nuevo_tipo_maquinaria_id is not None:

            tipo_maquinaria = TipoMaquinaria.query.get(
                nuevo_tipo_maquinaria_id
            )

            if not tipo_maquinaria:
                return jsonify({
                    "error": (
                        "El tipo de maquinaria "
                        "no existe"
                    )
                }), 400

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

    item.tipo_vehiculo_id = (
        nuevo_tipo_vehiculo_id
    )

    item.tipo_maquinaria_id = (
        nuevo_tipo_maquinaria_id
    )
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
    
    
# =========================================================
# TIPOS DE VEHÍCULO
# =========================================================
@plan_items_bp.route(
    '/plan-items/tipos-vehiculo',
    methods=['GET']
)
def listar_tipos_vehiculo():

    try:
        tipos = TipoVehiculo.query.order_by(
            TipoVehiculo.nombre.asc()
        ).all()

        return jsonify([
            tipo.to_dict()
            for tipo in tipos
        ]), 200

    except Exception as e:
        import traceback
        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
# =========================================================
# TIPOS DE MAQUINARIA
# =========================================================

@plan_items_bp.route(
    '/plan-items/tipos-maquinaria',
    methods=['GET']
)
def listar_tipos_maquinaria():

    tipos = TipoMaquinaria.query.order_by(
        TipoMaquinaria.nombre.asc()
    ).all()

    return jsonify([
        {
            "id": tipo.id,
            "nombre": tipo.nombre
        }
        for tipo in tipos
    ])