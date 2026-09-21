from models import (
    db,
    Alerta,
    Vehiculo,
    VehiculoPlanItem,
    VehiculoDocumento,
    VehiculoUbicacionActual,
    MaquinariaMantenimiento,
    Maquinaria,
    
    MaquinariaPlanItem,
    MaquinariaDocumento
)

from datetime import datetime, date

# sockets
from sockets.socket_handler import socketio
from services.email_service import enviar_email_alerta
from datetime import datetime
from zoneinfo import ZoneInfo

datetime.now(ZoneInfo("America/Bogota"))
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

    # =====================================================
    # PREOPERACIONALES Y ANOMALÍAS
    # SIEMPRE CREAN HISTÓRICO
    # =====================================================

    if tipo in ["PREOPERACIONAL", "ANOMALIA"]:

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
            estado="ACTIVA",

            origen=origen,

            fecha_evento=datetime.now(
                ZoneInfo("America/Bogota")
            ),

            metadata_json=metadata

        )

        db.session.add(alerta)
        db.session.commit()

        socketio.emit(
            "nueva_alerta",
            alerta.to_dict()
        )

        try:

            if prioridad in ["CRITICA", "ALTA"]:

                enviar_email_alerta(alerta)

        except Exception as e:

            print(
                "Error enviando email alerta:",
                e
            )

        return alerta

    # =====================================================
    # RESTO DE ALERTAS
    # EVITAR DUPLICADOS
    # =====================================================

    query = Alerta.query.filter_by(
        tipo=tipo,
        categoria=categoria,
        estado="ACTIVA"
    )

    # =====================================================
    # VEHÍCULO
    # =====================================================

    if vehiculo_id:

        query = query.filter_by(
            vehiculo_id=vehiculo_id
        )

    if vehiculo_plan_item_id:

        query = query.filter_by(
            vehiculo_plan_item_id=vehiculo_plan_item_id
        )

    # =====================================================
    # MAQUINARIA
    # =====================================================

    if maquinaria_id:

        query = query.filter_by(
            maquinaria_id=maquinaria_id
        )

    if maquinaria_plan_item_id:

        query = query.filter_by(
            maquinaria_plan_item_id=maquinaria_plan_item_id
        )

    # =====================================================
    # BUSCAR ALERTA EXISTENTE
    #
    # PARA MAQUINARIA RECURRENTE:
    #
    # La combinación real es:
    #
    # maquinaria_plan_item_id
    # +
    # horas_programadas
    #
    # =====================================================

    alerta_existente = None

    if (
        maquinaria_plan_item_id
        and metadata
        and metadata.get("horas_programadas") is not None
    ):

        horas_programadas = int(
            metadata.get(
                "horas_programadas"
            )
        )

        candidatos = query.all()

        for alerta in candidatos:

            alerta_metadata = (
                alerta.metadata_json or {}
            )

            alerta_horas_programadas = (
                alerta_metadata.get(
                    "horas_programadas"
                )
            )

            if alerta_horas_programadas is None:
                continue

            try:

                if int(
                    alerta_horas_programadas
                ) == horas_programadas:

                    alerta_existente = alerta
                    break

            except (TypeError, ValueError):

                continue

    else:

        # =================================================
        # COMPORTAMIENTO ANTERIOR
        #
        # Se mantiene para las demás alertas,
        # especialmente vehículos.
        # =================================================

        alerta_existente = query.first()

    # =====================================================
    # ACTUALIZAR ALERTA EXISTENTE
    # =====================================================

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

        if hubo_cambios:

            alerta_existente.fecha_evento = (
                datetime.now(
                    ZoneInfo("America/Bogota")
                )
            )

            db.session.commit()

            socketio.emit(
                "alerta_actualizada",
                alerta_existente.to_dict()
            )

            if prioridad == "CRITICA":

                try:

                    enviar_email_alerta(
                        alerta_existente
                    )

                except Exception as e:

                    print(
                        "Error enviando email:",
                        e
                    )

        return alerta_existente

    # =====================================================
    # CREAR NUEVA ALERTA
    # =====================================================

    alerta = Alerta(

        vehiculo_id=vehiculo_id,
        maquinaria_id=maquinaria_id,
        viaje_id=viaje_id,

        mantenimiento_id=mantenimiento_id,
        maquinaria_mantenimiento_id=(
            maquinaria_mantenimiento_id
        ),

        plan_item_id=plan_item_id,

        vehiculo_plan_item_id=(
            vehiculo_plan_item_id
        ),

        maquinaria_plan_item_id=(
            maquinaria_plan_item_id
        ),

        tipo=tipo,
        categoria=categoria,

        titulo=titulo,
        mensaje=mensaje,

        prioridad=prioridad,
        estado="ACTIVA",

        origen=origen,

        fecha_evento=datetime.now(
            ZoneInfo("America/Bogota")
        ),

        metadata_json=metadata

    )

    db.session.add(alerta)

    db.session.commit()

    socketio.emit(
        "nueva_alerta",
        alerta.to_dict()
    )

    try:

        if prioridad in ["CRITICA", "ALTA"]:

            enviar_email_alerta(alerta)

    except Exception as e:

        print(
            "Error enviando email alerta:",
            e
        )

    return alerta


