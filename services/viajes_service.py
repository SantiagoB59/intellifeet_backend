from extensions import db


def finalizar_viaje(viaje, km_fin, observaciones=None):

    viaje.km_fin = km_fin
    viaje.observaciones = observaciones

    viaje.km_recorrido = km_fin - viaje.km_inicio
    viaje.estado = "FINALIZADO"

    # Actualizar únicamente el remolque
    if viaje.remolque:
        viaje.remolque.km_actual = km_fin

    db.session.commit()

    return viaje