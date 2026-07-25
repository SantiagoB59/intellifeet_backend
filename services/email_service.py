from flask_mail import Message
from extensions import mail
from flask import current_app
import os



def enviar_email_alerta(alerta):
    destinatarios = [
        "transmenasmart@gmail.com",
        # "auxiliaroperaciones@transmenaycarga.com",
        # "mantenimiento@transmenaycarga.com"
    ]
    
    destinatario = os.getenv(
        "ALERTA_EMAIL",
        "transmenasmart@gmail.com"
    )

    color = "#dc2626"

    if alerta.prioridad == "ALTA":
        color = "#ea580c"

    elif alerta.prioridad == "MEDIA":
        color = "#ca8a04"

    elif alerta.prioridad == "BAJA":
        color = "#16a34a"

    placa = "N/A"

    if alerta.vehiculo:
        placa = alerta.vehiculo.placa

    msg = Message(
        subject=f"🚨 ALERTA {alerta.prioridad} | {placa}",
        recipients=destinatarios
    )

    # =========================
    # 📌 HTML DEL CORREO
    # =========================
    msg.html = f"""
    <html>

    <body style="
        font-family: Arial, sans-serif;
        background:#f4f6f9;
        padding:20px;
    ">

        <table
            width="700"
            align="center"
            cellpadding="0"
            cellspacing="0"
            style="
                background:white;
                border-radius:12px;
                overflow:hidden;
                box-shadow:0 4px 20px rgba(0,0,0,.1);
            "
        >

            <!-- ================= HEADER ================= -->
            <tr>
                <td style="
                    background:#0f172a;
                    padding:25px;
                    text-align:center;
                ">

                    <img src="cid:logo_transmena"
                         alt="Transmena Smart"
                         style="width:140px; margin-bottom:10px;" />

                    <h1 style="color:white; margin:0;">
                        TRANSMENA SMART
                    </h1>

                    <p style="color:#cbd5e1; margin-top:10px;">
                        Sistema de Monitoreo Vehicular
                    </p>

                </td>
            </tr>

            <!-- ================= BODY ================= -->
            <tr>
                <td style="padding:30px;">

                    <div style="
                        background:{color};
                        color:white;
                        padding:15px;
                        border-radius:8px;
                        text-align:center;
                        font-size:22px;
                        font-weight:bold;
                    ">
                        🚨 ALERTA {alerta.prioridad}
                    </div>

                    <br>

                    <table width="100%">

                        <tr>
                            <td><b>Vehículo:</b></td>
                            <td>{placa}</td>
                        </tr>

                        <tr>
                            <td><b>Tipo:</b></td>
                            <td>{alerta.tipo}</td>
                        </tr>

                        <tr>
                            <td><b>Categoría:</b></td>
                            <td>{alerta.categoria}</td>
                        </tr>

                        <tr>
                            <td><b>Origen:</b></td>
                            <td>{alerta.origen}</td>
                        </tr>

                        <tr>
                            <td><b>Fecha:</b></td>
                            <td>{alerta.fecha_evento}</td>
                        </tr>

                    </table>

                    <br>

                    <div style="
                        background:#f8fafc;
                        padding:20px;
                        border-left:6px solid {color};
                        border-radius:8px;
                    ">

                        <h3>{alerta.titulo}</h3>

                        <p style="
                            font-size:15px;
                            line-height:1.6;
                        ">
                            {alerta.mensaje}
                        </p>

                    </div>

                    <br>

                    <div style="text-align:center;">

                        <a href="http://localhost:4200"
                           style="
                           background:#2563eb;
                           color:white;
                           text-decoration:none;
                           padding:12px 25px;
                           border-radius:8px;
                           font-weight:bold;
                        ">
                            Abrir Plataforma
                        </a>

                    </div>

                </td>
            </tr>

            <!-- ================= FOOTER ================= -->
            <tr>
                <td style="
                    background:#f1f5f9;
                    padding:20px;
                    text-align:center;
                    color:#64748b;
                ">
                    © Transmena Smart
                </td>
            </tr>

        </table>

    </body>

    </html>
    """

    # =========================
    # 📌 EMBEBER LOGO (CID)
    # =========================
    with current_app.open_resource("static/logo_transmena.jpg") as img:
        msg.attach(
            "logo_transmena.jpg",
            "image/jpeg",
            img.read(),
            "inline",
            headers={"Content-ID": "<logo_transmena>"}
        )

    mail.send(msg)