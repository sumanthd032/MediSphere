from flask import Flask, render_template, request, redirect, url_for, session, flash, Response
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
from config import Config
from datetime import datetime, date
import csv
from io import StringIO
import re

app = Flask(__name__)
app.config.from_object(Config)

mysql = MySQL(app)
bcrypt = Bcrypt(app)

def login_required(role=None):
    def decorator(f):
        def wrapped_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            if role and session['role'] != role:
                flash('Access denied.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        wrapped_function.__name__ = f.__name__
        return wrapped_function
    return decorator

def log_activity(user_id, action):
    cur = mysql.connection.cursor()
    try:
        cur.execute("INSERT INTO activity_logs (user_id, action) VALUES (%s, %s)", (user_id, action))
        mysql.connection.commit()
    except:
        mysql.connection.rollback()
    finally:
        cur.close()

def validate_username(username):
    if not re.match(r'^[a-zA-Z0-9_]{3,50}$', username):
        return False
    return True

def validate_password(password):
    if len(password) < 6 or not re.search(r'[A-Z]', password) or not re.search(r'[0-9]', password):
        return False
    return True

def validate_contact(contact):
    if contact and not re.match(r'^\+?1?\d{9,15}$', contact):
        return False
    return True

def validate_date(appointment_date):
    try:
        dt = datetime.strptime(appointment_date, '%Y-%m-%dT%H:%M')
        return dt > datetime.now()
    except ValueError:
        return False

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        role = request.form['role']
        
        if not validate_username(username):
            flash('Invalid username format.', 'danger')
            return render_template('login.html')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id, password, role FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        
        if user and bcrypt.check_password_hash(user['password'], password) and user['role'] == role:
            if role == 'patient':
                cur = mysql.connection.cursor()
                cur.execute("SELECT is_approved FROM patients WHERE user_id = %s", (user['user_id'],))
                patient = cur.fetchone()
                cur.close()
                if not patient['is_approved']:
                    flash('Your account is pending approval.', 'warning')
                    return render_template('login.html')
            session['user_id'] = user['user_id']
            session['role'] = user['role']
            log_activity(user['user_id'], f"{role} login")
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials or role. Please try again.', 'danger')
            return render_template('login.html')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        name = request.form['name'].strip()
        contact = request.form.get('contact', '').strip()
        role = request.form['role']
        
        if not validate_username(username):
            flash('Username must be 3-50 characters, alphanumeric or underscore.', 'danger')
            return render_template('register.html')
        if not validate_password(password):
            flash('Password must be at least 6 characters, with an uppercase letter and a number.', 'danger')
            return render_template('register.html')
        if not name or len(name) > 100:
            flash('Name is required and must be under 100 characters.', 'danger')
            return render_template('register.html')
        if not validate_contact(contact):
            flash('Invalid contact number format.', 'danger')
            return render_template('register.html')
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT user_id FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            cur.close()
            flash('Username already exists.', 'danger')
            return render_template('register.html')
        
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        
        try:
            cur.execute(
                "INSERT INTO users (username, password, role) VALUES (%s, %s, %s)",
                (username, hashed_password, role)
            )
            user_id = cur.lastrowid
            
            if role == 'patient':
                cur.execute(
                    "INSERT INTO patients (user_id, name, contact, is_approved) VALUES (%s, %s, %s, %s)",
                    (user_id, name, contact, False)
                )
            elif role == 'doctor':
                specialization = request.form['specialization'].strip()
                department_id = request.form['department_id']
                if not specialization or len(specialization) > 100:
                    raise ValueError('Specialization is required and must be under 100 characters.')
                cur.execute(
                    "INSERT INTO doctors (user_id, name, specialization, department_id) VALUES (%s, %s, %s, %s)",
                    (user_id, name, specialization, department_id or None)
                )
            
            mysql.connection.commit()
            log_activity(user_id, f"{role} registration")
            flash('Registration successful! Awaiting approval for patients.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Registration failed: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT department_id, name FROM departments")
    departments = cur.fetchall()
    cur.close()
    return render_template('register.html', departments=departments)

@app.route('/dashboard')
@login_required()
def dashboard():
    cur = mysql.connection.cursor()
    if session['role'] == 'admin':
        cur.execute("SELECT COUNT(*) AS count FROM doctors")
        total_doctors = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) AS count FROM patients")
        total_patients = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) AS count FROM appointments")
        total_appointments = cur.fetchone()['count']
        cur.close()
        return render_template('admin_dashboard.html', total_doctors=total_doctors, total_patients=total_patients, total_appointments=total_appointments)
    elif session['role'] == 'doctor':
        cur.execute("SELECT COUNT(*) AS count FROM appointments WHERE doctor_id = (SELECT doctor_id FROM doctors WHERE user_id = %s) AND appointment_date >= CURDATE()", (session['user_id'],))
        upcoming_appointments = cur.fetchone()['count']
        cur.execute("SELECT COUNT(*) AS count FROM appointments WHERE doctor_id = (SELECT doctor_id FROM doctors WHERE user_id = %s) AND DATE(appointment_date) = CURDATE()", (session['user_id'],))
        today_appointments = cur.fetchone()['count']
        cur.close()
        return render_template('doctor_dashboard.html', upcoming_appointments=upcoming_appointments, today_appointments=today_appointments)
    else:  # patient
        cur.execute("SELECT a.appointment_id, a.appointment_date, a.status, d.name AS doctor_name FROM appointments a JOIN doctors d ON a.doctor_id = d.doctor_id WHERE a.patient_id = (SELECT patient_id FROM patients WHERE user_id = %s)", (session['user_id'],))
        appointments = cur.fetchall()
        cur.close()
        return render_template('patient_dashboard.html', appointments=appointments)

