from flask import Flask, render_template, request, redirect, url_for, flash
import redis

app = Flask(__name__)
app.secret_key = "secret_key_for_session"

redis_url = "redis://default:DUKDTvMPFTVlfAnhnOfCMPBgKPoWWqYv@autorack.proxy.rlwy.net:11870"
redis_client = redis.from_url(redis_url)

# Funciones auxiliares
def get_user_cart(username):
    user_data = redis_client.hgetall(username)
    if user_data:
        return {
            'cesta': eval(user_data.get(b'cesta', b'[]')),
            'importe_total': float(user_data.get(b'importe_total', b'0'))
        }
    return {'cesta': [], 'importe_total': 0}

def save_user_cart(username, cart_data):
    redis_client.hset(username, 'cesta', str(cart_data['cesta']))
    redis_client.hset(username, 'importe_total', str(cart_data['importe_total']))

def clear_user_cart(username):
    redis_client.hset(username, 'cesta', '[]')
    redis_client.hset(username, 'importe_total', '0')

def calculate_total(cart):
    return sum(item['cantidad'] * item['precio_unitario'] for item in cart['cesta'])

@app.route('/', methods=['GET', 'POST'])
def login():
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

    cart = get_user_cart(username)
    return render_template('main.html', username=username, cart=cart)

@app.route('/delete/<username>', methods=['GET', 'POST'])
def delete(username):
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
    return render_template('delete.html', cart=cart, username=username)

@app.route('/clear/<username>')
def clear(username):
    clear_user_cart(username)
    flash("Carrito vaciado.", "success")
    return redirect(url_for('main', username=username))

if __name__ == '__main__':
    app.run(debug=True)
