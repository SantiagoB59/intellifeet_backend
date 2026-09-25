from flask import jsonify

from werkzeug.security import generate_password_hash

from extensions import db

from models import (
    Usuario,
    Rol,
    TipoOperador,
    TipoOperadorDocumento,
    UsuarioDocumento
)


class UsuarioService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def listar():

        usuarios = Usuario.query.order_by(
            Usuario.nombre
        ).all()

        roles = Rol.query.order_by(
            Rol.nombre
        ).all()

        lista_usuarios = []

        for u in usuarios:

            lista_usuarios.append({

                "id": u.id,

                "nombre": u.nombre,

                "username": u.username,

                "email": u.email,

                "telefono": u.telefono,

                "activo": u.activo,

                "created_at": u.created_at,

                "rol": {

                    "id": u.rol.id,

                    "nombre": u.rol.nombre

                }

            })

        lista_roles = []

        for r in roles:

            lista_roles.append({

                "id": r.id,

                "nombre": r.nombre

            })

        return {

            "success": True,

            "data": {

                "usuarios": lista_usuarios,

                "roles": lista_roles

            }

        }


    # =====================================================
# LISTAR DOCUMENTOS SEGÚN TIPO DE OPERADOR
# =====================================================

    @staticmethod
    def listar_documentos_tipo_operador(
        tipo_operador_id
    ):

        tipo_operador = TipoOperador.query.get(
            tipo_operador_id
        )

        if not tipo_operador:

            return jsonify({
                "success": False,
                "message": "Tipo de operador no encontrado"
            }), 404

        documentos = (
            TipoOperadorDocumento.query
            .filter_by(
                tipo_operador_id=tipo_operador_id
            )
            .order_by(
                TipoOperadorDocumento.id
            )
            .all()
        )

        return jsonify({
            "success": True,
            "data": {
                "tipo_operador": tipo_operador.to_dict(),

                "documentos": [
                    {
                        "id": documento.documento_tipo_id,

                        "documento_tipo_id":
                            documento.documento_tipo_id,

                        "nombre":
                            documento.documento_tipo.nombre
                            if documento.documento_tipo
                            else None,

                        "obligatorio":
                            documento.obligatorio
                    }

                    for documento in documentos
                ]
            }
        })
    # =====================================================
    # OBTENER
    # =====================================================

    @staticmethod
    def obtener(usuario_id):

        usuario = Usuario.query.get(usuario_id)

        if not usuario:

            return jsonify({

                "success": False,

                "message": "Usuario no encontrado"

            }), 404

        return {

            "success": True,

            "data": {

                "id": usuario.id,

                "nombre": usuario.nombre,

                "username": usuario.username,

                "email": usuario.email,

                "telefono": usuario.telefono,

                "activo": usuario.activo,

                "role_id": usuario.role_id,
                "rol": usuario.rol.nombre

            }

        }

# =====================================================
# CREAR
# =====================================================

    @staticmethod
    def crear(data):

        # ==========================================
        # VALIDAR USERNAME
        # ==========================================

        if Usuario.query.filter_by(
            username=data["username"]
        ).first():

            return jsonify({
                "success": False,
                "message": "El usuario ya existe"
            }), 400

        # ==========================================
        # VALIDAR EMAIL
        # ==========================================

        if data.get("email"):

            existe = Usuario.query.filter_by(
                email=data["email"]
            ).first()

            if existe:

                return jsonify({
                    "success": False,
                    "message": "El correo ya existe"
                }), 400

        # ==========================================
        # OBTENER ROL
        # ==========================================

        if "role_id" in data:

            rol = Rol.query.get(data["role_id"])

        else:

            rol = Rol.query.filter_by(
                nombre=data.get("rol")
            ).first()

        if not rol:

            return jsonify({
                "success": False,
                "message": "Rol inválido"
            }), 400

        # ==========================================
        # TIPO DE OPERADOR
        # ==========================================

        tipo_operador_id = data.get(
            "tipo_operador_id"
        )

        tipo_operador = None

        # Solo los operadores necesitan
        # tipo de operador
        if rol.id == 3:

            if not tipo_operador_id:

                return jsonify({
                    "success": False,
                    "message": (
                        "Debe seleccionar el tipo "
                        "de operador"
                    )
                }), 400

            tipo_operador = TipoOperador.query.get(
                tipo_operador_id
            )

            if not tipo_operador:

                return jsonify({
                    "success": False,
                    "message": (
                        "El tipo de operador "
                        "no es válido"
                    )
                }), 400

        else:

            # Para usuarios que no son operadores
            # no se debe guardar tipo de operador
            tipo_operador_id = None

        # ==========================================
        # CREAR USUARIO
        # ==========================================

        usuario = Usuario(

            nombre=data["nombre"],

            username=data["username"],

            email=data.get("email"),

            telefono=data.get("telefono"),

            role_id=rol.id,

            tipo_operador_id=tipo_operador_id,

            activo=data.get("activo", True)

        )

        usuario.password_hash = generate_password_hash(
            data["password"]
        )

        db.session.add(usuario)

        # Necesitamos el ID del usuario
        # antes de crear sus documentos
        db.session.flush()

        # ==========================================
        # CREAR DOCUMENTOS DEL OPERADOR
        # ==========================================

        if rol.id == 3:

            documentos_requeridos = (
                TipoOperadorDocumento.query
                .filter_by(
                    tipo_operador_id=tipo_operador.id,
                    obligatorio=True
                )
                .all()
            )

            for requerido in documentos_requeridos:

                documento = UsuarioDocumento(

                    usuario_id=usuario.id,

                    documento_tipo_id=(
                        requerido.documento_tipo_id
                    ),

                    fecha_vencimiento=None,

                    archivo_url=None,

                    activo=True

                )

                db.session.add(documento)

        # ==========================================
        # GUARDAR
        # ==========================================

        db.session.commit()

        return jsonify({

            "success": True,

            "message": "Usuario creado correctamente"

        })