def resolver_alerta(alerta_id):

    alerta = Alerta.query.get(alerta_id)

    if not alerta:
        return None

    alerta.estado = 'RESUELTA'
    alerta.fecha_resolucion = datetime.now(ZoneInfo("America/Bogota"))

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
        alerta.fecha_resolucion = datetime.now(ZoneInfo("America/Bogota"))

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
        alerta.fecha_resolucion = datetime.now(ZoneInfo("America/Bogota"))

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
    maquinaria_plan_item_id,
    horas_programadas
):

    alertas = Alerta.query.filter_by(
        tipo="MANTENIMIENTO",
        maquinaria_plan_item_id=maquinaria_plan_item_id,
        estado="ACTIVA"
    ).all()

    for alerta in alertas:

        metadata = alerta.metadata_json or {}

        alerta_horas_programadas = (
            metadata.get("horas_programadas")
        )

        if alerta_horas_programadas is None:
            continue

        try:

            if int(alerta_horas_programadas) != int(
                horas_programadas
            ):
                continue

        except (TypeError, ValueError):

            continue

        alerta.estado = "RESUELTA"

        alerta.fecha_resolucion = (
            datetime.now(
                ZoneInfo("America/Bogota")
            )
        )

        socketio.emit(
            "alerta_resuelta",
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
        alerta.fecha_resolucion = datetime.now(ZoneInfo("America/Bogota"))

    db.session.commit()

    return True

def generar_alertas_maquinaria():

    items = MaquinariaPlanItem.query.filter_by(
        activo=True
    ).all()

    for item in items:

        maquinaria = item.maquinaria

        if not maquinaria:
            continue

        if not item.frecuencia_horas:
            continue

        # =====================================================
        # DATOS BASE
        # =====================================================

        actual = int(
            maquinaria.horometro_actual or 0
        )

        base = int(
            item.horas_base or 0
        )

        frecuencia = int(
            item.frecuencia_horas
        )

        alerta_horas = int(
            item.alerta_horas or 0
        )

        primera_ocurrencia = base + frecuencia

        # =====================================================
        # OBTENER MANTENIMIENTOS YA REALIZADOS
        # =====================================================

        realizadas = {
            m.horas_programadas
            for m in MaquinariaMantenimiento.query.filter_by(
                maquinaria_id=maquinaria.id,
                maquinaria_plan_item_id=item.id,
                completado=True
            ).all()
            if m.horas_programadas is not None
        }

        # =====================================================
        # DETERMINAR HASTA QUÉ OCURRENCIA DEBEMOS REVISAR
        #
        # Incluimos:
        # - todas las ocurrencias vencidas
        # - las que están dentro del rango de alerta
        # =====================================================

        limite = actual + alerta_horas

        if limite < primera_ocurrencia:
            continue

        cantidad = (
            (limite - base) // frecuencia
        )

        ocurrencias = [
            base + (frecuencia * i)
            for i in range(1, cantidad + 1)
        ]

        # =====================================================
        # REVISAR CADA OCURRENCIA
        # =====================================================

        for horas_programadas in ocurrencias:

            # Ya fue realizada
            if horas_programadas in realizadas:
                resolver_alertas_mantenimiento_maquinaria(
                    item.id,
                    horas_programadas
                )
                continue

            horas_restantes = (
                horas_programadas - actual
            )

            # =================================================
            # DETERMINAR ESTADO
            # =================================================

            if horas_programadas <= actual:

                estado = "VENCIDO"
                prioridad = "CRITICA"

            elif horas_restantes <= alerta_horas:

                estado = "PENDIENTE"
                prioridad = "ALTA"

            else:

                # No necesita alerta todavía
                continue

            # =================================================
            # METADATA DE LA OCURRENCIA
            # =================================================

            metadata = {

                "maquinaria": maquinaria.codigo,

                "plan_item": (
                    item.plan_item.nombre
                    if item.plan_item
                    else None
                ),

                "horometro_actual": actual,

                "horas_programadas": horas_programadas,

                "horas_restantes": horas_restantes,

                "frecuencia_horas": frecuencia,

                "alerta_horas": alerta_horas,

                "horas_base": base,

                "ultima_horas": item.ultima_horas,

                "estado_calculado": estado

            }

            # =================================================
            # CREAR / ACTUALIZAR ALERTA
            # =================================================

            crear_alerta(

                tipo="MANTENIMIENTO",

                categoria=estado,

                maquinaria_id=maquinaria.id,

                plan_item_id=item.plan_item_id,

                maquinaria_plan_item_id=item.id,

                titulo=(
                    f"Mantenimiento {estado}"
                ),

                mensaje=(
                    f"Maquinaria {maquinaria.codigo} "
                    f"requiere mantenimiento "
                    f"{item.plan_item.nombre} "
                    f"a las {horas_programadas} horas. "
                    f"Horómetro actual: {actual} horas."
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