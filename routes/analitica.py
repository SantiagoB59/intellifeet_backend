from datetime import datetime, date, timedelta
from collections import defaultdict
from math import isfinite

from flask import Blueprint, request, jsonify
from sqlalchemy import func, and_, or_

from extensions import db

from models import (
    Vehiculo,
    TipoVehiculo,
    VehiculoTracking,
    Maquinaria,
    MaquinariaHoras,
    Viaje,
    Mantenimiento,
    MaquinariaMantenimiento,
    VehiculoPlanItem,
    MaquinariaPlanItem,
    Alerta,
    Inspeccion,
)


analitica_bp = Blueprint(
    "analitica",
    __name__,
    url_prefix="/api/analitica"
)


# ============================================================
# CONFIGURACIÓN DE CONSUMO ESTIMADO
# ============================================================

# Litros por kilómetro.
#
# Estos valores son REFERENCIALES y deben ajustarse
# posteriormente según cada vehículo real.
#
# Ejemplo:
# 0.30 L/km = 30 litros cada 100 km
#
CONSUMO_VEHICULO_L_KM = {

    "CAMIONETA": 0.12,

    "CAMION": 0.25,

    "VOLQUETA": 0.35,

    "CARROTANQUE": 0.35,

    "TRACTOMULA": 0.40,

    "MINI-TRACTOMULA": 0.35,

    "MINI TRACTOMULA": 0.35,
}


# Consumo estimado de maquinaria.
# Litros por hora.

CONSUMO_MAQUINARIA_L_H = {

    "RETROEXCAVADORA": 6.0,

    "EXCAVADORA": 8.0,

    "MOTONIVELADORA": 10.0,

    "CARGADOR": 8.0,

    "BULLDOZER": 12.0,

}


# Valores de referencia configurables.
#
# IMPORTANTE:
# No representan abastecimientos reales.
# El sistema los utiliza únicamente para estimar
# el costo de combustible.

PRECIO_DIESEL = 10500.0
PRECIO_GASOLINA = 15500.0


# ============================================================
# UTILIDADES
# ============================================================

def numero(valor, decimales=2):

    if valor is None:
        return 0

    try:

        valor = float(valor)

        if not isfinite(valor):
            return 0

        return round(valor, decimales)

    except (TypeError, ValueError):

        return 0


def porcentaje(parte, total):

    if not total:
        return 0

    return numero(
        (parte / total) * 100
    )


def obtener_periodo():

    try:
        dias = int(
            request.args.get(
                "periodo",
                30
            )
        )

    except (TypeError, ValueError):

        dias = 30

    if dias not in [7, 30, 90, 365]:
        dias = 30

    fecha_fin = date.today()

    fecha_inicio = (
        fecha_fin -
        timedelta(days=dias - 1)
    )

    return fecha_inicio, fecha_fin, dias


def obtener_filtros():

    tipo_activo = (
        request.args
        .get("tipo_activo", "TODOS")
        .upper()
    )

    if tipo_activo not in [
        "TODOS",
        "VEHICULOS",
        "MAQUINARIA"
    ]:

        tipo_activo = "TODOS"

    activo_id = request.args.get(
        "activo_id"
    )

    if activo_id in [
        None,
        "",
        "TODOS",
        "undefined",
        "null"
    ]:

        activo_id = None

    else:

        try:
            activo_id = int(activo_id)

        except (TypeError, ValueError):

            activo_id = None

    return tipo_activo, activo_id


# ============================================================
# VEHÍCULOS SELECCIONADOS
# ============================================================

def obtener_vehiculos(
    tipo_activo,
    activo_id
):

    if tipo_activo == "MAQUINARIA":
        return []

    query = Vehiculo.query.filter(
        Vehiculo.activo.is_(True)
    )

    if tipo_activo == "VEHICULOS":

        query = query.filter(
            Vehiculo.activo.is_(True)
        )

    if activo_id is not None:

        query = query.filter(
            Vehiculo.id == activo_id
        )

    return query.all()


# ============================================================
# MAQUINARIA SELECCIONADA
# ============================================================

def obtener_maquinaria(
    tipo_activo,
    activo_id
):

    if tipo_activo == "VEHICULOS":
        return []

    query = Maquinaria.query.filter(
        Maquinaria.activo.is_(True)
    )

    if activo_id is not None:

        query = query.filter(
            Maquinaria.id == activo_id
        )

    return query.all()


# ============================================================
# KILÓMETROS VEHÍCULOS
# ============================================================

def calcular_km_vehiculo(
    vehiculo_id,
    fecha_inicio,
    fecha_fin
):

    inicio = datetime.combine(
        fecha_inicio,
        datetime.min.time()
    )

    fin = datetime.combine(
        fecha_fin + timedelta(days=1),
        datetime.min.time()
    )

    filas = (
        db.session.query(
            func.min(
                VehiculoTracking.odometro
            ).label("odometro_min"),

            func.max(
                VehiculoTracking.odometro
            ).label("odometro_max")
        )
        .filter(
            VehiculoTracking.vehiculo_id
            == vehiculo_id,

            VehiculoTracking.fecha_gps >= inicio,

            VehiculoTracking.fecha_gps < fin,

            VehiculoTracking.odometro.isnot(None)
        )
        .first()
    )

    if filas:

        minimo = numero(
            filas.odometro_min
        )

        maximo = numero(
            filas.odometro_max
        )

        if maximo >= minimo and maximo > 0:

            return numero(
                maximo - minimo
            )

    # --------------------------------------------------------
    # FALLBACK:
    # Si no existe histórico GPS, utilizamos viajes.
    # --------------------------------------------------------

    km_viajes = (
        db.session.query(
            func.coalesce(
                func.sum(
                    Viaje.km_recorrido
                ),
                0
            )
        )
        .filter(
            Viaje.vehiculo_id
            == vehiculo_id,

            Viaje.created_at >= inicio,

            Viaje.created_at < fin,

            Viaje.activo.is_(True)
        )
        .scalar()
    )

    return numero(km_viajes)


