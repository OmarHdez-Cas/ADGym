import os
import sys
import math
import threading
import webview
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from sqlalchemy.orm import joinedload
from sqlalchemy import func
from database import db, User, Client, MembershipPlan, Membership, Product, Sale, SaleItem

if getattr(sys, 'frozen', False):
    template_folder = os.path.join(sys._MEIPASS, 'templates')
    static_folder = os.path.join(sys._MEIPASS, 'static')
    app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
else:
    app = Flask(__name__)

home_dir = os.path.expanduser('~')
app_dir = os.path.join(home_dir, '.santa_fuerza')
if not os.path.exists(app_dir):
    os.makedirs(app_dir)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(app_dir, 'gym_database.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.environ.get('SECRET_KEY', 'dev_key_santa_fuerza_local')

db.init_app(app)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            return jsonify({'success': False, 'message': 'Acceso restringido a administradores'}), 403
        return f(*args, **kwargs)
    return decorated_function

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

with app.app_context():
    db.create_all()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if User.query.count() == 0:
        return redirect(url_for('setup'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = User.query.filter_by(username=username, password=password).first()
        if user:
            session['user_id'] = user.id
            session['user_name'] = user.name
            session['user_role'] = user.role
            return jsonify({'success': True})
        return jsonify({'success': False, 'message': 'Usuario o contraseña incorrectos'}), 401
    return render_template('login.html')

@app.route('/setup', methods=['GET', 'POST'])
def setup():
    if User.query.count() > 0:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        name = request.form.get('name')
        username = request.form.get('username')
        password = request.form.get('password')
        
        admin = User(name=name, username=username, password=password, role='admin')
        db.session.add(admin)
        db.session.commit()
        
        session['user_id'] = admin.id
        session['user_name'] = admin.name
        session['user_role'] = admin.role
        return jsonify({'success': True})
        
    return render_template('setup.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    if User.query.count() == 0:
        return redirect(url_for('setup'))
    return render_template('base.html', user_name=session.get('user_name'), user_role=session.get('user_role'))

@app.route('/view/<view_name>')
@login_required
def get_view(view_name):
    allowed_views = ['dashboard', 'clients', 'pos', 'inventory', 'plans', 'employees', 'reports']
    if view_name in allowed_views:
        return render_template(f'{view_name}.html')
    return "Vista no encontrada", 404

@app.route('/api/dashboard/stats')
def dashboard_stats():
    now = datetime.now()
    five_days_from_now = now + timedelta(days=5)

    latest_mem = db.session.query(
        Membership.client_id,
        func.max(Membership.created_at).label('max_created')
    ).group_by(Membership.client_id).subquery()

    memberships = db.session.query(Membership).join(
        latest_mem,
        db.and_(
            Membership.client_id == latest_mem.c.client_id,
            Membership.created_at == latest_mem.c.max_created
        )
    ).all()

    active_memberships = 0
    expiring_memberships = 0
    expired_memberships = 0

    for mem in memberships:
        if mem.end_date < now:
            expired_memberships += 1
        else:
            active_memberships += 1
            if mem.end_date <= five_days_from_now:
                expiring_memberships += 1

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_income = db.session.query(func.coalesce(func.sum(Sale.total), 0.0)).filter(
        Sale.created_at >= start_of_day
    ).scalar()

    return jsonify({
        'active_memberships': active_memberships,
        'expiring_memberships': expiring_memberships,
        'today_income': today_income,
        'expired_memberships': expired_memberships
    })


@app.route('/api/clients', methods=['GET', 'POST'])
@login_required
def api_clients():
    if request.method == 'POST':
        data = request.json
        new_client = Client(name=data['name'], phone='', email='', notes='')
        db.session.add(new_client)
        db.session.flush()

        start_date_str = data.get('start_date')
        now = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now()

        plan_id = data.get('plan_id')
        if plan_id:
            plan = MembershipPlan.query.get(plan_id)
            if plan:
                end_date = now + timedelta(days=plan.duration_days)
                membership = Membership(
                    client_id=new_client.id,
                    plan_id=plan.id,
                    start_date=now,
                    end_date=end_date,
                    price_paid=plan.price
                )
                db.session.add(membership)
                db.session.flush()

                sale = Sale(
                    total=plan.price,
                    user_id=session.get('user_id'),
                    client_id=new_client.id,
                    created_at=datetime.now()
                )
                db.session.add(sale)
                db.session.flush()

                sale_item = SaleItem(
                    sale_id=sale.id,
                    product_id=None,
                    name=f"Membresía: {plan.name}",
                    quantity=1,
                    price=plan.price
                )
                db.session.add(sale_item)

        db.session.commit()
        return jsonify({'success': True, 'id': new_client.id})

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', 'all', type=str)
    
    query = Client.query.order_by(Client.id.desc())

    if search:
        query = query.filter(Client.name.ilike(f'%{search}%'))

    total = query.count()
    client_ids = [c.id for c in query.offset((page - 1) * per_page).limit(per_page).all()]
    clients = Client.query.filter(Client.id.in_(client_ids)).options(
        joinedload(Client.memberships).joinedload(Membership.plan)
    ).order_by(Client.id.desc()).all()

    data = []
    now = datetime.now()
    for c in clients:
        active_mem = next(
            (m for m in sorted(c.memberships, key=lambda m: m.end_date, reverse=True)
             if m.end_date >= now),
            None
        )

        mem_name = active_mem.plan.name if (active_mem and active_mem.plan) else 'Sin plan'
        end_date = active_mem.end_date.strftime('%Y-%m-%d') if active_mem else '-'
        is_expired = not active_mem

        if status == 'active' and is_expired:
            continue
        if status == 'expired' and not is_expired:
            continue

        data.append({
            'id': c.id,
            'name': c.name,
            'created_at': c.created_at.strftime('%Y-%m-%d'),
            'membership': mem_name,
            'expires': end_date,
            'plan_id': active_mem.plan_id if active_mem else '',
            'start_date': active_mem.start_date.strftime('%Y-%m-%d') if active_mem else ''
        })
    
    return jsonify({
        'clients': data,
        'total': total,
        'page': page,
        'pages': math.ceil(total / per_page)
    })

@app.route('/api/clients/<int:client_id>', methods=['PUT', 'DELETE'])
@login_required
def client_detail(client_id):
    client = Client.query.get_or_404(client_id)
    if request.method == 'PUT':
        data = request.json
        client.name = data.get('name', client.name)

        plan_id = data.get('plan_id')
        if plan_id:
            plan = MembershipPlan.query.get(plan_id)
            if plan:
                start_date_str = data.get('start_date')
                now = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else datetime.now()
                end_date = now + timedelta(days=plan.duration_days)

                active_mem = Membership.query.filter_by(client_id=client.id).order_by(Membership.created_at.desc()).first()
                old_plan_id = str(active_mem.plan_id) if active_mem else None
                old_start_date = active_mem.start_date.strftime('%Y-%m-%d') if active_mem else None

                if old_plan_id != str(plan.id) or old_start_date != start_date_str:
                    membership = Membership(
                        client_id=client.id,
                        plan_id=plan.id,
                        start_date=now,
                        end_date=end_date,
                        price_paid=plan.price
                    )
                    db.session.add(membership)
                    db.session.flush()

                    sale = Sale(
                        total=plan.price,
                        user_id=session.get('user_id'),
                        client_id=client.id,
                        created_at=datetime.now()
                    )
                    db.session.add(sale)
                    db.session.flush()

                    sale_item = SaleItem(
                        sale_id=sale.id,
                        product_id=None,
                        name=f"Membresía: {plan.name}",
                        quantity=1,
                        price=plan.price
                    )
                    db.session.add(sale_item)

        db.session.commit()
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        db.session.delete(client)
        db.session.commit()
        return jsonify({'success': True})


@app.route('/api/products', methods=['GET', 'POST'])
@login_required
def api_products():
    if request.method == 'POST':
        data = request.json
        new_prod = Product(
            name=data['name'],
            price=data['price'],
            stock=0,
            min_stock=0
        )
        db.session.add(new_prod)
        db.session.commit()
        return jsonify({'success': True})

    products = Product.query.order_by(Product.name).all()
    data = []
    for p in products:
        data.append({
            'id': p.id,
            'name': p.name,
            'barcode': p.barcode,
            'price': p.price,
            'stock': p.stock,
            'min_stock': p.min_stock
        })
    return jsonify(data)

@app.route('/api/products/<int:product_id>', methods=['PUT', 'DELETE'])
@login_required
def product_detail(product_id):
    prod = Product.query.get_or_404(product_id)
    if request.method == 'PUT':
        data = request.json
        prod.name = data.get('name', prod.name)
        prod.price = data.get('price', prod.price)
        db.session.commit()
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        db.session.delete(prod)
        db.session.commit()
        return jsonify({'success': True})


@app.route('/api/plans', methods=['GET', 'POST'])
@login_required
def api_plans():
    if request.method == 'POST':
        data = request.json
        new_plan = MembershipPlan(
            name=data['name'],
            duration_days=data['duration_days'],
            price=data['price']
        )
        db.session.add(new_plan)
        db.session.commit()
        return jsonify({'success': True})

    plans = MembershipPlan.query.all()
    data = []
    for p in plans:
        data.append({
            'id': p.id,
            'name': p.name,
            'duration_days': p.duration_days,
            'price': p.price
        })
    return jsonify(data)

@app.route('/api/plans/<int:plan_id>', methods=['PUT', 'DELETE'])
@login_required
def plan_detail(plan_id):
    plan = MembershipPlan.query.get_or_404(plan_id)
    if request.method == 'PUT':
        data = request.json
        plan.name = data.get('name', plan.name)
        plan.duration_days = data.get('duration_days', plan.duration_days)
        plan.price = data.get('price', plan.price)
        db.session.commit()
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        db.session.delete(plan)
        db.session.commit()
        return jsonify({'success': True})


@app.route('/api/employees', methods=['GET', 'POST'])
@admin_required
def api_employees():
    if request.method == 'POST':
        data = request.json
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'success': False, 'message': 'El usuario ya existe'}), 400
            
        new_user = User(
            name=data['name'],
            username=data['username'],
            password=data['password'],
            role=data['role']
        )
        db.session.add(new_user)
        db.session.commit()
        return jsonify({'success': True})

    employees = User.query.all()
    data = []
    for e in employees:
        data.append({
            'id': e.id,
            'name': e.name,
            'username': e.username,
            'role': e.role
        })
    return jsonify(data)

@app.route('/api/employees/<int:user_id>', methods=['PUT', 'DELETE'])
@admin_required
def employee_detail(user_id):
    user = User.query.get_or_404(user_id)
    if request.method == 'PUT':
        data = request.json
        user.name = data.get('name', user.name)
        user.username = data.get('username', user.username)
        user.role = data.get('role', user.role)
        if 'password' in data and data['password']:
            user.password = data['password']
        db.session.commit()
        return jsonify({'success': True})
    elif request.method == 'DELETE':
        db.session.delete(user)
        db.session.commit()
        return jsonify({'success': True})


@app.route('/api/sales', methods=['POST'])
@login_required
def process_sale():
    data = request.json
    items = data.get('items', [])
    if not items:
        return jsonify({'success': False, 'message': 'Carrito vacío'}), 400

    total_sale = 0.0
    sale = Sale(total=0.0, user_id=session.get('user_id'))
    db.session.add(sale)
    db.session.flush()

    for item in items:
        p_id = None
        if item.get('product_id'):
            prod = Product.query.get(item['product_id'])
            if prod:
                p_id = prod.id
                if prod.stock > 0:
                    prod.stock -= item['qty']
            else:
                p_id = None

        subtotal = item['qty'] * item['price']
        total_sale += subtotal

        sale_item = SaleItem(
            sale_id=sale.id,
            product_id=p_id,
            name=item.get('name', 'Desconocido'),
            quantity=item['qty'],
            price=item['price']
        )
        db.session.add(sale_item)

    sale.total = total_sale
    db.session.commit()
    return jsonify({'success': True, 'sale_id': sale.id})


@app.route('/api/reports', methods=['GET'])
@login_required
def api_reports():
    emp_id = request.args.get('employee_id')
    start_str = request.args.get('start_date')
    end_str = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)

    query = Sale.query.options(
        joinedload(Sale.items),
        joinedload(Sale.user)
    )

    if emp_id and emp_id != 'all':
        query = query.filter(Sale.user_id == emp_id)

    if start_str and end_str:
        try:
            start_date = datetime.strptime(start_str, '%Y-%m-%d')
            end_date = datetime.strptime(end_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            query = query.filter(Sale.created_at >= start_date, Sale.created_at <= end_date)
        except ValueError:
            pass

    total_revenue = db.session.query(func.coalesce(func.sum(Sale.total), 0.0)).filter(
        Sale.id.in_(query.with_entities(Sale.id))
    ).scalar()

    total_count = query.count()
    sales = query.order_by(Sale.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    results = []
    for s in sales:
        has_products = any(i.product_id is not None for i in s.items)
        has_memberships = any(i.name and 'Membresía' in i.name for i in s.items)
        has_visits = any(i.product_id is None and (not i.name or 'Membresía' not in i.name) for i in s.items)

        types = []
        if has_products: types.append("Productos")
        if has_memberships: types.append("Membresía")
        if has_visits: types.append("Visita")

        tipo = " + ".join(types) if types else "Desconocido"

        results.append({
            'date': s.created_at.strftime('%Y-%m-%d %H:%M'),
            'employee': s.user.name if s.user else 'Desconocido',
            'tipo': tipo,
            'total': s.total
        })

    return jsonify({
        'total_revenue': total_revenue,
        'transactions': total_count,
        'sales': results,
        'page': page,
        'pages': math.ceil(total_count / per_page)
    })

if __name__ == '__main__':
    t = threading.Thread(target=app.run, kwargs={'host': '127.0.0.1', 'port': 5000})
    t.daemon = True
    t.start()
    webview.create_window('Santa Fuerza', 'http://127.0.0.1:5000', width=1280, height=800, text_select=True)
    webview.start()
