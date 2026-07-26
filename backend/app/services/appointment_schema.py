from sqlalchemy import inspect, text

from app.database import Base, engine


APPOINTMENT_COLUMNS = {
    "token_number": "VARCHAR(12)",
    "doctor_id": "INTEGER",
    "appointment_date": "DATE",
    "appointment_time": "TIME",
    "visit_type": "VARCHAR(40)",
    "priority": "VARCHAR(20)",
    "reason_for_visit": "TEXT",
    "notes": "TEXT",
    "created_by": "INTEGER",
    "updated_at": "DATETIME",
}


def ensure_appointment_schema() -> None:
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["appointments"]])
    inspector = inspect(engine)
    existing = {column["name"] for column in inspector.get_columns("appointments")}
    dialect = engine.dialect.name
    with engine.begin() as connection:
        if dialect == "mysql":
            connection.execute(text("ALTER TABLE appointments MODIFY status ENUM('waiting','in_progress','completed','cancelled','scheduled','missed') NOT NULL DEFAULT 'waiting'"))
        for column, column_type in APPOINTMENT_COLUMNS.items():
            if column in existing:
                continue
            if dialect == "sqlite":
                connection.execute(text(f"ALTER TABLE appointments ADD COLUMN {column} {column_type}"))
            elif dialect == "mysql":
                mysql_type = "INT" if column_type == "INTEGER" else column_type
                connection.execute(text(f"ALTER TABLE appointments ADD COLUMN {column} {mysql_type} NULL"))
