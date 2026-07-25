from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename

from models import (
    db,
    Vehiculo,
    Maquinaria,
    InspeccionMensual
)

from sqlalchemy import desc

from datetime import datetime
import os
import uuid

inspeccion_mensual_bp = Blueprint(
    "inspeccion_mensual",
    __name__
)

# ============================================
# CONFIG
# ============================================

UPLOAD_FOLDER = "uploads/inspecciones"

ALLOWED_EXTENSIONS = {
    "pdf",
    "png",
    "jpg",
    "jpeg"
}

# ============================================
# HELPERS
# ============================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )

# ============================================
# LISTAR INSPECCIONES VEHÍCULO
# ============================================

@inspeccion_mensual_bp.route(
    "/vehiculo/<int:vehiculo_id>",
    methods=["GET"]
)
def listar_vehiculo(vehiculo_id):

    inspecciones = (
        InspeccionMensual.query
        .filter_by(
            vehiculo_id=vehiculo_id
        )
        .order_by(
            desc(InspeccionMensual.fecha)
        )
        .all()
    )

    return jsonify([
        i.to_dict()
        for i in inspecciones
    ])


# ============================================
# LISTAR INSPECCIONES MAQUINARIA
# ============================================

@inspeccion_mensual_bp.route(
    "/maquinaria/<int:maquinaria_id>",
    methods=["GET"]
)
def listar_maquinaria(maquinaria_id):

    inspecciones = (
        InspeccionMensual.query
        .filter_by(
            maquinaria_id=maquinaria_id
        )
        .order_by(
            desc(InspeccionMensual.fecha)
        )
        .all()
    )

    return jsonify([
        i.to_dict()
        for i in inspecciones
    ])


# ============================================
# CREAR INSPECCIÓN
# ============================================

@inspeccion_mensual_bp.route(
    "",
    methods=["POST"]
)
def crear():

    vehiculo_id = request.form.get(
        "vehiculo_id",
        type=int
    )

    maquinaria_id = request.form.get(
        "maquinaria_id",
        type=int
    )

    fecha = request.form.get("fecha")

    observaciones = request.form.get(
        "observaciones"
    )

    # ==========================
    # VALIDACIONES
    # ==========================

    if not vehiculo_id and not maquinaria_id:

        return jsonify({
            "error": "Debe enviar un vehículo o maquinaria."
        }), 400

    if vehiculo_id:

        Vehiculo.query.get_or_404(
            vehiculo_id
        )

    if maquinaria_id:

        Maquinaria.query.get_or_404(
            maquinaria_id
        )

    if "archivo" not in request.files:

        return jsonify({
            "error": "Debe adjuntar un archivo."
        }), 400

    file = request.files["archivo"]

    if file.filename == "":

        return jsonify({
            "error": "Archivo inválido."
        }), 400

    if not allowed_file(file.filename):

        return jsonify({
            "error": "Formato no permitido."
        }), 400

    # ==========================
    # SUBIR ARCHIVO
    # ==========================

    os.makedirs(
        UPLOAD_FOLDER,
        exist_ok=True
    )

    filename = secure_filename(
        file.filename
    )

    extension = filename.rsplit(
        ".",
        1
    )[1].lower()

    nuevo_nombre = (
        f"{uuid.uuid4()}.{extension}"
    )

    filepath = os.path.join(
        UPLOAD_FOLDER,
        nuevo_nombre
    )

    file.save(filepath)

    ruta = (
        f"uploads/inspecciones/{nuevo_nombre}"
    )

    # ==========================
    # CREAR REGISTRO
    # ==========================

    inspeccion = InspeccionMensual(

        vehiculo_id=vehiculo_id,

        maquinaria_id=maquinaria_id,

        fecha=datetime.strptime(
            fecha,
            "%Y-%m-%d"
        ).date(),

        archivo=ruta,

        observaciones=observaciones
    )

    db.session.add(
        inspeccion
    )

    db.session.commit()

    return jsonify(
        inspeccion.to_dict()
    ), 201


# ============================================
# OBTENER
# ============================================

@inspeccion_mensual_bp.route(
    "/<int:id>",
    methods=["GET"]
)
def obtener(id):

    inspeccion = (
        InspeccionMensual.query
        .get_or_404(id)
    )

    return jsonify(
        inspeccion.to_dict()
    )


# ============================================
# ELIMINAR
# ============================================

@inspeccion_mensual_bp.route(
    "/<int:id>",
    methods=["DELETE"]
)
def eliminar(id):

    inspeccion = (
        InspeccionMensual.query
        .get_or_404(id)
    )

    if (
        inspeccion.archivo
        and os.path.exists(inspeccion.archivo)
    ):
        os.remove(
            inspeccion.archivo
        )

    db.session.delete(
        inspeccion
    )

    db.session.commit()

    return jsonify({
        "message": "Inspección eliminada correctamente."
    })