# ============================================================
# KM POR DÍA
# ============================================================

def calcular_grafica_km(
    vehiculos,
    fecha_inicio,
    fecha_fin
):

    if not vehiculos:
        return []

    inicio = datetime.combine(
        fecha_inicio,
        datetime.min.time()
    )

    fin = datetime.combine(
        fecha_fin + timedelta(days=1),
        datetime.min.time()
    )

    ids = [
        vehiculo.id
        for vehiculo in vehiculos
    ]

    filas = (
        db.session.query(
            VehiculoTracking.vehiculo_id,

            func.date(
                VehiculoTracking.fecha_gps
            ).label("fecha"),

            func.min(
                VehiculoTracking.odometro
            ).label("min_odometro"),

            func.max(
                VehiculoTracking.odometro
            ).label("max_odometro")
        )
        .filter(
            VehiculoTracking.vehiculo_id.in_(ids),

            VehiculoTracking.fecha_gps >= inicio,

            VehiculoTracking.fecha_gps < fin,

            VehiculoTracking.odometro.isnot(None)
        )
        .group_by(
            VehiculoTracking.vehiculo_id,

            func.date(
                VehiculoTracking.fecha_gps
            )
        )
        .all()
    )

    resultado = defaultdict(float)

    for fila in filas:

        minimo = numero(
            fila.min_odometro
        )

        maximo = numero(
            fila.max_odometro
        )

        recorrido = max(
            maximo - minimo,
            0
        )

        if recorrido > 0:

            resultado[
                str(fila.fecha)
            ] += recorrido

    # --------------------------------------------------------
    # Completar días faltantes.
    # --------------------------------------------------------

    datos = []

    cursor = fecha_inicio

    while cursor <= fecha_fin:

        datos.append({
            "fecha": str(cursor),
            "valor": numero(
                resultado.get(
                    str(cursor),
                    0
                )
            )
        })

        cursor += timedelta(days=1)

    return datos


# ============================================================
# HORAS MAQUINARIA
# ============================================================

def calcular_horas_maquinaria(
    maquinaria_id,
    fecha_inicio,
    fecha_fin
):

    inicio = datetime.combine(
        fecha_inicio,
        datetime.min.time()
    )

    fin = datetime.combine(
        fecha_fin + timedelta(days=1),
        datetime.min.time()
    )

    registros = (
        MaquinariaHoras.query
        .filter(
            MaquinariaHoras.maquinaria_id
            == maquinaria_id,

            MaquinariaHoras.fecha >= inicio,

            MaquinariaHoras.fecha < fin
        )
        .order_by(
            MaquinariaHoras.fecha.asc()
        )
        .all()
    )

    if len(registros) >= 2:

        inicial = numero(
            registros[0].horas
        )

        final = numero(
            registros[-1].horas
        )

        if final >= inicial:

            return numero(
                final - inicial
            )

    # --------------------------------------------------------
    # Fallback usando inspecciones.
    #
    # Esto es especialmente útil cuando las lecturas
    # vienen directamente de los preoperacionales.
    # --------------------------------------------------------

    inspecciones = (
        Inspeccion.query
        .filter(
            Inspeccion.maquinaria_id
            == maquinaria_id,

            Inspeccion.created_at >= inicio,

            Inspeccion.created_at < fin,

            Inspeccion.estado.in_([
                "FINALIZADA",
                "REVISADA"
            ]),

            Inspeccion.contador_inicial.isnot(None),

            Inspeccion.contador_final.isnot(None)
        )
        .all()
    )

    total = 0

    for inspeccion in inspecciones:

        inicial = numero(
            inspeccion.contador_inicial
        )

        final = numero(
            inspeccion.contador_final
        )

        if final >= inicial:

            total += (
                final - inicial
            )

    return numero(total)


# ============================================================
# CONSUMO VEHÍCULO
# ============================================================

def obtener_consumo_vehiculo(
    vehiculo
):

    nombre_tipo = ""

    if vehiculo.tipo_vehiculo:

        nombre_tipo = (
            vehiculo.tipo_vehiculo.nombre
            or ""
        )

    nombre_tipo = (
        nombre_tipo
        .strip()
        .upper()
    )

    consumo = (
        CONSUMO_VEHICULO_L_KM
        .get(
            nombre_tipo,
            0.25
        )
    )

    return numero(consumo)


# ============================================================
# CONSUMO MAQUINARIA
# ============================================================

def obtener_consumo_maquinaria(
    maquinaria
):

    nombre_tipo = ""

    if maquinaria.tipo_maquinaria:

        nombre_tipo = (
            maquinaria.tipo_maquinaria.nombre
            or ""
        )

    nombre_tipo = (
        nombre_tipo
        .strip()
        .upper()
    )

    consumo = (
        CONSUMO_MAQUINARIA_L_H
        .get(
            nombre_tipo,
            6.0
        )
    )

    return numero(consumo)


# ============================================================
# MANTENIMIENTO VEHÍCULOS
# ============================================================

