from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import datetime
from zoneinfo import ZoneInfo

from decimal import Decimal

# from models.alerta import Alerta
# ==========================
# ROLES
# ==========================
class Rol(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)

    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre}


# ==========================
# USUARIOS
# ==========================
class Usuario(db.Model):
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)

    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True)

    password_hash = db.Column(db.String(255), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    rol = db.relationship('Rol', backref='usuarios')

    telefono = db.Column(db.String(20))
    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "username": self.username,
            "email": self.email,
            "rol": self.rol.nombre if self.rol else None,
            "activo": self.activo,
            "created_at": str(self.created_at)
        }


# ==========================
# TIPOS VEHICULO
# ==========================
class TipoVehiculo(db.Model):
    __tablename__ = "tipos_vehiculo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True)
    codigo = db.Column(db.String(20))
    es_automotor = db.Column(db.Boolean, nullable=False, default=True)
    def to_dict(self):
        return {"id": self.id, "nombre": self.nombre}


# ==========================
# VEHICULOS

class Vehiculo(db.Model):
    __tablename__ = "vehiculos"

    id = db.Column(db.Integer, primary_key=True)

    placa = db.Column(
        db.String(10),
        unique=True,
        nullable=False
    )

    # ==========================
    # 🚘 TIPO
    # ==========================
    tipo_vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('tipos_vehiculo.id')
    )

    tipo_vehiculo = db.relationship(
        'TipoVehiculo'
    )

    # ==========================
    # 🚗 INFORMACIÓN GENERAL
    # ==========================
    marca = db.Column(db.String(50))
    linea = db.Column(db.String(50))
    modelo = db.Column(db.String(50))
    color = db.Column(db.String(30))

    vin = db.Column(db.String(50))
    numero_chasis = db.Column(db.String(50))
    numero_motor = db.Column(db.String(50))

    # ==========================
    # 👤 PROPIETARIO
    # ==========================
    propietario = db.Column(db.String(100))
    cc_propietario = db.Column(db.String(50))

    # ==========================
    # 👨‍✈️ CONDUCTOR BASE
    # (Opcional)
    # ==========================
    conductor = db.Column(db.String(100))
    cc_conductor = db.Column(db.String(20))

    # ==========================
    # 🚚 OPERACIÓN
    # ==========================
    servicio = db.Column(db.String(20))

    km_actual = db.Column(
        db.Integer,
        default=0
    )

    km_gps = db.Column(
        db.Float,
        default=0
    )

    gps_id = db.Column(db.String(50))

    estado = db.Column(
        db.String(20),
        default="OPERATIVO"
    )

    # ==========================
    # 🖼️ OTROS
    # ==========================
    foto_url = db.Column(db.String(255))

    notas = db.Column(db.Text)

    activo = db.Column(
        db.Boolean,
        default=True
    )

    # ==========================
    # 📅 FECHAS
    # ==========================
    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime,
        onupdate=db.func.now()
    )
    km_gps_inicial = db.Column(
        db.Float,
        nullable=True
    )

    km_base_control = db.Column(
        db.Integer,
        nullable=True
    )
    requiere_verificacion_km = db.Column(
        db.Boolean,
        default=False
    )

    fecha_proxima_verificacion = db.Column(
        db.Date
    )
    ultima_verificacion_km = db.Column(
        db.Date,
        nullable=True
    )

    # ==========================
    # 📄 DOCUMENTOS
    # ==========================
    documentos = db.relationship(
        'VehiculoDocumento',
        backref='vehiculo',
        lazy=True
    )
    
    # ==========================
    # 📋 INSPECCIONES MENSUALES
    # =========================
    inspecciones = db.relationship(
        'InspeccionMensual',
        backref='vehiculo',
        lazy=True,
        cascade='all, delete-orphan'
    )
    # Inspecciones preoperacionales
    inspecciones_preoperacionales = db.relationship(
        "Inspeccion",
        back_populates="vehiculo",
        lazy=True
    )

    # ==========================
    # 🚗 KM TOTAL
    # ==========================
    @property
    def km_estimado(self):
        """
        Kilometraje estimado actual del vehículo
        usando el avance del GPS desde la
        parametrización.
        """

        if self.km_gps is None:
            return self.km_actual or 0

        if self.km_gps_inicial is None:
            return self.km_actual or 0

        if self.km_base_control is None:
            return self.km_actual or 0

        recorrido = self.km_gps - self.km_gps_inicial

        return int(
            self.km_base_control +
            recorrido
        )


    @property
    def km_total(self):
        """
        Compatibilidad con el código actual.
        """
        return self.km_estimado

    def to_dict(self):

        return {

            # ==========================
            # 🔑 BÁSICO
            # ==========================
            "id": self.id,
            "placa": self.placa,

            # ==========================
            # 🚘 TIPO
            # ==========================
            "tipo_vehiculo_id":
                self.tipo_vehiculo_id,

            "tipo_vehiculo":
                self.tipo_vehiculo.nombre
                if self.tipo_vehiculo else None,

            # ==========================
            # 🚗 GENERAL
            # ==========================
            "marca": self.marca,
            "linea": self.linea,
            "modelo": self.modelo,
            "color": self.color,

            "vin": self.vin,
            "numero_chasis": self.numero_chasis,
            "numero_motor": self.numero_motor,

            # ==========================
            # 👤 PROPIETARIO
            # ==========================
            "propietario": self.propietario,
            "cc_propietario": self.cc_propietario,

            # ==========================
            # 👨‍✈️ CONDUCTOR
            # ==========================
            "conductor": self.conductor,
            "cc_conductor": self.cc_conductor,

            # ==========================
            # 🚚 OPERACIÓN
            # ==========================
            "servicio": self.servicio,

            "km_actual":
                self.km_actual or 0,

            "km_gps":
                self.km_gps or 0,
            
            "km_gps_inicial":
                self.km_gps_inicial,

            "km_base_control":
                self.km_base_control,

            "km_estimado":
                self.km_estimado,

            "km_total":
                self.km_total,
            
            "requiere_verificacion_km": self.requiere_verificacion_km,

            "fecha_proxima_verificacion": (
                str(self.fecha_proxima_verificacion)
                if self.fecha_proxima_verificacion
                else None
            ),
            "ultima_verificacion_km": (
                str(self.ultima_verificacion_km)
                if self.ultima_verificacion_km
                else None
            ),

            "gps_id": self.gps_id,

            "estado": self.estado,

            # ==========================
            # 🖼️ OTROS
            # ==========================
            "foto_url": self.foto_url,

            "notas": self.notas,

            "activo": self.activo,

            # ==========================
            # 📅 FECHAS
            # ==========================
            "created_at":
                str(self.created_at)
                if self.created_at else None,

            "updated_at":
                str(self.updated_at)
                if self.updated_at else None,
        }

# DOCUMENTOS TIPO
# ==========================
class DocumentoTipo(db.Model):
    __tablename__ = "documentos_tipo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100))


