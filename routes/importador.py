from flask import Blueprint, request, jsonify

from services.importador_service import (
    importar_excel_service
)

importador_bp = Blueprint(
    'importador',
    __name__
)

# ==========================
# IMPORTAR EXCEL
# ==========================
@importador_bp.route(
    '',
    methods=['POST']
)
def importar_excel():

    try:

        # ==========================
        # ARCHIVO
        # ==========================
        archivo = request.files.get(
            'file'
        )

        if not archivo:

            return jsonify({
                "error": "Archivo requerido"
            }), 400

        # ==========================
        # IMPORTAR
        # ==========================
        resultado = importar_excel_service(
            archivo
        )

        return jsonify({
            "success": True,
            "message": "Importación completada",
            "resultado": resultado
        })

    except Exception as e:

        return jsonify({
            "success": False,
            "error": str(e)
        }), 500