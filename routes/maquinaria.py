from flask import Blueprint, request, jsonify
from models import Maquinaria
from extensions import db
import os
import uuid
from sqlalchemy import or_
from models import TipoMaquinaria
maquinaria_bp = Blueprint('maquinaria', __name__)

UPLOAD_FOLDER = 'uploads/maquinaria'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


# ==========================
# HELPERS
# ==========================
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def guardar_imagen(file):
    if not file or not allowed_file(file.filename):
        return None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"{uuid.uuid4()}.{ext}"

    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    return f"/uploads/maquinaria/{filename}"


# ==========================
# LISTAR
# ==========================
@maquinaria_bp.route('/', methods=['GET'])
def listar():

    estado = request.args.get('estado')
    tipo = request.args.get('tipo')
    search = request.args.get('search')

    query = Maquinaria.query.filter(Maquinaria.activo.is_(True))

    if estado:
        query = query.filter(Maquinaria.estado == estado)

    # 🔥 FK correcta
    if tipo:
        query = query.filter(Maquinaria.tipo_maquinaria_id == tipo)

    # 🔥 búsqueda correcta
    if search:
        search = search.strip()

        query = query.filter(
            or_(
                Maquinaria.codigo.ilike(f"%{search}%"),
                Maquinaria.marca.ilike(f"%{search}%"),
                Maquinaria.modelo.ilike(f"%{search}%"),
                Maquinaria.operador.ilike(f"%{search}%")
            )
        )

    return jsonify([m.to_dict() for m in query.all()])


# ==========================
# OBTENER POR ID
# ==========================
@maquinaria_bp.route('/<int:id>', methods=['GET'])
def obtener(id):
    m = Maquinaria.query.get_or_404(id)
    return jsonify(m.to_dict())


# ==========================
# CREAR
# ==========================
@maquinaria_bp.route('/', methods=['POST'])
def crear():

    data = dict(request.form)
    file = request.files.get('foto')

    if not data.get('tipo_maquinaria_id'):
        return jsonify({"error": "tipo_maquinaria_id requerido"}), 400

    # 🔥 FIX HORAS
    if 'horometro_actual' in data:
        try:
            data['horometro_actual'] = float(data['horometro_actual'])
        except:
            return jsonify({"error": "horometro_actual debe ser numérico"}), 400

    columnas_validas = Maquinaria.__table__.columns.keys()

    m = Maquinaria(**{
        k: v for k, v in data.items() if k in columnas_validas
    })

    foto_url = guardar_imagen(file)
    if foto_url:
        m.foto_url = foto_url

    db.session.add(m)
    db.session.commit()

    return jsonify(m.to_dict()), 201


# ==========================
# ACTUALIZAR
# ==========================
@maquinaria_bp.route('/<int:id>', methods=['PUT'])
def actualizar(id):

    m = Maquinaria.query.get_or_404(id)

    data = dict(request.form)
    file = request.files.get('foto')

    columnas_validas = Maquinaria.__table__.columns.keys()

    for k, v in data.items():
        if k in columnas_validas:
            setattr(m, k, v)

    if file:
        m.foto_url = guardar_imagen(file)

    db.session.commit()

    return jsonify(m.to_dict())


# ==========================
# ELIMINAR (SOFT DELETE)
# ==========================
@maquinaria_bp.route('/<int:id>', methods=['DELETE'])
def eliminar(id):

    m = Maquinaria.query.get_or_404(id)

    m.activo = False
    db.session.commit()

    return jsonify({"message": "Maquinaria desactivada"})


# ==========================
# STATS
# ==========================
@maquinaria_bp.route('/stats', methods=['GET'])
def stats():

    total = Maquinaria.query.filter_by(activo=True).count()
    operativos = Maquinaria.query.filter_by(estado='OPERATIVA', activo=True).count()
    taller = Maquinaria.query.filter_by(estado='TALLER', activo=True).count()
    inactivos = Maquinaria.query.filter_by(estado='INACTIVA', activo=True).count()

    return jsonify({
        "total": total,
        "operativos": operativos,
        "en_taller": taller,
        "inactivos": inactivos
    })
    
    

@maquinaria_bp.route('/tipos', methods=['GET'])
def tipos():

    tipos = TipoMaquinaria.query.all()

    return jsonify([
        {
            "id": t.id,
            "nombre": t.nombre
        }
        for t in tipos
    ])