# ==========================
# VEHICULO DOCUMENTOS
# ==========================
class VehiculoDocumento(db.Model):
    __tablename__ = "vehiculo_documentos"

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'))
    documento_tipo_id = db.Column(db.Integer, db.ForeignKey('documentos_tipo.id'))

    numero = db.Column(db.String(100))
    fecha_expedicion = db.Column(db.Date)
    fecha_vencimiento = db.Column(db.Date)
    archivo_url = db.Column(db.String(255))

    documento_tipo = db.relationship('DocumentoTipo')

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.documento_tipo.nombre if self.documento_tipo else None,
            "numero": self.numero,
            "fecha_expedicion": str(self.fecha_expedicion) if self.fecha_expedicion else None,
            "fecha_vencimiento": str(self.fecha_vencimiento) if self.fecha_vencimiento else None,
            "archivo_url": self.archivo_url
        }


class PlanItem(db.Model):
    __tablename__ = 'plan_items'

    id = db.Column(db.Integer, primary_key=True)

    # ==========================
    # INFORMACIÓN DEL ITEM
    # ==========================
    sistema = db.Column(
        db.String(100),
        nullable=False
    )

    nombre = db.Column(
        db.String(150),
        nullable=False
    )

    descripcion = db.Column(
        db.Text
    )

    # ==========================
    # TIPO DE MANTENIMIENTO
    # ==========================
    tipo_mantenimiento = db.Column(
        db.Enum(
            'PREVENTIVO',
            'INSPECCION',
            'CORRECTIVO'
        ),
        default='PREVENTIVO',
        nullable=False
    )

    # ==========================
    # TIPO DE ACTIVO
    # ==========================
    tipo_activo = db.Column(
        db.Enum(
            'VEHICULO',
            'MAQUINARIA'
        ),
        default='VEHICULO',
        nullable=False
    )

    # ==========================
    # CONTROL DEL MANTENIMIENTO
    # ==========================
    tipo_control = db.Column(
        db.Enum(
            'KM',
            'DIAS',
            'HORAS',
            'OCASIONAL'
        ),
        default='KM',
        nullable=False
    )

    frecuencia_valor = db.Column(
        db.Integer
    )

    alerta_valor = db.Column(
        db.Integer
    )

    # ==========================
    # CONFIGURACIÓN
    # ==========================
    obligatorio = db.Column(
        db.Boolean,
        default=True
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    # ==========================
    # ACTIVIDADES
    # ==========================
    actividades = db.relationship(
        'PlanItemActividad',
        back_populates='plan_item',
        cascade='all, delete-orphan',
        order_by='PlanItemActividad.orden'
    )

    # ==========================
    # SERIALIZACIÓN
    # ==========================
    def to_dict(self):

        return {

            "id": self.id,

            "sistema": self.sistema,

            "nombre": self.nombre,

            "descripcion": self.descripcion,

            "tipo_mantenimiento":
                self.tipo_mantenimiento,

            "tipo_activo":
                self.tipo_activo,

            "tipo_control":
                self.tipo_control,

            "frecuencia_valor":
                self.frecuencia_valor,

            "alerta_valor":
                self.alerta_valor,

            "obligatorio":
                self.obligatorio,

            "activo":
                self.activo,

            "actividades": [
                actividad.to_dict()
                for actividad in self.actividades
                if actividad.activo
            ],

            "created_at": (
                str(self.created_at)
                if self.created_at
                else None
            )
        }

class VehiculoPlanItem(db.Model):
    __tablename__ = 'vehiculo_plan_item'

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id'),
        nullable=False
    )

    plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_items.id'),
        nullable=False
    )

    # ==========================
    # CONFIGURACIÓN
    # ==========================

    tipo_control = db.Column(
        db.Enum('KM', 'DIAS'),
        default='KM'
    )

    frecuencia_valor = db.Column(db.Integer)

    alerta_valor = db.Column(db.Integer)

    # ==========================
    # CONTROL
    # ==========================

    ultimo_km = db.Column(
        db.Integer,
        default=0
    )

    ultima_fecha = db.Column(db.Date)

    activo = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    # ==========================
    # RELACIONES
    # ==========================

    plan_item = db.relationship(
        'PlanItem',
        lazy='joined'
    )

    vehiculo = db.relationship(
        'Vehiculo',
        lazy='joined'
    )

    # ==========================
    # 🔥 KM TOTAL REAL
    # ==========================

    def get_km_total(self):

        if not self.vehiculo:
            return 0

        vehiculo = self.vehiculo

        km_total = (
            vehiculo.km_estimado
            if vehiculo
            else 0
        )

    # Remolques
        if (
            vehiculo.tipo_vehiculo
            and not vehiculo.tipo_vehiculo.es_automotor
        ):

            viajes = Viaje.query.filter(
                Viaje.remolque_id == vehiculo.id
            ).all()

            km_total += sum(
                v.km_recorrido or 0
                for v in viajes
            )

        return km_total

    # ==========================
    # PROGRAMADO
    # ==========================

    def calcular_programado(self):

        if self.tipo_control == 'KM':

            if not self.frecuencia_valor:
                return None

            return (
                (self.ultimo_km or 0)
                + self.frecuencia_valor
            )

        if self.tipo_control == 'DIAS':

            if (
                not self.frecuencia_valor
                or not self.ultima_fecha
            ):
                return None

            from datetime import timedelta

            return self.ultima_fecha + timedelta(
                days=self.frecuencia_valor
            )

        return None

    # ==========================
    # RESTANTE
    # ==========================

    def calcular_restante(self):

        if self.tipo_control == 'KM':

            programado = self.calcular_programado()

            if programado is None:
                return None

            return (
                programado
                - self.get_km_total()
            )

        if self.tipo_control == 'DIAS':

            programado = self.calcular_programado()

            if not programado:
                return None

            from datetime import date

            return (
                programado - date.today()
            ).days

        return None

    # ==========================
    # ESTADO
    # ==========================

    def calcular_estado(self):

        restante = self.calcular_restante()

        if restante is None:
            return "ACTIVO"

        if restante <= 0:
            return "VENCIDO"

        if restante <= (
            self.alerta_valor or 0
        ):
            return "PENDIENTE"

        return "ACTIVO"

    # ==========================
    # SERIALIZACIÓN
    # ==========================

    def to_dict(self):

        programado = self.calcular_programado()

        restante = self.calcular_restante()

        km_total = self.get_km_total()

        return {

            "id": self.id,

            "vehiculo_id": self.vehiculo_id,

            "plan_item_id": self.plan_item_id,

            # ==========================
            # INFO PLAN
            # ==========================

            "sistema": (
                self.plan_item.sistema
                if self.plan_item else None
            ),

            "nombre": (
                self.plan_item.nombre
                if self.plan_item else None
            ),

            "descripcion": (
                self.plan_item.descripcion
                if self.plan_item else None
            ),

            "tipo_mantenimiento": (
                self.plan_item.tipo_mantenimiento
                if self.plan_item else None
            ),

            # ==========================
            # CONFIG
            # ==========================

            "tipo_control": self.tipo_control,

            "frecuencia_valor": self.frecuencia_valor,

            "alerta_valor": self.alerta_valor,

            # ==========================
            # CONTROL
            # ==========================

            "ultimo_km": self.ultimo_km,

            "ultima_fecha": (
                str(self.ultima_fecha)
                if self.ultima_fecha
                else None
            ),

            # ==========================
            # KM
            # ==========================

            "km_base": (
                self.vehiculo.km_actual
                if self.vehiculo else 0
            ),

            "km_gps": (
                getattr(
                    self.vehiculo,
                    "km_gps",
                    0
                )
                if self.vehiculo else 0
            ),

            "km_total": km_total,

            # ==========================
            # PROGRAMACIÓN
            # ==========================

            "programado": (
                str(programado)
                if self.tipo_control == 'DIAS'
                and programado
                else programado
            ),

            "restante": restante,

            # ==========================
            # ESTADO
            # ==========================

            "estado": self.calcular_estado(),

            "activo": self.activo,

            "created_at": (
                str(self.created_at)
                if self.created_at else None
            ),

            # ==========================
            # PLAN COMPLETO
            # ==========================

            "plan_item": (
                self.plan_item.to_dict()
                if self.plan_item else None
            )
        }

