from flask import jsonify
from datetime import datetime

from extensions import db

from models import (
    Usuario,
    UsuarioDocumento,
    UsuarioDocumentoTipo
)


class UsuarioDocumentoService:

    # =====================================================
    # LISTAR DOCUMENTOS DE UN USUARIO
    # =====================================================

    @staticmethod
    def listar(usuario_id):

        usuario = Usuario.query.get(usuario_id)

        if not usuario:

            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404

        documentos = (
            UsuarioDocumento.query
            .filter_by(
                usuario_id=usuario_id,
                activo=True
            )
            .order_by(
                UsuarioDocumento.documento_tipo_id
            )
            .all()
        )

        return jsonify({
            "success": True,
            "data": {
                "usuario": {
                    "id": usuario.id,
                    "nombre": usuario.nombre,
                    "username": usuario.username,
                    "tipo_operador_id": usuario.tipo_operador_id,
                    "tipo_operador": (
                        usuario.tipo_operador.nombre
                        if usuario.tipo_operador
                        else None
                    )
                },
                "documentos": [
                    documento.to_dict()
                    for documento in documentos
                ]
            }
        })

    # =====================================================
    # ACTUALIZAR DOCUMENTO
    # =====================================================

    @staticmethod
    def actualizar(documento_id, data):

        documento = UsuarioDocumento.query.get(
            documento_id
        )

        if not documento:

            return jsonify({
                "success": False,
                "message": "Documento no encontrado"
            }), 404

        # ==========================================
        # FECHA DE VENCIMIENTO
        # ==========================================

        if "fecha_vencimiento" in data:

            fecha = data.get(
                "fecha_vencimiento"
            )

            if fecha:

                try:

                    documento.fecha_vencimiento = (
                        datetime.strptime(
                            fecha,
                            "%Y-%m-%d"
                        ).date()
                    )

                except ValueError:

                    return jsonify({
                        "success": False,
                        "message": (
                            "La fecha debe tener "
                            "el formato YYYY-MM-DD"
                        )
                    }), 400

            else:

                documento.fecha_vencimiento = None

        # ==========================================
        # ACTIVO
        # ==========================================

        if "activo" in data:

            documento.activo = bool(
                data["activo"]
            )

        # ==========================================
        # ARCHIVO
        # ==========================================

        if "archivo_url" in data:

            documento.archivo_url = (
                data.get("archivo_url")
            )

        db.session.commit()

        return jsonify({
            "success": True,
            "message": (
                "Documento actualizado correctamente"
            ),
            "data": documento.to_dict()
        })

    # =====================================================
    # LISTAR TIPOS DE DOCUMENTOS
    # =====================================================

    @staticmethod
    def listar_tipos():

        tipos = (
            UsuarioDocumentoTipo.query
            .filter_by(activo=True)
            .order_by(
                UsuarioDocumentoTipo.id
            )
            .all()
        )

        return jsonify({
            "success": True,
            "data": [
                tipo.to_dict()
                for tipo in tipos
            ]
        })