def obtener_mantenimientos_vehiculos(
    ids,
    fecha_inicio,
    fecha_fin
):

    if not ids:

        return []

    return (
        Mantenimiento.query
        .filter(
            Mantenimiento.vehiculo_id.in_(ids),

            Mantenimiento.fecha >= fecha_inicio,

            Mantenimiento.fecha <= fecha_fin
        )
        .all()
    )


# ============================================================
# MANTENIMIENTO MAQUINARIA
# ============================================================

def obtener_mantenimientos_maquinaria(
    ids,
    fecha_inicio,
    fecha_fin
):

    if not ids:

        return []

    return (
        MaquinariaMantenimiento.query
        .filter(
            MaquinariaMantenimiento.maquinaria_id.in_(ids),

            MaquinariaMantenimiento.fecha >= fecha_inicio,

            MaquinariaMantenimiento.fecha <= fecha_fin
        )
        .all()
    )


# ============================================================
# COSTOS
# ============================================================

def calcular_costos(
    mantenimientos_vehiculos,
    mantenimientos_maquinaria,
    combustible_vehiculos,
    combustible_maquinaria
):

    costo_mantenimiento_vehiculos = sum(
        numero(m.costo)
        for m in mantenimientos_vehiculos
    )

    costo_mantenimiento_maquinaria = sum(
        numero(m.costo)
        for m in mantenimientos_maquinaria
    )

    mantenimiento = (
        costo_mantenimiento_vehiculos
        +
        costo_mantenimiento_maquinaria
    )

    combustible = (
        combustible_vehiculos
        +
        combustible_maquinaria
    )

    costo_total = (
        mantenimiento
        +
        combustible
    )

    return {

        "costoTotal": numero(
            costo_total
        ),

        "combustible": numero(
            combustible
        ),

        "mantenimiento": numero(
            mantenimiento
        ),

        # No existe actualmente un modelo
        # de otros costos.
        "otros": 0,

        "porcentajeCombustible":
            porcentaje(
                combustible,
                costo_total
            ),

        "porcentajeMantenimiento":
            porcentaje(
                mantenimiento,
                costo_total
            ),

        "porcentajeOtros":
            0,

        "mantenimientoVehiculos":
            numero(
                costo_mantenimiento_vehiculos
            ),

        "mantenimientoMaquinaria":
            numero(
                costo_mantenimiento_maquinaria
            )
    }


# ============================================================
# ESTADO MANTENIMIENTO
# ============================================================

def calcular_salud_mantenimiento(
    vehiculos,
    maquinaria,
    mantenimientos_vehiculos,
    mantenimientos_maquinaria
):

    completados = sum(
        1
        for mantenimiento
        in (
            mantenimientos_vehiculos
            +
            mantenimientos_maquinaria
        )
        if mantenimiento.completado
    )

    total_registrados = (
        len(mantenimientos_vehiculos)
        +
        len(mantenimientos_maquinaria)
    )

    pendientes = sum(
        1
        for mantenimiento
        in (
            mantenimientos_vehiculos
            +
            mantenimientos_maquinaria
        )
        if not mantenimiento.completado
    )

    # --------------------------------------------------------
    # Planes actualmente vencidos / pendientes
    # --------------------------------------------------------

    vencidos = 0
    planes_pendientes = 0

    for vehiculo in vehiculos:

        planes = (
            VehiculoPlanItem.query
            .filter(
                VehiculoPlanItem.vehiculo_id
                == vehiculo.id,

                VehiculoPlanItem.activo.is_(True)
            )
            .all()
        )

        for plan in planes:

            estado = plan.calcular_estado()

            if estado == "VENCIDO":

                vencidos += 1

            elif estado == "PENDIENTE":

                planes_pendientes += 1

    for maquina in maquinaria:

        planes = (
            MaquinariaPlanItem.query
            .filter(
                MaquinariaPlanItem.maquinaria_id
                == maquina.id,

                MaquinariaPlanItem.activo.is_(True)
            )
            .all()
        )

        for plan in planes:

            estado = plan.calcular_estado()

            if estado == "VENCIDO":

                vencidos += 1

            elif estado == "PENDIENTE":

                planes_pendientes += 1

    programados = (
        total_registrados
        +
        vencidos
        +
        planes_pendientes
    )

    cumplimiento = (
        porcentaje(
            completados,
            total_registrados
        )
        if total_registrados
        else 0
    )

    return {

        "porcentajeCumplimiento":
            numero(cumplimiento),

        "completados":
            completados,

        "pendientes":
            pendientes + planes_pendientes,

        "vencidos":
            vencidos,

        "total":
            programados
    }


# ============================================================
# ALERTAS DE MANTENIMIENTO
# ============================================================

def obtener_alertas_mantenimiento(
    fecha_inicio,
    fecha_fin,
    vehiculos,
    maquinaria
):

    ids_vehiculos = [
        v.id
        for v in vehiculos
    ]

    ids_maquinaria = [
        m.id
        for m in maquinaria
    ]

    filtros = []

    if ids_vehiculos:

        filtros.append(
            Alerta.vehiculo_id.in_(
                ids_vehiculos
            )
        )

    if ids_maquinaria:

        filtros.append(
            Alerta.maquinaria_id.in_(
                ids_maquinaria
            )
        )

    if not filtros:

        return []

    alertas = (
        Alerta.query
        .filter(
            or_(*filtros),

            Alerta.fecha_evento >=
            datetime.combine(
                fecha_inicio,
                datetime.min.time()
            ),

            Alerta.fecha_evento <
            datetime.combine(
                fecha_fin + timedelta(days=1),
                datetime.min.time()
            ),

            Alerta.estado == "ACTIVA"
        )
        .order_by(
            Alerta.fecha_evento.desc()
        )
        .limit(10)
        .all()
    )

    resultado = []

    for alerta in alertas:

        if alerta.vehiculo:

            activo = alerta.vehiculo.placa

        elif alerta.maquinaria:

            activo = alerta.maquinaria.codigo

        else:

            activo = "Sin activo"

        resultado.append({

            "id":
                alerta.id,

            "titulo":
                alerta.titulo
                or alerta.tipo
                or "Alerta",

            "activo":
                activo,

            "prioridad":
                alerta.prioridad,

            "fecha":
                (
                    alerta.fecha_evento.isoformat()
                    if alerta.fecha_evento
                    else None
                )
        })

    return resultado