# ==========================
# MANTENIMIENTOS
# ==========================
class Mantenimiento(db.Model):
    __tablename__ = 'mantenimientos'

    id = db.Column(db.Integer, primary_key=True)

    # ==========================
    # RELACIONES
    # ==========================
    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id'),
        nullable=False
    )

    plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_items.id')
    )

    vehiculo_plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculo_plan_item.id'),
        nullable=False
    )

    # ==========================
    # DATOS MANTENIMIENTO
    # ==========================
    fecha = db.Column(db.Date, nullable=False)

    km = db.Column(db.Integer, nullable=False)

    tipo = db.Column(db.String(5))

    proveedor = db.Column(db.String(150))

    observaciones = db.Column(db.Text)

    # ==========================
    # NUEVOS CAMPOS
    # ==========================

    # 📸 Foto factura / soporte
    soporte = db.Column(db.String(255))

    # 💰 Valor mantenimiento
    costo = db.Column(db.Float)

    # 📍 Lugar exacto
    lugar = db.Column(db.String(150))

    # 👤 Responsable
    responsable = db.Column(db.String(120))

    # 🔥 SI EL MANTENIMIENTO
    # QUEDA COMPLETADO
    completado = db.Column(
        db.Boolean,
        default=True
    )

    # ==========================
    # FECHAS SISTEMA
    # ==========================
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota")),
        onupdate=datetime.utcnow
    )

    # ==========================
    # RELACIONES
    # ==========================
    vehiculo = db.relationship(
        'Vehiculo',
        lazy='joined'
    )

    plan_item = db.relationship(
        'PlanItem',
        lazy='joined'
    )

    vehiculo_plan_item = db.relationship(
        'VehiculoPlanItem',
        lazy='joined'
    )

    # ==========================
    # SERIALIZER
    # ==========================
    def to_dict(self):

        return {

            "id": self.id,

            # ==========================
            # VEHICULO
            # ==========================
            "vehiculo_id": self.vehiculo_id,

            "vehiculo": (
                {
                    "id": self.vehiculo.id,
                    "placa": self.vehiculo.placa,
                    "marca": self.vehiculo.marca,
                    "modelo": self.vehiculo.modelo
                }
                if self.vehiculo else None
            ),

            # ==========================
            # PLAN
            # ==========================
            "plan_item_id": self.plan_item_id,

            "vehiculo_plan_item_id": self.vehiculo_plan_item_id,

            "plan_item": (
                self.vehiculo_plan_item.plan_item.to_dict()
                if self.vehiculo_plan_item
                and self.vehiculo_plan_item.plan_item
                else None
            ),

            # ==========================
            # DATOS
            # ==========================
            "fecha": (
                str(self.fecha)
                if self.fecha else None
            ),

            "km": self.km,

            "tipo": self.tipo,

            "proveedor": self.proveedor,

            "observaciones": self.observaciones,

            # ==========================
            # NUEVOS
            # ==========================
            "soporte": self.soporte,

            "costo": self.costo,

            "lugar": self.lugar,

            "responsable": self.responsable,

            "completado": self.completado,

            # ==========================
            # FECHAS
            # ==========================
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            ),

            "updated_at": (
                self.updated_at.isoformat()
                if self.updated_at else None
            )
        }

# ==========================
# COMPONENTES VEHICULO
# ==========================

# class VehiculoComponente(db.Model):
#     __tablename__ = "vehiculo_componentes"

#     id = db.Column(db.Integer, primary_key=True)

#     vehiculo_padre_id = db.Column(
#         db.Integer,
#         db.ForeignKey('vehiculos.id'),
#         nullable=False
#     )

#     vehiculo_hijo_id = db.Column(
#         db.Integer,
#         db.ForeignKey('vehiculos.id'),
#         nullable=False
#     )

#     tipo_componente = db.Column(
#         db.String(50)
#     )

#     padre = db.relationship(
#         'Vehiculo',
#         foreign_keys=[vehiculo_padre_id]
#     )

#     hijo = db.relationship(
#         'Vehiculo',
#         foreign_keys=[vehiculo_hijo_id]
#     )

class TipoVehiculoCampo(db.Model):
    __tablename__ = "tipo_vehiculo_campos"

    id = db.Column(db.Integer, primary_key=True)
    tipo_vehiculo_id = db.Column(db.Integer, db.ForeignKey('tipos_vehiculo.id'))
    nombre_campo = db.Column(db.String(100))
    tipo_dato = db.Column(db.String(50))  # date, file, int, string
    requerido = db.Column(db.Boolean, default=False)

    tipo_vehiculo = db.relationship('TipoVehiculo', backref='campos')

class VehiculoCampoValor(db.Model):
    __tablename__ = "vehiculo_campos_valores"

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'))
    campo_id = db.Column(db.Integer, db.ForeignKey('tipo_vehiculo_campos.id'))

    valor = db.Column(db.Text)

    campo = db.relationship('TipoVehiculoCampo')






# ========================== GPS - HISTÓRICO Y TIEMPO REAL



class VehiculoUbicacionActual(db.Model):
    __tablename__ = "vehiculo_ubicacion_actual"

    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'), primary_key=True)

    gps_id = db.Column(db.String(50))

    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    speed = db.Column(db.Integer, default=0)
    ignition = db.Column(db.Boolean, default=False)

    direccion = db.Column(db.String(50))
    ciudad = db.Column(db.String(100))
    direccion_texto = db.Column(db.String(255))

    evento = db.Column(db.String(100))

    fecha_gps = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("America/Bogota")), onupdate=datetime.utcnow)
    
    
class VehiculoTracking(db.Model):
    __tablename__ = "vehiculo_tracking"

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(db.Integer, db.ForeignKey('vehiculos.id'))

    gps_id = db.Column(db.String(50))

    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)

    speed = db.Column(db.Integer)
    ignition = db.Column(db.Boolean)

    direccion = db.Column(db.String(50))
    ciudad = db.Column(db.String(100))

    evento = db.Column(db.String(100))

    fecha_gps = db.Column(db.DateTime)
    odometro = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("America/Bogota")))
    




# ========================== Maquinaria

class TipoMaquinaria(db.Model):
    __tablename__ = "tipos_maquinaria"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), unique=True, nullable=False)


