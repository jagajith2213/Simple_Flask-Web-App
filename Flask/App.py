from flask import Flask, request, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy # type: ignore
from sqlalchemy import func, or_, and_ # type: ignore
from datetime import datetime
from urllib.parse import quote_plus

# Note: the Templates and Static folders in the repo use capitalized names.
# Flask's defaults are 'templates' and 'static' (lowercase), so explicitly set them.
app = Flask(__name__, template_folder='Templates', static_folder='Static')

# Build the DB URI safely by URL-encoding the password (or use environment variables).
db_user = 'root'
db_password = 'Jaga@23'
db_host = 'localhost'
db_name = 'Inventory'
encoded_password = quote_plus(db_password)
app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{db_user}:{encoded_password}@{db_host}/{db_name}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Product(db.Model):
    product_id = db.Column(db.VARCHAR(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Location(db.Model):
    location_id = db.Column(db.VARCHAR(50), primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class ProductMovement(db.Model):
    movement_id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    from_location = db.Column(db.String(50), db.ForeignKey('location.location_id'))
    to_location = db.Column(db.String(50), db.ForeignKey('location.location_id'))
    product_id = db.Column(db.VARCHAR(50), db.ForeignKey('product.product_id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)

# Note: create tables when running the app (inside __main__) to avoid attempting
# a DB connection at import time (which makes debugging harder).

# Routes for Products
@app.route('/', methods=['GET'])
def list_products():
    productss = Product.query.all()
    return render_template('products.html', products=productss)

@app.route('/product/add', methods=['GET', 'POST'])
def add_product():
    if request.method == 'POST':
        product_id = request.form['product_id']
        name = request.form['name']
        if Product.query.get(product_id):
            return 'Product ID already exists', 400
        product = Product(product_id=product_id, name=name)
        db.session.add(product)
        db.session.commit()
        return redirect(url_for('list_products'))
    return render_template('add_product.html')

@app.route('/product/edit/<product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    product = Product.query.get_or_404(product_id)
    if request.method == 'POST':
        product.name = request.form['name']
        db.session.commit()
        return redirect(url_for('list_products'))
    return render_template('edit_product.html', product=product)


@app.route('/product/delete/<product_id>', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)
    # remove movements referencing this product first to avoid FK errors
    ProductMovement.query.filter_by(product_id=product_id).delete()
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for('list_products'))

# Routes for Locations
@app.route('/locations', methods=['GET'])
def list_locations():
    locations = Location.query.all()
    return render_template('locations.html', locations=locations)

@app.route('/location/add', methods=['GET', 'POST'])
def add_location():
    if request.method == 'POST':
        location_id = request.form['location_id']
        name = request.form['name']
        if Location.query.get(location_id):
            return 'Location ID already exists', 400
        location = Location(location_id=location_id, name=name)
        db.session.add(location)
        db.session.commit()
        return redirect(url_for('list_locations'))
    return render_template('add_location.html')

@app.route('/location/edit/<location_id>', methods=['GET', 'POST'])
def edit_location(location_id):
    location = Location.query.get_or_404(location_id)
    if request.method == 'POST':
        location.name = request.form['name']
        db.session.commit()
        return redirect(url_for('list_locations'))
    return render_template('edit_location.html', location=location)


@app.route('/location/delete/<location_id>', methods=['POST'])
def delete_location(location_id):
    location = Location.query.get_or_404(location_id)
    # delete movements that reference this location (either from or to)
    ProductMovement.query.filter(
        (ProductMovement.from_location == location.location_id) | (ProductMovement.to_location == location.location_id)
    ).delete(synchronize_session=False)
    db.session.delete(location)
    db.session.commit()
    return redirect(url_for('list_locations'))

# Routes for ProductMovements
@app.route('/movements', methods=['GET'])
def list_movements():
    movements = ProductMovement.query.all()
    return render_template('movements.html', movements=movements)

@app.route('/movement/add', methods=['GET', 'POST'])
def add_movement():
    products = Product.query.all()
    locations = Location.query.all()
    if request.method == 'POST':
        from_location = request.form['from_location'] if request.form['from_location'] else None
        to_location = request.form['to_location'] if request.form['to_location'] else None
        if not from_location and not to_location:
            return 'At least one of from_location or to_location must be provided', 400
        product_id = request.form['product_id']
        qty = int(request.form['qty'])
        movement = ProductMovement(from_location=from_location, to_location=to_location, product_id=product_id, qty=qty)
        db.session.add(movement)
        db.session.commit()
        return redirect(url_for('list_movements'))
    return render_template('add_movement.html', products=products, locations=locations)

@app.route('/movement/edit/<int:movement_id>', methods=['GET', 'POST'])
def edit_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)
    products = Product.query.all()
    locations = Location.query.all()
    if request.method == 'POST':
        movement.from_location = request.form['from_location'] if request.form['from_location'] else None
        movement.to_location = request.form['to_location'] if request.form['to_location'] else None
        if not movement.from_location and not movement.to_location:
            return 'At least one of from_location or to_location must be provided', 400
        movement.product_id = request.form['product_id']
        movement.qty = int(request.form['qty'])
        db.session.commit()
        return redirect(url_for('list_movements'))
    return render_template('edit_movement.html', movement=movement, products=products, locations=locations)


@app.route('/movement/delete/<int:movement_id>', methods=['POST'])
def delete_movement(movement_id):
    movement = ProductMovement.query.get_or_404(movement_id)
    db.session.delete(movement)
    db.session.commit()
    return redirect(url_for('list_movements'))

# Report Route
@app.route('/report', methods=['GET'])
def report():
    # Simpler, resilient approach: load movements into Python and aggregate.
    # This avoids complex SQL that can be sensitive to FK types or DB differences.
    movements = ProductMovement.query.order_by(ProductMovement.timestamp).all()
    products = {p.product_id: p for p in Product.query.all()}
    locations = {l.location_id: l for l in Location.query.all()}

    # structure: balances[location_id][product_id] = {'qty': int, 'last_movement': datetime}
    balances = {}

    for m in movements:
        # handle incoming (to_location)
        if m.to_location:
            loc = m.to_location
            prod = m.product_id
            balances.setdefault(loc, {}).setdefault(prod, {'qty': 0, 'last_movement': None})
            balances[loc][prod]['qty'] += int(m.qty)
            if not balances[loc][prod]['last_movement'] or (m.timestamp and m.timestamp > balances[loc][prod]['last_movement']):
                balances[loc][prod]['last_movement'] = m.timestamp

        # handle outgoing (from_location)
        if m.from_location:
            loc = m.from_location
            prod = m.product_id
            balances.setdefault(loc, {}).setdefault(prod, {'qty': 0, 'last_movement': None})
            balances[loc][prod]['qty'] -= int(m.qty)
            if not balances[loc][prod]['last_movement'] or (m.timestamp and m.timestamp > balances[loc][prod]['last_movement']):
                balances[loc][prod]['last_movement'] = m.timestamp

    # Convert balances dict into template-friendly list grouped by Location
    balances_by_location = []
    for loc_id, prod_map in sorted(balances.items()):
        location_obj = locations.get(loc_id)
        group = {'location': location_obj or {'location_id': loc_id, 'name': loc_id}, 'items': [], 'subtotal': 0}
        for prod_id, info in sorted(prod_map.items()):
            qty = info['qty']
            if qty == 0:
                continue
            product_obj = products.get(prod_id)
            group['items'].append({'product': product_obj or {'product_id': prod_id, 'name': prod_id}, 'qty': qty, 'last_movement': info['last_movement']})
            try:
                group['subtotal'] += int(qty)
            except Exception:
                pass
        if group['items']:
            balances_by_location.append(group)

    return render_template('report.html', balances_by_location=balances_by_location)

if __name__ == '__main__':
    # Create tables at startup (inside app context) so we avoid import-time DB connection
    # and ensure missing tables are created automatically when the app is run.
    with app.app_context():
        try:
            db.create_all()
            print('Database tables created (if they did not exist).')
        except Exception as e:
            # Print to console — don't crash the server; the error will still appear in logs.
            print('Warning: could not create tables at startup:', e)

    app.run(debug=True)