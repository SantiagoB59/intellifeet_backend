from models import (
    db,
    Alerta,
    Vehiculo,
    VehiculoPlanItem,
    VehiculoDocumento,
    VehiculoUbicacionActual,
    
    Maquinaria,
    MaquinariaPlanItem,
    MaquinariaDocumento
)

from datetime import datetime, date

# sockets
from sockets.socket_handler import socketio
from services.email_service import enviar_email_alerta

# =========================================================
# CREAR ALERTA
# =========================================================

def crear_alerta(
    tipo,
    categoria,

    titulo,
    mensaje,

    prioridad='MEDIA',
    origen='SISTEMA',

    vehiculo_id=None,
    maquinaria_id=None,

    viaje_id=None,

    mantenimiento_id=None,
    maquinaria_mantenimiento_id=None,

    plan_item_id=None,

    vehiculo_plan_item_id=None,
    maquinaria_plan_item_id=None,

    metadata=None
):

    """
    Evita crear alertas duplicadas ACTIVAS
    """

    query = Alerta.query.filter_by(
        tipo=tipo,
        categoria=categoria,
        estado='ACTIVA'
    )

    # -----------------------------------------
    # VEHÍCULO
    # -----------------------------------------
    if vehiculo_id:
        query = query.filter_by(
            vehiculo_id=vehiculo_id
        )

    if maquinaria_id:
        query = query.filter_by(
            maquinaria_id=maquinaria_id
        )

    if vehiculo_plan_item_id:
        query = query.filter_by(
            vehiculo_plan_item_id=vehiculo_plan_item_id
        )

    if maquinaria_plan_item_id:
        query = query.filter_by(
            maquinaria_plan_item_id=maquinaria_plan_item_id
        )

    # -----------------------------------------
    # PLAN ITEM
    # -----------------------------------------
    if vehiculo_plan_item_id:
        query = query.filter_by(
            vehiculo_plan_item_id=vehiculo_plan_item_id
        )

    alerta_existente = query.first()

    if alerta_existente:

        hubo_cambios = False

        if alerta_existente.titulo != titulo:
            alerta_existente.titulo = titulo
            hubo_cambios = True

        if alerta_existente.mensaje != mensaje:
            alerta_existente.mensaje = mensaje
            hubo_cambios = True

        if alerta_existente.prioridad != prioridad:
            alerta_existente.prioridad = prioridad
            hubo_cambios = True

        if alerta_existente.metadata_json != metadata:
            alerta_existente.metadata_json = metadata
            hubo_cambios = True

        # Actualiza la fecha del último evento
        if hubo_cambios:

            alerta_existente.fecha_evento = datetime.utcnow()

            db.session.commit()

            socketio.emit(
                "alerta_actualizada",
                alerta_existente.to_dict()
            )

            if prioridad == "CRITICA":
                try:
                    enviar_email_alerta(alerta_existente)
                except Exception as e:
                    print("Error enviando email:", e)

        return alerta_existente

    # -----------------------------------------
    # CREAR ALERTA
    # -----------------------------------------
    alerta = Alerta(

        vehiculo_id=vehiculo_id,
        maquinaria_id=maquinaria_id,
        viaje_id=viaje_id,

        mantenimiento_id=mantenimiento_id,
        maquinaria_mantenimiento_id=maquinaria_mantenimiento_id,
        plan_item_id=plan_item_id,
        vehiculo_plan_item_id=vehiculo_plan_item_id,
        maquinaria_plan_item_id=maquinaria_plan_item_id,

        tipo=tipo,
        categoria=categoria,

        titulo=titulo,
        mensaje=mensaje,

        prioridad=prioridad,
        estado='ACTIVA',

        origen=origen,

        fecha_evento=datetime.utcnow(),

        metadata_json=metadata
    )

    db.session.add(alerta)
    db.session.commit()

    # -----------------------------------------
    # SOCKET (TIEMPO REAL)
    # -----------------------------------------
    socketio.emit(
        'nueva_alerta',
        alerta.to_dict()
    )

    # -----------------------------------------
    # EMAIL (solo críticas y altas)
    # -----------------------------------------
    try:

        if prioridad in ['CRITICA', 'ALTA']:

            enviar_email_alerta(alerta)

    except Exception as e:

        print("Error enviando email alerta:", e)

    return alerta
