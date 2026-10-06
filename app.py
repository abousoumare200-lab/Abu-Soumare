from flask import Flask, render_template, redirect, url_for, session, request
import os
from dotenv import load_dotenv

load_dotenv()

PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")

from paypalserversdk.configuration import Environment
from paypalserversdk.http.auth.o_auth_2 import ClientCredentialsAuthCredentials
from paypalserversdk.paypal_serversdk_client import PaypalServersdkClient

from paypalserversdk.models.order_request import OrderRequest
from paypalserversdk.models.checkout_payment_intent import CheckoutPaymentIntent
from paypalserversdk.models.purchase_unit_request import PurchaseUnitRequest
from paypalserversdk.models.amount_with_breakdown import AmountWithBreakdown

paypal_client = PaypalServersdkClient(
    client_credentials_auth_credentials=ClientCredentialsAuthCredentials(
        o_auth_client_id=PAYPAL_CLIENT_ID,
        o_auth_client_secret=PAYPAL_CLIENT_SECRET
    ),
    environment=Environment.SANDBOX
)
import sqlite3
from datetime import datetime
app = Flask(__name__)
app.secret_key = "afrik_mogo_as_mi_clave"

@app.context_processor
def datos_paypal():
    return {"paypal_client_id": PAYPAL_CLIENT_ID}
# ============================================================
# BASE DE DATOS
# ============================================================

DATABASE = "pedidos.db"
def conectar_db():
    conexion = sqlite3.connect(DATABASE)
    conexion.row_factory = sqlite3.Row
    return conexion