# ============================================================
# VIAJES
# ============================================================

def calcular_operacion(
    vehiculos,
    maquinaria,
    fecha_inicio,
    fecha_fin
):

    ids_vehiculos = [
        v.id
        for v in vehiculos
    ]

    inicio = datetime.combine(
        fecha_inicio,
        datetime.min.time()
    )

    fin = datetime.combine(
        fecha_fin + timedelta(days=1),
        datetime.min.time()
    )

    query = (
        Viaje.query
        .filter(
            Viaje.created_at >= inicio,

            Viaje.created_at < fin,

            Viaje.activo.is_(True)
        )
    )

    if ids_vehiculos:

        query = query.filter(
            Viaje.vehiculo_id.in_(
                ids_vehiculos
            )
        )

    else:

        query = query.filter(
            db.literal(False)
        )

    viajes = query.all()

    finalizados = sum(
        1
        for viaje in viajes
        if str(viaje.estado).upper()
        in [
            "FINALIZADO",
            "COMPLETADO"
        ]
    )

    cancelados = sum(
        1
        for viaje in viajes
        if str(viaje.estado).upper()
        == "CANCELADO"
    )

    km = sum(
        numero(v.km_recorrido)
        for v in viajes
    )

    carga = sum(
        numero(v.peso)
        for v in viajes
        if v.peso is not None
    )

    horas = 0

    for maquina in maquinaria:

        horas += calcular_horas_maquinaria(
            maquina.id,
            fecha_inicio,
            fecha_fin
        )

    dias = (
        fecha_fin - fecha_inicio
    ).days + 1

    activos = (
        len(vehiculos)
        +
        len(maquinaria)
    )

    promedio_horas = (
        horas / dias
        if dias
        else 0
    )

    # --------------------------------------------------------
    # Utilización:
    # usamos las horas disponibles de maquinaria y,
    # para vehículos, la existencia de actividad mediante
    # viajes.
    # --------------------------------------------------------

    activos_con_actividad = set()

    for viaje in viajes:

        if viaje.vehiculo_id:

            activos_con_actividad.add(
                (
                    "V",
                    viaje.vehiculo_id
                )
            )

    for maquina in maquinaria:

        horas_maquina = calcular_horas_maquinaria(
            maquina.id,
            fecha_inicio,
            fecha_fin
        )

        if horas_maquina > 0:

            activos_con_actividad.add(
                (
                    "M",
                    maquina.id
                )
            )

    utilizacion = (
        porcentaje(
            len(activos_con_actividad),
            activos
        )
        if activos
        else 0
    )

    return {

        "utilizacion":
            numero(utilizacion),

        "horasOperativas":
            numero(horas),

        "promedioHoras":
            numero(promedio_horas),

        "metaHoras":
            numero(
                dias * 8
            ),

        "viajes":
            len(viajes),

        "viajesFinalizados":
            finalizados,

        "viajesCancelados":
            cancelados,

        "cargaTransportada":
            numero(carga),

        "kmViajes":
            numero(km)
    }


# ============================================================
# INSPECCIONES
# ============================================================

def calcular_inspecciones(
    vehiculos,
    maquinaria,
    fecha_inicio,
    fecha_fin
):

    ids_vehiculos = [
        v.id
        for v in vehiculos
    ]

    ids_maquinaria = [
        m.id
        for m in maquinaria
    ]

    inicio = datetime.combine(
        fecha_inicio,
        datetime.min.time()
    )

    fin = datetime.combine(
        fecha_fin + timedelta(days=1),
        datetime.min.time()
    )

    filtros = []

    if ids_vehiculos:

        filtros.append(
            Inspeccion.vehiculo_id.in_(
                ids_vehiculos
            )
        )

    if ids_maquinaria:

        filtros.append(
            Inspeccion.maquinaria_id.in_(
                ids_maquinaria
            )
        )

    if not filtros:

        return {
            "total": 0,
            "sinNovedades": 0,
            "conAnomalias": 0,
            "criticas": 0
        }

    inspecciones = (
        Inspeccion.query
        .filter(
            or_(*filtros),

            Inspeccion.created_at >= inicio,

            Inspeccion.created_at < fin,

            Inspeccion.estado.in_([
                "FINALIZADA",
                "REVISADA"
            ])
        )
        .all()
    )

    total = len(inspecciones)

    con_anomalias = sum(
        1
        for inspeccion in inspecciones
        if inspeccion.anomalias
    )

    criticas = 0

    for inspeccion in inspecciones:

        for anomalia in (
            inspeccion.anomalias or []
        ):

            criticidad = getattr(
                anomalia,
                "criticidad",
                None
            )

            if str(
                criticidad
            ).upper() == "CRITICA":

                criticas += 1

    return {

        "total":
            total,

        "sinNovedades":
            max(
                total - con_anomalias,
                0
            ),

        "conAnomalias":
            con_anomalias,

        "criticas":
            criticas
    }


