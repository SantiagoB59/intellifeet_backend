from flask import Blueprint, request, jsonify
from models import Usuario, Rol
from extensions import db
from flask_jwt_extended import create_access_token

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()

    if not data.get('username') or not data.get('password'):
        return jsonify({"error": "Faltan datos"}), 400

    if Usuario.query.filter_by(username=data['username']).first():
        return jsonify({"error": "Usuario ya existe"}), 400

    rol = Rol.query.filter_by(nombre=data.get('rol', 'operador')).first()

    if not rol:
        return jsonify({"error": "Rol no existe"}), 400

    user = Usuario(
        nombre=data.get('nombre'),
        username=data['username'],
        email=data.get('email'),
        role_id=rol.id
    )

    user.set_password(data['password'])

    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Usuario creado"}), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    user = Usuario.query.filter_by(username=data.get('username')).first()

    if not user or not user.check_password(data.get('password')):
        return jsonify({"error": "Credenciales inválidas"}), 401

    token = create_access_token(identity={
        "id": user.id,
        "username": user.username,
        "rol": user.rol.nombre
    })

    # 👇 FIX
    if isinstance(token, bytes):
        token = token.decode('utf-8')

    return jsonify({
        "token": token,
        "usuario": user.to_dict()
    })