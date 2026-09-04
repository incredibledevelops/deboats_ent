from flask import Flask, request, jsonify, render_template, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
from functools import wraps
import json, os, csv, io, smtplib, hashlib, hmac, base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random, string, uuid
from collections import defaultdict
from decimal import Decimal
from sqlalchemy import func, or_, and_

app = Flask(__name__)
app.secret_key = 'deboats-favour-enterprise-secret-2026-v2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///deboats.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)

db = SQLAlchemy(app)

# =============================================================================
# MODELS
# =============================================================================

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='Cashier')
    status = db.Column(db.String(20), default='Active')
    permissions = db.Column(db.Text, nullable=True)
    last_login = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.String(20), nullable=True)
    employee_id = db.Column(db.String(20), unique=True, nullable=True)
    shift = db.Column(db.String(20), default='Day')
    commission_rate = db.Column(db.Float, default=0)
    hire_date = db.Column(db.String(20), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)

class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.String(300))
    color = db.Column(db.String(20), default='#2d6a4f')
    loyalty_points_multiplier = db.Column(db.Float, default=1.0)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=True)
    barcode = db.Column(db.String(50), unique=True, nullable=True)
    category = db.Column(db.String(100))
    subcategory = db.Column(db.String(100), nullable=True)
    type = db.Column(db.String(20), default='Both')
    buy_price = db.Column(db.Float, default=0)
    sell_price = db.Column(db.Float, default=0)
    wsell_price = db.Column(db.Float, default=0)
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=5)
    max_stock = db.Column(db.Integer, default=100)
    unit = db.Column(db.String(30))
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=True)
    weight = db.Column(db.Float, default=0)
    location = db.Column(db.String(50), nullable=True)
    expiry_date = db.Column(db.String(20), nullable=True)
    batch_number = db.Column(db.String(50), nullable=True)
    serial_number = db.Column(db.String(50), nullable=True)
    reorder_quantity = db.Column(db.Integer, default=0)
    last_restock_date = db.Column(db.String(20), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    image_url = db.Column(db.Text, nullable=True)
    loyalty_points = db.Column(db.Integer, default=1)

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(30))
    email = db.Column(db.String(100))
    type = db.Column(db.String(20), default='Retail')
    address = db.Column(db.String(200))
    total_purchases = db.Column(db.Float, default=0)
    credit_limit = db.Column(db.Float, default=0)
    credit_used = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    created_date = db.Column(db.String(20))
    loyalty_points = db.Column(db.Integer, default=0)
    loyalty_tier = db.Column(db.String(20), default='Bronze')
    birthday = db.Column(db.String(10), nullable=True)
    last_purchase_date = db.Column(db.String(20), nullable=True)
    total_visits = db.Column(db.Integer, default=0)
    preferred_payment = db.Column(db.String(30), default='Cash')
    newsletter_optin = db.Column(db.Boolean, default=False)
    sms_optin = db.Column(db.Boolean, default=False)
    tags = db.Column(db.Text, nullable=True)

class LoyaltyTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'))
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'))
    points_earned = db.Column(db.Integer, default=0)
    points_used = db.Column(db.Integer, default=0)
    transaction_type = db.Column(db.String(20))
    description = db.Column(db.String(200))
    date = db.Column(db.String(20))
    expiry_date = db.Column(db.String(20), nullable=True)

class LoyaltyReward(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    points_required = db.Column(db.Integer, nullable=False)
    reward_type = db.Column(db.String(20))
    discount_value = db.Column(db.Float, default=0)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    expiry_days = db.Column(db.Integer, default=30)

class Supplier(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    contact = db.Column(db.String(100))
    phone = db.Column(db.String(30))
    email = db.Column(db.String(100))
    address = db.Column(db.String(300))
    products = db.Column(db.String(200))
    status = db.Column(db.String(20), default='Active')
    notes = db.Column(db.Text)
    total_supplied = db.Column(db.Float, default=0)
    rating = db.Column(db.Float, default=0)
    delivery_time = db.Column(db.Float, default=0)
    payment_terms = db.Column(db.String(50), default='Net 30')
    tax_id = db.Column(db.String(50), nullable=True)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    customer = db.Column(db.String(100), default='Walk-in')
    customer_id = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(20), default='Retail')
    subtotal = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    discount_type = db.Column(db.String(10), default='percent')
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    cost = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(30), default='Cash')
    amount_paid = db.Column(db.Float, default=0)
    change_due = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    items_json = db.Column(db.Text, default='[]')
    status = db.Column(db.String(20), default='Completed')
    created_by = db.Column(db.Integer, nullable=True)
    created_by_name = db.Column(db.String(100), nullable=True)
    loyalty_points_earned = db.Column(db.Integer, default=0)
    loyalty_points_used = db.Column(db.Integer, default=0)
    customer_phone = db.Column(db.String(30), nullable=True)
    device_id = db.Column(db.String(50), nullable=True)
    cashier_shift = db.Column(db.String(20), default='Day')
    sale_session_id = db.Column(db.String(50), nullable=True)

class SuspendedSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    customer = db.Column(db.String(100), default='Walk-in')
    customer_id = db.Column(db.Integer, nullable=True)
    type = db.Column(db.String(20), default='Retail')
    subtotal = db.Column(db.Float, default=0)
    discount = db.Column(db.Float, default=0)
    discount_type = db.Column(db.String(10), default='percent')
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    cost = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(30), default='Cash')
    amount_paid = db.Column(db.Float, default=0)
    change_due = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    items_json = db.Column(db.Text, default='[]')
    customer_name = db.Column(db.String(100), nullable=True)
    created_by = db.Column(db.Integer, nullable=True)
    created_by_name = db.Column(db.String(100), nullable=True)
    created_at = db.Column(db.String(20))
    device_id = db.Column(db.String(50), nullable=True)
    resume_code = db.Column(db.String(20), nullable=True)

class PurchaseOrder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'))
    supplier_name = db.Column(db.String(200))
    order_date = db.Column(db.String(20))
    expected_delivery = db.Column(db.String(20), nullable=True)
    actual_delivery = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='Draft')
    subtotal = db.Column(db.Float, default=0)
    tax = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)
    items_json = db.Column(db.Text, default='[]')
    created_by = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.String(20))

class Purchase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    supplier_id = db.Column(db.Integer)
    supplier_name = db.Column(db.String(200))
    product_id = db.Column(db.Integer)
    product_name = db.Column(db.String(200))
    qty = db.Column(db.Integer, default=0)
    unit_cost = db.Column(db.Float, default=0)
    total = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), default='Received')
    notes = db.Column(db.Text)
    po_number = db.Column(db.String(50), nullable=True)
    batch_number = db.Column(db.String(50), nullable=True)
    expiry_date = db.Column(db.String(20), nullable=True)
    received_by = db.Column(db.String(100), nullable=True)

class StockAdjustment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product_name = db.Column(db.String(200))
    adjustment_type = db.Column(db.String(20))
    quantity = db.Column(db.Integer)
    old_quantity = db.Column(db.Integer)
    new_quantity = db.Column(db.Integer)
    reason = db.Column(db.String(200))
    date = db.Column(db.String(20))
    performed_by = db.Column(db.String(100))
    notes = db.Column(db.Text)

class Expense(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.String(20))
    category = db.Column(db.String(100))
    description = db.Column(db.String(300))
    amount = db.Column(db.Float, default=0)
    payment_method = db.Column(db.String(30), default='Cash')
    notes = db.Column(db.Text)
    receipt_url = db.Column(db.Text, nullable=True)
    budget_category = db.Column(db.String(100), nullable=True)
    approved_by = db.Column(db.String(100), nullable=True)

class Budget(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(100), nullable=False)
    month = db.Column(db.String(7))
    allocated = db.Column(db.Float, default=0)
    spent = db.Column(db.Float, default=0)
    notes = db.Column(db.Text)

class Campaign(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20))
    description = db.Column(db.Text)
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    discount_percent = db.Column(db.Float, default=0)
    min_purchase = db.Column(db.Float, default=0)
    target_segment = db.Column(db.String(50))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.String(20))
    sent_count = db.Column(db.Integer, default=0)

class Setting(db.Model):
    key = db.Column(db.String(50), primary_key=True)
    value = db.Column(db.Text)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(20))
    user_id = db.Column(db.Integer, nullable=True)
    user_name = db.Column(db.String(100), nullable=True)
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50), nullable=True)
    device_id = db.Column(db.String(50), nullable=True)

# =============================================================================
# HELPERS
# =============================================================================

def get_setting(key, default=''):
    s = Setting.query.get(key)
    return s.value if s else default

def set_setting(key, value):
    s = Setting.query.get(key)
    if s:
        s.value = str(value)
    else:
        db.session.add(Setting(key=key, value=str(value)))
    db.session.commit()

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Unauthorized'}), 401
        return f(*args, **kwargs)
    return decorated

