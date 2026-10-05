from flask_jwt_extended import get_jwt_identity, get_jwt


def obtener_usuario_actual():
    """
    Obtiene el usuario autenticado desde el JWT.
    """

    identity = get_jwt_identity()
    claims = get_jwt()

    if not identity:
        return None

    try:
        usuario_id = int(identity)
    except (TypeError, ValueError):
        return None

    return {
        "id": usuario_id,
        "username": claims.get("username"),
        "rol": claims.get("rol")
    }