def crear_base_datos():

    conexion = conectar_db()

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS pedidos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT NOT NULL,
            direccion TEXT NOT NULL,
            ciudad TEXT NOT NULL,
            total REAL NOT NULL,
            fecha TEXT NOT NULL
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS productos_pedido (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pedido_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            cantidad INTEGER NOT NULL,
            subtotal REAL NOT NULL,
            FOREIGN KEY (pedido_id) REFERENCES pedidos(id)
        )
    """)

    conexion.execute("""
        CREATE TABLE IF NOT EXISTS stock (
            nombre TEXT PRIMARY KEY,
            cantidad INTEGER NOT NULL
        )
    """)

    stock_existente = conexion.execute("SELECT COUNT(*) FROM stock").fetchone()[0]

    if stock_existente == 0:

        stock_inicial = {
            "Traje Agbada Bazin Riche P├║rpura Real": 2,
            "Conjunto Bazin Riche Azul Cobalto": 1,
            "Agbada Imperial Algod├│n Blanco Ceremonial": 1,
            "Set Elegante 3 Piezas Gris Plata": 1,
            "Traje Agbada Bazin Riche Verde Oscuro": 2,
            "Set 3PCS Dashiki Agbada Verde Turquesa": 1,
            "Atuendo Formal Bazin Dashiki Azul Cielo": 2,
        }

        for nombre, cantidad in stock_inicial.items():
            conexion.execute(
                "INSERT INTO stock (nombre, cantidad) VALUES (?, ?)",
                (nombre, cantidad)
            )

    conexion.commit()
    conexion.close()


def obtener_stock_dict():

    conexion = conectar_db()

    filas = conexion.execute("SELECT nombre, cantidad FROM stock").fetchall()

    conexion.close()

    return {fila["nombre"]: fila["cantidad"] for fila in filas}


# ============================================================
# PRODUCTOS
# ============================================================

PRECIOS = {
    "1786308011240": {"nombre": "Traje Agbada Bazin Riche P├║rpura Real", "precio": 55, "talla": "L"},
    "1786308097375": {"nombre": "Conjunto Bazin Riche Azul Cobalto", "precio": 55.25, "talla": "L"},
    "1786308185528": {"nombre": "Agbada Imperial Algod├│n Blanco Ceremonial", "precio": 59, "talla": "L"},
    "1786308218290": {"nombre": "Set Elegante 3 Piezas Gris Plata", "precio": 45.24, "talla": "L"},
    "1786308254107": {"nombre": "Traje Agbada Bazin Riche Verde Oscuro", "precio": 55, "talla": "L"},
    "1786308283918": {"nombre": "Set 3PCS Dashiki Agbada Verde Turquesa", "precio": 49, "talla": "L"},
    "1786308314540": {"nombre": "Atuendo Formal Bazin Dashiki Azul Cielo", "precio": 55, "talla": "L"},
    "1786308155610": {"nombre": "Atuendo Formal Bazin Dashiki Azul Cielo", "precio": 55, "talla": "L"},
}


def obtener_productos():

    carpeta = os.path.join(app.static_folder, "images")

    extensiones = (".jpg", ".jpeg", ".png", ".webp", ".gif")

    stock_dict = obtener_stock_dict()

    vistos = set()

    productos = []

    for archivo in os.listdir(carpeta):

        if archivo.lower().endswith(extensiones):

            clave = os.path.splitext(archivo)[0]

            info = PRECIOS.get(clave, {"nombre": clave, "precio": 50, "talla": "├Ünica"})

            nombre = info["nombre"]

            # Evitar mostrar dos veces el mismo producto (2 fotos, mismo nombre)
            if nombre in vistos:
                continue

            vistos.add(nombre)

            productos.append({
                "nombre": nombre,
                "imagen": archivo,
                "precio": info["precio"],
                "talla": info.get("talla", "├Ünica"),
                "stock": stock_dict.get(nombre, 0)
            })

    return productos


# ============================================================
# TIENDA
# ============================================================

@app.route("/")
def inicio():
    productos = obtener_productos()
    return render_template("index.html", productos=productos)


# ============================================================
# AGREGAR AL CARRITO
# ============================================================

@app.route("/agregar/<nombre>")
def agregar(nombre):

    stock_dict = obtener_stock_dict()
    disponible = stock_dict.get(nombre, 0)

    carrito = session.get("carrito", {})

    cantidad_actual = carrito.get(nombre, 0)

    if cantidad_actual < disponible:
        carrito[nombre] = cantidad_actual + 1
        session["carrito"] = carrito

    return redirect(url_for("carrito"))


# ============================================================
# VER CARRITO
# ============================================================

@app.route("/carrito")
def carrito():

    productos = obtener_productos()

    carrito = session.get("carrito", {})

    if isinstance(carrito, list):

        carrito_nuevo = {}

        for nombre in carrito:
            carrito_nuevo[nombre] = carrito_nuevo.get(nombre, 0) + 1

        carrito = carrito_nuevo

        session["carrito"] = carrito

    productos_carrito = []

    total = 0

    for producto in productos:

        nombre = producto["nombre"]

        if nombre in carrito:

            cantidad = carrito[nombre]

            subtotal = producto["precio"] * cantidad

            productos_carrito.append({
                "nombre": nombre,
                "imagen": producto["imagen"],
                "precio": producto["precio"],
                "cantidad": cantidad,
                "subtotal": subtotal,
                "stock": producto["stock"]
            })

            total += subtotal

    return render_template("carrito.html", productos=productos_carrito, total=total)


# ============================================================
# SUMAR
# ============================================================

@app.route("/sumar/<nombre>")
def sumar(nombre):

    stock_dict = obtener_stock_dict()
    disponible = stock_dict.get(nombre, 0)

    carrito = session.get("carrito", {})

    if nombre in carrito and carrito[nombre] < disponible:
        carrito[nombre] += 1

    session["carrito"] = carrito

    return redirect(url_for("carrito"))


# ============================================================
# RESTAR
# ============================================================

@app.route("/restar/<nombre>")
def restar(nombre):

    carrito = session.get("carrito", {})

    if nombre in carrito:

        carrito[nombre] -= 1

        if carrito[nombre] <= 0:
            del carrito[nombre]

    session["carrito"] = carrito

    return redirect(url_for("carrito"))


# ============================================================
# ELIMINAR
# ============================================================

@app.route("/eliminar/<nombre>")
def eliminar(nombre):

    carrito = session.get("carrito", {})

    if nombre in carrito:
        del carrito[nombre]

    session["carrito"] = carrito

    return redirect(url_for("carrito"))


# ============================================================
# VACIAR CARRITO
# ============================================================

@app.route("/vaciar")
def vaciar():
    session["carrito"] = {}
    return redirect(url_for("inicio"))


# ============================================================
# HACER PEDIDO
# ============================================================

@app.route("/pedido", methods=["GET", "POST"])
def pedido():

    carrito = session.get("carrito", {})

    if not carrito:
        return redirect(url_for("carrito"))

    productos = obtener_productos()
    if not carrito:
        return redirect(url_for("carrito"))

    productos = obtener_productos()

    productos_carrito = []

    total = 0

    for producto in productos:

        nombre = producto["nombre"]

        if nombre in carrito:

            cantidad = carrito[nombre]

            subtotal = producto["precio"] * cantidad

            productos_carrito.append({
                "nombre": nombre,
                "imagen": producto["imagen"],
                "precio": producto["precio"],
                "cantidad": cantidad,
                "subtotal": subtotal
            })

            total += subtotal

    if request.method == "POST":

        nombre_cliente = request.form.get("nombre", "").strip()
        telefono = request.form.get("telefono", "").strip()
        direccion = request.form.get("direccion", "").strip()
        ciudad = request.form.get("ciudad", "").strip()

        if not nombre_cliente or not telefono or not direccion or not ciudad:

            return render_template(
                "pedido.html",
                productos=productos_carrito,
                total=total,
                error="Por favor, completa todos los campos."
            )

        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

        conexion = conectar_db()

        cursor = conexion.execute("""
            INSERT INTO pedidos
            (nombre, telefono, direccion, ciudad, total, fecha)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            nombre_cliente,
            telefono,
            direccion,
            ciudad,
            total,
            fecha
        ))

        pedido_id = cursor.lastrowid

        for producto in productos_carrito:

            conexion.execute("""
                INSERT INTO productos_pedido
                (pedido_id, nombre, precio, cantidad, subtotal)
                VALUES (?, ?, ?, ?, ?)
            """, (
                pedido_id,
                producto["nombre"],
                producto["precio"],
                producto["cantidad"],
                producto["subtotal"]
            ))

            # Descontar del stock
            conexion.execute("""
                UPDATE stock
                SET cantidad = cantidad - ?
                WHERE nombre = ?
            """, (producto["cantidad"], producto["nombre"]))

        conexion.commit()
        conexion.close()

        session["carrito"] = {}

        return render_template(
            "pedido.html",
            productos=[],
            total=total,
            confirmado=True,
            nombre_cliente=nombre_cliente,
            numero_pedido=pedido_id
        )

    return render_template("pedido.html", productos=productos_carrito, total=total)


