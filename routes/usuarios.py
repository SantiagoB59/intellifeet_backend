from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required

from services.usuario_services import UsuarioService


usuarios_bp = Blueprint(
    "usuarios",
    __name__
)

# =====================================================
# LISTAR
# =====================================================

@usuarios_bp.route("/", methods=["GET"])
@jwt_required()
def listar():

    return jsonify(
        UsuarioService.listar()
    )


# =====================================================
# OBTENER POR ID
# =====================================================

@usuarios_bp.route("/<int:usuario_id>", methods=["GET"])
@jwt_required()
def obtener(usuario_id):

    return jsonify(
        UsuarioService.obtener(usuario_id)
    )


# =====================================================
# CREAR
# =====================================================

@usuarios_bp.route("/", methods=["POST"])
@jwt_required()
def crear():

    data = request.get_json()

    return UsuarioService.crear(data)


# =====================================================
# ACTUALIZAR
# =====================================================

@usuarios_bp.route("/<int:usuario_id>", methods=["PUT"])
@jwt_required()
def actualizar(usuario_id):

    data = request.get_json()

    return UsuarioService.actualizar(
        usuario_id,
        data
    )


# =====================================================
# ELIMINAR (DESACTIVAR)
# =====================================================

@usuarios_bp.route("/<int:usuario_id>", methods=["DELETE"])
@jwt_required()
def eliminar(usuario_id):

    return UsuarioService.eliminar(
        usuario_id
    )