from __future__ import annotations

import sqlite3


SCHEMA = [

    """
    CREATE TABLE IF NOT EXISTS documents(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        filename TEXT NOT NULL UNIQUE,

        sha256 TEXT,

        document_type TEXT NOT NULL,

        subject TEXT,

        year INTEGER,

        phase TEXT,

        code TEXT,

        extracted_text TEXT NOT NULL,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS exams(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        exam_key TEXT NOT NULL UNIQUE,

        subject TEXT NOT NULL,

        code TEXT NOT NULL,

        year INTEGER NOT NULL,

        phase TEXT NOT NULL,

        exam_document_id INTEGER NOT NULL,

        criteria_document_id INTEGER,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(exam_document_id) REFERENCES documents(id),

        FOREIGN KEY(criteria_document_id) REFERENCES documents(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS groups_table(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        exam_id INTEGER NOT NULL,

        group_name TEXT NOT NULL,

        display_order INTEGER NOT NULL,

        FOREIGN KEY(exam_id) REFERENCES exams(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS questions(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        exam_id INTEGER NOT NULL,

        group_id INTEGER,

        question_number TEXT NOT NULL,

        statement TEXT NOT NULL,

        question_type TEXT,

        max_points REAL,

        difficulty TEXT,

        bloom_level TEXT,

        topic TEXT,

        FOREIGN KEY(exam_id) REFERENCES exams(id),

        FOREIGN KEY(group_id) REFERENCES groups_table(id)

    );
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_unique

    ON questions(

        exam_id,

        question_number

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS choices(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        question_id INTEGER NOT NULL,

        letter TEXT,

        text TEXT,

        is_correct INTEGER DEFAULT 0,

        FOREIGN KEY(question_id) REFERENCES questions(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS criteria(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        question_id INTEGER NOT NULL UNIQUE,

        criteria_text TEXT,

        FOREIGN KEY(question_id) REFERENCES questions(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS ai_cache(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        question_id INTEGER NOT NULL UNIQUE,

        model TEXT,

        prompt_hash TEXT,

        response_json TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY(question_id) REFERENCES questions(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS student_attempts(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student TEXT,

        exam_id INTEGER,

        started_at TIMESTAMP,

        finished_at TIMESTAMP,

        score REAL,

        FOREIGN KEY(exam_id) REFERENCES exams(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS student_answers(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        attempt_id INTEGER,

        question_id INTEGER,

        answer TEXT,

        is_correct INTEGER,

        obtained_points REAL,

        feedback TEXT,

        FOREIGN KEY(attempt_id) REFERENCES student_attempts(id),

        FOREIGN KEY(question_id) REFERENCES questions(id)

    );
    """,

    """
    CREATE TABLE IF NOT EXISTS student_statistics(

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        student TEXT,

        subject TEXT,

        topic TEXT,

        attempts INTEGER,

        success_rate REAL,

        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

    );
    """
]


def create_schema(conn: sqlite3.Connection):

    cursor = conn.cursor()

    cursor.execute("PRAGMA foreign_keys = ON")

    for sql in SCHEMA:

        cursor.execute(sql)

    conn.commit()