# =========================================================
# RESOLVER ALERTA
# =========================================================

def resolver_alerta(alerta_id):

    alerta = Alerta.query.get(alerta_id)

    if not alerta:
        return None

    alerta.estado = 'RESUELTA'
    alerta.fecha_resolucion = datetime.utcnow()

    db.session.commit()

    socketio.emit(
        'alerta_resuelta',
        alerta.to_dict()
    )

    return alerta


# =========================================================
# RESOLVER ALERTAS MANTENIMIENTO
# =========================================================

def resolver_alertas_mantenimiento(
    vehiculo_plan_item_id
):

    alertas = Alerta.query.filter_by(
        tipo='MANTENIMIENTO',
        vehiculo_plan_item_id=vehiculo_plan_item_id,
        estado='ACTIVA'
    ).all()

    for alerta in alertas:

        alerta.estado = 'RESUELTA'
        alerta.fecha_resolucion = datetime.utcnow()

        socketio.emit(
            'alerta_resuelta',
            alerta.to_dict()
        )

    db.session.commit()

    return True

# =========================================================
# RESOLVER ALERTAS DOCUMENTOS
# =========================================================

def resolver_alertas_documento(
    vehiculo_id,
    categoria
):

    alertas = Alerta.query.filter_by(
        tipo='DOCUMENTO',
        categoria=categoria,
        vehiculo_id=vehiculo_id,
        estado='ACTIVA'
    ).all()

    for alerta in alertas:

        alerta.estado = 'RESUELTA'
        alerta.fecha_resolucion = datetime.utcnow()

    db.session.commit()

    return True


# =========================================================
# ALERTAS MANTENIMIENTO VEHÍCULOS
# =========================================================

def generar_alertas_vehiculos():

    items = VehiculoPlanItem.query.filter_by(
        activo=True
    ).all()

    for item in items:

        estado = item.calcular_estado()

        # -----------------------------------------
        # SI YA NO NECESITA ALERTA
        # -----------------------------------------

        if estado not in ['PENDIENTE', 'VENCIDO']:

            resolver_alertas_mantenimiento(
                vehiculo_plan_item_id=item.id
            )

            continue

        vehiculo = item.vehiculo

        prioridad = (
            'CRITICA'
            if estado == 'VENCIDO'
            else 'ALTA'
        )

        metadata = {

            'vehiculo': vehiculo.placa,

            'plan_item': item.plan_item.nombre,

            'km_actual': vehiculo.km_actual,

            'ultimo_km': item.ultimo_km,

            'frecuencia': item.frecuencia_valor,

            'estado_calculado': estado
        }

        crear_alerta(

            tipo='MANTENIMIENTO',

            categoria=estado,

            vehiculo_id=vehiculo.id,

            plan_item_id=item.plan_item_id,

            vehiculo_plan_item_id=item.id,

            titulo=f"Mantenimiento {estado}",

            mensaje=(
                f"Vehículo {vehiculo.placa} "
                f"requiere mantenimiento "
                f"{item.plan_item.nombre}"
            ),

            prioridad=prioridad,

            metadata=metadata
        )


# =========================================================
# ALERTAS DOCUMENTOS
# =========================================================

def generar_alertas_documentos():

    documentos = VehiculoDocumento.query.all()

    hoy = date.today()

    for doc in documentos:

        if not doc.fecha_vencimiento:
            continue

        dias = (
            doc.fecha_vencimiento - hoy
        ).days

        # -----------------------------------------
        # DOCUMENTO OK
        # -----------------------------------------

        if dias > 15:

            resolver_alertas_documento(
                vehiculo_id=doc.vehiculo_id,
                categoria=doc.documento_tipo.nombre
            )

            continue

        prioridad = (
            'CRITICA'
            if dias <= 0
            else 'MEDIA'
        )

        estado = (
            'VENCIDO'
            if dias <= 0
            else 'POR_VENCER'
        )

        metadata = {

            'documento': doc.documento_tipo.nombre,

            'fecha_vencimiento': (
                doc.fecha_vencimiento.isoformat()
            ),

            'dias_restantes': dias,

            'estado': estado
}

        # -----------------------------------------
