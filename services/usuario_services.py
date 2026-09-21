from flask import jsonify

from werkzeug.security import generate_password_hash

from extensions import db

from models import Usuario, Rol


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

        if Usuario.query.filter_by(

            username=data["username"]

        ).first():

            return jsonify({

                "success": False,

                "message": "El usuario ya existe"

            }), 400

        if data.get("email"):

            existe = Usuario.query.filter_by(

                email=data["email"]

            ).first()

            if existe:

                return jsonify({

                    "success": False,

                    "message": "El correo ya existe"

                }), 400

        # Puede venir role_id o rol
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

        usuario = Usuario(

            nombre=data["nombre"],

            username=data["username"],

            email=data.get("email"),

            telefono=data.get("telefono"),

            role_id=rol.id,

            activo=data.get("activo", True)

        )

        usuario.password_hash = generate_password_hash(

            data["password"]

        )

        db.session.add(usuario)

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

        existe = Usuario.query.filter(

            Usuario.username == data["username"],

            Usuario.id != usuario_id

        ).first()

        if existe:

            return jsonify({

                "success": False,

                "message": "El nombre de usuario ya existe"

            }), 400

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
    # OBTENER ROL (POR ID O POR NOMBRE)
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
    # ACTUALIZAR DATOS
    # ==========================================

        usuario.nombre = data["nombre"]

        usuario.username = data["username"]

        usuario.email = data.get("email")

        usuario.telefono = data.get("telefono")

        usuario.role_id = rol.id

        usuario.activo = data.get("activo", True)

        if data.get("password"):

            usuario.password_hash = generate_password_hash(

                data["password"]

            )

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