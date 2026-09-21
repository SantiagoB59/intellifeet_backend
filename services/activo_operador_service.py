from datetime import datetime

from extensions import db
from models import (
    ActivoOperador,
    Usuario,
    Vehiculo,
    Maquinaria,
    Rol
)

from datetime import datetime
from zoneinfo import ZoneInfo

datetime.now(ZoneInfo("America/Bogota"))
class ActivoOperadorService:

    # ==================================================
    # LISTAR
    # ==================================================

    @staticmethod
    def listar():

    # ===============================
    # ASIGNACIONES
    # ===============================

        asignaciones = (
            ActivoOperador.query
            .order_by(
                ActivoOperador.activo.desc(),
                ActivoOperador.fecha_asignacion.desc()
            )
            .all()
        )

        lista_asignaciones = []

        for a in asignaciones:

            lista_asignaciones.append({

                "id": a.id,

                "activo": a.activo,

                "fecha_asignacion": (
                    a.fecha_asignacion.isoformat()
                    if a.fecha_asignacion else None
                ),

                "fecha_fin": (
                    a.fecha_fin.isoformat()
                    if a.fecha_fin else None
                ),

                "observaciones": a.observaciones,

                "usuario": {
                    "id": a.usuario.id,
                    "nombre": a.usuario.nombre
                },

                "vehiculo": (
                    {
                        "id": a.vehiculo.id,
                        "placa": a.vehiculo.placa,
                        "marca": a.vehiculo.marca,
                        "modelo": a.vehiculo.modelo
                    }
                    if a.vehiculo else None
                ),

                "maquinaria": (
                    {
                        "id": a.maquinaria.id,
                        "codigo": a.maquinaria.codigo,
                        "marca": a.maquinaria.marca,
                        "modelo": a.maquinaria.modelo
                    }
                    if a.maquinaria else None
                )

            })

    # ===============================
