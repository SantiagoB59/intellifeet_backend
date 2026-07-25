from flask import Blueprint, request, jsonify
from models import Viaje, Vehiculo
from extensions import db
from services.viajes_service import finalizar_viaje

viajes_bp = Blueprint('viajes', __name__)


# =========================
# LISTAR VIAJES
# =========================
@viajes_bp.route('/', methods=['GET'])
def listar_viajes():

    viajes = Viaje.query.filter_by(activo=True).all()
    return jsonify([v.to_dict() for v in viajes])


# =========================
# CREAR VIAJE
# =========================
@viajes_bp.route('/', methods=['POST'])
def crear_viaje():

    data = request.json

    vehiculo = Vehiculo.query.get(data['vehiculo_id'])

    if not vehiculo:
        return jsonify({"error": "Vehículo no encontrado"}), 404

    viaje = Viaje(

        vehiculo_id=vehiculo.id,
        remolque_id=data.get("remolque_id"),

        conductor=data.get("conductor"),
        cc_conductor=data.get("cc_conductor"),

        origen=data.get("origen"),
        destino=data.get("destino"),

        cliente=data.get("cliente"),
        tipo_carga=data.get("tipo_carga"),
        descripcion_carga=data.get("descripcion_carga"),
        peso=data.get("peso"),

        # KM inicial del remolque
        km_inicio=data.get("km_inicio"),

        estado="PROGRAMADO"

    )

    db.session.add(viaje)
    db.session.commit()

    return jsonify(viaje.to_dict()), 201


# =========================
# OBTENER VIAJE
# =========================
@viajes_bp.route('/<int:id>', methods=['GET'])
def obtener_viaje(id):

    viaje = Viaje.query.get_or_404(id)
    return jsonify(viaje.to_dict())


# =========================
# ACTUALIZAR VIAJE
# =========================
@viajes_bp.route('/<int:id>', methods=['PUT'])
def actualizar_viaje(id):

    viaje = Viaje.query.get_or_404(id)
    data = request.json

    viaje.vehiculo_id = data.get("vehiculo_id", viaje.vehiculo_id)
    viaje.remolque_id = data.get("remolque_id", viaje.remolque_id)

    viaje.conductor = data.get("conductor", viaje.conductor)
    viaje.cc_conductor = data.get("cc_conductor", viaje.cc_conductor)

    viaje.origen = data.get("origen", viaje.origen)
    viaje.destino = data.get("destino", viaje.destino)

    viaje.cliente = data.get("cliente", viaje.cliente)
    viaje.tipo_carga = data.get("tipo_carga", viaje.tipo_carga)
    viaje.descripcion_carga = data.get("descripcion_carga", viaje.descripcion_carga)
    viaje.peso = data.get("peso", viaje.peso)

    # Solo permitir modificar el KM inicial si aún no ha iniciado
    if viaje.estado == "PROGRAMADO":
        viaje.km_inicio = data.get("km_inicio", viaje.km_inicio)

    db.session.commit()

    return jsonify(viaje.to_dict())


# =========================
# ELIMINAR VIAJE
# =========================
@viajes_bp.route('/<int:id>', methods=['DELETE'])
def eliminar_viaje(id):

    viaje = Viaje.query.get_or_404(id)

    viaje.activo = False

    db.session.commit()

    return jsonify({
        "message": "Viaje desactivado correctamente"
    })


# =========================
# INICIAR VIAJE
# =========================
@viajes_bp.route('/<int:id>/iniciar', methods=['POST'])
def iniciar(id):

    viaje = Viaje.query.get_or_404(id)

    if viaje.estado != "PROGRAMADO":
        return jsonify({
            "error": "Solo se pueden iniciar viajes programados."
        }), 400

    viaje.estado = "EN_RUTA"

    db.session.commit()

    return jsonify(viaje.to_dict())


# =========================
# FINALIZAR VIAJE
# =========================
@viajes_bp.route('/<int:id>/finalizar', methods=['POST'])
def finalizar(id):

    viaje = Viaje.query.get_or_404(id)

    if viaje.estado != "EN_RUTA":
        return jsonify({
            "error": "Solo se pueden finalizar viajes en ruta."
        }), 400

    data = request.json

    km_fin = data.get("km_fin")

    if km_fin is None:
        return jsonify({
            "error": "Debe ingresar el kilometraje final."
        }), 400

    if km_fin < viaje.km_inicio:
        return jsonify({
            "error": "El kilometraje final no puede ser menor al inicial."
        }), 400

    finalizar_viaje(
        viaje,
        km_fin,
        data.get("observaciones")
    )

    return jsonify(viaje.to_dict())