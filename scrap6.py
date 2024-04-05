import requests
from bs4 import BeautifulSoup
import re
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderUnavailable
import csv
import os

def obtener_coordenadas(direccion, intentos = 3):
    try:
        geolocalizador = Nominatim(user_agent="prueba1") # Reemplaza "nombre_de_usuario" con un nombre de usuario único
        ubicacion = geolocalizador.geocode(direccion)
        if ubicacion:
            return (ubicacion.latitude, ubicacion.longitude)
        else:
            return None
    except (GeocoderTimedOut, GeocoderUnavailable):
        if intentos > 0:
            print(f"Intento de geocodificación fallido para la dirección: {direccion}. Reintentando...")
            return obtener_coordenadas(direccion, intentos=intentos-1)
        else:
            print(f"No se pudieron obtener las coordenadas para la dirección: {direccion} después de varios intentos.")
            return None
    except Exception as e:
        print(f"Ocurrió un error inesperado al geocodificar la dirección {direccion}: {e}")
        return None
    
# Lista para almacenar los eventos
eventos = []

# URL del sitio web a scrapear
url = 'https://www.visitvalencia.com/agenda-valencia'


# Realiza la solicitud HTTP al servidor
response = requests.get(url)

# Verifica si la solicitud fue exitosa (código de estado 200)
if response.status_code == 200:
    
    # Parsea el contenido HTML de la página web con BeautifulSoup
    soup = BeautifulSoup(response.text, 'html.parser')

    # Encuentra los elementos HTML que contienen la información que necesitas
    enlaces_eventos = soup.findAll('a', class_='visually-hidden card__link')

    contador_id = 0

    for enlace in enlaces_eventos:
        # Construye la URL completa del evento
        url_evento = 'https://www.visitvalencia.com' + enlace['href']
        
        # Realiza una solicitud HTTP al evento
        response_evento = requests.get(url_evento)
        
        # Verifica si la solicitud fue exitosa (código de estado 200)
        if response_evento.status_code == 200:
            # Parsea el contenido HTML de la página de evento con BeautifulSoup
            soup_evento = BeautifulSoup(response_evento.text, 'html.parser')
            
            # Construir el objeto de evento
            evento = {}

            #titulo
            titulo = soup_evento.find('h1', class_='heading').text.strip()

            # Comprobar si el evento ya existe en la lista de eventos
            if any(e['Titulo'] == titulo for e in eventos):
                print(f"El evento '{titulo}' ya existe. Se omitirá.")
                continue

            # fecha
            fecha_inicio = soup_evento.find('b', string='De:').find_next('p').text.strip()
            fecha_fin = soup_evento.find('b', string='A:').find_next('p').text.strip()

            #descripcion
            etiqueta_div = soup_evento.find('div', class_='text-long')
            # Extrae el texto de la descripción del evento
            descripcion_evento = etiqueta_div.get_text(separator=' ').strip()

            #categoria
            etiqueta_p = soup_evento.find('p', class_='paragraph heading--secondary article__subtitle')

            # Extrae el texto de la categoría del evento
            categoria_evento = etiqueta_p.get_text().strip()

            nombre_categoria = categoria_evento.split(':')[-1].strip().rstrip('.')

            try:
                #lugar
                etiqueta_lugar = soup_evento.find('div', class_ = "map__address").find('p').text.strip()

                codigo_postal_regex = re.compile(r'\b\d{5}\b')

                # Buscar el código postal en la dirección
                codigo_postal_match = codigo_postal_regex.search(etiqueta_lugar)

                if codigo_postal_match:
                    # Si se encuentra el código postal, extraerlo
                    codigo_postal = codigo_postal_match.group()
                    # Extraer la dirección quitando el código postal
                    direccion = etiqueta_lugar.replace(codigo_postal, '').strip(', ')
                else:
                    # Si no se encuentra el código postal, asignar la dirección completa y código postal como None
                    direccion = etiqueta_lugar
                    codigo_postal = "No disponible"

            except AttributeError:
                direccion = "No disponible"

            try:
                # precio
                etiqueta_precio = soup_evento.find('b', string='Precio').find_next('p').text.strip()
                precio_numero = re.search(r'\d+(?:,\d+)?', etiqueta_precio)
                precio = float(precio_numero.group().replace(',', '.')) if precio_numero else None
                #precio = float(precio_numero.group()) if precio_numero else None   
                
            except AttributeError:
                # Si no se encuentra la etiqueta de precio, asigna un valor por defecto
                precio = "No disponible"


            '''
            print('El titulo del evento es : ' + titulo)
            # Imprime las fechas del evento
            print("Fecha de inicio:", fecha_inicio)
            print("Fecha de fin:", fecha_fin)

            print("La descripcion del evento es : " + descripcion_evento)

            print("La categoría es : " + nombre_categoria)
            
            print("La dirección es : " + direccion)
            '''
            coordenadas = obtener_coordenadas(direccion)
            if coordenadas:
                evento['Coordenada X'] = coordenadas[0]
                evento['Coordenada Y'] = coordenadas[1]
            else:
                print(f"No se pudieron obtener las coordenadas para la dirección: {direccion}")
                evento['Coordenada X'] = None
                evento['Coordenada Y'] = None
            '''
            if coordenadas:
                print("Las coordenadas de la dirección {} son: Latitud {}, Longitud {}".format(direccion, coordenadas[0], coordenadas[1]))
            else:
                print("No se pudieron obtener las coordenadas para la dirección:", direccion)

            print("El CP es : " + codigo_postal)

            print("El precio es : " + str(precio))
            print()
            '''
            # Asigna el ID actual al evento
            evento['ID'] = contador_id
    
            # Incrementa el contador para el próximo evento
            contador_id += 1
            evento['Titulo'] = titulo
            evento['Fecha Inicio'] = fecha_inicio
            evento['Fecha Fin'] = fecha_fin
            evento['Descripción'] = descripcion_evento
            evento['Categoría'] = nombre_categoria
            evento['Dirección'] = direccion
            evento['Código Postal'] = codigo_postal
            evento['Precio'] = precio



            # Agregar el evento a la lista de eventos
            eventos.append(evento)
            print('Evento con título: ' + evento['Titulo'] + ' Añadido')

            # Persiste los atributos en la base de datos de Supabase
            # Aquí debes adaptar este paso para que se ajuste a tu esquema de base de datos en Supabase
            #supabase.table('<nombre_de_tabla>').insert({'titulo': titulo, 'fecha': fecha, 'descripcion': descripcion}).execute()
            
            #print(f'Evento persistido en Supabase: {titulo}')
            
        else:
            print(f'Error al acceder a la página del evento. Código de estado: {response_evento.status_code}')    

