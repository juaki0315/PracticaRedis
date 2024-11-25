from flask import Flask, render_template, request, redirect, url_for, flash
import redis
import json

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

# URL de Redis en Railway (ajusta esta URL según tu configuración)
redis_url = "redis://default:DUKDTvMPFTVlfAnhnOfCMPBgKPoWWqYv@autorack.proxy.rlwy.net:11870"
redis_client = redis.from_url(redis_url)

# Funciones auxiliares

def get_user_cart(username):
    """Obtiene el carrito del usuario desde Redis."""
    user_data = redis_client.hgetall(username)
    if user_data:
        cesta_data = user_data.get(b'cesta', b'[]').decode('utf-8')  # Decodificar de bytes a string
        try:
            cesta = json.loads(cesta_data)  # Convertir el JSON a una lista de productos
        except json.JSONDecodeError as e:
            flash(f"Error al cargar el carrito: {e}", "error")
            cesta = []  # Si hay un error, devolvemos un carrito vacío
        return {
            'cesta': cesta,
            'importe_total': float(user_data.get(b'importe_total', b'0'))
        }
    return {'cesta': [], 'importe_total': 0}

def save_user_cart(username, cart_data):
    """Guarda el carrito del usuario en Redis."""
    redis_client.hset(username, 'cesta', json.dumps(cart_data['cesta']))  # Guardar como JSON
    redis_client.hset(username, 'importe_total', str(cart_data['importe_total']))  # Guardar importe total como string

def clear_user_cart(username):
    """Vacía el carrito del usuario en Redis."""
    redis_client.hset(username, 'cesta', '[]')  # Vaciar cesta
    redis_client.hset(username, 'importe_total', '0')  # Establecer importe total a 0

def calculate_total(cart):
    """Calcula el total del carrito."""
    return sum(item['cantidad'] * item['precio_unitario'] for item in cart['cesta'])

@app.route('/', methods=['GET', 'POST'])
def login():
    """Muestra el formulario de login."""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username and password:
            flash(f"Bienvenido, {username}!", "success")
            return redirect(url_for('main', username=username))
        else:
            flash("Por favor ingresa un nombre de usuario y contraseña", "error")
    return render_template('login.html')

@app.route('/main/<username>', methods=['GET', 'POST'])
def main(username):
    """Página principal, donde el usuario puede ver y modificar su carrito."""
    if request.method == 'POST':
        cart = get_user_cart(username)
        if 'modify_cart' in request.form:
            for index, item in enumerate(cart['cesta']):
                new_quantity = int(request.form.get(f'quantity_{index}', item['cantidad']))
                item['cantidad'] = new_quantity
            cart['importe_total'] = calculate_total(cart)
            save_user_cart(username, cart)
            flash("Carrito modificado correctamente.", "success")
        else:
            product = request.form['producto']
            quantity = int(request.form['cantidad'])
            price_unit = float(request.form['precio_unitario'])

            if quantity <= 0 or price_unit <= 0:
                flash("Cantidad y precio deben ser mayores que cero.", "error")
                return redirect(url_for('main', username=username))

            # Verificar si el producto ya está en el carrito
            existing_product = next(
                (item for item in cart['cesta'] if item['articulo'].lower() == product.lower()), None
            )
            if existing_product:
                existing_product['cantidad'] += quantity
            else:
                cart['cesta'].append({'articulo': product, 'cantidad': quantity, 'precio_unitario': price_unit})

            cart['importe_total'] = calculate_total(cart)
            save_user_cart(username, cart)
            flash(f"Producto {product} añadido al carrito.", "success")

        return redirect(url_for('main', username=username))

    # Obtener el carrito actual para mostrarlo
    cart = get_user_cart(username)
    return render_template('main.html', username=username, cart=cart)

@app.route('/delete/<username>', methods=['GET', 'POST'])
def delete(username):
    """Permite eliminar productos del carrito."""
    cart = get_user_cart(username)
    if request.method == 'POST':
        if 'delete_all' in request.form:
            clear_user_cart(username)
            flash("Todos los productos han sido eliminados.", "success")
        else:
            selected_items = request.form.getlist('delete_items')
            cart['cesta'] = [
                item for index, item in enumerate(cart['cesta'])
                if str(index) not in selected_items
            ]
            cart['importe_total'] = calculate_total(cart)
            save_user_cart(username, cart)
            flash("Productos seleccionados eliminados.", "success")
        return redirect(url_for('main', username=username))
    return render_template('modify.html', cart=cart, username=username)

@app.route('/clear/<username>')
def clear(username):
    """Vacía el carrito."""
    clear_user_cart(username)
    flash("Carrito vaciado.", "success")
    return redirect(url_for('main', username=username))

@app.route('/logout', methods=['POST'])
def logout():
    """Cierra la sesión del usuario y lo redirige al login."""
    flash("Has cerrado sesión correctamente.", "info")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