class Maquinaria(db.Model):
    __tablename__ = "maquinaria"

    id = db.Column(db.Integer, primary_key=True)

    codigo = db.Column(db.String(50), unique=True, nullable=False)

    tipo_maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey('tipos_maquinaria.id'),
        nullable=False
    )

    tipo_maquinaria = db.relationship('TipoMaquinaria')

    marca = db.Column(db.String(50))
    modelo = db.Column(db.String(50))

    horometro_actual = db.Column(db.Float, default=0)

    operador = db.Column(db.String(100))
    gps_id = db.Column(db.String(50))
    estado = db.Column(db.String(20), default="OPERATIVA")
    notas = db.Column(db.Text)
    foto_url = db.Column(db.String(255))
    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # INSPECCIONES
    inspecciones = db.relationship(
        'InspeccionMensual',
        backref='maquinaria',
        lazy=True,
        cascade='all, delete-orphan'
    )

    inspecciones_preoperacionales = db.relationship(
        "Inspeccion",
        back_populates="maquinaria",
        lazy=True
    )

    # ==========================================
    # MANTENIMIENTOS PROGRAMADOS
    # ==========================================
    mantenimientos_programados = db.relationship(
        'MaquinariaPlanItem',
        back_populates='maquinaria',
        lazy=True,
        cascade='all, delete-orphan'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "codigo": self.codigo,

            "tipo_maquinaria_id": self.tipo_maquinaria_id,
            "tipo": self.tipo_maquinaria.nombre if self.tipo_maquinaria else None,

            "marca": self.marca,
            "modelo": self.modelo,

            "horometro_actual": self.horometro_actual,

            "operador": self.operador,
            "gps_id": self.gps_id,

            "estado": self.estado,
            "notas": self.notas,

            "foto_url": self.foto_url,
            "activo": self.activo,

            "created_at": str(self.created_at)
        }


class MaquinariaDocumento(db.Model):
    __tablename__ = "maquinaria_documentos"

    id = db.Column(db.Integer, primary_key=True)

    maquinaria_id = db.Column(db.Integer, db.ForeignKey('maquinaria.id'))
    documento_tipo_id = db.Column(db.Integer, db.ForeignKey('documentos_tipo.id'))

    numero = db.Column(db.String(100))
    fecha_expedicion = db.Column(db.Date)
    fecha_vencimiento = db.Column(db.Date)
    archivo_url = db.Column(db.String(255))

    documento_tipo = db.relationship('DocumentoTipo')

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.documento_tipo.nombre if self.documento_tipo else None,
            "numero": self.numero,
            "fecha_expedicion": str(self.fecha_expedicion) if self.fecha_expedicion else None,
            "fecha_vencimiento": str(self.fecha_vencimiento) if self.fecha_vencimiento else None,
            "archivo_url": self.archivo_url
        }

class MaquinariaHoras(db.Model):
    __tablename__ = "maquinaria_horas"

    id = db.Column(db.Integer, primary_key=True)

    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey("maquinaria.id"),
        nullable=False
    )

    horas = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    fecha = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    origen = db.Column(
        db.Enum(
            "MANUAL",
            "MANTENIMIENTO",
            "PREOPERACIONAL"
        ),
        nullable=False,
        default="MANUAL"
    )

    maquinaria = db.relationship(
        "Maquinaria",
        backref=db.backref(
            "historial_horas",
            lazy=True
        )
    )
# ==========================
# MAQUINARIA PLAN ITEM
# ==========================
class MaquinariaPlanItem(db.Model):
    __tablename__ = 'maquinaria_plan_item'

    id = db.Column(db.Integer, primary_key=True)

    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey('maquinaria.id'),
        nullable=False
    )

    plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_items.id'),
        nullable=False
    )

    # 🔥 HORAS
    frecuencia_horas = db.Column(db.Integer)

    alerta_horas = db.Column(db.Integer, default=20)
    horas_base = db.Column(db.Integer, default=0)
    ultima_horas = db.Column(db.Integer, default=0)

    ultima_fecha = db.Column(db.Date)

    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # RELACIONES
    maquinaria = db.relationship(
        'Maquinaria',
        back_populates='mantenimientos_programados',
        lazy='joined'
    )
    plan_item = db.relationship('PlanItem', lazy='joined')

    # ==========================
    # LÓGICA
    # ==========================
    def calcular_horas_programadas(self):

        if not self.frecuencia_horas:
            return None

        return self.calcular_proxima_hora()

    def calcular_ocurrencias(self):

        if not self.frecuencia_horas or not self.maquinaria:
            return []

        horas_actuales = int(
            self.maquinaria.horometro_actual or 0
        )

        base = int(
            self.horas_base or 0
        )

        frecuencia = int(
            self.frecuencia_horas
        )

        if horas_actuales < base + frecuencia:
            return []

        cantidad = (
            (horas_actuales - base)
            // frecuencia
        )

        return [
            base + (frecuencia * i)
            for i in range(1, cantidad + 1)
        ]
        
        
        
    def calcular_proxima_hora(self):

        if not self.frecuencia_horas:
            return None

        frecuencia = int(self.frecuencia_horas)

        # Si ya existe un mantenimiento registrado,
        # el próximo se calcula desde la hora de ese mantenimiento.
        if self.ultima_horas is not None and self.ultima_horas > 0:
            ultima_hora = int(self.ultima_horas)
        else:
            # Si todavía nunca se ha realizado un mantenimiento,
            # se toma horas_base como punto inicial.
            ultima_hora = int(self.horas_base or 0)

        return ultima_hora + frecuencia



    def calcular_horas_restantes(self):

        if not self.maquinaria:
            return None

        horas_actuales = self.maquinaria.horometro_actual or 0
        horas_programadas = self.calcular_proxima_hora()

        if horas_programadas is None:
            return None

        horas_actuales = Decimal(str(horas_actuales))
        horas_programadas = Decimal(str(horas_programadas))

        return horas_programadas - horas_actuales
    
    def calcular_estado(self):

        restantes = self.calcular_horas_restantes()

        if restantes is None:
            return "ACTIVO"

        if restantes <= 0:
            return "VENCIDO"

        if restantes <= (self.alerta_horas or 0):
            return "PENDIENTE"

        return "ACTIVO"

    # ==========================
    # SERIALIZACIÓN
    # ==========================
    def to_dict(self):

        return {
            "id": self.id,

            "maquinaria_id": self.maquinaria_id,
            "plan_item_id": self.plan_item_id,

            "frecuencia_horas": self.frecuencia_horas,
            "alerta_horas": self.alerta_horas,

            "horas_base": self.horas_base,
            "ultima_horas": self.ultima_horas,

            "ultima_fecha": (
                str(self.ultima_fecha)
                if self.ultima_fecha
                else None
            ),

            "horometro_actual": (
                self.maquinaria.horometro_actual
                if self.maquinaria
                else 0
            ),

            "horas_programadas": self.calcular_horas_programadas(),

            "horas_restantes": self.calcular_horas_restantes(),

            "estado": self.calcular_estado(),

            "activo": self.activo,

            "sistema": (
                self.plan_item.sistema
                if self.plan_item
                else None
            ),

            "nombre": (
                self.plan_item.nombre
                if self.plan_item
                else None
            ),

            "descripcion": (
                self.plan_item.descripcion
                if self.plan_item
                else None
            ),

            "tipo_mantenimiento": (
                self.plan_item.tipo_mantenimiento
                if self.plan_item
                else None
            ),

            "tipo_control": "HORAS",

            "plan_item": (
                self.plan_item.to_dict()
                if self.plan_item
                else None
            )
        }
        

