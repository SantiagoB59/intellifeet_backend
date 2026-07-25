from flask import Blueprint, jsonify, request

from models import Alerta
from services.alertas_service import (
    resolver_alerta,
    obtener_todas_alertas,
    obtener_alertas_activas,
    obtener_estadisticas_alertas,
    ejecutar_motor_alertas
)
from extensions import db

from models import (
    Alerta,
    VehiculoDocumento,
    DocumentoTipo
)

import os
import uuid

alertas_bp = Blueprint(
    'alertas',
    __name__
)

# =====================================================
# TODAS
# =====================================================

@alertas_bp.route('/', methods=['GET'])
def listar_alertas():

    return jsonify(
        obtener_todas_alertas()
    )


# =====================================================
# ACTIVAS
# =====================================================

@alertas_bp.route('/activas', methods=['GET'])
def listar_activas():

    return jsonify(
        obtener_alertas_activas()
    )


# =====================================================
# EJECUTAR MOTOR
# =====================================================

@alertas_bp.route(
    '/ejecutar-motor',
    methods=['POST']
)
def ejecutar_motor():

    ejecutar_motor_alertas()

    return jsonify({
        'message': 'Motor ejecutado correctamente'
    })


# =====================================================
# RESOLVER
# =====================================================

@alertas_bp.route(
    '/<int:alerta_id>/resolver',
    methods=['PUT']
)
def resolver(alerta_id):

    alerta = resolver_alerta(alerta_id)

    if not alerta:

        return jsonify({
            'error': 'Alerta no encontrada'
        }), 404

    return jsonify({
        'message': 'Alerta resuelta',
        'alerta': alerta.to_dict()
    })


# =====================================================
# ESTADÍSTICAS
# =====================================================

@alertas_bp.route(
    '/estadisticas',
    methods=['GET']
)
def estadisticas():

    return jsonify(
        obtener_estadisticas_alertas()
    )
    
    
# =====================================================
# RESOLVER DOCUMENTO
# =====================================================

@alertas_bp.route(
    '/<int:alerta_id>/resolver-documento',
    methods=['POST']
)
def resolver_documento(alerta_id):

    alerta = Alerta.query.get_or_404(alerta_id)

    vehiculo_id = request.form.get('vehiculo_id')
    categoria = request.form.get('categoria')
    fecha_vencimiento = request.form.get('fecha_vencimiento')

    archivo = request.files.get('archivo')

    # =========================================
    # VALIDACIONES
    # =========================================

    if not archivo:

        return jsonify({
            'error': 'Archivo requerido'
        }), 400

    if not fecha_vencimiento:

        return jsonify({
            'error': 'Fecha requerida'
        }), 400

    # =========================================
    # BUSCAR TIPO DOCUMENTO
    # =========================================

    tipo_documento = DocumentoTipo.query.filter_by(
        nombre=categoria
    ).first()

    if not tipo_documento:

        return jsonify({
            'error': 'Tipo documento no encontrado'
        }), 404

    # =========================================
    # BUSCAR DOCUMENTO VEHÍCULO
    # =========================================

    documento = VehiculoDocumento.query.filter_by(
        vehiculo_id=vehiculo_id,
        documento_tipo_id=tipo_documento.id
    ).first()

    if not documento:

        return jsonify({
            'error': 'Documento del vehículo no encontrado'
        }), 404

    # =========================================
    # CREAR CARPETA
    # =========================================

    upload_folder = 'uploads/documentos'

    os.makedirs(
        upload_folder,
        exist_ok=True
    )

    # =========================================
    # GUARDAR ARCHIVO
    # =========================================

    ext = archivo.filename.rsplit('.', 1)[1].lower()

    filename = f"{uuid.uuid4()}.{ext}"

    path = os.path.join(
        upload_folder,
        filename
    )

    archivo.save(path)

    # =========================================
    # ACTUALIZAR DOCUMENTO
    # =========================================

    documento.fecha_vencimiento = fecha_vencimiento

    documento.archivo_url = f"/uploads/documentos/{filename}"

    # =========================================
    # RESOLVER ALERTA
    # =========================================

    alerta.estado = 'RESUELTA'

    db.session.commit()

    return jsonify({
        'message': 'Documento actualizado correctamente'
    })