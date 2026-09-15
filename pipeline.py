#!/usr/bin/env python3
"""
Research Student Funding Data Pipeline (SQLite Embedded Edition)
================================================================
Automates the intake and normalization of two research funding CSV formats:
1. Federal Work Study (FWS) Research Funding applications
2. Student Project Grant funding applications

Stores cleaned and normalized records in an embedded SQLite database (`research_students.db`):
- Centralized table: `students_doing_research`
    (student_id, first_name, last_name, email, mentor_first_name, mentor_last_name, mentor_email, funding_type)
- Sub-table 1: `fws_funding_students` (foreign key student_id + all remaining FWS fields)
- Sub-table 2: `grant_funding_students` (foreign key student_id + all remaining Grant fields)

Built using Python, Pandas, and SQLite3 for robust data cleaning, validation, and relational migration.
"""

import sys
import os
import re
import json
import sqlite3
import argparse
from typing import Dict, Any, Tuple, Optional, List
import pandas as pd

DEFAULT_DB_PATH = os.path.abspath(os.environ.get("SQLITE_DB_PATH", "research_students.db"))


class ResearchFundingPipeline:
    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = os.path.abspath(db_path)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Returns a SQLite connection with row factory and foreign key enforcement."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def init_db(self) -> None:
        """Initializes the SQLite schema with centralized table and two sub-tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Centralized Students Doing Research Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS students_doing_research (
                student_id TEXT PRIMARY KEY,
                first_name TEXT NOT NULL,
                last_name TEXT NOT NULL,
                email TEXT NOT NULL,
                mentor_first_name TEXT,
                mentor_last_name TEXT,
                mentor_email TEXT,
                funding_type TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_students_email ON students_doing_research(email);
            """)

            # Sub-table for Federal Work Study funding students
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS fws_funding_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                submission_timestamp TEXT,
                email_raw TEXT,
                legal_first_name TEXT,
                last_name TEXT,
                preferred_name TEXT,
                pronouns TEXT,
                student_id_number TEXT,
                phone_number TEXT,
                college TEXT,
                department TEXT,
                major TEXT,
                research_duties_description TEXT,
                anticipated_graduation TEXT,
                mentor_affiliated_nc_state TEXT,
                faculty_mentor_first_name TEXT,
                faculty_mentor_last_name TEXT,
                faculty_mentor_email TEXT,
                faculty_mentor_college TEXT,
                faculty_mentor_department TEXT,
                faculty_mentor_phone TEXT,
                external_mentor_first_name TEXT,
                external_mentor_last_name TEXT,
                external_mentor_institution TEXT,
                external_mentor_job_title TEXT,
                external_mentor_email TEXT,
                external_mentor_phone TEXT,
                position_retention_intent TEXT,
                expectations_agreement TEXT,
                code_of_conduct_agreement TEXT,
                referral_source TEXT,
                approval_status TEXT,
                reviewer_name TEXT,
                review_notes TEXT,
                mentor_faculty_qualification TEXT,
                jens_notes TEXT,
                fws_eligible TEXT,
                award_amount TEXT,
                sent_contract TEXT,
                received_signed_contract TEXT,
                created_voucher TEXT,
                initiated_hire_action TEXT,
                hire_status TEXT,
                added_to_moodle TEXT,
                added_to_tracking_list TEXT,
                attended_orientation TEXT,
                raw_data_json TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students_doing_research(student_id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_fws_student_id ON fws_funding_students(student_id);
            """)

            # Sub-table for Project Grant funding students
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS grant_funding_students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                submission_timestamp TEXT,
                submitter_email TEXT,
                lead_student_first_name TEXT,
                lead_student_last_name TEXT,
                lead_student_email TEXT,
                has_co_applicants TEXT,
                co_applicants_summary TEXT,
                mentor_nc_state_affiliated TEXT,
                is_primary_mentor TEXT,
                mentor_first_name TEXT,
                mentor_last_name TEXT,
                mentor_department TEXT,
                mentor_email TEXT,
                external_mentor_first_name TEXT,
                external_mentor_last_name TEXT,
                external_mentor_institution TEXT,
                external_mentor_job_title TEXT,
                external_mentor_email TEXT,
                research_experience_narrative TEXT,
                student_readiness_evaluation TEXT,
                development_support_plan TEXT,
                additional_information TEXT,
                rec_letter_survey_preference TEXT,
                raw_data_json TEXT,
                imported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (student_id) REFERENCES students_doing_research(student_id) ON DELETE CASCADE
            );
            """)

            cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_grant_student_id ON grant_funding_students(student_id);
            """)

            cursor.execute("""
            UPDATE students_doing_research
            SET funding_type = REPLACE(REPLACE(funding_type, 'Project Grant', 'Project Supply Grant'), 'Grant', 'Project Supply Grant')
            WHERE (funding_type LIKE '%Grant%') AND (funding_type NOT LIKE '%Supply Grant%');
            """)

            conn.commit()

    def generate_next_student_id(self, cursor: sqlite3.Cursor) -> str:
        """Generates the next sequential unique student ID, e.g., STU-0001."""
        cursor.execute("SELECT student_id FROM students_doing_research ORDER BY student_id DESC")
        rows = cursor.fetchall()
        max_num = 0
        for r in rows:
            sid = r["student_id"]
            if sid.startswith("STU-"):
                try:
                    num = int(sid.split("-")[1])
                    if num > max_num:
                        max_num = num
                except (ValueError, IndexError):
                    pass
        return f"STU-{max_num + 1:04d}"

    def clean_str(self, val: Any) -> str:
        """Cleans null, NaN, and whitespace from strings."""
        if pd.isna(val) or val is None:
            return ""
        s = str(val).strip()
        if s.lower() in ("nan", "none", "null"):
            return ""
        return s

    def find_existing_student(self, cursor: sqlite3.Cursor, email: str, first_name: str, last_name: str) -> Optional[sqlite3.Row]:
        """
        Checks if student already exists in the centralized table:
        1. Exact match by email (case-insensitive)
        2. Prefix match for university unity IDs (e.g. 'pgeorge' matches 'pgeorge@ncsu.edu' or vice-versa)
        3. Match by First Name + Last Name (case-insensitive)
        """
        clean_email = email.lower().strip()
        clean_fn = first_name.lower().strip()
        clean_ln = last_name.lower().strip()

        # Check by email directly
        if clean_email:
            cursor.execute(
                "SELECT * FROM students_doing_research WHERE LOWER(email) = ?",
                (clean_email,)
            )
            match = cursor.fetchone()
            if match:
                return match

            # Unity ID / Email prefix matching
            email_prefix = clean_email.split("@")[0]
            cursor.execute(
                "SELECT * FROM students_doing_research WHERE LOWER(email) LIKE ? OR LOWER(email) = ?",
                (f"{email_prefix}@%", email_prefix)
            )
            prefix_match = cursor.fetchone()
            if prefix_match:
                return prefix_match

        # Check by student full name
        if clean_fn and clean_ln:
            cursor.execute(
                "SELECT * FROM students_doing_research WHERE LOWER(first_name) = ? AND LOWER(last_name) = ?",
                (clean_fn, clean_ln)
            )
            name_match = cursor.fetchone()
            if name_match:
                return name_match

        return None

    def update_or_create_central_student(
        self,
        cursor: sqlite3.Cursor,
        first_name: str,
        last_name: str,
        email: str,
        mentor_first: str,
        mentor_last: str,
        mentor_email: str,
        funding_source: str, # 'Federal Work Study' or 'Grant'
    ) -> Tuple[str, bool]:
        """
        Checks if student is already in the centralized students-doing-research table:
        - If not, adds the student full name, email, mentor full name, mentor email, and funding type.
        - If yes, merges funding type and fills any missing mentor/email info.
        Returns: (student_id, is_new)
        """
        existing = self.find_existing_student(cursor, email, first_name, last_name)

        if existing:
            student_id = existing["student_id"]
            existing_funding = existing["funding_type"] or ""

            # Check if funding type should be updated
            funding_parts = []
            for f in existing_funding.split(","):
                f_clean = f.strip()
                if not f_clean:
                    continue
                if f_clean in ["Grant", "Project Grant", "Supply Grant"]:
                    f_clean = "Project Supply Grant"
                if f_clean not in funding_parts:
                    funding_parts.append(f_clean)
            if funding_source not in funding_parts:
                funding_parts.append(funding_source)
            new_funding = ", ".join(funding_parts)

            # Preserve the more specific email if current one lacks domain
            best_email = existing["email"]
            if "@" in email and "@" not in best_email:
                best_email = email
            elif not best_email:
                best_email = email

            # Update mentor info if previously empty
            m_first = existing["mentor_first_name"] or mentor_first
            m_last = existing["mentor_last_name"] or mentor_last
            m_email = existing["mentor_email"] or mentor_email

            cursor.execute(
                """
                UPDATE students_doing_research
                SET funding_type = ?,
                    email = ?,
                    mentor_first_name = ?,
                    mentor_last_name = ?,
                    mentor_email = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE student_id = ?
                """,
                (new_funding, best_email, m_first, m_last, m_email, student_id)
            )
            return student_id, False

        # Student does not exist -> Create new student in centralized table
        student_id = self.generate_next_student_id(cursor)
        cursor.execute(
            """
            INSERT INTO students_doing_research (
                student_id, first_name, last_name, email,
                mentor_first_name, mentor_last_name, mentor_email, funding_type
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_id,
                first_name,
                last_name,
                email,
                mentor_first,
                mentor_last,
                mentor_email,
                funding_source
            )
        )
        return student_id, True

    def get_column_value(
        self,
        row: pd.Series,
        candidates: List[str],
        exclude_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Flexibly looks up a column value from candidate names or patterns.
        Handles punctuation (colons, apostrophes, parentheses), casing, and whitespace.
        Optional exclude_keywords prevents false positive matches (e.g. mentor vs student).
        """
        def normalize(text: Any) -> str:
            return re.sub(r"[^\w\s]", "", str(text)).lower().strip()

        # 1. Exact match against row keys
        for cand in candidates:
            if cand in row:
                val = self.clean_str(row[cand])
                if val:
                    return val

        # Map normalized column names to original column names in the row
        norm_map: Dict[str, str] = {}
        for col in row.index:
            col_str = str(col)
            norm_col = normalize(col_str)
            if exclude_keywords:
                if any(normalize(ex) in norm_col for ex in exclude_keywords):
                    continue
            norm_map[norm_col] = col_str

        # 2. Normalized equality match
        for cand in candidates:
            nc = normalize(cand)
            if nc in norm_map:
                val = self.clean_str(row[norm_map[nc]])
                if val:
                    return val

        # 3. Normalized substring match (candidate is a substring of column or column is a substring of candidate)
        for cand in candidates:
            nc = normalize(cand)
            for ncol, orig_col in norm_map.items():
                if nc in ncol or ncol in nc:
                    val = self.clean_str(row[orig_col])
                    if val:
                        return val

        return ""

    def find_val_by_keywords(self, row: pd.Series, keywords: List[str]) -> Optional[Any]:
        """Looks up a cell value in a row by finding matching keyword substrings in the column names."""
        for col_name, val in row.items():
            col_clean = str(col_name).strip().lower()
            for kw in keywords:
                if kw.lower() in col_clean:
                    if pd.notna(val) and val is not None:
                        return val
        return None

    def process_fws_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Processes Federal Work Study research applications dataframe:
        - Ingests student & mentor into central students_doing_research table
        - Ingests all remaining FWS application fields into fws_funding_students sub-table
        """
        total_rows = len(df)
        new_students_count = 0
        matched_students_count = 0
        records_inserted = 0
        details = []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for idx, row in df.iterrows():
                raw_dict = {str(k): (None if pd.isna(v) else str(v)) for k, v in row.items()}
                raw_json = json.dumps(raw_dict, default=str)

                # Extract identity fields: In FWS forms, fields are "First Name (Legal):" and "Last Name:"
                first_name = self.get_column_value(
                    row,
                    candidates=[
                        "First Name (Legal):",
                        "First Name (Legal)",
                        "Legal First Name:",
                        "Legal First Name",
                        "First Name:",
                        "First Name",
                        "Student First Name"
                    ],
                    exclude_keywords=["mentor", "reviewer", "jen"]
                )
                last_name = self.get_column_value(
                    row,
                    candidates=[
                        "Last Name:",
                        "Last Name",
                        "Legal Last Name:",
                        "Legal Last Name",
                        "Student Last Name"
                    ],
                    exclude_keywords=["mentor", "reviewer", "jen"]
                )
                email = self.get_column_value(
                    row,
                    candidates=[
                        "Email Address",
                        "Email",
                        "Student Email",
                        "Unity ID",
                        "Username"
                    ],
                    exclude_keywords=["mentor"]
                )

                # Faculty mentor fields
                mentor_first = self.get_column_value(
                    row,
                    candidates=[
                        "Faculty Mentor First Name:",
                        "Faculty Mentor First Name",
                        "Mentor First Name:",
                        "Mentor First Name"
                    ]
                )
                mentor_last = self.get_column_value(
                    row,
                    candidates=[
                        "Faculty Mentor Last Name:",
                        "Faculty Mentor Last Name",
                        "Mentor Last Name:",
                        "Mentor Last Name"
                    ]
                )
                mentor_email = self.get_column_value(
                    row,
                    candidates=[
                        "Faculty Mentor Email Address:",
                        "Faculty Mentor Email Address",
                        "Faculty Mentor Email",
                        "Mentor Email Address:",
                        "Mentor Email Address",
                        "Mentor Email"
                    ]
                )

                # Fallback to external mentor if faculty mentor is missing
                if not mentor_first and not mentor_last:
                    mentor_first = self.get_column_value(
                        row,
                        candidates=[
                            "External Mentor First Name:",
                            "External Mentor First Name",
                            "External Mentor First"
                        ]
                    )
                    mentor_last = self.get_column_value(
                        row,
                        candidates=[
                            "External Mentor Last Name:",
                            "External Mentor Last Name",
                            "External Mentor Last"
                        ]
                    )
                    mentor_email = self.get_column_value(
                        row,
                        candidates=[
                            "External Mentor Email Address:",
                            "External Mentor Email Address",
                            "External Mentor Email"
                        ]
                    )

                # Fallback if first/last name empty but email exists
                if not first_name and not last_name and email:
                    prefix = email.split("@")[0]
                    parts = prefix.split(".")
                    first_name = parts[0].capitalize()
                    last_name = parts[1].capitalize() if len(parts) > 1 else "Student"

                if not first_name and not last_name:
                    first_name = f"Applicant_{idx + 1}"
                    last_name = "FWS"

                # 1. Update or Create in Centralized Table
                student_id, is_new = self.update_or_create_central_student(
                    cursor=cursor,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    mentor_first=mentor_first,
                    mentor_last=mentor_last,
                    mentor_email=mentor_email,
                    funding_source="Federal Work Study"
                )

                if is_new:
                    new_students_count += 1
                else:
                    matched_students_count += 1

                # 2. Extract remaining FWS fields
                sub_ts = self.clean_str(row.get("Timestamp") or self.find_val_by_keywords(row, ["timestamp"]))
                email_raw = email
                pref_name = self.clean_str(row.get("Preferred Name") or self.find_val_by_keywords(row, ["preferred name"]))
                pronouns = self.clean_str(row.get("Pronouns") or self.find_val_by_keywords(row, ["pronouns"]))
                stu_id_num = self.clean_str(row.get("Student ID Number") or self.find_val_by_keywords(row, ["student id number", "student id"]))
                phone = self.clean_str(row.get("Phone Number") or self.find_val_by_keywords(row, ["phone number"]))
                college = self.clean_str(row.get("College") or self.find_val_by_keywords(row, ["college"]))
                dept = self.clean_str(row.get("Department") or self.find_val_by_keywords(row, ["department"]))
                major = self.clean_str(row.get("Major") or self.find_val_by_keywords(row, ["major"]))
                duties = self.clean_str(row.get("Description of Student Research Duties") or self.find_val_by_keywords(row, ["research duties", "duties"]))
                grad = self.clean_str(row.get("Anticipated Graduation Date") or self.find_val_by_keywords(row, ["graduation"]))
                nc_affil = self.clean_str(row.get("Is your mentor affiliated with NC State University?") or self.find_val_by_keywords(row, ["mentor affiliated"]))
                fac_coll = self.clean_str(row.get("Faculty Mentor College") or self.find_val_by_keywords(row, ["mentor college"]))
                fac_dept = self.clean_str(row.get("Faculty Mentor Department") or self.find_val_by_keywords(row, ["mentor department"]))
                fac_phone = self.clean_str(row.get("Faculty Mentor Phone Number") or self.find_val_by_keywords(row, ["mentor phone"]))
                ext_fn = self.clean_str(row.get("External Mentor First Name") or self.find_val_by_keywords(row, ["external mentor first"]))
                ext_ln = self.clean_str(row.get("External Mentor Last Name") or self.find_val_by_keywords(row, ["external mentor last"]))
                ext_inst = self.clean_str(row.get("External Mentor Institution") or self.find_val_by_keywords(row, ["external mentor institution"]))
                ext_title = self.clean_str(row.get("External Mentor Job Title") or self.find_val_by_keywords(row, ["external mentor job"]))
                ext_email = self.clean_str(row.get("External Mentor Email Address") or self.find_val_by_keywords(row, ["external mentor email"]))
                ext_phone = self.clean_str(row.get("External Mentor Phone Number") or self.find_val_by_keywords(row, ["external mentor phone"]))
                retention = self.clean_str(row.get("Do you plan to keep this position?") or self.find_val_by_keywords(row, ["keep this position"]))
                exp_agree = self.clean_str(row.get("Expectations") or self.find_val_by_keywords(row, ["expectations"]))
                code_agree = self.clean_str(row.get("Code of Conduct") or self.find_val_by_keywords(row, ["code of conduct"]))
                referral = self.clean_str(row.get("How did you hear about OUR research assistant positions?") or self.find_val_by_keywords(row, ["how did you hear"]))
                app_status = self.clean_str(row.get("Approval Status") or self.find_val_by_keywords(row, ["approval status"]))
                reviewer = self.clean_str(row.get("Reviewer Name") or self.find_val_by_keywords(row, ["reviewer name"]))
                review_notes = self.clean_str(row.get("Review Notes") or self.find_val_by_keywords(row, ["review notes"]))
                qual = self.clean_str(row.get("Faculty/Mentor Qualification") or self.find_val_by_keywords(row, ["faculty/mentor qualification"]))
                jens_notes = self.clean_str(row.get("Jen's Notes") or self.find_val_by_keywords(row, ["jen's notes"]))
                fws_elig = self.clean_str(row.get("FWS Eligible?") or self.find_val_by_keywords(row, ["fws eligible"]))
                award_amt = self.clean_str(row.get("Award Amount") or self.find_val_by_keywords(row, ["award amount"]))
                contract = self.clean_str(row.get("Sent Contract") or self.find_val_by_keywords(row, ["sent contract"]))
                rec_contract = self.clean_str(row.get("Received Signed Contract") or self.find_val_by_keywords(row, ["received signed contract"]))
                voucher = self.clean_str(row.get("Created Voucher") or self.find_val_by_keywords(row, ["created voucher"]))
                hire_action = self.clean_str(row.get("Initiated Hire Action") or self.find_val_by_keywords(row, ["initiated hire action"]))
                hire_status = self.clean_str(row.get("Hire Status") or self.find_val_by_keywords(row, ["hire status"]))
                moodle = self.clean_str(row.get("Added to Moodle") or self.find_val_by_keywords(row, ["added to moodle"]))
                tracking = self.clean_str(row.get("Added to Tracking List") or self.find_val_by_keywords(row, ["tracking list"]))
                orientation = self.clean_str(row.get("Attended Orientation") or self.find_val_by_keywords(row, ["orientation"]))

                cursor.execute(
                    """
                    INSERT INTO fws_funding_students (
                        student_id, submission_timestamp, email_raw, legal_first_name, last_name,
                        preferred_name, pronouns, student_id_number, phone_number, college,
                        department, major, research_duties_description, anticipated_graduation,
                        mentor_affiliated_nc_state, faculty_mentor_first_name, faculty_mentor_last_name,
                        faculty_mentor_email, faculty_mentor_college, faculty_mentor_department,
                        faculty_mentor_phone, external_mentor_first_name, external_mentor_last_name,
                        external_mentor_institution, external_mentor_job_title, external_mentor_email,
                        external_mentor_phone, position_retention_intent, expectations_agreement,
                        code_of_conduct_agreement, referral_source, approval_status, reviewer_name,
                        review_notes, mentor_faculty_qualification, jens_notes, fws_eligible,
                        award_amount, sent_contract, received_signed_contract, created_voucher,
                        initiated_hire_action, hire_status, added_to_moodle, added_to_tracking_list,
                        attended_orientation, raw_data_json
                    ) VALUES (
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?
                    )
                    """,
                    (
                        student_id, sub_ts, email_raw, first_name, last_name,
                        pref_name, pronouns, stu_id_num, phone, college,
                        dept, major, duties, grad,
                        nc_affil, mentor_first, mentor_last,
                        mentor_email, fac_coll, fac_dept,
                        fac_phone, ext_fn, ext_ln,
                        ext_inst, ext_title, ext_email,
                        ext_phone, retention, exp_agree,
                        code_agree, referral, app_status, reviewer,
                        review_notes, qual, jens_notes, fws_elig,
                        award_amt, contract, rec_contract, voucher,
                        hire_action, hire_status, moodle, tracking,
                        orientation, raw_json
                    )
                )
                records_inserted += 1
                details.append({
                    "student_id": student_id,
                    "student_name": f"{first_name} {last_name}",
                    "email": email,
                    "mentor": f"{mentor_first} {mentor_last}".strip(),
                    "is_new": is_new,
                    "funding_type": "Federal Work Study"
                })

            conn.commit()

        return {
            "source": "Federal Work Study (FWS)",
            "total_rows": total_rows,
            "new_students": new_students_count,
            "existing_students_matched": matched_students_count,
            "records_inserted": records_inserted,
            "details": details
        }

    def process_grant_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Processes Project Grant applications dataframe:
        - Ingests student & mentor into central students_doing_research table
        - Ingests all remaining Grant application fields into grant_funding_students sub-table
        """
        total_rows = len(df)
        new_students_count = 0
        matched_students_count = 0
        records_inserted = 0
        details = []

        with self.get_connection() as conn:
            cursor = conn.cursor()
            for idx, row in df.iterrows():
                raw_dict = {str(k): (None if pd.isna(v) else str(v)) for k, v in row.items()}
                raw_json = json.dumps(raw_dict, default=str)

                # Extract lead student identity: in grant forms, called "Lead Applicant First Name" / "Lead Student Applicant's First Name"
                first_name = self.get_column_value(
                    row,
                    candidates=[
                        "Lead Student Applicant's First Name",
                        "Lead Student Applicant First Name",
                        "Lead Applicant's First Name",
                        "Lead Applicant First Name",
                        "Lead Applicant First",
                        "Lead Student First Name",
                        "Student Applicant's First Name",
                        "Student First Name"
                    ],
                    exclude_keywords=["co-applicant", "coapplicant", "mentor", "your first"]
                )
                last_name = self.get_column_value(
                    row,
                    candidates=[
                        "Lead Student Applicant's Last Name",
                        "Lead Student Applicant Last Name",
                        "Lead Applicant's Last Name",
                        "Lead Applicant Last Name",
                        "Lead Applicant Last",
                        "Lead Student Last Name",
                        "Student Applicant's Last Name",
                        "Student Last Name"
                    ],
                    exclude_keywords=["co-applicant", "coapplicant", "mentor", "your last"]
                )
                email = self.get_column_value(
                    row,
                    candidates=[
                        "Lead Student Applicant's Email",
                        "Lead Applicant's Email",
                        "Lead Applicant Email",
                        "Lead Student Applicant Email Address",
                        "Lead Student Email",
                        "Student Applicant Email",
                        "Student Email"
                    ],
                    exclude_keywords=["co-applicant", "coapplicant", "mentor", "your email"]
                )

                submitter_email = self.get_column_value(
                    row,
                    candidates=[
                        "Email Address",
                        "Submitter Email Address",
                        "Submitter Email"
                    ]
                )

                # Extract Mentor fields: in Grant forms mentor is submitter ("Your First Name:", "Your Last Name:")
                mentor_first = self.get_column_value(
                    row,
                    candidates=[
                        "Your First Name:",
                        "Your First Name",
                        "Mentor First Name:",
                        "Mentor First Name",
                        "Primary Mentor First Name"
                    ],
                    exclude_keywords=["student", "co-applicant"]
                )
                mentor_last = self.get_column_value(
                    row,
                    candidates=[
                        "Your Last Name:",
                        "Your Last Name",
                        "Mentor Last Name:",
                        "Mentor Last Name",
                        "Primary Mentor Last Name"
                    ],
                    exclude_keywords=["student", "co-applicant"]
                )
                mentor_email = self.get_column_value(
                    row,
                    candidates=[
                        "Your Email Address:",
                        "Your Email Address",
                        "Mentor Email Address:",
                        "Mentor Email Address",
                        "Mentor Email"
                    ],
                    exclude_keywords=["student", "co-applicant"]
                )
                mentor_dept = self.get_column_value(
                    row,
                    candidates=[
                        "Your Department at NC State:",
                        "Your Department at NC State",
                        "Mentor Department",
                        "Department"
                    ]
                )

                # Fallback to submitter email for mentor if submitter is faculty mentor
                if not mentor_email and submitter_email:
                    mentor_email = submitter_email

                # Fallbacks if first/last name empty
                if not first_name and not last_name and email:
                    prefix = email.split("@")[0]
                    parts = prefix.split(".")
                    first_name = parts[0].capitalize()
                    last_name = parts[1].capitalize() if len(parts) > 1 else "GrantApplicant"

                if not first_name and not last_name:
                    first_name = f"Grantee_{idx + 1}"
                    last_name = "Grant"

                # 1. Update or Create in Centralized Table
                student_id, is_new = self.update_or_create_central_student(
                    cursor=cursor,
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    mentor_first=mentor_first,
                    mentor_last=mentor_last,
                    mentor_email=mentor_email,
                    funding_source="Project Supply Grant"
                )

                if is_new:
                    new_students_count += 1
                else:
                    matched_students_count += 1

                # 2. Extract remaining Grant fields
                sub_ts = self.clean_str(row.get("Timestamp") or self.find_val_by_keywords(row, ["timestamp"]))
                has_co_app = self.clean_str(row.get("Are there co-applicants?") or self.find_val_by_keywords(row, ["co-applicants", "co applicants"]))
                co_app_summary = self.clean_str(row.get("Co-Applicants") or self.find_val_by_keywords(row, ["co-applicants summary", "list co-applicants"]))
                mentor_nc_affil = self.clean_str(row.get("Is the primary mentor affiliated with NC State University?") or self.find_val_by_keywords(row, ["affiliated with nc state"]))
                is_primary = self.clean_str(row.get("Are you the primary mentor?") or self.find_val_by_keywords(row, ["primary mentor"]))
                mentor_dept = self.clean_str(row.get("Mentor Department") or self.find_val_by_keywords(row, ["mentor department"]))
                ext_mentor_fn = self.clean_str(row.get("External Mentor First Name") or self.find_val_by_keywords(row, ["external mentor first"]))
                ext_mentor_ln = self.clean_str(row.get("External Mentor Last Name") or self.find_val_by_keywords(row, ["external mentor last"]))
                ext_mentor_inst = self.clean_str(row.get("External Mentor Institution") or self.find_val_by_keywords(row, ["external mentor institution"]))
                ext_mentor_title = self.clean_str(row.get("External Mentor Job Title") or self.find_val_by_keywords(row, ["external mentor job"]))
                ext_mentor_email = self.clean_str(row.get("External Mentor Email Address") or self.find_val_by_keywords(row, ["external mentor email"]))
                narrative = self.clean_str(row.get("Describe your research experience with this student") or self.find_val_by_keywords(row, ["research experience with this student", "narrative"]))
                readiness = self.clean_str(row.get("Evaluate student readiness") or self.find_val_by_keywords(row, ["student readiness", "readiness"]))
                support_plan = self.clean_str(
                    row.get("Development support plan")
                    or row.get("How will you support the development of this student throughout their research project?")
                    or row.get("How will you support the development of this student throughout their research project?  ")
                    or self.find_val_by_keywords(row, [
                        "support the development of this student",
                        "development support plan",
                        "support plan",
                        "how will you support"
                    ])
                )
                add_info = self.clean_str(row.get("Additional Information") or self.find_val_by_keywords(row, ["additional information"]))
                rec_pref = self.clean_str(row.get("Recommendation Letter Preference") or self.find_val_by_keywords(row, ["recommendation", "letter"]))

                cursor.execute(
                    """
                    INSERT INTO grant_funding_students (
                        student_id, submission_timestamp, submitter_email,
                        lead_student_first_name, lead_student_last_name, lead_student_email,
                        has_co_applicants, co_applicants_summary, mentor_nc_state_affiliated,
                        is_primary_mentor, mentor_first_name, mentor_last_name,
                        mentor_department, mentor_email, external_mentor_first_name,
                        external_mentor_last_name, external_mentor_institution,
                        external_mentor_job_title, external_mentor_email,
                        research_experience_narrative, student_readiness_evaluation,
                        development_support_plan, additional_information,
                        rec_letter_survey_preference, raw_data_json
                    ) VALUES (
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?,
                        ?, ?
                    )
                    """,
                    (
                        student_id, sub_ts, submitter_email,
                        first_name, last_name, email,
                        has_co_app, co_app_summary, mentor_nc_affil,
                        is_primary, mentor_first, mentor_last,
                        mentor_dept, mentor_email, ext_mentor_fn,
                        ext_mentor_ln, ext_mentor_inst,
                        ext_mentor_title, ext_mentor_email,
                        narrative, readiness,
                        support_plan, add_info,
                        rec_pref, raw_json
                    )
                )
                records_inserted += 1
                details.append({
                    "student_id": student_id,
                    "student_name": f"{first_name} {last_name}",
                    "email": email,
                    "mentor": f"{mentor_first} {mentor_last}".strip(),
                    "is_new": is_new,
                    "funding_type": "Project Supply Grant"
                })

            conn.commit()

        return {
            "source": "Project Supply Grant",
            "total_rows": total_rows,
            "new_students": new_students_count,
            "existing_students_matched": matched_students_count,
            "records_inserted": records_inserted,
            "details": details
        }

    def import_fws_file(self, filepath: str) -> Dict[str, Any]:
        """Reads and processes Federal Work Study CSV file."""
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        for enc in encodings:
            try:
                df = pd.read_csv(filepath, encoding=enc)
                df.columns = [str(c).strip() for c in df.columns]
                return self.process_fws_dataframe(df)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode file {filepath} with supported encodings.")

    def import_grant_file(self, filepath: str) -> Dict[str, Any]:
        """Reads and processes Project Grant CSV file."""
        encodings = ["utf-8", "utf-8-sig", "latin1", "cp1252"]
        for enc in encodings:
            try:
                df = pd.read_csv(filepath, encoding=enc)
                df.columns = [str(c).strip() for c in df.columns]
                return self.process_grant_dataframe(df)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Could not decode file {filepath} with supported encodings.")

    def get_database_state(self) -> Dict[str, Any]:
        """Returns all tables and relational counts as a comprehensive structured dictionary from SQLite."""
        with self.get_connection() as conn:
            students_df = pd.read_sql_query(
                "SELECT * FROM students_doing_research ORDER BY student_id ASC",
                conn
            )
            fws_df = pd.read_sql_query(
                "SELECT * FROM fws_funding_students ORDER BY id DESC",
                conn
            )
            grant_df = pd.read_sql_query(
                "SELECT * FROM grant_funding_students ORDER BY id DESC",
                conn
            )

            students = students_df.to_dict(orient="records")
            fws = fws_df.to_dict(orient="records")
            grant = grant_df.to_dict(orient="records")

            total_students = len(students)
            fws_count = sum(1 for s in students if "Federal Work Study" in (s.get("funding_type") or ""))
            grant_count = sum(1 for s in students if any(g in (s.get("funding_type") or "") for g in ["Supply Grant", "Grant"]))
            dual_count = sum(
                1 for s in students
                if "Federal Work Study" in (s.get("funding_type") or "")
                and any(g in (s.get("funding_type") or "") for g in ["Supply Grant", "Grant"])
            )

            return {
                "summary": {
                    "total_students": total_students,
                    "total_fws_records": len(fws),
                    "total_grant_records": len(grant),
                    "students_fws": fws_count,
                    "students_grant": grant_count,
                    "students_dual_funded": dual_count,
                    "db_engine": "SQLite 3 (Embedded)"
                },
                "students_doing_research": students,
                "fws_funding_students": fws,
                "grant_funding_students": grant
            }

    def reset_database(self) -> Dict[str, str]:
        """Resets all 3 tables cleanly in SQLite."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS grant_funding_students;")
            cursor.execute("DROP TABLE IF EXISTS fws_funding_students;")
            cursor.execute("DROP TABLE IF EXISTS students_doing_research;")
            conn.commit()
        self.init_db()
        return {"status": "success", "message": "SQLite database reset successfully."}

    def delete_central_student(self, student_id: str) -> Dict[str, Any]:
        """
        Removes a student from the centralized students_doing_research database.
        With PRAGMA foreign_keys = ON and ON DELETE CASCADE, this automatically
        removes their corresponding entries from fws_funding_students and grant_funding_students.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students_doing_research WHERE student_id = ?", (student_id,))
            student = cursor.fetchone()
            if not student:
                return {"status": "error", "message": f"Student {student_id} not found."}

            cursor.execute("SELECT COUNT(*) as cnt FROM fws_funding_students WHERE student_id = ?", (student_id,))
            fws_count = cursor.fetchone()["cnt"]

            cursor.execute("SELECT COUNT(*) as cnt FROM grant_funding_students WHERE student_id = ?", (student_id,))
            grant_count = cursor.fetchone()["cnt"]

            # Explicitly delete from sub-tables and central table in transaction
            cursor.execute("DELETE FROM fws_funding_students WHERE student_id = ?", (student_id,))
            cursor.execute("DELETE FROM grant_funding_students WHERE student_id = ?", (student_id,))
            cursor.execute("DELETE FROM students_doing_research WHERE student_id = ?", (student_id,))
            conn.commit()

            return {
                "status": "success",
                "action": "delete_student",
                "student_id": student_id,
                "student_name": f"{student['first_name']} {student['last_name']}",
                "removed_fws_records": fws_count,
                "removed_grant_records": grant_count,
                "message": f"Student {student_id} ({student['first_name']} {student['last_name']}) and all linked sub-table records ({fws_count} FWS, {grant_count} Grant) were removed successfully."
            }

    def delete_subtable_record(self, table: str, record_id: int) -> Dict[str, Any]:
        """
        Removes a record from a sub-table (fws_funding_students or grant_funding_students).
        Subsequently updates/removes the funding field from the centralized table:
        - If the student has no more records of this funding type, removes that type from funding_type.
        - If all funding is removed, sets funding_type to 'No active funding'.
        """
        valid_tables = {
            "fws": "fws_funding_students",
            "fws_funding_students": "fws_funding_students",
            "grant": "grant_funding_students",
            "grant_funding_students": "grant_funding_students"
        }
        target_table = valid_tables.get(table.lower().strip())
        if not target_table:
            return {"status": "error", "message": f"Invalid table '{table}'. Must be 'fws' or 'grant'."}

        funding_name = "Federal Work Study" if "fws" in target_table else "Project Supply Grant"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {target_table} WHERE id = ?", (record_id,))
            record = cursor.fetchone()
            if not record:
                return {"status": "error", "message": f"Record #{record_id} not found in {target_table}."}

            student_id = record["student_id"]

            # Delete the sub-table record
            cursor.execute(f"DELETE FROM {target_table} WHERE id = ?", (record_id,))

            # Check if student has remaining records in this sub-table
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {target_table} WHERE student_id = ?", (student_id,))
            remaining_in_this_table = cursor.fetchone()["cnt"]

            # Check other sub-table
            other_table = "grant_funding_students" if target_table == "fws_funding_students" else "fws_funding_students"
            other_funding_name = "Project Supply Grant" if target_table == "fws_funding_students" else "Federal Work Study"
            cursor.execute(f"SELECT COUNT(*) as cnt FROM {other_table} WHERE student_id = ?", (student_id,))
            remaining_in_other_table = cursor.fetchone()["cnt"]

            remaining_sources = []
            if remaining_in_this_table > 0:
                remaining_sources.append(funding_name)
            if remaining_in_other_table > 0:
                remaining_sources.append(other_funding_name)

            new_funding_type = ", ".join(remaining_sources) if remaining_sources else "No active funding"

            cursor.execute(
                "UPDATE students_doing_research SET funding_type = ?, updated_at = CURRENT_TIMESTAMP WHERE student_id = ?",
                (new_funding_type, student_id)
            )
            conn.commit()

            return {
                "status": "success",
                "action": "delete_subtable_record",
                "table": target_table,
                "record_id": record_id,
                "student_id": student_id,
                "removed_funding_source": funding_name,
                "remaining_funding_type": new_funding_type,
                "message": f"Removed record #{record_id} from {target_table}. Student {student_id}'s central funding status updated to '{new_funding_type}'."
            }


def main():
    parser = argparse.ArgumentParser(description="Research Student Funding Data Pipeline (SQLite Embedded Edition)")
    parser.add_argument(
        "--action",
        choices=["import_fws", "import_grant", "import_both", "get_data", "reset", "delete_student", "delete_subtable_record"],
        default="get_data"
    )
    parser.add_argument("--fws", help="Path to Federal Work Study CSV")
    parser.add_argument("--grant", help="Path to Grant CSV")
    parser.add_argument("--db", default=DEFAULT_DB_PATH, help="SQLite database file path")
    parser.add_argument("--student_id", help="Student ID to delete from central table")
    parser.add_argument("--table", help="Sub-table name (fws or grant) for sub-record deletion")
    parser.add_argument("--record_id", type=int, help="Record ID in sub-table to delete")

    args = parser.parse_args()
    pipeline = ResearchFundingPipeline(db_path=args.db)

    if args.action == "import_fws":
        if not args.fws:
            print(json.dumps({"error": "Missing --fws argument"}))
            sys.exit(1)
        res = pipeline.import_fws_file(args.fws)
        print(json.dumps(res, indent=2))

    elif args.action == "import_grant":
        if not args.grant:
            print(json.dumps({"error": "Missing --grant argument"}))
            sys.exit(1)
        res = pipeline.import_grant_file(args.grant)
        print(json.dumps(res, indent=2))

    elif args.action == "import_both":
        results = {}
        if args.fws:
            results["fws"] = pipeline.import_fws_file(args.fws)
        if args.grant:
            results["grant"] = pipeline.import_grant_file(args.grant)
        results["database_state"] = pipeline.get_database_state()["summary"]
        print(json.dumps(results, indent=2))

    elif args.action == "reset":
        res = pipeline.reset_database()
        print(json.dumps(res, indent=2))

    elif args.action == "delete_student":
        if not args.student_id:
            print(json.dumps({"error": "Missing --student_id argument"}))
            sys.exit(1)
        res = pipeline.delete_central_student(args.student_id)
        print(json.dumps(res, indent=2))

    elif args.action == "delete_subtable_record":
        if not args.table or args.record_id is None:
            print(json.dumps({"error": "Missing --table or --record_id argument"}))
            sys.exit(1)
        res = pipeline.delete_subtable_record(args.table, args.record_id)
        print(json.dumps(res, indent=2))

    elif args.action == "get_data":
        state = pipeline.get_database_state()
        print(json.dumps(state, indent=2, default=str))


if __name__ == "__main__":
    main()
