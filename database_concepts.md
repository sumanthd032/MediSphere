
# Database Concepts in MediSphere Hospital Management System

The MediSphere Hospital Management System uses a relational database (MySQL with InnoDB engine) to manage hospital operations for administrators, doctors, and patients. This document explains the database concepts applied, including normalization, table structure, relationships, constraints, SQL commands, indexes, and other principles, along with their implementation in the project.
The below provided database concepts provide a deeper understanding to the project.

## 1. Database Concepts Applied

### 1.1 Relational Database Model
**Definition:** A relational database organizes data into tables, where each table (relation) contains rows (tuples) and columns (attributes). Tables are linked via keys (primary and foreign keys).  
**Implementation:** The MediSphere system uses MySQL to store data in eight tables: `users`, `departments`, `doctors`, `patients`, `appointments`, `prescriptions`, `activity_logs`, and `doctor_schedules`. Each table represents a specific entity, and relationships are established using foreign keys.

### 1.2 Normalization

Normalization is the process of organizing data to eliminate redundancy and ensure data integrity. The MediSphere database is normalized to the Third Normal Form (3NF), which includes:

**First Normal Form (1NF):**  
- Requirement: All attributes must be atomic (no repeating groups or arrays), and each table must have a primary key.  
- Implementation: All tables have atomic attributes. For example, the `users` table stores `username` as a single value (VARCHAR), and each table has a primary key (e.g., `user_id`, `department_id`). No multi-valued attributes (e.g., lists) are used.

**Second Normal Form (2NF):**  
- Requirement: Must be in 1NF, and all non-key attributes must depend on the entire primary key (no partial dependency).  
- Implementation: All tables have single-column primary keys, so partial dependency is not applicable. For composite keys (e.g., `doctor_schedules` unique constraint on `(doctor_id, day, start_time)`), all attributes (e.g., `end_time`) depend on the full key.

**Third Normal Form (3NF):**  
- Requirement: Must be in 2NF, and no transitive dependencies (non-key attributes must not depend on other non-key attributes).  
- Implementation: Non-key attributes depend only on the primary key. For example, in the `doctors` table, `name` and `specialization` depend on `doctor_id`, not on each other. The `patients` table separates `medical_history` from `appointments` to avoid transitive dependencies.

**Benefits in MediSphere:**  
- Reduced Redundancy: User details are stored once in `users`, referenced by `doctors` and `patients` via `user_id`.  
- Data Integrity: Foreign keys ensure valid relationships (e.g., `appointments.doctor_id` references `doctors.doctor_id`).  
- Efficient Updates: Changes to a doctor’s name are made in one place (`doctors` table).

### 1.3 Entity-Relationship (ER) Model
- **Entities:** Represented by tables (`users`, `doctors`, `patients`, etc.).  
- **Attributes:** Columns in each table (e.g., `users.username`, `appointments.appointment_date`).  
- **Relationships:**  
  - One-to-One: `users` to `doctors` or `patients` (each doctor/patient has one user account).  
  - One-to-Many: `doctors` to `appointments` (one doctor can have many appointments), `departments` to `doctors` (one department can have many doctors).  
  - Many-to-Many: Indirectly via `appointments` (patients book appointments with doctors).  

**Implementation:** The ER model is implemented in `init_db.sql` with foreign keys defining relationships (e.g., `doctors.department_id` references `departments.department_id`).

### 1.4 Constraints
- **Primary Key:** Uniquely identifies each row (e.g., `user_id` in `users`).  
- **Foreign Key:** Ensures referential integrity (e.g., `appointments.doctor_id` must exist in `doctors.doctor_id`).  
- **Unique:** Prevents duplicate values (e.g., `users.username`, `doctor_schedules(doctor_id, day, start_time)`).  
- **Not Null:** Ensures mandatory fields (e.g., `users.username`, `appointments.appointment_date`).  
- **Enum:** Restricts values to a predefined set (e.g., `users.role` as `admin`, `doctor`, `patient`).  

**Implementation:** Defined in `init_db.sql` (e.g., `FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE`).

### 1.5 Indexes
**Definition:** Indexes improve query performance by allowing faster data retrieval.  
**Types Used:**  
- **Primary Key Indexes:** Automatically created for primary keys (e.g., `user_id`, `doctor_id`).  
- **Unique Indexes:** Created for unique constraints (e.g., `users.username`).  
- **Secondary Indexes:** Explicitly defined for frequent queries (e.g., `appointments.doctor_id`, `activity_logs.timestamp`).  

**Implementation:** Defined in `init_db.sql` with `CREATE INDEX` statements (e.g., `CREATE INDEX idx_doctor_id ON appointments(doctor_id)`).

### 1.6 Transactions
**Definition:** A transaction is a sequence of operations performed as a single unit, ensuring ACID properties (Atomicity, Consistency, Isolation, Durability).  
**Implementation:** Used in `app.py` for multi-table operations (e.g., registering a user and doctor/patient).  
Example:
```python
try:
    cur.execute("INSERT INTO users ...")
    cur.execute("INSERT INTO doctors ...")
    mysql.connection.commit()
except:
    mysql.connection.rollback()
```

### 1.7 Data Integrity
- **Referential Integrity:** Enforced by foreign keys with `ON DELETE CASCADE` (e.g., deleting a user removes their doctor/patient record).  
- **Domain Integrity:** Enforced by data types (e.g., `DATETIME` for `appointment_date`), `ENUM`, and validation in `app.py` (e.g., `validate_username`).  
- **Entity Integrity:** Ensured by primary keys and `NOT NULL` constraints.

