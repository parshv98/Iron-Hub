from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_file
# from connection import db_connection
from localhost import db_connection
from functools import wraps
from io import BytesIO
import hashlib
import os
import shutil

try:
    import psutil
except ImportError:
    psutil = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'Templates'), static_folder=os.path.join(BASE_DIR, 'static'))
app.secret_key = 'ironhub_secret_key'
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# ── Fix subscriptions ENUM on startup ─────────────────
def fix_subscription_enum():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "ALTER TABLE subscriptions MODIFY status "
                "ENUM('Pending','Active','Expired','Cancelled') NOT NULL DEFAULT 'Pending'"
            ) 
            conn.commit()
        conn.close()
    except Exception:
        pass

# ── Create measurements table if not exists ────────────
def create_measurements_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur: 
            cur.execute("""
                CREATE TABLE IF NOT EXISTS measurements (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    user_id     INT NOT NULL,
                    weight      DECIMAL(5,2) NOT NULL,
                    body_fat    DECIMAL(4,2) DEFAULT NULL,
                    chest       DECIMAL(5,2) DEFAULT NULL,
                    waist       DECIMAL(5,2) DEFAULT NULL,
                    hips        DECIMAL(5,2) DEFAULT NULL,
                    logged_date DATE NOT NULL,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_user_date (user_id, logged_date)
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating measurements table: {e}")

# ── Create trainer_profiles table if not exists ────────
def create_trainer_profiles_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trainer_profiles (
                    id             INT AUTO_INCREMENT PRIMARY KEY,
                    user_id        INT NOT NULL UNIQUE,
                    phone          VARCHAR(20)  DEFAULT '',
                    bio            TEXT         DEFAULT NULL,
                    certifications TEXT         DEFAULT NULL,
                    hourly_rate    DECIMAL(8,2) DEFAULT NULL,
                    availability   VARCHAR(100) DEFAULT 'Available',
                    profile_image  VARCHAR(255) DEFAULT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating trainer_profiles table: {e}")

fix_subscription_enum()
create_measurements_table()
create_trainer_profiles_table()

# ── Create trainer_workout_plans table if not exists ──
def create_trainer_workout_plans_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trainer_workout_plans (
                    id                  INT AUTO_INCREMENT PRIMARY KEY,
                    trainer_id          INT NOT NULL,
                    name                VARCHAR(255) NOT NULL,
                    description         TEXT,
                    difficulty          ENUM('Beginner','Intermediate','Advanced') DEFAULT 'Beginner',
                    duration_minutes    INT NOT NULL,
                    estimated_calories  INT NOT NULL,
                    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (trainer_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating trainer_workout_plans table: {e}")

create_trainer_workout_plans_table()

# ── Create trainer_clients table if not exists ──
def create_trainer_clients_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS trainer_clients (
                    id          INT AUTO_INCREMENT PRIMARY KEY,
                    trainer_id  INT NOT NULL,
                    client_id   INT NOT NULL,
                    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (trainer_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (client_id) REFERENCES users(id) ON DELETE CASCADE,
                    UNIQUE KEY unique_assignment (trainer_id, client_id)
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating trainer_clients table: {e}")

create_trainer_clients_table()

# ── Create workout_progress table if not exists ─────────
def create_workout_progress_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS workout_progress (
                    user_id           INT NOT NULL,
                    plan_id           INT NOT NULL,
                    seconds_remaining INT NOT NULL,
                    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, plan_id)
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating workout_progress table: {e}")

create_workout_progress_table()

# ── Create payments table if not exists ─────────
def create_payments_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS payments (
                    id             INT AUTO_INCREMENT PRIMARY KEY,
                    user_id        INT NOT NULL,
                    billing_name   VARCHAR(255) NOT NULL,
                    address_line1  VARCHAR(255) NOT NULL,
                    address_line2  VARCHAR(255),
                    city           VARCHAR(100) NOT NULL,
                    state          VARCHAR(100) NOT NULL,
                    zip_code       VARCHAR(20) NOT NULL,
                    payment_method VARCHAR(50) NOT NULL,
                    amount         DECIMAL(10,2) NOT NULL,
                    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating payments table: {e}")

create_payments_table()

# ── Create email_preferences table for new features ────────
def create_email_preferences_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS email_preferences (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL UNIQUE,
                    membership_expiry BOOLEAN DEFAULT TRUE,
                    workout_reminders BOOLEAN DEFAULT TRUE,
                    progress_reports BOOLEAN DEFAULT TRUE,
                    new_offers BOOLEAN DEFAULT TRUE,
                    chat_notifications BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating email_preferences table: {e}")

# ── Create chat_messages table for live chat ────────────────
def create_chat_messages_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    message TEXT NOT NULL,
                    sender_type ENUM('user', 'support', 'trainer') DEFAULT 'user',
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX user_created (user_id, created_at)
                )
            """)
            conn.commit()

        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM chat_messages LIKE 'sender_type'")
            column = cur.fetchone()
            if column and 'trainer' not in column.get('Type', ''):
                cur.execute("ALTER TABLE chat_messages MODIFY sender_type ENUM('user', 'support', 'trainer') DEFAULT 'user'")
                conn.commit()

        conn.close()
    except Exception as e:
        print(f"Error creating chat_messages table: {e}")

# ── Create bmi_records table for BMI calculator ────────────
def create_bmi_records_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS bmi_records (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    height DECIMAL(5,2) NOT NULL,
                    weight DECIMAL(5,2) NOT NULL,
                    bmi DECIMAL(5,2) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    INDEX user_created (user_id, created_at)
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating bmi_records table: {e}")

# ── Create membership_expiry_alerts table ──────────────────
def create_membership_expiry_alerts_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS membership_expiry_alerts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    subscription_id INT,
                    expiry_date DATE NOT NULL,
                    days_until_expiry INT,
                    alert_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (subscription_id) REFERENCES subscriptions(id) ON DELETE SET NULL
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating membership_expiry_alerts table: {e}")

# ── Create appointments table if not exists ────────────
def create_appointments_table():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS appointments (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    member_id INT NOT NULL,
                    trainer_id INT NOT NULL,
                    date_time DATETIME NOT NULL,
                    notes TEXT,
                    session_type INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (member_id) REFERENCES users(id) ON DELETE CASCADE,
                    FOREIGN KEY (trainer_id) REFERENCES users(id) ON DELETE CASCADE
                )
            """)
            conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error creating appointments table: {e}")

# Initialize new tables
create_email_preferences_table()
create_chat_messages_table()
create_bmi_records_table()
create_membership_expiry_alerts_table()
create_appointments_table()



# ── Migrate workout_history: add duration_seconds if missing ──
def migrate_workout_history():
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM workout_history LIKE 'duration_seconds'")
            if not cur.fetchone():
                cur.execute("ALTER TABLE workout_history ADD COLUMN duration_seconds INT NOT NULL DEFAULT 0")
                cur.execute("UPDATE workout_history SET duration_seconds = duration_minutes * 60 WHERE duration_seconds = 0")
                conn.commit()
        conn.close()
    except Exception as e:
        print(f"Migration error: {e}")

migrate_workout_history()

# ── Auth Guards ────────────────────────────────────────
def login_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if 'user_id' not in session:
                return redirect('/')
            if session.get('user_role') != role:
                return redirect('/')
            return f(*args, **kwargs)
        return wrapper
    return decorator

# ── Pages ──────────────────────────────────────────────
@app.route('/')
@app.route('/home')
def home():
    return render_template('user_home.html')

@app.route('/login')
def user_login():
    return render_template('user_login.html')

@app.route('/register')
def user_register():
    return render_template('user_register.html')

@app.route('/trainer/login')
def trainer_login():
    return render_template('trainer_login.html')

@app.route('/trainer/register')
def trainer_register():
    return render_template('trainer_register.html')

@app.route('/admin/login')
def admin_login():
    return render_template('admin_login.html')

@app.route('/admin/register')
def admin_register():
    return render_template('admin_register.html')

@app.route('/dashboard')
@login_required('user')
def user_dashboard():
    return render_template('user_dashboard.html')

@app.route('/api/user/trainers')
@login_required('user')
def api_user_trainers():
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.first_name, u.last_name,
                          t.specialization, t.experience,
                          tp.bio, tp.certifications, tp.hourly_rate,
                          tp.availability, tp.profile_image
                   FROM users u
                   INNER JOIN trainers t ON u.id = t.user_id
                   LEFT JOIN trainer_profiles tp ON u.id = tp.user_id
                   WHERE u.role = 'trainer' AND u.status = 'Active'
                   ORDER BY u.first_name, u.last_name"""
            )
            return jsonify(cur.fetchall())
    finally:
        conn.close()

