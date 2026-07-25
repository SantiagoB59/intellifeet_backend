from extensions import db
from datetime import datetime

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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    

