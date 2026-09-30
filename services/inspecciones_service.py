# ============================================================
# services/inspecciones_service.py
# ============================================================
from datetime import datetime
from zoneinfo import ZoneInfo
from sqlalchemy.orm import joinedload
from sqlalchemy import and_
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from extensions import db
from sqlalchemy import extract
from reportlab.lib.units import cm
from models import (
    TipoInspeccion,
    InspeccionPlantilla,
    InspeccionCategoria,
    InspeccionItem,
    Inspeccion,
    InspeccionRespuesta,
    InspeccionFoto,
    ActivoOperador,
    Vehiculo,
    Maquinaria,
    InspeccionAnomalia,
    AnomaliaFoto,
    MaquinariaHoras,
)
from services.alertas_service import crear_alerta
from datetime import datetime
from sqlalchemy import func
import os
import uuid
from werkzeug.utils import secure_filename

from datetime import datetime
from zoneinfo import ZoneInfo
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter
from io import BytesIO
import os
from cryptography.hazmat.backends import default_backend
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    Image as RLImage,
)

from openpyxl.styles import Font, PatternFill, Border, Side, Alignment

from io import BytesIO

import os
import uuid
from flask import Blueprint, request, jsonify, send_file, current_app

datetime.now(ZoneInfo("America/Bogota"))
from openpyxl.drawing.image import Image

