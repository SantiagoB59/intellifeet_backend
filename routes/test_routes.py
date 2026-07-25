from flask import Blueprint

from flask_mail import Message
from extensions import mail

test_bp = Blueprint(
    'test',
    __name__
)

@test_bp.route('/test-email')
def test_email():

    msg = Message(

        subject='Prueba de correo',

        recipients=['transmenasmart@gmail.com']
    )

    msg.body = 'Hola mundo desde Flask 🚀'

    mail.send(msg)

    return {
        "message": "Correo enviado correctamente"
    }