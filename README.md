
# MediSphere Hospital Management System

MediSphere is a **web-based hospital management system** built using **Flask**, **MySQL**, and **Bootstrap 5**. It offers a modern, responsive platform with role-based functionality for **administrators**, **doctors**, and **patients** to efficiently manage hospital operations.

---

## 🚀 Features

### 🛠️ Admin
- Manage doctors (add/edit/delete) and departments.
- Approve or reject patient registrations.
- View, filter, and download appointment and activity reports (CSV).
- Monitor system activity through logs.

### 🩺 Doctor
- Manage personal schedule (day & time availability).
- View, accept/reject appointments.
- Access patient profiles and history.
- Write prescriptions for accepted appointments.

### 👨‍⚕️ Patient
- Register and await admin approval.
- Browse doctor directory and book appointments.
- View appointment status and prescriptions.
- Access personal dashboard with all details.

### 🌐 General
- Role-based authentication (admin, doctor, patient).
- Secure form validations (client-side and server-side).
- Responsive design with loading spinners and flash messages.
- Custom 404 and 500 error pages.
- Full activity logging and optimized DB with indexes and foreign keys.

---

## 🧑‍💻 Tech Stack

| Component   | Technology        |
|------------|-------------------|
| Backend     | Flask 3.0.3, Python 3.12 |
| Database    | MySQL (InnoDB)    |
| Frontend    | Bootstrap 5.3.0, HTML, CSS, JS |
| Security    | Bcrypt (Flask-Bcrypt), Parameterized SQL |
| Dependencies| Flask-MySQLdb, Flask-Bcrypt |

---

## ⚙️ Prerequisites

- Python 3.12+
- MySQL 8.0+
- pip (Python package manager)
- Git (optional, for cloning)

---

## 🛠️ Setup Instructions

### 1. Clone the Repository
```bash
git clone <repository-url>
cd MediSphere
```

### 2. Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure MySQL
- Start MySQL server.
- Create the database and tables:
```bash
mysql -u root -p < init_db.sql
```

- Update `config.py`:
```python
class Config:
    SECRET_KEY = 'your-secure-random-key'
    MYSQL_HOST = 'localhost'
    MYSQL_USER = 'root'
    MYSQL_PASSWORD = 'your-mysql-password'
    MYSQL_DB = 'medisphere'
    MYSQL_CURSORCLASS = 'DictCursor'
```

### 5. Create Admin User
Generate a hashed password:
```python
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()
print(bcrypt.generate_password_hash('Admin123').decode('utf-8'))
```

Insert admin:
```sql
INSERT INTO users (username, password, role) VALUES ('admin_user', '<hashed_password>', 'admin');
```

### 6. Run the Application
```bash
python app.py
```

Visit: [http://localhost:5000](http://localhost:5000)

---

## 🗂️ File Structure

```
MediSphere/
├── static/
│   └── css/style.css
├── templates/
│   ├── base.html, login.html, register.html
│   ├── admin_dashboard.html, doctor_dashboard.html, patient_dashboard.html
│   ├── doctor_management.html, patient_management.html
│   ├── appointment_overview.html, department_management.html, reports.html
│   ├── schedule_management.html, doctor_directory.html, book_appointment.html
│   ├── doctor_appointments.html, patient_profile.html
│   ├── write_prescription.html, view_prescriptions.html
│   ├── 404.html, 500.html
├── app.py
├── config.py
├── init_db.sql
└── README.md
```

---

## 🧭 Future Enhancements

- CSRF protection (Flask-WTF).
- Email notifications (approvals, appointments).
- File uploads (e.g., medical records).
- Timezone handling for global use.
- Charts and graphs in reports (e.g., Chart.js).
- Unit testing with pytest.

---



## 📄 License

This project is **for educational purposes only** and is **not licensed for commercial use**.

---

## 📬 Contact

For support or feedback, open an issue in the repository or contact me