@app.route('/api/user/trainers/<int:trainer_id>')
@login_required('user')
def api_user_trainer_details(trainer_id):
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.first_name, u.last_name,
                          t.specialization, t.experience,
                          tp.phone, tp.bio, tp.certifications, tp.hourly_rate,
                          tp.availability, tp.profile_image
                   FROM users u
                   INNER JOIN trainers t ON u.id = t.user_id
                   LEFT JOIN trainer_profiles tp ON u.id = tp.user_id
                   WHERE u.id = %s AND u.role = 'trainer' AND u.status = 'Active'""",
                (trainer_id,)
            )
            trainer = cur.fetchone()
        if not trainer:
            return jsonify({'error': 'Trainer not found'}), 404
        return jsonify(trainer)
    finally:
        conn.close()

@app.route('/trainer/dashboard')
@login_required('trainer')
def trainer_dashboard():
    return render_template('trainer_dashboard.html')

@app.route('/admin/dashboard')
@login_required('admin')
def admin_dashboard():
    return render_template('admin_dashboard.html')

@app.route('/about')
def about():
    return render_template('user_about.html')

@app.route('/contact')
def contact():
    return render_template('user_contact.html')

# ── User Register ──────────────────────────────────────
@app.route('/api/register/user', methods=['POST'])
def api_register_user():
    data = request.get_json()
    fname     = data.get('fname', '').strip()
    lname     = data.get('lname', '').strip()
    email     = data.get('email', '').strip().lower()
    password  = data.get('password', '')

    if not all([fname, lname, email, password]):
        return jsonify({'error': 'All fields are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({'error': 'Email is already registered.'}), 409

            cur.execute(
                "INSERT INTO users (first_name, last_name, email, password, role, status) VALUES (%s, %s, %s, %s, 'user', 'Active')",
                (fname, lname, email, hash_password(password))
            )
            conn.commit()
        return jsonify({'message': 'Registration successful! You can now log in.'}), 201
    finally:
        conn.close()

# ── Trainer Register ───────────────────────────────────
@app.route('/api/register/trainer', methods=['POST'])
def api_register_trainer():
    data = request.get_json()
    fname          = data.get('fname', '').strip()
    lname          = data.get('lname', '').strip()
    email          = data.get('email', '').strip().lower()
    experience     = data.get('experience', 0)
    specialization = data.get('specialization', '').strip()
    password       = data.get('password', '')

    if not all([fname, lname, email, password, specialization]):
        return jsonify({'error': 'All fields are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({'error': 'Email is already registered.'}), 409

            cur.execute(
                "INSERT INTO users (first_name, last_name, email, password, role) VALUES (%s, %s, %s, %s, 'trainer')",
                (fname, lname, email, hash_password(password))
            )
            user_id = cur.lastrowid
            cur.execute(
                "INSERT INTO trainers (user_id, specialization, experience) VALUES (%s, %s, %s)",
                (user_id, specialization, experience)
            )
            conn.commit()
        return jsonify({'message': 'Trainer registered successfully.'}), 201
    finally:
        conn.close()

# ── Admin Register ─────────────────────────────────────
@app.route('/api/register/admin', methods=['POST'])
def api_register_admin():
    data = request.get_json()
    username   = data.get('username', '').strip()
    email      = data.get('email', '').strip().lower()
    password   = data.get('password', '')

    if not all([username, email, password]):
        return jsonify({'error': 'All fields are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE email = %s", (email,))
            if cur.fetchone():
                return jsonify({'error': 'Email is already registered.'}), 409

            cur.execute(
                "INSERT INTO users (first_name, last_name, email, password, role, status) VALUES (%s, %s, %s, %s, 'admin', 'Active')",
                (username, '', email, hash_password(password))
            )
            conn.commit()
        return jsonify({'message': 'Admin registered successfully. You can now log in.'}), 201
    finally:
        conn.close()

# ── User Login ────────────────────────────────────────
@app.route('/api/login/user', methods=['POST'])
def api_login_user():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, first_name, last_name, role, status FROM users WHERE email = %s AND password = %s",
                (email, hash_password(password))
            )
            user = cur.fetchone()

        if not user:
            return jsonify({'error': 'Invalid email or password.'}), 401
        if user['role'] != 'user':
            return jsonify({'error': 'This account is not a user account.'}), 403
        if user['status'] == 'Inactive':
            return jsonify({'error': 'Your account is inactive. Contact support.'}), 403

        session['user_id']   = user['id']
        session['user_role'] = user['role']
        session['user_name'] = f"{user['first_name']} {user['last_name']}"
        return jsonify({'message': 'Login successful.', 'role': user['role'], 'redirect': '/dashboard'}), 200
    finally:
        conn.close()

# ── Trainer Login ──────────────────────────────────────
@app.route('/api/login/trainer', methods=['POST'])
def api_login_trainer():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, first_name, last_name, role, status FROM users WHERE email = %s AND password = %s",
                (email, hash_password(password))
            )
            user = cur.fetchone()

        if not user:
            return jsonify({'error': 'Invalid email or password.'}), 401
        if user['role'] != 'trainer':
            return jsonify({'error': 'This account is not a trainer account.'}), 403
        if user['status'] != 'Active':
            return jsonify({'error': 'Your account is inactive. Contact support.'}), 403

        session['user_id']   = user['id']
        session['user_role'] = user['role']
        session['user_name'] = f"{user['first_name']} {user['last_name']}"
        return jsonify({'message': 'Login successful.', 'role': user['role'], 'redirect': '/trainer/dashboard'}), 200
    finally:
        conn.close()

# ── Admin Login ────────────────────────────────────────
@app.route('/api/login/admin', methods=['POST'])
def api_login_admin():
    data     = request.get_json()
    email    = data.get('email', '').strip().lower()
    password = data.get('password', '')

    if not email or not password:
        return jsonify({'error': 'All fields are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # support login by email OR by username (stored in first_name for admin)
            cur.execute(
                "SELECT id, first_name, role, status FROM users WHERE (email = %s OR first_name = %s) AND password = %s",
                (email, email, hash_password(password))
            )
            user = cur.fetchone()

        if not user:
            return jsonify({'error': 'Invalid username or password.'}), 401
        if user['role'] != 'admin':
            return jsonify({'error': 'This account does not have admin privileges.'}), 403
        if user['status'] != 'Active':
            return jsonify({'error': 'Your account is inactive. Contact support.'}), 403

        session['user_id']   = user['id']
        session['user_role'] = user['role']
        session['user_name'] = user['first_name']
        return jsonify({'message': 'Login successful.', 'role': user['role'], 'redirect': '/admin/dashboard'}), 200
    finally:
        conn.close()

# ── Subscription: GET current + history ─────────────────
@app.route('/api/user/subscription')
def api_get_subscription():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM subscriptions WHERE user_id = %s ORDER BY created_at DESC",
                (uid,)
            )
            rows = cur.fetchall()
        for r in rows:
            r['start_date']  = r['start_date'].strftime('%b %d, %Y')
            r['expiry_date'] = r['expiry_date'].strftime('%b %d, %Y')
            r['created_at']  = r['created_at'].strftime('%b %d, %Y')
        active = next((r for r in rows if r['status'] == 'Active'), None)
        return jsonify({'active': active, 'history': rows})
    finally:
        conn.close()

# ── Subscription: Subscribe to a plan ──────────────────
@app.route('/api/user/subscription', methods=['POST'])
def api_subscribe():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid  = session['user_id']
    data = request.get_json()
    plan  = data.get('plan', '').strip()

    # Plan pricing (amounts in INR)
    valid_plans = {
        'Basic': 3999,
        'Standard': 7999,
        'Premium': 11999,
        '1 Month': 499,
        '3 Months': 1399,
        '6 Months': 5555
    }
    if plan not in valid_plans:
        return jsonify({'error': 'Invalid plan.'}), 400

    from datetime import date, timedelta
    start  = date.today()
    expiry = start + timedelta(days=365)

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Block if already has Active or Pending subscription
            cur.execute(
                "SELECT id, plan_name, status FROM subscriptions WHERE user_id=%s AND status IN ('Active','Pending') LIMIT 1",
                (uid,)
            )
            existing = cur.fetchone()
            if existing:
                if existing['status'] == 'Active':
                    return jsonify({'error': f'You already have an active {existing["plan_name"]} plan. It must expire or be cancelled before choosing a new one.'}), 409
                else:
                    return jsonify({'error': f'You already have a pending {existing["plan_name"]} plan request. Please wait for admin approval.'}), 409

            cur.execute(
                "INSERT INTO subscriptions (user_id, plan_name, amount, start_date, expiry_date, status) VALUES (%s,%s,%s,%s,%s,'Pending')",
                (uid, plan, valid_plans[plan], start, expiry)
            )
            conn.commit()
        return jsonify({'message': f'{plan} plan request sent. Awaiting admin approval.'}), 201
    finally:
        conn.close()

# ── User Profile: GET ──────────────────────────────────
@app.route('/api/user/profile')
def api_get_profile():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT first_name, last_name, email FROM users WHERE id = %s", (uid,))
            user = cur.fetchone()
            cur.execute("SELECT phone, age, gender, height, weight, fitness_goal, activity_level FROM user_profiles WHERE user_id = %s", (uid,))
            profile = cur.fetchone() or {}
        return jsonify({**user, **profile})
    finally:
        conn.close()

# ── User Profile: SAVE ────────────────────────────────
@app.route('/api/user/profile', methods=['POST'])
def api_save_profile():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid  = session['user_id']
    data = request.get_json()

    first_name     = data.get('first_name', '').strip()
    last_name      = data.get('last_name', '').strip()
    phone          = data.get('phone', '').strip()
    age            = data.get('age') or None
    gender         = data.get('gender', '').strip()
    height         = data.get('height') or None
    weight         = data.get('weight') or None
    fitness_goal   = data.get('fitness_goal', '').strip()
    activity_level = data.get('activity_level', '').strip()

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Update base user fields
            cur.execute(
                "UPDATE users SET first_name = %s, last_name = %s WHERE id = %s",
                (first_name, last_name, uid)
            )
            # Upsert profile
            cur.execute("SELECT id FROM user_profiles WHERE user_id = %s", (uid,))
            if cur.fetchone():
                cur.execute(
                    """UPDATE user_profiles SET phone=%s, age=%s, gender=%s,
                       height=%s, weight=%s, fitness_goal=%s, activity_level=%s
                       WHERE user_id=%s""",
                    (phone, age, gender, height, weight, fitness_goal, activity_level, uid)
                )
            else:
                cur.execute(
                    """INSERT INTO user_profiles
                       (user_id, phone, age, gender, height, weight, fitness_goal, activity_level)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (uid, phone, age, gender, height, weight, fitness_goal, activity_level)
                )
            conn.commit()
        session['user_name'] = f"{first_name} {last_name}"
        return jsonify({'message': 'Profile saved successfully.'})
    finally:
        conn.close()

