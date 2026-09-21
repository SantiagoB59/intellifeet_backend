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

from flask import Blueprint, request, jsonify, send_file

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

        return Inspeccion.query.filter(
            Inspeccion.usuario_id == usuario_id,
            Inspeccion.plantilla_id == plantilla_id,
            db.func.date(Inspeccion.created_at) == hoy,
            Inspeccion.estado != "ANULADA",
        ).first()

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
    def guardar_lectura_final(inspeccion_id, data):

        inspeccion = Inspeccion.query.get(inspeccion_id)

        if not inspeccion:
            raise Exception("La inspección no existe.")

        if inspeccion.estado != "PENDIENTE_CIERRE":
            raise Exception(
                "Debe finalizar el preoperacional antes de registrar la lectura final."
            )

        tipo_medicion = inspeccion.plantilla.tipo_medicion

        if tipo_medicion == "NINGUNO":
            raise Exception(
                "Esta inspección no requiere registrar una lectura final."
            )

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

        # =====================================================
        # GUARDAR LECTURA FINAL EN LA INSPECCIÓN
        # =====================================================

        inspeccion.contador_final = lectura

        if data.get("foto"):
            inspeccion.foto_contador_final = data["foto"]

        # =====================================================
        # ACTUALIZAR HORÓMETRO DE LA MAQUINARIA
        # =====================================================

        if (
            tipo_medicion == "HOROMETRO"
            and inspeccion.maquinaria_id is not None
        ):

            maquinaria = Maquinaria.query.get(
                inspeccion.maquinaria_id
            )

            if maquinaria:

                # Última lectura real registrada
                maquinaria.horometro_actual = lectura

                # =================================================
                # GUARDAR HISTORIAL DE LECTURA
                # =================================================

                registro_horas = MaquinariaHoras(
                    maquinaria_id=maquinaria.id,
                    horas=lectura,
                    origen="PREOPERACIONAL"
                )

                db.session.add(registro_horas)

        # =====================================================
        # CERRAR INSPECCIÓN
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
            Inspeccion.hora_inicio < fin_dia
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

        inspeccion = InspeccionService.obtener_inspeccion(inspeccion_id)

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=25,
            leftMargin=25,
            topMargin=25,
            bottomMargin=25,
        )

        estilos = getSampleStyleSheet()

        titulo = ParagraphStyle(
            "Titulo",
            parent=estilos["Heading1"],
            fontSize=18,
            alignment=1,
            spaceAfter=15,
        )

        subtitulo = ParagraphStyle(
            "Subtitulo",
            parent=estilos["Heading2"],
            fontSize=12,
            textColor=colors.darkblue,
            spaceBefore=12,
            spaceAfter=8,
        )

        normal = estilos["BodyText"]

        elementos = []

        # ==========================================
        # LOGO
        # ==========================================

        logo = "static/intellifeet.png"

        if os.path.exists(logo):

            img = RLImage(logo, width=140, height=70)

            img.hAlign = "CENTER"

            elementos.append(img)

        elementos.append(Paragraph("FORMATO DE INSPECCIÓN PREOPERACIONAL", titulo))

        elementos.append(Spacer(1, 15))

        # ==========================================
        # INFORMACIÓN GENERAL
        # ==========================================

        activo = ""

        if inspeccion.vehiculo:

            activo = inspeccion.vehiculo.placa

        elif inspeccion.maquinaria:

            activo = inspeccion.maquinaria.codigo

        datos = [
            ["Operador", inspeccion.usuario.nombre],
            ["Activo", activo],
            ["Plantilla", inspeccion.plantilla.nombre],
            ["Estado", inspeccion.estado],
            ["Inicio", inspeccion.hora_inicio.strftime("%d/%m/%Y %H:%M")],
            [
                "Fin",
                (
                    inspeccion.hora_fin.strftime("%d/%m/%Y %H:%M")
                    if inspeccion.hora_fin
                    else ""
                ),
            ],
        ]

        tabla = Table(datos, colWidths=[120, 320])

        tabla.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1F4E78")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("BACKGROUND", (1, 0), (1, -1), colors.whitesmoke),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )

        elementos.append(tabla)

        elementos.append(Spacer(1, 20))

        # ==========================================
        # RESPUESTAS
        # ==========================================

        for categoria in inspeccion.plantilla.categorias:

            elementos.append(Paragraph(categoria.nombre, subtitulo))

            filas = [["Pregunta", "Respuesta", "Observación"]]

            respuestas = {r.item_id: r for r in inspeccion.respuestas}

            for item in categoria.items:

                r = respuestas.get(item.id)

                filas.append(
                    [item.descripcion, r.valor if r else "", r.observacion if r else ""]
                )

            tabla = Table(filas, colWidths=[240, 70, 170])

            tabla.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
                    ]
                )
            )

            elementos.append(tabla)

            elementos.append(Spacer(1, 10))

        # ==========================================
        # ANOMALÍAS
        # ==========================================

        if inspeccion.anomalias:

            elementos.append(Paragraph("Anomalías reportadas", subtitulo))

            filas = [["Título", "Descripción", "Prioridad"]]

            for a in inspeccion.anomalias:

                filas.append([a.titulo, a.descripcion, a.prioridad])

            tabla = Table(filas, colWidths=[150, 250, 90])

            tabla.setStyle(
                TableStyle(
                    [
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("BACKGROUND", (0, 0), (-1, 0), colors.red),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ]
                )
            )

            elementos.append(tabla)

        # ==========================================
        # GENERAR PDF
        # ==========================================

        doc.build(elementos)

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

        inspecciones = InspeccionService.obtener_reporte_preoperacionales(
            mes, anio, vehiculo_id, maquinaria_id
        )

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20,
            leftMargin=20,
            topMargin=20,
            bottomMargin=20,
        )

        estilos = getSampleStyleSheet()

        elementos = []

        logo = "static/intellifeet.png"

        if os.path.exists(logo):

            img = RLImage(logo, width=140, height=70)

            img.hAlign = "CENTER"

            elementos.append(img)

        elementos.append(
            Paragraph(
                "<b>REPORTE DE INSPECCIONES PREOPERACIONALES</b>", estilos["Heading1"]
            )
        )

        elementos.append(Paragraph(f"Periodo: {mes}/{anio}", estilos["Normal"]))

        elementos.append(Spacer(1, 15))

        filas = [["Fecha", "Vehículo", "Operador", "Estado", "Anomalías"]]

        total_anomalias = 0

        for i in inspecciones:

            cantidad = len(i.anomalias)

            total_anomalias += cantidad

            activo = ""

            if i.vehiculo:
                activo = i.vehiculo.placa

            elif i.maquinaria:
                activo = i.maquinaria.codigo

            filas.append(
                [
                    i.hora_inicio.strftime("%d/%m/%Y"),
                    activo,
                    i.usuario.nombre,
                    i.estado,
                    str(cantidad),
                ]
            )

        tabla = Table(filas, colWidths=[70, 90, 150, 80, 80])

        tabla.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
                ]
            )
        )

        elementos.append(tabla)

        elementos.append(Spacer(1, 20))

        resumen = [
            ["Total inspecciones", str(len(inspecciones))],
            ["Total anomalías", str(total_anomalias)],
        ]

        tabla2 = Table(resumen, colWidths=[200, 80])

        tabla2.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#1F4E78")),
                    ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ]
            )
        )

        elementos.append(tabla2)

        doc.build(elementos)

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

        # weekday():
        # lunes = 0
        # domingo = 6

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
                vehiculo_id=vehiculo_id
            )
        )

        # =========================================================
        # IMPORTANTE
        # =========================================================
        #
        # NO hacemos:
        #
        # if not inspecciones:
        #     raise Exception(...)
        #
        # Porque una semana puede estar iniciando
        # y todavía no tener inspecciones.
        #
        # En ese caso queremos mostrar la plantilla
        # con los días vacíos.
        #
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

        encabezado = Table(

            [[

                img,

                Paragraph(

                    "<b>INSPECCIÓN PRE-OPERACIONAL</b><br/>"
                    f"<b>VEHÍCULO: "
                    f"{nombre_vehiculo}</b>",

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
                        else "<b>ESTADO:</b> SEMANA CERRADA"
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
        # CONSTRUIR TABLA
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

                    # =================================================
                    # FUTURO
                    # =================================================

                    if fecha > hoy:

                        marca = ""

                    # =================================================
                    # SIN INSPECCIÓN
                    # =================================================

                    elif valor is None:

                        marca = ""

                    # =================================================
                    # CON RESPUESTA
                    # =================================================

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
        # ANCHOS
        # =========================================================

        cantidad_dias = 7

        ancho_total = 780

        ancho_item = 430

        ancho_dia = (

            ancho_total
            - ancho_item

        ) / cantidad_dias

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
        # ESTILOS
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

        for indice_dia, fecha in enumerate(
            dias_semana,
            start=1
        ):

            if fecha > hoy:

                estilos_tabla.append(

                    (
                        "BACKGROUND",
                        (indice_dia, 1),
                        (indice_dia, -1),
                        GRIS_FUTURO,
                    )

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

        # =========================================================
        # KILOMETRAJE
        # =========================================================

        inspecciones_semana = [

            i
            for i in inspecciones

            if (
                inicio_semana
                <= i.hora_inicio.date()
                <= fin_semana
            )

        ]

        inspecciones_semana.sort(
            key=lambda x: x.hora_inicio
        )

        primera_inspeccion = (
            inspecciones_semana[0]
            if inspecciones_semana
            else None
        )

        ultima_inspeccion = (
            inspecciones_semana[-1]
            if inspecciones_semana
            else None
        )

        kilometraje_inicial = (

            primera_inspeccion.contador_inicial

            if primera_inspeccion

            and primera_inspeccion.contador_inicial
            is not None

            else ""

        )

        kilometraje_final = (

            ultima_inspeccion.contador_final

            if ultima_inspeccion

            and ultima_inspeccion.contador_final
            is not None

            else ""

        )

        kilometraje = Table(

            [[

                Paragraph(
                    "<b>KILOMETRAJE INICIAL</b>",
                    estilo_header
                ),

                str(
                    kilometraje_inicial
                ),

                Paragraph(
                    "<b>KILOMETRAJE FINAL</b>",
                    estilo_header
                ),

                str(
                    kilometraje_final
                ),

            ]],

            colWidths=[

                150,
                220,
                150,
                180,

            ],

        )

        kilometraje.setStyle(

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
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER",
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
            kilometraje
        )

        elementos.append(
            Spacer(1, 5)
        )

        # =========================================================
        # OBSERVACIONES
        # =========================================================

        observaciones_texto = []

        for inspeccion in inspecciones_semana:

            if inspeccion.observaciones_generales:

                observaciones_texto.append(

                    f"{inspeccion.hora_inicio.strftime('%d/%m')} - "
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
                700
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
        # FIRMA
        # =========================================================

        firma = Table(

            [[

                Paragraph(
                    "<b>FIRMA DIARIA "
                    "CONDUCTOR / OPERADOR</b>",
                    estilo_header
                ),

                "",

                Paragraph(
                    "<b>FUERA DE SERVICIO</b>",
                    estilo_header
                ),

                "SI ______  NO ______",

            ]],

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

            ])

        )

        elementos.append(
            firma
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

        # =====================================================
        # IMPORTACIONES
        # =====================================================

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

        # =====================================================
        # CREACIÓN EXCEL
        # =====================================================

        wb = Workbook()

        ws = wb.active
        ws.title = "R. PREOPERACIONAL"

        ws.sheet_view.showGridLines = False

        # =====================================================
        # COLORES
        # =====================================================

        azul_oscuro = PatternFill(
            "solid",
            fgColor="1F4E78"
        )

        azul_claro = PatternFill(
            "solid",
            fgColor="D9EAF7"
        )

        azul_header = PatternFill(
            "solid",
            fgColor="8DB4E2"
        )

        azul_muy_claro = PatternFill(
            "solid",
            fgColor="EAF3F8"
        )

        gris = PatternFill(
            "solid",
            fgColor="F2F2F2"
        )

        verde = PatternFill(
            "solid",
            fgColor="C6EFCE"
        )

        rojo = PatternFill(
            "solid",
            fgColor="FFC7CE"
        )

        amarillo = PatternFill(
            "solid",
            fgColor="FFEB9C"
        )

        blanco = PatternFill(
            "solid",
            fgColor="FFFFFF"
        )

        # =====================================================
        # BORDES
        # =====================================================

        thin = Side(
            border_style="thin",
            color="BFBFBF"
        )

        border = Border(
            left=thin,
            right=thin,
            top=thin,
            bottom=thin
        )

        # =====================================================
        # ALINEACIONES
        # =====================================================

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

        # =====================================================
        # FUENTES
        # =====================================================

        titulo_font = Font(
            bold=True,
            color="FFFFFF",
            size=14
        )

        subtitulo_font = Font(
            bold=True,
            color="FFFFFF",
            size=11
        )

        bold = Font(
            bold=True,
            size=10,
            color="1F1F1F"
        )

        normal = Font(
            size=10,
            color="333333"
        )

        white_bold = Font(
            bold=True,
            size=10,
            color="FFFFFF"
        )

        # =====================================================
        # ANCHO COLUMNAS
        # =====================================================

        columnas = {
            "A": 15,
            "B": 12,
            "C": 28,
            "D": 20,
            "E": 18,
            "F": 18,
            "G": 18,
            "H": 18,
            "I": 18,
            "J": 15,
            "K": 15,
            "L": 25,
        }

        for col, ancho in columnas.items():
            ws.column_dimensions[col].width = ancho

        # =====================================================
        # ALTURA FILAS
        # =====================================================

        for fila in range(1, 80):
            ws.row_dimensions[fila].height = 28

        ws.row_dimensions[1].height = 35
        ws.row_dimensions[2].height = 30
        ws.row_dimensions[3].height = 30

        # =====================================================
        # ENCABEZADO CORPORATIVO
        # =====================================================

        ws.merge_cells("A1:B3")

        for row in ws["A1:B3"]:
            for cell in row:
                cell.fill = azul_oscuro
                cell.border = border

        ruta_logo = "static/intellifeet.png"

        if os.path.exists(ruta_logo):

            logo = Image(ruta_logo)

            logo.width = 260
            logo.height = 128

            ws.add_image(
                logo,
                "A1"
            )

        # =====================================================
        # TITULO
        # =====================================================

        ws.merge_cells("C1:G2")

        ws["C1"] = (
            "INTELLIFEET\n"
            "GESTIÓN DE SEGURIDAD OPERACIONAL"
        )

        ws["C1"].fill = azul_oscuro
        ws["C1"].font = titulo_font
        ws["C1"].alignment = center
        ws["C1"].border = border

        # =====================================================
        # NOMBRE REPORTE
        # =====================================================

        ws.merge_cells("C3:G3")

        ws["C3"] = (
            "REPORTE DE INSPECCIONES PREOPERACIONALES"
        )

        ws["C3"].fill = azul_claro
        ws["C3"].font = Font(
            bold=True,
            size=12,
            color="1F1F1F"
        )

        ws["C3"].alignment = center
        ws["C3"].border = border

        # =====================================================
        # INFORMACIÓN DOCUMENTO
        # =====================================================

        info_documento = [
            ("H1:I1", "VERSIÓN: 001"),
            ("H2:I2", "CÓDIGO: PRE-R-001"),
            ("H3:I3", "PÁGINA: 1 DE 1"),
        ]

        for rango, texto in info_documento:

            ws.merge_cells(rango)

            celda = rango.split(":")[0]

            ws[celda] = texto
            ws[celda].fill = azul_oscuro
            ws[celda].font = white_bold
            ws[celda].alignment = center
            ws[celda].border = border

        # =====================================================
        # INFORMACIÓN GENERAL
        # =====================================================

        ws.merge_cells("A5:L5")

        ws["A5"] = "INFORMACIÓN GENERAL DEL ACTIVO"

        ws["A5"].fill = azul_oscuro
        ws["A5"].font = subtitulo_font
        ws["A5"].alignment = center
        ws["A5"].border = border

        primera = inspecciones[0]

        activo = (
            primera.vehiculo
            if primera.vehiculo
            else primera.maquinaria
        )

        operador = primera.usuario

        # =====================================================
        # TIPO ACTIVO
        # =====================================================

        if primera.vehiculo:

            tipo_activo = "VEHÍCULO"

            tipo_vehiculo = ""

            if primera.vehiculo.tipo_vehiculo:
                tipo_vehiculo = (
                    primera.vehiculo.tipo_vehiculo.nombre
                )

            identificador = (
                primera.vehiculo.placa or ""
            )

        else:

            tipo_activo = "MAQUINARIA"

            tipo_vehiculo = ""

            if primera.maquinaria.tipo_maquinaria:
                tipo_vehiculo = (
                    primera.maquinaria.tipo_maquinaria.nombre
                )

            identificador = (
                primera.maquinaria.codigo or ""
            )

        marca = getattr(
            activo,
            "marca",
            ""
        ) or ""

        modelo = getattr(
            activo,
            "modelo",
            ""
        ) or ""

        nombre_operador = (
            operador.nombre
            if operador
            else ""
        )

        datos_vehiculo = [

            ("TIPO DE ACTIVO", tipo_activo),

            (
                "CLASE / TIPO",
                tipo_vehiculo
            ),

            (
                "PLACA / CÓDIGO",
                str(identificador)
            ),

            (
                "MARCA",
                str(marca)
            ),

            (
                "MODELO",
                str(modelo)
            ),

            (
                "OPERADOR",
                str(nombre_operador)
            ),

            (
                "PERIODO",
                f"{mes:02d}/{anio}"
            ),
        ]

        posiciones = [

            ("A7:B7", "C7:E7"),

            ("F7:G7", "H7:L7"),

            ("A9:B9", "C9:E9"),

            ("F9:G9", "H9:L9"),

            ("A11:B11", "C11:E11"),

            ("F11:G11", "H11:L11"),

        ]

        # Solo utilizamos las primeras 6 posiciones
        for i, posicion in enumerate(posiciones):

            etiqueta = datos_vehiculo[i][0]
            valor = datos_vehiculo[i][1]

            label_pos = posicion[0]
            value_pos = posicion[1]

            # -------------------------
            # ETIQUETA
            # -------------------------

            ws.merge_cells(label_pos)

            celda = label_pos.split(":")[0]

            ws[celda] = etiqueta
            ws[celda].fill = azul_claro
            ws[celda].font = bold
            ws[celda].alignment = center
            ws[celda].border = border

            # -------------------------
            # VALOR
            # -------------------------

            ws.merge_cells(value_pos)

            celda_valor = value_pos.split(":")[0]

            ws[celda_valor] = valor
            ws[celda_valor].fill = gris
            ws[celda_valor].font = normal
            ws[celda_valor].alignment = center
            ws[celda_valor].border = border

        # =====================================================
        # RESUMEN ESTADÍSTICO
        # =====================================================

        total_inspecciones = len(
            inspecciones
        )

        total_anomalias = sum(
            len(i.anomalias)
            for i in inspecciones
        )

        aprobadas = len([
            i
            for i in inspecciones
            if (i.estado or "").upper()
            in ["APROBADO", "APROBADA"]
        ])

        rechazadas = (
            total_inspecciones
            - aprobadas
        )

        cumplimiento = 0

        if total_inspecciones > 0:

            cumplimiento = round(
                (
                    aprobadas
                    / total_inspecciones
                ) * 100,
                2
            )

        ws.merge_cells("A14:L14")

        ws["A14"] = (
            "RESUMEN ESTADÍSTICO DEL PERIODO"
        )

        ws["A14"].fill = azul_oscuro
        ws["A14"].font = subtitulo_font
        ws["A14"].alignment = center
        ws["A14"].border = border

        indicadores = [

            (
                "TOTAL INSPECCIONES",
                total_inspecciones
            ),

            (
                "APROBADAS",
                aprobadas
            ),

            (
                "RECHAZADAS",
                rechazadas
            ),

            (
                "ANOMALÍAS",
                total_anomalias
            ),

            (
                "CUMPLIMIENTO",
                f"{cumplimiento}%"
            ),

        ]

        columnas_indicador = [

            ("A15:B16"),
            ("C15:D16"),
            ("E15:F16"),
            ("G15:H16"),
            ("I15:L16"),

        ]

        for index, rango in enumerate(
            columnas_indicador
        ):

            ws.merge_cells(rango)

            celda = rango.split(":")[0]

            ws[celda] = (
                indicadores[index][0]
                + "\n\n"
                + str(indicadores[index][1])
            )

            ws[celda].fill = azul_claro
            ws[celda].font = Font(
                bold=True,
                size=11
            )

            ws[celda].alignment = center
            ws[celda].border = border

        # =====================================================
        # HISTORIAL
        # =====================================================

        historial = wb.create_sheet(
            "Historial"
        )

        historial.sheet_view.showGridLines = False

        columnas_historial = {

            "A": 15,
            "B": 10,
            "C": 18,
            "D": 12,
            "E": 25,
            "F": 45,
            "G": 18,
            "H": 18,

        }

        for col, ancho in columnas_historial.items():

            historial.column_dimensions[
                col
            ].width = ancho

        historial.merge_cells("A1:H1")

        historial["A1"] = (
            "HISTORIAL DE INSPECCIONES PREOPERACIONALES"
        )

        historial["A1"].fill = azul_oscuro
        historial["A1"].font = titulo_font
        historial["A1"].alignment = center
        historial["A1"].border = border

        headers_historial = [

            "FECHA",
            "HORA",
            "ESTADO",
            "ANOMALÍAS",
            "OPERADOR",
            "OBSERVACIÓN GENERAL",
            "LECTURA INICIAL",
            "LECTURA FINAL",

        ]

        for col, titulo_col in enumerate(
            headers_historial,
            1
        ):

            celda = historial.cell(
                3,
                col
            )

            celda.value = titulo_col
            celda.fill = azul_header
            celda.font = bold
            celda.alignment = center
            celda.border = border

        fila = 4

        for inspeccion in inspecciones:

            historial.cell(
                fila,
                1
            ).value = inspeccion.hora_inicio.strftime(
                "%d/%m/%Y"
            )

            historial.cell(
                fila,
                2
            ).value = inspeccion.hora_inicio.strftime(
                "%H:%M"
            )

            estado = (
                inspeccion.estado
                or ""
            )

            celda_estado = historial.cell(
                fila,
                3
            )

            celda_estado.value = estado

            if estado.upper() in [
                "APROBADO",
                "APROBADA"
            ]:

                celda_estado.fill = verde

            elif estado.upper() in [
                "FINALIZADA",
                "REVISADA"
            ]:

                celda_estado.fill = amarillo

            else:

                celda_estado.fill = rojo

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

            historial.cell(
                fila,
                7
            ).value = (
                float(inspeccion.contador_inicial)
                if inspeccion.contador_inicial is not None
                else ""
            )

            historial.cell(
                fila,
                8
            ).value = (
                float(inspeccion.contador_final)
                if inspeccion.contador_final is not None
                else ""
            )

            for col in range(
                1,
                9
            ):

                celda = historial.cell(
                    fila,
                    col
                )

                celda.border = border
                celda.alignment = center
                celda.font = normal

            fila += 1

        historial.freeze_panes = "A4"

        historial.auto_filter.ref = (
            historial.dimensions
        )

        # =====================================================
        # DETALLE DE CADA INSPECCIÓN
        # =====================================================

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

            # =================================================
            # COLUMNAS
            # =================================================

            columnas_detalle = {

                "A": 25,
                "B": 45,
                "C": 18,
                "D": 40,
                "E": 28,

            }

            for col, ancho in columnas_detalle.items():

                hoja.column_dimensions[
                    col
                ].width = ancho

            # =================================================
            # TITULO
            # =================================================

            hoja.merge_cells("A1:E1")

            hoja["A1"] = (
                f"DETALLE INSPECCIÓN #{indice}"
            )

            hoja["A1"].fill = azul_oscuro
            hoja["A1"].font = titulo_font
            hoja["A1"].alignment = center
            hoja["A1"].border = border

            # =================================================
            # INFORMACIÓN
            # =================================================

            if inspeccion.vehiculo:

                identificador = (
                    inspeccion.vehiculo.placa
                )

                tipo_activo = "VEHÍCULO"

            else:

                identificador = (
                    inspeccion.maquinaria.codigo
                    if inspeccion.maquinaria
                    else ""
                )

                tipo_activo = "MAQUINARIA"

            datos = [

                (
                    "FECHA",
                    inspeccion.hora_inicio.strftime(
                        "%d/%m/%Y %H:%M"
                    )
                ),

                (
                    "ESTADO",
                    inspeccion.estado
                ),

                (
                    "TIPO ACTIVO",
                    tipo_activo
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

            fila = 3

            for campo, valor in datos:

                hoja[f"A{fila}"] = campo
                hoja[f"B{fila}"] = valor

                hoja[f"A{fila}"].fill = azul_claro
                hoja[f"A{fila}"].font = bold
                hoja[f"A{fila}"].border = border

                hoja[f"B{fila}"].border = border
                hoja[f"B{fila}"].alignment = left

                fila += 1

            # =================================================
            # OBSERVACIONES GENERALES
            # =================================================

            fila += 1

            hoja.merge_cells(
                start_row=fila,
                start_column=1,
                end_row=fila,
                end_column=5
            )

            hoja.cell(
                fila,
                1
            ).value = "OBSERVACIONES GENERALES"

            hoja.cell(
                fila,
                1
            ).fill = azul_header

            hoja.cell(
                fila,
                1
            ).font = bold

            hoja.cell(
                fila,
                1
            ).alignment = center

            hoja.cell(
                fila,
                1
            ).border = border

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
                or ""
            )

            hoja.cell(
                fila,
                1
            ).alignment = left

            hoja.cell(
                fila,
                1
            ).border = border

            fila += 4

            # =================================================
            # RESPUESTAS
            # =================================================

            headers = [

                "CATEGORÍA",
                "PREGUNTA",
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
                celda.fill = azul_header
                celda.font = bold
                celda.alignment = center
                celda.border = border

            fila += 1

            # =================================================
            # ORDENAR RESPUESTAS
            # =================================================

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

            # =================================================
            # RESPUESTAS
            # =================================================

            for respuesta in respuestas_ordenadas:

                item = respuesta.item

                if not item:
                    continue

                categoria = (
                    item.categoria
                    if item.categoria
                    else None
                )

                nombre_categoria = (
                    categoria.nombre
                    if categoria
                    else ""
                )

                pregunta = (
                    item.descripcion
                    or ""
                )

                valor = (
                    respuesta.valor
                    or ""
                )

                observacion = (
                    respuesta.observacion
                    or ""
                )

                # ---------------------------------------------
                # ESCRIBIR DATOS
                # ---------------------------------------------

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

                # ---------------------------------------------
                # ESTILO RESPUESTA
                # ---------------------------------------------

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

                hoja.cell(
                    fila,
                    3
                ).alignment = center

                # ---------------------------------------------
                # COLOR RESPUESTA
                # ---------------------------------------------

                valor_normalizado = (
                    str(valor)
                    .strip()
                    .upper()
                )

                if valor_normalizado in [
                    "SI",
                    "SÍ",
                    "OK",
                    "CUMPLE",
                    "BUENO",
                    "1",
                    "TRUE"
                ]:

                    hoja.cell(
                        fila,
                        3
                    ).fill = verde

                elif valor_normalizado in [
                    "NO",
                    "NO CUMPLE",
                    "MALO",
                    "0",
                    "FALSE"
                ]:

                    hoja.cell(
                        fila,
                        3
                    ).fill = rojo

                elif valor_normalizado in [
                    "N/A",
                    "NA",
                    "NO APLICA"
                ]:

                    hoja.cell(
                        fila,
                        3
                    ).fill = amarillo

                # =================================================
                # FOTOS
                # =================================================

                fotos = (
                    respuesta.fotos
                    if respuesta.fotos
                    else []
                )

                if fotos:

                    nombres_fotos = []

                    for foto in fotos:

                        archivo = (
                            foto.archivo
                            or ""
                        )

                        if not archivo:
                            continue

                        # -------------------------------------
                        # BUSCAR ARCHIVO
                        # -------------------------------------

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

                        # -------------------------------------
                        # INSERTAR FOTO
                        # -------------------------------------

                        if ruta_foto:

                            try:

                                imagen = Image(
                                    ruta_foto
                                )

                                # Tamaño de miniatura
                                imagen.width = 150
                                imagen.height = 110

                                hoja.add_image(
                                    imagen,
                                    f"E{fila}"
                                )

                                # Si hay varias imágenes,
                                # se colocan debajo
                                # aumentando la altura.

                                hoja.row_dimensions[
                                    fila
                                ].height = 90

                            except Exception as error:

                                nombres_fotos.append(
                                    f"Error imagen: {error}"
                                )

                        else:

                            nombres_fotos.append(
                                os.path.basename(
                                    archivo
                                )
                            )

                    # -----------------------------------------
                    # SI NO SE PUDO INSERTAR
                    # -----------------------------------------

                    if nombres_fotos:

                        hoja.cell(
                            fila,
                            5
                        ).value = "\n".join(
                            nombres_fotos
                        )

                        hoja.cell(
                            fila,
                            5
                        ).alignment = left

                else:

                    hoja.cell(
                        fila,
                        5
                    ).value = "SIN EVIDENCIA"

                    hoja.cell(
                        fila,
                        5
                    ).alignment = center

                fila += 1

            # =================================================
            # ANOMALÍAS
            # =================================================

            if inspeccion.anomalias:

                fila += 2

                hoja.merge_cells(
                    start_row=fila,
                    start_column=1,
                    end_row=fila,
                    end_column=5
                )

                hoja.cell(
                    fila,
                    1
                ).value = "ANOMALÍAS REPORTADAS"

                hoja.cell(
                    fila,
                    1
                ).fill = rojo

                hoja.cell(
                    fila,
                    1
                ).font = bold

                hoja.cell(
                    fila,
                    1
                ).alignment = center

                hoja.cell(
                    fila,
                    1
                ).border = border

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
                    celda.fill = azul_header
                    celda.font = bold
                    celda.alignment = center
                    celda.border = border

                fila += 1

                for anomalia in inspeccion.anomalias:

                    hoja.cell(
                        fila,
                        1
                    ).value = (
                        anomalia.titulo
                        or ""
                    )

                    hoja.cell(
                        fila,
                        2
                    ).value = (
                        anomalia.descripcion
                        or ""
                    )

                    hoja.cell(
                        fila,
                        3
                    ).value = (
                        getattr(
                            anomalia,
                            "prioridad",
                            ""
                        )
                        or ""
                    )

                    hoja.cell(
                        fila,
                        4
                    ).value = (
                        getattr(
                            anomalia,
                            "estado",
                            ""
                        )
                        or ""
                    )

                    fecha_anomalia = getattr(
                        anomalia,
                        "created_at",
                        None
                    )

                    if fecha_anomalia:

                        hoja.cell(
                            fila,
                            5
                        ).value = (
                            fecha_anomalia.strftime(
                                "%d/%m/%Y %H:%M"
                            )
                        )

                    for col in range(
                        1,
                        6
                    ):

                        hoja.cell(
                            fila,
                            col
                        ).border = border

                        hoja.cell(
                            fila,
                            col
                        ).alignment = left

                    fila += 1

            # =================================================
            # CONGELAR ENCABEZADOS
            # =================================================

            hoja.freeze_panes = "A15"

        # =====================================================
        # HOJA PRINCIPAL
        # =====================================================

        ws.freeze_panes = "A5"

        # =====================================================
        # GUARDAR
        # =====================================================

        buffer = BytesIO()

        wb.save(buffer)

        buffer.seek(0)

        return buffer