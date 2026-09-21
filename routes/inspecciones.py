from flask import (
    Blueprint,
    request,
    jsonify,
    send_file,
    current_app
)

from flask_jwt_extended import (
    jwt_required,
    get_jwt_identity
)

from services.inspecciones_service import InspeccionService

from extensions import db

from werkzeug.utils import secure_filename

from datetime import datetime

import os
import uuid
import traceback

from io import BytesIO

from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image
)

from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.units import cm

inspecciones_bp = Blueprint(
    "inspecciones",
    __name__
)

import traceback
@inspecciones_bp.route("/mi-plantilla", methods=["GET"])
@jwt_required()
def mi_plantilla():

    try:

        usuario = get_jwt_identity()
        usuario_id = usuario["id"]

        activo = InspeccionService.obtener_activo_operador(usuario_id)

        plantilla = InspeccionService.obtener_plantilla(
            activo["tipo"],
            activo["tipo_id"]
        )

        # ---------------------------------------
        # ¿YA HIZO LA INSPECCIÓN HOY?
        # ---------------------------------------

        inspeccion_hoy = InspeccionService.obtener_inspeccion_hoy(
            usuario_id,
            vehiculo_id=activo["id"] if activo["tipo"] == "VEHICULO" else None,
            maquinaria_id=activo["id"] if activo["tipo"] == "MAQUINARIA" else None
        )
        lectura_final_registrada = (
            inspeccion_hoy is not None
            and inspeccion_hoy.contador_final is not None
        )

        return jsonify({

            "success": True,
            "lectura_final_registrada": lectura_final_registrada,
            "ya_realizada": (
                inspeccion_hoy is not None
                and inspeccion_hoy.estado == "FINALIZADA"
            ),

            "pendiente_cierre": (
                inspeccion_hoy is not None
                and inspeccion_hoy.estado == "PENDIENTE_CIERRE"
            ),

            "en_proceso": (
                inspeccion_hoy is not None
                and inspeccion_hoy.estado == "EN_PROCESO"
            ),

            "inspeccion_hoy": (
                inspeccion_hoy.to_dict()
                if inspeccion_hoy else None
            ),

            "activo": {

                "tipo": activo["tipo"],
                "id": activo["id"],
                "nombre": activo["nombre"],
                "tipo_id": activo["tipo_id"],

                "vehiculo": {

                    "id": activo["activo"].id,
                    "placa": activo["activo"].placa,
                    "marca": activo["activo"].marca,
                    "modelo": activo["activo"].modelo,
                    "tipo": activo["activo"].tipo_vehiculo.nombre

                } if activo["tipo"] == "VEHICULO" else None,

                "maquinaria": {

                    "id": activo["activo"].id,
                    "codigo": activo["activo"].codigo,
                    "marca": activo["activo"].marca,
                    "modelo": activo["activo"].modelo

                } if activo["tipo"] == "MAQUINARIA" else None

            },

            "plantilla": plantilla.to_dict()

        })

    except Exception as e:

        traceback.print_exc()

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
        
        
            
