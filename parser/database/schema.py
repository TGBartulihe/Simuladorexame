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
        context_text TEXT,
        FOREIGN KEY(exam_id) REFERENCES exams(id)
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS question_contexts(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        group_id INTEGER,
        context_key TEXT NOT NULL,
        title TEXT,
        raw_text TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(exam_id) REFERENCES exams(id),
        FOREIGN KEY(group_id) REFERENCES groups_table(id)
    );
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_question_contexts_unique
    ON question_contexts(exam_id, context_key);
    """,

    """
    CREATE TABLE IF NOT EXISTS questions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        group_id INTEGER,
        context_id INTEGER,
        question_number TEXT NOT NULL,
        statement TEXT NOT NULL,
        question_type TEXT,
        max_points REAL,
        difficulty TEXT,
        bloom_level TEXT,
        topic TEXT,
        subtopic TEXT,
        estimated_minutes INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(exam_id) REFERENCES exams(id),
        FOREIGN KEY(group_id) REFERENCES groups_table(id),
        FOREIGN KEY(context_id) REFERENCES question_contexts(id)
    );
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_questions_unique
    ON questions(exam_id, question_number);
    """,

    """
    CREATE TABLE IF NOT EXISTS choices(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL,
        letter TEXT NOT NULL,
        text TEXT NOT NULL,
        is_correct INTEGER DEFAULT 0,
        FOREIGN KEY(question_id) REFERENCES questions(id)
    );
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_choices_unique
    ON choices(question_id, letter);
    """,

    """
    CREATE TABLE IF NOT EXISTS criteria(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL UNIQUE,
        criteria_text TEXT,
        max_points REAL,
        official_answer TEXT,
        FOREIGN KEY(question_id) REFERENCES questions(id)
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS images(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        question_id INTEGER,
        context_id INTEGER,
        label TEXT,
        description TEXT,
        page_number INTEGER,
        source TEXT,
        FOREIGN KEY(exam_id) REFERENCES exams(id),
        FOREIGN KEY(question_id) REFERENCES questions(id),
        FOREIGN KEY(context_id) REFERENCES question_contexts(id)
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS tables(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        exam_id INTEGER NOT NULL,
        question_id INTEGER,
        context_id INTEGER,
        label TEXT,
        raw_text TEXT NOT NULL,
        page_number INTEGER,
        FOREIGN KEY(exam_id) REFERENCES exams(id),
        FOREIGN KEY(question_id) REFERENCES questions(id),
        FOREIGN KEY(context_id) REFERENCES question_contexts(id)
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS topics(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        name TEXT NOT NULL,
        parent_id INTEGER,
        FOREIGN KEY(parent_id) REFERENCES topics(id)
    );
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_topics_unique
    ON topics(subject, name);
    """,

    """
    CREATE TABLE IF NOT EXISTS skills(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        subject TEXT NOT NULL,
        name TEXT NOT NULL
    );
    """,

    """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_skills_unique
    ON skills(subject, name);
    """,

    """
    CREATE TABLE IF NOT EXISTS question_skills(
        question_id INTEGER NOT NULL,
        skill_id INTEGER NOT NULL,
        PRIMARY KEY(question_id, skill_id),
        FOREIGN KEY(question_id) REFERENCES questions(id),
        FOREIGN KEY(skill_id) REFERENCES skills(id)
    );
    """,

    """
    CREATE TABLE IF NOT EXISTS ai_cache(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        question_id INTEGER NOT NULL UNIQUE,
        model TEXT,
        prompt_version TEXT,
        prompt_hash TEXT,
        response_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
    """,
]


def create_schema(conn: sqlite3.Connection) -> None:
    cursor = conn.cursor()
    cursor.execute("PRAGMA foreign_keys = ON")

    for sql in SCHEMA:
        cursor.execute(sql)

    conn.commit()