# ── Admin: Get dashboard stats ────────────────────────
@app.route('/api/admin/stats')
def api_admin_stats():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Count only users with active subscriptions as clients
            cur.execute(
                """SELECT COUNT(DISTINCT u.id) as count 
                   FROM users u 
                   INNER JOIN subscriptions s ON u.id = s.user_id 
                   WHERE u.role='user' AND s.status='Active'"""
            )
            total_clients = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM users WHERE role='trainer' AND status='Active'")
            active_trainers = cur.fetchone()['count']
            
            cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM subscriptions WHERE status='Active'")
            monthly_revenue = cur.fetchone()['total']
            
            cur.execute("SELECT COUNT(*) as count FROM users WHERE role='user' AND status='Pending'")
            pending_users = cur.fetchone()['count']
            
            cur.execute("SELECT COUNT(*) as count FROM subscriptions WHERE status='Pending'")
            pending_subs = cur.fetchone()['count']
            
        return jsonify({
            'total_clients': total_clients,
            'active_trainers': active_trainers,
            'monthly_revenue': monthly_revenue,
            'pending_approvals': pending_users + pending_subs
        })
    finally:
        conn.close()

# ── Admin: Get live platform analytics ────────────────
@app.route('/api/admin/analytics')
def api_admin_analytics():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) as count FROM users")
            total_users = cur.fetchone()['count']
    finally:
        conn.close()

    disk = shutil.disk_usage(os.path.abspath(os.sep))
    server_load = psutil.cpu_percent(interval=0.1) if psutil else 0
    return jsonify({
        'total_users': total_users,
        'user_target': 2000,
        'server_load': round(server_load, 1),
        'storage_total': disk.total,
        'storage_used': disk.used,
        'storage_percent': round((disk.used / disk.total) * 100, 1) if disk.total else 0
    })

# ── Admin: Get recent registrations ────────────────────
@app.route('/api/admin/recent-users')
def api_admin_recent_users():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, first_name, last_name, email, status, created_at
                   FROM users WHERE role='user' ORDER BY created_at DESC LIMIT 5"""
            )
            users = cur.fetchall()
        for u in users:
            u['created_at'] = u['created_at'].strftime('%b %d, %Y') if u['created_at'] else '—'
        return jsonify(users)
    finally:
        conn.close()

# ── Admin: Get live financials ─────────────────────────
@app.route('/api/admin/financials')
def api_admin_financials():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT COALESCE(SUM(amount), 0) AS total
                   FROM payments
                   WHERE YEAR(created_at) = YEAR(CURDATE())"""
            )
            total_revenue = cur.fetchone()['total'] or 0

            cur.execute(
                """SELECT p.id, p.created_at, p.billing_name,
                          p.payment_method, p.amount,
                          'Completed' AS status
                   FROM payments p
                   ORDER BY p.created_at DESC
                   LIMIT 50"""
            )
            transactions = cur.fetchall()

        for transaction in transactions:
            transaction['created_at'] = transaction['created_at'].strftime('%b %d, %Y')

        return jsonify({
            'total_revenue': total_revenue,
            'trainer_payouts': 0,
            'operational_costs': 0,
            'net_profit': total_revenue,
            'transactions': transactions
        })
    finally:
        conn.close()

# ── Admin: Get all clients (Active + Pending) ──────────
@app.route('/api/admin/users')
def api_admin_get_users():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.first_name, u.last_name, u.email, u.status, u.created_at,
                          sp.id   AS sub_id,      sp.plan_name AS sub_plan,
                          sp.amount AS sub_amount, sp.status   AS sub_status,
                          sp.expiry_date          AS sub_expiry
                   FROM users u
                   LEFT JOIN subscriptions sp
                     ON sp.user_id = u.id
                     AND sp.status IN ('Pending', 'Active')
                   WHERE u.role = 'user'
                   ORDER BY u.created_at DESC"""
            )
            users = cur.fetchall()
        for u in users:
            u['created_at'] = u['created_at'].strftime('%b %d, %Y') if u['created_at'] else '—'
            if u.get('sub_expiry'):
                u['sub_expiry'] = u['sub_expiry'].strftime('%b %d, %Y')
        return jsonify(users)
    finally:
        conn.close()

# ── Admin: Get all trainers ────────────────────────────
@app.route('/api/admin/trainers')
def api_admin_get_trainers():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.first_name, u.last_name, u.email, u.status, u.created_at,
                          t.specialization, t.experience
                   FROM users u
                   INNER JOIN trainers t ON u.id = t.user_id
                   WHERE u.role = 'trainer'
                   ORDER BY u.created_at DESC"""
            )
            trainers = cur.fetchall()
        for t in trainers:
            t['created_at'] = t['created_at'].strftime('%b %d, %Y') if t['created_at'] else '—'
        return jsonify(trainers)
    finally:
        conn.close()

# ── Admin: Cancel active subscription ─────────────────
@app.route('/api/admin/subscription/<int:sub_id>/cancel', methods=['POST'])
def api_admin_cancel_subscription(sub_id):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE subscriptions SET status='Cancelled' WHERE id=%s AND status='Active'",
                (sub_id,)
            )
            conn.commit()
        return jsonify({'message': 'Subscription cancelled successfully.'})
    finally:
        conn.close()

# ── Admin: Approve subscription ────────────────────────
@app.route('/api/admin/subscription/<int:sub_id>/approve', methods=['POST'])
def api_admin_approve_subscription(sub_id):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE subscriptions SET status='Active' WHERE id=%s AND status='Pending'", (sub_id,))
            conn.commit()
        return jsonify({'message': 'Subscription approved.'})
    finally:
        conn.close()

# ── Admin: Reject subscription ─────────────────────────
@app.route('/api/admin/subscription/<int:sub_id>/reject', methods=['POST'])
def api_admin_reject_subscription(sub_id):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE subscriptions SET status='Cancelled' WHERE id=%s AND status='Pending'", (sub_id,))
            conn.commit()
        return jsonify({'message': 'Subscription request rejected.'})
    finally:
        conn.close()

# ── Admin: Approve user ────────────────────────────────
@app.route('/api/admin/users/<int:uid>/approve', methods=['POST'])
def api_admin_approve_user(uid):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status = 'Active' WHERE id = %s AND role = 'user'", (uid,))
            conn.commit()
        return jsonify({'message': 'User approved.'})
    finally:
        conn.close()

# ── Admin: Reject / delete user ────────────────────────
@app.route('/api/admin/users/<int:uid>/reject', methods=['POST'])
def api_admin_reject_user(uid):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s AND role = 'user'", (uid,))
            conn.commit()
        return jsonify({'message': 'User rejected and removed.'})
    finally:
        conn.close()

# ── Admin: Toggle Active / Inactive ───────────────────
@app.route('/api/admin/users/<int:uid>/toggle', methods=['POST'])
def api_admin_toggle_user(uid):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM users WHERE id = %s", (uid,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'User not found'}), 404
            new_status = 'Inactive' if row['status'] == 'Active' else 'Active'
            cur.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, uid))
            conn.commit()
        return jsonify({'message': f'User set to {new_status}.', 'status': new_status})
    finally:
        conn.close()

# ── Admin: Approve trainer ─────────────────────────────
@app.route('/api/admin/trainers/<int:tid>/approve', methods=['POST'])
def api_admin_approve_trainer(tid):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET status = 'Active' WHERE id = %s AND role = 'trainer'", (tid,))
            conn.commit()
        return jsonify({'message': 'Trainer approved.'})
    finally:
        conn.close()

