from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required

from services.activo_operador_service import ActivoOperadorService

activo_operador_bp = Blueprint(
    "activo_operador",
    __name__
)

# ==========================================
# LISTAR
# ==========================================

@activo_operador_bp.route("", methods=["GET"])
@jwt_required()
def listar():

    try:

        datos = ActivoOperadorService.listar()

        return jsonify({

            "success": True,

            "data": datos

        })

    except Exception as e:

        return jsonify({

            "success": False,

            "message": str(e)

        }), 400
# ==========================================
# OBTENER
# ==========================================

@activo_operador_bp.route("/<int:id>", methods=["GET"])
@jwt_required()
def obtener(id):

    try:

        dato = ActivoOperadorService.obtener(id)

        return jsonify({
            "success": True,
            "data": dato.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 404


# ==========================================
# CREAR
# ==========================================

@activo_operador_bp.route("", methods=["POST"])
@jwt_required()
def crear():

    try:

        dato = ActivoOperadorService.crear(
            request.get_json()
        )

        return jsonify({
            "success": True,
            "data": dato.to_dict()
        }), 201

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400


# ==========================================
# ACTUALIZAR
# ==========================================

@activo_operador_bp.route("/<int:id>", methods=["PUT"])
@jwt_required()
def actualizar(id):

    try:

        dato = ActivoOperadorService.actualizar(
            id,
            request.get_json()
        )

        return jsonify({
            "success": True,
            "data": dato.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400


# ==========================================
# ELIMINAR
# ==========================================

@activo_operador_bp.route("/<int:id>", methods=["DELETE"])
@jwt_required()
def eliminar(id):

    try:

        dato = ActivoOperadorService.eliminar(id)

        return jsonify({
            "success": True,
            "data": dato.to_dict()
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "message": str(e)
        }), 400