import csv
import io
import re
from datetime import datetime
from flask import Blueprint, request, jsonify

# 1. Importación de la base de datos y tus modelos (subiendo un nivel de carpeta)
from ..models import db, Vehiculo, PlanItem, VehiculoPlanItem

# 2. Definición del Blueprint exclusivo para importaciones
mantenimiento_importar_bp = Blueprint(
    'mantenimiento_importar', 
    __name__
)

def limpiar_km(texto):
    """
    Función auxiliar para convertir texto de frecuencias en números enteros.
    Ejemplo: 'Cada 15,000 km' -> 15000 | 'Cada 6,000' -> 6000 | 'Diario' -> 0
    """
    if not texto:
        return 0
    texto_limpio = texto.lower()
    if 'diario' in texto_limpio or 'diaria' in texto_limpio:
        return 0
        
    # Extraer primer patrón numérico incluyendo puntos y comas de miles
    numeros = re.findall(r'\d[\d\s\.,]*', texto)
    if numeros:
        # Quitar puntos, comas y espacios para dejar el número puro
        return int(re.sub(r'[\.,\s]', '', numeros[0]))
    return 0


# =========================================================================
# 📌 RUTA: CREAR EXCLUSIVAMENTE EL PLAN DE MANTENIMIENTO DEL VEHÍCULO
# =========================================================================
@mantenimiento_importar_bp.route(
    '/vehiculos/importar-plan', 
    methods=['POST']
)
def importar_plan_excel():
    # Validar que venga un archivo en la petición HTTP
    if 'file' not in request.files:
        return jsonify({"error": "No se subió ningún archivo bajo la clave 'file'"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "El archivo seleccionado está vacío o no tiene nombre"}), 400

    # Capturar el parámetro dinámico de alerta enviado desde el cliente (Frontend o Postman)
    # Si el usuario no envía nada, por defecto se usará un margen preventivo de 1,000 km antes.
    km_anticipacion_alerta = request.form.get('km_alerta', default=1000, type=int)

    try:
        # Leer el flujo del archivo plano decodificando en UTF-8
        stream = io.StringIO(file.stream.read().decode("UTF-8"), newline=None)
        reader = list(csv.reader(stream))
    except Exception as e:
        return jsonify({"error": f"Error al procesar el formato del archivo: {str(e)}"}), 400

    # ---------------------------------------------------------------------
    # Paso 1: Encontrar la PLACA del vehículo (Primeras 10 filas)
    # ---------------------------------------------------------------------
    placa_detectada = None
    for fila in reader[:10]:
        for i, celda in enumerate(fila):
            if "PLACA" in str(celda).upper():
                for item_posterior in fila[i+1:]:
                    if item_posterior.strip():
                        placa_detectada = item_posterior.strip().replace(" ", "").upper()
                        break
        if placa_detectada:
            break

    if not placa_detectada:
        return jsonify({"error": "No se pudo identificar la celda 'PLACA' en el encabezado del documento"}), 400

    # Buscar el vehículo real en tu base de datos utilizando la placa mapeada
    vehiculo = Vehiculo.query.filter_by(placa=placa_detectada).first()
    if not vehiculo:
        return jsonify({
            "error": f"El vehículo con placa '{placa_detectada}' no existe en la base de datos. Regístralo primero."
        }), 404

    # ---------------------------------------------------------------------
    # Paso 2: Identificar las filas de SISTEMAS y FRECUENCIAS
    # ---------------------------------------------------------------------
    fila_sistemas = None
    fila_frecuencias = None
    indice_inicio_columnas = None

    for idx, fila in enumerate(reader):
        if any("SISTEMA" in str(celda).upper() or "LLANTAS" in str(celda).upper() for celda in fila):
            fila_sistemas = fila
            if "KM" in "".join(reader[idx + 1]).upper() or "CADA" in "".join(reader[idx + 1]).upper():
                fila_frecuencias = reader[idx + 1]
            else:
                fila_frecuencias = reader[idx + 2]
            
            for s_idx, celda in enumerate(fila_sistemas):
                if "SISTEMA" in str(celda).upper() or "LLANTAS" in str(celda).upper():
                    indice_inicio_columnas = s_idx
                    break
            break

    if not fila_sistemas or not fila_frecuencias or indice_inicio_columnas is None:
        return jsonify({"error": "No se localizó la estructura de Sistemas/Frecuencias en las cabeceras"}), 400

    # ---------------------------------------------------------------------
    # Paso 3: Vincular el plan de mantenimiento al Vehículo
    # ---------------------------------------------------------------------
    items_vinculados = 0
    sistema_actual = "GENERAL"

    for i in range(indice_inicio_columnas, len(fila_sistemas)):
        if i >= len(fila_frecuencias):
            break
            
        if fila_sistemas[i].strip():
            sistema_actual = fila_sistemas[i].strip().upper()
            
        texto_frecuencia = fila_frecuencias[i].strip()
        if not texto_frecuencia or any(k in texto_frecuencia.lower() for k in ['proveedor', 'soporte', 'observaciones']):
            continue
            
        km_frecuencia = limpiar_km(texto_frecuencia)
        if km_frecuencia == 0:
            continue

        # CALCULO DE LA ALERTA: Frecuencia menos los kilómetros de anticipación que requiere el usuario
        # Ejemplo: Si se hace cada 15,000 km y pides alerta con 1,500 km de anticipación -> Alerta en 13,500 km.
        # Evitamos que de valores negativos si la frecuencia es muy pequeña.
        valor_calculado_alerta = max(100, km_frecuencia - km_anticipacion_alerta)

        nombre_item = f"Mantenimiento {sistema_actual} ({texto_frecuencia})"

        # A) Buscar o crear el PlanItem maestro en el catálogo global de la BD
        plan_item = PlanItem.query.filter_by(sistema=sistema_actual, frecuencia_valor=km_frecuencia).first()
        if not plan_item:
            plan_item = PlanItem(
                sistema=sistema_actual,
                nombre=nombre_item,
                descripcion=f"Control dinámico cargado desde Excel para {sistema_actual.lower()}",
                tipo_mantenimiento="PREVENTIVO",
                tipo_control="KM",
                frecuencia_valor=km_frecuencia,
                alerta_valor=valor_calculado_alerta, 
                obligatorio=True,
                activo=True
            )
            db.session.add(plan_item)
            db.session.flush() # Obtener ID temporalmente sin cerrar la transacción
            
        # B) Vincular el plan al vehículo si no lo tiene asignado previamente
        vpi = VehiculoPlanItem.query.filter_by(vehiculo_id=vehiculo.id, plan_item_id=plan_item.id).first()
        if not vpi:
            vpi = VehiculoPlanItem(
                vehiculo_id=vehiculo.id,
                plan_item_id=plan_item.id,
                tipo_control="KM",
                frecuencia_valor=km_frecuencia,
                alerta_valor=valor_calculado_alerta,
                ultimo_km=vehiculo.km_actual or 0,  # Arranca desde el kilometraje que tiene el carro hoy
                ultima_fecha=datetime.today().date(),
                activo=True
            )
            db.session.add(vpi)
            items_vinculados += 1

    # Persistir los planes en la base de datos de forma segura
    db.session.commit()

    return jsonify({
        "status": "success",
        "codigo_respuesta": 200,
        "data": {
            "placa_procesada": vehiculo.placa,
            "vehiculo_id": vehiculo.id,
            "nuevos_sistemas_parametrizados": items_vinculados,
            "anticipacion_alerta_km": km_anticipacion_alerta
        },
        "mensaje": "Plan de mantenimiento inicializado con éxito. Alertas calculadas dinámicamente."
    }), 200