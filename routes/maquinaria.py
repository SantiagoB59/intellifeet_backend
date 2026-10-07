from flask import Blueprint, request, jsonify
from models import Maquinaria
from extensions import db
import os
import uuid
from sqlalchemy import or_
from models import TipoMaquinaria

maquinaria_bp = Blueprint('maquinaria', __name__)


# ============================================================
# CARPETAS
# ============================================================

UPLOAD_FOLDER = 'uploads/maquinaria'
DOCUMENTOS_FOLDER = 'uploads/maquinaria/documentos'

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg'}
ALLOWED_DOCUMENT_EXTENSIONS = {'pdf'}


# ============================================================
# HELPERS
# ============================================================

def allowed_image(filename):
    if not filename or '.' not in filename:
        return False

    return (
        filename.rsplit('.', 1)[1].lower()
        in ALLOWED_IMAGE_EXTENSIONS
    )


def allowed_pdf(filename):
    if not filename or '.' not in filename:
        return False

    return (
        filename.rsplit('.', 1)[1].lower()
        in ALLOWED_DOCUMENT_EXTENSIONS
    )


# ============================================================
# GUARDAR IMAGEN
# ============================================================

def guardar_imagen(file):

    if not file or not file.filename:
        return None

    if not allowed_image(file.filename):
        return None

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    ext = file.filename.rsplit('.', 1)[1].lower()

    filename = f"{uuid.uuid4()}.{ext}"

    path = os.path.join(
        UPLOAD_FOLDER,
        filename
    )

    file.save(path)

    return f"/uploads/maquinaria/{filename}"


# ============================================================
# GUARDAR DOCUMENTO PDF
# ============================================================

def guardar_documento(file, tipo_documento):

    if not file or not file.filename:
        return None

    if not allowed_pdf(file.filename):
        return None

    os.makedirs(DOCUMENTOS_FOLDER, exist_ok=True)

    filename = (
        f"{tipo_documento}_"
        f"{uuid.uuid4()}.pdf"
    )

    path = os.path.join(
        DOCUMENTOS_FOLDER,
        filename
    )

    file.save(path)

    return (
        f"/uploads/maquinaria/documentos/"
        f"{filename}"
    )


# ============================================================
# LISTAR
# ============================================================

@maquinaria_bp.route('/', methods=['GET'])
def listar():

    estado = request.args.get('estado')
    tipo = request.args.get('tipo')
    search = request.args.get('search')

    query = Maquinaria.query.filter(
        Maquinaria.activo.is_(True)
    )

    if estado:
        query = query.filter(
            Maquinaria.estado == estado
        )

    if tipo:
        query = query.filter(
            Maquinaria.tipo_maquinaria_id == tipo
        )

    if search:

        search = search.strip()

        query = query.filter(
            or_(
                Maquinaria.codigo.ilike(
                    f"%{search}%"
                ),
                Maquinaria.marca.ilike(
                    f"%{search}%"
                ),
                Maquinaria.modelo.ilike(
                    f"%{search}%"
                ),
                Maquinaria.linea.ilike(
                    f"%{search}%"
                ),
                Maquinaria.operador.ilike(
                    f"%{search}%"
                )
            )
        )

    return jsonify([
        m.to_dict()
        for m in query.all()
    ])


# ============================================================
# OBTENER POR ID
# ============================================================

@maquinaria_bp.route('/<int:id>', methods=['GET'])
def obtener(id):

    m = Maquinaria.query.get_or_404(id)

    return jsonify(
        m.to_dict()
    )


# ============================================================
# CREAR
# ============================================================

