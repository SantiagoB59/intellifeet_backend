from flask import Blueprint, jsonify
from models import SistemaVehiculo

sistemas_bp = Blueprint('sistemas', __name__)

@sistemas_bp.route('/sistemas-vehiculo', methods=['GET'])
def listar_sistemas():

    sistemas = SistemaVehiculo.query.filter_by(activo=True).all()

    return jsonify([
        {
            "id": s.id,
            "nombre": s.nombre
        }
        for s in sistemas
    ])