# =====================================================
# ACTUALIZAR
# =====================================================

    @staticmethod
    def actualizar(usuario_id, data):

        usuario = Usuario.query.get(usuario_id)

        if not usuario:

            return jsonify({

                "success": False,
                "message": "Usuario no encontrado"

            }), 404

        # ==========================================
        # VALIDAR USERNAME
        # ==========================================

        existe = Usuario.query.filter(

            Usuario.username == data["username"],

            Usuario.id != usuario_id

        ).first()

        if existe:

            return jsonify({

                "success": False,
                "message": "El nombre de usuario ya existe"

            }), 400

        # ==========================================
        # VALIDAR EMAIL
        # ==========================================

        if data.get("email"):

            existe = Usuario.query.filter(

                Usuario.email == data["email"],

                Usuario.id != usuario_id

            ).first()

            if existe:

                return jsonify({

                    "success": False,
                    "message": "El correo ya existe"

                }), 400

        # ==========================================
        # OBTENER ROL
        # ==========================================

        if "role_id" in data:

            rol = Rol.query.get(data["role_id"])

        else:

            rol = Rol.query.filter_by(
                nombre=data.get("rol")
            ).first()

        if not rol:

            return jsonify({

                "success": False,
                "message": "Rol inválido"

            }), 400

        # ==========================================
        # TIPO DE OPERADOR
        # ==========================================

        tipo_operador_id = data.get(
            "tipo_operador_id"
        )

        tipo_operador = None

        # ------------------------------------------
        # SI ES OPERADOR
        # ------------------------------------------

        if rol.id == 3:

            if not tipo_operador_id:

                return jsonify({

                    "success": False,
                    "message": (
                        "Debe seleccionar el tipo "
                        "de operador"
                    )

                }), 400

            tipo_operador = TipoOperador.query.get(
                tipo_operador_id
            )

            if not tipo_operador:

                return jsonify({

                    "success": False,
                    "message": (
                        "El tipo de operador "
                        "no es válido"
                    )

                }), 400

        else:

            # Si deja de ser operador,
            # quitamos el tipo de operador.
            tipo_operador_id = None

        # ==========================================
        # ACTUALIZAR DATOS DEL USUARIO
        # ==========================================

        usuario.nombre = data["nombre"]

        usuario.username = data["username"]

        usuario.email = data.get("email")

        usuario.telefono = data.get("telefono")

        usuario.role_id = rol.id

        usuario.tipo_operador_id = tipo_operador_id

        usuario.activo = data.get(
            "activo",
            True
        )

        # ==========================================
        # ACTUALIZAR CONTRASEÑA
        # ==========================================

        if data.get("password"):

            usuario.password_hash = generate_password_hash(
                data["password"]
            )

        # ==========================================
        # DOCUMENTOS DEL OPERADOR
        # ==========================================

        if rol.id == 3:

            documentos_requeridos = (
                TipoOperadorDocumento.query
                .filter_by(
                    tipo_operador_id=tipo_operador.id,
                    obligatorio=True
                )
                .all()
            )

            # IDs de documentos que ya tiene
            documentos_existentes = {
                documento.documento_tipo_id
                for documento in UsuarioDocumento.query.filter_by(
                    usuario_id=usuario.id
                ).all()
            }

            # ------------------------------------------
            # CREAR SOLO LOS DOCUMENTOS QUE FALTEN
            # ------------------------------------------

            for requerido in documentos_requeridos:

                if requerido.documento_tipo_id not in documentos_existentes:

                    documento = UsuarioDocumento(

                        usuario_id=usuario.id,

                        documento_tipo_id=(
                            requerido.documento_tipo_id
                        ),

                        fecha_vencimiento=None,

                        archivo_url=None,

                        activo=True

                    )

                    db.session.add(documento)

        # ==========================================
        # GUARDAR
        # ==========================================

        db.session.commit()

        return jsonify({

            "success": True,

            "message": "Usuario actualizado correctamente"

        })

    
    # =====================================================
    # ELIMINAR
    # =====================================================

    @staticmethod
    def eliminar(usuario_id):

        usuario = Usuario.query.get(usuario_id)

        if not usuario:

            return jsonify({

                "success": False,

                "message": "Usuario no encontrado"

            }), 404

        usuario.activo = False

        db.session.commit()

        return jsonify({

            "success": True,

            "message": "Usuario desactivado correctamente"

        })