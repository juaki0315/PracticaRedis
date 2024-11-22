from flask import Flask, render_template, request, redirect, url_for, flash
import redis

app = Flask(__name__)
app.secret_key = "secret_key_for_session"  # Necesario para el uso de `flash` en Flask

# Conexión a Redis en Railway
redis_url = "redis://default:DUKDTvMPFTVlfAnhnOfCMPBgKPoWWqYv@autorack.proxy.rlwy.net:11870"
redis_client = redis.from_url(redis_url)

# Funciones para interactuar con Redis
def get_user_cart(username):
    """Obtener el carrito de un usuario desde Redis"""
    user_data = redis_client.hgetall(username)
    if user_data:
        return {
            'cesta': eval(user_data.get('cesta', '[]')),
            'importe_total': float(user_data.get('importe_total', 0))
        }
    return {'cesta': [], 'importe_total': 0}

def save_user_cart(username, cart_data):
    """Guardar el carrito de un usuario en Redis"""
    redis_client.hset(username, 'cesta', str(cart_data['cesta']))
    redis_client.hset(username, 'importe_total', str(cart_data['importe_total']))

def clear_user_cart(username):
    """Vaciar el carrito de un usuario"""
    redis_client.hset(username, 'cesta', '[]')
    redis_client.hset(username, 'importe_total', '0')

# Ruta de la pantalla de login
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username and password:
            cart = get_user_cart(username)
            if cart['cesta']:
                flash(f"Bienvenido de nuevo, {username}!", "success")
            else:
                flash(f"Bienvenido, {username}!", "success")
            return redirect(url_for('main', username=username))
        else:
            flash("Por favor ingresa un nombre de usuario y contraseña", "error")
    
    return render_template('login.html')

# Ruta de la pantalla principal
@app.route('/main/<username>', methods=['GET', 'POST'])
def main(username):
    if request.method == 'POST':
        product = request.form['producto']
        quantity = int(request.form['cantidad'])
        price_unit = float(request.form['precio_unitario'])
        
        # Añadir producto al carrito
        cart = get_user_cart(username)
        item = {'articulo': product, 'cantidad': quantity, 'precio_unitario': price_unit}
        cart['cesta'].append(item)
        cart['importe_total'] += quantity * price_unit
        save_user_cart(username, cart)
        
        flash(f"Producto {product} añadido al carrito", "success")
        return redirect(url_for('main', username=username))
    
    cart = get_user_cart(username)
    return render_template('main.html', username=username, cart=cart)

# Ruta para modificar el carrito
@app.route('/modify/<username>', methods=['GET', 'POST'])
def modify(username):
    cart = get_user_cart(username)
    
    if request.method == 'POST':
        # Modificar carrito
        item_index = int(request.form['item_index'])
        new_quantity = int(request.form['new_quantity'])
        
        cart['cesta'][item_index]['cantidad'] = new_quantity
        cart['cesta'][item_index]['precio_total'] = new_quantity * cart['cesta'][item_index]['precio_unitario']
        
        # Recalcular importe total
        cart['importe_total'] = sum(item['cantidad'] * item['precio_unitario'] for item in cart['cesta'])
        save_user_cart(username, cart)
        
        flash("Carrito actualizado!", "success")
        return redirect(url_for('main', username=username))
    
    return render_template('modify.html', cart=cart, username=username)

# Ruta para vaciar el carrito
@app.route('/clear/<username>')
def clear(username):
    clear_user_cart(username)
    flash("Carrito vaciado.", "success")
    return redirect(url_for('main', username=username))

if __name__ == '__main__':
    app.run(debug=True)