@maquinaria_bp.route('/', methods=['POST'])
def crear():

    data = dict(request.form)

    # ========================================================
    # ARCHIVOS
    # ========================================================

    foto = request.files.get('foto')

    tarjeta_registro = request.files.get(
        'tarjeta_registro'
    )

    ficha_tecnica = request.files.get(
        'ficha_tecnica'
    )

    # ========================================================
    # VALIDACIONES
    # ========================================================

    if not data.get('tipo_maquinaria_id'):

        return jsonify({
            "error": "tipo_maquinaria_id requerido"
        }), 400

    # ========================================================
    # HORÓMETRO
    # ========================================================

    if 'horometro_actual' in data:

        try:

            data['horometro_actual'] = float(
                data['horometro_actual']
            )

        except:

            return jsonify({
                "error":
                    "horometro_actual debe ser numérico"
            }), 400

    # ========================================================
    # COLUMNAS
    # ========================================================

    columnas_validas = (
        Maquinaria.__table__.columns.keys()
    )

    m = Maquinaria(**{
        k: v
        for k, v in data.items()
        if k in columnas_validas
    })

    # ========================================================
    # FOTO
    # ========================================================

    foto_url = guardar_imagen(foto)

    if foto_url:
        m.foto_url = foto_url

    # ========================================================
    # TARJETA DE REGISTRO
    # ========================================================

    if tarjeta_registro:

        tarjeta_url = guardar_documento(
            tarjeta_registro,
            'tarjeta_registro'
        )

        if tarjeta_url:

            m.tarjeta_registro = tarjeta_url

    # ========================================================
    # FICHA TÉCNICA
    # ========================================================

    if ficha_tecnica:

        ficha_url = guardar_documento(
            ficha_tecnica,
            'ficha_tecnica'
        )

        if ficha_url:

            m.ficha_tecnica = ficha_url

    # ========================================================
    # GUARDAR
    # ========================================================

    db.session.add(m)

    db.session.commit()

    return jsonify(
        m.to_dict()
    ), 201


# ============================================================
# ACTUALIZAR
# ============================================================

@maquinaria_bp.route('/<int:id>', methods=['PUT'])
def actualizar(id):

    m = Maquinaria.query.get_or_404(id)

    data = dict(request.form)

    # ========================================================
    # ARCHIVOS
    # ========================================================

    foto = request.files.get('foto')

    tarjeta_registro = request.files.get(
        'tarjeta_registro'
    )

    ficha_tecnica = request.files.get(
        'ficha_tecnica'
    )

    # ========================================================
    # CAMPOS NORMALES
    # ========================================================

    columnas_validas = (
        Maquinaria.__table__.columns.keys()
    )

    for k, v in data.items():

        if k in columnas_validas:

            setattr(
                m,
                k,
                v
            )

    # ========================================================
    # FOTO
    # ========================================================

    if foto:

        foto_url = guardar_imagen(
            foto
        )

        if foto_url:

            m.foto_url = foto_url

    # ========================================================
    # TARJETA DE REGISTRO
    # ========================================================

    if tarjeta_registro:

        tarjeta_url = guardar_documento(
            tarjeta_registro,
            'tarjeta_registro'
        )

        if tarjeta_url:

            m.tarjeta_registro = tarjeta_url

    # ========================================================
    # FICHA TÉCNICA
    # ========================================================

    if ficha_tecnica:

        ficha_url = guardar_documento(
            ficha_tecnica,
            'ficha_tecnica'
        )

        if ficha_url:

            m.ficha_tecnica = ficha_url

    # ========================================================
    # GUARDAR
    # ========================================================

    db.session.commit()

    return jsonify(
        m.to_dict()
    )


# ============================================================
# ELIMINAR
# ============================================================

@maquinaria_bp.route('/<int:id>', methods=['DELETE'])
def eliminar(id):

    m = Maquinaria.query.get_or_404(id)

    m.activo = False

    db.session.commit()

    return jsonify({
        "message":
            "Maquinaria desactivada"
    })


# ============================================================
# STATS
# ============================================================

@maquinaria_bp.route('/stats', methods=['GET'])
def stats():

    total = Maquinaria.query.filter_by(
        activo=True
    ).count()

    operativos = Maquinaria.query.filter_by(
        estado='OPERATIVA',
        activo=True
    ).count()

    taller = Maquinaria.query.filter_by(
        estado='TALLER',
        activo=True
    ).count()

    inactivos = Maquinaria.query.filter_by(
        estado='INACTIVA',
        activo=True
    ).count()

    return jsonify({
        "total": total,
        "operativos": operativos,
        "en_taller": taller,
        "inactivos": inactivos
    })


# ============================================================
# TIPOS
# ============================================================

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