def permission_required(section):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Unauthorized'}), 401
            user = User.query.get(session['user_id'])
            if not user:
                return jsonify({'error': 'Unauthorized'}), 401
            if user.role == 'Admin':
                return f(*args, **kwargs)
            if user.permissions:
                allowed = json.loads(user.permissions)
                if section not in allowed:
                    return jsonify({'error': 'Forbidden: insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def log_action(action, details=None):
    try:
        log = AuditLog(
            timestamp=datetime.utcnow().isoformat(),
            user_id=session.get('user_id'),
            user_name=session.get('user_name', 'Unknown'),
            action=action,
            details=details,
            ip_address=request.remote_addr,
            device_id=request.headers.get('X-Device-ID')
        )
        db.session.add(log)
        db.session.commit()
    except:
        pass

def generate_barcode(product_id):
    """Generate a unique barcode based on product ID"""
    base = str(product_id).zfill(12)
    # Simple checksum calculation
    check = sum(int(c) for c in base) % 10
    return base + str(check)

def generate_po_number():
    return f"PO-{datetime.now().strftime('%Y%m')}-{random.randint(1000, 9999)}"

def generate_resume_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def send_sms(phone, message):
    try:
        print(f"[SMS] To: {phone}, Message: {message}")
        return True
    except:
        return False

def send_email_alert(subject, body, to_email=None):
    try:
        smtp_host = get_setting('smtp_host', 'smtp.gmail.com')
        smtp_port = int(get_setting('smtp_port', '587'))
        smtp_user = get_setting('smtp_user', '')
        smtp_pass = get_setting('smtp_password', '')
        alert_email = to_email or get_setting('alert_email', '')

        if not smtp_user or not smtp_pass or not alert_email:
            return False

        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = alert_email
        msg['Subject'] = f"[Deboat's Favour] {subject}"

        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def calculate_loyalty_points(customer_id, total_amount):
    customer = Customer.query.get(customer_id)
    if not customer:
        return 0

    points = int(total_amount)

    tier_multipliers = {
        'Bronze': 1.0,
        'Silver': 1.5,
        'Gold': 2.0,
        'Platinum': 3.0
    }
    multiplier = tier_multipliers.get(customer.loyalty_tier, 1.0)
    points = int(points * multiplier)
    return points

def get_customer_tier(total_spent):
    if total_spent >= 10000:
        return 'Platinum'
    elif total_spent >= 5000:
        return 'Gold'
    elif total_spent >= 2000:
        return 'Silver'
    else:
        return 'Bronze'

def get_tier_benefits(tier):
    benefits = {
        'Bronze': {'discount': 0, 'points_multiplier': 1.0},
        'Silver': {'discount': 5, 'points_multiplier': 1.5},
        'Gold': {'discount': 10, 'points_multiplier': 2.0},
        'Platinum': {'discount': 15, 'points_multiplier': 3.0}
    }
    return benefits.get(tier, benefits['Bronze'])

def product_to_dict(p):
    return {
        'id': p.id, 'name': p.name, 'sku': p.sku or '', 'barcode': p.barcode or '',
        'category': p.category or '', 'type': p.type, 'buyPrice': p.buy_price,
        'sellPrice': p.sell_price, 'wsellPrice': p.wsell_price,
        'stock': p.stock, 'minStock': p.min_stock, 'unit': p.unit or '',
        'supplierId': p.supplier_id, 'expiryDate': p.expiry_date,
        'batchNumber': p.batch_number, 'location': p.location
    }

def customer_to_dict(c):
    return {
        'id': c.id, 'name': c.name, 'phone': c.phone or '', 'email': c.email or '',
        'type': c.type, 'address': c.address or '', 'totalPurchases': c.total_purchases or 0,
        'creditLimit': c.credit_limit or 0, 'creditUsed': c.credit_used or 0,
        'creditAvailable': max(0, (c.credit_limit or 0) - (c.credit_used or 0)),
        'notes': c.notes or '', 'createdDate': c.created_date or '',
        'loyalty_points': c.loyalty_points or 0, 'loyalty_tier': c.loyalty_tier or 'Bronze',
        'birthday': c.birthday, 'newsletter_optin': c.newsletter_optin,
        'sms_optin': c.sms_optin
    }

def sale_to_dict(s):
    return {
        'id': s.id, 'date': s.date, 'customer': s.customer, 'customerId': s.customer_id,
        'type': s.type, 'subtotal': s.subtotal, 'discount': s.discount,
        'discountType': s.discount_type or 'percent',
        'tax': s.tax or 0, 'total': s.total, 'cost': s.cost,
        'paymentMethod': s.payment_method or 'Cash',
        'amountPaid': s.amount_paid or 0, 'changeDue': s.change_due or 0,
        'notes': s.notes or '', 'status': s.status or 'Completed',
        'items': json.loads(s.items_json or '[]'),
        'createdBy': s.created_by_name or '',
        'loyalty_points_earned': s.loyalty_points_earned or 0,
        'loyalty_points_used': s.loyalty_points_used or 0
    }

# =============================================================================
# ROUTES
# =============================================================================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.json or {}
    user = User.query.filter_by(
        username=data.get('username', ''),
        password=data.get('password', '')
    ).first()
    if user and user.status == 'Active':
        session['user_id'] = user.id
        session['user_name'] = user.name
        session['user_role'] = user.role
        user.last_login = datetime.utcnow().isoformat()
        db.session.commit()

        perms = json.loads(user.permissions) if user.permissions else None
        log_action('Login', f"User {user.name} logged in")

        return jsonify({
            'ok': True, 'name': user.name, 'role': user.role,
            'permissions': perms
        })
    return jsonify({'ok': False, 'error': 'Invalid credentials or inactive account'}), 401

@app.route('/api/logout', methods=['POST'])
def logout():
    if 'user_id' in session:
        log_action('Logout', f"User {session.get('user_name')} logged out")
    session.clear()
    return jsonify({'ok': True})

@app.route('/api/me')
def me():
    if 'user_id' not in session:
        return jsonify({'ok': False}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'ok': False}), 401
    perms = json.loads(user.permissions) if user.permissions else None
    return jsonify({
        'ok': True,
        'name': session.get('user_name'),
        'role': session.get('user_role'),
        'permissions': perms
    })

@app.route('/api/test-email', methods=['POST'])
@login_required
def test_email():
    try:
        sent = send_email_alert(
            'Test Email from Deboat\'s Favour',
            'This is a test email to confirm your SMTP settings are working correctly.\n\nIf you received this, your email configuration is correct!',
            get_setting('alert_email')
        )
        if sent:
            return jsonify({'message': 'Email sent successfully!'})
        else:
            return jsonify({'error': 'Failed to send email. Check SMTP settings.'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# SETTINGS
# =============================================================================

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    return jsonify({
        'name': get_setting('name'),
        'address': get_setting('address'),
        'phone': get_setting('phone'),
        'email': get_setting('email'),
        'currency': get_setting('currency', '₵'),
        'lowstock': int(get_setting('lowstock', '10')),
        'footer': get_setting('footer'),
        'tax_rate': float(get_setting('tax_rate', '0')),
        'tax_name': get_setting('tax_name', 'Tax'),
        'invoice_prefix': get_setting('invoice_prefix', 'INV'),
        'theme_brand': get_setting('theme_brand', '#1a3a2a'),
        'theme_brand_mid': get_setting('theme_brand_mid', '#2d6a4f'),
        'theme_brand_light': get_setting('theme_brand_light', '#52b788'),
        'theme_accent': get_setting('theme_accent', '#f4a261'),
        'db_type': get_setting('db_type', 'sqlite'),
        'system_name': get_setting('system_name', "Deboat's Favour"),
        'system_tagline': get_setting('system_tagline', 'Management System'),
        'smtp_host': get_setting('smtp_host', 'smtp.gmail.com'),
        'smtp_port': get_setting('smtp_port', '587'),
        'smtp_user': get_setting('smtp_user', ''),
        'smtp_password': get_setting('smtp_password', ''),
        'alert_email': get_setting('alert_email', ''),
        'enable_audit_logs': get_setting('enable_audit_logs', 'true') == 'true',
        'enable_email_alerts': get_setting('enable_email_alerts', 'false') == 'true',
        'loyalty_enabled': get_setting('loyalty_enabled', 'true') == 'true',
        'points_to_currency_rate': get_setting('points_to_currency_rate', '100'),
        'birthday_discount': get_setting('birthday_discount', '10'),
        'points_expiry': get_setting('points_expiry', '365'),
        'silver_tier': get_setting('silver_tier', '2000'),
        'gold_tier': get_setting('gold_tier', '5000'),
        'platinum_tier': get_setting('platinum_tier', '10000'),
    })

@app.route('/api/settings', methods=['POST'])
@login_required
def save_settings():
    data = request.json or {}
    keys = [
        'name', 'address', 'phone', 'email', 'currency', 'lowstock', 'footer',
        'tax_rate', 'tax_name', 'invoice_prefix',
        'theme_brand', 'theme_brand_mid', 'theme_brand_light', 'theme_accent',
        'db_type', 'system_name', 'system_tagline',
        'smtp_host', 'smtp_port', 'smtp_user', 'smtp_password', 'alert_email',
        'enable_audit_logs', 'enable_email_alerts',
        'loyalty_enabled', 'points_to_currency_rate', 'birthday_discount',
        'points_expiry', 'silver_tier', 'gold_tier', 'platinum_tier'
    ]
    for k in keys:
        if k in data:
            set_setting(k, data[k])

    log_action('Settings Updated', f"Settings updated by {session.get('user_name')}")
    return jsonify({'ok': True})

@app.route('/api/settings/db-test', methods=['POST'])
@login_required
def test_db_connection():
    data = request.json or {}
    db_type = data.get('dbType', 'sqlite')

    if db_type == 'sqlite':
        return jsonify({'message': 'SQLite connection is active'})

    try:
        if db_type == 'mysql':
            import pymysql as driver
        elif db_type == 'postgresql':
            import psycopg2 as driver
        else:
            return jsonify({'error': f'Unsupported database type: {db_type}'}), 400

        # Use driver module for connection
        if db_type == 'mysql':
            conn = driver.connect(
                host=data.get('dbHost', 'localhost'),
                port=int(data.get('dbPort', 3306)),
                user=data.get('dbUser', 'root'),
                password=data.get('dbPass', ''),
                database=data.get('dbName', 'deboats_favour')
            )
        else:  # postgresql
            conn = driver.connect(
                host=data.get('dbHost', 'localhost'),
                port=int(data.get('dbPort', 5432)),
                user=data.get('dbUser', 'postgres'),
                password=data.get('dbPass', ''),
                database=data.get('dbName', 'deboats_favour')
            )
        conn.close()
        return jsonify({'message': f'{db_type} connection successful!'})
    except ImportError as e:
        return jsonify({'error': f'Driver for {db_type} not installed: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# =============================================================================
# AUDIT LOGS
# =============================================================================

@app.route('/api/audit-logs', methods=['GET'])
@login_required
def get_audit_logs():
    limit = request.args.get('limit', 100, type=int)
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action', '')

    query = AuditLog.query.order_by(AuditLog.id.desc())

    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f'%{action}%'))

    logs = query.limit(limit).all()

    return jsonify([{
        'id': l.id,
        'timestamp': l.timestamp,
        'userId': l.user_id,
        'userName': l.user_name,
        'action': l.action,
        'details': l.details,
        'ipAddress': l.ip_address
    } for l in logs])

# =============================================================================
# CATEGORIES
# =============================================================================

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    return jsonify([{
        'id': c.id, 'name': c.name, 'description': c.description or '',
        'color': c.color or '#2d6a4f', 'loyalty_points_multiplier': c.loyalty_points_multiplier or 1.0
    } for c in Category.query.order_by(Category.name).all()])

@app.route('/api/categories', methods=['POST'])
@login_required
def add_category():
    d = request.json or {}
    name = d.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Name required'}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({'error': 'Category already exists'}), 409
    c = Category(
        name=name,
        description=d.get('description', ''),
        color=d.get('color', '#2d6a4f'),
        loyalty_points_multiplier=float(d.get('loyalty_points_multiplier', 1.0))
    )
    db.session.add(c)
    db.session.commit()
    log_action('Category Added', f"Added category: {name}")
    return jsonify({'id': c.id, 'name': c.name}), 201

@app.route('/api/categories/<int:cid>', methods=['PUT'])
@login_required
def update_category(cid):
    c = Category.query.get_or_404(cid)
    d = request.json or {}
    new_name = d.get('name', c.name).strip()
    if new_name != c.name and Category.query.filter_by(name=new_name).first():
        return jsonify({'error': 'Category name already exists'}), 409
    c.name = new_name
    c.description = d.get('description', c.description)
    c.color = d.get('color', c.color)
    c.loyalty_points_multiplier = float(d.get('loyalty_points_multiplier', 1.0))
    db.session.commit()
    log_action('Category Updated', f"Updated category: {new_name}")
    return jsonify({'ok': True})

@app.route('/api/categories/<int:cid>', methods=['DELETE'])
@login_required
def delete_category(cid):
    c = Category.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    log_action('Category Deleted', f"Deleted category: {c.name}")
    return jsonify({'ok': True})

# =============================================================================
# INVENTORY
# =============================================================================

@app.route('/api/inventory', methods=['GET'])
@login_required
def get_inventory():
    q = request.args.get('q', '').lower()
    cat = request.args.get('category', '')
    query = Product.query.filter_by(is_active=True)
    if q:
        query = query.filter(
            or_(
                Product.name.ilike(f'%{q}%'),
                Product.sku.ilike(f'%{q}%'),
                Product.barcode.ilike(f'%{q}%')
            )
        )
    if cat:
        query = query.filter_by(category=cat)
    return jsonify([product_to_dict(p) for p in query.all()])

@app.route('/api/inventory', methods=['POST'])
@login_required
def add_product():
    d = request.json or {}
    if not d.get('name'):
        return jsonify({'error': 'Product name required'}), 400

    # Generate barcode if not provided
    barcode = d.get('barcode')
    if not barcode:
        # We'll assign a temporary ID then generate barcode after commit
        pass

    p = Product(
        name=d['name'],
        sku=d.get('sku', ''),
        barcode=d.get('barcode'),  # Will be set after commit if needed
        category=d.get('category', 'Other'),
        type=d.get('type', 'Both'),
        buy_price=float(d.get('buyPrice', 0)),
        sell_price=float(d.get('sellPrice', 0)),
        wsell_price=float(d.get('wsellPrice', 0)),
        stock=int(d.get('stock', 0)),
        min_stock=int(d.get('minStock', 5)),
        unit=d.get('unit', 'pcs'),
        supplier_id=d.get('supplierId') or None,
        expiry_date=d.get('expiryDate'),
        batch_number=d.get('batchNumber'),
        location=d.get('location')
    )
    db.session.add(p)
    db.session.commit()

    # Generate barcode if not provided
    if not d.get('barcode'):
        p.barcode = generate_barcode(p.id)
        db.session.commit()

    log_action('Product Added', f"Added product: {p.name}")
    return jsonify(product_to_dict(p)), 201

@app.route('/api/inventory/<int:pid>', methods=['GET'])
@login_required
def get_product(pid):
    p = Product.query.get_or_404(pid)
    return jsonify(product_to_dict(p))

@app.route('/api/inventory/<int:pid>', methods=['PUT'])
@login_required
def update_product(pid):
    p = Product.query.get_or_404(pid)
    d = request.json or {}
    old_stock = p.stock
    p.name = d.get('name', p.name)
    p.sku = d.get('sku', p.sku)
    p.barcode = d.get('barcode', p.barcode)
    p.category = d.get('category', p.category)
    p.type = d.get('type', p.type)
    p.buy_price = float(d.get('buyPrice', p.buy_price))
    p.sell_price = float(d.get('sellPrice', p.sell_price))
    p.wsell_price = float(d.get('wsellPrice', p.wsell_price))
    p.stock = int(d.get('stock', p.stock))
    p.min_stock = int(d.get('minStock', p.min_stock))
    p.unit = d.get('unit', p.unit)
    p.supplier_id = d.get('supplierId') or None
    p.expiry_date = d.get('expiryDate')
    p.batch_number = d.get('batchNumber')
    p.location = d.get('location')
    db.session.commit()
    log_action('Product Updated', f"Updated product: {p.name}, stock: {old_stock} -> {p.stock}")
    return jsonify(product_to_dict(p))

@app.route('/api/inventory/<int:pid>', methods=['DELETE'])
@login_required
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    p.is_active = False
    db.session.commit()
    log_action('Product Deleted', f"Deleted product: {p.name}")
    return jsonify({'ok': True})

@app.route('/api/inventory/barcode/<barcode>', methods=['GET'])
@login_required
def get_product_by_barcode(barcode):
    product = Product.query.filter_by(barcode=barcode, is_active=True).first()
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    return jsonify(product_to_dict(product))

@app.route('/api/inventory/low-stock', methods=['GET'])
@login_required
def get_low_stock_products():
    threshold = int(get_setting('lowstock', '10'))
    products = Product.query.filter(
        or_(
            Product.stock <= Product.min_stock,
            Product.stock <= threshold,
            Product.stock == 0
        ),
        Product.is_active == True
    ).all()
    return jsonify([{
        'id': p.id, 'name': p.name, 'sku': p.sku,
        'stock': p.stock, 'min_stock': p.min_stock,
        'reorder_quantity': p.reorder_quantity,
        'supplier_id': p.supplier_id,
        'supplier_name': Supplier.query.get(p.supplier_id).name if p.supplier_id else None
    } for p in products])

@app.route('/api/inventory/generate-barcode', methods=['POST'])
@login_required
def generate_product_barcode():
    data = request.json or {}
    product_id = data.get('product_id')

    if not product_id:
        return jsonify({'error': 'Product ID required'}), 400

    product = Product.query.get_or_404(product_id)

    # Generate unique barcode
    barcode = generate_barcode(product.id)

    # Ensure uniqueness
    existing = Product.query.filter_by(barcode=barcode).first()
    if existing and existing.id != product.id:
        # Add random suffix for uniqueness
        suffix = str(random.randint(10, 99))
        barcode = generate_barcode(product.id)[:12] + suffix + str(random.randint(0, 9))

    product.barcode = barcode
    db.session.commit()

    log_action('Barcode Generated', f"Generated barcode for {product.name}: {barcode}")
    return jsonify({'ok': True, 'barcode': barcode})

@app.route('/api/inventory/bulk-generate-barcodes', methods=['POST'])
@login_required
def bulk_generate_barcodes():
    products = Product.query.filter(
        or_(
            Product.barcode.is_(None),
            Product.barcode == ''
        ),
        Product.is_active == True
    ).all()

    generated = []
    for product in products:
        barcode = generate_barcode(product.id)

        # Ensure uniqueness
        existing = Product.query.filter_by(barcode=barcode).first()
        if existing and existing.id != product.id:
            suffix = str(random.randint(10, 99))
            barcode = generate_barcode(product.id)[:12] + suffix + str(random.randint(0, 9))

        product.barcode = barcode
        generated.append({'id': product.id, 'name': product.name, 'barcode': barcode})

    db.session.commit()
    log_action('Bulk Barcode Generation', f"Generated {len(generated)} barcodes")
    return jsonify({'ok': True, 'generated': len(generated)})

# =============================================================================
# CUSTOMERS
# =============================================================================

@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    q = request.args.get('q', '').lower()
    query = Customer.query
    if q:
        query = query.filter(
            or_(Customer.name.ilike(f'%{q}%'), Customer.phone.ilike(f'%{q}%'))
        )
    return jsonify([customer_to_dict(c) for c in query.all()])

@app.route('/api/customers', methods=['POST'])
@login_required
def add_customer():
    d = request.json or {}
    if not d.get('name'):
        return jsonify({'error': 'Customer name required'}), 400
    c = Customer(
        name=d['name'],
        phone=d.get('phone', ''),
        email=d.get('email', ''),
        type=d.get('type', 'Retail'),
        address=d.get('address', ''),
        credit_limit=float(d.get('creditLimit', 0)),
        notes=d.get('notes', ''),
        birthday=d.get('birthday'),
        newsletter_optin=d.get('newsletter_optin', False),
        sms_optin=d.get('sms_optin', False),
        created_date=date.today().isoformat()
    )
    db.session.add(c)
    db.session.commit()
    log_action('Customer Added', f"Added customer: {c.name}")
    return jsonify(customer_to_dict(c)), 201

@app.route('/api/customers/<int:cid>', methods=['GET'])
@login_required
def get_customer(cid):
    c = Customer.query.get_or_404(cid)
    data = customer_to_dict(c)
    sales = Sale.query.filter_by(customer_id=cid).order_by(Sale.id.desc()).all()
    data['purchases'] = [sale_to_dict(s) for s in sales]
    return jsonify(data)

@app.route('/api/customers/<int:cid>', methods=['PUT'])
@login_required
def update_customer(cid):
    c = Customer.query.get_or_404(cid)
    d = request.json or {}
    c.name = d.get('name', c.name)
    c.phone = d.get('phone', c.phone)
    c.email = d.get('email', c.email)
    c.type = d.get('type', c.type)
    c.address = d.get('address', c.address)
    c.credit_limit = float(d.get('creditLimit', c.credit_limit or 0))
    c.notes = d.get('notes', c.notes)
    c.birthday = d.get('birthday', c.birthday)
    c.newsletter_optin = d.get('newsletter_optin', c.newsletter_optin)
    c.sms_optin = d.get('sms_optin', c.sms_optin)
    db.session.commit()
    log_action('Customer Updated', f"Updated customer: {c.name}")
    return jsonify(customer_to_dict(c))

@app.route('/api/customers/<int:cid>', methods=['DELETE'])
@login_required
def delete_customer(cid):
    c = Customer.query.get_or_404(cid)
    db.session.delete(c)
    db.session.commit()
    log_action('Customer Deleted', f"Deleted customer: {c.name}")
    return jsonify({'ok': True})

@app.route('/api/customers/<int:cid>/pay-credit', methods=['POST'])
@login_required
def pay_credit(cid):
    c = Customer.query.get_or_404(cid)
    d = request.json or {}
    amount = float(d.get('amount', 0))
    if amount <= 0:
        return jsonify({'error': 'Invalid amount'}), 400
    c.credit_used = max(0, (c.credit_used or 0) - amount)
    db.session.commit()
    log_action('Credit Payment', f"Customer {c.name} paid {amount} credit")
    return jsonify(customer_to_dict(c))

@app.route('/api/customers/<int:cid>/loyalty', methods=['GET'])
@login_required
def get_customer_loyalty(cid):
    customer = Customer.query.get_or_404(cid)
    transactions = LoyaltyTransaction.query.filter_by(customer_id=cid).order_by(LoyaltyTransaction.id.desc()).limit(20).all()
    available_rewards = LoyaltyReward.query.filter(
        LoyaltyReward.is_active == True,
        LoyaltyReward.points_required <= customer.loyalty_points
    ).all()
    return jsonify({
        'points': customer.loyalty_points or 0,
        'tier': customer.loyalty_tier or 'Bronze',
        'tier_benefits': get_tier_benefits(customer.loyalty_tier or 'Bronze'),
        'transactions': [{
            'id': t.id,
            'points_earned': t.points_earned,
            'points_used': t.points_used,
            'transaction_type': t.transaction_type,
            'description': t.description,
            'date': t.date,
            'expiry_date': t.expiry_date
        } for t in transactions],
        'available_rewards': [{
            'id': r.id,
            'name': r.name,
            'description': r.description,
            'points_required': r.points_required,
            'reward_type': r.reward_type,
            'discount_value': r.discount_value
        } for r in available_rewards]
    })

@app.route('/api/customers/<int:cid>/redeem', methods=['POST'])
@login_required
def redeem_loyalty_points(cid):
    data = request.json or {}
    points_to_use = data.get('points', 0)
    customer = Customer.query.get_or_404(cid)

    if points_to_use > 0:
        if customer.loyalty_points < points_to_use:
            return jsonify({'error': 'Insufficient points'}), 400

        discount_value = points_to_use / 100
        customer.loyalty_points -= points_to_use

        transaction = LoyaltyTransaction(
            customer_id=cid,
            points_used=points_to_use,
            transaction_type='redeem',
            description=f"Redeemed {points_to_use} points for ₵{discount_value:.2f} discount",
            date=date.today().isoformat()
        )
        db.session.add(transaction)
        db.session.commit()

        return jsonify({
            'ok': True,
            'remaining_points': customer.loyalty_points,
            'discount_value': discount_value
        })

    return jsonify({'error': 'Invalid redemption request'}), 400

@app.route('/api/customers/loyalty-tier-update', methods=['POST'])
@login_required
def update_loyalty_tiers():
    customers = Customer.query.all()
    updated = 0
    for customer in customers:
        new_tier = get_customer_tier(customer.total_purchases or 0)
        if customer.loyalty_tier != new_tier:
            customer.loyalty_tier = new_tier
            updated += 1
    db.session.commit()
    log_action('Loyalty Tier Update', f"Updated {updated} customers")
    return jsonify({'ok': True, 'updated': updated})

# =============================================================================
# SALES
# =============================================================================

@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    q = request.args.get('q', '').lower()
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    sale_type = request.args.get('type', '')
    status = request.args.get('status', '')

    query = Sale.query.order_by(Sale.id.desc())
    if q:
        query = query.filter(
            or_(
                Sale.customer.ilike(f'%{q}%'),
                db.cast(Sale.id, db.String).ilike(f'%{q}%')
            )
        )
    if date_from:
        query = query.filter(Sale.date >= date_from)
    if date_to:
        query = query.filter(Sale.date <= date_to)
    if sale_type:
        query = query.filter_by(type=sale_type)
    if status:
        query = query.filter_by(status=status)

    sales = query.all()
    result = []
    prefix = get_setting('invoice_prefix', 'INV')
    for s in sales:
        data = sale_to_dict(s)
        data['invoiceNumber'] = f"{prefix}-{s.id:05d}"
        result.append(data)
    return jsonify(result)

@app.route('/api/sales', methods=['POST'])
@login_required
def create_sale():
    data = request.json or {}
    items = data.get('items', [])
    if not items:
        return jsonify({'error': 'No items in sale'}), 400

    subtotal = sum(float(i['price']) * int(i['qty']) for i in items)
    discount_type = data.get('discountType', 'percent')
    discount = float(data.get('discount', 0))
    tax_rate = float(data.get('tax', 0))
    payment_method = data.get('paymentMethod', 'Cash')
    customer_id = data.get('customerId')

    if discount_type == 'fixed':
        after_discount = max(0, subtotal - discount)
    else:
        after_discount = subtotal * (1 - discount / 100)

    tax_amount = after_discount * (tax_rate / 100)
    total = after_discount + tax_amount
    cost = sum(float(i.get('cost', 0)) * int(i['qty']) for i in items)

    amount_paid = float(data.get('amountPaid', total))
    change_due = max(0, amount_paid - total)
    sale_status = data.get('status', 'Completed')

    # Update stock
    for item in items:
        p = Product.query.get(item['productId'])
        if p:
            p.stock = max(0, p.stock - int(item['qty']))

    points_earned = 0
    if customer_id:
        cust = Customer.query.get(customer_id)
        if cust:
            cust.total_purchases = (cust.total_purchases or 0) + total
            cust.total_visits = (cust.total_visits or 0) + 1
            cust.last_purchase_date = date.today().isoformat()
            points_earned = calculate_loyalty_points(customer_id, total)
            cust.loyalty_points = (cust.loyalty_points or 0) + points_earned
            cust.loyalty_tier = get_customer_tier(cust.total_purchases)

            if points_earned > 0:
                lt = LoyaltyTransaction(
                    customer_id=customer_id,
                    points_earned=points_earned,
                    transaction_type='earn',
                    description=f"Purchase - {points_earned} points earned",
                    date=date.today().isoformat(),
                    expiry_date=(datetime.now() + timedelta(days=365)).isoformat()
                )
                db.session.add(lt)

    sale = Sale(
        date=date.today().isoformat(),
        customer=cust.name if customer_id else 'Walk-in',
        customer_id=customer_id,
        type=data.get('type', 'Retail'),
        subtotal=subtotal,
        discount=discount,
        discount_type=discount_type,
        tax=tax_amount,
        total=total,
        cost=cost,
        payment_method=payment_method,
        amount_paid=amount_paid,
        change_due=change_due,
        notes=data.get('notes', ''),
        status=sale_status,
        items_json=json.dumps(items),
        created_by=session.get('user_id'),
        created_by_name=session.get('user_name', 'Unknown'),
        loyalty_points_earned=points_earned
    )
    db.session.add(sale)
    db.session.commit()

    log_action('Sale Completed', f"Sale #{sale.id} for {sale.customer}, total {total}")

    result = sale_to_dict(sale)
    prefix = get_setting('invoice_prefix', 'INV')
    result['invoiceNumber'] = f"{prefix}-{sale.id:05d}"
    return jsonify(result), 201

@app.route('/api/sales/<int:sid>', methods=['GET'])
@login_required
def get_sale(sid):
    s = Sale.query.get_or_404(sid)
    result = sale_to_dict(s)
    prefix = get_setting('invoice_prefix', 'INV')
    result['invoiceNumber'] = f"{prefix}-{s.id:05d}"
    return jsonify(result)

@app.route('/api/sales/<int:sid>/void', methods=['POST'])
@login_required
def void_sale(sid):
    s = Sale.query.get_or_404(sid)
    if s.status == 'Voided':
        return jsonify({'error': 'Already voided'}), 400
    for item in json.loads(s.items_json or '[]'):
        p = Product.query.get(item.get('productId'))
        if p:
            p.stock += int(item.get('qty', 0))
    s.status = 'Voided'
    db.session.commit()
    log_action('Sale Voided', f"Sale #{s.id} voided by {session.get('user_name')}")
    return jsonify({'ok': True})

@app.route('/api/sales/<int:sid>/edit-receipt', methods=['PUT'])
@login_required
def edit_receipt(sid):
    s = Sale.query.get_or_404(sid)
    d = request.json or {}
    if 'customer' in d:
        s.customer = d['customer']
    if 'notes' in d:
        s.notes = d['notes']
    if 'payment_method' in d:
        s.payment_method = d['payment_method']
    if 'amount_paid' in d:
        s.amount_paid = float(d['amount_paid'])
        s.change_due = max(0, s.amount_paid - s.total)
    db.session.commit()
    log_action('Receipt Edited', f"Receipt #{s.id} edited by {session.get('user_name')}")
    return jsonify(sale_to_dict(s))

# =============================================================================
# SUSPENDED SALES
# =============================================================================

@app.route('/api/suspended-sales', methods=['GET'])
@login_required
def get_suspended_sales():
    suspended = SuspendedSale.query.order_by(SuspendedSale.id.desc()).all()
    return jsonify([{
        'id': s.id, 'date': s.date, 'customer': s.customer or 'Walk-in',
        'customerId': s.customer_id, 'type': s.type, 'subtotal': s.subtotal,
        'discount': s.discount, 'discountType': s.discount_type or 'percent',
        'tax': s.tax or 0, 'total': s.total, 'cost': s.cost,
        'paymentMethod': s.payment_method or 'Cash',
        'amountPaid': s.amount_paid or 0, 'changeDue': s.change_due or 0,
        'notes': s.notes or '', 'customerName': s.customer_name or '',
        'items': json.loads(s.items_json or '[]'),
        'createdBy': s.created_by_name or '',
        'createdAt': s.created_at or ''
    } for s in suspended])

@app.route('/api/suspended-sales', methods=['POST'])
@login_required
def suspend_sale():
    d = request.json or {}
    items = d.get('items', [])
    if not items:
        return jsonify({'error': 'No items to suspend'}), 400

    subtotal = sum(float(i['price']) * int(i['qty']) for i in items)
    discount_type = d.get('discountType', 'percent')
    discount = float(d.get('discount', 0))
    tax_rate = float(d.get('tax', 0))

    if discount_type == 'fixed':
        after_discount = max(0, subtotal - discount)
    else:
        after_discount = subtotal * (1 - discount / 100)

    tax_amount = after_discount * (tax_rate / 100)
    total = after_discount + tax_amount
    cost = sum(float(i.get('cost', 0)) * int(i['qty']) for i in items)

    suspended = SuspendedSale(
        date=date.today().isoformat(),
        customer=d.get('customer', 'Walk-in'),
        customer_id=d.get('customerId'),
        type=d.get('type', 'Retail'),
        subtotal=subtotal,
        discount=discount,
        discount_type=discount_type,
        tax=tax_amount,
        total=total,
        cost=cost,
        payment_method=d.get('paymentMethod', 'Cash'),
        amount_paid=float(d.get('amountPaid', 0)),
        change_due=float(d.get('changeDue', 0)),
        notes=d.get('notes', ''),
        items_json=json.dumps(items),
        customer_name=d.get('customerName', 'Walk-in'),
        created_by=session.get('user_id'),
        created_by_name=session.get('user_name', 'Unknown'),
        created_at=datetime.utcnow().isoformat()
    )
    db.session.add(suspended)
    db.session.commit()
    log_action('Sale Suspended', f"Sale suspended, items: {len(items)}")
    return jsonify({'ok': True, 'id': suspended.id}), 201

@app.route('/api/suspended-sales/<int:sid>', methods=['GET'])
@login_required
def get_suspended_sale(sid):
    s = SuspendedSale.query.get_or_404(sid)
    return jsonify({
        'id': s.id, 'date': s.date, 'customer': s.customer or 'Walk-in',
        'customerId': s.customer_id, 'type': s.type, 'subtotal': s.subtotal,
        'discount': s.discount, 'discountType': s.discount_type or 'percent',
        'tax': s.tax or 0, 'total': s.total, 'cost': s.cost,
        'paymentMethod': s.payment_method or 'Cash',
        'amountPaid': s.amount_paid or 0, 'changeDue': s.change_due or 0,
        'notes': s.notes or '', 'customerName': s.customer_name or '',
        'items': json.loads(s.items_json or '[]'),
        'createdBy': s.created_by_name or '',
        'createdAt': s.created_at or ''
    })

@app.route('/api/suspended-sales/<int:sid>', methods=['DELETE'])
@login_required
def delete_suspended_sale(sid):
    s = SuspendedSale.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    log_action('Suspended Sale Deleted', f"Deleted suspended sale #{s.id}")
    return jsonify({'ok': True})

# =============================================================================
# REPORTS
# =============================================================================

@app.route('/api/reports/sales-summary', methods=['GET'])
@login_required
def report_sales_summary():
    date_from = request.args.get('date_from', (date.today() - timedelta(days=30)).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())
    sales = Sale.query.filter(
        Sale.date >= date_from, Sale.date <= date_to, Sale.status != 'Voided'
    ).order_by(Sale.date).all()

    by_day = {}
    for s in sales:
        if s.date not in by_day:
            by_day[s.date] = {'date': s.date, 'count': 0, 'revenue': 0, 'cost': 0, 'profit': 0}
        by_day[s.date]['count'] += 1
        by_day[s.date]['revenue'] += s.total
        by_day[s.date]['cost'] += s.cost
        by_day[s.date]['profit'] += (s.total - s.cost)

    return jsonify({
        'rows': list(by_day.values()),
        'total_rev': sum(s.total for s in sales),
        'total_cost': sum(s.cost for s in sales),
        'total_count': len(sales),
    })

@app.route('/api/reports/inventory-valuation', methods=['GET'])
@login_required
def report_inventory_valuation():
    products = Product.query.filter_by(is_active=True).all()
    rows = []
    for p in products:
        rows.append({
            'id': p.id, 'name': p.name, 'category': p.category,
            'stock': p.stock, 'buyPrice': p.buy_price, 'sellPrice': p.sell_price,
            'costValue': round(p.stock * p.buy_price, 2),
            'sellValue': round(p.stock * p.sell_price, 2),
            'potentialProfit': round(p.stock * (p.sell_price - p.buy_price), 2),
        })
    total_cost_val = sum(r['costValue'] for r in rows)
    total_sell_val = sum(r['sellValue'] for r in rows)
    return jsonify({
        'rows': rows,
        'totalCostValue': total_cost_val,
        'totalSellValue': total_sell_val,
        'totalPotentialProfit': total_sell_val - total_cost_val,
    })

@app.route('/api/reports/expense-summary', methods=['GET'])
@login_required
def report_expense_summary():
    date_from = request.args.get('date_from', (date.today() - timedelta(days=30)).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())
    expenses = Expense.query.filter(
        Expense.date >= date_from, Expense.date <= date_to
    ).order_by(Expense.date).all()

    by_cat = {}
    for e in expenses:
        if e.category not in by_cat:
            by_cat[e.category] = {'category': e.category, 'count': 0, 'total': 0}
        by_cat[e.category]['count'] += 1
        by_cat[e.category]['total'] += e.amount

    return jsonify({
        'rows': [{'id': e.id, 'date': e.date, 'category': e.category, 'description': e.description,
                  'amount': e.amount, 'paymentMethod': e.payment_method} for e in expenses],
        'byCategory': list(by_cat.values()),
        'total': sum(e.amount for e in expenses),
    })

@app.route('/api/reports/profit-loss', methods=['GET'])
@login_required
def report_profit_loss():
    date_from = request.args.get('date_from', (date.today() - timedelta(days=30)).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())

    sales = Sale.query.filter(Sale.date >= date_from, Sale.date <= date_to, Sale.status != 'Voided').all()
    expenses = Expense.query.filter(Expense.date >= date_from, Expense.date <= date_to).all()

    revenue = sum(s.total for s in sales)
    cogs = sum(s.cost for s in sales)
    gross_profit = revenue - cogs
    total_exp = sum(e.amount for e in expenses)
    net_profit = gross_profit - total_exp

    return jsonify({
        'dateFrom': date_from,
        'dateTo': date_to,
        'revenue': revenue,
        'cogs': cogs,
        'grossProfit': gross_profit,
        'grossMargin': (gross_profit / revenue * 100) if revenue else 0,
        'expenses': total_exp,
        'netProfit': net_profit,
        'netMargin': (net_profit / revenue * 100) if revenue else 0,
        'salesCount': len(sales),
        'expenseBreakdown': [{'date': e.date, 'category': e.category, 'description': e.description, 'amount': e.amount} for e in expenses],
    })

@app.route('/api/reports/loyalty-summary', methods=['GET'])
@login_required
def report_loyalty_summary():
    customers = Customer.query.all()
    total_points = sum(c.loyalty_points or 0 for c in customers)
    tier_counts = {'Bronze': 0, 'Silver': 0, 'Gold': 0, 'Platinum': 0}
    tier_spending = {'Bronze': 0, 'Silver': 0, 'Gold': 0, 'Platinum': 0}
    for c in customers:
        tier = c.loyalty_tier or 'Bronze'
        tier_counts[tier] = tier_counts.get(tier, 0) + 1
        tier_spending[tier] = tier_spending.get(tier, 0) + (c.total_purchases or 0)

    redemptions = LoyaltyTransaction.query.filter_by(transaction_type='redeem').order_by(LoyaltyTransaction.id.desc()).limit(20).all()
    return jsonify({
        'total_customers': len(customers),
        'total_points': total_points,
        'tier_distribution': tier_counts,
        'tier_spending': tier_spending,
        'recent_redemptions': [{
            'customer': Customer.query.get(r.customer_id).name if r.customer_id else 'Unknown',
            'points_used': r.points_used,
            'description': r.description,
            'date': r.date
        } for r in redemptions]
    })

@app.route('/api/reports/sales-performance', methods=['GET'])
@login_required
def report_sales_performance():
    date_from = request.args.get('date_from', (date.today() - timedelta(days=30)).isoformat())
    date_to = request.args.get('date_to', date.today().isoformat())
    sales = Sale.query.filter(
        Sale.date >= date_from, Sale.date <= date_to, Sale.status != 'Voided'
    ).all()

    staff_sales = {}
    for s in sales:
        staff = s.created_by_name or 'Unknown'
        if staff not in staff_sales:
            staff_sales[staff] = {'total': 0, 'count': 0, 'items': 0}
        staff_sales[staff]['total'] += s.total
        staff_sales[staff]['count'] += 1
        items = json.loads(s.items_json or '[]')
        staff_sales[staff]['items'] += sum(i['qty'] for i in items)

    # Top selling days
    day_sales = {}
    for s in sales:
        if s.date:
            day_sales[s.date] = day_sales.get(s.date, 0) + s.total
    top_days = sorted(day_sales.items(), key=lambda x: x[1], reverse=True)[:7]

    # Hourly pattern (simplified - based on time of day if available)
    hourly = {}
    for s in sales:
        # Use date string as hour approximation if no time field
        hour = 12  # Default
        if s.date:
            try:
                dt = datetime.strptime(s.date + ' 12:00:00', '%Y-%m-%d %H:%M:%S')
                hour = 12
            except:
                hour = 12
        hourly[hour] = hourly.get(hour, 0) + s.total

    return jsonify({
        'total_sales': len(sales),
        'total_revenue': sum(s.total for s in sales),
        'average_sale': sum(s.total for s in sales) / len(sales) if sales else 0,
        'staff_performance': [{
            'staff': staff,
            'total_sales': data['total'],
            'transaction_count': data['count'],
            'items_sold': data['items'],
            'avg_transaction': data['total'] / data['count'] if data['count'] > 0 else 0
        } for staff, data in staff_sales.items()],
        'top_selling_days': [{'date': d, 'revenue': amt} for d, amt in top_days],
        'hourly_pattern': [{'hour': h, 'revenue': amt} for h, amt in sorted(hourly.items())]
    })

@app.route('/api/reports/advanced-analytics', methods=['GET'])
@login_required
def advanced_analytics():
    sales_data = Sale.query.filter(Sale.status != 'Voided').order_by(Sale.date).all()
    daily_sales = {}
    for s in sales_data:
        if s.date:
            daily_sales[s.date] = daily_sales.get(s.date, 0) + s.total

    sorted_dates = sorted(daily_sales.keys())
    recent_values = [daily_sales[d] for d in sorted_dates[-7:]] if sorted_dates else []
    forecast = sum(recent_values) / len(recent_values) if recent_values else 0

    customers = Customer.query.all()
    returning_customers = sum(1 for c in customers if (c.total_visits or 0) > 1)
    retention_rate = (returning_customers / len(customers) * 100) if customers else 0

    # Product associations - find products frequently bought together
    associations = []
    sales_list = Sale.query.filter(Sale.status != 'Voided').limit(100).all()
    product_pairs = {}
    for s in sales_list:
        items = json.loads(s.items_json or '[]')
        product_ids = [i['productId'] for i in items if i.get('productId')]
        for i in range(len(product_ids)):
            for j in range(i+1, len(product_ids)):
                key = tuple(sorted([product_ids[i], product_ids[j]]))
                product_pairs[key] = product_pairs.get(key, 0) + 1

    # Get product names
    for pair, freq in sorted(product_pairs.items(), key=lambda x: x[1], reverse=True)[:10]:
        p1 = Product.query.get(pair[0])
        p2 = Product.query.get(pair[1])
        if p1 and p2:
            associations.append({
                'products': [p1.name, p2.name],
                'frequency': freq
            })

    # Predicted stockouts
    products = Product.query.filter(Product.is_active == True).all()
    predicted_stockouts = []
    for p in products:
        if p.stock > 0:
            # Calculate daily velocity from recent sales
            sales_with_product = Sale.query.filter(Sale.status != 'Voided').all()
            total_sold = 0
            days = 30
            for s in sales_with_product[-days:]:
                items = json.loads(s.items_json or '[]')
                for item in items:
                    if item.get('productId') == p.id:
                        total_sold += item.get('qty', 0)
            velocity = total_sold / days if days > 0 else 0
            if velocity > 0:
                days_to_empty = int(p.stock / velocity)
                if days_to_empty < 7:
                    predicted_stockouts.append({
                        'product_id': p.id,
                        'product_name': p.name,
                        'current_stock': p.stock,
                        'days_until_empty': days_to_empty
                    })

    return jsonify({
        'sales_forecast': {
            'daily_forecast': forecast,
            'weekly_forecast': forecast * 7,
            'monthly_forecast': forecast * 30,
            'based_on_days': len(recent_values)
        },
        'customer_retention': {
            'total_customers': len(customers),
            'returning_customers': returning_customers,
            'retention_rate': retention_rate,
            'new_customers': len(customers) - returning_customers
        },
        'product_associations': associations,
        'predicted_stockouts': predicted_stockouts
    })

# =============================================================================
# DASHBOARD
# =============================================================================

@app.route('/api/dashboard', methods=['GET'])
@login_required
def dashboard():
    today_str = date.today().isoformat()
    month_str = today_str[:7]
    lowstock_threshold = int(get_setting('lowstock', '10'))

    today_sales = Sale.query.filter_by(date=today_str).filter(Sale.status != 'Voided').all()
    month_sales = Sale.query.filter(
        Sale.date.startswith(month_str), Sale.status != 'Voided'
    ).all()

    today_total = sum(s.total for s in today_sales)
    month_total = sum(s.total for s in month_sales)

    low_stock = Product.query.filter(
        or_(
            Product.stock <= lowstock_threshold,
            Product.stock == 0
        ),
        Product.is_active == True
    ).all()
    recent = Sale.query.filter(Sale.status != 'Voided').order_by(Sale.id.desc()).limit(6).all()

    weekly = []
    for i in range(6, -1, -1):
        d_str = (date.today() - timedelta(days=i)).isoformat()
        day_sales = Sale.query.filter_by(date=d_str).filter(Sale.status != 'Voided').all()
        weekly.append({
            'label': datetime.strptime(d_str, '%Y-%m-%d').strftime('%a'),
            'total': sum(s.total for s in day_sales)
        })

    wholesale_total = sum(s.total for s in Sale.query.filter_by(type='Wholesale').filter(Sale.status != 'Voided').all())
    retail_total = sum(s.total for s in Sale.query.filter_by(type='Retail').filter(Sale.status != 'Voided').all())

    today_expenses = sum(e.amount for e in Expense.query.filter_by(date=today_str).all())
    month_expenses = sum(e.amount for e in Expense.query.filter(Expense.date.startswith(month_str)).all())

    total_loyalty_points = sum(c.loyalty_points or 0 for c in Customer.query.all())

    # Prepare recent sales with invoice numbers
    recent_data = []
    prefix = get_setting('invoice_prefix', 'INV')
    for s in recent:
        data = sale_to_dict(s)
        data['invoiceNumber'] = f"{prefix}-{s.id:05d}"
        recent_data.append(data)

    return jsonify({
        'todayTotal': today_total,
        'todayCount': len(today_sales),
        'monthTotal': month_total,
        'productCount': Product.query.filter_by(is_active=True).count(),
        'lowStockCount': len(low_stock),
        'customerCount': Customer.query.count(),
        'todayExpenses': today_expenses,
        'monthExpenses': month_expenses,
        'recentSales': recent_data,
        'lowStockItems': [{'id': p.id, 'name': p.name, 'stock': p.stock} for p in low_stock],
        'weekly': weekly,
        'wholesaleTotal': wholesale_total,
        'retailTotal': retail_total,
        'totalLoyaltyPoints': total_loyalty_points,
    })

# =============================================================================
# ANALYTICS
# =============================================================================

@app.route('/api/analytics', methods=['GET'])
@login_required
def get_analytics():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')

    # Sales query
    sale_query = Sale.query.filter(Sale.status != 'Voided')
    if date_from:
        sale_query = sale_query.filter(Sale.date >= date_from)
    if date_to:
        sale_query = sale_query.filter(Sale.date <= date_to)
    sales = sale_query.all()

    total_revenue = sum(s.total for s in sales)
    total_cost = sum(s.cost for s in sales)
    gross_profit = total_revenue - total_cost

    # Expenses
    exp_query = Expense.query
    if date_from:
        exp_query = exp_query.filter(Expense.date >= date_from)
    if date_to:
        exp_query = exp_query.filter(Expense.date <= date_to)
    expenses = exp_query.all()
    total_expenses = sum(e.amount for e in expenses)

    # Monthly data
    monthly_data = {}
    for s in sales:
        if s.date and len(s.date) >= 7:
            month = s.date[:7]
            if month not in monthly_data:
                monthly_data[month] = {'revenue': 0, 'cost': 0, 'expenses': 0}
            monthly_data[month]['revenue'] += s.total
            monthly_data[month]['cost'] += s.cost

    # Add expenses to monthly
    for e in expenses:
        if e.date and len(e.date) >= 7:
            month = e.date[:7]
            if month in monthly_data:
                monthly_data[month]['expenses'] += e.amount
            else:
                monthly_data[month] = {'revenue': 0, 'cost': 0, 'expenses': e.amount}

    monthly = [{'label': m, 'revenue': d['revenue'], 'cost': d['cost'], 'expenses': d['expenses']}
               for m, d in sorted(monthly_data.items())[-12:]]

    # Category performance
    category_data = {}
    for s in sales:
        items = json.loads(s.items_json or '[]')
        for item in items:
            cat = 'Other'
            prod = Product.query.get(item.get('productId'))
            if prod and prod.category:
                cat = prod.category
            category_data[cat] = category_data.get(cat, 0) + (item.get('price', 0) * item.get('qty', 0))

    categories = [{'name': c, 'value': v} for c, v in sorted(category_data.items(), key=lambda x: x[1], reverse=True)]

    # Payment methods
    payment_data = {}
    for s in sales:
        method = s.payment_method or 'Cash'
        payment_data[method] = payment_data.get(method, 0) + s.total

    payment_methods = [{'name': m, 'value': v} for m, v in payment_data.items()]

    # Expense categories
    exp_cat_data = {}
    for e in expenses:
        cat = e.category or 'Other'
        exp_cat_data[cat] = exp_cat_data.get(cat, 0) + e.amount

    expense_categories = [{'name': c, 'value': v} for c, v in sorted(exp_cat_data.items(), key=lambda x: x[1], reverse=True)]

    # Top products
    product_sales = {}
    for s in sales:
        items = json.loads(s.items_json or '[]')
        for item in items:
            pid = item.get('productId')
            if pid:
                if pid not in product_sales:
                    product_sales[pid] = {'rev': 0, 'qty': 0}
                product_sales[pid]['rev'] += item.get('price', 0) * item.get('qty', 0)
                product_sales[pid]['qty'] += item.get('qty', 0)

    top_products = []
    for pid, data in sorted(product_sales.items(), key=lambda x: x[1]['rev'], reverse=True)[:10]:
        prod = Product.query.get(pid)
        if prod:
            top_products.append({'name': prod.name, 'rev': data['rev'], 'qty': data['qty']})

    return jsonify({
        'totalRevenue': total_revenue,
        'totalCost': total_cost,
        'grossProfit': gross_profit,
        'totalExpenses': total_expenses,
        'netProfit': gross_profit - total_expenses,
        'margin': (gross_profit / total_revenue * 100) if total_revenue else 0,
        'monthly': monthly,
        'categories': categories,
        'paymentMethods': payment_methods,
        'expenseCategories': expense_categories,
        'topProducts': top_products
    })

# =============================================================================
# EXPORT
# =============================================================================

@app.route('/api/export/<dtype>', methods=['GET'])
@login_required
def export_data(dtype):
    if dtype == 'inventory':
        data = [product_to_dict(p) for p in Product.query.filter_by(is_active=True).all()]
    elif dtype == 'sales':
        sales = Sale.query.all()
        data = []
        prefix = get_setting('invoice_prefix', 'INV')
        for s in sales:
            d = sale_to_dict(s)
            d['invoiceNumber'] = f"{prefix}-{s.id:05d}"
            data.append(d)
    elif dtype == 'customers':
        data = [customer_to_dict(c) for c in Customer.query.all()]
    elif dtype == 'suppliers':
        data = [{'id': s.id, 'name': s.name, 'contact': s.contact, 'phone': s.phone,
                 'email': s.email, 'address': s.address, 'products': s.products,
                 'status': s.status, 'totalSupplied': s.total_supplied} for s in Supplier.query.all()]
    elif dtype == 'expenses':
        data = [{'id': e.id, 'date': e.date, 'category': e.category, 'description': e.description,
                 'amount': e.amount, 'paymentMethod': e.payment_method} for e in Expense.query.all()]
    elif dtype == 'purchases':
        data = [{'id': p.id, 'date': p.date, 'supplierName': p.supplier_name, 'productName': p.product_name,
                 'qty': p.qty, 'unitCost': p.unit_cost, 'total': p.total, 'status': p.status} for p in Purchase.query.all()]
    elif dtype == 'full':
        data = {
            'inventory': [product_to_dict(p) for p in Product.query.filter_by(is_active=True).all()],
            'sales': [sale_to_dict(s) for s in Sale.query.all()],
            'customers': [customer_to_dict(c) for c in Customer.query.all()],
            'suppliers': [{'id': s.id, 'name': s.name, 'contact': s.contact} for s in Supplier.query.all()],
            'expenses': [{'id': e.id, 'date': e.date, 'category': e.category, 'description': e.description, 'amount': e.amount} for e in Expense.query.all()],
            'settings': {s.key: s.value for s in Setting.query.all()},
            'exported_at': datetime.utcnow().isoformat(),
        }
    else:
        return jsonify({'error': 'Unknown export type'}), 400
    return jsonify(data)

# =============================================================================
# IMPORT
# =============================================================================

@app.route('/api/import/full', methods=['POST'])
@login_required
def import_full():
    d = request.json or {}
    imported = {}

    if 'inventory' in d:
        count = 0
        for row in d['inventory']:
            if row.get('name'):
                # Check if product exists by SKU or barcode
                existing = None
                if row.get('sku'):
                    existing = Product.query.filter_by(sku=row['sku']).first()
                if not existing and row.get('barcode'):
                    existing = Product.query.filter_by(barcode=row['barcode']).first()

                if existing:
                    # Update existing
                    existing.name = row['name']
                    existing.category = row.get('category', 'Other')
                    existing.type = row.get('type', 'Both')
                    existing.buy_price = float(row.get('buyPrice', 0))
                    existing.sell_price = float(row.get('sellPrice', 0))
                    existing.wsell_price = float(row.get('wsellPrice', 0))
                    existing.stock = int(float(row.get('stock', 0)))
                    existing.unit = row.get('unit', 'pcs')
                else:
                    db.session.add(Product(
                        name=row['name'],
                        sku=row.get('sku', ''),
                        barcode=row.get('barcode'),
                        category=row.get('category', 'Other'),
                        type=row.get('type', 'Both'),
                        buy_price=float(row.get('buyPrice', 0)),
                        sell_price=float(row.get('sellPrice', 0)),
                        wsell_price=float(row.get('wsellPrice', 0)),
                        stock=int(float(row.get('stock', 0))),
                        unit=row.get('unit', 'pcs')
                    ))
                count += 1
        imported['inventory'] = count

    if 'customers' in d:
        count = 0
        for row in d['customers']:
            if row.get('name'):
                existing = Customer.query.filter_by(phone=row.get('phone', '')).first()
                if existing:
                    existing.name = row['name']
                    existing.email = row.get('email', '')
                    existing.type = row.get('type', 'Retail')
                    existing.address = row.get('address', '')
                else:
                    db.session.add(Customer(
                        name=row['name'],
                        phone=row.get('phone', ''),
                        email=row.get('email', ''),
                        type=row.get('type', 'Retail'),
                        address=row.get('address', ''),
                        created_date=date.today().isoformat()
                    ))
                count += 1
        imported['customers'] = count

    if 'suppliers' in d:
        count = 0
        for row in d['suppliers']:
            if row.get('name'):
                existing = Supplier.query.filter_by(name=row['name']).first()
                if existing:
                    existing.contact = row.get('contact', '')
                    existing.phone = row.get('phone', '')
                    existing.email = row.get('email', '')
                    existing.products = row.get('products', '')
                else:
                    db.session.add(Supplier(
                        name=row['name'],
                        contact=row.get('contact', ''),
                        phone=row.get('phone', ''),
                        email=row.get('email', ''),
                        products=row.get('products', ''),
                        status=row.get('status', 'Active')
                    ))
                count += 1
        imported['suppliers'] = count

    db.session.commit()
    log_action('Full Import', f"Full backup imported: {json.dumps(imported)}")
    return jsonify({'ok': True, 'imported': imported})

@app.route('/api/inventory/bulk', methods=['POST'])
@login_required
def bulk_import_inventory():
    data = request.json or []
    count = 0
    for row in data:
        if row.get('name'):
            existing = None
            if row.get('sku'):
                existing = Product.query.filter_by(sku=row['sku']).first()
            if not existing and row.get('barcode'):
                existing = Product.query.filter_by(barcode=row['barcode']).first()

            if existing:
                existing.name = row['name']
                existing.category = row.get('category', 'Other')
                existing.type = row.get('type', 'Both')
                existing.buy_price = float(row.get('buyPrice', 0))
                existing.sell_price = float(row.get('sellPrice', 0))
                existing.wsell_price = float(row.get('wsellPrice', 0))
                existing.stock = int(float(row.get('stock', 0)))
                existing.unit = row.get('unit', 'pcs')
            else:
                db.session.add(Product(
                    name=row['name'],
                    sku=row.get('sku', ''),
                    barcode=row.get('barcode'),
                    category=row.get('category', 'Other'),
                    type=row.get('type', 'Both'),
                    buy_price=float(row.get('buyPrice', 0)),
                    sell_price=float(row.get('sellPrice', 0)),
                    wsell_price=float(row.get('wsellPrice', 0)),
                    stock=int(float(row.get('stock', 0))),
                    unit=row.get('unit', 'pcs')
                ))
            count += 1
    db.session.commit()
    log_action('Bulk Import', f"Imported {count} products")
    return jsonify({'ok': True, 'imported': count})

@app.route('/api/customers/bulk', methods=['POST'])
@login_required
def bulk_import_customers():
    data = request.json or []
    count = 0
    for row in data:
        if row.get('name'):
            existing = Customer.query.filter_by(phone=row.get('phone', '')).first()
            if existing:
                existing.name = row['name']
                existing.email = row.get('email', '')
                existing.type = row.get('type', 'Retail')
                existing.address = row.get('address', '')
            else:
                db.session.add(Customer(
                    name=row['name'],
                    phone=row.get('phone', ''),
                    email=row.get('email', ''),
                    type=row.get('type', 'Retail'),
                    address=row.get('address', ''),
                    created_date=date.today().isoformat()
                ))
            count += 1
    db.session.commit()
    log_action('Bulk Import', f"Imported {count} customers")
    return jsonify({'ok': True, 'imported': count})

@app.route('/api/suppliers/bulk', methods=['POST'])
@login_required
def bulk_import_suppliers():
    data = request.json or []
    count = 0
    for row in data:
        if row.get('name'):
            existing = Supplier.query.filter_by(name=row['name']).first()
            if existing:
                existing.contact = row.get('contact', '')
                existing.phone = row.get('phone', '')
                existing.email = row.get('email', '')
                existing.products = row.get('products', '')
            else:
                db.session.add(Supplier(
                    name=row['name'],
                    contact=row.get('contact', ''),
                    phone=row.get('phone', ''),
                    email=row.get('email', ''),
                    products=row.get('products', ''),
                    status=row.get('status', 'Active')
                ))
            count += 1
    db.session.commit()
    log_action('Bulk Import', f"Imported {count} suppliers")
    return jsonify({'ok': True, 'imported': count})

# =============================================================================
# EXPENSES
# =============================================================================

@app.route('/api/expenses', methods=['GET'])
@login_required
def get_expenses():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    category = request.args.get('category', '')
    query = Expense.query.order_by(Expense.id.desc())
    if date_from:
        query = query.filter(Expense.date >= date_from)
    if date_to:
        query = query.filter(Expense.date <= date_to)
    if category:
        query = query.filter_by(category=category)
    return jsonify([{
        'id': e.id, 'date': e.date, 'category': e.category or '',
        'description': e.description or '', 'amount': e.amount,
        'paymentMethod': e.payment_method or 'Cash', 'notes': e.notes or ''
    } for e in query.all()])

@app.route('/api/expenses', methods=['POST'])
@login_required
def add_expense():
    d = request.json or {}
    if not d.get('description') or not d.get('amount'):
        return jsonify({'error': 'Description and amount required'}), 400
    e = Expense(
        date=d.get('date', date.today().isoformat()),
        category=d.get('category', 'General'),
        description=d['description'],
        amount=float(d['amount']),
        payment_method=d.get('paymentMethod', 'Cash'),
        notes=d.get('notes', '')
    )
    db.session.add(e)
    db.session.commit()
    log_action('Expense Added', f"Added expense: {e.description} - {e.amount}")
    return jsonify({'ok': True}), 201

@app.route('/api/expenses/<int:eid>', methods=['PUT'])
@login_required
def update_expense(eid):
    e = Expense.query.get_or_404(eid)
    d = request.json or {}
    e.date = d.get('date', e.date)
    e.category = d.get('category', e.category)
    e.description = d.get('description', e.description)
    e.amount = float(d.get('amount', e.amount))
    e.payment_method = d.get('paymentMethod', e.payment_method)
    e.notes = d.get('notes', e.notes)
    db.session.commit()
    log_action('Expense Updated', f"Updated expense: {e.description}")
    return jsonify({'ok': True})

@app.route('/api/expenses/<int:eid>', methods=['DELETE'])
@login_required
def delete_expense(eid):
    e = Expense.query.get_or_404(eid)
    db.session.delete(e)
    db.session.commit()
    log_action('Expense Deleted', f"Deleted expense: {e.description}")
    return jsonify({'ok': True})

@app.route('/api/expenses/categories', methods=['GET'])
@login_required
def get_expense_categories():
    cats = db.session.query(Expense.category).distinct().all()
    default_cats = ['Rent', 'Utilities', 'Salaries', 'Transport', 'Maintenance',
                    'Marketing', 'Supplies', 'Insurance', 'Taxes', 'General']
    existing = [c[0] for c in cats if c[0]]
    all_cats = sorted(set(default_cats + existing))
    return jsonify(all_cats)

# =============================================================================
# SUPPLIERS
# =============================================================================

@app.route('/api/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    q = request.args.get('q', '').lower()
    query = Supplier.query
    if q:
        query = query.filter(Supplier.name.ilike(f'%{q}%'))
    return jsonify([{
        'id': s.id, 'name': s.name, 'contact': s.contact or '', 'phone': s.phone or '',
        'email': s.email or '', 'address': s.address or '', 'products': s.products or '',
        'status': s.status, 'notes': s.notes or '', 'totalSupplied': s.total_supplied or 0,
        'payment_terms': s.payment_terms or 'Net 30'
    } for s in query.all()])

@app.route('/api/suppliers', methods=['POST'])
@login_required
def add_supplier():
    d = request.json or {}
    if not d.get('name'):
        return jsonify({'error': 'Supplier name required'}), 400
    s = Supplier(
        name=d['name'], contact=d.get('contact', ''), phone=d.get('phone', ''),
        email=d.get('email', ''), address=d.get('address', ''),
        products=d.get('products', ''), status=d.get('status', 'Active'),
        notes=d.get('notes', ''), payment_terms=d.get('payment_terms', 'Net 30')
    )
    db.session.add(s)
    db.session.commit()
    log_action('Supplier Added', f"Added supplier: {s.name}")
    return jsonify({'ok': True}), 201

@app.route('/api/suppliers/<int:sid>', methods=['PUT'])
@login_required
def update_supplier(sid):
    s = Supplier.query.get_or_404(sid)
    d = request.json or {}
    s.name = d.get('name', s.name)
    s.contact = d.get('contact', s.contact)
    s.phone = d.get('phone', s.phone)
    s.email = d.get('email', s.email)
    s.address = d.get('address', s.address)
    s.products = d.get('products', s.products)
    s.status = d.get('status', s.status)
    s.notes = d.get('notes', s.notes)
    s.payment_terms = d.get('payment_terms', s.payment_terms)
    db.session.commit()
    log_action('Supplier Updated', f"Updated supplier: {s.name}")
    return jsonify({'ok': True})

@app.route('/api/suppliers/<int:sid>', methods=['DELETE'])
@login_required
def delete_supplier(sid):
    s = Supplier.query.get_or_404(sid)
    db.session.delete(s)
    db.session.commit()
    log_action('Supplier Deleted', f"Deleted supplier: {s.name}")
    return jsonify({'ok': True})

# =============================================================================
# PURCHASES
# =============================================================================

@app.route('/api/purchases', methods=['GET'])
@login_required
def get_purchases():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    query = Purchase.query.order_by(Purchase.id.desc())
    if date_from:
        query = query.filter(Purchase.date >= date_from)
    if date_to:
        query = query.filter(Purchase.date <= date_to)
    return jsonify([{
        'id': p.id, 'date': p.date, 'supplierId': p.supplier_id, 'supplierName': p.supplier_name or '',
        'productId': p.product_id, 'productName': p.product_name or '',
        'qty': p.qty, 'unitCost': p.unit_cost, 'total': p.total,
        'status': p.status, 'notes': p.notes or ''
    } for p in query.all()])

@app.route('/api/purchases', methods=['POST'])
@login_required
def add_purchase():
    d = request.json or {}
    supp = Supplier.query.get(d.get('supplierId'))
    prod = Product.query.get(d.get('productId'))
    qty = int(d.get('qty', 0))
    cost = float(d.get('unitCost', 0))
    status = d.get('status', 'Received')
    total = qty * cost

    p = Purchase(
        date=d.get('date', date.today().isoformat()),
        supplier_id=d.get('supplierId'), supplier_name=supp.name if supp else '',
        product_id=d.get('productId'), product_name=prod.name if prod else '',
        qty=qty, unit_cost=cost, total=total, status=status,
        notes=d.get('notes', ''), batch_number=d.get('batchNumber')
    )

    if status == 'Received' and prod:
        prod.stock += qty
        prod.buy_price = cost
        prod.last_restock_date = date.today().isoformat()

    if supp:
        supp.total_supplied = (supp.total_supplied or 0) + total

    db.session.add(p)
    db.session.commit()
    log_action('Purchase Added', f"Added purchase: {prod.name if prod else 'Unknown'} x{qty}")
    return jsonify({'ok': True}), 201

@app.route('/api/purchases/<int:pid>', methods=['DELETE'])
@login_required
def delete_purchase(pid):
    p = Purchase.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    log_action('Purchase Deleted', f"Deleted purchase #{p.id}")
    return jsonify({'ok': True})

# =============================================================================
# PURCHASE ORDERS
# =============================================================================

@app.route('/api/purchase-orders', methods=['POST'])
@login_required
def create_purchase_order():
    d = request.json or {}
    supplier_id = d.get('supplier_id')
    items = d.get('items', [])

    if not supplier_id or not items:
        return jsonify({'error': 'Supplier and items required'}), 400

    subtotal = sum(item['qty'] * item['cost'] for item in items)
    total = subtotal

    po = PurchaseOrder(
        po_number=generate_po_number(),
        supplier_id=supplier_id,
        supplier_name=d.get('supplier_name', ''),
        order_date=date.today().isoformat(),
        expected_delivery=d.get('expected_delivery'),
        status='Draft',
        subtotal=subtotal,
        total=total,
        notes=d.get('notes', ''),
        items_json=json.dumps(items),
        created_by=session.get('user_id'),
        created_at=datetime.utcnow().isoformat()
    )
    db.session.add(po)
    db.session.commit()

    # Also add to purchases
    for item in items:
        p = Purchase(
            date=date.today().isoformat(),
            supplier_id=supplier_id,
            supplier_name=d.get('supplier_name', ''),
            product_id=item['product_id'],
            product_name=item.get('name', ''),
            qty=item['qty'],
            unit_cost=item['cost'],
            total=item['qty'] * item['cost'],
            status='Pending',
            po_number=po.po_number
        )
        db.session.add(p)

    db.session.commit()
    log_action('Purchase Order Created', f"PO #{po.po_number} created")
    return jsonify({'ok': True, 'po_number': po.po_number})

# =============================================================================
# USERS
# =============================================================================

ROLE_PERMISSIONS = {
    'Admin': None,
    'Manager': ['dashboard','inventory','categories','sales','customers','suppliers','purchases','expenses','analytics','reports','export','import','users','settings'],
    'Cashier': ['dashboard','sales','customers'],
    'Stock Keeper': ['dashboard','inventory','categories','purchases','suppliers'],
    'Accountant': ['dashboard','analytics','expenses','export','sales','reports'],
}

@app.route('/api/users', methods=['GET'])
@login_required
def get_users():
    users = User.query.all()
    return jsonify([{
        'id': u.id, 'name': u.name, 'username': u.username,
        'role': u.role, 'status': u.status,
        'permissions': json.loads(u.permissions) if u.permissions else None,
        'lastLogin': u.last_login,
        'createdAt': u.created_at
    } for u in users])

@app.route('/api/users', methods=['POST'])
@login_required
def add_user():
    d = request.json or {}
    name = d.get('name', '').strip()
    username = d.get('username', '').strip()
    password = d.get('password', '')
    role = d.get('role', 'Cashier')
    if not name or not username or not password:
        return jsonify({'error': 'All fields required'}), 400
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    custom_perms = d.get('permissions')
    if custom_perms is not None:
        perms_json = json.dumps(custom_perms)
    elif role in ROLE_PERMISSIONS and ROLE_PERMISSIONS[role] is not None:
        perms_json = json.dumps(ROLE_PERMISSIONS[role])
    else:
        perms_json = None

    u = User(name=name, username=username, password=password, role=role,
             status=d.get('status', 'Active'), permissions=perms_json,
             created_at=datetime.utcnow().isoformat())
    db.session.add(u)
    db.session.commit()
    log_action('User Added', f"Added user: {username} ({role})")
    return jsonify({'ok': True}), 201

@app.route('/api/users/<int:uid>', methods=['PUT'])
@login_required
def update_user(uid):
    u = User.query.get_or_404(uid)
    d = request.json or {}

    if 'name' in d:
        u.name = d['name']
    if 'role' in d:
        u.role = d['role']
        role = d['role']
        if d.get('permissions') is not None:
            u.permissions = json.dumps(d['permissions'])
        elif role in ROLE_PERMISSIONS and ROLE_PERMISSIONS[role] is not None:
            u.permissions = json.dumps(ROLE_PERMISSIONS[role])
        else:
            u.permissions = None
    if 'status' in d:
        u.status = d['status']
    if 'password' in d and d['password']:
        u.password = d['password']
    if 'permissions' in d and d['permissions'] is not None:
        u.permissions = json.dumps(d['permissions'])

    db.session.commit()
    log_action('User Updated', f"Updated user: {u.username}")
    return jsonify({'ok': True})

@app.route('/api/users/<int:uid>', methods=['DELETE'])
@login_required
def delete_user(uid):
    if uid == 1:
        return jsonify({'error': 'Cannot delete main admin'}), 403
    u = User.query.get_or_404(uid)
    db.session.delete(u)
    db.session.commit()
    log_action('User Deleted', f"Deleted user: {u.username}")
    return jsonify({'ok': True})

@app.route('/api/roles', methods=['GET'])
@login_required
def get_roles():
    return jsonify([
        {'role': r, 'permissions': p}
        for r, p in ROLE_PERMISSIONS.items()
    ])

# =============================================================================
# CLEAR DATA
# =============================================================================

@app.route('/api/clear/<dtype>', methods=['DELETE'])
@login_required
def clear_data(dtype):
    if dtype == 'sales':
        Sale.query.delete()
    elif dtype == 'inventory':
        Product.query.delete()
    elif dtype == 'customers':
        Customer.query.delete()
    elif dtype == 'suppliers':
        Supplier.query.delete()
    elif dtype == 'expenses':
        Expense.query.delete()
    elif dtype == 'purchases':
        Purchase.query.delete()
    elif dtype == 'audit-logs':
        AuditLog.query.delete()
    else:
        return jsonify({'error': 'Unknown type'}), 400
    db.session.commit()
    log_action('Clear Data', f"Cleared {dtype} data")
    return jsonify({'ok': True})

@app.route('/api/reset', methods=['DELETE'])
@login_required
def reset_all():
    # Clear all data except the main admin user
    for model in [Sale, SuspendedSale, Purchase, PurchaseOrder, Product, Customer, Supplier, Expense, Category, Setting, AuditLog, LoyaltyTransaction, LoyaltyReward]:
        model.query.delete()
    # Keep only admin user (id=1)
    User.query.filter(User.id != 1).delete()
    db.session.commit()
    seed_data()
    log_action('Factory Reset', "System factory reset performed")
    return jsonify({'ok': True})

# =============================================================================
# SEED DATA
# =============================================================================

def seed_data():
    if User.query.count() == 0:
        db.session.add(User(
            name="Deboat Admin", username="admin",
            password="admin123", role="Admin", status="Active",
            created_at=datetime.utcnow().isoformat()
        ))
        db.session.commit()

    if Category.query.count() == 0:
        cats = [
            Category(name='Beverages', description='Drinks and liquids', color='#2d6a4f', loyalty_points_multiplier=1.0),
            Category(name='Grains', description='Rice, flour, cereals', color='#f4a261', loyalty_points_multiplier=1.2),
            Category(name='Dairy', description='Milk, cheese, eggs', color='#52b788', loyalty_points_multiplier=1.0),
            Category(name='Snacks', description='Biscuits, chips, sweets', color='#e76f51', loyalty_points_multiplier=1.0),
            Category(name='Personal Care', description='Hygiene and beauty', color='#264653', loyalty_points_multiplier=1.0),
            Category(name='Cleaning', description='Detergents and cleaners', color='#2a9d8f', loyalty_points_multiplier=1.0),
            Category(name='Condiments', description='Oils, sauces, spices', color='#e9c46a', loyalty_points_multiplier=1.0),
            Category(name='Frozen', description='Frozen foods', color='#4cc9f0', loyalty_points_multiplier=1.0),
            Category(name='Other', description='Miscellaneous items', color='#6b7280', loyalty_points_multiplier=1.0),
        ]
        db.session.add_all(cats)
        db.session.commit()

    if LoyaltyReward.query.count() == 0:
        rewards = [
            LoyaltyReward(
                name='₵5 Discount',
                description='Redeem 500 points for ₵5 off your next purchase',
                points_required=500,
                reward_type='discount',
                discount_value=5.0
            ),
            LoyaltyReward(
                name='₵10 Discount',
                description='Redeem 1000 points for ₵10 off your next purchase',
                points_required=1000,
                reward_type='discount',
                discount_value=10.0
            ),
            LoyaltyReward(
                name='₵20 Discount',
                description='Redeem 2000 points for ₵20 off your next purchase',
                points_required=2000,
                reward_type='discount',
                discount_value=20.0
            ),
        ]
        db.session.add_all(rewards)
        db.session.commit()

    defaults = {
        'name': "Deboat's Favour",
        'address': '123 Market Street, Accra, Ghana',
        'phone': '+233 24 000 0000',
        'email': 'info@deboatfavour.com',
        'currency': '₵',
        'lowstock': '10',
        'footer': "Thank you for shopping at Deboat's Favour!",
        'tax_rate': '0',
        'tax_name': 'Tax',
        'invoice_prefix': 'INV',
        'theme_brand': '#1a3a2a',
        'theme_brand_mid': '#2d6a4f',
        'theme_brand_light': '#52b788',
        'theme_accent': '#f4a261',
        'db_type': 'sqlite',
        'system_name': "Deboat's Favour",
        'system_tagline': 'Management System',
        'smtp_host': 'smtp.gmail.com',
        'smtp_port': '587',
        'smtp_user': '',
        'smtp_password': '',
        'alert_email': '',
        'enable_audit_logs': 'true',
        'enable_email_alerts': 'false',
        'loyalty_enabled': 'true',
        'points_to_currency_rate': '100',
        'birthday_discount': '10',
        'points_expiry': '365',
        'silver_tier': '2000',
        'gold_tier': '5000',
        'platinum_tier': '10000',
    }
    for k, v in defaults.items():
        if not Setting.query.get(k):
            db.session.add(Setting(key=k, value=v))
    db.session.commit()

# =============================================================================
# INIT
# =============================================================================

with app.app_context():
    db.create_all()
    seed_data()

if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')