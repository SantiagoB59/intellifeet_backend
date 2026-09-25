from flask import Blueprint, request

from services.usuario_documento_service import (
    UsuarioDocumentoService
)


usuario_documento_bp = Blueprint(
    "usuario_documento",
    __name__,
    url_prefix="/api/usuarios"
)


# =====================================================
# LISTAR DOCUMENTOS DE USUARIO
# =====================================================

@usuario_documento_bp.route(
    "/<int:usuario_id>/documentos",
    methods=["GET"]
)
def listar_documentos(usuario_id):

    return UsuarioDocumentoService.listar(
        usuario_id
    )


# =====================================================
# ACTUALIZAR DOCUMENTO
# =====================================================

@usuario_documento_bp.route(
    "/documentos/<int:documento_id>",
    methods=["PUT"]
)
def actualizar_documento(documento_id):

    data = request.get_json() or {}

    return UsuarioDocumentoService.actualizar(
        documento_id,
        data
    )


# =====================================================
# LISTAR TIPOS DE DOCUMENTOS
# =====================================================

@usuario_documento_bp.route(
    "/documentos/tipos",
    methods=["GET"]
)
def listar_tipos():

    return UsuarioDocumentoService.listar_tipos()