from flask import Blueprint, jsonify, request

from models import Alerta
from services.alertas_service import (
    resolver_alerta,
    obtener_todas_alertas,
    obtener_alertas_activas,
    obtener_estadisticas_alertas,
    ejecutar_motor_alertas,
    resolver_documento_operador
)
from extensions import db

from models import (
    Alerta,
    VehiculoDocumento,
    DocumentoTipo,
    TipoVehiculoCampo,
    VehiculoCampoValor
    
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
    
    
# =====================================================
# RESOLVER DOCUMENTO OPERADOR
# =====================================================

@alertas_bp.route(
    '/<int:alerta_id>/resolver-documento-operador',
    methods=['POST']
)
def resolver_documento_operador_route(alerta_id):

    usuario_id = request.form.get(
        'usuario_id'
    )

    categoria = request.form.get(
        'documento'
    )

    fecha_vencimiento = request.form.get(
        'fecha_vencimiento'
    )

    archivo = request.files.get(
        'archivo'
    )

    # =================================================
    # VALIDAR USUARIO
    # =================================================

    if not usuario_id:

        return jsonify({
            'success': False,
            'message': 'Usuario requerido'
        }), 400

    # =================================================
    # LLAMAR SERVICIO
    # =================================================

    resultado, status = resolver_documento_operador(

        alerta_id=alerta_id,

        usuario_id=usuario_id,

        categoria=categoria,

        fecha_vencimiento=fecha_vencimiento,

        archivo=archivo
    )

    return jsonify(resultado), status



# =====================================================
# RESOLVER CAMPO DINÁMICO
# =====================================================

@alertas_bp.route(
    '/<int:alerta_id>/resolver-campo-dinamico',
    methods=['POST']
)
def resolver_campo_dinamico(alerta_id):

    alerta = Alerta.query.get_or_404(alerta_id)

    # =================================================
    # DATOS
    # =================================================

    vehiculo_id = request.form.get('vehiculo_id')
    campo_id = request.form.get('campo_id')
    fecha_vencimiento = request.form.get('fecha_vencimiento')

    # =================================================
    # VALIDACIONES
    # =================================================

    if not vehiculo_id:
        return jsonify({
            'success': False,
            'message': 'Vehículo requerido'
        }), 400

    if not campo_id:
        return jsonify({
            'success': False,
            'message': 'Campo dinámico requerido'
        }), 400

    if not fecha_vencimiento:
        return jsonify({
            'success': False,
            'message': 'Nueva fecha requerida'
        }), 400

    # =================================================
    # VALIDAR ALERTA
    # =================================================

    if alerta.vehiculo_id != int(vehiculo_id):

        return jsonify({
            'success': False,
            'message': 'El vehículo no corresponde a la alerta'
        }), 400

    # =================================================
    # BUSCAR CAMPO
    # =================================================

    campo = TipoVehiculoCampo.query.get(
        int(campo_id)
    )

    if not campo:

        return jsonify({
            'success': False,
            'message': 'Campo dinámico no encontrado'
        }), 404

    # =================================================
    # VALIDAR QUE SEA FECHA
    # =================================================

    if campo.tipo_dato != 'date':

        return jsonify({
            'success': False,
            'message': 'El campo no es de tipo fecha'
        }), 400

    # =================================================
    # BUSCAR VALOR
    # =================================================

    campo_valor = VehiculoCampoValor.query.filter_by(
        vehiculo_id=int(vehiculo_id),
        campo_id=campo.id
    ).first()

    if not campo_valor:

        return jsonify({
            'success': False,
            'message': 'Valor del campo dinámico no encontrado'
        }), 404

    # =================================================
    # ACTUALIZAR FECHA
    # =================================================

    campo_valor.valor = fecha_vencimiento

    # =================================================
    # RESOLVER ALERTA
    # =================================================

    alerta.estado = 'RESUELTA'

    from datetime import datetime
    from zoneinfo import ZoneInfo

    alerta.fecha_resolucion = datetime.now(
        ZoneInfo('America/Bogota')
    )

    # =================================================
    # GUARDAR
    # =================================================

    db.session.commit()

    # =================================================
    # RESPUESTA
    # =================================================

    return jsonify({
        'success': True,
        'message': 'Fecha actualizada y alerta resuelta',
        'alerta': alerta.to_dict(),
        'campo': {
            'id': campo.id,
            'nombre': campo.nombre_campo,
            'valor': campo_valor.valor
        }
    }), 200