else:
    print(f'Error al acceder a la página. Código de estado: {response.status_code}')


# Nombre del archivo CSV donde se guardarán los eventos
nombre_archivo_csv = 'eventos.csv'

# Encabezados para el archivo CSV
encabezados = ['ID', 'Titulo', 'Fecha Inicio', 'Fecha Fin', 'Descripción', 'Categoría', 'Dirección', 'Coordenada X', 'Coordenada Y', 'Código Postal', 'Precio']

# Verificar si el archivo CSV ya existe
if os.path.exists(nombre_archivo_csv):
    # Si el archivo ya existe, cargar los eventos existentes para verificar duplicados
    eventos_existentes = []
    with open(nombre_archivo_csv, mode='r', newline='', encoding='utf-8') as archivo_csv:
        lector_csv = csv.DictReader(archivo_csv)
        for row in lector_csv:
            eventos_existentes.append(row['Titulo'])

    # Filtrar los nuevos eventos para evitar duplicados
    eventos_filtrados = [evento for evento in eventos if evento['Titulo'] not in eventos_existentes]
else:
    eventos_filtrados = eventos

# Guardar eventos en un archivo CSV
with open(nombre_archivo_csv, mode='a', newline='', encoding='utf-8') as archivo_csv:
    escritor_csv = csv.DictWriter(archivo_csv, fieldnames=encabezados)
    
    # Escribir los eventos filtrados en el archivo CSV
    for evento in eventos_filtrados:
        # Envolver la descripción entre comillas dobles
        evento['Descripción'] = f'"{descripcion_evento}"'

        escritor_csv.writerow(evento)