@app.route('/doctor_management', methods=['GET', 'POST'])
@login_required('admin')
def doctor_management():
    if request.method == 'POST':
        action = request.form.get('action')
        cur = mysql.connection.cursor()
        try:
            if action == 'add':
                username = request.form['username'].strip()
                password = request.form['password']
                name = request.form['name'].strip()
                specialization = request.form['specialization'].strip()
                department_id = request.form['department_id']
                if not validate_username(username) or not validate_password(password) or not name or not specialization:
                    raise ValueError('Invalid input data.')
                hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
                cur.execute("INSERT INTO users (username, password, role) VALUES (%s, %s, %s)", (username, hashed_password, 'doctor'))
                user_id = cur.lastrowid
                cur.execute("INSERT INTO doctors (user_id, name, specialization, department_id) VALUES (%s, %s, %s, %s)", (user_id, name, specialization, department_id or None))
                log_activity(session['user_id'], "Doctor added")
                flash('Doctor added successfully.', 'success')
            elif action == 'edit':
                doctor_id = request.form['doctor_id']
                name = request.form['name'].strip()
                specialization = request.form['specialization'].strip()
                department_id = request.form['department_id']
                if not name or not specialization:
                    raise ValueError('Name and specialization are required.')
                cur.execute("UPDATE doctors SET name = %s, specialization = %s, department_id = %s WHERE doctor_id = %s", (name, specialization, department_id or None, doctor_id))
                log_activity(session['user_id'], f"Doctor {doctor_id} updated")
                flash('Doctor updated successfully.', 'success')
            elif action == 'delete':
                doctor_id = request.form['doctor_id']
                cur.execute("DELETE FROM doctors WHERE doctor_id = %s", (doctor_id,))
                log_activity(session['user_id'], f"Doctor {doctor_id} deleted")
                flash('Doctor deleted successfully.', 'success')
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT d.doctor_id, d.name, d.specialization, dep.name AS department_name FROM doctors d LEFT JOIN departments dep ON d.department_id = dep.department_id")
    doctors = cur.fetchall()
    cur.execute("SELECT department_id, name FROM departments")
    departments = cur.fetchall()
    cur.close()
    return render_template('doctor_management.html', doctors=doctors, departments=departments)