class MaquinariaMantenimiento(db.Model):
    __tablename__ = 'maquinaria_mantenimientos'

    id = db.Column(db.Integer, primary_key=True)

    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey('maquinaria.id')
    )

    plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_items.id')
    )

    maquinaria_plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('maquinaria_plan_item.id')
    )

    fecha = db.Column(db.Date)

    horas = db.Column(db.Integer)
    horas_programadas = db.Column(db.Integer)

    tipo = db.Column(db.String(5))

    proveedor = db.Column(db.String(100))

    costo = db.Column(db.Float)

    lugar = db.Column(db.String(150))

    responsable = db.Column(db.String(150))

    soporte = db.Column(db.String(255))

    observaciones = db.Column(db.Text)

    completado = db.Column(db.Boolean, default=True)

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    maquinaria_plan_item = db.relationship(
        'MaquinariaPlanItem',
        lazy='joined'
    )

    maquinaria = db.relationship(
        'Maquinaria',
        lazy='joined'
    )

    def to_dict(self):

        return {
            "id": self.id,

            "maquinaria_id": self.maquinaria_id,

            "plan_item_id": self.plan_item_id,

            "maquinaria_plan_item_id": self.maquinaria_plan_item_id,

            "fecha": str(self.fecha) if self.fecha else None,

            "horas": self.horas,

            "tipo": self.tipo,

            "proveedor": self.proveedor,

            "costo": self.costo,

            "lugar": self.lugar,

            "responsable": self.responsable,

            "soporte": self.soporte,

            "observaciones": self.observaciones,

            "completado": self.completado,
            "horas_programadas": self.horas_programadas,
            "plan_item": (
                self.maquinaria_plan_item.plan_item.to_dict()
                if self.maquinaria_plan_item and self.maquinaria_plan_item.plan_item
                else None
            ),
            "maquinaria": (
                {
                    "id": self.maquinaria.id,
                    "codigo": self.maquinaria.codigo,
                    "marca": self.maquinaria.marca,
                    "modelo": self.maquinaria.modelo
                }
                if self.maquinaria else None
            ),
        }

class PlanesMantenimiento(db.Model):
    __tablename__ = "planes_mantenimiento"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)

    tipo_equipo = db.Column(
        db.Enum("AUTOMOTOR", "NO_AUTOMOTOR", "MAQUINARIA"),
        nullable=False
    )

    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())
    updated_at = db.Column(db.DateTime, onupdate=db.func.now())


    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "tipo_equipo": self.tipo_equipo,
            "activo": self.activo,
            "created_at": str(self.created_at) if self.created_at else None,
            "updated_at": str(self.updated_at) if self.updated_at else None
        }
        
        
class SistemaVehiculo(db.Model):
    __tablename__ = "sistemas_vehiculo"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    