@inspecciones_bp.route("/iniciar", methods=["POST"])
@jwt_required()
def iniciar_inspeccion():

    try:

        usuario = get_jwt_identity()
        usuario_id = usuario["id"]

        inspeccion = InspeccionService.iniciar_inspeccion(
            usuario_id
        )

        return jsonify({
            "success": True,
            "data": inspeccion.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
        
        
        
@inspecciones_bp.route("/<int:inspeccion_id>", methods=["GET"])
@jwt_required()
def obtener_inspeccion(inspeccion_id):

    try:

        inspeccion = InspeccionService.obtener_inspeccion(
            inspeccion_id
        )

        return jsonify({

            "success": True,

            "data": {

                **inspeccion.to_dict(),

                "plantilla": inspeccion.plantilla.to_dict(),

                "respuestas": [
                    r.to_dict()
                    for r in inspeccion.respuestas
                ]

            }

        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 404
        
@inspecciones_bp.route(
    "/<int:inspeccion_id>/respuesta",
    methods=["POST"]
)
@jwt_required()
def guardar_respuesta(inspeccion_id):

    try:

        data = request.get_json()

        respuesta = InspeccionService.guardar_respuesta(
            inspeccion_id,
            data
        )

        return jsonify({
            "success": True,
            "data": respuesta.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
        
@inspecciones_bp.route(
    "/respuesta/<int:respuesta_id>/foto",
    methods=["POST"]
)
@jwt_required()
def guardar_foto(respuesta_id):

    try:

        if "foto" not in request.files:
            return jsonify({
                "success": False,
                "message": "No se recibió ninguna fotografía."
            }), 400

        archivo = request.files["foto"]

        datos = request.form.to_dict()

        # =====================================
        # GUARDAR EL ARCHIVO
        # =====================================

        UPLOAD_FOLDER = "uploads/inspecciones"

        os.makedirs(UPLOAD_FOLDER, exist_ok=True)

        extension = archivo.filename.rsplit(".", 1)[1].lower()

        nombre = f"{uuid.uuid4().hex}.{extension}"

        ruta = os.path.join(
            UPLOAD_FOLDER,
            nombre
        )

        archivo.save(ruta)

# Guardar la ruta con barras normales
        datos["archivo"] = ruta.replace("\\", "/")
        datos["mime_type"] = archivo.mimetype
        datos["tamano_bytes"] = os.path.getsize(ruta)

        foto = InspeccionService.guardar_foto(
            respuesta_id,
            datos
        )

        return jsonify({
            "success": True,
            "data": foto.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@inspecciones_bp.route(
    "/<int:inspeccion_id>/finalizar",
    methods=["POST"]
)
@jwt_required()
def finalizar_inspeccion(inspeccion_id):

    try:

        resultado = InspeccionService.finalizar_inspeccion(
            inspeccion_id
        )

        return jsonify({
            "success": True,
            "data": resultado
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400

@inspecciones_bp.route("/plantillas", methods=["GET"])
@jwt_required()
def listar_plantillas():

    try:

        plantillas = InspeccionService.listar_plantillas()

        return jsonify([
            p.to_dict()
            for p in plantillas
        ])

    except Exception as e:

        return jsonify({
            "message": str(e)
        }), 400
        
@inspecciones_bp.route("/plantillas", methods=["POST"])
@jwt_required()
def crear_plantilla():

    try:

        plantilla = InspeccionService.crear_plantilla(
            request.get_json()
        )

        return jsonify(
            plantilla.to_dict()
        ), 201

    except Exception as e:

        return jsonify({
            "message": str(e)
        }), 400
        

@inspecciones_bp.route(
    "/plantillas/<int:id>",
    methods=["PUT"]
)
@jwt_required()
def actualizar_plantilla(id):

    try:

        plantilla = InspeccionService.actualizar_plantilla(
            id,
            request.get_json()
        )

        return jsonify(
            plantilla.to_dict()
        )

    except Exception as e:

        return jsonify({
            "message": str(e)
        }), 400
        
@inspecciones_bp.route(
    "/plantillas/<int:id>",
    methods=["DELETE"]
)
@jwt_required()
def eliminar_plantilla(id):

    try:

        InspeccionService.eliminar_plantilla(id)

        return jsonify({
            "success": True
        })

    except Exception as e:

        return jsonify({
            "message": str(e)
        }), 400
        


@inspecciones_bp.route("/plantillas/<int:plantilla_id>", methods=["GET"])
@jwt_required()
def obtener_plantilla(plantilla_id):

    try:

        plantilla = InspeccionService.obtener_plantilla_completa(
            plantilla_id
        )

        return jsonify({
            "success": True,
            "data": plantilla.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 404
        


@inspecciones_bp.route("/anomalias", methods=["POST"])
@jwt_required()
def reportar_anomalia():

    try:

        usuario = get_jwt_identity()
        print(usuario)
        print(type(usuario))
        anomalia = InspeccionService.reportar_anomalia(
            usuario["id"],
            request.get_json()
        )

        return jsonify({
            "success": True,
            "data": anomalia.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400
        


@inspecciones_bp.route(
    "/<int:inspeccion_id>/anomalias",
    methods=["GET"]
)
@jwt_required()
def obtener_anomalias(inspeccion_id):

    datos = InspeccionService.listar_anomalias(inspeccion_id)

    return jsonify({
        "success": True,
        "data": [
            a.to_dict()
            for a in datos
        ]
    })
    
    


@inspecciones_bp.route(
    "/anomalias/<int:id>/cerrar",
    methods=["PUT"]
)
@jwt_required()
def cerrar_anomalia(id):

    dato = InspeccionService.cerrar_anomalia(id)

    return jsonify({
        "success": True,
        "data": dato.to_dict()
    })
    
@inspecciones_bp.route(
    "/anomalias/<int:anomalia_id>/foto",
    methods=["POST"]
)
@jwt_required()
def subir_foto_anomalia(anomalia_id):

    try:

        archivo = request.files.get("foto")

        if not archivo:
            return jsonify({
                "success": False,
                "message": "No se recibió ninguna foto."
            }), 400

        foto = InspeccionService.subir_foto_anomalia(
            anomalia_id,
            archivo
        )

        return jsonify({
            "success": True,
            "data": foto.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
        
 
# ==========================================================
# PDF INDIVIDUAL DE UNA INSPECCIÓN
# ==========================================================

@inspecciones_bp.route(
    "/<int:inspeccion_id>/pdf",
    methods=["GET"]
)
@jwt_required()
def descargar_pdf(inspeccion_id):

    pdf = InspeccionService.descargar_pdf(inspeccion_id)

    return send_file(
        pdf,
        download_name=f"INSPECCION_{inspeccion_id}.pdf",
        as_attachment=True,
        mimetype="application/pdf"
    )


# ==========================================================
# LISTADO ADMIN
# ==========================================================

@inspecciones_bp.route(
    "/admin/listar",
    methods=["GET"]
)
@jwt_required()
def listar_inspecciones_admin():

    try:

        fecha_inicio = request.args.get("fecha_inicio")
        fecha_fin = request.args.get("fecha_fin")
        vehiculo_id = request.args.get("vehiculo_id")
        maquinaria_id = request.args.get("maquinaria_id")
        usuario_id = request.args.get("usuario_id")
        estado = request.args.get("estado")

        inspecciones = InspeccionService.listar_inspecciones(
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            vehiculo_id=vehiculo_id,
            maquinaria_id=maquinaria_id,
            usuario_id=usuario_id,
            estado=estado
        )

        return jsonify({
            "success": True,
            "data": [
                i.to_dict()
                for i in inspecciones
            ]
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400


# ==========================================================
# REPORTE RESUMEN DEL MES
# ==========================================================

@inspecciones_bp.route(
    "/reporte-preoperacionales/pdf",
    methods=["GET"]
)
@jwt_required()
def reporte_preoperacionales():

    mes = int(request.args.get("mes"))
    anio = int(request.args.get("anio"))

    vehiculo_id = request.args.get("vehiculo_id")
    maquinaria_id = request.args.get("maquinaria_id")

    pdf = InspeccionService.descargar_reporte_preoperacionales(
        mes,
        anio,
        vehiculo_id,
        maquinaria_id
    )

    return send_file(
        pdf,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"RESUMEN_PREOPERACIONALES_{mes}_{anio}.pdf"
    )


# ==========================================================
# LIBRO DETALLADO
# ==========================================================

@inspecciones_bp.route(
    "/reporte-preoperacionales-detalle/pdf",
    methods=["GET"]
)
@jwt_required()
def libro_preoperacionales():

    mes = int(request.args.get("mes"))
    anio = int(request.args.get("anio"))

    vehiculo_id = request.args.get("vehiculo_id")
    maquinaria_id = request.args.get("maquinaria_id")

    # ======================================================
    # VALIDAR ACTIVO
    # ======================================================

    if not vehiculo_id and not maquinaria_id:
        return jsonify({
            "success": False,
            "message": "Debe seleccionar un vehículo o una maquinaria."
        }), 400

    if vehiculo_id and maquinaria_id:
        return jsonify({
            "success": False,
            "message": "Seleccione solamente un activo."
        }), 400

    # ======================================================
    # VEHÍCULO
    # ======================================================

    if vehiculo_id:

        pdf = InspeccionService.descargar_libro_preoperacionales(
            int(vehiculo_id),
            anio,
            mes
        )

        nombre_archivo = (
            f"LIBRO_PREOPERACIONALES_VEHICULO_"
            f"{vehiculo_id}_{mes}_{anio}.pdf"
        )

    # ======================================================
    # MAQUINARIA
    # ======================================================

    else:

        pdf = InspeccionService.descargar_libro_preoperacionales_maquinaria(
            int(maquinaria_id),
            anio,
            mes
        )

        nombre_archivo = (
            f"LIBRO_PREOPERACIONALES_MAQUINARIA_"
            f"{maquinaria_id}_{mes}_{anio}.pdf"
        )

    return send_file(
        pdf,
        as_attachment=True,
        mimetype="application/pdf",
        download_name=nombre_archivo
    )

# ==========================================================
# LIBRO EXCEL
# ==========================================================

@inspecciones_bp.route(
    "/reporte-preoperacionales/excel",
    methods=["GET"]
)
@jwt_required()
def reporte_excel():

    mes = int(request.args.get("mes"))
    anio = int(request.args.get("anio"))

    vehiculo_id = request.args.get("vehiculo_id")
    maquinaria_id = request.args.get("maquinaria_id")

    excel = InspeccionService.descargar_excel_preoperacionales(
        mes,
        anio,
        vehiculo_id,
        maquinaria_id
    )

    return send_file(
        excel,
        as_attachment=True,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"PREOPERACIONALES_{mes}_{anio}.xlsx"
    )
    
 
 

@inspecciones_bp.route(
    "/<int:inspeccion_id>/lectura-inicial",
    methods=["POST"]
)
@jwt_required()
def guardar_lectura_inicial(inspeccion_id):

    try:

        lectura = request.form.get("lectura")

        archivo = request.files.get("foto")

        if not lectura:
            return jsonify({
                "success": False,
                "message": "Debe ingresar la lectura inicial."
            }), 400

        if not archivo:
            return jsonify({
                "success": False,
                "message": "Debe adjuntar la fotografía de la lectura inicial."
            }), 400

        # ==============================================
        # VALIDAR EXTENSIÓN
        # ==============================================

        extension = ""

        if archivo.filename and "." in archivo.filename:
            extension = archivo.filename.rsplit(
                ".", 1
            )[1].lower()

        extensiones_permitidas = {
            "jpg",
            "jpeg",
            "png",
            "webp"
        }

        if extension not in extensiones_permitidas:

            return jsonify({
                "success": False,
                "message": "Formato de imagen no permitido."
            }), 400

        # ==============================================
        # CREAR CARPETA
        # ==============================================

        carpeta = os.path.join(
            "uploads",
            "inspecciones",
            str(inspeccion_id)
        )

        os.makedirs(
            carpeta,
            exist_ok=True
        )

        # ==============================================
        # NOMBRE
        # ==============================================

        nombre = (
            f"lectura_inicial_"
            f"{uuid.uuid4().hex}."
            f"{extension}"
        )

        ruta = os.path.join(
            carpeta,
            nombre
        )

        archivo.save(ruta)

        ruta_bd = ruta.replace("\\", "/")

        # ==============================================
        # GUARDAR
        # ==============================================

        data = {

            "lectura": lectura,

            "foto": ruta_bd

        }

        inspeccion = (
            InspeccionService
            .guardar_lectura_inicial(
                inspeccion_id,
                data
            )
        )

        return jsonify({

            "success": True,

            "message": (
                "Lectura inicial registrada correctamente."
            ),

            "data": inspeccion.to_dict()

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        }), 400
    
    
@inspecciones_bp.route(
    "/<int:inspeccion_id>/lectura-final",
    methods=["POST"]
)
@jwt_required()
def guardar_lectura_final(inspeccion_id):

    try:

        lectura = request.form.get("lectura")

        archivo = request.files.get("foto")

        if not lectura:
            return jsonify({
                "success": False,
                "message": "Debe ingresar la lectura final."
            }), 400

        if not archivo:
            return jsonify({
                "success": False,
                "message": "Debe adjuntar la fotografía de la lectura final."
            }), 400

        extension = ""

        if archivo.filename and "." in archivo.filename:
            extension = archivo.filename.rsplit(
                ".", 1
            )[1].lower()

        extensiones_permitidas = {
            "jpg",
            "jpeg",
            "png",
            "webp"
        }

        if extension not in extensiones_permitidas:

            return jsonify({
                "success": False,
                "message": "Formato de imagen no permitido."
            }), 400

        carpeta = os.path.join(
            "uploads",
            "inspecciones",
            str(inspeccion_id)
        )

        os.makedirs(
            carpeta,
            exist_ok=True
        )

        nombre = (
            f"lectura_final_"
            f"{uuid.uuid4().hex}."
            f"{extension}"
        )

        ruta = os.path.join(
            carpeta,
            nombre
        )

        archivo.save(ruta)

        ruta_bd = ruta.replace("\\", "/")

        data = {

            "lectura": lectura,

            "foto": ruta_bd

        }

        inspeccion = (
            InspeccionService
            .guardar_lectura_final(
                inspeccion_id,
                data
            )
        )

        return jsonify({

            "success": True,

            "message": (
                "Lectura final registrada correctamente."
            ),

            "data": inspeccion.to_dict()

        })

    except Exception as e:

        return jsonify({

            "success": False,
            "message": str(e)

        }), 400
        
        
        
# ==========================================================
# REPORTE SEMANAL PREOPERACIONAL
# ==========================================================

@inspecciones_bp.route(
    "/reportes/preoperacionales/semanal",
    methods=["POST"]
)
@jwt_required()
def reporte_preoperacionales_semanal():

    try:

        data = request.get_json() or {}

        tipo_activo = data.get("tipo_activo")
        activo_id = data.get("activo_id")
        fecha = data.get("fecha")

        # ==================================================
        # VALIDAR TIPO DE ACTIVO
        # ==================================================

        if not tipo_activo:

            return jsonify({
                "success": False,
                "message": "Debe indicar el tipo de activo."
            }), 400

        tipo_activo = tipo_activo.upper()

        if tipo_activo not in [
            "VEHICULO",
            "MAQUINARIA"
        ]:

            return jsonify({
                "success": False,
                "message": (
                    "El tipo de activo debe ser "
                    "VEHICULO o MAQUINARIA."
                )
            }), 400

        # ==================================================
        # VALIDAR ACTIVO
        # ==================================================

        if not activo_id:

            return jsonify({
                "success": False,
                "message": "Debe seleccionar un activo."
            }), 400

        try:

            activo_id = int(activo_id)

        except (ValueError, TypeError):

            return jsonify({
                "success": False,
                "message": "El ID del activo no es válido."
            }), 400

        # ==================================================
        # VALIDAR FECHA
        # ==================================================

        if not fecha:

            return jsonify({
                "success": False,
                "message": "Debe seleccionar una fecha."
            }), 400

        try:

            fecha = datetime.strptime(
                fecha,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            return jsonify({
                "success": False,
                "message": (
                    "La fecha debe tener formato "
                    "YYYY-MM-DD."
                )
            }), 400

        # ==================================================
        # GENERAR REPORTE
        # ==================================================

        pdf = InspeccionService.descargar_libro_preoperacionales_semanal(
            fecha_referencia=fecha,
            vehiculo_id=activo_id if tipo_activo == "VEHICULO" else None,
            maquinaria_id=activo_id if tipo_activo == "MAQUINARIA" else None,
        )

        # ==================================================
        # NOMBRE ARCHIVO
        # ==================================================

        nombre_archivo = (
            "REPORTE_SEMANAL_PREOPERACIONAL_"
            f"{tipo_activo}_"
            f"{activo_id}_"
            f"{fecha.strftime('%Y-%m-%d')}.pdf"
        )

        return send_file(
            pdf,
            as_attachment=True,
            mimetype="application/pdf",
            download_name=nombre_archivo
        )

    except Exception as e:

        current_app.logger.exception(
            "Error generando reporte semanal"
        )

        return jsonify({
            "success": False,
            "message": str(e)
        }), 500