# MENSAJE
# -----------------------------------------

        if dias > 1:

            mensaje = (
                f"{doc.documento_tipo.nombre} vence en {dias} días"
            )

        elif dias == 1:

            mensaje = (
                f"{doc.documento_tipo.nombre} vence mañana"
            )

        elif dias == 0:

            mensaje = (
                f"{doc.documento_tipo.nombre} vence hoy"
            )

        else:

            mensaje = (
                f"{doc.documento_tipo.nombre} venció hace {abs(dias)} días"
            )

# -----------------------------------------
# CREAR / ACTUALIZAR ALERTA
# -----------------------------------------

        crear_alerta(

            tipo='DOCUMENTO',

            categoria=doc.documento_tipo.nombre,

            vehiculo_id=doc.vehiculo_id,

            titulo=f"Documento {estado}",

            mensaje=mensaje,

            prioridad=prioridad,

            metadata=metadata
        )

# =========================================================
# ALERTAS GPS VELOCIDAD
# =========================================================

def generar_alertas_velocidad():

    ubicaciones = VehiculoUbicacionActual.query.all()

    LIMITE = 80

    for ubicacion in ubicaciones:

        if not ubicacion.speed:
            continue

        velocidad = ubicacion.speed

        if velocidad <= LIMITE:
            continue

        vehiculo = Vehiculo.query.get(
            ubicacion.vehiculo_id
        )

        if not vehiculo:
            continue

        prioridad = (
            'CRITICA'
            if velocidad >= 100
            else 'ALTA'
        )

        metadata = {

            'velocidad_detectada': velocidad,

            'limite_permitido': LIMITE,

            'gps_id': ubicacion.gps_id,

            'latitud': float(ubicacion.latitude),

            'longitud': float(ubicacion.longitude),

            'direccion': ubicacion.direccion_texto,

            'ciudad': ubicacion.ciudad
        }

        crear_alerta(

            tipo='GPS',

            categoria='EXCESO_VELOCIDAD',

            vehiculo_id=vehiculo.id,

            titulo='Exceso de velocidad',

            mensaje=(
                f"Vehículo {vehiculo.placa} "
                f"superó límite permitido "
                f"({velocidad} km/h)"
            ),

            prioridad=prioridad,

            origen='GPS',

            metadata=metadata
        )


# =========================================================
# ALERTAS GPS VEHÍCULO APAGADO
# =========================================================

def generar_alertas_apagado():

    ubicaciones = VehiculoUbicacionActual.query.all()

    for ubicacion in ubicaciones:

        if ubicacion.ignition != 0:
            continue

        vehiculo = Vehiculo.query.get(
            ubicacion.vehiculo_id
        )

        if not vehiculo:
            continue

        metadata = {

            'evento': ubicacion.evento,

            'direccion': ubicacion.direccion_texto,

            'ciudad': ubicacion.ciudad
        }

        crear_alerta(

            tipo='GPS',

            categoria='VEHICULO_APAGADO',

            vehiculo_id=vehiculo.id,

            titulo='Vehículo apagado',

            mensaje=(
                f"Vehículo {vehiculo.placa} "
                f"se encuentra apagado"
            ),

            prioridad='BAJA',

            origen='GPS',

            metadata=metadata
        )


# =========================================================
# EJECUTAR MOTOR COMPLETO
# =========================================================

def ejecutar_motor_alertas():

    generar_alertas_vehiculos()
    
    generar_alertas_maquinaria()

    generar_alertas_documentos()
    
    generar_alertas_documentos_maquinaria()

    generar_alertas_velocidad()

    # generar_alertas_apagado()


# =========================================================
# OBTENER TODAS
# =========================================================

def obtener_todas_alertas():

    alertas = Alerta.query.order_by(
        Alerta.created_at.desc()
    ).all()

    return [
        a.to_dict()
        for a in alertas
    ]


# =========================================================
# OBTENER ACTIVAS
# =========================================================

def obtener_alertas_activas():

    alertas = Alerta.query.filter_by(
        estado='ACTIVA'
    ).order_by(
        Alerta.created_at.desc()
    ).all()

    return [
        a.to_dict()
        for a in alertas
    ]


# =========================================================
# ESTADÍSTICAS
# =========================================================