class PlanItemActividad(db.Model):
    __tablename__ = 'plan_item_actividades'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_items.id'),
        nullable=False
    )

    nombre = db.Column(
        db.String(255),
        nullable=False
    )

    descripcion = db.Column(
        db.Text
    )

    obligatorio = db.Column(
        db.Boolean,
        default=True
    )

    orden = db.Column(
        db.Integer,
        default=0
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    plan_item = db.relationship(
        'PlanItem',
        back_populates='actividades'
    )

    def to_dict(self):
        return {
            "id": self.id,
            "plan_item_id": self.plan_item_id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "obligatorio": self.obligatorio,
            "orden": self.orden,
            "activo": self.activo
        }
          
class Viaje(db.Model):
    __tablename__ = 'viajes'

    # ==========================
    # ID
    # ==========================
    id = db.Column(db.Integer, primary_key=True)

    # ==========================
    # VEHÍCULO Y REMOLQUE
    # ==========================
    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id'),
        nullable=False
    )

    remolque_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id'),
        nullable=True
    )

    vehiculo = db.relationship(
        'Vehiculo',
        foreign_keys=[vehiculo_id]
    )

    remolque = db.relationship(
        'Vehiculo',
        foreign_keys=[remolque_id]
    )

    # ==========================
    # CONDUCTOR
    # ==========================
    conductor = db.Column(db.String(100))
    cc_conductor = db.Column(db.String(50))

    # ==========================
    # RUTA
    # ==========================
    origen = db.Column(db.String(255))
    destino = db.Column(db.String(255))

    # ==========================
    # CARGA
    # ==========================
    cliente = db.Column(db.String(150))
    tipo_carga = db.Column(db.String(100))
    descripcion_carga = db.Column(db.Text)
    peso = db.Column(db.Numeric)

    # ==========================
    # KILOMETRAJE DEL REMOLQUE
    # ==========================
    km_inicio = db.Column(db.Integer)
    km_fin = db.Column(db.Integer)
    km_recorrido = db.Column(db.Integer)

    # ==========================
    # OBSERVACIONES
    # ==========================
    observaciones = db.Column(db.Text)

    # ==========================
    # ESTADO
    # ==========================
    estado = db.Column(
        db.String(50),
        default='PROGRAMADO'
    )

    # ==========================
    # CONTROL
    # ==========================
    activo = db.Column(
        db.Boolean,
        default=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    # ==========================
    # SERIALIZACIÓN
    # ==========================
    def to_dict(self):
        return {

            "id": self.id,

            "vehiculo_id": self.vehiculo_id,
            "remolque_id": self.remolque_id,

            "vehiculo": self.vehiculo.to_dict() if self.vehiculo else None,
            "remolque": self.remolque.to_dict() if self.remolque else None,

            "conductor": self.conductor,
            "cc_conductor": self.cc_conductor,

            "origen": self.origen,
            "destino": self.destino,

            "cliente": self.cliente,
            "tipo_carga": self.tipo_carga,
            "descripcion_carga": self.descripcion_carga,

            "peso": float(self.peso) if self.peso else None,

            "km_inicio": self.km_inicio,
            "km_fin": self.km_fin,
            "km_recorrido": self.km_recorrido,

            "observaciones": self.observaciones,

            "estado": self.estado,

            "activo": self.activo,

            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }


class Alerta(db.Model):

    __tablename__ = 'alertas'

    # =====================================================
    # PRIMARY KEY
    # =====================================================

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculos.id'),
        nullable=True
    )

    viaje_id = db.Column(
        db.Integer,
        db.ForeignKey('viajes.id'),
        nullable=True
    )

    mantenimiento_id = db.Column(
        db.Integer,
        db.ForeignKey('mantenimientos.id'),
        nullable=True
    )

    plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('plan_items.id'),
        nullable=True
    )

    vehiculo_plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('vehiculo_plan_item.id'),
        nullable=True
    )

    # =====================================================
    # INFORMACIÓN ALERTA
    # =====================================================

    tipo = db.Column(
        db.String(100)
    )

    categoria = db.Column(
        db.String(100)
    )

    titulo = db.Column(
        db.String(255)
    )

    mensaje = db.Column(
        db.Text
    )

    prioridad = db.Column(
        db.Enum(
            'BAJA',
            'MEDIA',
            'ALTA',
            'CRITICA'
        ),
        default='MEDIA'
    )

    estado = db.Column(
        db.Enum(
            'ACTIVA',
            'RESUELTA',
            'IGNORADA'
        ),
        default='ACTIVA'
    )

    origen = db.Column(
        db.String(100)
    )
    email_enviado = db.Column(
    db.Boolean,
    default=False)

    # =====================================================
    # FECHAS
    # =====================================================

    fecha_evento = db.Column(
        db.DateTime
    )

    fecha_resolucion = db.Column(
        db.DateTime,
        nullable=True
    )

    # =====================================================
    # JSON FLEXIBLE
    # =====================================================

    metadata_json = db.Column(
        'metadata',
        db.JSON,
        nullable=True
    )

    # =====================================================
    # CREATED
    # =====================================================

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    
    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey('maquinaria.id'),
        nullable=True
    )

    maquinaria_mantenimiento_id = db.Column(
        db.Integer,
        db.ForeignKey('maquinaria_mantenimientos.id'),
        nullable=True
    )

    maquinaria_plan_item_id = db.Column(
        db.Integer,
        db.ForeignKey('maquinaria_plan_item.id'),
        nullable=True
    )

    # =====================================================
    # RELACIONES SQLALCHEMY
    # =====================================================

    vehiculo = db.relationship(
        'Vehiculo',
        lazy=True
    )

    viaje = db.relationship(
        'Viaje',
        lazy=True
    )

    mantenimiento = db.relationship(
        'Mantenimiento',
        lazy=True
    )

    plan_item = db.relationship(
        'PlanItem',
        lazy=True
    )

    vehiculo_plan_item = db.relationship(
        'VehiculoPlanItem',
        lazy=True
    )
    maquinaria = db.relationship(
        'Maquinaria',
        lazy=True
    )

    maquinaria_mantenimiento = db.relationship(
        'MaquinariaMantenimiento',
        lazy=True
    )

    maquinaria_plan_item = db.relationship(
        'MaquinariaPlanItem',
        lazy=True
    )
    

    # =====================================================
    # SERIALIZAR
    # =====================================================

    def to_dict(self):

        return {

            'id': self.id,

            # =========================================
            # RELACIONES
            # =========================================

            'vehiculo_id': self.vehiculo_id,

            'viaje_id': self.viaje_id,

            'mantenimiento_id':
                self.mantenimiento_id,

            'plan_item_id':
                self.plan_item_id,

            'vehiculo_plan_item_id':
                self.vehiculo_plan_item_id,

            # =========================================
            # ALERTA
            # =========================================

            'tipo': self.tipo,

            'categoria': self.categoria,

            'titulo': self.titulo,

            'mensaje': self.mensaje,

            'prioridad': self.prioridad,

            'estado': self.estado,

            'origen': self.origen,

            # =========================================
            # FECHAS
            # =========================================

            'fecha_evento': (
                self.fecha_evento.isoformat()
                if self.fecha_evento
                else None
            ),

            'fecha_resolucion': (
                self.fecha_resolucion.isoformat()
                if self.fecha_resolucion
                else None
            ),

            'created_at': (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            # =========================================
            # METADATA
            # =========================================

            'metadata': self.metadata_json,

            # =========================================
            # VEHÍCULO
            # =========================================

            'vehiculo': (
                {
                    'id': self.vehiculo.id,
                    'placa': self.vehiculo.placa,
                    'marca': self.vehiculo.marca
                }
                if self.vehiculo
                else None
            ),

            # =========================================
            # VIAJE
            # =========================================

            'viaje': (
                {
                    'id': self.viaje.id,
                    'origen': self.viaje.origen,
                    'destino': self.viaje.destino,
                    'estado': self.viaje.estado
                }
                if self.viaje
                else None
            ),
            'maquinaria_id': self.maquinaria_id,

            'maquinaria_plan_item_id': self.maquinaria_plan_item_id,
            'maquinaria_mantenimiento_id': self.maquinaria_mantenimiento_id,
            'maquinaria': (
                {
                    'id': self.maquinaria.id,
                    'codigo': self.maquinaria.codigo,
                    'marca': self.maquinaria.marca
                }
                if self.maquinaria
                else None
            ),

            # =========================================
            # PLAN ITEM
            # =========================================

            'plan_item': (
                {
                    'id': self.plan_item.id,
                    'nombre': self.plan_item.nombre
                }
                if self.plan_item
                else None
            ),
            
            'maquinaria_plan_item': (

                {
                    'id': self.maquinaria_plan_item.id,

                    'plan_item_id': self.maquinaria_plan_item.plan_item_id,

                    'plan_item': (
                        self.maquinaria_plan_item.plan_item.nombre
                        if self.maquinaria_plan_item.plan_item
                        else None
                    )
                }

                if self.maquinaria_plan_item
                else None
            ),
            
        }
        
        
class ConfiguracionSistema(db.Model):
    __tablename__ = "configuracion_sistema"

    id = db.Column(db.Integer, primary_key=True)

    ultima_sync_satrack = db.Column(db.DateTime)
    
    

# ==========================
# INSPECCIONES MENSUALES
# ==========================
class InspeccionMensual(db.Model):
    __tablename__ = "inspecciones_mensuales"

    id = db.Column(db.Integer, primary_key=True)

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("vehiculos.id"),
        nullable=True
    )

    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey("maquinaria.id"),
        nullable=True
    )

    fecha = db.Column(db.Date, nullable=False)

    archivo = db.Column(
        db.String(255),
        nullable=False
    )

    observaciones = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )

    def to_dict(self):
        return {
            "id": self.id,
            "vehiculo_id": self.vehiculo_id,
            "maquinaria_id": self.maquinaria_id,
            "fecha": str(self.fecha),
            "archivo": self.archivo,
            "observaciones": self.observaciones,
            "created_at": str(self.created_at)
        }
        
        
# ==========================
# PREOPERACIONAL VEHICULAR
# ==========================


class TipoInspeccion(db.Model):
    __tablename__ = "tipos_inspeccion"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    activo = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(ZoneInfo("America/Bogota")))

    plantillas = db.relationship(
        "InspeccionPlantilla",
        backref="tipo_inspeccion",
        lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "activo": self.activo
        }

