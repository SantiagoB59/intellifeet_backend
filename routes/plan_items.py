from flask import Blueprint, request, jsonify
from models import db, PlanItem

plan_items_bp = Blueprint('plan_items', __name__)

# =========================
# 📌 LISTAR
# =========================
@plan_items_bp.route('/plan-items', methods=['GET'])
def listar_plan_items():

    items = PlanItem.query.order_by(
        PlanItem.id.desc()
    ).all()

    return jsonify([
        i.to_dict()
        for i in items
    ])

# =========================
# 📌 OBTENER UNO
# =========================
@plan_items_bp.route('/plan-items/<int:id>', methods=['GET'])
def obtener_plan_item(id):

    item = PlanItem.query.get_or_404(id)

    return jsonify(item.to_dict())

# =========================
# 📌 CREAR
# =========================
@plan_items_bp.route('/plan-items', methods=['POST'])
def crear_plan_item():

    data = request.get_json()

    item = PlanItem(

        sistema=data.get('sistema'),
        nombre=data.get('nombre'),
        descripcion=data.get('descripcion'),

        tipo_mantenimiento=data.get(
            'tipo_mantenimiento',
            'PREVENTIVO'
        ),

        tipo_control=data.get(
            'tipo_control',
            'KM'
        ),

        frecuencia_valor=data.get('frecuencia_valor'),
        alerta_valor=data.get('alerta_valor'),

        obligatorio=data.get('obligatorio', True),
        activo=True
    )

    db.session.add(item)
    db.session.commit()

    return jsonify(item.to_dict()), 201

# =========================
# 📌 ACTUALIZAR
# =========================
@plan_items_bp.route('/plan-items/<int:id>', methods=['PUT'])
def actualizar_plan_item(id):

    item = PlanItem.query.get_or_404(id)
    data = request.get_json()

    item.sistema = data.get('sistema', item.sistema)
    item.nombre = data.get('nombre', item.nombre)
    item.descripcion = data.get('descripcion', item.descripcion)

    item.tipo_mantenimiento = data.get(
        'tipo_mantenimiento',
        item.tipo_mantenimiento
    )

    item.tipo_control = data.get(
        'tipo_control',
        item.tipo_control
    )

    item.frecuencia_valor = data.get(
        'frecuencia_valor',
        item.frecuencia_valor
    )

    item.alerta_valor = data.get(
        'alerta_valor',
        item.alerta_valor
    )

    item.obligatorio = data.get(
        'obligatorio',
        item.obligatorio
    )

    db.session.commit()

    return jsonify(item.to_dict())

# =========================
# 📌 ELIMINAR (SOFT DELETE)
# =========================
@plan_items_bp.route('/plan-items/<int:id>', methods=['DELETE'])
def eliminar_plan_item(id):

    item = PlanItem.query.get_or_404(id)

    item.activo = False

    db.session.commit()

    return jsonify({
        "msg": "Plan eliminado"
    })