# ============================================================
# RENDIMIENTO DE ACTIVOS
# ============================================================

def calcular_rendimiento(
    vehiculos,
    maquinaria,
    fecha_inicio,
    fecha_fin
):

    resultado = []

    # ========================================================
    # VEHÍCULOS
    # ========================================================

    for vehiculo in vehiculos:

        km = calcular_km_vehiculo(
            vehiculo.id,
            fecha_inicio,
            fecha_fin
        )

        consumo_l_km = obtener_consumo_vehiculo(
            vehiculo
        )

        litros = (
            km * consumo_l_km
        )

        costo_combustible = (
            litros * PRECIO_DIESEL
        )

        mantenimientos = (
            Mantenimiento.query
            .filter(
                Mantenimiento.vehiculo_id
                == vehiculo.id,

                Mantenimiento.fecha >= fecha_inicio,

                Mantenimiento.fecha <= fecha_fin
            )
            .all()
        )

        costo_mantenimiento = sum(
            numero(m.costo)
            for m in mantenimientos
        )

        disponibilidad = (
            100
            if str(
                vehiculo.estado
            ).upper()
            in [
                "OPERATIVO",
                "OPERATIVA"
            ]
            else 0
        )

        # ----------------------------------------------------
        # Eficiencia:
        #
        # 50% disponibilidad
        # 30% eficiencia combustible
        # 20% mantenimiento
        # ----------------------------------------------------

        eficiencia_combustible = (
            100
            if km > 0 and litros <= 0
            else (
                100
                if consumo_l_km <= 0.25
                else max(
                    0,
                    min(
                        100,
                        (
                            0.25
                            /
                            consumo_l_km
                        ) * 100
                    )
                )
            )
        )

        costo_score = (
            100
            if costo_mantenimiento <= 0
            else max(
                0,
                min(
                    100,
                    100 -
                    (
                        costo_mantenimiento
                        /
                        max(
                            costo_mantenimiento,
                            1
                        )
                    ) * 50
                )
            )
        )

        eficiencia = (
            disponibilidad * 0.50
            +
            eficiencia_combustible * 0.30
            +
            costo_score * 0.20
        )

        resultado.append({

            "id":
                vehiculo.id,

            "nombre":
                vehiculo.placa,

            "marca":
                vehiculo.marca
                or "",

            "tipo":
                (
                    vehiculo.tipo_vehiculo.nombre
                    if vehiculo.tipo_vehiculo
                    else "Vehículo"
                ),

            "icono":
                "🚛",

            "uso":
                numero(km),

            "unidad":
                "km",

            "consumo":
                numero(
                    (
                        km / litros
                        if litros > 0
                        else 0
                    )
                ),

            "unidadConsumo":
                "km/L",

            "consumoPorcentaje":
                min(
                    100,
                    max(
                        0,
                        numero(
                            (
                                0.25
                                /
                                consumo_l_km
                            ) * 100
                        )
                    )
                ),

            "litrosEstimados":
                numero(litros),

            "costoCombustible":
                numero(
                    costo_combustible
                ),

            "costoMantenimiento":
                numero(
                    costo_mantenimiento
                ),

            "disponibilidad":
                numero(disponibilidad),

            "eficiencia":
                numero(
                    eficiencia
                ),

            "estado":
                (
                    vehiculo.estado
                    or "OPERATIVO"
                )
        })

    # ========================================================
    # MAQUINARIA
    # ========================================================

    for maquina in maquinaria:

        horas = calcular_horas_maquinaria(
            maquina.id,
            fecha_inicio,
            fecha_fin
        )

        consumo_l_h = (
            obtener_consumo_maquinaria(
                maquina
            )
        )

        litros = (
            horas * consumo_l_h
        )

        costo_combustible = (
            litros * PRECIO_DIESEL
        )

        mantenimientos = (
            MaquinariaMantenimiento.query
            .filter(
                MaquinariaMantenimiento.maquinaria_id
                == maquina.id,

                MaquinariaMantenimiento.fecha >= fecha_inicio,

                MaquinariaMantenimiento.fecha <= fecha_fin
            )
            .all()
        )

        costo_mantenimiento = sum(
            numero(m.costo)
            for m in mantenimientos
        )

        disponibilidad = (
            100
            if str(
                maquina.estado
            ).upper()
            in [
                "OPERATIVA",
                "OPERATIVO"
            ]
            else 0
        )

        eficiencia_combustible = (
            max(
                0,
                min(
                    100,
                    (
                        6.0
                        /
                        consumo_l_h
                    ) * 100
                )
            )
            if consumo_l_h > 0
            else 0
        )

        costo_score = (
            100
            if costo_mantenimiento == 0
            else 50
        )

        eficiencia = (
            disponibilidad * 0.50
            +
            eficiencia_combustible * 0.30
            +
            costo_score * 0.20
        )

        resultado.append({

            "id":
                maquina.id,

            "nombre":
                maquina.codigo,

            "marca":
                maquina.marca
                or "",

            "tipo":
                (
                    maquina.tipo_maquinaria.nombre
                    if maquina.tipo_maquinaria
                    else "Maquinaria"
                ),

            "icono":
                "🚜",

            "uso":
                numero(horas),

            "unidad":
                "h",

            "consumo":
                numero(
                    consumo_l_h
                ),

            "unidadConsumo":
                "L/h",

            "consumoPorcentaje":
                min(
                    100,
                    max(
                        0,
                        numero(
                            (
                                6.0
                                /
                                consumo_l_h
                            ) * 100
                        )
                    )
                ),

            "litrosEstimados":
                numero(litros),

            "costoCombustible":
                numero(
                    costo_combustible
                ),

            "costoMantenimiento":
                numero(
                    costo_mantenimiento
                ),

            "disponibilidad":
                numero(disponibilidad),

            "eficiencia":
                numero(
                    eficiencia
                ),

            "estado":
                (
                    maquina.estado
                    or "OPERATIVA"
                )
        })

    return resultado


