from extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
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


# ==========================
# PLANES
class PlanItem(db.Model):
    __tablename__ = 'plan_items'

    id = db.Column(db.Integer, primary_key=True)

    # ==========================
    # INFORMACIÓN DEL ITEM
    # ==========================
    sistema = db.Column(db.String(100), nullable=False)
    nombre = db.Column(db.String(150), nullable=False)
    descripcion = db.Column(db.Text)

    # ==========================
    # TIPO DE MANTENIMIENTO
    # ==========================
    tipo_mantenimiento = db.Column(
        db.Enum('PREVENTIVO', 'INSPECCION', 'CORRECTIVO'),
        default='PREVENTIVO',
        nullable=False
    )

    # ==========================
    # CONTROL DEL MANTENIMIENTO
    # ==========================
    tipo_control = db.Column(
        db.Enum('KM', 'DIAS', 'HORAS', 'OCASIONAL'),
        default='KM',
        nullable=False
    )

    frecuencia_valor = db.Column(db.Integer)
    alerta_valor = db.Column(db.Integer)

    # ==========================
    # CONFIGURACIÓN
    # ==========================
    obligatorio = db.Column(db.Boolean, default=True)
    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # ==========================
    # SERIALIZACIÓN
    # ==========================
    def to_dict(self):
        return {
            "id": self.id,

            "sistema": self.sistema,
            "nombre": self.nombre,
            "descripcion": self.descripcion,

            "tipo_mantenimiento": self.tipo_mantenimiento,
            "tipo_control": self.tipo_control,

            "frecuencia_valor": self.frecuencia_valor,
            "alerta_valor": self.alerta_valor,

            "obligatorio": self.obligatorio,
            "activo": self.activo,

            "created_at": str(self.created_at) if self.created_at else None
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
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
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
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    




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

    operador = db.Column(db.String(100))  # 🔥 importante si lo usas en front

    gps_id = db.Column(db.String(50))

    estado = db.Column(db.String(20), default="OPERATIVA")

    notas = db.Column(db.Text)

    foto_url = db.Column(db.String(255))

    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # ==========================
    # 📋 INSPECCIONES MENSUALES
    # ==========================
    inspecciones = db.relationship(
        'InspeccionMensual',
        backref='maquinaria',
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

    ultima_horas = db.Column(db.Integer, default=0)

    ultima_fecha = db.Column(db.Date)

    activo = db.Column(db.Boolean, default=True)

    created_at = db.Column(db.DateTime, server_default=db.func.now())

    # RELACIONES
    maquinaria = db.relationship('Maquinaria', lazy='joined')
    plan_item = db.relationship('PlanItem', lazy='joined')

    # ==========================
    # LÓGICA
    # ==========================

    def calcular_horas_programadas(self):

        if not self.frecuencia_horas:
            return None

        return (self.ultima_horas or 0) + self.frecuencia_horas

    def calcular_horas_restantes(self):

        if not self.maquinaria:
            return None

        horas_actuales = self.maquinaria.horometro_actual or 0
        horas_programadas = self.calcular_horas_programadas()

        if horas_programadas is None:
            return None

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

            "ultima_horas": self.ultima_horas,
            "ultima_fecha": str(self.ultima_fecha) if self.ultima_fecha else None,

            "horometro_actual": (
                self.maquinaria.horometro_actual
                if self.maquinaria else 0
            ),

            "horas_programadas": self.calcular_horas_programadas(),
            "horas_restantes": self.calcular_horas_restantes(),

            "estado": self.calcular_estado(),

            "activo": self.activo,
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

            "tipo_control": "HORAS",


            "plan_item": (
                self.plan_item.to_dict()
                if self.plan_item else None
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
        default=datetime.utcnow
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