# ============================================================

# PAYPAL - CREAR ORDEN
# ============================================================
@app.route("/api/paypal/create-order", methods=["POST"])
def crear_orden_paypal():
    carrito = session.get("carrito", {})

    if not carrito:
        return {"error": "El carrito está vacío."}, 400

    datos_cliente = request.get_json(silent=True) or {}

    nombre_cliente = datos_cliente.get("nombre", "").strip()
    telefono = datos_cliente.get("telefono", "").strip()
    direccion = datos_cliente.get("direccion", "").strip()
    ciudad = datos_cliente.get("ciudad", "").strip()
    codigo_postal = datos_cliente.get("codigo_postal", "").strip()

    if (
        not nombre_cliente
        or not telefono
        or not direccion
        or not ciudad
        or not codigo_postal
    ):
        return {
            "error": "Por favor, completa todos los datos del cliente."
        }, 400

    session["datos_cliente_paypal"] = {
        "nombre": nombre_cliente,
        "telefono": telefono,
        "direccion": direccion,
        "ciudad": ciudad,
        "codigo_postal": codigo_postal
    }

    productos = obtener_productos()
    subtotal = 0

    for producto in productos:
        nombre = producto["nombre"]

        if nombre in carrito:
            cantidad = carrito[nombre]
            subtotal += producto["precio"] * cantidad

    # Coste de envío para España peninsular
    coste_envio = 13.90

    total = subtotal + coste_envio
    total = f"{total:.2f}"

    order_request = OrderRequest(
        intent=CheckoutPaymentIntent.CAPTURE,
        purchase_units=[
            PurchaseUnitRequest(
                amount=AmountWithBreakdown(
                    currency_code="EUR",
                    value=total
                )
            )
        ]
    )

    try:
        respuesta = paypal_client.orders.create_order(
            {"body": order_request}
        )

        return {"id": respuesta.body.id}

    except Exception as e:
        return {"error": str(e)}, 500
    
if __name__ == "__main__":
    crear_base_datos()
    app.run(debug=True)