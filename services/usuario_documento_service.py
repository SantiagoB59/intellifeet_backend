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
        
    # =====================================================
    # CREAR DOCUMENTO PARA UN USUARIO
    # =====================================================

    @staticmethod
    def crear(usuario_id, data):

        # ==========================================
        # VALIDAR USUARIO
        # ==========================================

        usuario = Usuario.query.get(usuario_id)

        if not usuario:

            return jsonify({
                "success": False,
                "message": "Usuario no encontrado"
            }), 404

        # ==========================================
        # OBTENER TIPO DE DOCUMENTO
        # ==========================================

        documento_tipo_id = data.get(
            "documento_tipo_id"
        )

        if not documento_tipo_id:

            return jsonify({
                "success": False,
                "message": "Debe indicar el tipo de documento"
            }), 400

        documento_tipo = (
            UsuarioDocumentoTipo.query.get(
                documento_tipo_id
            )
        )

        if not documento_tipo:

            return jsonify({
                "success": False,
                "message": "Tipo de documento no encontrado"
            }), 404

        # ==========================================
        # EVITAR DOCUMENTOS DUPLICADOS
        # ==========================================

        documento = (
            UsuarioDocumento.query
            .filter_by(
                usuario_id=usuario_id,
                documento_tipo_id=documento_tipo_id
            )
            .first()
        )

        # ==========================================
        # SI YA EXISTE
        # ==========================================

        if documento:

            documento.activo = True

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

        # ==========================================
        # FECHA
        # ==========================================

        fecha_vencimiento = None

        fecha = data.get(
            "fecha_vencimiento"
        )

        if fecha:

            try:

                fecha_vencimiento = (
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

        # ==========================================
        # CREAR DOCUMENTO
        # ==========================================

        nuevo_documento = UsuarioDocumento(

            usuario_id=usuario_id,

            documento_tipo_id=documento_tipo_id,

            fecha_vencimiento=fecha_vencimiento,

            archivo_url=data.get(
                "archivo_url"
            ),

            activo=data.get(
                "activo",
                True
            )
        )

        db.session.add(
            nuevo_documento
        )

        db.session.commit()

        return jsonify({
            "success": True,
            "message": (
                "Documento creado correctamente"
            ),
            "data": nuevo_documento.to_dict()
        }), 201
        
        
        
    @staticmethod
    def listar_operadores_documentos():
        from models import Usuario, UsuarioDocumento

        operadores = (
            Usuario.query
            .filter(
                Usuario.role_id == 3,
                Usuario.activo == True
            )
            .order_by(Usuario.nombre)
            .all()
        )

        resultado = []

        for operador in operadores:

            documentos = (
                UsuarioDocumento.query
                .filter_by(
                    usuario_id=operador.id,
                    activo=True
                )
                .order_by(
                    UsuarioDocumento.documento_tipo_id
                )
                .all()
            )

            resultado.append({
                "usuario": {
                    "id": operador.id,
                    "nombre": operador.nombre,
                    "username": operador.username,
                    "tipo_operador_id": operador.tipo_operador_id,
                    "tipo_operador": (
                        operador.tipo_operador.nombre
                        if operador.tipo_operador
                        else None
                    )
                },
                "documentos": [
                    documento.to_dict()
                    for documento in documentos
                ]
            })

        return jsonify({
            "success": True,
            "data": resultado
        })