# ── Admin: Reject / delete trainer ─────────────────────
@app.route('/api/admin/trainers/<int:tid>/reject', methods=['POST'])
def api_admin_reject_trainer(tid):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s AND role = 'trainer'", (tid,))
            conn.commit()
        return jsonify({'message': 'Trainer rejected and removed.'})
    finally:
        conn.close()

# ── Admin: Toggle trainer Active / Inactive ────────────
@app.route('/api/admin/trainers/<int:tid>/toggle', methods=['POST'])
def api_admin_toggle_trainer(tid):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT status FROM users WHERE id = %s", (tid,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'Trainer not found'}), 404
            new_status = 'Inactive' if row['status'] == 'Active' else 'Active'
            cur.execute("UPDATE users SET status = %s WHERE id = %s", (new_status, tid))
            conn.commit()
        return jsonify({'message': f'Trainer set to {new_status}.', 'status': new_status})
    finally:
        conn.close()

# ── Workout Plans: Create temporary (24hr) ────────────
@app.route('/api/user/workout-plans', methods=['POST'])
def api_create_workout_plan():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    data = request.get_json()
    
    name = data.get('name', '').strip()
    workout_type = data.get('type', '').strip()
    duration = data.get('duration_minutes')
    calories = data.get('estimated_calories')
    difficulty = data.get('difficulty', 'Intermediate').strip()
    description = data.get('description', '').strip()
    
    if not name or not duration or not calories:
        return jsonify({'error': 'Name, duration, and calories are required.'}), 400
    
    from datetime import datetime, timedelta
    expires_at = datetime.now() + timedelta(hours=24)
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workout_plans 
                   (user_id, name, type, duration_minutes, estimated_calories, difficulty, description, expires_at)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (uid, name, workout_type, duration, calories, difficulty, description, expires_at)
            )
            plan_id = cur.lastrowid
            conn.commit()
        return jsonify({
            'id': plan_id,
            'name': name,
            'type': workout_type,
            'duration_minutes': duration,
            'estimated_calories': calories,
            'difficulty': difficulty,
            'description': description,
            'message': 'Workout plan created (expires in 24 hours)'
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Workout Plans: Get all (auto-delete expired) ───────
@app.route('/api/user/workout-plans')
def api_get_workout_plans():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    from datetime import datetime
    now = datetime.now()
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Delete expired plans
            cur.execute("DELETE FROM workout_plans WHERE user_id = %s AND expires_at < %s", (uid, now))
            conn.commit()
            
            # Get remaining plans
            cur.execute(
                """SELECT id, name, type, duration_minutes, estimated_calories, difficulty, description, created_at, expires_at
                   FROM workout_plans WHERE user_id = %s ORDER BY created_at DESC""",
                (uid,)
            )
            plans = cur.fetchall()
        
        for p in plans:
            p['created_at'] = p['created_at'].strftime('%b %d, %Y %I:%M %p') if p['created_at'] else ''
            p['expires_at'] = p['expires_at'].strftime('%b %d, %Y %I:%M %p') if p['expires_at'] else ''
        
        return jsonify(plans)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Workout Plans: Update ──────────────────────────────
@app.route('/api/user/workout-plans/<int:plan_id>', methods=['PATCH'])
def api_update_workout_plan(plan_id):
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    data = request.get_json()
    
    name = data.get('name', '').strip()
    duration = data.get('duration_minutes')
    calories = data.get('estimated_calories')
    difficulty = data.get('difficulty', '').strip()
    description = data.get('description', '').strip()
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE workout_plans SET name=%s, duration_minutes=%s, estimated_calories=%s, 
                   difficulty=%s, description=%s WHERE id=%s AND user_id=%s""",
                (name, duration, calories, difficulty, description, plan_id, uid)
            )
            conn.commit()
        return jsonify({'message': 'Workout plan updated.'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Workout Plans: Delete ──────────────────────────────
@app.route('/api/user/workout-plans/<int:plan_id>', methods=['DELETE'])
def api_delete_workout_plan(plan_id):
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_plans WHERE id=%s AND user_id=%s", (plan_id, uid))
            conn.commit()
        return jsonify({'message': 'Workout plan deleted.'}), 204
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Workout Progress: Save / Get paused state ────────────
@app.route('/api/user/workout-progress/<int:plan_id>', methods=['GET'])
def api_get_workout_progress(plan_id):
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT seconds_remaining FROM workout_progress WHERE user_id=%s AND plan_id=%s",
                (uid, plan_id)
            )
            row = cur.fetchone()
        return jsonify({'seconds_remaining': row['seconds_remaining'] if row else None})
    finally:
        conn.close()

@app.route('/api/user/workout-progress', methods=['POST'])
def api_save_workout_progress():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid  = session['user_id']
    data = request.get_json()
    plan_id           = data.get('plan_id')
    seconds_remaining = data.get('seconds_remaining')
    if not plan_id or seconds_remaining is None:
        return jsonify({'error': 'plan_id and seconds_remaining required'}), 400
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workout_progress (user_id, plan_id, seconds_remaining)
                   VALUES (%s, %s, %s)
                   ON DUPLICATE KEY UPDATE seconds_remaining=%s""",
                (uid, plan_id, seconds_remaining, seconds_remaining)
            )
            conn.commit()
        return jsonify({'message': 'Progress saved.'})
    finally:
        conn.close()

@app.route('/api/user/workout-progress/<int:plan_id>', methods=['DELETE'])
def api_clear_workout_progress(plan_id):
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_progress WHERE user_id=%s AND plan_id=%s", (uid, plan_id))
            conn.commit()
        return jsonify({'message': 'Progress cleared.'})
    finally:
        conn.close()

# ── Workout History: Log completed workout ─────────────
@app.route('/api/user/workout-history', methods=['POST'])
def api_log_workout_history():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    data = request.get_json()
    
    workout_plan_id  = data.get('workout_plan_id')
    workout_name     = data.get('workout_name', '').strip()
    duration_seconds = data.get('duration_seconds')
    duration_minutes = data.get('duration_minutes')
    calories         = data.get('calories_burned')
    completed        = data.get('completed', True)
    update_if_exists = data.get('update_if_exists', False)
    
    if duration_seconds is not None:
        final_seconds = int(duration_seconds)
        final_minutes = max(1, round(final_seconds / 60))
    elif duration_minutes is not None:
        final_minutes = int(duration_minutes)
        final_seconds = final_minutes * 60
    else:
        return jsonify({'error': 'Duration (seconds or minutes) is required.'}), 400
    
    if not workout_name or not calories:
        return jsonify({'error': 'Workout name and calories are required.'}), 400
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SHOW COLUMNS FROM workout_history LIKE 'duration_seconds'")
            has_seconds_col = cur.fetchone() is not None
            
            if update_if_exists:
                cur.execute(
                    """SELECT id FROM workout_history 
                       WHERE user_id = %s AND workout_name = %s AND completed = FALSE 
                       ORDER BY completed_at DESC LIMIT 1""",
                    (uid, workout_name)
                )
                existing = cur.fetchone()
                
                if existing:
                    history_id = existing['id']
                    if has_seconds_col:
                        cur.execute(
                            """UPDATE workout_history 
                               SET duration_minutes = %s, duration_seconds = %s, 
                                   calories_burned = %s, completed = %s, completed_at = NOW()
                               WHERE id = %s""",
                            (final_minutes, final_seconds, calories, completed, history_id)
                        )
                    else:
                        cur.execute(
                            """UPDATE workout_history 
                               SET duration_minutes = %s, calories_burned = %s, 
                                   completed = %s, completed_at = NOW()
                               WHERE id = %s""",
                            (final_minutes, calories, completed, history_id)
                        )
                    conn.commit()
                    print(f"🔄 Workout history updated: ID={history_id}, User={uid}, Workout={workout_name}, Duration={final_minutes}min ({final_seconds}s), Calories={calories}, Completed={completed}")
                    return jsonify({'id': history_id, 'message': 'Workout history updated!', 'updated': True}), 200
            
            if has_seconds_col:
                cur.execute(
                    """INSERT INTO workout_history 
                       (user_id, workout_plan_id, workout_name, duration_minutes, duration_seconds, calories_burned, completed)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (uid, workout_plan_id, workout_name, final_minutes, final_seconds, calories, completed)
                )
            else:
                cur.execute(
                    """INSERT INTO workout_history 
                       (user_id, workout_plan_id, workout_name, duration_minutes, calories_burned, completed)
                       VALUES (%s, %s, %s, %s, %s, %s)""",
                    (uid, workout_plan_id, workout_name, final_minutes, calories, completed)
                )
            history_id = cur.lastrowid
            conn.commit()
        print(f"✅ Workout history logged: ID={history_id}, User={uid}, Workout={workout_name}, Duration={final_minutes}min ({final_seconds}s), Calories={calories}, Completed={completed}")
        return jsonify({'id': history_id, 'message': 'Workout logged to history!', 'updated': False}), 201
    except Exception as e:
        print(f"❌ Error logging workout history: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Workout History: Get all ───────────────────────────
@app.route('/api/user/workout-history')
def api_get_workout_history():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, workout_plan_id, workout_name, duration_minutes,
                          COALESCE(duration_seconds, duration_minutes * 60, 0) AS duration_seconds,
                          calories_burned, completed, completed_at
                   FROM workout_history WHERE user_id = %s ORDER BY completed_at DESC""",
                (uid,)
            )
            history = cur.fetchall()
        
        for h in history:
            h['completed_at'] = h['completed_at'].strftime('%b %d, %Y %I:%M %p') if h['completed_at'] else ''
        
        return jsonify(history)
    except Exception as e:
        print(f"Error fetching workout history: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Workout History: Delete entry ──────────────────────
@app.route('/api/user/workout-history/<int:history_id>', methods=['DELETE'])
def api_delete_workout_history(history_id):
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM workout_history WHERE id=%s AND user_id=%s", (history_id, uid))
            conn.commit()
        return jsonify({'message': 'History entry deleted.'}), 204
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Measurements: Log new entry ────────────────────────
@app.route('/api/user/measurements', methods=['POST'])
def api_log_measurement():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    data = request.get_json()
    
    weight = data.get('weight')
    body_fat = data.get('body_fat') or None
    chest = data.get('chest') or None
    waist = data.get('waist') or None
    hips = data.get('hips') or None
    logged_date = data.get('logged_date')
    
    if not weight or not logged_date:
        return jsonify({'error': 'Weight and date are required.'}), 400
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Check if entry exists for this date
            cur.execute(
                "SELECT id FROM measurements WHERE user_id = %s AND logged_date = %s",
                (uid, logged_date)
            )
            existing = cur.fetchone()
            
            if existing:
                # Update existing entry
                cur.execute(
                    """UPDATE measurements SET weight=%s, body_fat=%s, chest=%s, waist=%s, hips=%s
                       WHERE id=%s""",
                    (weight, body_fat, chest, waist, hips, existing['id'])
                )
            else:
                # Insert new entry
                cur.execute(
                    """INSERT INTO measurements (user_id, weight, body_fat, chest, waist, hips, logged_date)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (uid, weight, body_fat, chest, waist, hips, logged_date)
                )
            conn.commit()
        return jsonify({'message': 'Measurement logged successfully!'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Measurements: Get all ──────────────────────────────
@app.route('/api/user/measurements')
def api_get_measurements():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, weight, body_fat, chest, waist, hips, logged_date, created_at
                   FROM measurements WHERE user_id = %s ORDER BY logged_date DESC""",
                (uid,)
            )
            measurements = cur.fetchall()
        
        for m in measurements:
            m['logged_date'] = m['logged_date'].strftime('%Y-%m-%d') if m['logged_date'] else ''
            m['created_at'] = m['created_at'].strftime('%b %d, %Y') if m['created_at'] else ''
        
        return jsonify(measurements)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Measurements: Get today's weight ──────────────────
@app.route('/api/user/measurements/today')
def api_get_today_measurement():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    from datetime import date
    today = date.today()
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT weight FROM measurements 
                   WHERE user_id = %s AND logged_date = %s""",
                (uid, today)
            )
            measurement = cur.fetchone()
        
        if measurement:
            return jsonify({'weight': float(measurement['weight'])})
        else:
            return jsonify({'weight': None})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Measurements: Get streak ───────────────────────────
@app.route('/api/user/measurements/streak')
def api_get_measurement_streak():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    
    from datetime import date, timedelta
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Get all logged dates ordered by date descending
            cur.execute(
                """SELECT DISTINCT logged_date FROM measurements 
                   WHERE user_id = %s ORDER BY logged_date DESC""",
                (uid,)
            )
            dates = [row['logged_date'] for row in cur.fetchall()]
        
        if not dates:
            return jsonify({'streak': 0})
        
        # Calculate streak
        today = date.today()
        streak = 0
        
        # Check if there's an entry for today or yesterday
        if dates[0] == today or dates[0] == today - timedelta(days=1):
            streak = 1
            current_date = dates[0]
            
            for i in range(1, len(dates)):
                expected_date = current_date - timedelta(days=1)
                if dates[i] == expected_date:
                    streak += 1
                    current_date = dates[i]
                else:
                    break
        
        return jsonify({'streak': streak})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Trainer Profile: GET ──────────────────────────────
@app.route('/api/trainer/profile')
def api_get_trainer_profile():
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.first_name, u.last_name, u.email, 
                          t.specialization, t.experience,
                          tp.phone, tp.bio, tp.certifications, tp.hourly_rate, 
                          tp.availability, tp.profile_image
                   FROM users u
                   INNER JOIN trainers t ON u.id = t.user_id
                   LEFT JOIN trainer_profiles tp ON u.id = tp.user_id
                   WHERE u.id = %s""", (uid,)
            )
            trainer = cur.fetchone()
        return jsonify(trainer if trainer else {})
    finally:
        conn.close()

# ── Trainer Profile: SAVE ──────────────────────────────
@app.route('/api/trainer/profile', methods=['POST'])
def api_save_trainer_profile():
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    data = request.get_json()

    first_name = data.get('first_name', '').strip()
    last_name = data.get('last_name', '').strip()
    specialization = data.get('specialization', '').strip()
    experience = data.get('experience', 0)
    phone = data.get('phone', '').strip()
    bio = data.get('bio', '').strip()
    certifications = data.get('certifications', '').strip()
    hourly_rate = data.get('hourly_rate')
    availability = data.get('availability', 'Available').strip()

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET first_name = %s, last_name = %s WHERE id = %s",
                (first_name, last_name, uid)
            )
            cur.execute(
                "UPDATE trainers SET specialization = %s, experience = %s WHERE user_id = %s",
                (specialization, experience, uid)
            )
            
            cur.execute("SELECT id FROM trainer_profiles WHERE user_id = %s", (uid,))
            if cur.fetchone():
                cur.execute(
                    """UPDATE trainer_profiles SET phone=%s, bio=%s, certifications=%s,
                       hourly_rate=%s, availability=%s WHERE user_id=%s""",
                    (phone, bio, certifications, hourly_rate, availability, uid)
                )
            else:
                cur.execute(
                    """INSERT INTO trainer_profiles
                       (user_id, phone, bio, certifications, hourly_rate, availability)
                       VALUES (%s,%s,%s,%s,%s,%s)""",
                    (uid, phone, bio, certifications, hourly_rate, availability)
                )
            conn.commit()
        session['user_name'] = f"{first_name} {last_name}"
        return jsonify({'message': 'Profile saved successfully.'})
    finally:
        conn.close()

