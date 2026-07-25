from app import create_app, db
from models import Usuario

app = create_app()

with app.app_context():
    admin = Usuario(
        nombre="Administrador",
        email="admin@amaretto.com",
        role_id=1,   # rol superadmin
        telefono="123456789",
        activo=True
    )
    admin.set_password("admin123")

    mesero = Usuario(
        nombre="Mesero",
        email="mesero@amaretto.com",
        role_id=2,   # rol trabajador
        telefono="987654321",
        activo=True
    )
    mesero.set_password("trabajador123")

    db.session.add(admin)
    db.session.add(mesero)
    db.session.commit()

    print("✅ Usuarios creados con éxito")
