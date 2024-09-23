from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
import bcrypt
import os
from datetime import datetime
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1 import FieldFilter
from BD_config import registrar_usuario, procesar_busqueda, obtener_noticias_guardadas

# Cargar variables de entorno desde .env
load_dotenv()

app = Flask(__name__)

# Configurar CORS para permitir solicitudes desde tu frontend
CORS(app, resources={r"/*": {"origins": "https://search-engine-update-617702685780.us-west1.run.app"}})

# Inicializar Firebase usando variables de entorno
service_account_info = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL")
}

cred = credentials.Certificate(service_account_info)
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

DEFAULT_TOPIC = "predefined_topic"
DEFAULT_CONTEXT = "predefined_context"

@app.route('/register', methods=['POST'])
@cross_origin()
def register():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    search = data.get('search', DEFAULT_TOPIC)
    context = data.get('context', DEFAULT_CONTEXT)

    usuarios_ref = db.collection('Usuarios')
    query = usuarios_ref.where('correo', '==', email).stream()

    if any(query):
        return jsonify({'success': False, 'message': 'El correo ya está registrado.'}), 409

    try:
        registrar_usuario(email, password, search, context)
        return jsonify({'success': True, 'message': 'Usuario registrado correctamente.'})
    except Exception as e:
        print(f"Error durante el registro: {e}")
        return jsonify({'success': False, 'message': 'Hubo un problema al registrar el usuario.'}), 500

@app.route('/login', methods=['POST'])
@cross_origin(origin='localhost', headers=['Content-Type', 'Authorization'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')

    print(f"Received login attempt: email={email}")

    usuarios_ref = db.collection('Usuarios')
    query = usuarios_ref.where(filter=FieldFilter('correo', '==', email)).stream()

    for user in query:
        user_data = user.to_dict()
        stored_password = user_data.get('contrasena')
        predefined_topic = user_data.get('busqueda_contextos_predefinidos', {}).get('busqueda', DEFAULT_TOPIC)
        predefined_context = user_data.get('busqueda_contextos_predefinidos', {}).get('contexto', DEFAULT_CONTEXT)

        if bcrypt.checkpw(password.encode('utf-8'), stored_password.encode('utf-8')):
            print(f"Login successful for: email={email}")
            return jsonify({
                'success': True,
                'predefined_topic': predefined_topic,
                'predefined_context': predefined_context,
                'user_id': user.id
            })

    print("Login failed: invalid credentials")
    return jsonify({'success': False}), 401

@app.route('/update_predefined_search', methods=['POST'])
@cross_origin(origin='localhost', headers=['Content-Type', 'Authorization'])
def update_predefined_search():
    data = request.json
    user_id = data.get('user_id')
    predefined_topic = data.get('predefined_topic')
    predefined_context = data.get('predefined_context')

    try:
        usuario_ref = db.collection('Usuarios').document(user_id)
        usuario_ref.update({
            'busqueda_contextos_predefinidos.busqueda': predefined_topic,
            'busqueda_contextos_predefinidos.contexto': predefined_context
        })
        return jsonify({"success": True, "message": "Predefined search updated successfully."})
    except Exception as e:
        print(f"Error updating predefined search: {e}")
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/search', methods=['POST'])
@cross_origin(origin='localhost', headers=['Content-Type', 'Authorization'])
def search_news():
    data = request.json  # Asegúrate de que 'data' es un diccionario
    query = data.get('query')

    if not query:
        return jsonify({"message": "Query is required"}), 400

    try:
        resultados = procesar_busqueda(query, batch_size=20)  # Ajustar el tamaño del lote según necesidad
        
        # Asegurarse de que 'resultados' sea una lista de diccionarios, no una cadena o número
        if not isinstance(resultados, list):
            raise ValueError("Los resultados no son una lista como se esperaba.")
        
        # Asegúrate de que cada 'resumen' en 'resultados' sea un diccionario con los campos esperados
        for resultado in resultados:
            if not isinstance(resultado, dict):
                raise ValueError(f"Un resultado no es un diccionario: {resultado}")

        return jsonify({"success": True, "message": "Search completed successfully.", "results": resultados}), 200
    except Exception as e:
        print(f"Error during search processing: {e}")
        return jsonify({"message": "Error occurred during search processing", "error": str(e)}), 500


@app.route('/get_news_report', methods=['POST'])
@cross_origin(origin='localhost', headers=['Content-Type', 'Authorization'])
def get_news_report():
    data = request.json
    query = data.get('query')
    page = int(data.get('page', 1))  # Página solicitada
    page_size = int(data.get('pageSize', 5))  # Tamaño de la página (5 por defecto)

    if not query:
        return jsonify({"message": "Query is required"}), 400

    try:
        # Obtén todas las noticias guardadas desde la base de datos
        noticias_guardadas = obtener_noticias_guardadas(query)

        # Si no hay noticias, responde con un mensaje de error
        if not noticias_guardadas:
            print(f"No se encontraron noticias para el tema: {query}")
            return jsonify({"success": False, "message": "No se encontraron noticias guardadas para este tema."}), 404

        # Ordenar las noticias por fecha descendente y tomar las 10 más recientes
        noticias_guardadas.sort(key=lambda x: x['Fecha'], reverse=True)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_news = noticias_guardadas[start:end]

        return jsonify({"success": True, "report": paginated_news}), 200
    except ValueError as ve:
        print(f"Error de formato de fecha: {ve}")
        return jsonify({"message": "Error en el formato de la fecha de las noticias.", "error": str(ve)}), 501
    except Exception as e:
        print(f"Error fetching news report: {e}")
        return jsonify({"message": "Error occurred during fetching news report", "error": str(e)}), 502


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

