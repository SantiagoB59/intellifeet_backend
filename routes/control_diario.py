# ============================================================
# INTELLIFEET
# RUTAS - CONTROL DIARIO
# ============================================================

from flask import (
    Blueprint,
    request,
    jsonify,
    send_file
)
from flask_jwt_extended import jwt_required, get_jwt_identity

from services.control_diario_service import (
    obtener_usuario,
    obtener_activos_operador,
    crear_control_diario,
    obtener_controles_operador,
    obtener_control_diario,
    obtener_controles_admin,
    validar_control_diario,
    rechazar_control_diario,
    validar_rol_admin,
    generar_excel_controles_diarios
)


# ============================================================
# BLUEPRINT
# ============================================================

control_diario_bp = Blueprint(
    "control_diario",
    __name__
)


# ============================================================
# OBTENER USUARIO ACTUAL
# ============================================================

def obtener_usuario_actual():
    """
    Obtiene el usuario autenticado a partir del JWT.

    El JWT de IntelliFeet tiene esta estructura:

    {
        "id": 11,
        "username": "operadorpajarita001",
        "rol": "operador"
    }
    """

    identity = get_jwt_identity()

    if not identity:
        return None

    # --------------------------------------------------------
    # El JWT devuelve un diccionario
    # --------------------------------------------------------

    if isinstance(identity, dict):

        usuario_id = identity.get("id")

    else:

        # ----------------------------------------------------
        # Compatibilidad por si algún token antiguo
        # devuelve directamente el ID
        # ----------------------------------------------------

        usuario_id = identity

    if not usuario_id:
        return None

    try:

        usuario_id = int(usuario_id)

    except (TypeError, ValueError):

        return None

    return obtener_usuario(
        usuario_id
    )


# ============================================================
# ACTIVOS ASIGNADOS AL OPERADOR
# ============================================================

@control_diario_bp.get("/mis-activos")
@jwt_required()
def mis_activos():

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    try:

        activos = obtener_activos_operador(
            usuario.id
        )

        return jsonify(
            activos
        ), 200

    except Exception as e:

        return jsonify({
            "error": (
                "Error al consultar "
                "los activos asignados"
            ),
            "detail": str(e)
        }), 500


# ============================================================
# CREAR CONTROL DIARIO
# ============================================================

@control_diario_bp.post("")
@jwt_required()
def crear_control():

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    try:

        control = crear_control_diario(

            usuario_id=usuario.id,

            fecha_control=request.form.get(
                "fecha"
            ),

            vehiculo_id=request.form.get(
                "vehiculo_id"
            ),

            maquinaria_id=request.form.get(
                "maquinaria_id"
            ),

            archivo=request.files.get(
                "archivo"
            ),

            observaciones=request.form.get(
                "observaciones"
            )
        )

        return jsonify({

            "message": (
                "Control diario cargado "
                "correctamente"
            ),

            "control": control.to_dict()

        }), 201

    except PermissionError as e:

        return jsonify({
            "error": str(e)
        }), 403

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({

            "error": (
                "Error al crear el "
                "control diario"
            ),

            "detail": str(e)

        }), 500


# ============================================================
# MIS CONTROLES
# ============================================================

@control_diario_bp.get("/mis-controles")
@jwt_required()
def mis_controles():

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    fecha_desde = request.args.get(
        "fecha_desde"
    )

    fecha_hasta = request.args.get(
        "fecha_hasta"
    )

    try:

        controles = obtener_controles_operador(

            usuario_id=usuario.id,

            fecha_desde=fecha_desde,

            fecha_hasta=fecha_hasta

        )

        return jsonify([

            control.to_dict()

            for control in controles

        ]), 200

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({

            "error": (
                "Error al consultar "
                "los controles"
            ),

            "detail": str(e)

        }), 500


# ============================================================
# VER UN CONTROL
# ============================================================

@control_diario_bp.get("/<int:control_id>")
@jwt_required()
def obtener_control(control_id):

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    control = obtener_control_diario(
        control_id
    )

    if not control:

        return jsonify({
            "error": "Control no encontrado"
        }), 404

    # --------------------------------------------------------
    # ADMIN / SUPERVISOR
    # --------------------------------------------------------

    if validar_rol_admin(usuario):

        return jsonify(
            control.to_dict()
        ), 200

    # --------------------------------------------------------
    # OPERADOR
    # --------------------------------------------------------

    if control.usuario_id != usuario.id:

        return jsonify({

            "error": (
                "No tiene permiso para "
                "ver este control"
            )

        }), 403

    return jsonify(
        control.to_dict()
    ), 200


# ============================================================
# LISTADO ADMINISTRATIVO
# ============================================================

@control_diario_bp.get("")
@jwt_required()
def listar_controles():

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    if not validar_rol_admin(usuario):

        return jsonify({

            "error": (
                "No tiene permisos para "
                "consultar este módulo"
            )

        }), 403

    try:

        controles = obtener_controles_admin(

            mes=request.args.get(
                "mes"
            ),

            anio=request.args.get(
                "anio"
            ),

            vehiculo_id=request.args.get(
                "vehiculo_id"
            ),

            maquinaria_id=request.args.get(
                "maquinaria_id"
            ),

            usuario_id=request.args.get(
                "usuario_id"
            ),

            estado=request.args.get(
                "estado"
            ),

            fecha_desde=request.args.get(
                "fecha_desde"
            ),

            fecha_hasta=request.args.get(
                "fecha_hasta"
            )

        )

        return jsonify({

            "total": len(controles),

            "controles": [

                control.to_dict()

                for control in controles

            ]

        }), 200

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({

            "error": (
                "Error al consultar "
                "los controles"
            ),

            "detail": str(e)

        }), 500