class InspeccionPlantilla(db.Model):
    __tablename__ = "inspeccion_plantillas"

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(150), nullable=False)

    descripcion = db.Column(db.Text)

    tipo_inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("tipos_inspeccion.id"),
        nullable=False
    )

    tipo_activo = db.Column(
        db.Enum("VEHICULO", "MAQUINARIA", name="tipo_activo_inspeccion"),
        nullable=False
    )
    tipo_medicion = db.Column(
        db.Enum(
            "KILOMETRAJE",
            "HOROMETRO",
            "NINGUNO",
            name="tipo_medicion_inspeccion"
        ),
        default="NINGUNO",
        nullable=False
    )

    tipo_vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("tipos_vehiculo.id")
    )

    tipo_maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey("tipos_maquinaria.id")
    )

    version = db.Column(db.Integer, default=1)

    activa = db.Column(db.Boolean, default=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )
    inspecciones = db.relationship(
        "Inspeccion",
        backref="plantilla",
        lazy=True
    )

    categorias = db.relationship(
        "InspeccionCategoria",
        backref="plantilla",
        cascade="all, delete-orphan",
        lazy=True
    )
    tipo_vehiculo = db.relationship(
        "TipoVehiculo",
        backref="plantillas_inspeccion"
    )

    tipo_maquinaria = db.relationship(
        "TipoMaquinaria",
        backref="plantillas_inspeccion"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "tipo_inspeccion_id",
            "tipo_vehiculo_id",
            "version",
            name="uq_plantilla_vehiculo"
        ),
        db.UniqueConstraint(
            "tipo_inspeccion_id",
            "tipo_maquinaria_id",
            "version",
            name="uq_plantilla_maquinaria"
        )
        
    )

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "descripcion": self.descripcion,
            "tipo_inspeccion_id": self.tipo_inspeccion_id,
            "tipo_activo": self.tipo_activo,
            "tipo_vehiculo_id": self.tipo_vehiculo_id,
            "tipo_maquinaria_id": self.tipo_maquinaria_id,
            "version": self.version,
            "activa": self.activa,
            "tipo_medicion": self.tipo_medicion,

            "categorias": [
                categoria.to_dict()
                for categoria in self.categorias
            ]
        }

class InspeccionCategoria(db.Model):
    __tablename__ = "inspeccion_categorias"

    id = db.Column(db.Integer, primary_key=True)

    plantilla_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion_plantillas.id", ondelete="CASCADE"),
        nullable=False
    )

    nombre = db.Column(db.String(150), nullable=False)

    orden = db.Column(db.Integer, default=1)

    items = db.relationship(
        "InspeccionItem",
        backref="categoria",
        cascade="all, delete-orphan",
        lazy=True,
        order_by="InspeccionItem.orden"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "plantilla_id": self.plantilla_id,
            "nombre": self.nombre,
            "orden": self.orden,

            "items": [
                item.to_dict()
                for item in self.items
                if item.activo
            ]
        }

class InspeccionItem(db.Model):
    __tablename__ = "inspeccion_items"

    id = db.Column(db.Integer, primary_key=True)

    categoria_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion_categorias.id", ondelete="CASCADE"),
        nullable=False
    )

    codigo = db.Column(db.String(50), unique=True, nullable=False)

    descripcion = db.Column(db.String(255))

    orden = db.Column(db.Integer, default=1)

    tipo_respuesta = db.Column(
        db.Enum(
            "SI_NO",
            "SI_NO_NA",
            "NUMERO",
            "TEXTO",
            name="tipo_respuesta_inspeccion"
        ),
        default="SI_NO_NA"
    )

    ayuda = db.Column(db.Text)

    placeholder = db.Column(db.String(150))

    obligatorio = db.Column(db.Boolean, default=True)

    permite_na = db.Column(db.Boolean, default=False)

    requiere_observacion = db.Column(db.Boolean, default=False)

    requiere_foto = db.Column(db.Boolean, default=False)

    foto_si_falla = db.Column(db.Boolean, default=True)

    genera_alerta = db.Column(db.Boolean, default=True)

    bloquea_operacion = db.Column(db.Boolean, default=False)

    criticidad = db.Column(
        db.Enum(
            "BAJA",
            "MEDIA",
            "ALTA",
            "CRITICA",
            name="criticidad_inspeccion"
        ),
        default="MEDIA"
    )

    activo = db.Column(db.Boolean, default=True)

    respuestas = db.relationship(
        "InspeccionRespuesta",
        backref="item",
        lazy=True
    )

    def to_dict(self):
        return {
            "id": self.id,
            "categoria_id": self.categoria_id,
            "codigo": self.codigo,
            "descripcion": self.descripcion,
            "orden": self.orden,
            "tipo_respuesta": self.tipo_respuesta,
            "ayuda": self.ayuda,
            "placeholder": self.placeholder,
            "obligatorio": self.obligatorio,
            "permite_na": self.permite_na,
            "requiere_observacion": self.requiere_observacion,
            "requiere_foto": self.requiere_foto,
            "foto_si_falla": self.foto_si_falla,
            "genera_alerta": self.genera_alerta,
            "bloquea_operacion": self.bloquea_operacion,
            "criticidad": self.criticidad,
            "activo": self.activo
        }


class Inspeccion(db.Model):
    __tablename__ = "inspecciones"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    plantilla_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion_plantillas.id"),
        nullable=False
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("vehiculos.id")
    )

    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey("maquinaria.id")
    )

    hora_inicio = db.Column(
        db.DateTime,
        nullable=False,
        default=lambda: datetime.now(
            ZoneInfo("America/Bogota")
        )
    )

    hora_fin = db.Column(
        db.DateTime
    )

    # =====================================================
    # LECTURA / CONTADOR DEL ACTIVO
    # =====================================================

    contador_inicial = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    foto_contador_inicial = db.Column(
        db.String(500),
        nullable=True
    )

    contador_final = db.Column(
        db.Numeric(12, 2),
        nullable=True
    )

    foto_contador_final = db.Column(
        db.String(500),
        nullable=True
    )

    # =====================================================
    # ESTADO
    # =====================================================

    estado = db.Column(
        db.Enum(
            'BORRADOR',
            'EN_PROCESO',
            'FINALIZADA',
            'REVISADA',
            'ANULADA',
            'PENDIENTE_CIERRE',
            name="estado_inspeccion"
        ),
        default="BORRADOR"
    )

    responsable_revision = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id")
    )

    fecha_revision = db.Column(
        db.DateTime
    )

    observaciones_generales = db.Column(
        db.Text
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(
            ZoneInfo("America/Bogota")
        )
    )

    # =====================================================
    # RELACIONES
    # =====================================================

    anomalias = db.relationship(
        "InspeccionAnomalia",
        backref="inspeccion",
        cascade="all, delete-orphan",
        lazy=True
    )

    respuestas = db.relationship(
        "InspeccionRespuesta",
        backref="inspeccion",
        cascade="all, delete-orphan",
        lazy=True
    )

    usuario = db.relationship(
        "Usuario",
        foreign_keys=[usuario_id],
        backref="inspecciones_realizadas"
    )

    revisor = db.relationship(
        "Usuario",
        foreign_keys=[responsable_revision],
        backref="inspecciones_revisadas"
    )

    vehiculo = db.relationship(
        "Vehiculo",
        back_populates="inspecciones_preoperacionales"
    )

    maquinaria = db.relationship(
        "Maquinaria",
        back_populates="inspecciones_preoperacionales"
    )

    # =====================================================
    # SERIALIZACIÓN
    # =====================================================

    def to_dict(self):

        return {

            "id": self.id,

            "plantilla_id": self.plantilla_id,

            "estado": self.estado,

            # =================================================
            # FECHAS
            # =================================================

            "hora_inicio": (
                self.hora_inicio.isoformat()
                if self.hora_inicio
                else None
            ),

            "hora_fin": (
                self.hora_fin.isoformat()
                if self.hora_fin
                else None
            ),

            "created_at": (
                self.created_at.isoformat()
                if self.created_at
                else None
            ),

            # =================================================
            # USUARIO
            # =================================================

            "usuario_id": self.usuario_id,

            "usuario": (
                self.usuario.nombre
                if self.usuario
                else None
            ),

            # =================================================
            # ACTIVO
            # =================================================

            "vehiculo_id": self.vehiculo_id,

            "placa": (
                self.vehiculo.placa
                if self.vehiculo
                else None
            ),

            "maquinaria_id": self.maquinaria_id,

            "codigo_maquinaria": (
                self.maquinaria.codigo
                if self.maquinaria
                else None
            ),

            "tipo_maquinaria": (
                self.maquinaria.tipo_maquinaria.nombre
                if self.maquinaria
                and self.maquinaria.tipo_maquinaria
                else None
            ),

            # =================================================
            # TIPO DE MEDICIÓN
            # =================================================

            "tipo_medicion": (
                self.plantilla.tipo_medicion
                if self.plantilla
                else None
            ),

            # =================================================
            # LECTURAS
            # =================================================

            "lectura_inicial": (
                float(self.contador_inicial)
                if self.contador_inicial is not None
                else None
            ),

            "lectura_final": (
                float(self.contador_final)
                if self.contador_final is not None
                else None
            ),

            "contador_inicial": (
                float(self.contador_inicial)
                if self.contador_inicial is not None
                else None
            ),

            "contador_final": (
                float(self.contador_final)
                if self.contador_final is not None
                else None
            ),

            "foto_contador_inicial": (
                self.foto_contador_inicial
            ),

            "foto_contador_final": (
                self.foto_contador_final
            ),

            # =================================================
            # OBSERVACIONES
            # =================================================

            "observaciones_generales": (
                self.observaciones_generales
            )
        }



