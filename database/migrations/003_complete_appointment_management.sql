USE ai_clinicos;

ALTER TABLE appointments
  MODIFY status ENUM('waiting','in_progress','completed','cancelled','scheduled','missed') NOT NULL DEFAULT 'waiting';

ALTER TABLE appointments
  ADD COLUMN token_number VARCHAR(12) NULL,
  ADD COLUMN doctor_id INT NULL,
  ADD COLUMN appointment_date DATE NULL,
  ADD COLUMN appointment_time TIME NULL,
  ADD COLUMN visit_type VARCHAR(40) NULL,
  ADD COLUMN priority VARCHAR(20) NULL,
  ADD COLUMN reason_for_visit TEXT NULL,
  ADD COLUMN notes TEXT NULL,
  ADD COLUMN created_by INT NULL,
  ADD COLUMN updated_at DATETIME NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  ADD INDEX ix_appointments_token (token_number),
  ADD INDEX ix_appointments_doctor (doctor_id),
  ADD INDEX ix_appointments_date (appointment_date),
  ADD CONSTRAINT fk_appointments_doctor FOREIGN KEY (doctor_id) REFERENCES users(id),
  ADD CONSTRAINT fk_appointments_created_by FOREIGN KEY (created_by) REFERENCES users(id);