def obtener_estadisticas_alertas():

    total = Alerta.query.count()

    activas = Alerta.query.filter_by(
        estado='ACTIVA'
    ).count()

    resueltas = Alerta.query.filter_by(
        estado='RESUELTA'
    ).count()

    criticas = Alerta.query.filter_by(
        prioridad='CRITICA',
        estado='ACTIVA'
    ).count()

    return {

        'total': total,

        'activas': activas,

        'resueltas': resueltas,

        'criticas': criticas
    }
    
    
# ========================================================
# OBTENER ALERTAS maquinaria
# ========================================================
def resolver_alertas_mantenimiento_maquinaria(
    maquinaria_plan_item_id
):

    alertas = Alerta.query.filter_by(
        tipo='MANTENIMIENTO',
        maquinaria_plan_item_id=maquinaria_plan_item_id,
        estado='ACTIVA'
    ).all()

    for alerta in alertas:

        alerta.estado = 'RESUELTA'
        alerta.fecha_resolucion = datetime.utcnow()

        socketio.emit(
            'alerta_resuelta',
            alerta.to_dict()
        )

    db.session.commit()

    return True


def resolver_alertas_documento_maquinaria(
    maquinaria_id,
    categoria
):

    alertas = Alerta.query.filter_by(
        tipo='DOCUMENTO',
        categoria=categoria,
        maquinaria_id=maquinaria_id,
        estado='ACTIVA'
    ).all()

    for alerta in alertas:

        alerta.estado = 'RESUELTA'
        alerta.fecha_resolucion = datetime.utcnow()

    db.session.commit()

    return True



def generar_alertas_maquinaria():

    items = MaquinariaPlanItem.query.filter_by(
        activo=True
    ).all()

    for item in items:

        estado = item.calcular_estado()

        if estado not in ['PENDIENTE', 'VENCIDO']:

            resolver_alertas_mantenimiento_maquinaria(
                item.id
            )

            continue

        maquinaria = item.maquinaria

        prioridad = (
            'CRITICA'
            if estado == 'VENCIDO'
            else 'ALTA'
        )

        metadata = {

            'maquinaria': maquinaria.codigo,

            'plan_item': item.plan_item.nombre,

            'horometro_actual': maquinaria.horometro_actual,

            'ultima_horas': item.ultima_horas,

            'frecuencia_horas': item.frecuencia_horas,

            'estado_calculado': estado

        }

        crear_alerta(

            tipo='MANTENIMIENTO',

            categoria=estado,

            maquinaria_id=maquinaria.id,

            plan_item_id=item.plan_item_id,

            maquinaria_plan_item_id=item.id,

            titulo=f"Mantenimiento {estado}",

            mensaje=(
                f"Maquinaria {maquinaria.codigo} "
                f"requiere mantenimiento "
                f"{item.plan_item.nombre}"
            ),

            prioridad=prioridad,

            metadata=metadata
        )
        
def generar_alertas_documentos_maquinaria():

    documentos = MaquinariaDocumento.query.all()

    hoy = date.today()

    for doc in documentos:

        if not doc.fecha_vencimiento:
            continue

        dias = (
            doc.fecha_vencimiento - hoy
        ).days

        if dias > 15:

            resolver_alertas_documento_maquinaria(
                maquinaria_id=doc.maquinaria_id,
                categoria=doc.documento_tipo.nombre
            )

            continue

        prioridad = (
            'CRITICA'
            if dias <= 0
            else 'MEDIA'
        )

        estado = (
            'VENCIDO'
            if dias <= 0
            else 'POR_VENCER'
        )

        metadata = {

            'documento': doc.documento_tipo.nombre,

            'fecha_vencimiento': doc.fecha_vencimiento.isoformat(),

            'dias_restantes': dias,

            'estado': estado

        }

        if dias > 1:

            mensaje = (
                f"{doc.documento_tipo.nombre} vence en {dias} días"
            )

        elif dias == 1:

            mensaje = (
                f"{doc.documento_tipo.nombre} vence mañana"
            )

        elif dias == 0:

            mensaje = (
                f"{doc.documento_tipo.nombre} vence hoy"
            )

        else:

            mensaje = (
                f"{doc.documento_tipo.nombre} venció hace {abs(dias)} días"
            )

        crear_alerta(

            tipo='DOCUMENTO',

            categoria=doc.documento_tipo.nombre,

            maquinaria_id=doc.maquinaria_id,

            titulo=f"Documento {estado}",

            mensaje=mensaje,

            prioridad=prioridad,

            metadata=metadata
        )