# ============================================================
# RANKING
# ============================================================

def calcular_ranking(
    activos,
    indicador
):

    if not activos:

        return [], []

    indicador = (
        indicador
        or "EFICIENCIA"
    ).upper()

    valores = []

    for activo in activos:

        if indicador == "COSTO":

            valor = (
                activo["costoMantenimiento"]
            )

        elif indicador == "COMBUSTIBLE":

            if activo["unidadConsumo"] == "km/L":

                valor = activo["consumo"]

            else:

                # Para L/h:
                # menor consumo = mejor.
                consumo = (
                    activo["consumo"]
                )

                valor = (
                    100 / consumo
                    if consumo > 0
                    else 0
                )

        elif indicador == "DISPONIBILIDAD":

            valor = (
                activo["disponibilidad"]
            )

        else:

            valor = (
                activo["eficiencia"]
            )

        valores.append(
            (
                activo,
                numero(valor)
            )
        )

    if indicador == "COSTO":

        valores.sort(
            key=lambda x: x[1]
        )

    else:

        valores.sort(
            key=lambda x: x[1],
            reverse=True
        )

    mejores = []

    for activo, valor in valores[:5]:

        mejores.append({

            "id":
                activo["id"],

            "nombre":
                activo["nombre"],

            "tipo":
                activo["tipo"],

            "icono":
                activo["icono"],

            "valor":
                numero(
                    activo["eficiencia"]
                    if indicador
                    == "EFICIENCIA"
                    else (
                        activo["disponibilidad"]
                        if indicador
                        == "DISPONIBILIDAD"
                        else valor
                    )
                )
        })

    peores = []

    for activo, valor in valores[-5:]:

        peores.append({

            "id":
                activo["id"],

            "nombre":
                activo["nombre"],

            "tipo":
                activo["tipo"],

            "icono":
                activo["icono"],

            "valor":
                numero(
                    activo["eficiencia"]
                    if indicador
                    == "EFICIENCIA"
                    else (
                        activo["disponibilidad"]
                        if indicador
                        == "DISPONIBILIDAD"
                        else valor
                    )
                )
        })

    peores.reverse()

    return mejores, peores


# ============================================================
# ÚLTIMAS ALERTAS
# ============================================================

def obtener_ultimas_alertas(
    vehiculos,
    maquinaria
):

    ids_v = [
        v.id
        for v in vehiculos
    ]

    ids_m = [
        m.id
        for m in maquinaria
    ]

    filtros = []

    if ids_v:

        filtros.append(
            Alerta.vehiculo_id.in_(
                ids_v
            )
        )

    if ids_m:

        filtros.append(
            Alerta.maquinaria_id.in_(
                ids_m
            )
        )

    if not filtros:

        return []

    alertas = (
        Alerta.query
        .filter(
            or_(*filtros)
        )
        .order_by(
            Alerta.fecha_evento.desc()
        )
        .limit(10)
        .all()
    )

    resultado = []

    for alerta in alertas:

        if alerta.vehiculo:

            activo = (
                alerta.vehiculo.placa
            )

        elif alerta.maquinaria:

            activo = (
                alerta.maquinaria.codigo
            )

        else:

            activo = "Sin activo"

        resultado.append({

            "id":
                alerta.id,

            "titulo":
                alerta.titulo
                or alerta.tipo
                or "Alerta",

            "descripcion":
                alerta.mensaje
                or "",

            "activo":
                activo,

            "fecha":
                (
                    alerta.fecha_evento.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                    if alerta.fecha_evento
                    else ""
                ),

            "prioridad":
                alerta.prioridad,

            "estado":
                alerta.estado
        })

    return resultado


# ============================================================
# ENDPOINT PRINCIPAL
# ============================================================

