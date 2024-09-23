import os
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime, timedelta
import bcrypt
from duckduckgo import obtener_enlaces
from test_scraper import scrape_contenido
from ia import generar_resumen_ia   

# Cargar las variables desde el archivo .env
load_dotenv()

# Construir el diccionario para las credenciales de Firebase
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

# Inicializar Firebase con las credenciales cargadas desde el .env
cred = credentials.Certificate(service_account_info)
firebase_admin.initialize_app(cred)

# Inicializar Firestore
db = firestore.client()

def registrar_usuario(correo, contrasena, busqueda_predefinida, contexto_predefinido):
    hashed_password = bcrypt.hashpw(contrasena.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    usuarios_ref = db.collection('Usuarios')
    total_usuarios = usuarios_ref.stream()
    cantidad_usuarios = len(list(total_usuarios))
    nuevo_id = f"user_{cantidad_usuarios + 1}"
    usuario_ref = usuarios_ref.document(nuevo_id)

    usuario_ref.set({
        'correo': correo,
        'contrasena': hashed_password,
        'busqueda_contextos_predefinidos': {
            'busqueda': busqueda_predefinida,
            'contexto': contexto_predefinido
        },
        'temas': []
    })

    print(f"Usuario {nuevo_id} registrado correctamente.")

# Función para agregar una noticia
def agregar_noticia(search_id, noticia_id, contenido, titulo, url, date, source, processed_titles, processed_contents):
    try:
        noticias_ref = db.collection('Noticias').document(search_id).collection('noticias_investigadas')

        # Verificar si el título o el contenido ya fueron procesados
        if titulo in processed_titles or contenido in processed_contents:
            print(f"Noticia {noticia_id} tiene el mismo título o contenido que una noticia existente, no se guardará en la base de datos.")
            return

        noticia_data = {
            "Contenido": contenido,
            "Fecha": date,
            "Título": titulo,
            "URL": url,
            "Source": source
        }

        noticia_ref = noticias_ref.document(noticia_id)
        noticia_ref.set(noticia_data)
        print(f"Noticia {noticia_id} agregada correctamente bajo la búsqueda {search_id}.")

        # Añadir el título y contenido a las listas procesadas
        processed_titles.add(titulo)
        processed_contents.add(contenido)

    except Exception as e:
        print(f"Error al agregar la noticia: {e}")

# Función para manejar fechas en el formato "mes-día-año"
def convertir_fecha(fecha_str):
    formatos = ['%m-%d-%Y', '%m/%d/%Y', '%m-%d-%y', '%m/%d/%y']  # Formatos en mes-día-año
    for formato in formatos:
        try:
            return datetime.strptime(fecha_str, formato)
        except ValueError:
            continue
    print(f"Fecha inválida: {fecha_str}")
    return None  # Retorna None si no se encuentra un formato válido

def procesar_enlace(enlace, tema, noticia_id, processed_titles, processed_contents):
    # Extraer contenido del enlace
    contenido = scrape_contenido(enlace)
    
    # Agregar el enlace al contenido para el procesamiento del resumen
    texto_con_enlace = f"URL: {enlace}\n\n{contenido}"
    
    # Generar resumen en formato JSON incluyendo el enlace y el tema
    resumen = generar_resumen_ia(texto_con_enlace, tema)
    
    # Verificar si el resumen es un diccionario y tiene las claves esperadas
    if not isinstance(resumen, dict) or not all(key in resumen for key in ['title', 'content', 'date']):
        print(f"Error: Resumen no válido o no tiene las claves esperadas: {resumen}")
        return {}

    # Verificar si el resumen es relevante y si la fecha es válida
    if resumen['title'].lower() != "irrelevant" and resumen['content'].lower() != "irrelevant" and resumen['date']:
        
        # Convertir la fecha del resumen a un objeto datetime
        noticia_fecha = convertir_fecha(resumen['date'])
        
        if noticia_fecha:
            # Calcular la fecha límite de los últimos 8 meses
            fecha_limite = datetime.now() - timedelta(days=246)
            
            # Filtrar las noticias por la fecha dentro de los últimos 8 meses
            if noticia_fecha >= fecha_limite:
                agregar_noticia(
                    search_id=tema,
                    noticia_id=noticia_id,
                    contenido=resumen['content'],
                    titulo=resumen['title'],
                    url=enlace,
                    date=resumen['date'],
                    source=resumen.get('source', 'Unknown'),
                    processed_titles=processed_titles,
                    processed_contents=processed_contents
                )
            else:
                print(f"Noticia {noticia_id} es antigua (fecha: {noticia_fecha.strftime('%m-%d-%Y')}), no se guardará en la base de datos.")
        else:
            print(f"Fecha inválida para Noticia {noticia_id}, no se guardará en la base de datos.")
    else:
        print(f"Noticia {noticia_id} clasificada como 'Irrelevant' o sin fecha válida, no se guardará en la base de datos.")
    
    return resumen

def procesar_busqueda(query, batch_size=10, start_index=0):
    enlaces = obtener_enlaces(query)
    contador = start_index + 1
    batch = []
    
    # Conjuntos para mantener los títulos y contenidos ya procesados
    processed_titles = set()
    processed_contents = set()
    
    for enlace in enlaces[start_index:start_index + batch_size]:
        noticia_id = f"Noticia_{contador}"
        print(f"\nProcesando enlace {contador}: {enlace}")
        
        # Procesar cada enlace individualmente pasando el tema, search_id y noticia_id
        resumen = procesar_enlace(enlace, query, noticia_id, processed_titles, processed_contents)
        
        # Verificar si el resumen es un diccionario válido antes de agregarlo al batch
        if isinstance(resumen, dict) and 'title' in resumen and 'content' in resumen:
            batch.append(resumen)  # Agregar resumen al lote actual
        else:
            print(f"Resumen no válido para la noticia {noticia_id}: {resumen}")
            continue  # Continuar con el siguiente enlace si el resumen no es válido
        
        print(f"Resumen {contador}:")
        print(resumen)
        
        contador += 1

    # Asegúrate de que el batch es una lista de diccionarios
    if not all(isinstance(item, dict) for item in batch):
        raise ValueError("El lote de resultados no contiene exclusivamente diccionarios.")

    return batch  # Retornar siempre una lista de diccionarios


def obtener_noticias_guardadas(query):
    try:
        # Referencia a la colección de noticias del tema específico
        noticias_ref = db.collection('Noticias').document(query).collection('noticias_investigadas')
        noticias = noticias_ref.stream()  # Obtiene todas las noticias guardadas
        
        noticias_list = []
        for noticia in noticias:
            noticia_data = noticia.to_dict()  # Convierte el documento a diccionario
            noticia_data['id'] = noticia.id  # Agrega el ID de la noticia
            
            # Convertir la fecha a un objeto datetime para ordenación
            noticia_data['Fecha'] = convertir_fecha(noticia_data['Fecha'])
            if noticia_data['Fecha'] is not None:  # Solo agregar si la fecha es válida
                noticias_list.append(noticia_data)
        
        # Ordenar las noticias por fecha en orden descendente
        noticias_list.sort(key=lambda x: x['Fecha'], reverse=True)

        # Convertir la fecha de vuelta a string para devolver al frontend
        for noticia in noticias_list:
            noticia['Fecha'] = noticia['Fecha'].strftime('%m-%d-%Y')
        
        return noticias_list
    except Exception as e:
        print(f"Error al obtener noticias guardadas: {e}")
        return []
