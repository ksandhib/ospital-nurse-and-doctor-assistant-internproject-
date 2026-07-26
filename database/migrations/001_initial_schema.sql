CREATE DATABASE IF NOT EXISTS ai_clinicos CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE ai_clinicos;

CREATE TABLE users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  full_name VARCHAR(120) NOT NULL,
  email VARCHAR(160) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role ENUM('doctor','nurse') NOT NULL,
  specialty VARCHAR(120),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX ix_users_email (email)
);

CREATE TABLE patients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_code VARCHAR(16) NOT NULL UNIQUE,
  name VARCHAR(140) NOT NULL,
  age INT,
  gender VARCHAR(30),
  dob DATE,
  phone VARCHAR(30) NOT NULL,
  email VARCHAR(160),
  address TEXT,
  emergency_contact VARCHAR(80),
  blood_group VARCHAR(8),
  height_cm FLOAT,
  weight_kg FLOAT,
  bmi FLOAT,
  allergies TEXT,
  chronic_diseases TEXT,
  photo_path VARCHAR(255),
  notes TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_patient_search (patient_code, name, phone),
  INDEX ix_patients_name (name),
  INDEX ix_patients_phone (phone)
);

CREATE TABLE vitals (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  recorded_by_id INT NOT NULL,
  temperature_c FLOAT,
  pulse INT,
  systolic_bp INT,
  diastolic_bp INT,
  oxygen_saturation FLOAT,
  respiratory_rate INT,
  notes TEXT,
  recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_vitals_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
  CONSTRAINT fk_vitals_user FOREIGN KEY (recorded_by_id) REFERENCES users(id),
  INDEX ix_vitals_patient (patient_id)
);

CREATE TABLE visits (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  doctor_id INT NOT NULL,
  symptoms TEXT NOT NULL,
  diagnosis TEXT,
  doctor_notes TEXT,
  ai_summary TEXT,
  follow_up_date DATE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_visits_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
  CONSTRAINT fk_visits_doctor FOREIGN KEY (doctor_id) REFERENCES users(id),
  INDEX ix_visits_patient (patient_id),
  INDEX ix_visits_doctor (doctor_id),
  FULLTEXT INDEX ft_visits_search (symptoms, diagnosis, doctor_notes)
);

CREATE TABLE medicines (
  id INT AUTO_INCREMENT PRIMARY KEY,
  medicine_code VARCHAR(40) NOT NULL UNIQUE,
  medicine_name VARCHAR(180) NOT NULL,
  generic_name VARCHAR(180),
  brand_name VARCHAR(180),
  drug_class VARCHAR(120),
  therapeutic_category VARCHAR(120),
  indications TEXT,
  dosage_form VARCHAR(80),
  strength VARCHAR(80),
  adult_dose TEXT,
  pediatric_dose TEXT,
  elderly_dose TEXT,
  contraindications TEXT,
  side_effects TEXT,
  drug_interactions TEXT,
  pregnancy_safety VARCHAR(120),
  storage_conditions TEXT,
  manufacturer VARCHAR(160),
  prescription_required BOOLEAN NOT NULL DEFAULT TRUE,
  stock_quantity INT NOT NULL DEFAULT 0,
  notes TEXT,
  symptoms_keywords TEXT,
  search_keywords TEXT,
  medicine_description TEXT,
  clinical_notes TEXT,
  common_diseases TEXT,
  alternative_medicines TEXT,
  INDEX ix_medicines_name (medicine_name),
  INDEX ix_medicines_generic (generic_name),
  FULLTEXT INDEX ft_medicine_search (medicine_name, generic_name, brand_name, indications, therapeutic_category, symptoms_keywords, search_keywords, medicine_description, common_diseases)
);

CREATE TABLE prescription_items (
  id INT AUTO_INCREMENT PRIMARY KEY,
  visit_id INT NOT NULL,
  medicine_id INT,
  medicine_name VARCHAR(180) NOT NULL,
  dosage VARCHAR(120) NOT NULL,
  frequency VARCHAR(120) NOT NULL,
  duration VARCHAR(120) NOT NULL,
  instructions TEXT,
  ai_suggested BOOLEAN NOT NULL DEFAULT FALSE,
  doctor_approved BOOLEAN NOT NULL DEFAULT FALSE,
  CONSTRAINT fk_prescriptions_visit FOREIGN KEY (visit_id) REFERENCES visits(id),
  CONSTRAINT fk_prescriptions_medicine FOREIGN KEY (medicine_id) REFERENCES medicines(id),
  INDEX ix_prescriptions_visit (visit_id)
);

CREATE TABLE patient_documents (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  uploaded_by_id INT NOT NULL,
  document_type VARCHAR(80) NOT NULL,
  title VARCHAR(160) NOT NULL,
  file_path VARCHAR(255) NOT NULL,
  notes TEXT,
  uploaded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_documents_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
  CONSTRAINT fk_documents_user FOREIGN KEY (uploaded_by_id) REFERENCES users(id),
  INDEX ix_documents_patient (patient_id)
);

CREATE TABLE appointments (
  id INT AUTO_INCREMENT PRIMARY KEY,
  patient_id INT NOT NULL,
  booked_by_id INT NOT NULL,
  appointment_at DATETIME NOT NULL,
  reason TEXT,
  status ENUM('scheduled','completed','cancelled','missed') NOT NULL DEFAULT 'scheduled',
  follow_up_required BOOLEAN NOT NULL DEFAULT FALSE,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_appointments_patient FOREIGN KEY (patient_id) REFERENCES patients(id),
  CONSTRAINT fk_appointments_user FOREIGN KEY (booked_by_id) REFERENCES users(id),
  INDEX ix_appointments_patient (patient_id),
  INDEX ix_appointments_at (appointment_at)
);