# OPERADORES
# ===============================

        usuarios = (
            Usuario.query
            .join(Rol)
            .filter(
                Usuario.activo == True,
                Rol.nombre == "operador"
            )
            .order_by(Usuario.nombre)
            .all()
        )

        lista_usuarios = []

        for u in usuarios:

            lista_usuarios.append({

            "id": u.id,
            "nombre": u.nombre,
            "username": u.username,
            "telefono": u.telefono

        })

    # ===============================
    # VEHÍCULOS
    # ===============================

        vehiculos = []

        datos = (
            Vehiculo.query
            .filter_by(activo=True)
            .order_by(Vehiculo.placa)
            .all()
        )

        for v in datos:

            vehiculos.append({

                "id": v.id,

                "placa": v.placa,

                "marca": v.marca,

                "modelo": v.modelo,

                "tipo_vehiculo_id": v.tipo_vehiculo_id

            })

    # ===============================
    # MAQUINARIA
    # ===============================

        maquinarias = []

        datos = (
            Maquinaria.query
            .filter_by(activo=True)
            .order_by(Maquinaria.codigo)
            .all()
        )

        for m in datos:

            maquinarias.append({

                "id": m.id,

                "codigo": m.codigo,

                "marca": m.marca,

                "modelo": m.modelo,

                "tipo_maquinaria_id": m.tipo_maquinaria_id

            })

        return {

            "asignaciones": lista_asignaciones,

            "usuarios": lista_usuarios,

            "vehiculos": vehiculos,

            "maquinarias": maquinarias

        }
    # ==================================================
    # OBTENER
    # ==================================================

    @staticmethod
    def obtener(id):

        dato = ActivoOperador.query.get(id)

        if not dato:
            raise Exception("Asignación no encontrada.")

        return dato

    # ==================================================
    # CREAR
    # ==================================================

    @staticmethod
    def crear(data):

        usuario_id = data.get("usuario_id")
        vehiculo_id = data.get("vehiculo_id")
        maquinaria_id = data.get("maquinaria_id")
        observaciones = data.get("observaciones")

        if not usuario_id:
            raise Exception("Debe seleccionar un operador.")

        if not vehiculo_id and not maquinaria_id:
            raise Exception("Debe seleccionar un vehículo o maquinaria.")

        if vehiculo_id and maquinaria_id:
            raise Exception("Solo puede asignar un tipo de activo.")

        # --------------------------------------------
        # El operador ya tiene asignación
        # --------------------------------------------

        existe = ActivoOperador.query.filter_by(
            usuario_id=usuario_id,
            activo=True
        ).first()

        if existe:
            raise Exception(
                "El operador ya tiene un activo asignado."
            )

        # --------------------------------------------
        # Vehículo ocupado
        # --------------------------------------------

        if vehiculo_id:

            ocupado = ActivoOperador.query.filter_by(
                vehiculo_id=vehiculo_id,
                activo=True
            ).first()

            if ocupado:
                raise Exception(
                    "Ese vehículo ya está asignado."
                )

        # --------------------------------------------
        # Maquinaria ocupada
        # --------------------------------------------

        if maquinaria_id:

            ocupado = ActivoOperador.query.filter_by(
                maquinaria_id=maquinaria_id,
                activo=True
            ).first()

            if ocupado:
                raise Exception(
                    "Esa maquinaria ya está asignada."
                )

        nuevo = ActivoOperador(

            usuario_id=usuario_id,

            vehiculo_id=vehiculo_id,

            maquinaria_id=maquinaria_id,

            observaciones=observaciones,

            activo=True

        )

        db.session.add(nuevo)

        db.session.commit()

        return nuevo

    # ==================================================
    # ACTUALIZAR
    # ==================================================

    @staticmethod
    def actualizar(id, data):

        asignacion = ActivoOperador.query.get(id)

        if not asignacion:
            raise Exception("Asignación no encontrada.")

        usuario_id = data.get("usuario_id")
        vehiculo_id = data.get("vehiculo_id")
        maquinaria_id = data.get("maquinaria_id")

        if not vehiculo_id and not maquinaria_id:
            raise Exception("Debe seleccionar un activo.")

        # --------------------------------------------
        # Validar operador
        # --------------------------------------------

        existe = (
            ActivoOperador.query
            .filter(
                ActivoOperador.usuario_id == usuario_id,
                ActivoOperador.activo == True,
                ActivoOperador.id != id
            )
            .first()
        )

        if existe:
            raise Exception(
                "El operador ya tiene otro activo asignado."
            )

        # --------------------------------------------
        # Validar vehículo
        # --------------------------------------------

        if vehiculo_id:

            ocupado = (
                ActivoOperador.query
                .filter(
                    ActivoOperador.vehiculo_id == vehiculo_id,
                    ActivoOperador.activo == True,
                    ActivoOperador.id != id
                )
                .first()
            )

            if ocupado:
                raise Exception(
                    "Ese vehículo ya está asignado."
                )

        # --------------------------------------------
        # Validar maquinaria
        # --------------------------------------------

        if maquinaria_id:

            ocupado = (
                ActivoOperador.query
                .filter(
                    ActivoOperador.maquinaria_id == maquinaria_id,
                    ActivoOperador.activo == True,
                    ActivoOperador.id != id
                )
                .first()
            )

            if ocupado:
                raise Exception(
                    "Esa maquinaria ya está asignada."
                )

        asignacion.usuario_id = usuario_id
        asignacion.vehiculo_id = vehiculo_id
        asignacion.maquinaria_id = maquinaria_id
        asignacion.observaciones = data.get("observaciones")

        db.session.commit()

        return asignacion

    # ==================================================
    # DESACTIVAR
    # ==================================================

    @staticmethod
    def eliminar(id):

        asignacion = ActivoOperador.query.get(id)

        if not asignacion:
            raise Exception("Asignación no encontrada.")

        asignacion.activo = False
        asignacion.fecha_fin = datetime.now(ZoneInfo("America/Bogota"))

        db.session.commit()

        return asignacion