class InspeccionRespuesta(db.Model):
    __tablename__ = "inspeccion_respuestas"

    id = db.Column(db.Integer, primary_key=True)

    alerta_id = db.Column(
        db.Integer,
        db.ForeignKey("alertas.id")
    )

    inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("inspecciones.id", ondelete="CASCADE"),
        nullable=False
    )

    item_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion_items.id"),
        nullable=False
    )

    valor = db.Column(db.String(255))

    observacion = db.Column(db.Text)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    fotos = db.relationship(
        "InspeccionFoto",
        backref="respuesta",
        cascade="all, delete-orphan",
        lazy=True
    )
    alerta = db.relationship(
        "Alerta",
        backref="respuestas_inspeccion"
    )

    def to_dict(self):
        return {
            "id": self.id,
            "alerta_id": self.alerta_id,
            "inspeccion_id": self.inspeccion_id,
            "item_id": self.item_id,
            "valor": self.valor,
            "observacion": self.observacion,
            "fotos": [foto.to_dict() for foto in self.fotos]
        }

class InspeccionFoto(db.Model):
    __tablename__ = "inspeccion_fotos"

    id = db.Column(db.Integer, primary_key=True)

    respuesta_id = db.Column(
        db.Integer,
        db.ForeignKey("inspeccion_respuestas.id", ondelete="CASCADE"),
        nullable=False
    )

    archivo = db.Column(db.String(500), nullable=False)

    latitud = db.Column(db.Numeric(10, 8))

    longitud = db.Column(db.Numeric(11, 8))

    precision_gps = db.Column(db.Numeric(8, 2))

    direccion = db.Column(db.String(255))

    fecha_dispositivo = db.Column(db.DateTime)

    fecha_servidor = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    watermark = db.Column(db.Boolean, default=True)

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    mime_type = db.Column(db.String(50))

    tamano_bytes = db.Column(db.BigInteger)

    ancho = db.Column(db.Integer)

    alto = db.Column(db.Integer)

    hash_archivo = db.Column(db.String(64))

    def to_dict(self):
        return {
            "id": self.id,
            "respuesta_id": self.respuesta_id,
            "archivo": self.archivo,
            "latitud": float(self.latitud) if self.latitud else None,
            "longitud": float(self.longitud) if self.longitud else None,
            "precision_gps": float(self.precision_gps) if self.precision_gps else None,
            "direccion": self.direccion,
            "fecha_dispositivo": self.fecha_dispositivo.isoformat() if self.fecha_dispositivo else None,
            "fecha_servidor": self.fecha_servidor.isoformat() if self.fecha_servidor else None,
            "watermark": self.watermark,
            "mime_type": self.mime_type,
            "tamano_bytes": self.tamano_bytes,
            "ancho": self.ancho,
            "alto": self.alto,
            "hash_archivo": self.hash_archivo
        }

class ActivoOperador(db.Model):
    __tablename__ = "activo_operador"

    id = db.Column(db.Integer, primary_key=True)

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    vehiculo_id = db.Column(
        db.Integer,
        db.ForeignKey("vehiculos.id")
    )

    maquinaria_id = db.Column(
        db.Integer,
        db.ForeignKey("maquinaria.id")
    )

    activo = db.Column(
        db.Boolean,
        default=True
    )

    fecha_asignacion = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    fecha_fin = db.Column(db.DateTime)

    observaciones = db.Column(db.Text)

    usuario = db.relationship(
        "Usuario",
        backref="activos_asignados"
    )

    vehiculo = db.relationship(
        "Vehiculo",
        backref="operadores_asignados"
    )

    maquinaria = db.relationship(
        "Maquinaria",
        backref="operadores_asignados"
    )
    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "vehiculo_id": self.vehiculo_id,
            "maquinaria_id": self.maquinaria_id,
            "activo": self.activo,
            "fecha_asignacion": self.fecha_asignacion.isoformat() if self.fecha_asignacion else None,
            "fecha_fin": self.fecha_fin.isoformat() if self.fecha_fin else None,
            "observaciones": self.observaciones
        }


class InspeccionAnomalia(db.Model):

    __tablename__ = "anomalias"

    id = db.Column(db.Integer, primary_key=True)

    inspeccion_id = db.Column(
        db.Integer,
        db.ForeignKey("inspecciones.id"),
        nullable=False
    )

    usuario_id = db.Column(
        db.Integer,
        db.ForeignKey("usuarios.id"),
        nullable=False
    )

    titulo = db.Column(db.String(200), nullable=False)

    descripcion = db.Column(db.Text)

    prioridad = db.Column(
        db.String(20),
        nullable=False,
        default="MEDIA"
    )

    estado = db.Column(
        db.String(30),
        default="ABIERTA"
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    def to_dict(self):
        return {
            "id": self.id,
            "inspeccion_id": self.inspeccion_id,
            "usuario_id": self.usuario_id,
            "titulo": self.titulo,
            "descripcion": self.descripcion,
            "prioridad": self.prioridad,
            "estado": self.estado,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        

       
class AnomaliaFoto(db.Model):

    __tablename__ = "anomalia_fotos"

    id = db.Column(db.Integer, primary_key=True)

    anomalia_id = db.Column(
        db.Integer,
        db.ForeignKey("anomalias.id"),
        nullable=False
    )

    archivo = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(ZoneInfo("America/Bogota"))
    )

    def to_dict(self):
        return {
            "id": self.id,
            "anomalia_id": self.anomalia_id,
            "archivo": self.archivo,
            "created_at": (
                self.created_at.isoformat()
                if self.created_at else None
            )
        }