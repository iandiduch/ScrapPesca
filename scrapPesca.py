import os
import requests
import pymysql
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from time import sleep
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Conexión a la base de datos
db = pymysql.connect(
    host="localhost",
    user="root",
    database="dbsistema"
)

cursor = db.cursor()

# Configuración del driver
options = webdriver.ChromeOptions()
options.add_argument("--headless")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# Función para descargar la imagen
def descargar_imagen(url, nombre_archivo):
    carpeta_imagenes = os.path.expanduser("D:\Datos\Escritorio\imagenes")
    
    if not os.path.exists(carpeta_imagenes):
        os.makedirs(carpeta_imagenes)
        
    ruta_imagen = os.path.join(carpeta_imagenes, nombre_archivo)
    
    img_data = requests.get(url).content
    
    with open(ruta_imagen, 'wb') as handler:
        handler.write(img_data)
        
    return nombre_archivo

# Función para insertar o devolver ID de categoría
def obtener_o_insertar_categoria(nombre):
    cursor.execute("SELECT idcategoria FROM categoria WHERE nombre = %s", (nombre,))
    categoria = cursor.fetchone()
    
    if categoria:
        return categoria[0]
    else:
        cursor.execute("INSERT INTO categoria (nombre, descripcion, condicion) VALUES (%s, NULL, 1)", (nombre,))
        db.commit()
        return cursor.lastrowid

# Función para insertar o devolver ID de marca
def obtener_o_insertar_marca(nombre):
    cursor.execute("SELECT idmarca FROM marca WHERE nombre = %s", (nombre,))
    marca = cursor.fetchone()
    if marca:
        return marca[0]
    else:
        cursor.execute("INSERT INTO marca (nombre, condicion) VALUES (%s, 1)", (nombre,))
        db.commit()
        return cursor.lastrowid
        
# Función para limpiar el nombre del archivo
def limpiar_nombre_archivo(nombre):
    return re.sub(r'[<>:"/\\|?*]', '_', nombre)


# Función para procesar cada producto
def procesar_producto(li_element):
    # Extraer datos de producto
    imagen_url = li_element.find_element(By.CSS_SELECTOR, ".wc-product-media img").get_attribute("src")
    categoria = li_element.find_element(By.CSS_SELECTOR, ".wc-product__category a").text
    titulo = li_element.find_element(By.CSS_SELECTOR, ".wc-product__title a").text
    
    try:
        precio = li_element.find_element(By.CSS_SELECTOR, ".wc-product__price .woocommerce-Price-amount").text.replace("$", "").replace(",", "")
    except NoSuchElementException:
        precio = "0"  # O asigna otro valor predeterminado si lo prefieres
    
    descripcion_completa = ""

    # Obtener el HTML de la descripción del producto
    try:
        descripcion_html = li_element.find_element(By.CSS_SELECTOR, ".wc-product__part.wc-product__description.hide-in-grid.hide-in-list").get_attribute("innerHTML")
        soup = BeautifulSoup(descripcion_html, 'html.parser')

        # Encuentra el div que contiene la descripción
        descripcion_div = soup.find("div", class_="woocommerce-loop-product__desc")

        # Extrae el texto de la descripción si existe
        if descripcion_div:
            descripcion_completa = descripcion_div.get_text(separator="\n", strip=True)
        else:
            print("No se encontró el div con la clase 'woocommerce-loop-product__desc'")
    except Exception as e:
        print("Error al obtener la descripción:", e)

    # Extraer la marca si el texto "Marca:" está presente
    marca_texto = "Sin especificar"
    if "Marca:" in descripcion_completa:
        try:
            marca_texto = descripcion_completa.split("Marca:")[1].split("–")[0].strip()
            
        except IndexError:
            print("No se pudo extraer la marca del producto.")
    else:
        print("La marca no está presente en la descripción.")

    # Insertar o recuperar IDs
    id_categoria = obtener_o_insertar_categoria(categoria)
    marca_texto = marca_texto[:45]
    id_marca = obtener_o_insertar_marca(marca_texto)

    # Descargar imagen y obtener nombre del archivo
    nombre_imagen = limpiar_nombre_archivo(f"{titulo.replace(' ', '_')}.jpg")
    descargar_imagen(imagen_url, nombre_imagen)

    descripcion_completa = descripcion_completa[:255]
    # Insertar artículo
    cursor.execute("INSERT INTO articulo (idcategoria, codigo, nombre, stock, descripcion, imagen, condicion, marca) VALUES (%s, 0, %s, 0, %s, %s, 1, %s)", 
                   (id_categoria, titulo, descripcion_completa, nombre_imagen, id_marca))
    db.commit()
    id_articulo = cursor.lastrowid

    # Calcular y almacenar en detalle_ingreso
    precio_venta = float(precio)
    precio_compra = precio_venta * 0.6
    cursor.execute("INSERT INTO detalle_ingreso (idingreso, idarticulo, cantidad, precio_compra, precio_venta) VALUES (1, %s, 10, %s, %s)", 
                   (id_articulo, precio_compra, precio_venta))
    db.commit()


# Lista de URLs base para cada categoría
categorias = [
    "https://shopdepesca.com.ar/categoria-producto/camping/accesorios-de-camping/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/anafes-hornallas-etc/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/bolsas-de-dormir-colchones-etc/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/bolsos-mochilas-etc/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/carpas-gazebos-etc/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/conservadoras-vasos-y-termos/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/cuchilleria/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/camping/linternas-y-faroles/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/canas/baitcasting/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/canas/embarcado/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/canas/feeder/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/canas/lance/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/canas/spinning/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/canas/telescopicas/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/indumentaria-waders-etc/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/nautica-y-kayaks/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/nylon-multifilamento-y-fluorocarbono/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/reeles/frontales/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/reeles/rotativos-perfil-alto/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/reeles/baitcasting-bajo-rerfil/page/{pagina}/",
    "https://shopdepesca.com.ar/categoria-producto/senuelos-y-artificiales/page/{pagina}/"
]

# Recorrer cada categoría
for categoria in categorias:
    pagina = 1  # Empezar desde la página 1 para cada categoría
    while True:
        # Formar la URL de la página actual
        url = categoria.format(pagina=pagina)
        driver.get(url)
        sleep(5)  # Esperar a que cargue la página

        # Buscar productos en la página actual
        productos = driver.find_elements(By.CSS_SELECTOR, "ul.products li.product")
        if not productos:
            break  # Si no hay productos, salimos del bucle de la categoría

        # Procesar cada producto en la página actual
        for producto in productos:
            procesar_producto(producto)

        # Avanzar a la siguiente página
        pagina += 1


# Cerrar conexión
driver.quit()
cursor.close()
db.close()
