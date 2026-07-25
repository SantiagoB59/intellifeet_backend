from datetime import date

from extensions import db
from models import Vehiculo


def generar_verificacion_kilometraje():

    hoy = date.today()

    vehiculos = Vehiculo.query.filter_by(
        activo=True
    ).all()

    creados = 0

    for vehiculo in vehiculos:

        # Nunca se ha programado
        if vehiculo.fecha_proxima_verificacion is None:

            vehiculo.requiere_verificacion_km = True
            vehiculo.fecha_proxima_verificacion = hoy

            creados += 1
            continue

        # Ya está pendiente, no hacer nada
        if vehiculo.requiere_verificacion_km:
            continue

        # Llegó la fecha
        if hoy >= vehiculo.fecha_proxima_verificacion:

            vehiculo.requiere_verificacion_km = True

            creados += 1

    db.session.commit()

    print(f"✅ Vehículos marcados para verificar: {creados}")