@analitica_bp.route(
    "",
    methods=["GET"]
)
def obtener_analitica():

    try:

        fecha_inicio, fecha_fin, dias = (
            obtener_periodo()
        )

        tipo_activo, activo_id = (
            obtener_filtros()
        )

        # ----------------------------------------------------
        # ACTIVOS
        # ----------------------------------------------------

        vehiculos = obtener_vehiculos(
            tipo_activo,
            activo_id
        )

        maquinaria = obtener_maquinaria(
            tipo_activo,
            activo_id
        )

        # ----------------------------------------------------
        # IDs
        # ----------------------------------------------------

        ids_vehiculos = [
            v.id
            for v in vehiculos
        ]

        ids_maquinaria = [
            m.id
            for m in maquinaria
        ]

        # ----------------------------------------------------
        # KM
        # ----------------------------------------------------

        km_por_vehiculo = {}

        for vehiculo in vehiculos:

            km_por_vehiculo[
                vehiculo.id
            ] = calcular_km_vehiculo(
                vehiculo.id,
                fecha_inicio,
                fecha_fin
            )

        km_recorridos = sum(
            km_por_vehiculo.values()
        )

        # ----------------------------------------------------
        # MANTENIMIENTOS
        # ----------------------------------------------------

        mantenimientos_vehiculos = (
            obtener_mantenimientos_vehiculos(
                ids_vehiculos,
                fecha_inicio,
                fecha_fin
            )
        )

        mantenimientos_maquinaria = (
            obtener_mantenimientos_maquinaria(
                ids_maquinaria,
                fecha_inicio,
                fecha_fin
            )
        )

        # ----------------------------------------------------
        # RENDIMIENTO
        # ----------------------------------------------------

        rendimiento = calcular_rendimiento(
            vehiculos,
            maquinaria,
            fecha_inicio,
            fecha_fin
        )

        # ----------------------------------------------------
        # COMBUSTIBLE
        # ----------------------------------------------------

        litros_vehiculos = sum(
            numero(
                activo["litrosEstimados"]
            )
            for activo in rendimiento
            if activo["unidad"] == "km"
        )

        litros_maquinaria = sum(
            numero(
                activo["litrosEstimados"]
            )
            for activo in rendimiento
            if activo["unidad"] == "h"
        )

        costo_combustible_vehiculos = sum(
            numero(
                activo["costoCombustible"]
            )
            for activo in rendimiento
            if activo["unidad"] == "km"
        )

        costo_combustible_maquinaria = sum(
            numero(
                activo["costoCombustible"]
            )
            for activo in rendimiento
            if activo["unidad"] == "h"
        )

        litros_totales = (
            litros_vehiculos
            +
            litros_maquinaria
        )

        costo_combustible = (
            costo_combustible_vehiculos
            +
            costo_combustible_maquinaria
        )

        # ----------------------------------------------------
        # CONSUMO PROMEDIO
        # ----------------------------------------------------

        km_vehiculos = sum(
            activo["uso"]
            for activo in rendimiento
            if activo["unidad"] == "km"
        )

        consumo_promedio = (
            km_vehiculos
            /
            litros_vehiculos
            if litros_vehiculos > 0
            else 0
        )

        # ----------------------------------------------------
        # COSTOS
        # ----------------------------------------------------

        costos = calcular_costos(
            mantenimientos_vehiculos,
            mantenimientos_maquinaria,
            costo_combustible_vehiculos,
            costo_combustible_maquinaria
        )

        # ----------------------------------------------------
        # MANTENIMIENTO
        # ----------------------------------------------------

        mantenimiento = (
            calcular_salud_mantenimiento(
                vehiculos,
                maquinaria,
                mantenimientos_vehiculos,
                mantenimientos_maquinaria
            )
        )

        # ----------------------------------------------------
        # ALERTAS
        # ----------------------------------------------------

        alertas_mantenimiento = (
            obtener_alertas_mantenimiento(
                fecha_inicio,
                fecha_fin,
                vehiculos,
                maquinaria
            )
        )

        # ----------------------------------------------------
        # ALERTAS ACTIVAS
        # ----------------------------------------------------

        filtros_alertas = []

        if ids_vehiculos:

            filtros_alertas.append(
                Alerta.vehiculo_id.in_(
                    ids_vehiculos
                )
            )

        if ids_maquinaria:

            filtros_alertas.append(
                Alerta.maquinaria_id.in_(
                    ids_maquinaria
                )
            )

        if filtros_alertas:

            alertas_activas_query = (
                Alerta.query
                .filter(
                    or_(*filtros_alertas),
                    Alerta.estado == "ACTIVA"
                )
            )

            alertas_activas = (
                alertas_activas_query.count()
            )

            alertas_criticas = (
                alertas_activas_query
                .filter(
                    Alerta.prioridad
                    == "CRITICA"
                )
                .count()
            )

        else:

            alertas_activas = 0
            alertas_criticas = 0

        # ----------------------------------------------------
        # OPERACIÓN
        # ----------------------------------------------------

        operacion = calcular_operacion(
            vehiculos,
            maquinaria,
            fecha_inicio,
            fecha_fin
        )

        # ----------------------------------------------------
        # INSPECCIONES
        # ----------------------------------------------------

        inspecciones = calcular_inspecciones(
            vehiculos,
            maquinaria,
            fecha_inicio,
            fecha_fin
        )

        # ----------------------------------------------------
        # DISPONIBILIDAD
        # ----------------------------------------------------

        activos_totales = (
            len(vehiculos)
            +
            len(maquinaria)
        )

        activos_operativos = sum(
            1
            for vehiculo in vehiculos
            if str(
                vehiculo.estado
            ).upper()
            == "OPERATIVO"
        )

        activos_operativos += sum(
            1
            for maquina in maquinaria
            if str(
                maquina.estado
            ).upper()
            == "OPERATIVA"
        )

        disponibilidad = (
            porcentaje(
                activos_operativos,
                activos_totales
            )
            if activos_totales
            else 0
        )

        # ----------------------------------------------------
        # CRECIMIENTO KM
        #
        # Comparamos contra el período anterior.
        # ----------------------------------------------------

        dias_periodo = (
            fecha_fin -
            fecha_inicio
        ).days + 1

        anterior_fin = (
            fecha_inicio -
            timedelta(days=1)
        )

        anterior_inicio = (
            anterior_fin -
            timedelta(days=dias_periodo - 1)
        )

        km_anterior = 0

        for vehiculo in vehiculos:

            km_anterior += (
                calcular_km_vehiculo(
                    vehiculo.id,
                    anterior_inicio,
                    anterior_fin
                )
            )

        crecimiento_km = 0

        if km_anterior > 0:

            crecimiento_km = (
                (
                    (
                        km_recorridos
                        -
                        km_anterior
                    )
                    /
                    km_anterior
                )
                * 100
            )

        # ----------------------------------------------------
        # EFICIENCIA GLOBAL
        # ----------------------------------------------------

        eficiencia_combustible = 0

        if km_vehiculos > 0:

            eficiencia_combustible = (
                consumo_promedio
                /
                0.25
            ) * 100

        eficiencia_combustible = max(
            0,
            min(
                100,
                eficiencia_combustible
            )
        )

        # ----------------------------------------------------
        # RANKING
        # ----------------------------------------------------

        indicador_ranking = (
            request.args
            .get(
                "ranking",
                "EFICIENCIA"
            )
        )

        ranking_mejores, ranking_peores = (
            calcular_ranking(
                rendimiento,
                indicador_ranking
            )
        )

        # ----------------------------------------------------
        # CONSUMO PARA GRÁFICA
        # ----------------------------------------------------

        consumo_combustible = []

        for activo in rendimiento:

            consumo_combustible.append({

                "id":
                    activo["id"],

                "nombre":
                    activo["nombre"],

                "consumo":
                    activo["consumo"],

                "unidad":
                    activo["unidadConsumo"],

                "porcentaje":
                    activo["consumoPorcentaje"]
            })

        # ----------------------------------------------------
        # RENTABILIDAD
        #
        # Actualmente NO existe un modelo de ingresos.
        # Por eso no inventamos ingresos.
        # ----------------------------------------------------

        rentabilidad = {

            "disponible":
                False,

            "ingresos":
                None,

            "costos":
                numero(
                    costos["costoTotal"]
                ),

            "utilidad":
                None,

            "porcentaje":
                None,

            "porcentajeCostos":
                100,

            "mensaje":
                "No existe actualmente una fuente de ingresos/facturación."
        }

        # ----------------------------------------------------
        # ÚLTIMAS ALERTAS
        # ----------------------------------------------------

        ultimas_alertas = (
            obtener_ultimas_alertas(
                vehiculos,
                maquinaria
            )
        )

        # ----------------------------------------------------
        # GRÁFICA KM
        # ----------------------------------------------------

        grafica_km = calcular_grafica_km(
            vehiculos,
            fecha_inicio,
            fecha_fin
        )

        # ----------------------------------------------------
        # ACTIVOS PARA SELECT ANGULAR
        # ----------------------------------------------------

        activos = []

        for vehiculo in vehiculos:

            activos.append({

                "id":
                    vehiculo.id,

                "nombre":
                    vehiculo.placa,

                "tipo":
                    "VEHICULO"
            })

        for maquina in maquinaria:

            activos.append({

                "id":
                    maquina.id,

                "nombre":
                    maquina.codigo,

                "tipo":
                    "MAQUINARIA"
            })

        # ----------------------------------------------------
        # RESPUESTA
        # ----------------------------------------------------

        respuesta = {

            "periodo": {

                "dias":
                    dias,

                "inicio":
                    str(fecha_inicio),

                "fin":
                    str(fecha_fin)
            },

            "filtros": {

                "tipoActivo":
                    tipo_activo,

                "activoId":
                    activo_id
            },

            "activos":
                activos,

            "metricas": {

                "totalActivos":
                    activos_totales,

                "activosOperativos":
                    activos_operativos,

                "kmRecorridos":
                    numero(
                        km_recorridos
                    ),

                "crecimientoKm":
                    numero(
                        crecimiento_km
                    ),

                "consumoPromedio":
                    numero(
                        consumo_promedio
                    ),

                "eficienciaCombustible":
                    numero(
                        eficiencia_combustible
                    ),

                "litrosCombustible":
                    numero(
                        litros_totales
                    ),

                "costoCombustible":
                    numero(
                        costo_combustible
                    ),

                "costoMantenimiento":
                    numero(
                        costos["mantenimiento"]
                    ),

                "mantenimientosPendientes":
                    mantenimiento[
                        "pendientes"
                    ],

                "disponibilidad":
                    numero(
                        disponibilidad
                    ),

                "alertasActivas":
                    alertas_activas,

                "alertasCriticas":
                    alertas_criticas
            },

            "consumoCombustible":
                consumo_combustible,

            "rendimientoActivos":
                rendimiento,

            "costos":
                costos,

            "mantenimiento":
                mantenimiento,

            "alertasMantenimiento":
                alertas_mantenimiento,

            "operacion":
                operacion,

            "rentabilidad":
                rentabilidad,

            "inspecciones":
                inspecciones,

            "rankingMejores":
                ranking_mejores,

            "rankingPeores":
                ranking_peores,

            "ultimasAlertas":
                ultimas_alertas,

            "graficaKm":
                grafica_km,

            "combustible": {

                "tipoCalculo":
                    "ESTIMADO",

                "precioDiesel":
                    PRECIO_DIESEL,

                "precioGasolina":
                    PRECIO_GASOLINA,

                "litrosVehiculos":
                    numero(
                        litros_vehiculos
                    ),

                "litrosMaquinaria":
                    numero(
                        litros_maquinaria
                    ),

                "costoVehiculos":
                    numero(
                        costo_combustible_vehiculos
                    ),

                "costoMaquinaria":
                    numero(
                        costo_combustible_maquinaria
                    )
            }
        }

        return jsonify(respuesta), 200

    except Exception as error:

        db.session.rollback()

        print(
            "❌ ERROR ANALÍTICA:",
            error
        )

        import traceback

        traceback.print_exc()

        return jsonify({

            "error":
                "Error generando analítica",

            "detalle":
                str(error)

        }), 500