class InspeccionService:

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def obtener_tipo_preoperacional():
        """
        Obtiene el tipo de inspección PREOPERACIONAL.
        """

        tipo = TipoInspeccion.query.filter_by(
            nombre="PREOPERACIONAL", activo=True
        ).first()

        if not tipo:
            raise Exception("No existe el tipo de inspección PREOPERACIONAL.")

        return tipo

    # -----------------------------------------------------

    @staticmethod
    def obtener_fecha_actual():
        return datetime.now(ZoneInfo("America/Bogota"))

    # -----------------------------------------------------

    @staticmethod
    def obtener_fecha_hoy():
        return datetime.now(ZoneInfo("America/Bogota")).date()

    # -----------------------------------------------------

    @staticmethod
    def existe_inspeccion_hoy(usuario_id, plantilla_id):

        hoy = InspeccionService.obtener_fecha_hoy()

        return (
            Inspeccion.query
            .filter(
                Inspeccion.usuario_id == usuario_id,
                Inspeccion.plantilla_id == plantilla_id,
                db.func.date(Inspeccion.hora_inicio) == hoy,
                Inspeccion.estado != "ANULADA",
            )
            .order_by(
                Inspeccion.id.desc()
            )
            .first()
        )

    # =====================================================
    # OBTENER ACTIVO ASIGNADO AL OPERADOR
    # =====================================================

    @staticmethod
    def obtener_activo_operador(usuario_id):

        asignacion = ActivoOperador.query.filter_by(
            usuario_id=usuario_id, activo=True
        ).first()

        if not asignacion:
            raise Exception("El operador no tiene un vehículo o maquinaria asignada.")

        # -------------------------------
        # VEHICULO
        # -------------------------------

        if asignacion.vehiculo_id:

            vehiculo = Vehiculo.query.get(asignacion.vehiculo_id)

            if not vehiculo:
                raise Exception("Vehículo no encontrado.")

            return {
                "tipo": "VEHICULO",
                "activo": vehiculo,
                "id": vehiculo.id,
                "nombre": vehiculo.placa,
                "tipo_id": vehiculo.tipo_vehiculo_id,
            }

        # -------------------------------
        # MAQUINARIA
        # -------------------------------

        if asignacion.maquinaria_id:

            maquinaria = Maquinaria.query.get(asignacion.maquinaria_id)

            if not maquinaria:
                raise Exception("Maquinaria no encontrada.")

            return {
                "tipo": "MAQUINARIA",
                "activo": maquinaria,
                "id": maquinaria.id,
                "nombre": maquinaria.codigo,
                "tipo_id": maquinaria.tipo_maquinaria_id,
            }

        raise Exception("La asignación del operador no es válida.")

    # =====================================================
    # OBTENER PLANTILLA
    # =====================================================

    # =====================================================
    # OBTENER PLANTILLA
    # =====================================================

    @staticmethod
    def obtener_lectura_actual_activo(activo):

        if activo["tipo"] == "VEHICULO":
            return activo["activo"].km_actual

        if activo["tipo"] == "MAQUINARIA":
            return activo["activo"].horometro_actual

        return None
    
    @staticmethod
    def obtener_plantilla(tipo_activo, tipo_id):

        print("\n================ OBTENER PLANTILLA ================")
        print(f"Tipo activo recibido: {tipo_activo}")
        print(f"Tipo ID recibido: {tipo_id}")

        tipo_preop = InspeccionService.obtener_tipo_preoperacional()

        print(f"Tipo inspección PREOPERACIONAL ID: {tipo_preop.id}")

        query = InspeccionPlantilla.query.filter(
            InspeccionPlantilla.tipo_inspeccion_id == tipo_preop.id,
            InspeccionPlantilla.tipo_activo == tipo_activo,
            InspeccionPlantilla.activa == True,
        )

        if tipo_activo == "VEHICULO":

            print(f"Buscando plantilla para VEHICULO tipo {tipo_id}")

            query = query.filter(InspeccionPlantilla.tipo_vehiculo_id == tipo_id)

        else:

            print(f"Buscando plantilla para MAQUINARIA tipo {tipo_id}")

            query = query.filter(InspeccionPlantilla.tipo_maquinaria_id == tipo_id)

        plantilla = (
            query.options(
                joinedload(InspeccionPlantilla.categorias).joinedload(
                    InspeccionCategoria.items
                )
            )
            .order_by(InspeccionPlantilla.version.desc())
            .first()
        )

        print("Resultado de la búsqueda:", plantilla)

        if plantilla:
            print("ID plantilla:", plantilla.id)
            print("Nombre:", plantilla.nombre)
        else:
            print("❌ No se encontró ninguna plantilla.")

        print("==================================================\n")

        if not plantilla:

            raise Exception("No existe una plantilla activa para este tipo de activo.")

        return plantilla

    # =====================================================
    # OBTENER PLANTILLA COMPLETA
    # =====================================================

    @staticmethod
    def obtener_plantilla_completa(plantilla_id):

        plantilla = (
            InspeccionPlantilla.query.options(
                joinedload(InspeccionPlantilla.categorias).joinedload(
                    InspeccionCategoria.items
                )
            )
            .filter_by(id=plantilla_id)
            .first()
        )

        if not plantilla:
            raise Exception("Plantilla no encontrada.")

        return plantilla

    # =====================================================
    # OBTENER INSPECCION
    # =====================================================

    @staticmethod
    def obtener_inspeccion(inspeccion_id):

        inspeccion = (
            Inspeccion.query.options(
                joinedload(Inspeccion.usuario),
                joinedload(Inspeccion.vehiculo),
                joinedload(Inspeccion.maquinaria),
                joinedload(Inspeccion.plantilla),
                joinedload(Inspeccion.respuestas).joinedload(InspeccionRespuesta.item),
                joinedload(Inspeccion.respuestas).joinedload(InspeccionRespuesta.fotos),
            )
            .filter_by(id=inspeccion_id)
            .first()
        )

        if not inspeccion:
            raise Exception("La inspección no existe.")

        return inspeccion

    # =====================================================
    # LISTAR PLANTILLAS
    # =====================================================

    @staticmethod
    def listar_plantillas():

        return (
            InspeccionPlantilla.query.options(
                joinedload(InspeccionPlantilla.categorias).joinedload(
                    InspeccionCategoria.items
                )
            )
            .order_by(InspeccionPlantilla.nombre.asc())
            .all()
        )
        # =====================================================

    # CREAR PLANTILLA
    # =====================================================

    @staticmethod
    def crear_plantilla(data):

        tipo = TipoInspeccion.query.get(data["tipo_inspeccion_id"])

        if not tipo:
            raise Exception("Tipo de inspección no encontrado.")

        existe = InspeccionPlantilla.query.filter_by(
            tipo_inspeccion_id=data["tipo_inspeccion_id"],
            tipo_activo=data["tipo_activo"],
            tipo_vehiculo_id=data.get("tipo_vehiculo_id"),
            tipo_maquinaria_id=data.get("tipo_maquinaria_id"),
            version=data.get("version", 1),
        ).first()

        if existe:
            raise Exception("Ya existe una plantilla con esa versión.")

        plantilla = InspeccionPlantilla(
            nombre=data["nombre"],
            descripcion=data.get("descripcion"),
            tipo_inspeccion_id=data["tipo_inspeccion_id"],
            tipo_activo=data["tipo_activo"],
            tipo_vehiculo_id=data.get("tipo_vehiculo_id"),
            tipo_maquinaria_id=data.get("tipo_maquinaria_id"),
            version=data.get("version", 1),
            activa=data.get("activa", True),
        )

        db.session.add(plantilla)

        db.session.commit()

        return plantilla

    # =====================================================
    # ACTUALIZAR PLANTILLA
    # =====================================================

    @staticmethod
    def actualizar_plantilla(plantilla_id, data):

        plantilla = InspeccionPlantilla.query.get(plantilla_id)

        if not plantilla:
            raise Exception("Plantilla no encontrada.")

        plantilla.nombre = data.get("nombre", plantilla.nombre)

        plantilla.descripcion = data.get("descripcion", plantilla.descripcion)

        plantilla.version = data.get("version", plantilla.version)

        plantilla.activa = data.get("activa", plantilla.activa)

        db.session.commit()

        return plantilla

    # =====================================================
    # ACTIVAR PLANTILLA
    # =====================================================

    @staticmethod
    def activar_plantilla(plantilla_id):

        plantilla = InspeccionPlantilla.query.get(plantilla_id)

        if not plantilla:
            raise Exception("Plantilla no encontrada.")

        plantilla.activa = True

        db.session.commit()

        return plantilla

    # =====================================================
    # DESACTIVAR PLANTILLA
    # =====================================================

    @staticmethod
    def desactivar_plantilla(plantilla_id):

        plantilla = InspeccionPlantilla.query.get(plantilla_id)

        if not plantilla:
            raise Exception("Plantilla no encontrada.")

        plantilla.activa = False

        db.session.commit()

        return plantilla

    # =====================================================
    # ELIMINAR PLANTILLA
    # =====================================================

    @staticmethod
    def eliminar_plantilla(plantilla_id):

        plantilla = InspeccionPlantilla.query.get(plantilla_id)

        if not plantilla:
            raise Exception("Plantilla no encontrada.")

        if plantilla.inspecciones:
            raise Exception(
                "No se puede eliminar una plantilla que ya tiene inspecciones."
            )

        db.session.delete(plantilla)

        db.session.commit()

        return True
        # =====================================================

    # CREAR CATEGORIA
    # =====================================================

    @staticmethod
    def crear_categoria(plantilla_id, data):

        plantilla = InspeccionPlantilla.query.get(plantilla_id)

        if not plantilla:
            raise Exception("Plantilla no encontrada.")

        categoria = InspeccionCategoria(
            plantilla_id=plantilla.id, nombre=data["nombre"], orden=data.get("orden", 1)
        )

        db.session.add(categoria)
        db.session.commit()

        return categoria

    # =====================================================
    # ACTUALIZAR CATEGORIA
    # =====================================================

    @staticmethod
    def actualizar_categoria(categoria_id, data):

        categoria = InspeccionCategoria.query.get(categoria_id)

        if not categoria:
            raise Exception("Categoría no encontrada.")

        categoria.nombre = data.get("nombre", categoria.nombre)

        categoria.orden = data.get("orden", categoria.orden)

        db.session.commit()

        return categoria

    # =====================================================
    # ELIMINAR CATEGORIA
    # =====================================================

    @staticmethod
    def eliminar_categoria(categoria_id):

        categoria = InspeccionCategoria.query.get(categoria_id)

        if not categoria:
            raise Exception("Categoría no encontrada.")

        db.session.delete(categoria)

        db.session.commit()

        return True

    # =====================================================
    # LISTAR CATEGORIAS
    # =====================================================

    @staticmethod
    def listar_categorias(plantilla_id):

        categorias = (
            InspeccionCategoria.query.filter_by(plantilla_id=plantilla_id)
            .order_by(InspeccionCategoria.orden.asc())
            .all()
        )

        return categorias

    # =====================================================
    # OBTENER CATEGORIA
    # =====================================================

    @staticmethod
    def obtener_categoria(categoria_id):

        categoria = (
            InspeccionCategoria.query.options(joinedload(InspeccionCategoria.items))
            .filter_by(id=categoria_id)
            .first()
        )

        if not categoria:
            raise Exception("Categoría no encontrada.")

        return categoria

        # =====================================================

    # CREAR ITEM
    # =====================================================

    @staticmethod
    def crear_item(categoria_id, data):

        categoria = InspeccionCategoria.query.get(categoria_id)

        if not categoria:
            raise Exception("Categoría no encontrada.")

        existe = InspeccionItem.query.filter_by(codigo=data["codigo"]).first()

        if existe:
            raise Exception("El código ya existe.")

        item = InspeccionItem(
            categoria_id=categoria.id,
            codigo=data["codigo"],
            descripcion=data["descripcion"],
            orden=data.get("orden", 1),
            tipo_respuesta=data.get("tipo_respuesta", "SI_NO_NA"),
            ayuda=data.get("ayuda"),
            placeholder=data.get("placeholder"),
            obligatorio=data.get("obligatorio", True),
            permite_na=data.get("permite_na", False),
            requiere_observacion=data.get("requiere_observacion", False),
            requiere_foto=data.get("requiere_foto", False),
            foto_si_falla=data.get("foto_si_falla", True),
            genera_alerta=data.get("genera_alerta", True),
            bloquea_operacion=data.get("bloquea_operacion", False),
            criticidad=data.get("criticidad", "MEDIA"),
            activo=True,
        )

        db.session.add(item)

        db.session.commit()

        return item

    # =====================================================
    # ACTUALIZAR ITEM
    # =====================================================

    @staticmethod
    def actualizar_item(item_id, data):

        item = InspeccionItem.query.get(item_id)

        if not item:
            raise Exception("Item no encontrado.")

        item.descripcion = data.get("descripcion", item.descripcion)

        item.orden = data.get("orden", item.orden)

        item.tipo_respuesta = data.get("tipo_respuesta", item.tipo_respuesta)

        item.ayuda = data.get("ayuda", item.ayuda)

        item.placeholder = data.get("placeholder", item.placeholder)

        item.obligatorio = data.get("obligatorio", item.obligatorio)

        item.permite_na = data.get("permite_na", item.permite_na)

        item.requiere_observacion = data.get(
            "requiere_observacion", item.requiere_observacion
        )

        item.requiere_foto = data.get("requiere_foto", item.requiere_foto)

        item.foto_si_falla = data.get("foto_si_falla", item.foto_si_falla)

        item.genera_alerta = data.get("genera_alerta", item.genera_alerta)

        item.bloquea_operacion = data.get("bloquea_operacion", item.bloquea_operacion)

        item.criticidad = data.get("criticidad", item.criticidad)

        item.activo = data.get("activo", item.activo)

        db.session.commit()

        return item

    # =====================================================
    # ELIMINAR ITEM
    # =====================================================

    @staticmethod
    def eliminar_item(item_id):

        item = InspeccionItem.query.get(item_id)

        if not item:
            raise Exception("Item no encontrado.")

        db.session.delete(item)

        db.session.commit()

        return True

    # =====================================================
    # LISTAR ITEMS
    # =====================================================

    @staticmethod
    def listar_items(categoria_id):

        return (
            InspeccionItem.query.filter_by(categoria_id=categoria_id)
            .order_by(InspeccionItem.orden.asc())
            .all()
        )

        # =====================================================

    # INICIAR INSPECCIÓN
    # =====================================================

    @staticmethod
    def iniciar_inspeccion(usuario_id):

        # Obtener el activo asignado
        activo = InspeccionService.obtener_activo_operador(usuario_id)

        # Obtener plantilla
        plantilla = InspeccionService.obtener_plantilla(
            activo["tipo"], activo["tipo_id"]
        )

        # ¿Ya existe una inspección hoy?
        inspeccion = InspeccionService.existe_inspeccion_hoy(usuario_id, plantilla.id)

        if inspeccion:
            return inspeccion

        inspeccion = Inspeccion(
            plantilla_id=plantilla.id,
            usuario_id=usuario_id,
            vehiculo_id=activo["id"] if activo["tipo"] == "VEHICULO" else None,
            maquinaria_id=activo["id"] if activo["tipo"] == "MAQUINARIA" else None,
            hora_inicio=InspeccionService.obtener_fecha_actual(),
            estado="EN_PROCESO",
        )

        db.session.add(inspeccion)

        db.session.commit()

        return inspeccion

        # =====================================================

    # GUARDAR RESPUESTA
    # =====================================================

    @staticmethod
    def guardar_respuesta(inspeccion_id, data):

        inspeccion = Inspeccion.query.get(inspeccion_id)

        if not inspeccion:
            raise Exception("La inspección no existe.")

        if inspeccion.estado != "EN_PROCESO":
            raise Exception(
                "La inspección ya no permite modificar respuestas."
            )

        item = InspeccionItem.query.get(data["item_id"])

        if not item:
            raise Exception("Item no encontrado.")

        respuesta = InspeccionRespuesta.query.filter_by(
            inspeccion_id=inspeccion_id,
            item_id=item.id
        ).first()

        if not respuesta:

            respuesta = InspeccionRespuesta(
                inspeccion_id=inspeccion_id,
                item_id=item.id
            )

            db.session.add(respuesta)

        respuesta.valor = data.get("respuesta")
        respuesta.observacion = data.get("observacion")

        db.session.commit()

        return respuesta

        # =====================================================

    # GUARDAR FOTO
    # =====================================================

    @staticmethod
    def guardar_foto(respuesta_id, data):

        respuesta = InspeccionRespuesta.query.get(respuesta_id)

        if not respuesta:
            raise Exception("La respuesta no existe.")

        foto = InspeccionFoto(
            respuesta_id=respuesta.id,
            archivo=data["archivo"],
            latitud=data.get("latitud"),
            longitud=data.get("longitud"),
            precision_gps=data.get("precision_gps"),
            direccion=data.get("direccion"),
            fecha_dispositivo=data.get("fecha_dispositivo"),
            fecha_servidor=datetime.utcnow(),
            watermark=True,
            mime_type=data.get("mime_type"),
            tamano_bytes=data.get("tamano_bytes"),
            ancho=data.get("ancho"),
            alto=data.get("alto"),
            hash_archivo=data.get("hash_archivo"),
        )

        db.session.add(foto)

        db.session.commit()

        return foto

        # =====================================================

    # VALIDAR INSPECCIÓN
    # =====================================================

    @staticmethod
    def validar_inspeccion(inspeccion_id):

        inspeccion = InspeccionService.obtener_inspeccion(inspeccion_id)

        errores = []

        plantilla = inspeccion.plantilla

        for categoria in plantilla.categorias:

            for item in categoria.items:

                if not item.activo:
                    continue

                respuesta = next(
                    (r for r in inspeccion.respuestas if r.item_id == item.id), None
                )

                if not respuesta:

                    if item.obligatorio:
                        errores.append(f"Debe responder: {item.descripcion}")

                    continue

                # ===========================
                # RESPUESTA
                # ===========================

                if item.obligatorio and (
                    respuesta.valor is None or str(respuesta.valor).strip() == ""
                ):

                    errores.append(f"Debe responder: {item.descripcion}")

                # ===========================
                # OBSERVACIÓN SOLO SI FALLA
                # ===========================

                if (
                    item.requiere_observacion
                    and respuesta.valor == "NO"
                    and not respuesta.observacion
                ):

                    errores.append(f"Debe escribir observación en: {item.descripcion}")

                # ===========================
                # FOTO SIEMPRE
                # ===========================

                if item.requiere_foto and len(respuesta.fotos) == 0:

                    errores.append(f"Debe tomar fotografía en: {item.descripcion}")

                # ===========================
                # FOTO SOLO SI FALLA
                # ===========================

                if (
                    item.foto_si_falla
                    and respuesta.valor == "NO"
                    and len(respuesta.fotos) == 0
                ):

                    errores.append(
                        f"Debe tomar fotografía porque reportó falla en: {item.descripcion}"
                    )

        return errores
    @staticmethod
    def validar_lectura_inicial(inspeccion):

        errores = []

        tipo_medicion = inspeccion.plantilla.tipo_medicion

        # No requiere kilometraje ni horómetro
        if tipo_medicion == "NINGUNO":
            return errores

        nombre_medicion = (
            "kilometraje"
            if tipo_medicion == "KILOMETRAJE"
            else "horómetro"
        )

        # Validar lectura inicial
        if inspeccion.contador_inicial is None:
            errores.append(
                f"Debe registrar el {nombre_medicion} inicial."
            )

        # Validar fotografía inicial
        if not inspeccion.foto_contador_inicial:
            errores.append(
                f"Debe adjuntar la fotografía del {nombre_medicion} inicial."
            )

        return errores
    
    @staticmethod
    def finalizar_inspeccion(inspeccion_id):

        inspeccion = Inspeccion.query.get(inspeccion_id)

        if not inspeccion:
            raise Exception("La inspección no existe.")

        if inspeccion.estado != "EN_PROCESO":
            raise Exception(
                "La inspección ya no se encuentra en proceso."
            )

        # =====================================================
        # VALIDAR LECTURA INICIAL
        # =====================================================

        errores_lecturas = InspeccionService.validar_lectura_inicial(
            inspeccion
        )

        # =====================================================
        # VALIDAR RESPUESTAS
        # =====================================================

        errores_respuestas = InspeccionService.validar_inspeccion(
            inspeccion_id
        )

        # =====================================================
        # UNIFICAR ERRORES
        # =====================================================

        errores = errores_lecturas + errores_respuestas

        if errores:

            return {
                "ok": False,
                "errores": errores
            }

        # =====================================================
        # CREAR ALERTAS DEL PREOPERACIONAL
        # =====================================================

        InspeccionService.crear_alertas(
            inspeccion_id
        )

        # =====================================================
        # CAMBIAR A PENDIENTE DE CIERRE
        # =====================================================

        inspeccion.estado = "PENDIENTE_CIERRE"

        db.session.commit()

        return {
            "ok": True,
            "mensaje": "Inspección guardada correctamente. Debe registrar la lectura final.",
            "inspeccion": inspeccion.to_dict()
        }
            

    @staticmethod
    def guardar_lectura_inicial(inspeccion_id, data):

        inspeccion = Inspeccion.query.get(inspeccion_id)

        if not inspeccion:
            raise Exception("La inspección no existe.")

        if inspeccion.estado != "EN_PROCESO":
            raise Exception(
                "La inspección ya no permite modificar la lectura inicial."
            )

        tipo_medicion = inspeccion.plantilla.tipo_medicion

        if tipo_medicion == "NINGUNO":
            raise Exception(
                "Esta inspección no requiere registrar una lectura inicial."
            )

        lectura = data.get("lectura")

        if lectura is None:
            raise Exception(
                "Debe registrar la lectura inicial."
            )

        try:
            lectura = float(lectura)
        except (ValueError, TypeError):
            raise Exception(
                "La lectura inicial no es válida."
            )

        if lectura < 0:
            raise Exception(
                "La lectura inicial no puede ser negativa."
            )

        inspeccion.contador_inicial = lectura

        if data.get("foto"):
            inspeccion.foto_contador_inicial = data["foto"]

        db.session.commit()

        return inspeccion


    @staticmethod
    def guardar_lectura_final(
        inspeccion_id,
        data,
        firma=None,
        tratamiento_datos_aceptado=False,
        confirma_firma=False
    ):

        inspeccion = Inspeccion.query.get(inspeccion_id)

        if not inspeccion:
            raise Exception("La inspección no existe.")

        if inspeccion.estado != "PENDIENTE_CIERRE":
            raise Exception(
                "Debe finalizar el preoperacional antes de registrar "
                "la lectura final."
            )

        # =====================================================
        # VALIDAR CONFIRMACIÓN Y FIRMA
        # =====================================================

        if not tratamiento_datos_aceptado:
            raise Exception(
                "Debe aceptar el tratamiento de datos."
            )

        if not confirma_firma:
            raise Exception(
                "Debe confirmar que está firmando la inspección."
            )

        if not firma:
            raise Exception(
                "Debe realizar la firma antes de finalizar."
            )

        tipo_medicion = inspeccion.plantilla.tipo_medicion

        # =====================================================
        # LECTURA FINAL
        # Solo aplica para KILOMETRAJE / HOROMETRO
        # =====================================================

        if tipo_medicion != "NINGUNO":

            lectura = data.get("lectura")

            if lectura is None:
                raise Exception(
                    "Debe registrar la lectura final."
                )

            try:
                lectura = float(lectura)

            except (ValueError, TypeError):
                raise Exception(
                    "La lectura final no es válida."
                )

            if lectura < 0:
                raise Exception(
                    "La lectura no puede ser negativa."
                )

            if inspeccion.contador_inicial is None:
                raise Exception(
                    "Primero debe registrar la lectura inicial."
                )

            if lectura < float(inspeccion.contador_inicial):

                nombre_medicion = (
                    "kilometraje"
                    if tipo_medicion == "KILOMETRAJE"
                    else "horómetro"
                )

                raise Exception(
                    f"El {nombre_medicion} final no puede ser menor "
                    f"que el {nombre_medicion} inicial."
                )

            # =================================================
            # GUARDAR LECTURA FINAL
            # =================================================

            inspeccion.contador_final = lectura

            if data.get("foto"):
                inspeccion.foto_contador_final = data["foto"]

            # =================================================
            # ACTUALIZAR HORÓMETRO DE LA MAQUINARIA
            # =================================================

            if (
                tipo_medicion == "HOROMETRO"
                and inspeccion.maquinaria_id is not None
            ):

                maquinaria = Maquinaria.query.get(
                    inspeccion.maquinaria_id
                )

                if maquinaria:

                    maquinaria.horometro_actual = lectura

                    registro_horas = MaquinariaHoras(
                        maquinaria_id=maquinaria.id,
                        horas=lectura,
                        origen="PREOPERACIONAL"
                    )

                    db.session.add(registro_horas)

        # =====================================================
        # GUARDAR FIRMA DEL OPERADOR
        # =====================================================

        carpeta_firma = os.path.join(
            "uploads",
            "inspecciones",
            str(inspeccion.id)
        )

        os.makedirs(
            carpeta_firma,
            exist_ok=True
        )

        nombre_firma = (
            f"firma_{uuid.uuid4().hex}.png"
        )

        ruta_firma = os.path.join(
            carpeta_firma,
            nombre_firma
        )

        firma.save(ruta_firma)

        inspeccion.firma_path = ruta_firma.replace(
            "\\",
            "/"
        )

        # =====================================================
        # CONFIRMACIÓN DE TRATAMIENTO Y FIRMA
        # =====================================================

        inspeccion.tratamiento_datos_aceptado = True

        inspeccion.confirma_firma = True

        inspeccion.confirmacion_fecha = (
            datetime.now(
                ZoneInfo("America/Bogota")
            )
        )

        inspeccion.hora_fin = (
            datetime.now(
                ZoneInfo("America/Bogota")
            )
        )

        # =====================================================
        # FINALIZAR INSPECCIÓN
        # =====================================================

        inspeccion.estado = "FINALIZADA"

        db.session.commit()

        return inspeccion

    @staticmethod
    def validar_lecturas(inspeccion):
    
        errores = []
    
        tipo_medicion = inspeccion.plantilla.tipo_medicion
    
        # =====================================================
        # NO REQUIERE MEDICIÓN
        # =====================================================
    
        if tipo_medicion == "NINGUNO":
            return errores
    
        # =====================================================
        # LECTURA INICIAL
        # =====================================================
    
        if inspeccion.contador_inicial is None:
        
            nombre_medicion = (
                "kilometraje"
                if tipo_medicion == "KILOMETRAJE"
                else "horómetro"
            )
    
            errores.append(
                f"Debe registrar el {nombre_medicion} inicial."
            )
    
        if not inspeccion.foto_contador_inicial:
        
            nombre_medicion = (
                "kilometraje"
                if tipo_medicion == "KILOMETRAJE"
                else "horómetro"
            )
    
            errores.append(
                f"Debe adjuntar la fotografía del {nombre_medicion} inicial."
            )
    
        # =====================================================
        # LECTURA FINAL
        # =====================================================
    
        if inspeccion.contador_final is None:
        
            nombre_medicion = (
                "kilometraje"
                if tipo_medicion == "KILOMETRAJE"
                else "horómetro"
            )
    
            errores.append(
                f"Debe registrar el {nombre_medicion} final."
            )
    
        if not inspeccion.foto_contador_final:
        
            nombre_medicion = (
                "kilometraje"
                if tipo_medicion == "KILOMETRAJE"
                else "horómetro"
            )
    
            errores.append(
                f"Debe adjuntar la fotografía del {nombre_medicion} final."
            )
    
        # =====================================================
        # VALIDAR QUE FINAL >= INICIAL
        # =====================================================
    
        if (
            inspeccion.contador_inicial is not None
            and inspeccion.contador_final is not None
            and float(inspeccion.contador_final)
            < float(inspeccion.contador_inicial)
        ):
    
            nombre_medicion = (
                "kilometraje"
                if tipo_medicion == "KILOMETRAJE"
                else "horómetro"
            )
    
            errores.append(
                f"El {nombre_medicion} final no puede ser menor "
                f"que el {nombre_medicion} inicial."
            )
    
        return errores
            
        
        # =====================================================

    # CREAR ALERTAS
    # =====================================================

    @staticmethod
    def crear_alertas(inspeccion_id):

        inspeccion = InspeccionService.obtener_inspeccion(inspeccion_id)

        for respuesta in inspeccion.respuestas:

            item = respuesta.item

            if not item.genera_alerta:
                continue

            if str(respuesta.valor).upper() != "NO":
                continue

            descripcion = (
                f"{item.descripcion}\n"
                f"Observación: {respuesta.observacion or 'Sin observaciones'}"
            )

            # ===========================================
            # AQUÍ REUTILIZAS TU MOTOR ACTUAL
            # ===========================================

            # ===========================================
            # CREAR ALERTA
            # ===========================================

            alerta = crear_alerta(
                tipo="PREOPERACIONAL",
                categoria="INSPECCION",
                titulo=f"Falla detectada: {item.descripcion}",
                mensaje=(
                    f"{item.descripcion}\n"
                    f"Observación: {respuesta.observacion or 'Sin observaciones'}"
                ),
                prioridad=item.criticidad,
                vehiculo_id=inspeccion.vehiculo_id,
                maquinaria_id=inspeccion.maquinaria_id,
                metadata={
                    "inspeccion_id": inspeccion.id,
                    "respuesta_id": respuesta.id,
                    "item_id": item.id,
                },
            )

            if alerta:

                respuesta.alerta_id = alerta.id

        db.session.commit()

    @staticmethod
    def ahora():
        return datetime.now(ZoneInfo("America/Bogota"))

    @staticmethod
    def obtener_inspeccion_hoy(usuario_id, vehiculo_id=None, maquinaria_id=None):

        ahora = datetime.now(ZoneInfo("America/Bogota"))
        inicio_dia = ahora.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0
        )

        fin_dia = inicio_dia + timedelta(days=1)

        query = Inspeccion.query.filter(
            Inspeccion.usuario_id == usuario_id,
            Inspeccion.hora_inicio >= inicio_dia,
            Inspeccion.hora_inicio < fin_dia,
            Inspeccion.estado != "ANULADA"
        )

        if vehiculo_id is not None:
            query = query.filter(
                Inspeccion.vehiculo_id == vehiculo_id
            )

        if maquinaria_id is not None:
            query = query.filter(
                Inspeccion.maquinaria_id == maquinaria_id
            )

        return query.order_by(
            Inspeccion.id.desc()
        ).first()

    @staticmethod
    def crear_anomalia(data):

        anomalia = InspeccionAnomalia(
            inspeccion_id=data["inspeccion_id"],
            descripcion=data["descripcion"],
            prioridad=data["prioridad"],
            estado="ABIERTA",
        )

        db.session.add(anomalia)
        db.session.commit()

        crear_alerta(
            tipo="ANOMALIA",
            categoria="INSPECCION",
            titulo="Nueva anomalía reportada",
            mensaje=data["descripcion"],
            prioridad=data["prioridad"],
            vehiculo_id=anomalia.inspeccion.vehiculo_id,
            maquinaria_id=anomalia.inspeccion.maquinaria_id,
        )

        return anomalia

    @staticmethod
    def reportar_anomalia(usuario_id, data):

        inspeccion = Inspeccion.query.get_or_404(data["inspeccion_id"])

        anomalia = InspeccionAnomalia(
            inspeccion_id=inspeccion.id,
            usuario_id=usuario_id,
            titulo=data["titulo"],
            descripcion=data["descripcion"],
            prioridad=data.get("prioridad", "MEDIA"),
            estado="ABIERTA",
        )

        db.session.add(anomalia)
        db.session.commit()

        crear_alerta(
            tipo="ANOMALIA",
            categoria="INSPECCION",
            titulo=anomalia.titulo,
            mensaje=anomalia.descripcion,
            prioridad=anomalia.prioridad,
            vehiculo_id=inspeccion.vehiculo_id,
            maquinaria_id=inspeccion.maquinaria_id,
            metadata={"anomalia_id": anomalia.id, "inspeccion_id": inspeccion.id},
        )

        return anomalia

    @staticmethod
    def listar_anomalias(inspeccion_id):

        return (
            InspeccionAnomalia.query.filter_by(inspeccion_id=inspeccion_id)
            .order_by(InspeccionAnomalia.created_at.desc())
            .all()
        )

    @staticmethod
    def cerrar_anomalia(anomalia_id):

        anomalia = InspeccionAnomalia.query.get_or_404(anomalia_id)

        anomalia.estado = "CERRADA"

        db.session.commit()

        return anomalia

    @staticmethod
    def subir_foto_anomalia(anomalia_id, archivo):

        anomalia = InspeccionAnomalia.query.get_or_404(anomalia_id)

        carpeta = os.path.join("uploads", "anomalias")

        os.makedirs(carpeta, exist_ok=True)

        extension = archivo.filename.rsplit(".", 1)[1].lower()

        nombre = f"{uuid.uuid4().hex}.{extension}"

        ruta = os.path.join(carpeta, nombre)

        archivo.save(ruta)

        foto = AnomaliaFoto(anomalia_id=anomalia.id, archivo=nombre)

        db.session.add(foto)
        db.session.commit()

        return foto

    @staticmethod
    def listar_inspecciones(
        fecha_inicio=None,
        fecha_fin=None,
        vehiculo_id=None,
        maquinaria_id=None,
        usuario_id=None,
        estado=None,
    ):

        consulta = Inspeccion.query.options(
            joinedload(Inspeccion.usuario),
            joinedload(Inspeccion.vehiculo),
            joinedload(Inspeccion.maquinaria),
            joinedload(Inspeccion.plantilla),
            joinedload(Inspeccion.anomalias),
        )

        if fecha_inicio:
            consulta = consulta.filter(Inspeccion.hora_inicio >= fecha_inicio)

        if fecha_fin:
            consulta = consulta.filter(Inspeccion.hora_inicio <= fecha_fin)

        if vehiculo_id:
            consulta = consulta.filter(Inspeccion.vehiculo_id == vehiculo_id)

        if maquinaria_id:
            consulta = consulta.filter(Inspeccion.maquinaria_id == maquinaria_id)

        if usuario_id:
            consulta = consulta.filter(Inspeccion.usuario_id == usuario_id)
        if estado:
            consulta = consulta.filter(Inspeccion.estado == estado)

        return consulta.order_by(Inspeccion.hora_inicio.desc()).all()

    @staticmethod
    def obtener_inspeccion_pdf(inspeccion_id):

        inspeccion = (
            Inspeccion.query.options(
                joinedload(Inspeccion.usuario),
                joinedload(Inspeccion.vehiculo),
                joinedload(Inspeccion.maquinaria),
                joinedload(Inspeccion.plantilla)
                .joinedload(InspeccionPlantilla.categorias)
                .joinedload(InspeccionCategoria.items),
                joinedload(Inspeccion.respuestas).joinedload(InspeccionRespuesta.item),
                joinedload(Inspeccion.respuestas).joinedload(InspeccionRespuesta.fotos),
            )
            .filter(Inspeccion.id == inspeccion_id)
            .first()
        )

        if not inspeccion:
            raise Exception("Inspección no encontrada.")

        return inspeccion

    @staticmethod
    def obtener_anomalias_pdf(inspeccion_id):

        return (
            InspeccionAnomalia.query.filter(
                InspeccionAnomalia.inspeccion_id == inspeccion_id
            )
            .order_by(InspeccionAnomalia.created_at.asc())
            .all()
        )

    @staticmethod
    def obtener_fotos_anomalia(anomalia_id):

        return AnomaliaFoto.query.filter(AnomaliaFoto.anomalia_id == anomalia_id).all()


    @staticmethod
    def descargar_pdf(inspeccion_id):

        import os
        from io import BytesIO

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            Image as RLImage,
            KeepTogether
        )

        # =========================================================
        # OBTENER INSPECCIÓN
        # =========================================================

        inspeccion = InspeccionService.obtener_inspeccion(inspeccion_id)

        if not inspeccion:
            raise ValueError("La inspección no existe.")

        buffer = BytesIO()

        # =========================================================
        # COLORES CORPORATIVOS
        # =========================================================

        AZUL_OSCURO = colors.HexColor("#172554")
        AZUL = colors.HexColor("#1E40AF")
        AZUL_MEDIO = colors.HexColor("#2563EB")
        AZUL_CLARO = colors.HexColor("#EFF6FF")

        VERDE = colors.HexColor("#15803D")
        VERDE_CLARO = colors.HexColor("#DCFCE7")

        ROJO = colors.HexColor("#B91C1C")
        ROJO_CLARO = colors.HexColor("#FEE2E2")

        NARANJA = colors.HexColor("#C2410C")
        NARANJA_CLARO = colors.HexColor("#FFEDD5")

        GRIS_OSCURO = colors.HexColor("#374151")
        GRIS = colors.HexColor("#6B7280")
        GRIS_CLARO = colors.HexColor("#F3F4F6")
        GRIS_BORDE = colors.HexColor("#D1D5DB")
        BLANCO = colors.white

        # =========================================================
        # DOCUMENTO
        # =========================================================

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=16 * mm,
            leftMargin=16 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title="Inspección Preoperacional",
            author="IntelliFeet"
        )

        estilos = getSampleStyleSheet()

        titulo = ParagraphStyle(
            "TituloIntelliFeet",
            parent=estilos["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=21,
            textColor=AZUL_OSCURO,
            alignment=TA_LEFT,
            spaceAfter=3,
        )

        subtitulo = ParagraphStyle(
            "SubtituloIntelliFeet",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10.5,
            leading=14,
            textColor=AZUL_OSCURO,
            spaceBefore=10,
            spaceAfter=6,
        )

        seccion = ParagraphStyle(
            "SeccionIntelliFeet",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=BLANCO,
            alignment=TA_LEFT,
        )

        normal = ParagraphStyle(
            "NormalIntelliFeet",
            parent=estilos["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=GRIS_OSCURO,
        )

        pequeño = ParagraphStyle(
            "PequenoIntelliFeet",
            parent=estilos["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=GRIS,
        )

        pregunta_style = ParagraphStyle(
            "PreguntaIntelliFeet",
            parent=normal,
            fontName="Helvetica",
            fontSize=7.8,
            leading=10,
        )

        respuesta_style = ParagraphStyle(
            "RespuestaIntelliFeet",
            parent=normal,
            fontName="Helvetica-Bold",
            fontSize=7.8,
            leading=10,
        )

        observacion_style = ParagraphStyle(
            "ObservacionIntelliFeet",
            parent=normal,
            fontSize=7.5,
            leading=9.5,
        )

        centro = ParagraphStyle(
            "CentroIntelliFeet",
            parent=normal,
            alignment=TA_CENTER,
        )

        # =========================================================
        # HELPERS
        # =========================================================

        def texto(valor, defecto=""):
            if valor is None:
                return defecto

            valor = str(valor).strip()

            if not valor:
                return defecto

            return valor

        def safe_paragraph(valor, style=normal, defecto="-"):
            return Paragraph(
                texto(valor, defecto).replace("&", "&amp;"),
                style
            )

        def fecha_formateada(fecha):
            if not fecha:
                return "-"

            try:
                return fecha.strftime("%d/%m/%Y %H:%M")
            except Exception:
                return str(fecha)

        def obtener_estado_color(estado):

            estado = texto(estado).upper()

            if estado == "FINALIZADA":
                return VERDE, VERDE_CLARO

            if estado == "REVISADA":
                return AZUL, AZUL_CLARO

            if estado == "PENDIENTE_CIERRE":
                return NARANJA, NARANJA_CLARO

            if estado == "ANULADA":
                return ROJO, ROJO_CLARO

            return GRIS_OSCURO, GRIS_CLARO

        # =========================================================
        # RESOLVER RUTAS DE ARCHIVOS
        # =========================================================

        def buscar_archivo(ruta):

            if not ruta:
                return None

            ruta = str(ruta).strip()

            if not ruta:
                return None

            # -----------------------------------------------------
            # Ruta absoluta
            # -----------------------------------------------------

            if os.path.isabs(ruta) and os.path.exists(ruta):
                return ruta

            # -----------------------------------------------------
            # Limpiar posibles URLs
            # -----------------------------------------------------

            ruta_limpia = ruta.replace("\\", "/")

            if "://" in ruta_limpia:
                ruta_limpia = ruta_limpia.split("://", 1)[1]

                partes = ruta_limpia.split("/", 1)

                if len(partes) == 2:
                    ruta_limpia = partes[1]

            # -----------------------------------------------------
            # Eliminar slash inicial
            # -----------------------------------------------------

            ruta_limpia = ruta_limpia.lstrip("/")

            # -----------------------------------------------------
            # Posibles ubicaciones
            # -----------------------------------------------------

            candidatos = [
                ruta_limpia,

                os.path.join(
                    "uploads",
                    ruta_limpia
                ),

                os.path.join(
                    "uploads",
                    "inspecciones",
                    ruta_limpia
                ),

                os.path.join(
                    "static",
                    ruta_limpia
                ),

                os.path.join(
                    "static",
                    "uploads",
                    ruta_limpia
                ),

                os.path.join(
                    "static",
                    "inspecciones",
                    ruta_limpia
                ),
            ]

            # -----------------------------------------------------
            # Si empieza por uploads/inspecciones
            # -----------------------------------------------------

            if ruta_limpia.startswith(
                "uploads/inspecciones/"
            ):
                candidatos.append(ruta_limpia)

            # -----------------------------------------------------
            # Buscar
            # -----------------------------------------------------

            for candidato in candidatos:

                if os.path.exists(candidato):
                    return candidato

            return None

        # =========================================================
        # AGREGAR IMAGEN
        # =========================================================

        def crear_imagen(
            ruta,
            ancho_max=70 * mm,
            alto_max=50 * mm
        ):

            ruta_real = buscar_archivo(ruta)

            if not ruta_real:
                return None

            try:

                imagen = RLImage(
                    ruta_real
                )

                # -------------------------------------------------
                # Mantener proporción
                # -------------------------------------------------

                ancho_original = imagen.imageWidth
                alto_original = imagen.imageHeight

                if not ancho_original or not alto_original:
                    return None

                proporcion = min(
                    ancho_max / ancho_original,
                    alto_max / alto_original
                )

                imagen.drawWidth = (
                    ancho_original * proporcion
                )

                imagen.drawHeight = (
                    alto_original * proporcion
                )

                return imagen

            except Exception:
                return None

        # =========================================================
        # PIE DE PÁGINA
        # =========================================================

        def dibujar_footer(canvas, documento):

            canvas.saveState()

            ancho, alto = A4

            canvas.setStrokeColor(GRIS_BORDE)
            canvas.setLineWidth(0.5)

            canvas.line(
                16 * mm,
                11 * mm,
                ancho - 16 * mm,
                11 * mm
            )

            canvas.setFont(
                "Helvetica",
                7
            )

            canvas.setFillColor(GRIS)

            canvas.drawString(
                16 * mm,
                6 * mm,
                "IntelliFeet · Sistema de Gestión Operacional"
            )

            canvas.drawRightString(
                ancho - 16 * mm,
                6 * mm,
                f"Página {documento.page}"
            )

            canvas.restoreState()

        # =========================================================
        # CONTENEDOR PRINCIPAL
        # =========================================================

        elementos = []

        # =========================================================
        # HEADER
        # =========================================================

        logo_path = buscar_archivo(
            "static/intellifeet.png"
        )

        logo = None

        if logo_path:

            try:

                logo = RLImage(
                    logo_path,
                    width=40 * mm,
                    height=18 * mm,
                    kind="proportional"
                )

            except Exception:
                logo = None

        encabezado_texto = [
            Paragraph(
                "FORMATO DE INSPECCIÓN<br/>PREOPERACIONAL",
                titulo
            ),
            Spacer(1, 2 * mm),
            Paragraph(
                "Registro de control operacional del activo",
                pequeño
            )
        ]

        if logo:

            header = Table(
                [[
                    logo,
                    encabezado_texto
                ]],
                colWidths=[
                    48 * mm,
                    125 * mm
                ]
            )

        else:

            header = Table(
                [[
                    Paragraph(
                        "<b>IntelliFeet</b>",
                        titulo
                    ),
                    encabezado_texto
                ]],
                colWidths=[
                    48 * mm,
                    125 * mm
                ]
            )

        header.setStyle(
            TableStyle([
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    0
                ),
            ])
        )

        elementos.append(header)

        elementos.append(
            Spacer(1, 7 * mm)
        )

        # =========================================================
        # ESTADO
        # =========================================================

        estado_texto = texto(
            inspeccion.estado,
            "SIN ESTADO"
        ).replace("_", " ")

        estado_color, estado_fondo = (
            obtener_estado_color(
                inspeccion.estado
            )
        )

        estado_badge = Table(
            [[
                Paragraph(
                    f"<b>{estado_texto}</b>",
                    ParagraphStyle(
                        "EstadoBadge",
                        parent=normal,
                        fontSize=8,
                        textColor=estado_color,
                        alignment=TA_CENTER
                    )
                )
            ]],
            colWidths=[42 * mm]
        )

        estado_badge.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    estado_fondo
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    estado_color
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
            ])
        )

        elementos.append(
            estado_badge
        )

        elementos.append(
            Spacer(1, 5 * mm)
        )

        # =========================================================
        # IDENTIFICAR ACTIVO
        # =========================================================

        activo = "-"

        if inspeccion.vehiculo:

            activo = texto(
                inspeccion.vehiculo.placa
            )

        elif inspeccion.maquinaria:

            activo = texto(
                inspeccion.maquinaria.codigo
            )

        # =========================================================
        # TIPO DE ACTIVO
        # =========================================================

        tipo_activo = "Vehículo"

        if inspeccion.maquinaria:

            tipo_activo = (
                texto(
                    inspeccion.maquinaria.tipo_maquinaria.nombre
                )
                if inspeccion.maquinaria.tipo_maquinaria
                else "Maquinaria"
            )

        # =========================================================
        # INFORMACIÓN GENERAL
        # =========================================================

        elementos.append(
            Paragraph(
                "INFORMACIÓN GENERAL",
                seccion
            )
        )

        tabla_general = Table(
            [
                [
                    safe_paragraph(
                        "OPERADOR",
                        respuesta_style
                    ),
                    safe_paragraph(
                        inspeccion.usuario.nombre
                        if inspeccion.usuario
                        else "-",
                        normal
                    ),

                    safe_paragraph(
                        "ACTIVO",
                        respuesta_style
                    ),
                    safe_paragraph(
                        activo,
                        normal
                    ),
                ],

                [
                    safe_paragraph(
                        "TIPO DE ACTIVO",
                        respuesta_style
                    ),
                    safe_paragraph(
                        tipo_activo,
                        normal
                    ),

                    safe_paragraph(
                        "PLANTILLA",
                        respuesta_style
                    ),
                    safe_paragraph(
                        inspeccion.plantilla.nombre
                        if inspeccion.plantilla
                        else "-",
                        normal
                    ),
                ],

                [
                    safe_paragraph(
                        "INICIO",
                        respuesta_style
                    ),
                    safe_paragraph(
                        fecha_formateada(
                            inspeccion.hora_inicio
                        ),
                        normal
                    ),

                    safe_paragraph(
                        "FINALIZACIÓN",
                        respuesta_style
                    ),
                    safe_paragraph(
                        fecha_formateada(
                            inspeccion.hora_fin
                        ),
                        normal
                    ),
                ],
            ],
            colWidths=[
                32 * mm,
                54 * mm,
                32 * mm,
                55 * mm
            ]
        )

        tabla_general.setStyle(
            TableStyle([
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    GRIS_BORDE
                ),
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    AZUL_CLARO
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, -1),
                    AZUL_CLARO
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
            ])
        )

        elementos.append(
            tabla_general
        )

        elementos.append(
            Spacer(1, 6 * mm)
        )

        # =========================================================
        # LECTURAS DEL ACTIVO
        # =========================================================

        tipo_medicion = (
            texto(
                inspeccion.plantilla.tipo_medicion
                if inspeccion.plantilla
                else ""
            ).upper()
        )

        tiene_lecturas = (
            inspeccion.contador_inicial is not None
            or inspeccion.contador_final is not None
            or inspeccion.foto_contador_inicial
            or inspeccion.foto_contador_final
        )

        if tiene_lecturas:

            elementos.append(
                Paragraph(
                    "LECTURA DEL ACTIVO",
                    seccion
                )
            )

            nombre_medicion = "Lectura"

            if tipo_medicion == "KILOMETRAJE":
                nombre_medicion = "Kilometraje"

            elif tipo_medicion == "HOROMETRO":
                nombre_medicion = "Horómetro"

            unidad = ""

            if tipo_medicion == "KILOMETRAJE":
                unidad = " km"

            elif tipo_medicion == "HOROMETRO":
                unidad = " h"

            tabla_lecturas = Table(
                [
                    [
                        safe_paragraph(
                            "LECTURA INICIAL",
                            respuesta_style
                        ),
                        safe_paragraph(
                            (
                                f"{inspeccion.contador_inicial}"
                                f"{unidad}"
                                if inspeccion.contador_inicial
                                is not None
                                else "-"
                            ),
                            normal
                        ),

                        safe_paragraph(
                            "LECTURA FINAL",
                            respuesta_style
                        ),
                        safe_paragraph(
                            (
                                f"{inspeccion.contador_final}"
                                f"{unidad}"
                                if inspeccion.contador_final
                                is not None
                                else "-"
                            ),
                            normal
                        ),
                    ]
                ],
                colWidths=[
                    38 * mm,
                    48 * mm,
                    38 * mm,
                    49 * mm
                ]
            )

            tabla_lecturas.setStyle(
                TableStyle([
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        GRIS_BORDE
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, 0),
                        AZUL_CLARO
                    ),
                    (
                        "BACKGROUND",
                        (2, 0),
                        (2, 0),
                        AZUL_CLARO
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        7
                    ),
                ])
            )

            elementos.append(
                tabla_lecturas
            )

            elementos.append(
                Spacer(1, 4 * mm)
            )

            # -----------------------------------------------------
            # FOTOS DE CONTADORES
            # -----------------------------------------------------

            foto_inicial = crear_imagen(
                inspeccion.foto_contador_inicial,
                ancho_max=75 * mm,
                alto_max=55 * mm
            )

            foto_final = crear_imagen(
                inspeccion.foto_contador_final,
                ancho_max=75 * mm,
                alto_max=55 * mm
            )

            if foto_inicial or foto_final:

                celdas_fotos = []

                if foto_inicial:

                    celdas_fotos.append([
                        Paragraph(
                            "<b>Foto lectura inicial</b>",
                            centro
                        ),
                        foto_inicial
                    ])

                else:

                    celdas_fotos.append([
                        Paragraph(
                            "<b>Foto lectura inicial</b>",
                            centro
                        ),
                        Paragraph(
                            "Sin fotografía",
                            pequeño
                        )
                    ])

                if foto_final:

                    celdas_fotos.append([
                        Paragraph(
                            "<b>Foto lectura final</b>",
                            centro
                        ),
                        foto_final
                    ])

                else:

                    celdas_fotos.append([
                        Paragraph(
                            "<b>Foto lectura final</b>",
                            centro
                        ),
                        Paragraph(
                            "Sin fotografía",
                            pequeño
                        )
                    ])

                tabla_fotos_contador = Table(
                    [
                        [
                            celdas_fotos[0][0],
                            celdas_fotos[1][0]
                        ],
                        [
                            celdas_fotos[0][1],
                            celdas_fotos[1][1]
                        ]
                    ],
                    colWidths=[
                        85 * mm,
                        85 * mm
                    ]
                )

                tabla_fotos_contador.setStyle(
                    TableStyle([
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            GRIS_BORDE
                        ),
                        (
                            "INNERGRID",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            GRIS_BORDE
                        ),
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            GRIS_CLARO
                        ),
                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER"
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE"
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            6
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            6
                        ),
                    ])
                )

                elementos.append(
                    tabla_fotos_contador
                )

                elementos.append(
                    Spacer(1, 5 * mm)
                )

        # =========================================================
        # RESPUESTAS DE LA INSPECCIÓN
        # =========================================================

        respuestas_por_item = {
            r.item_id: r
            for r in inspeccion.respuestas
        }

        for categoria in inspeccion.plantilla.categorias:

            elementos.append(
                Paragraph(
                    texto(
                        categoria.nombre,
                        "Categoría"
                    ),
                    seccion
                )
            )

            filas = [[
                Paragraph(
                    "<b>Ítem</b>",
                    centro
                ),
                Paragraph(
                    "<b>Respuesta</b>",
                    centro
                ),
                Paragraph(
                    "<b>Observación</b>",
                    centro
                )
            ]]

            filas_con_fotos = []

            for item in categoria.items:

                respuesta = respuestas_por_item.get(
                    item.id
                )

                valor = (
                    respuesta.valor
                    if respuesta
                    else ""
                )

                observacion = (
                    respuesta.observacion
                    if respuesta
                    else ""
                )

                filas.append([
                    safe_paragraph(
                        item.descripcion,
                        pregunta_style
                    ),
                    safe_paragraph(
                        valor,
                        respuesta_style
                    ),
                    safe_paragraph(
                        observacion,
                        observacion_style
                    )
                ])

                # ---------------------------------------------
                # Fotos asociadas a la respuesta
                # ---------------------------------------------

                if respuesta and respuesta.fotos:

                    fotos_validas = []

                    for foto in respuesta.fotos:

                        imagen = crear_imagen(
                            foto.archivo,
                            ancho_max=48 * mm,
                            alto_max=42 * mm
                        )

                        if imagen:

                            fotos_validas.append(
                                (
                                    foto,
                                    imagen
                                )
                            )

                    if fotos_validas:

                        fotos_fila = []

                        for foto, imagen in fotos_validas:

                            info = [
                                imagen,
                                Spacer(1, 1 * mm)
                            ]

                            metadata = []

                            if foto.direccion:

                                metadata.append(
                                    texto(
                                        foto.direccion
                                    )
                                )

                            if foto.fecha_dispositivo:

                                metadata.append(
                                    fecha_formateada(
                                        foto.fecha_dispositivo
                                    )
                                )

                            if (
                                foto.latitud is not None
                                and foto.longitud is not None
                            ):

                                metadata.append(
                                    (
                                        f"GPS: "
                                        f"{float(foto.latitud):.6f}, "
                                        f"{float(foto.longitud):.6f}"
                                    )
                                )

                            if metadata:

                                info.append(
                                    Paragraph(
                                        "<br/>".join(
                                            metadata
                                        ),
                                        pequeño
                                    )
                                )

                            bloque = Table(
                                [[
                                    info
                                ]],
                                colWidths=[
                                    53 * mm
                                ]
                            )

                            bloque.setStyle(
                                TableStyle([
                                    (
                                        "BOX",
                                        (0, 0),
                                        (-1, -1),
                                        0.4,
                                        GRIS_BORDE
                                    ),
                                    (
                                        "ALIGN",
                                        (0, 0),
                                        (-1, -1),
                                        "CENTER"
                                    ),
                                    (
                                        "VALIGN",
                                        (0, 0),
                                        (-1, -1),
                                        "MIDDLE"
                                    ),
                                    (
                                        "TOPPADDING",
                                        (0, 0),
                                        (-1, -1),
                                        4
                                    ),
                                    (
                                        "BOTTOMPADDING",
                                        (0, 0),
                                        (-1, -1),
                                        4
                                    ),
                                ])
                            )

                            fotos_fila.append(
                                bloque
                            )

                        # -----------------------------------------
                        # Agregar fila de fotografías
                        # -----------------------------------------

                        if fotos_fila:

                            while len(fotos_fila) < 3:

                                fotos_fila.append(
                                    ""
                                )

                            filas.append([
                                Paragraph(
                                    "<b>Fotografías</b>",
                                    pequeño
                                ),
                                "",
                                Table(
                                    [fotos_fila],
                                    colWidths=[
                                        57 * mm,
                                        57 * mm,
                                        57 * mm
                                    ]
                                )
                            ])

            tabla_respuestas = Table(
                filas,
                colWidths=[
                    75 * mm,
                    28 * mm,
                    83 * mm,
                ],
                repeatRows=1
            )

            tabla_respuestas.setStyle(
                TableStyle([
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        GRIS_BORDE
                    ),

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        AZUL_MEDIO
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        BLANCO
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP"
                    ),

                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            BLANCO,
                            colors.HexColor("#F8FAFC")
                        ]
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),
                ])
            )

            elementos.append(
                tabla_respuestas
            )

            elementos.append(
                Spacer(1, 5 * mm)
            )

        # =========================================================
        # OBSERVACIONES GENERALES
        # =========================================================

        if inspeccion.observaciones_generales:

            elementos.append(
                Paragraph(
                    "OBSERVACIONES GENERALES",
                    seccion
                )
            )

            tabla_observaciones = Table(
                [[
                    safe_paragraph(
                        inspeccion.observaciones_generales,
                        normal
                    )
                ]],
                colWidths=[186 * mm]
            )

            tabla_observaciones.setStyle(
                TableStyle([
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        GRIS_BORDE
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        GRIS_CLARO
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        8
                    ),
                ])
            )

            elementos.append(
                tabla_observaciones
            )

            elementos.append(
                Spacer(1, 5 * mm)
            )

        # =========================================================
        # ANOMALÍAS
        # =========================================================

        elementos.append(
            Paragraph(
                "ANOMALÍAS REPORTADAS",
                seccion
            )
        )

        if inspeccion.anomalias:

            for anomalia in inspeccion.anomalias:

                prioridad = texto(
                    anomalia.prioridad,
                    "MEDIA"
                ).upper()

                if prioridad == "CRITICA":
                    color_prioridad = ROJO
                    fondo_prioridad = ROJO_CLARO

                elif prioridad == "ALTA":
                    color_prioridad = NARANJA
                    fondo_prioridad = NARANJA_CLARO

                elif prioridad == "BAJA":
                    color_prioridad = VERDE
                    fondo_prioridad = VERDE_CLARO

                else:
                    color_prioridad = GRIS_OSCURO
                    fondo_prioridad = GRIS_CLARO

                cabecera_anomalia = Table(
                    [[
                        safe_paragraph(
                            anomalia.titulo,
                            respuesta_style
                        ),
                        Paragraph(
                            f"<b>{prioridad}</b>",
                            ParagraphStyle(
                                "Prioridad",
                                parent=normal,
                                fontSize=7.5,
                                alignment=TA_CENTER,
                                textColor=color_prioridad
                            )
                        )
                    ]],
                    colWidths=[
                        145 * mm,
                        41 * mm
                    ]
                )

                cabecera_anomalia.setStyle(
                    TableStyle([
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            GRIS_BORDE
                        ),
                        (
                            "BACKGROUND",
                            (1, 0),
                            (1, 0),
                            fondo_prioridad
                        ),
                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE"
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            6
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            6
                        ),
                    ])
                )

                elementos.append(
                    cabecera_anomalia
                )

                descripcion = Table(
                    [[
                        safe_paragraph(
                            anomalia.descripcion,
                            normal,
                            "Sin descripción."
                        )
                    ]],
                    colWidths=[186 * mm]
                )

                descripcion.setStyle(
                    TableStyle([
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            GRIS_BORDE
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            7
                        ),
                    ])
                )

                elementos.append(
                    descripcion
                )

                # -------------------------------------------------
                # FOTOS DE LA ANOMALÍA
                # -------------------------------------------------

                fotos_anomalia = []

                # -------------------------------------------------
                # IMPORTANTE:
                # actualmente InspeccionAnomalia no tiene relación
                # declarada con AnomaliaFoto.
                #
                # Por eso buscamos las fotos directamente.
                # -------------------------------------------------

                fotos_db = AnomaliaFoto.query.filter_by(
                    anomalia_id=anomalia.id
                ).all()

                for foto in fotos_db:

                    imagen = crear_imagen(
                        foto.archivo,
                        ancho_max=55 * mm,
                        alto_max=48 * mm
                    )

                    if imagen:

                        bloque = Table(
                            [[
                                imagen
                            ]],
                            colWidths=[
                                58 * mm
                            ]
                        )

                        bloque.setStyle(
                            TableStyle([
                                (
                                    "BOX",
                                    (0, 0),
                                    (-1, -1),
                                    0.5,
                                    GRIS_BORDE
                                ),
                                (
                                    "ALIGN",
                                    (0, 0),
                                    (-1, -1),
                                    "CENTER"
                                ),
                                (
                                    "VALIGN",
                                    (0, 0),
                                    (-1, -1),
                                    "MIDDLE"
                                ),
                                (
                                    "TOPPADDING",
                                    (0, 0),
                                    (-1, -1),
                                    5
                                ),
                                (
                                    "BOTTOMPADDING",
                                    (0, 0),
                                    (-1, -1),
                                    5
                                ),
                            ])
                        )

                        fotos_anomalia.append(
                            bloque
                        )

                if fotos_anomalia:

                    while len(fotos_anomalia) < 3:

                        fotos_anomalia.append(
                            ""
                        )

                    tabla_fotos_anomalia = Table(
                        [fotos_anomalia[:3]],
                        colWidths=[
                            62 * mm,
                            62 * mm,
                            62 * mm
                        ]
                    )

                    tabla_fotos_anomalia.setStyle(
                        TableStyle([
                            (
                                "VALIGN",
                                (0, 0),
                                (-1, -1),
                                "MIDDLE"
                            ),
                            (
                                "ALIGN",
                                (0, 0),
                                (-1, -1),
                                "CENTER"
                            ),
                            (
                                "TOPPADDING",
                                (0, 0),
                                (-1, -1),
                                5
                            ),
                            (
                                "BOTTOMPADDING",
                                (0, 0),
                                (-1, -1),
                                5
                            ),
                        ])
                    )

                    elementos.append(
                        Spacer(1, 2 * mm)
                    )

                    elementos.append(
                        Paragraph(
                            "<b>Fotografías de la anomalía</b>",
                            pequeño
                        )
                    )

                    elementos.append(
                        tabla_fotos_anomalia
                    )

                elementos.append(
                    Spacer(1, 4 * mm)
                )

        else:

            sin_anomalias = Table(
                [[
                    Paragraph(
                        "✓ INSPECCIÓN SIN ANOMALÍAS REPORTADAS",
                        ParagraphStyle(
                            "SinAnomalias",
                            parent=normal,
                            fontName="Helvetica-Bold",
                            fontSize=8,
                            alignment=TA_CENTER,
                            textColor=VERDE
                        )
                    )
                ]],
                colWidths=[186 * mm]
            )

            sin_anomalias.setStyle(
                TableStyle([
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, -1),
                        VERDE_CLARO
                    ),
                    (
                        "BOX",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        VERDE
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        9
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        9
                    ),
                ])
            )

            elementos.append(
                sin_anomalias
            )

        # =========================================================
        # FIRMA DEL OPERADOR
        # =========================================================

        elementos.append(
            Spacer(1, 6 * mm)
        )

        elementos.append(
            Paragraph(
                "CIERRE Y FIRMA DEL OPERADOR",
                seccion
            )
        )

        firma = crear_imagen(
            inspeccion.firma_path,
            ancho_max=70 * mm,
            alto_max=35 * mm
        )

        firma_contenido = []

        if firma:

            firma_contenido.append(
                firma
            )

        else:

            firma_contenido.append(
                Paragraph(
                    "Firma no registrada",
                    pequeño
                )
            )

        firma_contenido.append(
            Spacer(1, 2 * mm)
        )

        firma_contenido.append(
            Paragraph(
                texto(
                    inspeccion.usuario.nombre
                    if inspeccion.usuario
                    else "Operador"
                ),
                ParagraphStyle(
                    "FirmaNombre",
                    parent=normal,
                    fontName="Helvetica-Bold",
                    alignment=TA_CENTER
                )
            )
        )

        if inspeccion.confirmacion_fecha:

            firma_contenido.append(
                Paragraph(
                    (
                        "Confirmación: "
                        + fecha_formateada(
                            inspeccion.confirmacion_fecha
                        )
                    ),
                    pequeño
                )
            )

        firma_tabla = Table(
            [[
                firma_contenido
            ]],
            colWidths=[90 * mm]
        )

        firma_tabla.setStyle(
            TableStyle([
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    GRIS_BORDE
                ),
                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE"
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),
            ])
        )

        elementos.append(
            firma_tabla
        )

        # =========================================================
        # CONSENTIMIENTOS
        # =========================================================

        consentimiento = Table(
            [[
                Paragraph(
                    (
                        "Tratamiento de datos: "
                        + (
                            "ACEPTADO"
                            if inspeccion.tratamiento_datos_aceptado
                            else "NO ACEPTADO"
                        )
                    ),
                    pequeño
                ),
                Paragraph(
                    (
                        "Confirmación de firma: "
                        + (
                            "CONFIRMADA"
                            if inspeccion.confirma_firma
                            else "NO CONFIRMADA"
                        )
                    ),
                    pequeño
                )
            ]],
            colWidths=[
                93 * mm,
                93 * mm
            ]
        )

        consentimiento.setStyle(
            TableStyle([
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    GRIS_CLARO
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    GRIS_BORDE
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    6
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5
                ),
            ])
        )

        elementos.append(
            Spacer(1, 3 * mm)
        )

        elementos.append(
            consentimiento
        )

        # =========================================================
        # PIE FINAL
        # =========================================================

        elementos.append(
            Spacer(1, 7 * mm)
        )

        elementos.append(
            Paragraph(
                "Documento generado automáticamente por IntelliFeet. "
                "La información contenida corresponde al registro "
                "realizado durante la inspección preoperacional.",
                pequeño
            )
        )

        # =========================================================
        # GENERAR PDF
        # =========================================================

        doc.build(
            elementos,
            onFirstPage=dibujar_footer,
            onLaterPages=dibujar_footer
        )

        buffer.seek(0)

        return buffer


    @staticmethod
    def obtener_reporte_preoperacionales(
        mes, anio, vehiculo_id=None, maquinaria_id=None
    ):

        consulta = Inspeccion.query.options(
            joinedload(Inspeccion.usuario),
            joinedload(Inspeccion.vehiculo),
            joinedload(Inspeccion.maquinaria),
            joinedload(Inspeccion.anomalias),
        ).filter(
            func.month(Inspeccion.hora_inicio) == mes,
            func.year(Inspeccion.hora_inicio) == anio,
            Inspeccion.estado == "FINALIZADA",
        )

        if vehiculo_id:

            consulta = consulta.filter(Inspeccion.vehiculo_id == vehiculo_id)

        if maquinaria_id:

            consulta = consulta.filter(Inspeccion.maquinaria_id == maquinaria_id)

        return consulta.order_by(Inspeccion.hora_inicio.asc()).all()

    @staticmethod
    def descargar_reporte_preoperacionales(
        mes, anio, vehiculo_id=None, maquinaria_id=None
    ):
        """
        Genera reporte mensual profesional de inspecciones preoperacionales.
        """

        from io import BytesIO
        import os

        from reportlab.lib import colors
        from reportlab.lib.enums import TA_CENTER, TA_LEFT
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import (
            getSampleStyleSheet,
            ParagraphStyle,
        )
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate,
            Paragraph,
            Spacer,
            Table,
            TableStyle,
            Image as RLImage,
            KeepTogether,
        )

        # =========================================================
        # OBTENER INFORMACIÓN
        # =========================================================

        inspecciones = InspeccionService.obtener_reporte_preoperacionales(
            mes,
            anio,
            vehiculo_id,
            maquinaria_id
        )

        buffer = BytesIO()

        # =========================================================
        # COLORES CORPORATIVOS
        # =========================================================

        AZUL = colors.HexColor("#1E40AF")
        AZUL_OSCURO = colors.HexColor("#172554")
        AZUL_MEDIO = colors.HexColor("#2563EB")
        AZUL_CLARO = colors.HexColor("#EFF6FF")

        VERDE = colors.HexColor("#15803D")
        VERDE_CLARO = colors.HexColor("#DCFCE7")

        ROJO = colors.HexColor("#B91C1C")
        ROJO_CLARO = colors.HexColor("#FEE2E2")

        NARANJA = colors.HexColor("#C2410C")
        NARANJA_CLARO = colors.HexColor("#FFEDD5")

        GRIS_TEXTO = colors.HexColor("#334155")
        GRIS_MEDIO = colors.HexColor("#64748B")
        GRIS_CLARO = colors.HexColor("#F8FAFC")
        GRIS_BORDE = colors.HexColor("#CBD5E1")

        BLANCO = colors.white

        # =========================================================
        # DOCUMENTO
        # =========================================================

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=15 * mm,
            leftMargin=15 * mm,
            topMargin=20 * mm,
            bottomMargin=18 * mm,
            title="Reporte de Inspecciones Preoperacionales",
            author="IntelliFeet",
        )

        # =========================================================
        # ESTILOS
        # =========================================================

        estilos = getSampleStyleSheet()

        titulo = ParagraphStyle(
            "TituloReporte",
            parent=estilos["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=17,
            leading=20,
            textColor=AZUL_OSCURO,
            alignment=TA_LEFT,
            spaceAfter=3 * mm,
        )

        subtitulo = ParagraphStyle(
            "SubtituloReporte",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=GRIS_MEDIO,
            alignment=TA_LEFT,
        )

        seccion = ParagraphStyle(
            "Seccion",
            parent=estilos["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=AZUL_OSCURO,
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
        )

        texto = ParagraphStyle(
            "Texto",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=11,
            textColor=GRIS_TEXTO,
        )

        texto_centro = ParagraphStyle(
            "TextoCentro",
            parent=texto,
            alignment=TA_CENTER,
        )

        texto_blanco = ParagraphStyle(
            "TextoBlanco",
            parent=texto,
            textColor=BLANCO,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        )

        resumen_numero = ParagraphStyle(
            "ResumenNumero",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=18,
            textColor=AZUL_OSCURO,
            alignment=TA_CENTER,
        )

        resumen_label = ParagraphStyle(
            "ResumenLabel",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=9,
            textColor=GRIS_MEDIO,
            alignment=TA_CENTER,
        )

        estado_style = ParagraphStyle(
            "Estado",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=9,
            alignment=TA_CENTER,
        )

        # =========================================================
        # HELPERS
        # =========================================================

        def texto_seguro(valor, defecto="-"):
            if valor is None:
                return defecto

            valor = str(valor).strip()

            return valor if valor else defecto

        def fecha_segura(fecha):
            if not fecha:
                return "-"

            try:
                return fecha.strftime("%d/%m/%Y")
            except Exception:
                return str(fecha)

        def estado_badge(estado):
            estado = texto_seguro(estado).upper()

            if estado == "FINALIZADA":
                return Paragraph(
                    f'<font color="#15803D"><b>{estado}</b></font>',
                    estado_style
                )

            if estado == "REVISADA":
                return Paragraph(
                    f'<font color="#1E40AF"><b>{estado}</b></font>',
                    estado_style
                )

            if estado == "PENDIENTE_CIERRE":
                return Paragraph(
                    f'<font color="#C2410C"><b>PENDIENTE CIERRE</b></font>',
                    estado_style
                )

            if estado == "ANULADA":
                return Paragraph(
                    f'<font color="#B91C1C"><b>{estado}</b></font>',
                    estado_style
                )

            if estado == "EN_PROCESO":
                return Paragraph(
                    f'<font color="#C2410C"><b>EN PROCESO</b></font>',
                    estado_style
                )

            return Paragraph(
                f'<b>{estado}</b>',
                estado_style
            )

        # =========================================================
        # ELEMENTOS
        # =========================================================

        elementos = []

        # =========================================================
        # ENCABEZADO
        # =========================================================

        logo = "static/intellifeet.png"

        if os.path.exists(logo):

            img = RLImage(
                logo,
                width=38 * mm,
                height=19 * mm,
            )

            img.hAlign = "LEFT"

            encabezado_texto = [
                Paragraph(
                    "REPORTE DE INSPECCIONES<br/>PREOPERACIONALES",
                    titulo
                ),
                Paragraph(
                    f"Periodo de consulta: <b>{mes:02d}/{anio}</b>",
                    subtitulo
                ),
                Paragraph(
                    "Sistema de Gestión Operacional · IntelliFeet",
                    subtitulo
                ),
            ]

            encabezado = Table(
                [[img, encabezado_texto]],
                colWidths=[48 * mm, 122 * mm],
            )

        else:

            encabezado_texto = [
                Paragraph(
                    "REPORTE DE INSPECCIONES PREOPERACIONALES",
                    titulo
                ),
                Paragraph(
                    f"Periodo de consulta: <b>{mes:02d}/{anio}</b>",
                    subtitulo
                ),
                Paragraph(
                    "Sistema de Gestión Operacional · IntelliFeet",
                    subtitulo
                ),
            ]

            encabezado = Table(
                [[encabezado_texto]],
                colWidths=[170 * mm],
            )

        encabezado.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                ]
            )
        )

        elementos.append(encabezado)

        elementos.append(
            Table(
                [[""]],
                colWidths=[170 * mm],
                rowHeights=[1.5 * mm],
                style=TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            AZUL_MEDIO
                        ),
                        ("BOX", (0, 0), (-1, -1), 0, AZUL_MEDIO),
                    ]
                )
            )
        )

        elementos.append(Spacer(1, 5 * mm))

        # =========================================================
        # INFORMACIÓN DEL REPORTE
        # =========================================================

        filtro_activo = "Todos los activos"

        if vehiculo_id:
            filtro_activo = "Vehículo seleccionado"

        elif maquinaria_id:
            filtro_activo = "Maquinaria seleccionada"

        informacion = Table(
            [
                [
                    Paragraph("<b>PERIODO</b>", texto),
                    Paragraph(
                        f"{mes:02d}/{anio}",
                        texto
                    ),
                    Paragraph("<b>ACTIVO</b>", texto),
                    Paragraph(
                        filtro_activo,
                        texto
                    ),
                ]
            ],
            colWidths=[28 * mm, 50 * mm, 28 * mm, 64 * mm],
        )

        informacion.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), AZUL_CLARO),
                    ("BACKGROUND", (2, 0), (2, 0), AZUL_CLARO),

                    ("TEXTCOLOR", (0, 0), (-1, -1), GRIS_TEXTO),

                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, GRIS_BORDE),

                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),

                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )

        elementos.append(informacion)

        elementos.append(Spacer(1, 6 * mm))

        # =========================================================
        # ESTADÍSTICAS
        # =========================================================

        total_inspecciones = len(inspecciones)
        total_anomalias = 0
        total_finalizadas = 0
        total_pendientes = 0

        for inspeccion in inspecciones:

            total_anomalias += len(inspeccion.anomalias)

            estado = texto_seguro(
                inspeccion.estado,
                ""
            ).upper()

            if estado in ("FINALIZADA", "REVISADA"):
                total_finalizadas += 1

            if estado == "PENDIENTE_CIERRE":
                total_pendientes += 1

        tarjetas = Table(
            [
                [
                    [
                        Paragraph(
                            str(total_inspecciones),
                            resumen_numero
                        ),
                        Paragraph(
                            "TOTAL INSPECCIONES",
                            resumen_label
                        ),
                    ],
                    [
                        Paragraph(
                            str(total_finalizadas),
                            resumen_numero
                        ),
                        Paragraph(
                            "FINALIZADAS / REVISADAS",
                            resumen_label
                        ),
                    ],
                    [
                        Paragraph(
                            str(total_pendientes),
                            resumen_numero
                        ),
                        Paragraph(
                            "PENDIENTES DE CIERRE",
                            resumen_label
                        ),
                    ],
                    [
                        Paragraph(
                            str(total_anomalias),
                            resumen_numero
                        ),
                        Paragraph(
                            "ANOMALÍAS REPORTADAS",
                            resumen_label
                        ),
                    ],
                ]
            ],
            colWidths=[
                42.5 * mm,
                42.5 * mm,
                42.5 * mm,
                42.5 * mm,
            ],
        )

        tarjetas.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), AZUL_CLARO),
                    ("BACKGROUND", (1, 0), (1, 0), colors.HexColor("#F0FDF4")),
                    ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#FFF7ED")),
                    ("BACKGROUND", (3, 0), (3, 0), colors.HexColor("#FEF2F2")),

                    ("BOX", (0, 0), (-1, -1), 0.5, GRIS_BORDE),
                    ("INNERGRID", (0, 0), (-1, -1), 0.5, GRIS_BORDE),

                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),

                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 7),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        elementos.append(tarjetas)

        elementos.append(Spacer(1, 7 * mm))

        # =========================================================
        # TÍTULO DE LA TABLA
        # =========================================================

        elementos.append(
            Paragraph(
                "Detalle de inspecciones",
                seccion
            )
        )

        # =========================================================
        # TABLA PRINCIPAL
        # =========================================================

        filas = [
            [
                Paragraph("Fecha", texto_blanco),
                Paragraph("Activo", texto_blanco),
                Paragraph("Operador", texto_blanco),
                Paragraph("Estado", texto_blanco),
                Paragraph("Anomalías", texto_blanco),
            ]
        ]

        for inspeccion in inspecciones:

            cantidad_anomalias = len(
                inspeccion.anomalias
            )

            # -----------------------------------------------------
            # ACTIVO
            # -----------------------------------------------------

            activo = "-"

            if inspeccion.vehiculo:

                activo = texto_seguro(
                    inspeccion.vehiculo.placa
                )

            elif inspeccion.maquinaria:

                activo = texto_seguro(
                    inspeccion.maquinaria.codigo
                )

            # -----------------------------------------------------
            # OPERADOR
            # -----------------------------------------------------

            operador = "-"

            if inspeccion.usuario:

                operador = texto_seguro(
                    inspeccion.usuario.nombre
                )

            # -----------------------------------------------------
            # FECHA
            # -----------------------------------------------------

            fecha = fecha_segura(
                inspeccion.hora_inicio
            )

            # -----------------------------------------------------
            # ANOMALÍAS
            # -----------------------------------------------------

            if cantidad_anomalias > 0:

                anomalias_cell = Paragraph(
                    f'<font color="#B91C1C"><b>{cantidad_anomalias}</b></font>',
                    texto_centro
                )

            else:

                anomalias_cell = Paragraph(
                    '<font color="#15803D"><b>0</b></font>',
                    texto_centro
                )

            filas.append(
                [
                    Paragraph(fecha, texto_centro),

                    Paragraph(
                        f"<b>{activo}</b>",
                        texto_centro
                    ),

                    Paragraph(
                        operador,
                        texto
                    ),

                    estado_badge(
                        inspeccion.estado
                    ),

                    anomalias_cell,
                ]
            )

        tabla = Table(
            filas,
            colWidths=[
                25 * mm,
                31 * mm,
                55 * mm,
                35 * mm,
                24 * mm,
            ],
            repeatRows=1,
        )

        tabla.setStyle(
            TableStyle(
                [
                    # -------------------------------------------------
                    # CABECERA
                    # -------------------------------------------------

                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        AZUL_MEDIO
                    ),

                    (
                        "TEXTCOLOR",
                        (0, 0),
                        (-1, 0),
                        BLANCO
                    ),

                    (
                        "FONTNAME",
                        (0, 0),
                        (-1, 0),
                        "Helvetica-Bold"
                    ),

                    (
                        "ALIGN",
                        (0, 0),
                        (-1, 0),
                        "CENTER"
                    ),

                    # -------------------------------------------------
                    # CUERPO
                    # -------------------------------------------------

                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            BLANCO,
                            GRIS_CLARO
                        ]
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        GRIS_BORDE
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),

                    (
                        "ALIGN",
                        (0, 1),
                        (1, -1),
                        "CENTER"
                    ),

                    (
                        "ALIGN",
                        (3, 1),
                        (-1, -1),
                        "CENTER"
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        5
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, 0),
                        7
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, 0),
                        7
                    ),
                ]
            )
        )

        elementos.append(tabla)

        elementos.append(Spacer(1, 7 * mm))

        # =========================================================
        # RESUMEN FINAL
        # =========================================================

        elementos.append(
            Paragraph(
                "Resumen del periodo",
                seccion
            )
        )

        porcentaje_anomalias = 0

        if total_inspecciones > 0:
            porcentaje_anomalias = (
                total_anomalias / total_inspecciones
            )

        porcentaje_finalizadas = 0

        if total_inspecciones > 0:
            porcentaje_finalizadas = (
                total_finalizadas / total_inspecciones
            ) * 100

        resumen = [
            [
                Paragraph(
                    "<b>Total de inspecciones</b>",
                    texto
                ),
                Paragraph(
                    str(total_inspecciones),
                    texto_centro
                ),
            ],
            [
                Paragraph(
                    "<b>Inspecciones finalizadas/revisadas</b>",
                    texto
                ),
                Paragraph(
                    str(total_finalizadas),
                    texto_centro
                ),
            ],
            [
                Paragraph(
                    "<b>Pendientes de cierre</b>",
                    texto
                ),
                Paragraph(
                    str(total_pendientes),
                    texto_centro
                ),
            ],
            [
                Paragraph(
                    "<b>Total de anomalías</b>",
                    texto
                ),
                Paragraph(
                    str(total_anomalias),
                    texto_centro
                ),
            ],
            [
                Paragraph(
                    "<b>Promedio de anomalías por inspección</b>",
                    texto
                ),
                Paragraph(
                    f"{porcentaje_anomalias:.2f}",
                    texto_centro
                ),
            ],
            [
                Paragraph(
                    "<b>% de inspecciones finalizadas/revisadas</b>",
                    texto
                ),
                Paragraph(
                    f"{porcentaje_finalizadas:.1f}%",
                    texto_centro
                ),
            ],
        ]

        tabla_resumen = Table(
            resumen,
            colWidths=[
                125 * mm,
                45 * mm,
            ],
        )

        tabla_resumen.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        AZUL_CLARO
                    ),

                    (
                        "BACKGROUND",
                        (1, 0),
                        (1, -1),
                        BLANCO
                    ),

                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.4,
                        GRIS_BORDE
                    ),

                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE"
                    ),

                    (
                        "ALIGN",
                        (1, 0),
                        (1, -1),
                        "CENTER"
                    ),

                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),

                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6
                    ),
                ]
            )
        )

        elementos.append(tabla_resumen)

        # =========================================================
        # MENSAJE CUANDO NO HAY INSPECCIONES
        # =========================================================

        if not inspecciones:

            elementos.append(Spacer(1, 10 * mm))

            mensaje = Table(
                [
                    [
                        Paragraph(
                            "<b>No se encontraron inspecciones "
                            "preoperacionales para el periodo seleccionado.</b>",
                            texto_centro
                        )
                    ]
                ],
                colWidths=[170 * mm],
            )

            mensaje.setStyle(
                TableStyle(
                    [
                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, -1),
                            AZUL_CLARO
                        ),
                        (
                            "BOX",
                            (0, 0),
                            (-1, -1),
                            0.5,
                            GRIS_BORDE
                        ),
                        (
                            "LEFTPADDING",
                            (0, 0),
                            (-1, -1),
                            10
                        ),
                        (
                            "RIGHTPADDING",
                            (0, 0),
                            (-1, -1),
                            10
                        ),
                        (
                            "TOPPADDING",
                            (0, 0),
                            (-1, -1),
                            12
                        ),
                        (
                            "BOTTOMPADDING",
                            (0, 0),
                            (-1, -1),
                            12
                        ),
                    ]
                )
            )

            elementos.append(mensaje)

        # =========================================================
        # PIE DE PÁGINA
        # =========================================================

        def dibujar_footer(canvas, documento):

            canvas.saveState()

            ancho, alto = A4

            # Línea superior
            canvas.setStrokeColor(GRIS_BORDE)
            canvas.setLineWidth(0.5)

            canvas.line(
                15 * mm,
                12 * mm,
                ancho - 15 * mm,
                12 * mm
            )

            # Texto izquierdo
            canvas.setFont(
                "Helvetica",
                7
            )

            canvas.setFillColor(
                GRIS_MEDIO
            )

            canvas.drawString(
                15 * mm,
                7 * mm,
                "IntelliFeet · Sistema de Gestión Operacional"
            )

            # Página
            canvas.drawRightString(
                ancho - 15 * mm,
                7 * mm,
                f"Página {canvas.getPageNumber()}"
            )

            canvas.restoreState()

        # =========================================================
        # GENERAR PDF
        # =========================================================

        doc.build(
            elementos,
            onFirstPage=dibujar_footer,
            onLaterPages=dibujar_footer
        )

        buffer.seek(0)

        return buffer


    @staticmethod
    def obtener_reporte_preoperacionales(
        mes, anio, vehiculo_id=None, maquinaria_id=None
    ):

        consulta = Inspeccion.query.options(
            joinedload(Inspeccion.usuario),
            joinedload(Inspeccion.vehiculo),
            joinedload(Inspeccion.maquinaria),

            joinedload(Inspeccion.anomalias),

            joinedload(Inspeccion.respuestas)
            .joinedload(InspeccionRespuesta.item)
            .joinedload(InspeccionItem.categoria),

            joinedload(Inspeccion.respuestas)
            .joinedload(InspeccionRespuesta.fotos),

        ).filter(
            func.month(Inspeccion.hora_inicio) == mes,
            func.year(Inspeccion.hora_inicio) == anio,
            Inspeccion.estado == "FINALIZADA",
        )

        if vehiculo_id:
            consulta = consulta.filter(
                Inspeccion.vehiculo_id == vehiculo_id
            )

        if maquinaria_id:
            consulta = consulta.filter(
                Inspeccion.maquinaria_id == maquinaria_id
            )

        return consulta.order_by(
            Inspeccion.hora_inicio.asc()
        ).all()
    
    @staticmethod
    def descargar_libro_preoperacionales(vehiculo_id, anio, mes):

        inspecciones = InspeccionService.obtener_libro_preoperacionales(
            vehiculo_id,
            anio,
            mes
        )

        if not inspecciones:
            raise Exception("No existen inspecciones.")

        buffer = BytesIO()

        # =========================================================
        # DOCUMENTO
        # =========================================================

        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            leftMargin=15,
            rightMargin=15,
            topMargin=15,
            bottomMargin=15,
        )

        estilos = getSampleStyleSheet()

        # =========================================================
        # ESTILOS
        # =========================================================

        estilo_normal = ParagraphStyle(
            "NormalPequeno",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=7,
            alignment=TA_CENTER,
        )

        estilo_item = ParagraphStyle(
            "Item",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=7,
            alignment=TA_LEFT,
        )

        estilo_header = ParagraphStyle(
            "Header",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
        )

        estilo_componente = ParagraphStyle(
            "Componente",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
        )

        elementos = []
        # =========================================================
        # COLORES INTELLIFEET
        # =========================================================

        AZUL_INTELLIFEET = colors.HexColor("#2563EB")
        AZUL_OSCURO = colors.HexColor("#1E3A8A")
        AZUL_CLARO = colors.HexColor("#DBEAFE")
        AZUL_MUY_CLARO = colors.HexColor("#EFF6FF")

        # =========================================================
        # VEHÍCULO
        # =========================================================

        vehiculo = inspecciones[0].vehiculo

        nombre_vehiculo = (
            vehiculo.placa
            if vehiculo
            else "SIN VEHÍCULO"
        )

        # =========================================================
        # LOGO
        # =========================================================

        logo = "static/intellifeet.png"

        if os.path.exists(logo):

            img = RLImage(
                logo,
                width=100,
                height=45,
            )

            img.hAlign = "CENTER"

        else:

            img = ""

        # =========================================================
        # OBTENER TODOS LOS ÍTEMS Y RESPUESTAS
        # =========================================================

        items = {}

        for inspeccion in inspecciones:

            for respuesta in inspeccion.respuestas:

                if not respuesta.item:
                    continue

                item = respuesta.item

                item_id = item.id

                # -------------------------------------------------
                # CREAR ITEM
                # -------------------------------------------------

                if item_id not in items:

                    # =============================================
                    # OBTENER CATEGORÍA REAL
                    # =============================================

                    categoria = item.categoria

                    if categoria:

                        categoria_nombre = categoria.nombre
                        categoria_orden = categoria.orden or 9999

                    else:

                        categoria_nombre = (
                            "INSPECCIÓN PRE-OPERACIONAL"
                        )

                        categoria_orden = 9999

                    items[item_id] = {

                        "item": item,

                        "categoria": categoria,

                        "categoria_nombre": categoria_nombre,

                        "categoria_orden": categoria_orden,

                        "item_orden": item.orden or 9999,

                        "respuestas": {}
                    }

                # -------------------------------------------------
                # FECHA DE LA INSPECCIÓN
                # -------------------------------------------------

                fecha = inspeccion.hora_inicio.date()

                # -------------------------------------------------
                # GUARDAR RESPUESTA
                # -------------------------------------------------

                items[item_id]["respuestas"][fecha] = (
                    respuesta.valor
                )

        # =========================================================
        # ORDENAR ÍTEMS
        # =========================================================

        items_ordenados = sorted(
            items.values(),
            key=lambda x: (
                x["categoria_orden"],
                x["item_orden"],
                x["item"].id
            )
        )

        # =========================================================
        # OBTENER SEMANAS DEL MES
        # =========================================================

        from calendar import monthrange
        from datetime import date, timedelta

        ultimo_dia = monthrange(
            anio,
            mes
        )[1]

        fecha_inicio_mes = date(
            anio,
            mes,
            1
        )

        fecha_fin_mes = date(
            anio,
            mes,
            ultimo_dia
        )

        semanas = []

        fecha_actual = fecha_inicio_mes

        while fecha_actual <= fecha_fin_mes:

            inicio_semana = fecha_actual

            fin_semana = inicio_semana + timedelta(
                days=6
            )

            if fin_semana > fecha_fin_mes:

                fin_semana = fecha_fin_mes

            semanas.append(
                (
                    inicio_semana,
                    fin_semana
                )
            )

            fecha_actual = (
                fin_semana +
                timedelta(days=1)
            )

        # =========================================================
        # GENERAR UNA PÁGINA POR SEMANA
        # =========================================================

        for numero_semana, (
            inicio_semana,
            fin_semana
        ) in enumerate(
            semanas,
            start=1
        ):

            # =====================================================
            # ENCABEZADO PRINCIPAL
            # =====================================================

            encabezado = Table(
                [
                    [
                        img,

                        Paragraph(
                            "<b>INSPECCIÓN PRE-OPERACIONAL</b><br/>"
                            f"<b>VEHÍCULO: {nombre_vehiculo}</b>",
                            estilo_header,
                        ),

                        Paragraph(
                            "<b>HSE-FOR-022</b><br/>"
                            "<b>Versión: 003</b>",
                            estilo_header,
                        ),
                    ]
                ],
                colWidths=[
                    100,
                    450,
                    100,
                ],
                rowHeights=[
                    55
                ],
            )

            encabezado.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.6,
                            colors.black,
                        ),

                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),

                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                    ]
                )
            )

            elementos.append(
                encabezado
            )

            elementos.append(
                Spacer(1, 5)
            )

            # =====================================================
            # INFORMACIÓN DEL VEHÍCULO
            # =====================================================

            operador = inspecciones[0].usuario

            nombre_operador = (
                operador.nombre
                if operador
                else "SIN OPERADOR"
            )

            informacion = Table(
                [
                    [
                        Paragraph(
                            f"<b>VEHÍCULO:</b> "
                            f"{nombre_vehiculo}",
                            estilo_normal,
                        ),

                        Paragraph(
                            f"<b>CONDUCTOR / OPERADOR:</b> "
                            f"{nombre_operador}",
                            estilo_normal,
                        ),

                        Paragraph(
                            f"<b>MES:</b> "
                            f"{mes:02d}/{anio}",
                            estilo_normal,
                        ),
                    ],

                    [
                        Paragraph(
                            f"<b>SEMANA:</b> "
                            f"{inicio_semana.strftime('%d/%m/%Y')} - "
                            f"{fin_semana.strftime('%d/%m/%Y')}",
                            estilo_normal,
                        ),

                        "",

                        Paragraph(
                            "<b>TIPO:</b> PRE-OPERACIONAL",
                            estilo_normal,
                        ),
                    ],
                ],
                colWidths=[
                    220,
                    300,
                    130,
                ],
            )

            informacion.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.black,
                        ),

                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),
                    ]
                )
            )

            elementos.append(
                informacion
            )

            elementos.append(
                Spacer(1, 5)
            )

            # =====================================================
            # DÍAS DE LA SEMANA
            # =====================================================

            dias_semana = []

            fecha = inicio_semana

            while fecha <= fin_semana:

                dias_semana.append(
                    fecha
                )

                fecha += timedelta(
                    days=1
                )

            # =====================================================
            # ENCABEZADO DE LA MATRIZ
            # =====================================================

            filas = []

            encabezado_dias = [
                Paragraph(
                    "<b>ELEMENTO DE INSPECCIÓN</b>",
                    estilo_header,
                )
            ]

            nombres_dias = [
                "L",
                "M",
                "M",
                "J",
                "V",
                "S",
                "D",
            ]

            for fecha in dias_semana:

                indice = fecha.weekday()

                encabezado_dias.append(
                    Paragraph(
                        f"<b>{nombres_dias[indice]}</b><br/>"
                        f"{fecha.strftime('%d/%m')}",
                        estilo_header,
                    )
                )

            filas.append(
                encabezado_dias
            )

            # =====================================================
            # AGRUPAR POR CATEGORÍA
            # =====================================================

            categorias = {}

            for info_item in items_ordenados:

                categoria = info_item["categoria"]

                # -------------------------------------------------
                # NOMBRE REAL DE LA CATEGORÍA
                # -------------------------------------------------

                if categoria:

                    nombre_categoria = (
                        categoria.nombre
                    )

                    orden_categoria = (
                        categoria.orden
                        or 9999
                    )

                else:

                    nombre_categoria = (
                        "INSPECCIÓN PRE-OPERACIONAL"
                    )

                    orden_categoria = 9999

                # -------------------------------------------------
                # CREAR CATEGORÍA
                # -------------------------------------------------

                if nombre_categoria not in categorias:

                    categorias[nombre_categoria] = {
                        "orden": orden_categoria,
                        "items": []
                    }

                categorias[
                    nombre_categoria
                ]["items"].append(
                    info_item
                )

            # =====================================================
            # ORDENAR CATEGORÍAS
            # =====================================================

            categorias_ordenadas = sorted(
                categorias.items(),
                key=lambda x: (
                    x[1]["orden"],
                    x[0]
                )
            )

            # =====================================================
            # AGREGAR CATEGORÍAS E ÍTEMS
            # =====================================================

            filas_componentes = []

            for nombre_categoria, datos_categoria in categorias_ordenadas:

                lista_items = datos_categoria[
                    "items"
                ]

                # -------------------------------------------------
                # FILA DE CATEGORÍA / COMPONENTE
                # -------------------------------------------------

                fila_categoria = [
                    Paragraph(
                        str(
                            nombre_categoria
                        ).upper(),
                        estilo_componente,
                    )
                ]

                for _ in dias_semana:

                    fila_categoria.append("")

                filas.append(
                    fila_categoria
                )

                # Guardamos la posición real
                filas_componentes.append(
                    len(filas) - 1
                )

                # -------------------------------------------------
                # ÍTEMS
                # -------------------------------------------------

                for info_item in lista_items:

                    item = info_item["item"]

                    respuestas = info_item[
                        "respuestas"
                    ]

                    fila = [
                        Paragraph(
                            str(
                                item.descripcion
                                or ""
                            ),
                            estilo_item,
                        )
                    ]

                    # ---------------------------------------------
                    # RESPUESTA POR DÍA
                    # ---------------------------------------------

                    for fecha in dias_semana:

                        valor = respuestas.get(
                            fecha
                        )

                        if valor is None:

                            marca = ""

                        else:

                            valor_normalizado = (
                                str(valor)
                                .strip()
                                .upper()
                            )

                            if valor_normalizado in [
                                "SI",
                                "SÍ",
                                "OK",
                                "BUENO",
                                "CUMPLE",
                                "1",
                                "TRUE",
                            ]:

                                marca = "✓"

                            elif valor_normalizado in [
                                "NO",
                                "MALO",
                                "NO CUMPLE",
                                "0",
                                "FALSE",
                            ]:

                                marca = "X"

                            elif valor_normalizado in [
                                "N/A",
                                "NA",
                                "NO APLICA",
                            ]:

                                marca = "N/A"

                            else:

                                marca = str(
                                    valor
                                )

                        fila.append(
                            Paragraph(
                                marca,
                                estilo_normal,
                            )
                        )

                    filas.append(
                        fila
                    )

            # =====================================================
            # TABLA PRINCIPAL
            # =====================================================

            cantidad_dias = len(
                dias_semana
            )

            ancho_total = 780

            ancho_item = 430

            ancho_dia = (
                ancho_total -
                ancho_item
            ) / max(
                cantidad_dias,
                1
            )

            tabla = Table(
                filas,
                colWidths=[
                    ancho_item
                ]
                +
                [
                    ancho_dia
                    for _ in dias_semana
                ],
                repeatRows=1,
            )

            # =====================================================
            # ESTILOS TABLA
            # =====================================================

            estilos_tabla = [

                # -------------------------------------------------
                # BORDES
                # -------------------------------------------------

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    colors.black,
                ),

                # -------------------------------------------------
                # CABECERA
                # -------------------------------------------------

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    AZUL_INTELLIFEET,
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),

                # -------------------------------------------------
                # ALINEACIÓN
                # -------------------------------------------------

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "ALIGN",
                    (1, 0),
                    (-1, -1),
                    "CENTER",
                ),

                # -------------------------------------------------
                # PADDING
                # -------------------------------------------------

                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),

                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3,
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2,
                ),
            ]

            # =====================================================
            # ESTILO DE LAS CATEGORÍAS
            # =====================================================

            for fila_categoria in filas_componentes:

                estilos_tabla.extend(
                    [

                        (
                            "BACKGROUND",
                            (0, fila_categoria),
                            (-1, fila_categoria),
                            AZUL_CLARO,
                        ),

                        (
                            "TEXTCOLOR",
                            (0, fila_categoria),
                            (-1, fila_categoria),
                            AZUL_OSCURO,
                        ),

                        (
                            "FONTNAME",
                            (0, fila_categoria),
                            (-1, fila_categoria),
                            "Helvetica-Bold",
                        ),

                        (
                            "ALIGN",
                            (0, fila_categoria),
                            (0, fila_categoria),
                            "LEFT",
                        ),

                        (
                            "VALIGN",
                            (0, fila_categoria),
                            (-1, fila_categoria),
                            "MIDDLE",
                        ),
                    ]
                )

            tabla.setStyle(
                TableStyle(
                    estilos_tabla
                )
            )

            elementos.append(
                tabla
            )

            elementos.append(
                Spacer(1, 8)
            )

            # =====================================================
            # KILOMETRAJE
            # =====================================================

            kilometraje = Table(
                [
                    [
                        Paragraph(
                            "<b>KILOMETRAJE INICIAL</b>",
                            estilo_header,
                        ),

                        "",

                        Paragraph(
                            "<b>KILOMETRAJE FINAL</b>",
                            estilo_header,
                        ),

                        "",
                    ]
                ],
                colWidths=[
                    150,
                    220,
                    150,
                    180,
                ],
            )

            kilometraje.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.black,
                        ),

                        (
                            "BACKGROUND",
                            (0, 0),
                            (0, 0),
                            AZUL_MUY_CLARO,
                        ),

                        (
                            "BACKGROUND",
                            (2, 0),
                            (2, 0),
                            AZUL_MUY_CLARO,
                        ),

                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, -1),
                            AZUL_OSCURO,
                        ),

                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),

                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                    ]
                )
            )

            elementos.append(
                kilometraje
            )

            elementos.append(
                Spacer(1, 5)
            )

            # =====================================================
            # OBSERVACIONES
            # =====================================================

            observaciones = Table(
                [
                    [
                        Paragraph(
                            "<b>OBSERVACIONES:</b>",
                            estilo_header,
                        )
                    ],

                    [
                        ""
                    ],

                    [
                        ""
                    ],
                ],
                colWidths=[
                    700
                ],
                rowHeights=[
                    18,
                    20,
                    20,
                ],
            )

            observaciones.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.black,
                        ),

                        (
                            "BACKGROUND",
                            (0, 0),
                            (-1, 0),
                            AZUL_MUY_CLARO,
                        ),

                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, 0),
                            AZUL_OSCURO,
                        ),

                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "TOP",
                        ),
                    ]
                )
            )

            elementos.append(
                observaciones
            )

            elementos.append(
                Spacer(1, 5)
            )

            # =====================================================
            # FIRMA
            # =====================================================

            firma = Table(
                [
                    [
                        Paragraph(
                            "<b>FIRMA DIARIA "
                            "CONDUCTOR / OPERADOR</b>",
                            estilo_header,
                        ),

                        "",

                        Paragraph(
                            "<b>FUERA DE SERVICIO</b>",
                            estilo_header,
                        ),

                        "SI ______  NO ______",
                    ]
                ],
                colWidths=[
                    180,
                    220,
                    130,
                    170,
                ],
                rowHeights=[
                    35
                ],
            )

            firma.setStyle(
                TableStyle(
                    [
                        (
                            "GRID",
                            (0, 0),
                            (-1, -1),
                            0.4,
                            colors.black,
                        ),

                        (
                            "BACKGROUND",
                            (0, 0),
                            (0, 0),
                            AZUL_MUY_CLARO,
                        ),

                        (
                            "BACKGROUND",
                            (2, 0),
                            (2, 0),
                            AZUL_MUY_CLARO,
                        ),

                        (
                            "TEXTCOLOR",
                            (0, 0),
                            (-1, -1),
                            AZUL_OSCURO,
                        ),

                        (
                            "VALIGN",
                            (0, 0),
                            (-1, -1),
                            "MIDDLE",
                        ),

                        (
                            "ALIGN",
                            (0, 0),
                            (-1, -1),
                            "CENTER",
                        ),
                    ]
                )
            )

            elementos.append(
                firma
            )

            # =====================================================
            # SALTO DE PÁGINA
            # =====================================================

            if numero_semana < len(semanas):

                elementos.append(
                    PageBreak()
                )

        # =========================================================
        # GENERAR PDF
        # =========================================================

        doc.build(
            elementos
        )

        buffer.seek(0)

        return buffer
 
    
    @staticmethod
    def obtener_libro_preoperacionales_semanal(
        fecha_inicio,
        vehiculo_id=None,
        maquinaria_id=None,
    ):

        from datetime import timedelta

        fecha_fin = fecha_inicio + timedelta(days=6)

        inicio_datetime = datetime.combine(
            fecha_inicio,
            datetime.min.time()
        )

        fin_datetime = datetime.combine(
            fecha_fin,
            datetime.max.time()
        )

        consulta = Inspeccion.query.options(

            joinedload(Inspeccion.usuario),

            joinedload(Inspeccion.vehiculo),

            joinedload(Inspeccion.maquinaria),

            joinedload(Inspeccion.anomalias),

            joinedload(
                Inspeccion.respuestas
            )
            .joinedload(
                InspeccionRespuesta.item
            )
            .joinedload(
                InspeccionItem.categoria
            ),

        ).filter(

            Inspeccion.estado == "FINALIZADA",

            Inspeccion.hora_inicio >= inicio_datetime,

            Inspeccion.hora_inicio <= fin_datetime,

        )

        if vehiculo_id:

            consulta = consulta.filter(
                Inspeccion.vehiculo_id == vehiculo_id
            )

        if maquinaria_id:

            consulta = consulta.filter(
                Inspeccion.maquinaria_id == maquinaria_id
            )

        return consulta.order_by(
            Inspeccion.hora_inicio.asc()
        ).all()


    @staticmethod
    def descargar_libro_preoperacionales_semanal(
        fecha_referencia,
        vehiculo_id=None,
        maquinaria_id=None,
    ):

        from datetime import datetime, date, timedelta
        from flask import current_app

        # =========================================================
        # CONVERTIR FECHA
        # =========================================================

        if isinstance(
            fecha_referencia,
            str
        ):

            fecha_referencia = datetime.strptime(
                fecha_referencia,
                "%Y-%m-%d"
            ).date()

        elif isinstance(
            fecha_referencia,
            datetime
        ):

            fecha_referencia = (
                fecha_referencia.date()
            )

        # =========================================================
        # CALCULAR SEMANA
        # =========================================================

        inicio_semana = (
            fecha_referencia
            - timedelta(
                days=fecha_referencia.weekday()
            )
        )

        fin_semana = (
            inicio_semana
            + timedelta(days=6)
        )

        # =========================================================
        # OBTENER INSPECCIONES
        # =========================================================

        inspecciones = (
            InspeccionService
            .obtener_libro_preoperacionales_semanal(
                inicio_semana,
                vehiculo_id=vehiculo_id,
                maquinaria_id=maquinaria_id
            )
        )

        # =========================================================
        # SI NO HAY INSPECCIONES
        # =========================================================

        if not inspecciones:

            raise Exception(
                "No existen inspecciones para el activo "
                "durante esta semana."
            )

        # =========================================================
        # BUFFER
        # =========================================================

        buffer = BytesIO()

        # =========================================================
        # DOCUMENTO
        # =========================================================

        doc = SimpleDocTemplate(

            buffer,

            pagesize=landscape(A4),

            leftMargin=15,
            rightMargin=15,
            topMargin=15,
            bottomMargin=15,

        )

        estilos = getSampleStyleSheet()

        # =========================================================
        # ESTILOS
        # =========================================================

        estilo_normal = ParagraphStyle(
            "NormalPequeno",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=7,
            alignment=TA_CENTER,
        )

        estilo_item = ParagraphStyle(
            "Item",
            parent=estilos["Normal"],
            fontName="Helvetica",
            fontSize=6,
            leading=7,
            alignment=TA_LEFT,
        )

        estilo_header = ParagraphStyle(
            "Header",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=7,
            leading=8,
            alignment=TA_CENTER,
        )

        estilo_componente = ParagraphStyle(
            "Componente",
            parent=estilos["Normal"],
            fontName="Helvetica-Bold",
            fontSize=6.5,
            leading=8,
            alignment=TA_LEFT,
        )

        elementos = []

        # =========================================================
        # COLORES
        # =========================================================

        AZUL_INTELLIFEET = colors.HexColor(
            "#2563EB"
        )

        AZUL_OSCURO = colors.HexColor(
            "#1E3A8A"
        )

        AZUL_CLARO = colors.HexColor(
            "#DBEAFE"
        )

        AZUL_MUY_CLARO = colors.HexColor(
            "#EFF6FF"
        )

        GRIS_FUTURO = colors.HexColor(
            "#F8FAFC"
        )

        # =========================================================
        # DETERMINAR TIPO DE ACTIVO
        # =========================================================

        es_maquinaria = maquinaria_id is not None

        # =========================================================
        # VEHÍCULO
        # =========================================================

        vehiculo = (
            inspecciones[0].vehiculo
            if inspecciones
            else None
        )

        nombre_vehiculo = (

            vehiculo.placa

            if vehiculo

            else "SIN VEHÍCULO"

        )

        # =========================================================
        # MAQUINARIA
        # =========================================================

        maquinaria = (

            inspecciones[0].maquinaria

            if inspecciones
            and es_maquinaria

            else None

        )

        nombre_maquinaria = (

            getattr(
                maquinaria,
                "nombre",
                None
            )

            or getattr(
                maquinaria,
                "codigo",
                None
            )

            or getattr(
                maquinaria,
                "placa",
                None
            )

            or "SIN MAQUINARIA"

        )

        # =========================================================
        # NOMBRE DEL ACTIVO
        # =========================================================

        nombre_activo = (

            nombre_maquinaria
            if es_maquinaria
            else nombre_vehiculo

        )

        # =========================================================
        # LOGO
        # =========================================================

        logo = "static/intellifeet.png"

        if os.path.exists(logo):

            img = RLImage(
                logo,
                width=100,
                height=45,
            )

            img.hAlign = "CENTER"

        else:

            img = ""

        # =========================================================
        # OBTENER TODOS LOS ÍTEMS
        # =========================================================

        items = {}

        for inspeccion in inspecciones:

            for respuesta in inspeccion.respuestas:

                if not respuesta.item:
                    continue

                item = respuesta.item

                item_id = item.id

                if item_id not in items:

                    categoria = item.categoria

                    if categoria:

                        categoria_nombre = (
                            categoria.nombre
                        )

                        categoria_orden = (
                            categoria.orden
                            or 9999
                        )

                    else:

                        categoria_nombre = (
                            "INSPECCIÓN PRE-OPERACIONAL"
                        )

                        categoria_orden = 9999

                    items[item_id] = {

                        "item": item,

                        "categoria": categoria,

                        "categoria_nombre":
                            categoria_nombre,

                        "categoria_orden":
                            categoria_orden,

                        "item_orden":
                            item.orden or 9999,

                        "respuestas": {}

                    }

                # =================================================
                # FECHA
                # =================================================

                if not inspeccion.hora_inicio:
                    continue

                fecha = (
                    inspeccion
                    .hora_inicio
                    .date()
                )

                # =================================================
                # RESPUESTA
                # =================================================

                items[item_id][
                    "respuestas"
                ][fecha] = respuesta.valor

        # =========================================================
        # ORDENAR ÍTEMS
        # =========================================================

        items_ordenados = sorted(

            items.values(),

            key=lambda x: (

                x["categoria_orden"],

                x["item_orden"],

                x["item"].id

            )

        )

        # =========================================================
        # DÍAS DE LA SEMANA
        # =========================================================

        dias_semana = [

            inicio_semana
            + timedelta(days=i)

            for i in range(7)

        ]

        # =========================================================
        # FECHA ACTUAL
        # =========================================================

        hoy = date.today()

        # =========================================================
        # INFORMACIÓN DE LA SEMANA
        # =========================================================

        operador = (
            inspecciones[0].usuario
            if inspecciones
            else None
        )

        nombre_operador = (

            operador.nombre

            if operador

            else "SIN OPERADOR"

        )

        # =========================================================
        # ENCABEZADO
        # =========================================================

        titulo_activo = (
            "MAQUINARIA"
            if es_maquinaria
            else "VEHÍCULO"
        )

        encabezado = Table(

            [[

                img,

                Paragraph(

                    "<b>INSPECCIÓN PRE-OPERACIONAL</b><br/>"
                    f"<b>{titulo_activo}: "
                    f"{nombre_activo}</b>",

                    estilo_header,

                ),

                Paragraph(

                    "<b>HSE-FOR-022</b><br/>"
                    "<b>Versión: 003</b>",

                    estilo_header,

                ),

            ]],

            colWidths=[

                100,
                450,
                100,

            ],

            rowHeights=[55],

        )

        encabezado.setStyle(

            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.6,
                    colors.black,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),

            ])

        )

        elementos.append(
            encabezado
        )

        elementos.append(
            Spacer(1, 5)
        )

        # =========================================================
        # INFORMACIÓN
        # =========================================================

        informacion = Table(

            [[

                Paragraph(

                    f"<b>{titulo_activo}:</b> "
                    f"{nombre_activo}",

                    estilo_normal,

                ),

                Paragraph(

                    f"<b>CONDUCTOR / OPERADOR:</b> "
                    f"{nombre_operador}",

                    estilo_normal,

                ),

                Paragraph(

                    "<b>TIPO:</b> "
                    "PRE-OPERACIONAL",

                    estilo_normal,

                ),

            ], [

                Paragraph(

                    f"<b>SEMANA:</b> "
                    f"{inicio_semana.strftime('%d/%m/%Y')} - "
                    f"{fin_semana.strftime('%d/%m/%Y')}",

                    estilo_normal,

                ),

                Paragraph(

                    f"<b>FECHA CONSULTADA:</b> "
                    f"{hoy.strftime('%d/%m/%Y')}",

                    estilo_normal,

                ),

                Paragraph(

                    (
                        "<b>ESTADO:</b> "
                        "SEMANA EN CURSO"

                        if inicio_semana <= hoy <= fin_semana

                        else

                        "<b>ESTADO:</b> "
                        "SEMANA CERRADA"
                    ),

                    estilo_normal,

                ),

            ]],

            colWidths=[

                220,
                300,
                130,

            ],

        )

        informacion.setStyle(

            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.black,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

            ])

        )

        elementos.append(
            informacion
        )

        elementos.append(
            Spacer(1, 5)
        )

        # =========================================================
        # MATRIZ
        # =========================================================

        filas = []

        # =========================================================
        # ENCABEZADO DÍAS
        # =========================================================

        nombres_dias = [

            "LUN",
            "MAR",
            "MIÉ",
            "JUE",
            "VIE",
            "SÁB",
            "DOM",

        ]

        encabezado_dias = [

            Paragraph(
                "<b>ELEMENTO DE INSPECCIÓN</b>",
                estilo_header
            )

        ]

        for fecha in dias_semana:

            indice = fecha.weekday()

            encabezado_dias.append(

                Paragraph(

                    f"<b>{nombres_dias[indice]}</b><br/>"
                    f"{fecha.strftime('%d/%m')}",

                    estilo_header

                )

            )

        filas.append(
            encabezado_dias
        )

        # =========================================================
        # CATEGORÍAS
        # =========================================================

        categorias = {}

        for info_item in items_ordenados:

            nombre_categoria = (
                info_item[
                    "categoria_nombre"
                ]
            )

            orden_categoria = (
                info_item[
                    "categoria_orden"
                ]
            )

            if nombre_categoria not in categorias:

                categorias[
                    nombre_categoria
                ] = {

                    "orden":
                        orden_categoria,

                    "items":
                        []

                }

            categorias[
                nombre_categoria
            ][
                "items"
            ].append(
                info_item
            )

        categorias_ordenadas = sorted(

            categorias.items(),

            key=lambda x: (

                x[1]["orden"],

                x[0]

            )

        )

        filas_componentes = []

        # =========================================================
        # CONSTRUIR MATRIZ
        # =========================================================

        for nombre_categoria, datos_categoria in categorias_ordenadas:

            fila_categoria = [

                Paragraph(

                    str(
                        nombre_categoria
                    ).upper(),

                    estilo_componente

                )

            ]

            for _ in dias_semana:

                fila_categoria.append("")

            filas.append(
                fila_categoria
            )

            filas_componentes.append(
                len(filas) - 1
            )

            # =====================================================
            # ÍTEMS
            # =====================================================

            for info_item in datos_categoria["items"]:

                item = info_item["item"]

                respuestas = (
                    info_item["respuestas"]
                )

                fila = [

                    Paragraph(

                        str(
                            item.descripcion
                            or ""
                        ),

                        estilo_item

                    )

                ]

                for fecha in dias_semana:

                    valor = respuestas.get(
                        fecha
                    )

                    # =============================================
                    # FUTURO
                    # =============================================

                    if fecha > hoy:

                        marca = ""

                    # =============================================
                    # SIN INSPECCIÓN
                    # =============================================

                    elif valor is None:

                        marca = ""

                    # =============================================
                    # CON RESPUESTA
                    # =============================================

                    else:

                        valor_normalizado = (

                            str(valor)
                            .strip()
                            .upper()

                        )

                        if valor_normalizado in [

                            "SI",
                            "SÍ",
                            "OK",
                            "BUENO",
                            "CUMPLE",
                            "1",
                            "TRUE",

                        ]:

                            marca = "✓"

                        elif valor_normalizado in [

                            "NO",
                            "MALO",
                            "NO CUMPLE",
                            "0",
                            "FALSE",

                        ]:

                            marca = "X"

                        elif valor_normalizado in [

                            "N/A",
                            "NA",
                            "NO APLICA",

                        ]:

                            marca = "N/A"

                        else:

                            marca = str(
                                valor
                            )

                    fila.append(

                        Paragraph(
                            marca,
                            estilo_normal
                        )

                    )

                filas.append(
                    fila
                )

        # =========================================================
        # GUARDAR ÚLTIMA FILA DE LA MATRIZ
        # =========================================================

        fila_final_matriz = len(filas) - 1

        # =========================================================
        # ANCHOS
        # =========================================================

        cantidad_dias = 7

        ancho_total = 780

        ancho_item = 430

        ancho_dia = (

            ancho_total
            - ancho_item

        ) / cantidad_dias

        # =========================================================
        # OBTENER INSPECCIONES POR DÍA
        # =========================================================

        inspecciones_por_dia = {}

        for fecha_dia in dias_semana:

            inspecciones_dia = [

                inspeccion

                for inspeccion in inspecciones

                if (

                    inspeccion.hora_inicio

                    and
                    inspeccion.hora_inicio.date()
                    == fecha_dia

                )

            ]

            inspecciones_dia.sort(
                key=lambda x: x.hora_inicio
            )

            inspecciones_por_dia[
                fecha_dia
            ] = inspecciones_dia

        # =========================================================
        # FILA DE SEPARACIÓN - CONTROL DIARIO
        # =========================================================

        fila_control_diario = [

            Paragraph(
                (
                    "<b>CONTROL DIARIO DE "
                    "HORÓMETRO</b>"
                    if es_maquinaria
                    else
                    "<b>CONTROL DIARIO DE "
                    "KILOMETRAJE</b>"
                ),
                estilo_componente
            )

        ]

        for _ in dias_semana:

            fila_control_diario.append("")

        filas.append(
            fila_control_diario
        )

        fila_control_diario_index = len(filas) - 1

        # =========================================================
        # FILA KM/HORÓMETRO INICIAL
        # =========================================================

        fila_inicial = [

            Paragraph(
                (
                    "<b>HORÓMETRO INICIAL</b>"
                    if es_maquinaria
                    else
                    "<b>KM INICIAL</b>"
                ),
                estilo_item
            )

        ]

        # =========================================================
        # FILA KM/HORÓMETRO FINAL
        # =========================================================

        fila_final = [

            Paragraph(
                (
                    "<b>HORÓMETRO FINAL</b>"
                    if es_maquinaria
                    else
                    "<b>KM FINAL</b>"
                ),
                estilo_item
            )

        ]

        # =========================================================
        # FILA FIRMA
        # =========================================================

        fila_firma = [

            Paragraph(
                "<b>FIRMA</b>",
                estilo_item
            )

        ]

        # =========================================================
        # CONSTRUIR INFORMACIÓN DE LOS 7 DÍAS
        # =========================================================

        for fecha_dia in dias_semana:

            inspecciones_dia = (
                inspecciones_por_dia.get(
                    fecha_dia,
                    []
                )
            )

            # =====================================================
            # SIN INSPECCIÓN
            # =====================================================

            if not inspecciones_dia:

                fila_inicial.append(

                    Paragraph(
                        "—",
                        estilo_normal
                    )

                )

                fila_final.append(

                    Paragraph(
                        "—",
                        estilo_normal
                    )

                )

                fila_firma.append(

                    Paragraph(
                        "SIN REGISTRO",
                        estilo_normal
                    )

                )

                continue

            # =====================================================
            # PRIMERA INSPECCIÓN DEL DÍA
            # =====================================================

            primera = inspecciones_dia[0]

            # =====================================================
            # ÚLTIMA INSPECCIÓN DEL DÍA
            # =====================================================

            ultima = inspecciones_dia[-1]

            # =====================================================
            # CONTADOR INICIAL
            # =====================================================

            contador_inicial = (

                primera.contador_inicial

                if primera.contador_inicial is not None

                else None

            )

            # =====================================================
            # CONTADOR FINAL
            # =====================================================

            contador_final = (

                ultima.contador_final

                if ultima.contador_final is not None

                else None

            )

            # =====================================================
            # FORMATEAR INICIAL
            # =====================================================

            if contador_inicial is not None:

                try:

                    contador_inicial = (

                        f"{float(contador_inicial):,.0f}"
                        .replace(",", ".")

                    )

                except (
                    ValueError,
                    TypeError
                ):

                    contador_inicial = str(
                        contador_inicial
                    )

            else:

                contador_inicial = "—"

            # =====================================================
            # FORMATEAR FINAL
            # =====================================================

            if contador_final is not None:

                try:

                    contador_final = (

                        f"{float(contador_final):,.0f}"
                        .replace(",", ".")

                    )

                except (
                    ValueError,
                    TypeError
                ):

                    contador_final = str(
                        contador_final
                    )

            else:

                contador_final = "—"

            # =====================================================
            # AGREGAR INICIAL
            # =====================================================

            if es_maquinaria:

                fila_inicial.append(

                    Paragraph(
                        f"{contador_inicial} h",
                        estilo_normal
                    )

                )

            else:

                fila_inicial.append(

                    Paragraph(
                        contador_inicial,
                        estilo_normal
                    )

                )

            # =====================================================
            # AGREGAR FINAL
            # =====================================================

            if es_maquinaria:

                fila_final.append(

                    Paragraph(
                        f"{contador_final} h",
                        estilo_normal
                    )

                )

            else:

                fila_final.append(

                    Paragraph(
                        contador_final,
                        estilo_normal
                    )

                )

            # =====================================================
            # OBTENER FIRMA DEL DÍA
            # =====================================================

            ruta_firma = ultima.firma_path

            imagen_firma = None

            if ruta_firma:

                try:

                    ruta_firma_normalizada = (

                        str(ruta_firma)
                        .replace("\\", os.sep)
                        .replace("/", os.sep)

                    )

                    # ---------------------------------------------
                    # RUTA ABSOLUTA
                    # ---------------------------------------------

                    if os.path.isabs(
                        ruta_firma_normalizada
                    ):

                        posibles_rutas = [

                            ruta_firma_normalizada

                        ]

                    else:

                        ruta_relativa = (
                            ruta_firma_normalizada
                            .lstrip("/\\")
                        )

                        posibles_rutas = [

                            ruta_relativa,

                            os.path.join(
                                current_app.root_path,
                                ruta_relativa
                            ),

                        ]

                    # ---------------------------------------------
                    # BUSCAR FIRMA
                    # ---------------------------------------------

                    ruta_real_firma = None

                    for ruta_posible in posibles_rutas:

                        if os.path.exists(
                            ruta_posible
                        ):

                            ruta_real_firma = (
                                ruta_posible
                            )

                            break

                    # ---------------------------------------------
                    # CREAR IMAGEN
                    # ---------------------------------------------

                    if ruta_real_firma:

                        imagen_firma = RLImage(

                            ruta_real_firma,

                            width=42,
                            height=20

                        )

                        imagen_firma.hAlign = (
                            "CENTER"
                        )

                except Exception as e:

                    current_app.logger.warning(

                        "No se pudo cargar la firma "
                        f"de la inspección "
                        f"{ultima.id}: {str(e)}"

                    )

            # =====================================================
            # AGREGAR FIRMA
            # =====================================================

            if imagen_firma:

                fila_firma.append(
                    imagen_firma
                )

            else:

                fila_firma.append(

                    Paragraph(
                        "SIN FIRMA",
                        estilo_normal
                    )

                )

        # =========================================================
        # AGREGAR LAS FILAS DIARIAS A LA MISMA MATRIZ
        # =========================================================

        filas.append(
            fila_inicial
        )

        fila_inicial_index = len(filas) - 1

        filas.append(
            fila_final
        )

        fila_final_index = len(filas) - 1

        filas.append(
            fila_firma
        )

        fila_firma_index = len(filas) - 1

        # =========================================================
        # CREAR TABLA COMPLETA
        # =========================================================

        tabla = Table(

            filas,

            colWidths=[

                ancho_item

            ]
            +
            [
                ancho_dia
                for _ in dias_semana
            ],

            repeatRows=1,

        )

        # =========================================================
        # ESTILOS MATRIZ
        # =========================================================

        estilos_tabla = [

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.35,
                colors.black,
            ),

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                AZUL_INTELLIFEET,
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white,
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE",
            ),

            (
                "ALIGN",
                (1, 0),
                (-1, -1),
                "CENTER",
            ),

            (
                "LEFTPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),

            (
                "RIGHTPADDING",
                (0, 0),
                (-1, -1),
                3,
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                2,
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                2,
            ),

        ]

        # =========================================================
        # CATEGORÍAS
        # =========================================================

        for fila_categoria in filas_componentes:

            estilos_tabla.extend([

                (
                    "SPAN",
                    (0, fila_categoria),
                    (-1, fila_categoria),
                ),

                (
                    "BACKGROUND",
                    (0, fila_categoria),
                    (-1, fila_categoria),
                    AZUL_CLARO,
                ),

                (
                    "TEXTCOLOR",
                    (0, fila_categoria),
                    (-1, fila_categoria),
                    AZUL_OSCURO,
                ),

                (
                    "FONTNAME",
                    (0, fila_categoria),
                    (-1, fila_categoria),
                    "Helvetica-Bold",
                ),

                (
                    "ALIGN",
                    (0, fila_categoria),
                    (-1, fila_categoria),
                    "LEFT",
                ),

            ])

        # =========================================================
        # MARCAR DÍAS FUTUROS
        # =========================================================
        #
        # IMPORTANTE:
        # Solo se aplica hasta la matriz de preguntas.
        # No se pinta la sección de KM/FIRMA.
        # =========================================================

        for indice_dia, fecha in enumerate(
            dias_semana,
            start=1
        ):

            if fecha > hoy:

                estilos_tabla.append(

                    (
                        "BACKGROUND",
                        (indice_dia, 1),
                        (
                            indice_dia,
                            fila_final_matriz
                        ),
                        GRIS_FUTURO,
                    )

                )

        # =========================================================
        # FILA CONTROL DIARIO
        # =========================================================

        estilos_tabla.extend([

            (
                "SPAN",
                (0, fila_control_diario_index),
                (-1, fila_control_diario_index),
            ),

            (
                "BACKGROUND",
                (0, fila_control_diario_index),
                (-1, fila_control_diario_index),
                AZUL_MUY_CLARO,
            ),

            (
                "TEXTCOLOR",
                (0, fila_control_diario_index),
                (-1, fila_control_diario_index),
                AZUL_OSCURO,
            ),

            (
                "ALIGN",
                (0, fila_control_diario_index),
                (-1, fila_control_diario_index),
                "CENTER",
            ),

            (
                "TOPPADDING",
                (0, fila_control_diario_index),
                (-1, fila_control_diario_index),
                4,
            ),

            (
                "BOTTOMPADDING",
                (0, fila_control_diario_index),
                (-1, fila_control_diario_index),
                4,
            ),

        ])

        # =========================================================
        # FILAS DIARIAS
        # =========================================================

        for fila_diaria in [

            fila_inicial_index,
            fila_final_index,
            fila_firma_index,

        ]:

            estilos_tabla.extend([

                (
                    "BACKGROUND",
                    (0, fila_diaria),
                    (0, fila_diaria),
                    AZUL_MUY_CLARO,
                ),

                (
                    "TEXTCOLOR",
                    (0, fila_diaria),
                    (0, fila_diaria),
                    AZUL_OSCURO,
                ),

                (
                    "VALIGN",
                    (0, fila_diaria),
                    (-1, fila_diaria),
                    "MIDDLE",
                ),

                (
                    "ALIGN",
                    (1, fila_diaria),
                    (-1, fila_diaria),
                    "CENTER",
                ),

                (
                    "TOPPADDING",
                    (0, fila_diaria),
                    (-1, fila_diaria),
                    3,
                ),

                (
                    "BOTTOMPADDING",
                    (0, fila_diaria),
                    (-1, fila_diaria),
                    3,
                ),

            ])

        # =========================================================
        # FIRMA
        # =========================================================

        estilos_tabla.extend([

            (
                "TOPPADDING",
                (1, fila_firma_index),
                (-1, fila_firma_index),
                2,
            ),

            (
                "BOTTOMPADDING",
                (1, fila_firma_index),
                (-1, fila_firma_index),
                2,
            ),

        ])

        # =========================================================
        # APLICAR ESTILOS
        # =========================================================

        tabla.setStyle(
            TableStyle(
                estilos_tabla
            )
        )

        # =========================================================
        # AGREGAR MATRIZ COMPLETA
        # =========================================================

        elementos.append(
            tabla
        )

        elementos.append(
            Spacer(1, 8)
        )

        # =========================================================
        # OBSERVACIONES
        # =========================================================

        observaciones_texto = []

        for inspeccion in inspecciones:

            if inspeccion.observaciones_generales:

                fecha_observacion = (

                    inspeccion.hora_inicio.strftime(
                        "%d/%m"
                    )

                    if inspeccion.hora_inicio

                    else ""

                )

                observaciones_texto.append(

                    f"{fecha_observacion} - "
                    f"{inspeccion.observaciones_generales}"

                )

        texto_observaciones = (

            "<br/>".join(
                observaciones_texto
            )

            if observaciones_texto

            else ""

        )

        observaciones = Table(

            [

                [

                    Paragraph(
                        "<b>OBSERVACIONES:</b>",
                        estilo_header
                    )

                ],

                [

                    Paragraph(
                        texto_observaciones,
                        estilo_item
                    )

                ],

            ],

            colWidths=[
                ancho_total
            ],

            rowHeights=[
                18,
                40,
            ],

        )

        observaciones.setStyle(

            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.black,
                ),

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    AZUL_MUY_CLARO,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),

            ])

        )

        elementos.append(
            observaciones
        )

        elementos.append(
            Spacer(1, 5)
        )

        # =========================================================
        # FUERA DE SERVICIO
        # =========================================================

        fuera_servicio = Table(

            [[

                Paragraph(
                    "<b>FUERA DE SERVICIO</b>",
                    estilo_header
                ),

                Paragraph(
                    "SI ______",
                    estilo_normal
                ),

                Paragraph(
                    "NO ______",
                    estilo_normal
                ),

            ]],

            colWidths=[

                250,
                250,
                250,

            ],

            rowHeights=[
                30
            ],

        )

        fuera_servicio.setStyle(

            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.4,
                    colors.black,
                ),

                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    AZUL_MUY_CLARO,
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, -1),
                    AZUL_OSCURO,
                ),

                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
                ),

            ])

        )

        elementos.append(
            fuera_servicio
        )

        # =========================================================
        # GENERAR PDF
        # =========================================================

        doc.build(
            elementos
        )

        buffer.seek(0)

        return buffer
    
    @staticmethod
    def descargar_excel_preoperacionales(
        mes, anio, vehiculo_id=None, maquinaria_id=None
    ):

        inspecciones = InspeccionService.obtener_reporte_preoperacionales(
            mes,
            anio,
            vehiculo_id,
            maquinaria_id
        )

        if not inspecciones:
            raise Exception(
                "No existen inspecciones para el periodo especificado."
            )

        # =========================================================
        # IMPORTACIONES
        # =========================================================

        from io import BytesIO
        import os

        from openpyxl import Workbook
        from openpyxl.styles import (
            Font,
            PatternFill,
            Border,
            Side,
            Alignment
        )
        from openpyxl.drawing.image import Image
        from openpyxl.utils import get_column_letter

        # =========================================================
        # WORKBOOK
        # =========================================================

        wb = Workbook()

        ws = wb.active
        ws.title = "R. PREOPERACIONAL"

        ws.sheet_view.showGridLines = False

        # =========================================================
        # COLORES CORPORATIVOS
        # =========================================================

        AZUL_OSCURO = "172554"
        AZUL = "1E40AF"
        AZUL_MEDIO = "2563EB"
        AZUL_CLARO = "EFF6FF"
        AZUL_HEADER = "DBEAFE"

        VERDE = "15803D"
        VERDE_CLARO = "DCFCE7"

        ROJO = "B91C1C"
        ROJO_CLARO = "FEE2E2"

        NARANJA = "C2410C"
        NARANJA_CLARO = "FFEDD5"

        GRIS_OSCURO = "334155"
        GRIS_MEDIO = "64748B"
        GRIS_CLARO = "F8FAFC"
        GRIS_BORDE = "CBD5E1"

        BLANCO = "FFFFFF"

        # =========================================================
        # FILLS
        # =========================================================

        fill_azul_oscuro = PatternFill(
            "solid",
            fgColor=AZUL_OSCURO
        )

        fill_azul = PatternFill(
            "solid",
            fgColor=AZUL
        )

        fill_azul_medio = PatternFill(
            "solid",
            fgColor=AZUL_MEDIO
        )

        fill_azul_claro = PatternFill(
            "solid",
            fgColor=AZUL_CLARO
        )

        fill_azul_header = PatternFill(
            "solid",
            fgColor=AZUL_HEADER
        )

        fill_gris = PatternFill(
            "solid",
            fgColor=GRIS_CLARO
        )

        fill_blanco = PatternFill(
            "solid",
            fgColor=BLANCO
        )

        fill_verde = PatternFill(
            "solid",
            fgColor=VERDE_CLARO
        )

        fill_rojo = PatternFill(
            "solid",
            fgColor=ROJO_CLARO
        )

        fill_naranja = PatternFill(
            "solid",
            fgColor=NARANJA_CLARO
        )

        # =========================================================
        # BORDES
        # =========================================================

        thin = Side(
            border_style="thin",
            color=GRIS_BORDE
        )

        medium = Side(
            border_style="medium",
            color=AZUL
        )

        border = Border(
            left=thin,
            right=thin,
            top=thin,
            bottom=thin
        )

        border_seccion = Border(
            left=medium,
            right=medium,
            top=medium,
            bottom=medium
        )

        # =========================================================
        # ALINEACIONES
        # =========================================================

        center = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True
        )

        left = Alignment(
            horizontal="left",
            vertical="center",
            wrap_text=True
        )

        # =========================================================
        # FUENTES
        # =========================================================

        font_titulo = Font(
            name="Calibri",
            bold=True,
            color=BLANCO,
            size=16
        )

        font_subtitulo = Font(
            name="Calibri",
            bold=True,
            color=BLANCO,
            size=11
        )

        font_seccion = Font(
            name="Calibri",
            bold=True,
            color=BLANCO,
            size=11
        )

        font_label = Font(
            name="Calibri",
            bold=True,
            color=GRIS_OSCURO,
            size=10
        )

        font_normal = Font(
            name="Calibri",
            color=GRIS_OSCURO,
            size=10
        )

        font_pequena = Font(
            name="Calibri",
            color=GRIS_MEDIO,
            size=9
        )

        font_header = Font(
            name="Calibri",
            bold=True,
            color=BLANCO,
            size=10
        )

        font_indicador = Font(
            name="Calibri",
            bold=True,
            color=AZUL_OSCURO,
            size=13
        )

        font_indicador_label = Font(
            name="Calibri",
            bold=True,
            color=GRIS_MEDIO,
            size=9
        )

        # =========================================================
        # HELPERS
        # =========================================================

        def texto_seguro(valor, defecto=""):
            if valor is None:
                return defecto

            valor = str(valor).strip()

            return valor if valor else defecto

        def aplicar_borde_rango(hoja, rango):
            for fila in hoja[rango]:
                for celda in fila:
                    celda.border = border

        def aplicar_encabezado(
            hoja,
            fila,
            columnas,
            titulo,
            fill=fill_azul_medio
        ):

            hoja.merge_cells(
                start_row=fila,
                start_column=1,
                end_row=fila,
                end_column=columnas
            )

            celda = hoja.cell(
                fila,
                1
            )

            celda.value = titulo
            celda.fill = fill
            celda.font = font_seccion
            celda.alignment = center
            celda.border = border_seccion

            for col in range(1, columnas + 1):
                hoja.cell(
                    fila,
                    col
                ).border = border_seccion

        def aplicar_estado(celda, estado):

            estado = texto_seguro(
                estado
            ).upper()

            if estado in (
                "FINALIZADA",
                "REVISADA",
                "APROBADO",
                "APROBADA"
            ):

                celda.fill = fill_verde
                celda.font = Font(
                    bold=True,
                    color=VERDE,
                    size=9
                )

            elif estado in (
                "PENDIENTE_CIERRE",
                "EN_PROCESO"
            ):

                celda.fill = fill_naranja
                celda.font = Font(
                    bold=True,
                    color=NARANJA,
                    size=9
                )

            elif estado in (
                "ANULADA",
                "RECHAZADO",
                "RECHAZADA"
            ):

                celda.fill = fill_rojo
                celda.font = Font(
                    bold=True,
                    color=ROJO,
                    size=9
                )

            else:

                celda.fill = fill_gris
                celda.font = font_normal

        def aplicar_respuesta(celda, valor):

            valor_normalizado = (
                texto_seguro(valor)
                .upper()
                .strip()
            )

            if valor_normalizado in [
                "SI",
                "SÍ",
                "OK",
                "CUMPLE",
                "BUENO",
                "TRUE",
                "1"
            ]:

                celda.fill = fill_verde
                celda.font = Font(
                    bold=True,
                    color=VERDE,
                    size=10
                )

            elif valor_normalizado in [
                "NO",
                "NO CUMPLE",
                "MALO",
                "FALSE",
                "0"
            ]:

                celda.fill = fill_rojo
                celda.font = Font(
                    bold=True,
                    color=ROJO,
                    size=10
                )

            elif valor_normalizado in [
                "N/A",
                "NA",
                "NO APLICA"
            ]:

                celda.fill = fill_naranja
                celda.font = Font(
                    bold=True,
                    color=NARANJA,
                    size=10
                )

        # =========================================================
        # CONFIGURACIÓN HOJA PRINCIPAL
        # =========================================================

        columnas_principal = {
            "A": 15,
            "B": 12,
            "C": 20,
            "D": 20,
            "E": 18,
            "F": 18,
            "G": 18,
            "H": 16,
            "I": 16,
            "J": 16,
            "K": 16,
            "L": 18,
        }

        for col, ancho in columnas_principal.items():
            ws.column_dimensions[col].width = ancho

        ws.sheet_view.zoomScale = 90

        # =========================================================
        # ENCABEZADO CORPORATIVO
        # =========================================================

        ws.merge_cells("A1:B4")

        for fila in ws["A1:B4"]:
            for celda in fila:
                celda.fill = fill_azul_oscuro
                celda.border = border_seccion

        ruta_logo = "static/intellifeet.png"

        if os.path.exists(ruta_logo):

            try:

                logo = Image(ruta_logo)

                logo.width = 235
                logo.height = 115

                ws.add_image(
                    logo,
                    "A1"
                )

            except Exception:
                pass

        # =========================================================
        # TITULO
        # =========================================================

        ws.merge_cells("C1:G2")

        ws["C1"] = (
            "INTELLIFEET\n"
            "GESTIÓN DE SEGURIDAD OPERACIONAL"
        )

        ws["C1"].fill = fill_azul_oscuro
        ws["C1"].font = font_titulo
        ws["C1"].alignment = center
        ws["C1"].border = border_seccion

        for fila in range(1, 3):
            for col in range(3, 8):
                ws.cell(
                    fila,
                    col
                ).fill = fill_azul_oscuro

        # =========================================================
        # NOMBRE DEL REPORTE
        # =========================================================

        ws.merge_cells("C3:G4")

        ws["C3"] = (
            "REPORTE DE INSPECCIONES PREOPERACIONALES"
        )

        ws["C3"].fill = fill_azul_claro
        ws["C3"].font = Font(
            bold=True,
            color=AZUL_OSCURO,
            size=12
        )
        ws["C3"].alignment = center
        ws["C3"].border = border_seccion

        # =========================================================
        # INFORMACIÓN DOCUMENTAL
        # =========================================================

        documentos = [
            ("H1:I1", "VERSIÓN", "001"),
            ("J1:L1", "CÓDIGO", "PRE-R-001"),
            ("H2:I2", "PERIODO", f"{mes:02d}/{anio}"),
            ("J2:L2", "SISTEMA", "INTELLIFEET"),
            ("H3:I4", "TIPO", "PREOPERACIONAL"),
            ("J3:L4", "GENERADO", "REPORTE"),
        ]

        for rango, etiqueta, valor in documentos:

            ws.merge_cells(rango)

            inicio = rango.split(":")[0]

            ws[inicio] = (
                f"{etiqueta}\n{valor}"
            )

            ws[inicio].fill = fill_azul_oscuro
            ws[inicio].font = Font(
                bold=True,
                color=BLANCO,
                size=9
            )
            ws[inicio].alignment = center

            aplicar_borde_rango(
                ws,
                rango
            )

        # =========================================================
        # ALTURA ENCABEZADO
        # =========================================================

        ws.row_dimensions[1].height = 30
        ws.row_dimensions[2].height = 30
        ws.row_dimensions[3].height = 28
        ws.row_dimensions[4].height = 28

        # =========================================================
        # INFORMACIÓN GENERAL
        # =========================================================

        aplicar_encabezado(
            ws,
            6,
            12,
            "INFORMACIÓN GENERAL DEL ACTIVO"
        )

        primera = inspecciones[0]

        activo = (
            primera.vehiculo
            if primera.vehiculo
            else primera.maquinaria
        )

        operador = primera.usuario

        # =========================================================
        # TIPO ACTIVO
        # =========================================================

        if primera.vehiculo:

            tipo_activo = "VEHÍCULO"

            tipo_vehiculo = ""

            if primera.vehiculo.tipo_vehiculo:

                tipo_vehiculo = texto_seguro(
                    primera.vehiculo.tipo_vehiculo.nombre
                )

            identificador = texto_seguro(
                primera.vehiculo.placa
            )

        else:

            tipo_activo = "MAQUINARIA"

            tipo_vehiculo = ""

            if (
                primera.maquinaria
                and primera.maquinaria.tipo_maquinaria
            ):

                tipo_vehiculo = texto_seguro(
                    primera.maquinaria.tipo_maquinaria.nombre
                )

            identificador = texto_seguro(
                primera.maquinaria.codigo
                if primera.maquinaria
                else ""
            )

        marca = texto_seguro(
            getattr(
                activo,
                "marca",
                ""
            )
        )

        modelo = texto_seguro(
            getattr(
                activo,
                "modelo",
                ""
            )
        )

        nombre_operador = texto_seguro(
            operador.nombre
            if operador
            else ""
        )

        datos_vehiculo = [

            (
                "TIPO DE ACTIVO",
                tipo_activo
            ),

            (
                "CLASE / TIPO",
                tipo_vehiculo
            ),

            (
                "PLACA / CÓDIGO",
                identificador
            ),

            (
                "MARCA",
                marca
            ),

            (
                "MODELO",
                modelo
            ),

            (
                "OPERADOR",
                nombre_operador
            ),

            (
                "PERIODO",
                f"{mes:02d}/{anio}"
            ),
        ]

        posiciones = [

            ("A8:B8", "C8:E8"),
            ("F8:G8", "H8:L8"),

            ("A10:B10", "C10:E10"),
            ("F10:G10", "H10:L10"),

            ("A12:B12", "C12:E12"),
            ("F12:G12", "H12:L12"),

            ("A13:B13", "C13:E13"),

        ]

        for i, posicion in enumerate(posiciones):

            if i >= len(datos_vehiculo):
                break

            etiqueta = datos_vehiculo[i][0]
            valor = datos_vehiculo[i][1]

            label_pos = posicion[0]
            value_pos = posicion[1]

            # -----------------------------------------------------
            # LABEL
            # -----------------------------------------------------

            ws.merge_cells(label_pos)

            celda = label_pos.split(":")[0]

            ws[celda] = etiqueta
            ws[celda].fill = fill_azul_claro
            ws[celda].font = font_label
            ws[celda].alignment = center

            aplicar_borde_rango(
                ws,
                label_pos
            )

            # -----------------------------------------------------
            # VALOR
            # -----------------------------------------------------

            ws.merge_cells(value_pos)

            celda_valor = value_pos.split(":")[0]

            ws[celda_valor] = valor
            ws[celda_valor].fill = fill_blanco
            ws[celda_valor].font = font_normal
            ws[celda_valor].alignment = center

            aplicar_borde_rango(
                ws,
                value_pos
            )

        # =========================================================
        # RESUMEN ESTADÍSTICO
        # =========================================================

        total_inspecciones = len(
            inspecciones
        )

        total_anomalias = sum(
            len(i.anomalias)
            for i in inspecciones
        )

        finalizadas = len([
            i
            for i in inspecciones
            if (
                texto_seguro(
                    i.estado
                ).upper()
                in [
                    "FINALIZADA",
                    "REVISADA"
                ]
            )
        ])

        pendientes = len([
            i
            for i in inspecciones
            if (
                texto_seguro(
                    i.estado
                ).upper()
                == "PENDIENTE_CIERRE"
            )
        ])

        anuladas = len([
            i
            for i in inspecciones
            if (
                texto_seguro(
                    i.estado
                ).upper()
                == "ANULADA"
            )
        ])

        cumplimiento = 0

        if total_inspecciones > 0:

            cumplimiento = round(
                (
                    finalizadas
                    / total_inspecciones
                ) * 100,
                2
            )

        aplicar_encabezado(
            ws,
            15,
            12,
            "RESUMEN ESTADÍSTICO DEL PERIODO"
        )

        indicadores = [

            (
                "TOTAL INSPECCIONES",
                total_inspecciones,
                fill_azul_claro
            ),

            (
                "FINALIZADAS / REVISADAS",
                finalizadas,
                fill_verde
            ),

            (
                "PENDIENTES DE CIERRE",
                pendientes,
                fill_naranja
            ),

            (
                "ANOMALÍAS",
                total_anomalias,
                fill_rojo
            ),

            (
                "ANULADAS",
                anuladas,
                fill_gris
            ),

            (
                "CUMPLIMIENTO",
                f"{cumplimiento}%",
                fill_azul_claro
            ),
        ]

        posiciones_indicadores = [

            ("A17:B19"),
            ("C17:D19"),
            ("E17:F19"),
            ("G17:H19"),
            ("I17:J19"),
            ("K17:L19"),
        ]

        for index, rango in enumerate(
            posiciones_indicadores
        ):

            ws.merge_cells(rango)

            celda = rango.split(":")[0]

            etiqueta = indicadores[index][0]
            valor = indicadores[index][1]
            fill = indicadores[index][2]

            ws[celda] = (
                f"{etiqueta}\n\n"
                f"{valor}"
            )

            ws[celda].fill = fill
            ws[celda].font = font_indicador
            ws[celda].alignment = center

            aplicar_borde_rango(
                ws,
                rango
            )

        ws.row_dimensions[17].height = 24
        ws.row_dimensions[18].height = 24
        ws.row_dimensions[19].height = 24

        # =========================================================
        # INFORMACIÓN DE FILTRO
        # =========================================================

        aplicar_encabezado(
            ws,
            21,
            12,
            "FILTROS APLICADOS"
        )

        filtro = "TODOS LOS ACTIVOS"

        if vehiculo_id:
            filtro = "VEHÍCULO SELECCIONADO"

        elif maquinaria_id:
            filtro = "MAQUINARIA SELECCIONADA"

        ws.merge_cells("A23:L23")

        ws["A23"] = (
            f"Periodo: {mes:02d}/{anio}   |   "
            f"Filtro: {filtro}"
        )

        ws["A23"].fill = fill_gris
        ws["A23"].font = font_normal
        ws["A23"].alignment = center

        aplicar_borde_rango(
            ws,
            "A23:L23"
        )

        # =========================================================
        # CONFIGURACIÓN IMPRESIÓN
        # =========================================================

        ws.freeze_panes = "A6"

        ws.print_title_rows = "1:4"

        ws.page_setup.orientation = "landscape"
        ws.page_setup.paperSize = ws.PAPERSIZE_A4

        ws.page_setup.fitToWidth = 1
        ws.page_setup.fitToHeight = 0

        ws.sheet_properties.pageSetUpPr.fitToPage = True

        ws.page_margins.left = 0.25
        ws.page_margins.right = 0.25
        ws.page_margins.top = 0.40
        ws.page_margins.bottom = 0.40

        ws.oddFooter.center.text = (
            "IntelliFeet · Sistema de Gestión Operacional"
        )

        ws.oddFooter.right.text = (
            "Página &P de &N"
        )

        # =========================================================
        # HOJA HISTORIAL
        # =========================================================

        historial = wb.create_sheet(
            "Historial"
        )

        historial.sheet_view.showGridLines = False
        historial.sheet_view.zoomScale = 90

        columnas_historial = {

            "A": 15,
            "B": 10,
            "C": 20,
            "D": 13,
            "E": 28,
            "F": 48,
            "G": 18,
            "H": 18,
            "I": 18,

        }

        for col, ancho in columnas_historial.items():

            historial.column_dimensions[
                col
            ].width = ancho

        # =========================================================
        # TITULO
        # =========================================================

        historial.merge_cells("A1:I1")

        historial["A1"] = (
            "HISTORIAL DE INSPECCIONES PREOPERACIONALES"
        )

        historial["A1"].fill = fill_azul_oscuro
        historial["A1"].font = font_titulo
        historial["A1"].alignment = center

        aplicar_borde_rango(
            historial,
            "A1:I1"
        )

        historial.row_dimensions[1].height = 35

        # =========================================================
        # SUBTITULO
        # =========================================================

        historial.merge_cells("A2:I2")

        historial["A2"] = (
            f"Periodo consultado: {mes:02d}/{anio}"
        )

        historial["A2"].fill = fill_azul_claro
        historial["A2"].font = Font(
            bold=True,
            color=AZUL_OSCURO,
            size=10
        )

        historial["A2"].alignment = center

        aplicar_borde_rango(
            historial,
            "A2:I2"
        )

        # =========================================================
        # HEADERS
        # =========================================================

        headers_historial = [

            "FECHA",
            "HORA",
            "ESTADO",
            "ANOMALÍAS",
            "OPERADOR",
            "OBSERVACIÓN GENERAL",
            "LECTURA INICIAL",
            "LECTURA FINAL",
            "DIFERENCIA",

        ]

        for col, titulo_col in enumerate(
            headers_historial,
            1
        ):

            celda = historial.cell(
                4,
                col
            )

            celda.value = titulo_col
            celda.fill = fill_azul_medio
            celda.font = font_header
            celda.alignment = center
            celda.border = border

        # =========================================================
        # DATOS HISTORIAL
        # =========================================================

        fila = 5

        for inspeccion in inspecciones:

            fecha_inicio = inspeccion.hora_inicio

            historial.cell(
                fila,
                1
            ).value = (
                fecha_inicio.strftime(
                    "%d/%m/%Y"
                )
                if fecha_inicio
                else ""
            )

            historial.cell(
                fila,
                2
            ).value = (
                fecha_inicio.strftime(
                    "%H:%M"
                )
                if fecha_inicio
                else ""
            )

            estado = texto_seguro(
                inspeccion.estado
            )

            celda_estado = historial.cell(
                fila,
                3
            )

            celda_estado.value = estado
            aplicar_estado(
                celda_estado,
                estado
            )

            historial.cell(
                fila,
                4
            ).value = len(
                inspeccion.anomalias
            )

            historial.cell(
                fila,
                5
            ).value = (
                inspeccion.usuario.nombre
                if inspeccion.usuario
                else ""
            )

            historial.cell(
                fila,
                6
            ).value = (
                inspeccion.observaciones_generales
                or ""
            )

            lectura_inicial = (
                float(
                    inspeccion.contador_inicial
                )
                if inspeccion.contador_inicial
                is not None
                else None
            )

            lectura_final = (
                float(
                    inspeccion.contador_final
                )
                if inspeccion.contador_final
                is not None
                else None
            )

            historial.cell(
                fila,
                7
            ).value = lectura_inicial

            historial.cell(
                fila,
                8
            ).value = lectura_final

            if (
                lectura_inicial is not None
                and lectura_final is not None
            ):

                historial.cell(
                    fila,
                    9
                ).value = round(
                    lectura_final
                    - lectura_inicial,
                    2
                )

            # -----------------------------------------------------
            # ESTILOS
            # -----------------------------------------------------

            for col in range(
                1,
                10
            ):

                celda = historial.cell(
                    fila,
                    col
                )

                celda.border = border

                if col in [
                    1,
                    2,
                    3,
                    4,
                    7,
                    8,
                    9
                ]:

                    celda.alignment = center

                else:

                    celda.alignment = left

                if col != 3:

                    if fila % 2 == 0:
                        celda.fill = fill_gris
                    else:
                        celda.fill = fill_blanco

                    celda.font = font_normal

            # -----------------------------------------------------
            # ANOMALÍAS
            # -----------------------------------------------------

            celda_anomalias = historial.cell(
                fila,
                4
            )

            if len(inspeccion.anomalias) > 0:

                celda_anomalias.fill = fill_rojo
                celda_anomalias.font = Font(
                    bold=True,
                    color=ROJO,
                    size=10
                )

            else:

                celda_anomalias.fill = fill_verde
                celda_anomalias.font = Font(
                    bold=True,
                    color=VERDE,
                    size=10
                )

            fila += 1

        historial.freeze_panes = "A5"

        if fila > 5:

            historial.auto_filter.ref = (
                f"A4:I{fila - 1}"
            )

        historial.print_title_rows = "1:4"

        historial.page_setup.orientation = "landscape"
        historial.page_setup.paperSize = (
            historial.PAPERSIZE_A4
        )

        historial.page_setup.fitToWidth = 1
        historial.page_setup.fitToHeight = 0

        historial.sheet_properties.pageSetUpPr.fitToPage = True

        historial.oddFooter.center.text = (
            "IntelliFeet · Historial de inspecciones"
        )

        historial.oddFooter.right.text = (
            "Página &P de &N"
        )

        # =========================================================
        # HOJAS INDIVIDUALES
        # =========================================================

        for indice, inspeccion in enumerate(
            inspecciones,
            start=1
        ):

            nombre_hoja = (
                f"INS {indice}"
            )

            hoja = wb.create_sheet(
                nombre_hoja[:31]
            )

            hoja.sheet_view.showGridLines = False
            hoja.sheet_view.zoomScale = 90

            # =====================================================
            # COLUMNAS
            # =====================================================

            columnas_detalle = {

                "A": 24,
                "B": 43,
                "C": 17,
                "D": 42,
                "E": 30,

            }

            for col, ancho in columnas_detalle.items():

                hoja.column_dimensions[
                    col
                ].width = ancho

            # =====================================================
            # TITULO
            # =====================================================

            hoja.merge_cells("A1:E2")

            hoja["A1"] = (
                f"DETALLE DE INSPECCIÓN #{indice}"
            )

            hoja["A1"].fill = fill_azul_oscuro
            hoja["A1"].font = font_titulo
            hoja["A1"].alignment = center

            aplicar_borde_rango(
                hoja,
                "A1:E2"
            )

            # =====================================================
            # INFORMACIÓN
            # =====================================================

            if inspeccion.vehiculo:

                identificador = texto_seguro(
                    inspeccion.vehiculo.placa
                )

                tipo_activo = "VEHÍCULO"

                tipo_nombre = ""

                if inspeccion.vehiculo.tipo_vehiculo:

                    tipo_nombre = texto_seguro(
                        inspeccion.vehiculo.tipo_vehiculo.nombre
                    )

            else:

                identificador = texto_seguro(
                    inspeccion.maquinaria.codigo
                    if inspeccion.maquinaria
                    else ""
                )

                tipo_activo = "MAQUINARIA"

                tipo_nombre = ""

                if (
                    inspeccion.maquinaria
                    and inspeccion.maquinaria.tipo_maquinaria
                ):

                    tipo_nombre = texto_seguro(
                        inspeccion.maquinaria.tipo_maquinaria.nombre
                    )

            datos = [

                (
                    "FECHA",
                    (
                        inspeccion.hora_inicio.strftime(
                            "%d/%m/%Y %H:%M"
                        )
                        if inspeccion.hora_inicio
                        else ""
                    )
                ),

                (
                    "ESTADO",
                    texto_seguro(
                        inspeccion.estado
                    )
                ),

                (
                    "TIPO DE ACTIVO",
                    tipo_activo
                ),

                (
                    "CLASE / TIPO",
                    tipo_nombre
                ),

                (
                    "PLACA / CÓDIGO",
                    identificador
                ),

                (
                    "OPERADOR",
                    (
                        inspeccion.usuario.nombre
                        if inspeccion.usuario
                        else ""
                    )
                ),

                (
                    "LECTURA INICIAL",
                    (
                        float(
                            inspeccion.contador_inicial
                        )
                        if inspeccion.contador_inicial
                        is not None
                        else ""
                    )
                ),

                (
                    "LECTURA FINAL",
                    (
                        float(
                            inspeccion.contador_final
                        )
                        if inspeccion.contador_final
                        is not None
                        else ""
                    )
                ),

            ]

            fila = 4

            for campo, valor in datos:

                hoja.cell(
                    fila,
                    1
                ).value = campo

                hoja.cell(
                    fila,
                    1
                ).fill = fill_azul_claro

                hoja.cell(
                    fila,
                    1
                ).font = font_label

                hoja.cell(
                    fila,
                    1
                ).alignment = center

                hoja.cell(
                    fila,
                    1
                ).border = border

                hoja.merge_cells(
                    start_row=fila,
                    start_column=2,
                    end_row=fila,
                    end_column=5
                )

                hoja.cell(
                    fila,
                    2
                ).value = valor

                hoja.cell(
                    fila,
                    2
                ).fill = fill_blanco

                hoja.cell(
                    fila,
                    2
                ).font = font_normal

                hoja.cell(
                    fila,
                    2
                ).alignment = left

                aplicar_borde_rango(
                    hoja,
                    f"B{fila}:E{fila}"
                )

                if campo == "ESTADO":

                    aplicar_estado(
                        hoja.cell(
                            fila,
                            2
                        ),
                        valor
                    )

                fila += 1

            # =====================================================
            # OBSERVACIONES GENERALES
            # =====================================================

            fila += 1

            aplicar_encabezado(
                hoja,
                fila,
                5,
                "OBSERVACIONES GENERALES"
            )

            fila += 1

            hoja.merge_cells(
                start_row=fila,
                start_column=1,
                end_row=fila + 2,
                end_column=5
            )

            hoja.cell(
                fila,
                1
            ).value = (
                inspeccion.observaciones_generales
                or "Sin observaciones generales."
            )

            hoja.cell(
                fila,
                1
            ).alignment = Alignment(
                horizontal="left",
                vertical="top",
                wrap_text=True
            )

            hoja.cell(
                fila,
                1
            ).font = font_normal

            aplicar_borde_rango(
                hoja,
                f"A{fila}:E{fila + 2}"
            )

            fila += 4

            # =====================================================
            # RESPUESTAS
            # =====================================================

            aplicar_encabezado(
                hoja,
                fila,
                5,
                "RESULTADO DE LA INSPECCIÓN"
            )

            fila += 1

            headers = [

                "CATEGORÍA",
                "PREGUNTA / ÍTEM",
                "RESPUESTA",
                "OBSERVACIÓN",
                "EVIDENCIA FOTOGRÁFICA",

            ]

            for col, titulo_col in enumerate(
                headers,
                1
            ):

                celda = hoja.cell(
                    fila,
                    col
                )

                celda.value = titulo_col
                celda.fill = fill_azul_medio
                celda.font = font_header
                celda.alignment = center
                celda.border = border

            fila += 1

            # =====================================================
            # RESPUESTAS ORDENADAS
            # =====================================================

            respuestas_ordenadas = sorted(

                inspeccion.respuestas,

                key=lambda respuesta: (

                    getattr(
                        getattr(
                            respuesta.item,
                            "categoria",
                            None
                        ),
                        "orden",
                        9999
                    ),

                    getattr(
                        respuesta.item,
                        "orden",
                        9999
                    ),

                    respuesta.item.id
                    if respuesta.item
                    else 9999

                )

            )

            for respuesta in respuestas_ordenadas:

                item = respuesta.item

                if not item:
                    continue

                categoria = getattr(
                    item,
                    "categoria",
                    None
                )

                nombre_categoria = texto_seguro(
                    categoria.nombre
                    if categoria
                    else ""
                )

                pregunta = texto_seguro(
                    item.descripcion
                )

                valor = texto_seguro(
                    respuesta.valor
                )

                observacion = texto_seguro(
                    respuesta.observacion,
                    "Sin observación."
                )

                # -------------------------------------------------
                # DATOS
                # -------------------------------------------------

                hoja.cell(
                    fila,
                    1
                ).value = nombre_categoria

                hoja.cell(
                    fila,
                    2
                ).value = pregunta

                hoja.cell(
                    fila,
                    3
                ).value = valor

                hoja.cell(
                    fila,
                    4
                ).value = observacion

                # -------------------------------------------------
                # ESTILOS
                # -------------------------------------------------

                for col in range(
                    1,
                    6
                ):

                    celda = hoja.cell(
                        fila,
                        col
                    )

                    celda.border = border

                    if col == 3:
                        celda.alignment = center
                    else:
                        celda.alignment = left

                    if fila % 2 == 0:
                        celda.fill = fill_gris
                    else:
                        celda.fill = fill_blanco

                    celda.font = font_normal

                # -------------------------------------------------
                # COLOR RESPUESTA
                # -------------------------------------------------

                aplicar_respuesta(
                    hoja.cell(
                        fila,
                        3
                    ),
                    valor
                )

                # -------------------------------------------------
                # FOTOS
                # -------------------------------------------------

                fotos = (
                    respuesta.fotos
                    if respuesta.fotos
                    else []
                )

                fotos_validas = []

                for foto in fotos[:3]:

                    archivo = texto_seguro(
                        foto.archivo
                        if foto
                        else ""
                    )

                    if not archivo:
                        continue

                    posibles_rutas = [

                        archivo,

                        os.path.join(
                            "uploads",
                            archivo
                        ),

                        os.path.join(
                            "static",
                            archivo
                        ),

                    ]

                    ruta_foto = None

                    for ruta in posibles_rutas:

                        if os.path.exists(ruta):

                            ruta_foto = ruta
                            break

                    if ruta_foto:

                        fotos_validas.append(
                            ruta_foto
                        )

                if fotos_validas:

                    try:

                        # -------------------------------------------------
                        # INSERTAR PRIMERA FOTO
                        # -------------------------------------------------

                        imagen = Image(
                            fotos_validas[0]
                        )

                        imagen.width = 145
                        imagen.height = 105

                        hoja.add_image(
                            imagen,
                            f"E{fila}"
                        )

                        hoja.row_dimensions[
                            fila
                        ].height = 85

                        # -------------------------------------------------
                        # INFORMACIÓN DE FOTOS ADICIONALES
                        # -------------------------------------------------

                        if len(fotos_validas) > 1:

                            hoja.cell(
                                fila,
                                5
                            ).comment = (
                                f"Esta respuesta contiene "
                                f"{len(fotos_validas)} evidencias "
                                f"fotográficas."
                            )

                    except Exception:

                        hoja.cell(
                            fila,
                            5
                        ).value = (
                            "Evidencia fotográfica"
                        )

                        hoja.cell(
                            fila,
                            5
                        ).alignment = center

                else:

                    hoja.cell(
                        fila,
                        5
                    ).value = (
                        "SIN EVIDENCIA"
                    )

                    hoja.cell(
                        fila,
                        5
                    ).font = font_pequena

                    hoja.cell(
                        fila,
                        5
                    ).alignment = center

                fila += 1

            # =====================================================
            # ANOMALÍAS
            # =====================================================

            if inspeccion.anomalias:

                fila += 2

                aplicar_encabezado(
                    hoja,
                    fila,
                    5,
                    "ANOMALÍAS REPORTADAS",
                    fill=fill_rojo
                )

                fila += 1

                headers_anomalias = [

                    "TÍTULO",
                    "DESCRIPCIÓN",
                    "PRIORIDAD",
                    "ESTADO",
                    "FECHA",

                ]

                for col, titulo_col in enumerate(
                    headers_anomalias,
                    1
                ):

                    celda = hoja.cell(
                        fila,
                        col
                    )

                    celda.value = titulo_col
                    celda.fill = fill_azul_medio
                    celda.font = font_header
                    celda.alignment = center
                    celda.border = border

                fila += 1

                for anomalia in inspeccion.anomalias:

                    hoja.cell(
                        fila,
                        1
                    ).value = texto_seguro(
                        anomalia.titulo
                    )

                    hoja.cell(
                        fila,
                        2
                    ).value = texto_seguro(
                        anomalia.descripcion
                    )

                    prioridad = texto_seguro(
                        getattr(
                            anomalia,
                            "prioridad",
                            ""
                        )
                    )

                    estado_anomalia = texto_seguro(
                        getattr(
                            anomalia,
                            "estado",
                            ""
                        )
                    )

                    hoja.cell(
                        fila,
                        3
                    ).value = prioridad

                    hoja.cell(
                        fila,
                        4
                    ).value = estado_anomalia

                    fecha_anomalia = getattr(
                        anomalia,
                        "created_at",
                        None
                    )

                    hoja.cell(
                        fila,
                        5
                    ).value = (
                        fecha_anomalia.strftime(
                            "%d/%m/%Y %H:%M"
                        )
                        if fecha_anomalia
                        else ""
                    )

                    for col in range(
                        1,
                        6
                    ):

                        celda = hoja.cell(
                            fila,
                            col
                        )

                        celda.border = border
                        celda.alignment = left
                        celda.font = font_normal

                        if fila % 2 == 0:
                            celda.fill = fill_rojo
                        else:
                            celda.fill = fill_blanco

                    # ---------------------------------------------
                    # PRIORIDAD
                    # ---------------------------------------------

                    if prioridad.upper() == "CRITICA":
                        hoja.cell(
                            fila,
                            3
                        ).fill = fill_rojo

                        hoja.cell(
                            fila,
                            3
                        ).font = Font(
                            bold=True,
                            color=ROJO
                        )

                    elif prioridad.upper() == "ALTA":
                        hoja.cell(
                            fila,
                            3
                        ).fill = fill_naranja

                        hoja.cell(
                            fila,
                            3
                        ).font = Font(
                            bold=True,
                            color=NARANJA
                        )

                    fila += 1

            # =====================================================
            # FIRMA / CIERRE
            # =====================================================

            fila += 2

            aplicar_encabezado(
                hoja,
                fila,
                5,
                "CIERRE DE LA INSPECCIÓN"
            )

            fila += 1

            datos_cierre = [

                (
                    "FIRMA REGISTRADA",
                    "SÍ"
                    if inspeccion.firma_path
                    else "NO"
                ),

                (
                    "TRATAMIENTO DE DATOS",
                    "ACEPTADO"
                    if inspeccion.tratamiento_datos_aceptado
                    else "NO REGISTRADO"
                ),

                (
                    "CONFIRMACIÓN DE FIRMA",
                    "CONFIRMADA"
                    if inspeccion.confirma_firma
                    else "NO REGISTRADA"
                ),

                (
                    "FECHA CONFIRMACIÓN",
                    (
                        inspeccion.confirmacion_fecha.strftime(
                            "%d/%m/%Y %H:%M"
                        )
                        if inspeccion.confirmacion_fecha
                        else ""
                    )
                ),

            ]

            for campo, valor in datos_cierre:

                hoja.cell(
                    fila,
                    1
                ).value = campo

                hoja.cell(
                    fila,
                    1
                ).fill = fill_azul_claro
                hoja.cell(
                    fila,
                    1
                ).font = font_label
                hoja.cell(
                    fila,
                    1
                ).alignment = center
                hoja.cell(
                    fila,
                    1
                ).border = border

                hoja.merge_cells(
                    start_row=fila,
                    start_column=2,
                    end_row=fila,
                    end_column=5
                )

                hoja.cell(
                    fila,
                    2
                ).value = valor
                hoja.cell(
                    fila,
                    2
                ).font = font_normal
                hoja.cell(
                    fila,
                    2
                ).alignment = left

                aplicar_borde_rango(
                    hoja,
                    f"B{fila}:E{fila}"
                )

                fila += 1

            # =====================================================
            # CONFIGURACIÓN IMPRESIÓN
            # =====================================================

            hoja.freeze_panes = "A14"

            hoja.page_setup.orientation = "landscape"
            hoja.page_setup.paperSize = (
                hoja.PAPERSIZE_A4
            )

            hoja.page_setup.fitToWidth = 1
            hoja.page_setup.fitToHeight = 0

            hoja.sheet_properties.pageSetUpPr.fitToPage = True

            hoja.page_margins.left = 0.25
            hoja.page_margins.right = 0.25
            hoja.page_margins.top = 0.40
            hoja.page_margins.bottom = 0.40

            hoja.oddFooter.center.text = (
                "IntelliFeet · Inspección Preoperacional"
            )

            hoja.oddFooter.right.text = (
                "Página &P de &N"
            )

        # =========================================================
        # PROPIEDADES DEL ARCHIVO
        # =========================================================

        wb.properties.title = (
            "Reporte de Inspecciones Preoperacionales"
        )

        wb.properties.subject = (
            f"Reporte del periodo {mes:02d}/{anio}"
        )

        wb.properties.creator = "IntelliFeet"

        wb.properties.description = (
            "Reporte generado automáticamente por "
            "el sistema IntelliFeet."
        )

        # =========================================================
        # GUARDAR EXCEL
        # =========================================================

        buffer = BytesIO()

        wb.save(
            buffer
        )

        buffer.seek(0)

        return buffer