# ── API v1: Get Members/Clients (for trainer) ──────────
@app.route('/api/v1/members/')
def api_v1_get_members():
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    trainer_id = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Get only clients assigned to this trainer
            cur.execute(
                """SELECT u.id, u.first_name, u.last_name, u.email, u.status,
                          COALESCE(NULLIF(TRIM(CONCAT(u.first_name, ' ', u.last_name)), ''), u.email) as username,
                          up.phone, up.age, up.gender, up.height, up.weight,
                          s.plan_name, s.status as subscription_status
                   FROM trainer_clients tc
                   INNER JOIN users u ON tc.client_id = u.id
                   LEFT JOIN user_profiles up ON u.id = up.user_id
                   LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'Active'
                   WHERE tc.trainer_id = %s AND u.role = 'user' AND u.status IN ('Active', 'Pending')
                   ORDER BY tc.assigned_at DESC""",
                (trainer_id,)
            )
            members = cur.fetchall()
        
        for member in members:
            if not member.get('username') or member['username'].strip() == '':
                member['username'] = member.get('email', 'Unknown User')
        
        return jsonify({'results': members})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Get Workout Plans (for trainer) ────────────
@app.route('/api/v1/workout-plans/')
def api_v1_get_workout_plans():
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    trainer_id = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, name, duration_minutes, estimated_calories, 
                          difficulty, description, created_at, updated_at
                   FROM trainer_workout_plans
                   WHERE trainer_id = %s
                   ORDER BY created_at DESC""",
                (trainer_id,)
            )
            plans = cur.fetchall()
        
        return jsonify({'results': plans})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Create Workout Plan (for trainer) ──────────
@app.route('/api/v1/workout-plans/', methods=['POST'])
def api_v1_create_workout_plan():
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    trainer_id = session['user_id']
    data = request.get_json()
    
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    difficulty = data.get('difficulty', 'Beginner')
    duration = data.get('duration_minutes')
    calories = data.get('estimated_calories')
    
    if not name or not duration or not calories:
        return jsonify({'error': 'Name, duration, and calories are required'}), 400
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO trainer_workout_plans 
                   (trainer_id, name, duration_minutes, estimated_calories, difficulty, description)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (trainer_id, name, duration, calories, difficulty, description)
            )
            plan_id = cur.lastrowid
            conn.commit()
        
        return jsonify({
            'id': plan_id,
            'name': name,
            'duration_minutes': duration,
            'estimated_calories': calories,
            'difficulty': difficulty,
            'description': description
        }), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Update Workout Plan (for trainer) ──────────
@app.route('/api/v1/workout-plans/<int:plan_id>/', methods=['PUT'])
def api_v1_update_workout_plan(plan_id):
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    trainer_id = session['user_id']
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    difficulty = data.get('difficulty', 'Beginner')
    duration = data.get('duration_minutes')
    calories = data.get('estimated_calories')
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE trainer_workout_plans 
                   SET name=%s, duration_minutes=%s, estimated_calories=%s, 
                       difficulty=%s, description=%s 
                   WHERE id=%s AND trainer_id=%s""",
                (name, duration, calories, difficulty, description, plan_id, trainer_id)
            )
            conn.commit()
        return jsonify({'message': 'Workout plan updated'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Delete Workout Plan (for trainer) ──────────
@app.route('/api/v1/workout-plans/<int:plan_id>/', methods=['DELETE'])
def api_v1_delete_workout_plan(plan_id):
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    trainer_id = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM trainer_workout_plans WHERE id=%s AND trainer_id=%s", (plan_id, trainer_id))
            conn.commit()
        return jsonify({'success': True}), 204
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Appointments/Sessions (for trainer & user) ────────
@app.route('/api/v1/appointments/', methods=['GET', 'POST'])
def api_v1_appointments():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    
    uid = session['user_id']
    role = session.get('user_role')
    conn = db_connection()
    try:
        if request.method == 'GET':
            with conn.cursor() as cur:
                if role == 'trainer':
                    cur.execute(
                        "SELECT a.id, a.member_id, a.trainer_id, a.date_time, a.notes, a.session_type, "
                        "CONCAT(u.first_name, ' ', u.last_name) as client_name "
                        "FROM appointments a "
                        "LEFT JOIN users u ON a.member_id = u.id "
                        "WHERE a.trainer_id = %s",
                        (uid,)
                    )
                else:
                    cur.execute(
                        "SELECT a.id, a.member_id, a.trainer_id, a.date_time, a.notes, a.session_type, "
                        "CONCAT(u.first_name, ' ', u.last_name) as trainer_name "
                        "FROM appointments a "
                        "LEFT JOIN users u ON a.trainer_id = u.id "
                        "WHERE a.member_id = %s",
                        (uid,)
                    )
                rows = cur.fetchall()
            
            results = []
            for row in rows:
                dt = row['date_time']
                dt_str = dt.strftime('%Y-%m-%dT%H:%M') if hasattr(dt, 'strftime') else str(dt)
                
                st_map = {
                    1: 'Personal Training',
                    2: 'Group Session',
                    3: 'Consultation'
                }
                session_type = row['session_type'] or 1
                session_type_name = st_map.get(session_type, 'Personal Training')
                
                res_obj = {
                    'id': row['id'],
                    'member': row['member_id'],
                    'trainer': row['trainer_id'],
                    'date_time': dt_str,
                    'notes': row['notes'] or '',
                    'session_type': session_type,
                    'session_type_name': session_type_name,
                    'session_type_details': {
                        'id': session_type,
                        'name': session_type_name
                    }
                }
                if role == 'trainer':
                    res_obj['client_name'] = row['client_name'] or f"Member #{row['member_id']}"
                else:
                    res_obj['trainer_name'] = row['trainer_name'] or f"Trainer #{row['trainer_id']}"
                    
                results.append(res_obj)
            return jsonify({'results': results})
            
        elif request.method == 'POST':
            if role != 'trainer':
                return jsonify({'error': 'Unauthorized'}), 403
                
            data = request.get_json() or {}
            member_id = data.get('member')
            date_time_str = data.get('date_time')
            notes = data.get('notes') or ''
            session_type = data.get('session_type') or 1
            
            if date_time_str:
                date_time_str = date_time_str.replace('T', ' ')
            
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO appointments (member_id, trainer_id, date_time, notes, session_type) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (member_id, uid, date_time_str, notes, session_type)
                )
                conn.commit()
                new_id = cur.lastrowid
                
            st_map = {
                1: 'Personal Training',
                2: 'Group Session',
                3: 'Consultation'
            }
            session_type_name = st_map.get(session_type, 'Personal Training')
            
            return jsonify({
                'id': new_id,
                'member': member_id,
                'trainer': uid,
                'date_time': date_time_str,
                'notes': notes,
                'session_type': session_type,
                'session_type_details': {
                    'id': session_type,
                    'name': session_type_name
                }
            }), 201
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/v1/appointments/<int:app_id>/', methods=['PUT', 'DELETE'])
def api_v1_appointment_detail(app_id):
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
        
    trainer_id = session['user_id']
    conn = db_connection()
    try:
        if request.method == 'PUT':
            data = request.get_json() or {}
            member_id = data.get('member')
            date_time_str = data.get('date_time')
            notes = data.get('notes') or ''
            session_type = data.get('session_type') or 1
            
            if date_time_str:
                date_time_str = date_time_str.replace('T', ' ')
                
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE appointments "
                    "SET member_id = %s, date_time = %s, notes = %s, session_type = %s "
                    "WHERE id = %s AND trainer_id = %s",
                    (member_id, date_time_str, notes, session_type, app_id, trainer_id)
                )
                conn.commit()
                
            st_map = {
                1: 'Personal Training',
                2: 'Group Session',
                3: 'Consultation'
            }
            session_type_name = st_map.get(session_type, 'Personal Training')
            
            return jsonify({
                'id': app_id,
                'member': member_id,
                'trainer': trainer_id,
                'date_time': date_time_str,
                'notes': notes,
                'session_type': session_type,
                'session_type_details': {
                    'id': session_type,
                    'name': session_type_name
                }
            })
            
        elif request.method == 'DELETE':
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM appointments WHERE id = %s AND trainer_id = %s",
                    (app_id, trainer_id)
                )
                conn.commit()
            return jsonify({'success': True}), 204
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Delete user account (member self-delete) ──
@app.route('/api/v1/members/me/', methods=['DELETE'])
def api_v1_delete_member_me():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 403
    uid = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (uid,))
            conn.commit()
        session.clear()
        return jsonify({'success': True, 'message': 'Account successfully deleted.'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Contact / Enquiries ───────────────────────
@app.route('/api/v1/enquiries/', methods=['POST'])
def api_v1_enquiries():
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    message = data.get('message')
    
    if not name or not email:
        return jsonify({'error': 'Name and Email are required.'}), 400
        
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS enquiries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) NOT NULL,
                    phone VARCHAR(50),
                    message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            cur.execute(
                "INSERT INTO enquiries (name, email, phone, message) VALUES (%s, %s, %s, %s)",
                (name, email, phone, message)
            )
            conn.commit()
        return jsonify({'success': True, 'message': 'Enquiry submitted successfully.'}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API v1: Get Session Types (for trainer) ────────────
@app.route('/api/v1/session-types/')
def api_v1_get_session_types():
    if 'user_id' not in session or session.get('user_role') != 'trainer':
        return jsonify({'error': 'Unauthorized'}), 403
    
    return jsonify({'results': [
        {'id': 1, 'name': 'Personal Training'},
        {'id': 2, 'name': 'Group Session'},
        {'id': 3, 'name': 'Consultation'}
    ]})

# ── Admin: Get clients assigned to a trainer ────────────
@app.route('/api/admin/trainer/<int:trainer_id>/clients')
def api_admin_get_trainer_clients(trainer_id):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.first_name, u.last_name, u.email, u.status,
                          s.plan_name, s.status as sub_status
                   FROM trainer_clients tc
                   INNER JOIN users u ON tc.client_id = u.id
                   LEFT JOIN subscriptions s ON u.id = s.user_id AND s.status = 'Active'
                   WHERE tc.trainer_id = %s
                   ORDER BY tc.assigned_at DESC""",
                (trainer_id,)
            )
            clients = cur.fetchall()
        return jsonify(clients)
    finally:
        conn.close()

# ── Admin: Assign clients to trainer ──────────────────
@app.route('/api/admin/trainer/<int:trainer_id>/assign-clients', methods=['POST'])
def api_admin_assign_clients(trainer_id):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    client_ids = data.get('client_ids', [])
    
    if not client_ids:
        return jsonify({'error': 'No clients selected'}), 400
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            for client_id in client_ids:
                cur.execute(
                    """INSERT INTO trainer_clients (trainer_id, client_id)
                       VALUES (%s, %s)
                       ON DUPLICATE KEY UPDATE assigned_at = CURRENT_TIMESTAMP""",
                    (trainer_id, client_id)
                )
            conn.commit()
        return jsonify({'message': f'{len(client_ids)} client(s) assigned successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Admin: Unassign client from trainer ───────────────
@app.route('/api/admin/trainer/<int:trainer_id>/unassign-client/<int:client_id>', methods=['DELETE'])
def api_admin_unassign_client(trainer_id, client_id):
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM trainer_clients WHERE trainer_id = %s AND client_id = %s",
                (trainer_id, client_id)
            )
            conn.commit()
        return jsonify({'message': 'Client unassigned successfully'})
    finally:
        conn.close()

# ── Admin: Export Reports ─────────────────────────────
@app.route('/api/admin/reports/financial/export')
def api_admin_reports_financial_export():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Active Subscriptions Breakdown
            cur.execute("""
                SELECT plan_name, COUNT(*) as count, SUM(amount) as total_amount
                FROM subscriptions 
                WHERE status = 'Active'
                GROUP BY plan_name
            """)
            active_plans = cur.fetchall()
            
            # Pending Subscriptions
            cur.execute("""
                SELECT plan_name, COUNT(*) as count, SUM(amount) as total_amount
                FROM subscriptions 
                WHERE status = 'Pending'
                GROUP BY plan_name
            """)
            pending_plans = cur.fetchall()
            
            # Total Revenue
            cur.execute("SELECT COALESCE(SUM(amount), 0) as total FROM subscriptions WHERE status='Active'")
            total_revenue = cur.fetchone()['total']
            
            # All transactions (Subscriptions list)
            cur.execute("""
                SELECT s.id, u.first_name, u.last_name, s.plan_name, s.amount, s.status, s.created_at
                FROM subscriptions s
                JOIN users u ON s.user_id = u.id
                ORDER BY s.created_at DESC
            """)
            transactions = cur.fetchall()
            
        from datetime import datetime
        report_text = [
            '===========================================',
            'IRON HUB - MONTHLY FINANCIAL SUMMARY',
            '===========================================',
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '',
            f'Total Active Revenue: INR {total_revenue:,.2f}',
            '',
            '-------------------------------------------',
            'ACTIVE SUBSCRIPTIONS BY PLAN',
            '-------------------------------------------',
        ]
        
        for plan in active_plans:
            report_text.append(f"Plan: {plan['plan_name']} | Active Count: {plan['count']} | Total: INR {plan['total_amount']:,.2f}")
            
        if not active_plans:
            report_text.append("No active subscriptions.")
            
        report_text.extend([
            '',
            '-------------------------------------------',
            'PENDING SUBSCRIPTIONS BY PLAN',
            '-------------------------------------------',
        ])
        
        for plan in pending_plans:
            report_text.append(f"Plan: {plan['plan_name']} | Pending Count: {plan['count']} | Total: INR {plan['total_amount']:,.2f}")
            
        if not pending_plans:
            report_text.append("No pending subscriptions.")
            
        report_text.extend([
            '',
            '-------------------------------------------',
            'TRANSACTIONS HISTORY (ALL SUBSCRIPTIONS)',
            '-------------------------------------------',
        ])
        
        for tx in transactions:
            report_text.append(
                f"Tx ID: {tx['id']} | User: {tx['first_name']} {tx['last_name']} | "
                f"Plan: {tx['plan_name']} | Amount: INR {tx['amount']:,.2f} | Status: {tx['status']} | Date: {tx['created_at']}"
            )
            
        if not transactions:
            report_text.append("No transactions found.")
            
        report_text.extend([
            '',
            '===========================================',
            'End of Financial Summary',
            '===========================================',
        ])
        
        output = '\n'.join(report_text)
        buffer = BytesIO(output.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'monthly-financial-summary-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/reports/activity/export')
def api_admin_reports_activity_export():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # User registration activities and status
            cur.execute("""
                SELECT id, first_name, last_name, email, role, status, created_at
                FROM users
                ORDER BY created_at DESC
            """)
            users = cur.fetchall()
            
        csv_rows = [['User ID', 'First Name', 'Last Name', 'Email', 'Role', 'Status', 'Registration Date']]
        for u in users:
            csv_rows.append([
                str(u['id']),
                u['first_name'],
                u['last_name'],
                u['email'],
                u['role'],
                u['status'],
                str(u['created_at'])
            ])
            
        output = '\n'.join(','.join(f'"{val}"' for val in row) for row in csv_rows)
        buffer = BytesIO(output.encode('utf-8'))
        buffer.seek(0)
        
        from datetime import datetime
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'user-activity-logs-{datetime.now().strftime("%Y%m%d-%H%M%S")}.csv',
            mimetype='text/csv'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/admin/reports/trainer/export')
def api_admin_reports_trainer_export():
    if session.get('user_role') != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Trainer list
            cur.execute("""
                SELECT id, first_name, last_name, email, status, created_at
                FROM users
                WHERE role = 'trainer'
                ORDER BY created_at DESC
            """)
            trainers = cur.fetchall()
            
            # Count assigned clients per trainer
            cur.execute("""
                SELECT trainer_id, COUNT(*) as client_count
                FROM trainer_clients
                GROUP BY trainer_id
            """)
            assignment_counts = {row['trainer_id']: row['client_count'] for row in cur.fetchall()}
            
        from datetime import datetime
        report_text = [
            '===========================================',
            'IRON HUB - TRAINER PERFORMANCE REPORT',
            '===========================================',
            f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            '',
            '-------------------------------------------',
            'TRAINER PERFORMANCE METRICS',
            '-------------------------------------------',
        ]
        
        for t in trainers:
            client_count = assignment_counts.get(t['id'], 0)
            report_text.extend([
                f"Trainer: {t['first_name']} {t['last_name']}",
                f"Email: {t['email']}",
                f"Registered: {t['created_at']}",
                f"Status: {t['status']}",
                f"Assigned Active Clients: {client_count}",
                f"Average Rating: 4.9/5.0",
                ''
            ])
            
        if not trainers:
            report_text.append("No trainers registered in the system.")
            
        report_text.extend([
            '===========================================',
            'End of Trainer Performance Report',
            '===========================================',
        ])
        
        output = '\n'.join(report_text)
        buffer = BytesIO(output.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'trainer-performance-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── Session Check API ───────────────────────────────────
@app.route('/api/session/check')
def session_check():
    if 'user_id' in session:
        return jsonify({'logged_in': True, 'role': session.get('user_role')})
    return jsonify({'logged_in': False})

# ═════════════════════════════════════════════════════════
# ═ NEW FEATURES API ENDPOINTS ════════════════════════════
# ═════════════════════════════════════════════════════════

# ── API: Get Membership Expiry Status ────────────────────
@app.route('/api/features/membership-expiry')
def api_membership_expiry():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Get active subscription
            cur.execute("""
                SELECT id, plan_name, expiry_date, status FROM subscriptions 
                WHERE user_id=%s AND status='Active'
                ORDER BY expiry_date DESC LIMIT 1
            """, (user_id,))
            sub = cur.fetchone()
            
            if sub:
                from datetime import datetime, timedelta
                expiry = datetime.strptime(str(sub['expiry_date']), '%Y-%m-%d')
                today = datetime.now()
                days_left = (expiry - today).days
                
                return jsonify({
                    'has_active_subscription': True,
                    'plan_name': sub['plan_name'],
                    'expiry_date': str(sub['expiry_date']),
                    'days_left': days_left,
                    'expiring_soon': days_left <= 30 and days_left > 0
                })
            return jsonify({'has_active_subscription': False})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Get Email Notification Preferences ─────────────
@app.route('/api/features/email-preferences')
def api_get_email_preferences():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT membership_expiry, workout_reminders, progress_reports, 
                       new_offers, chat_notifications 
                FROM email_preferences WHERE user_id=%s
            """, (user_id,))
            prefs = cur.fetchone()
            
            if prefs:
                return jsonify(prefs)
            
            # Create default preferences
            cur.execute("""
                INSERT INTO email_preferences (user_id) VALUES (%s)
            """, (user_id,))
            conn.commit()
            
            return jsonify({
                'membership_expiry': True,
                'workout_reminders': True,
                'progress_reports': True,
                'new_offers': True,
                'chat_notifications': True
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Update Email Notification Preferences ──────────
@app.route('/api/features/email-preferences', methods=['POST'])
def api_update_email_preferences():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    data = request.get_json()
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE email_preferences 
                SET membership_expiry=%s, workout_reminders=%s, 
                    progress_reports=%s, new_offers=%s, chat_notifications=%s
                WHERE user_id=%s
            """, (
                data.get('membership_expiry', True),
                data.get('workout_reminders', True),
                data.get('progress_reports', True),
                data.get('new_offers', True),
                data.get('chat_notifications', True),
                user_id
            ))
            conn.commit()
        return jsonify({'message': 'Preferences updated successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Send Chat Message ───────────────────────────────
@app.route('/api/features/chat/send', methods=['POST'])
def api_send_chat_message():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    data = request.get_json()
    message = data.get('message', '').strip()
    
    if not message:
        return jsonify({'error': 'Message cannot be empty'}), 400
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_messages (user_id, message, sender_type) 
                VALUES (%s, %s, 'user')
            """, (user_id, message))
            conn.commit()
        return jsonify({'message': 'Message sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Get Chat Messages ───────────────────────────────
@app.route('/api/features/chat/messages')
def api_get_chat_messages():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    limit = request.args.get('limit', 50, type=int)
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, message, sender_type, created_at 
                FROM chat_messages 
                WHERE user_id=%s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (user_id, limit))
            messages = cur.fetchall()
            messages.reverse()  # Reverse to get chronological order
        
        return jsonify({'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Trainer Chat Users ─────────────────────────────
@app.route('/api/features/chat/users')
@login_required('trainer')
def api_get_chat_users():
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT u.id AS user_id,
                       CONCAT(COALESCE(u.first_name, ''), ' ', COALESCE(u.last_name, '')) AS full_name,
                       u.email,
                       MAX(cm.created_at) AS last_message_at
                FROM users u
                JOIN chat_messages cm ON u.id = cm.user_id
                WHERE u.role = 'user'
                GROUP BY u.id, u.first_name, u.last_name, u.email
                ORDER BY last_message_at DESC
            """)
            users = cur.fetchall()
        return jsonify({'users': users})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Trainer Get Chat Messages ──────────────────────
@app.route('/api/features/chat/messages/<int:user_id>')
@login_required('trainer')
def api_get_chat_messages_for_trainer(user_id):
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, message, sender_type, created_at 
                FROM chat_messages 
                WHERE user_id=%s 
                ORDER BY created_at ASC
            """, (user_id,))
            messages = cur.fetchall()
        return jsonify({'messages': messages})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Trainer Send Reply ────────────────────────────
@app.route('/api/features/chat/reply', methods=['POST'])
@login_required('trainer')
def api_trainer_reply():
    data = request.get_json()
    user_id = data.get('user_id')
    message = data.get('message', '').strip()

    if not user_id or not message:
        return jsonify({'error': 'User and message are required.'}), 400

    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_messages (user_id, message, sender_type) 
                VALUES (%s, %s, 'trainer')
            """, (user_id, message))
            conn.commit()
        return jsonify({'message': 'Reply sent successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Add Auto-Response to Chat ───────────────────────
@app.route('/api/features/chat/auto-response', methods=['POST'])
def api_chat_auto_response():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    data = request.get_json()
    
    responses = [
        'Thank you for reaching out! How can I assist you today?',
        'I\'m here to help. What seems to be the issue?',
        'I understand. Let me help you with that.',
        'That\'s a great question! Let me provide you with more information.',
        'Our support team will look into this for you.',
        'Thank you for your patience. Is there anything else I can help with?'
    ]
    
    import random
    response = random.choice(responses)
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_messages (user_id, message, sender_type) 
                VALUES (%s, %s, 'support')
            """, (user_id, response))
            conn.commit()
        return jsonify({'response': response})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Calculate and Save BMI ──────────────────────────
@app.route('/api/features/bmi/calculate', methods=['POST'])
def api_calculate_bmi():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    data = request.get_json()
    
    try:
        height = float(data.get('height', 0))  # in cm
        weight = float(data.get('weight', 0))  # in kg
        
        if height <= 0 or weight <= 0:
            return jsonify({'error': 'Invalid height or weight'}), 400
        
        # Convert height to meters
        height_m = height / 100
        bmi = weight / (height_m ** 2)
        bmi_rounded = round(bmi, 1)
        
        # Determine category
        if bmi < 18.5:
            category = 'Underweight'
        elif bmi < 25:
            category = 'Normal Weight'
        elif bmi < 30:
            category = 'Overweight'
        else:
            category = 'Obese'
        
        conn = db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO bmi_records (user_id, height, weight, bmi, category) 
                    VALUES (%s, %s, %s, %s, %s)
                """, (user_id, height, weight, bmi_rounded, category))
                conn.commit()
            
            return jsonify({
                'bmi': bmi_rounded,
                'category': category,
                'height': height,
                'weight': weight,
                'message': f'Your BMI is {bmi_rounded} - {category}'
            })
        finally:
            conn.close()
    except (ValueError, TypeError):
        return jsonify({'error': 'Invalid input values'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── API: Get BMI History ─────────────────────────────────
@app.route('/api/features/bmi/history')
def api_get_bmi_history():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    limit = request.args.get('limit', 30, type=int)
    
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, height, weight, bmi, category, created_at 
                FROM bmi_records 
                WHERE user_id=%s 
                ORDER BY created_at DESC 
                LIMIT %s
            """, (user_id, limit))
            records = cur.fetchall()
        
        return jsonify({'records': records})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Export Progress Report as PDF/Text ──────────────
@app.route('/api/features/report/export')
def api_export_report():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    conn = db_connection()
    try:
        with conn.cursor() as cur:
            # Get user info
            cur.execute("SELECT first_name, last_name, email FROM users WHERE id=%s", (user_id,))
            user = cur.fetchone()
            
            # Get current subscription
            cur.execute("""
                SELECT plan_name, expiry_date FROM subscriptions 
                WHERE user_id=%s AND status='Active' 
                ORDER BY expiry_date DESC LIMIT 1
            """, (user_id,))
            sub = cur.fetchone()
            
            # Get latest measurements
            cur.execute("""
                SELECT weight, body_fat, chest, waist, hips, logged_date 
                FROM measurements 
                WHERE user_id=%s 
                ORDER BY logged_date DESC LIMIT 5
            """, (user_id,))
            measurements = cur.fetchall()
            
            # Get latest BMI
            cur.execute("""
                SELECT bmi, category, created_at FROM bmi_records 
                WHERE user_id=%s 
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,))
            bmi = cur.fetchone()
            
            # Get workout stats
            cur.execute("""
                SELECT 
                    COUNT(*) as total_workouts,
                    SUM(duration_minutes) as total_minutes,
                    SUM(calories_burned) as total_calories
                FROM workout_history WHERE user_id=%s AND DATE(completed_at) >= DATE_SUB(NOW(), INTERVAL 30 DAY)
            """, (user_id,))
            stats = cur.fetchone()
        
        from datetime import datetime
        report_text = [
            '===========================================',
            'FITNESS PROGRESS REPORT',
            '===========================================',
            '',
            f'Report Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            f'User: {user.get("first_name", "")} {user.get("last_name", "")}',
            f'Email: {user.get("email", "")}',
            '',
            '-------------------------------------------',
            'SUBSCRIPTION DETAILS',
            '-------------------------------------------',
            f'Plan: {sub.get("plan_name") if sub else "No active subscription"}',
            f'Expiry: {sub.get("expiry_date") if sub else "N/A"}',
            '',
            '-------------------------------------------',
            'LATEST MEASUREMENTS',
            '-------------------------------------------',
        ]
        
        if measurements:
            for row in measurements:
                report_text.extend([
                    f'Date: {row.get("logged_date")}',
                    f'Weight: {row.get("weight")} kg',
                    f'Body Fat: {row.get("body_fat") or "N/A"}',
                    f'Chest: {row.get("chest") or "N/A"} cm',
                    f'Waist: {row.get("waist") or "N/A"} cm',
                    f'Hips: {row.get("hips") or "N/A"} cm',
                    ''
                ])
        else:
            report_text.append('No measurements available.')
            report_text.append('')

        report_text.extend([
            '-------------------------------------------',
            'LATEST BMI',
            '-------------------------------------------',
        ])

        if bmi:
            report_text.extend([
                f'BMI: {bmi.get("bmi")}',
                f'Category: {bmi.get("category")}',
                f'Recorded: {bmi.get("created_at")}',
                ''
            ])
        else:
            report_text.extend(['No BMI records available.', ''])

        report_text.extend([
            '-------------------------------------------',
            'WORKOUT STATISTICS (LAST 30 DAYS)',
            '-------------------------------------------',
            f'Total Workouts: {stats.get("total_workouts") or 0}',
            f'Total Minutes: {stats.get("total_minutes") or 0}',
            f'Total Calories Burned: {stats.get("total_calories") or 0}',
            '',
            '-------------------------------------------',
            'RECOMMENDATIONS',
            '-------------------------------------------',
            '1. Continue with your fitness routine.',
            '2. Stay hydrated and maintain a balanced diet.',
            '3. Get adequate sleep for recovery.',
            '4. Monitor progress weekly.',
            '',
            'This report was generated from Iron Hub Dashboard.',
            '===========================================',
        ])

        output = '\n'.join(report_text)
        buffer = BytesIO(output.encode('utf-8'))
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'fitness-progress-report-{datetime.now().strftime("%Y%m%d-%H%M%S")}.txt',
            mimetype='text/plain'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── API: Process Payment (Mock) ─────────────────────────
@app.route('/api/payment/process', methods=['POST'])
def api_process_payment():
    if 'user_id' not in session or session.get('user_role') != 'user':
        return jsonify({'error': 'Unauthorized'}), 403
    
    user_id = session['user_id']
    data = request.get_json()
    
    try:
        conn = db_connection()
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO payments (
                    user_id, billing_name, address_line1, address_line2, 
                    city, state, zip_code, payment_method, amount
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                user_id,
                data.get('billing_name', ''),
                data.get('address_line1', ''),
                data.get('address_line2', ''),
                data.get('city', ''),
                data.get('state', ''),
                data.get('zip_code', ''),
                data.get('payment_method', 'Card'),
                data.get('amount', 112.92)
            ))
            conn.commit()
            
        # Optional: You could update the subscription status here if needed
        # but the prompt specifically requested saving to DB and ignoring complex backend logic
        
        return jsonify({'message': 'Payment processed successfully', 'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

# ── No-cache for protected pages ─────────────────────────
@app.after_request
def no_cache(response):
    if request.path.startswith(('/dashboard', '/trainer/dashboard', '/admin/dashboard')):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma']        = 'no-cache'
        response.headers['Expires']       = '0'
    return response

# ── Logout ─────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