# ============================================================
# EXPORTAR EXCEL CONSOLIDADO
# ============================================================

@control_diario_bp.get(
    "/exportar-excel"
)
@jwt_required()
def exportar_excel():

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    # --------------------------------------------------------
    # VALIDAR ROL
    # --------------------------------------------------------

    if not validar_rol_admin(usuario):

        return jsonify({
            "error": (
                "No tiene permisos para "
                "exportar controles"
            )
        }), 403

    try:

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------

        mes = request.args.get(
            "mes"
        )

        anio = request.args.get(
            "anio"
        )

        vehiculo_id = request.args.get(
            "vehiculo_id"
        )

        maquinaria_id = request.args.get(
            "maquinaria_id"
        )

        usuario_id = request.args.get(
            "usuario_id"
        )

        estado = request.args.get(
            "estado"
        )

        fecha_desde = request.args.get(
            "fecha_desde"
        )

        fecha_hasta = request.args.get(
            "fecha_hasta"
        )

        # ----------------------------------------------------
        # OBTENER LOS MISMOS CONTROLES DEL LISTADO
        # ----------------------------------------------------

        controles = obtener_controles_admin(

            mes=mes,

            anio=anio,

            vehiculo_id=vehiculo_id,

            maquinaria_id=maquinaria_id,

            usuario_id=usuario_id,

            estado=estado,

            fecha_desde=fecha_desde,

            fecha_hasta=fecha_hasta

        )

        # ----------------------------------------------------
        # BASE URL
        # ----------------------------------------------------

        base_url = request.host_url.rstrip("/")

        # ----------------------------------------------------
        # GENERAR EXCEL
        # ----------------------------------------------------

        archivo = generar_excel_controles_diarios(

            controles=controles,

            base_url=base_url

        )

        # ----------------------------------------------------
        # NOMBRE DEL ARCHIVO
        # ----------------------------------------------------

        if mes and anio:

            try:

                nombre_archivo = (
                    f"CONTROL_DIARIO_"
                    f"{int(anio)}_"
                    f"{int(mes):02d}.xlsx"
                )

            except (TypeError, ValueError):

                nombre_archivo = (
                    "CONTROL_DIARIO_CONSOLIDADO.xlsx"
                )

        elif anio:

            nombre_archivo = (
                f"CONTROL_DIARIO_{anio}.xlsx"
            )

        else:

            nombre_archivo = (
                "CONTROL_DIARIO_CONSOLIDADO.xlsx"
            )

        # ----------------------------------------------------
        # RESPUESTA
        # ----------------------------------------------------

        return send_file(

            archivo,

            as_attachment=True,

            download_name=nombre_archivo,

            mimetype=(
                "application/vnd.openxmlformats-"
                "officedocument.spreadsheetml.sheet"
            )

        )

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({

            "error": (
                "Error al generar "
                "el Excel"
            ),

            "detail": str(e)

        }), 500
# ============================================================
# VALIDAR CONTROL
# ============================================================

@control_diario_bp.put(
    "/<int:control_id>/validar"
)
@jwt_required()
def validar_control(control_id):

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    if not validar_rol_admin(usuario):

        return jsonify({

            "error": (
                "No tiene permisos para "
                "validar controles"
            )

        }), 403

    data = request.get_json(
        silent=True
    ) or {}

    observacion = data.get(
        "observacion"
    )

    try:

        control = validar_control_diario(

            control_id=control_id,

            validador_id=usuario.id,

            observacion=observacion

        )

        return jsonify({

            "message": (
                "Control validado "
                "correctamente"
            ),

            "control": control.to_dict()

        }), 200

    except PermissionError as e:

        return jsonify({
            "error": str(e)
        }), 403

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({

            "error": (
                "Error al validar "
                "el control"
            ),

            "detail": str(e)

        }), 500


# ============================================================
# RECHAZAR CONTROL
# ============================================================

@control_diario_bp.put(
    "/<int:control_id>/rechazar"
)
@jwt_required()
def rechazar_control(control_id):

    usuario = obtener_usuario_actual()

    if not usuario:

        return jsonify({
            "error": "Usuario no encontrado"
        }), 404

    if not validar_rol_admin(usuario):

        return jsonify({

            "error": (
                "No tiene permisos para "
                "rechazar controles"
            )

        }), 403

    data = request.get_json(
        silent=True
    ) or {}

    observacion = data.get(
        "observacion"
    )

    try:

        control = rechazar_control_diario(

            control_id=control_id,

            validador_id=usuario.id,

            observacion=observacion

        )

        return jsonify({

            "message": (
                "Control rechazado "
                "correctamente"
            ),

            "control": control.to_dict()

        }), 200

    except PermissionError as e:

        return jsonify({
            "error": str(e)
        }), 403

    except ValueError as e:

        return jsonify({
            "error": str(e)
        }), 400

    except Exception as e:

        return jsonify({

            "error": (
                "Error al rechazar "
                "el control"
            ),

            "detail": str(e)

        }), 500