@app.route('/patient_management', methods=['GET', 'POST'])
@login_required('admin')
def patient_management():
    if request.method == 'POST':
        patient_id = request.form['patient_id']
        cur = mysql.connection.cursor()
        try:
            cur.execute("UPDATE patients SET is_approved = TRUE WHERE patient_id = %s", (patient_id,))
            mysql.connection.commit()
            log_activity(session['user_id'], f"Patient {patient_id} approved")
            flash('Patient approved successfully.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT p.patient_id, p.name, p.contact, p.is_approved, p.medical_history FROM patients p")
    patients = cur.fetchall()
    cur.close()
    return render_template('patient_management.html', patients=patients)

@app.route('/appointment_overview', methods=['GET', 'POST'])
@login_required('admin')
def appointment_overview():
    cur = mysql.connection.cursor()
    query = """
        SELECT a.appointment_id, a.appointment_date, a.status, d.name AS doctor_name, p.name AS patient_name
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN patients p ON a.patient_id = p.patient_id
    """
    params = []
    if request.method == 'POST':
        doctor_id = request.form.get('doctor_id')
        patient_id = request.form.get('patient_id')
        if doctor_id:
            query += " WHERE a.doctor_id = %s"
            params.append(doctor_id)
        elif patient_id:
            query += " WHERE a.patient_id = %s"
            params.append(patient_id)
    
    cur.execute(query, params)
    appointments = cur.fetchall()
    cur.execute("SELECT doctor_id, name FROM doctors")
    doctors = cur.fetchall()
    cur.execute("SELECT patient_id, name FROM patients")
    patients = cur.fetchall()
    cur.close()
    return render_template('appointment_overview.html', appointments=appointments, doctors=doctors, patients=patients)

@app.route('/department_management', methods=['GET', 'POST'])
@login_required('admin')
def department_management():
    if request.method == 'POST':
        action = request.form.get('action')
        cur = mysql.connection.cursor()
        try:
            if action == 'add':
                name = request.form['name'].strip()
                if not name or len(name) > 100:
                    raise ValueError('Department name is required and must be under 100 characters.')
                cur.execute("INSERT INTO departments (name) VALUES (%s)", (name,))
                log_activity(session['user_id'], f"Department {name} added")
                flash('Department added successfully.', 'success')
            elif action == 'edit':
                department_id = request.form['department_id']
                name = request.form['name'].strip()
                if not name or len(name) > 100:
                    raise ValueError('Department name is required and must be under 100 characters.')
                cur.execute("UPDATE departments SET name = %s WHERE department_id = %s", (name, department_id))
                log_activity(session['user_id'], f"Department {department_id} updated")
                flash('Department updated successfully.', 'success')
            elif action == 'delete':
                department_id = request.form['department_id']
                cur.execute("DELETE FROM departments WHERE department_id = %s", (department_id,))
                log_activity(session['user_id'], f"Department {department_id} deleted")
                flash('Department deleted successfully.', 'success')
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT department_id, name FROM departments")
    departments = cur.fetchall()
    cur.close()
    return render_template('department_management.html', departments=departments)

@app.route('/reports', methods=['GET', 'POST'])
@login_required('admin')
def reports():
    cur = mysql.connection.cursor()
    report_type = request.form.get('report_type', 'appointments') if request.method == 'POST' else 'appointments'
    start_date = request.form.get('start_date', '')
    end_date = request.form.get('end_date', '')
    
    if report_type == 'appointments':
        query = """
            SELECT a.appointment_id, a.appointment_date, a.status, d.name AS doctor_name, p.name AS patient_name
            FROM appointments a
            JOIN doctors d ON a.doctor_id = d.doctor_id
            JOIN patients p ON a.patient_id = p.patient_id
        """
        params = []
        if start_date and end_date:
            query += " WHERE a.appointment_date BETWEEN %s AND %s"
            params = [start_date, end_date]
        cur.execute(query, params)
        data = cur.fetchall()
    else:  # activity_logs
        query = """
            SELECT al.log_id, al.action, al.timestamp, u.username
            FROM activity_logs al
            JOIN users u ON al.user_id = u.user_id
        """
        params = []
        if start_date and end_date:
            query += " WHERE al.timestamp BETWEEN %s AND %s"
            params = [start_date, end_date]
        cur.execute(query, params)
        data = cur.fetchall()
    
    if request.form.get('download'):
        output = StringIO()
        writer = csv.writer(output)
        if report_type == 'appointments':
            writer.writerow(['Appointment ID', 'Date', 'Status', 'Doctor', 'Patient'])
            for row in data:
                writer.writerow([row['appointment_id'], row['appointment_date'], row['status'], row['doctor_name'], row['patient_name']])
        else:
            writer.writerow(['Log ID', 'Action', 'Timestamp', 'Username'])
            for row in data:
                writer.writerow([row['log_id'], row['action'], row['timestamp'], row['username']])
        
        output.seek(0)
        cur.close()
        return Response(
            output.getvalue(),
            mimetype='text/csv',
            headers={'Content-Disposition': f'attachment;filename={report_type}_report.csv'}
        )
    
    cur.close()
    return render_template('reports.html', report_type=report_type, data=data, start_date=start_date, end_date=end_date)

@app.route('/schedule_management', methods=['GET', 'POST'])
@login_required('doctor')
def schedule_management():
    if request.method == 'POST':
        action = request.form.get('action')
        cur = mysql.connection.cursor()
        try:
            if action == 'add':
                day = request.form['day']
                start_time = request.form['start_time']
                end_time = request.form['end_time']
                if not day or not start_time or not end_time or start_time >= end_time:
                    raise ValueError('Invalid time range.')
                cur.execute("SELECT doctor_id FROM doctors WHERE user_id = %s", (session['user_id'],))
                doctor_id = cur.fetchone()['doctor_id']
                cur.execute(
                    "INSERT INTO doctor_schedules (doctor_id, day, start_time, end_time) VALUES (%s, %s, %s, %s)",
                    (doctor_id, day, start_time, end_time)
                )
                log_activity(session['user_id'], f"Schedule added for {day}")
                flash('Schedule added successfully.', 'success')
            elif action == 'delete':
                schedule_id = request.form['schedule_id']
                cur.execute("DELETE FROM doctor_schedules WHERE schedule_id = %s", (schedule_id,))
                log_activity(session['user_id'], f"Schedule {schedule_id} deleted")
                flash('Schedule deleted successfully.', 'success')
            mysql.connection.commit()
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT doctor_id FROM doctors WHERE user_id = %s", (session['user_id'],))
    doctor_id = cur.fetchone()['doctor_id']
    cur.execute("SELECT schedule_id, day, start_time, end_time FROM doctor_schedules WHERE doctor_id = %s", (doctor_id,))
    schedules = cur.fetchall()
    cur.close()
    return render_template('schedule_management.html', schedules=schedules)

@app.route('/doctor_appointments', methods=['GET', 'POST'])
@login_required('doctor')
def doctor_appointments():
    if request.method == 'POST':
        appointment_id = request.form['appointment_id']
        action = request.form['action']
        cur = mysql.connection.cursor()
        try:
            cur.execute("UPDATE appointments SET status = %s WHERE appointment_id = %s", (action, appointment_id))
            mysql.connection.commit()
            log_activity(session['user_id'], f"Appointment {appointment_id} {action}")
            flash(f'Appointment {action}.', 'success')
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT a.appointment_id, a.appointment_date, a.status, p.name AS patient_name, p.patient_id
        FROM appointments a
        JOIN patients p ON a.patient_id = p.patient_id
        WHERE a.doctor_id = (SELECT doctor_id FROM doctors WHERE user_id = %s)
    """, (session['user_id'],))
    appointments = cur.fetchall()
    cur.close()
    return render_template('doctor_appointments.html', appointments=appointments)

@app.route('/patient_profile/<int:patient_id>')
@login_required('doctor')
def patient_profile(patient_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT p.name, p.contact, p.medical_history FROM patients p WHERE p.patient_id = %s", (patient_id,))
    patient = cur.fetchone()
    cur.execute("SELECT pr.prescription_id, pr.medication, pr.notes, pr.created_at FROM prescriptions pr WHERE pr.patient_id = %s", (patient_id,))
    prescriptions = cur.fetchall()
    cur.close()
    return render_template('patient_profile.html', patient=patient, prescriptions=prescriptions)

@app.route('/write_prescription/<int:appointment_id>', methods=['GET', 'POST'])
@login_required('doctor')
def write_prescription(appointment_id):
    if request.method == 'POST':
        medication = request.form['medication'].strip()
        notes = request.form['notes'].strip()
        if not medication:
            flash('Medication is required.', 'danger')
            return render_template('write_prescription.html', appointment_id=appointment_id)
        cur = mysql.connection.cursor()
        try:
            cur.execute("SELECT doctor_id, patient_id FROM appointments WHERE appointment_id = %s", (appointment_id,))
            appt = cur.fetchone()
            cur.execute(
                "INSERT INTO prescriptions (appointment_id, doctor_id, patient_id, medication, notes) VALUES (%s, %s, %s, %s, %s)",
                (appointment_id, appt['doctor_id'], appt['patient_id'], medication, notes)
            )
            mysql.connection.commit()
            log_activity(session['user_id'], f"Prescription added for appointment {appointment_id}")
            flash('Prescription added successfully.', 'success')
            return redirect(url_for('doctor_appointments'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    return render_template('write_prescription.html', appointment_id=appointment_id)

@app.route('/doctor_directory')
@login_required('patient')
def doctor_directory():
    cur = mysql.connection.cursor()
    cur.execute("SELECT d.doctor_id, d.name, d.specialization, d.schedule, dep.name AS department_name FROM doctors d LEFT JOIN departments dep ON d.department_id = dep.department_id")
    doctors = cur.fetchall()
    cur.close()
    return render_template('doctor_directory.html', doctors=doctors)

@app.route('/book_appointment', methods=['GET', 'POST'])
@login_required('patient')
def book_appointment():
    if request.method == 'POST':
        doctor_id = request.form['doctor_id']
        appointment_date = request.form['appointment_date']
        
        if not validate_date(appointment_date):
            flash('Appointment date must be in the future.', 'danger')
            cur = mysql.connection.cursor()
            cur.execute("SELECT doctor_id, name FROM doctors")
            doctors = cur.fetchall()
            cur.close()
            return render_template('book_appointment.html', doctors=doctors, now=datetime.now)
        
        appt_dt = datetime.strptime(appointment_date, '%Y-%m-%dT%H:%M')
        day_name = appt_dt.strftime('%A')
        appt_time = appt_dt.time()
        
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT start_time, end_time
            FROM doctor_schedules
            WHERE doctor_id = %s AND day = %s AND start_time <= %s AND end_time >= %s
        """, (doctor_id, day_name, appt_time, appt_time))
        schedule = cur.fetchone()
        
        if not schedule:
            flash('Selected time is outside doctor’s availability.', 'danger')
            cur.execute("SELECT doctor_id, name FROM doctors")
            doctors = cur.fetchall()
            cur.close()
            return render_template('book_appointment.html', doctors=doctors, now=datetime.now)
        
        try:
            cur.execute("SELECT patient_id FROM patients WHERE user_id = %s", (session['user_id'],))
            patient_id = cur.fetchone()['patient_id']
            cur.execute(
                "INSERT INTO appointments (doctor_id, patient_id, appointment_date) VALUES (%s, %s, %s)",
                (doctor_id, patient_id, appointment_date)
            )
            mysql.connection.commit()
            log_activity(session['user_id'], f"Appointment booked with doctor {doctor_id}")
            flash('Appointment booked successfully.', 'success')
            return redirect(url_for('dashboard'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT doctor_id, name FROM doctors")
    doctors = cur.fetchall()
    cur.close()
    return render_template('book_appointment.html', doctors=doctors, now=datetime.now)

@app.route('/view_prescriptions')
@login_required('patient')
def view_prescriptions():
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT pr.prescription_id, pr.medication, pr.notes, pr.created_at, d.name AS doctor_name
        FROM prescriptions pr
        JOIN doctors d ON pr.doctor_id = d.doctor_id
        WHERE pr.patient_id = (SELECT patient_id FROM patients WHERE user_id = %s)
    """, (session['user_id'],))
    prescriptions = cur.fetchall()
    cur.close()
    return render_template('view_prescriptions.html', prescriptions=prescriptions)

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        log_activity(user_id, f"{session['role']} logout")
    session.pop('user_id', None)
    session.pop('role', None)
    flash('Logged out successfully.', 'success')
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)