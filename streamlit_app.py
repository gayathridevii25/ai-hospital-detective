
import streamlit as st
import sqlite3
import hashlib
import secrets
from pathlib import Path

# ==========================================
# PAGE CONFIGURATION
# ==========================================

st.set_page_config(
    page_title="AI Hospital Detective",
    page_icon="🫀",
    layout="wide"
)

DB_PATH = Path("heart_assessment_demo.db")


# ==========================================
# DATABASE
# ==========================================

def get_conn():
    return sqlite3.connect(
        DB_PATH,
        check_same_thread=False
    )


def initialize_database():

    with get_conn() as c:

        c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL
        )
        """)

        c.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            case_label TEXT NOT NULL,
            age INTEGER NOT NULL,
            systolic_bp INTEGER NOT NULL,
            heart_rate INTEGER NOT NULL,
            symptom_level INTEGER NOT NULL,
            score INTEGER NOT NULL,
            category TEXT NOT NULL,
            explanation TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """)


initialize_database()


# ==========================================
# PASSWORD SECURITY
# ==========================================

def password_hash(password, salt):

    return hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        salt.encode(),
        150000
    ).hex()


def create_user(username, password):

    salt = secrets.token_hex(16)

    try:

        with get_conn() as c:

            c.execute(
                """INSERT INTO users
                (username, password_hash, salt)
                VALUES (?, ?, ?)""",
                (
                    username,
                    password_hash(password, salt),
                    salt
                )
            )

        return True

    except sqlite3.IntegrityError:

        return False


def check_user(username, password):

    with get_conn() as c:

        row = c.execute(
            """SELECT id, password_hash, salt
            FROM users WHERE username=?""",
            (username,)
        ).fetchone()

    if row:

        entered_hash = password_hash(
            password,
            row[2]
        )

        if secrets.compare_digest(
            row[1],
            entered_hash
        ):

            st.session_state.user_id = row[0]
            st.session_state.username = username

            return True

    return False


# ==========================================
# FUZZY MEMBERSHIP FUNCTIONS
# ==========================================

def fuzzy_low(x, a, b):

    if x <= a:
        return 1.0

    if x >= b:
        return 0.0

    return (b - x) / (b - a)


def fuzzy_high(x, a, b):

    if x <= a:
        return 0.0

    if x >= b:
        return 1.0

    return (x - a) / (b - a)


def fuzzy_medium(x, a, b, c):

    if x <= a or x >= c:
        return 0.0

    if x == b:
        return 1.0

    if x < b:
        return (x - a) / (b - a)

    return (c - x) / (c - b)


# ==========================================
# FUZZY-INSPIRED SCORE CALCULATION
# ==========================================

def demo_score(age, systolic, heart_rate, symptom):

    age_value = fuzzy_high(
        age, 35, 75
    )

    bp_value = fuzzy_high(
        systolic, 120, 180
    )

    hr_high = fuzzy_high(
        heart_rate, 100, 150
    )

    hr_low = fuzzy_low(
        heart_rate, 30, 45
    )

    hr_value = max(hr_high, hr_low)

    symptom_value = symptom / 10.0

    score = round(
        100 * (
            0.15 * age_value +
            0.30 * bp_value +
            0.20 * hr_value +
            0.35 * symptom_value
        )
    )

    score = max(0, min(100, score))

    memberships = {
        "Age": age_value,
        "Blood Pressure": bp_value,
        "Heart Rate": hr_value,
        "Symptoms": symptom_value
    }

    return score, memberships


# ==========================================
# RISK CATEGORY
# ==========================================

def get_risk_category(score):

    if score <= 30:
        return "Low Risk"

    elif score <= 60:
        return "Moderate Risk"

    else:
        return "High Risk"


# ==========================================
# SESSION STATE
# ==========================================

if "user_id" not in st.session_state:
    st.session_state.user_id = None

if "username" not in st.session_state:
    st.session_state.username = None


# ==========================================
# CUSTOM DESIGN
# ==========================================

st.markdown("""
<style>

.stApp {
    background: linear-gradient(
        135deg,
        #0b1220 0%,
        #101d33 55%,
        #102b3a 100%
    );
    color: #f4f7fb;
}

section[data-testid="stSidebar"] {
    background: #111c2d;
}

div[data-testid="stMetric"] {
    background: #16263a;
    padding: 16px;
    border-radius: 14px;
    border: 1px solid #2c4660;
}

div.stButton > button {
    border-radius: 10px;
    font-weight: 700;
}

div.stFormSubmitButton > button {
    border-radius: 10px;
    font-weight: 700;
}

</style>
""", unsafe_allow_html=True)


# ==========================================
# HEADER
# ==========================================

st.markdown("# 🫀 AI Hospital Detective")

st.caption(
    "Heart Risk Decision-Support Prototype | "
    "Fuzzy Logic"
)


# ==========================================
# LOGIN AND SIGNUP
# ==========================================

if not st.session_state.user_id:

    st.markdown("## Welcome")

    st.write(
        "Sign in or create an account to explore "
        "the heart-health assessment application."
    )

    st.warning(
        "This is an educational simulation. "
        "It is not clinically validated and cannot "
        "diagnose heart disease. Use fictional data only."
    )

    login_tab, signup_tab = st.tabs(
        ["🔐 Login", "✨ Create Account"]
    )

    # LOGIN

    with login_tab:

        with st.form("login_form"):

            username = st.text_input("Username")

            password = st.text_input(
                "Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True
            )

        if submitted:

            if check_user(
                username.strip(),
                password
            ):

                st.success("Login successful!")
                st.rerun()

            else:

                st.error(
                    "Invalid username or password."
                )

    # SIGNUP

    with signup_tab:

        with st.form("signup_form"):

            new_username = st.text_input(
                "Choose Username"
            )

            new_password = st.text_input(
                "Choose Password",
                type="password"
            )

            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )

            submitted = st.form_submit_button(
                "Create Account",
                use_container_width=True
            )

        if submitted:

            if len(new_username.strip()) < 3:

                st.error(
                    "Username must contain at least 3 characters."
                )

            elif len(new_password) < 8:

                st.error(
                    "Password must contain at least 8 characters."
                )

            elif new_password != confirm_password:

                st.error("Passwords do not match.")

            elif create_user(
                new_username.strip(),
                new_password
            ):

                st.success(
                    "Account created! Please login."
                )

            else:

                st.error(
                    "Username already exists."
                )

    st.stop()


# ==========================================
# SIDEBAR
# ==========================================

with st.sidebar:

    st.markdown("## 🩺 Navigation")

    st.write(
        f"Welcome, **{st.session_state.username}**"
    )

    page = st.radio(
        "Select Page",
        [
            "Dashboard",
            "New Assessment",
            "Fuzzy Logic Explorer",
            "Learning Chatbot",
            "About"
        ]
    )

    st.divider()

    if st.button(
        "Logout",
        use_container_width=True
    ):

        st.session_state.user_id = None
        st.session_state.username = None

        st.rerun()


# ==========================================
# DASHBOARD
# ==========================================

if page == "Dashboard":

    st.markdown("## 📊 Dashboard")

    st.write(
        "Overview of saved fictional assessments."
    )

    with get_conn() as c:

        rows = c.execute(
            """
            SELECT case_label, age, systolic_bp,
                   heart_rate, symptom_level,
                   score, category, explanation,
                   created_at
            FROM assessments
            WHERE user_id=?
            ORDER BY id DESC
            """,
            (st.session_state.user_id,)
        ).fetchall()

    total = len(rows)

    low_count = sum(
        1 for r in rows if r[6] == "Low Risk"
    )

    moderate_count = sum(
        1 for r in rows if r[6] == "Moderate Risk"
    )

    high_count = sum(
        1 for r in rows if r[6] == "High Risk"
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Total Cases", total)
    col2.metric("Low Risk", low_count)
    col3.metric("Moderate Risk", moderate_count)
    col4.metric("High Risk", high_count)

    if rows:

        st.markdown("### Assessment History")

        for r in rows:

            with st.expander(
                f"{r[0]} | {r[5]}/100 | {r[6]}"
            ):

                st.write(f"Age: {r[1]} years")

                st.write(
                    f"Systolic BP: {r[2]} mmHg"
                )

                st.write(
                    f"Heart Rate: {r[3]} BPM"
                )

                st.write(
                    f"Symptoms: {r[4]}/10"
                )

                st.metric(
                    "Demo Score",
                    f"{r[5]}/100"
                )

                if r[6] == "Low Risk":
                    st.success(r[6])

                elif r[6] == "Moderate Risk":
                    st.warning(r[6])

                else:
                    st.error(r[6])

                st.write(r[7])

                st.caption(
                    f"Saved at: {r[8]}"
                )

    else:

        st.info(
            "No assessments available. "
            "Go to New Assessment."
        )


# ==========================================
# NEW ASSESSMENT
# ==========================================

elif page == "New Assessment":

    st.markdown("## 🧾 New Heart-Health Assessment")

    st.warning(
        "Enter fictional values only. "
        "This result is not a medical diagnosis."
    )

    with st.form("assessment_form"):

        label = st.text_input(
            "Fictional Case Label",
            placeholder="Example: Case A"
        )

        col1, col2 = st.columns(2)

        age = col1.number_input(
            "Age (Years)",
            min_value=1,
            max_value=110,
            value=40
        )

        systolic = col2.number_input(
            "Systolic Blood Pressure (mmHg)",
            min_value=60,
            max_value=250,
            value=120
        )

        col3, col4 = st.columns(2)

        heart_rate = col3.number_input(
            "Heart Rate (Beats/min)",
            min_value=20,
            max_value=250,
            value=75
        )

        symptom = col4.slider(
            "Reported Symptom Level (Demo Scale)",
            min_value=0,
            max_value=10,
            value=0
        )

        consent = st.checkbox(
            "I understand this is an educational simulation, not a diagnosis."
        )

        submit = st.form_submit_button(
            "🫀 Run Fuzzy Assessment",
            use_container_width=True
        )

    if submit:

        if not label.strip():

            st.error(
                "Please enter a fictional case label."
            )

        elif not consent:

            st.error(
                "Please confirm the educational-use notice."
            )

        else:

            score, memberships = demo_score(
                int(age),
                int(systolic),
                int(heart_rate),
                int(symptom)
            )

            category = get_risk_category(score)

            explanation = (
                "This is an illustrative fuzzy-inspired "
                "score. It is not a clinically validated "
                "risk prediction."
            )

            with get_conn() as c:

                c.execute(
                    """
                    INSERT INTO assessments (
                        user_id,
                        case_label,
                        age,
                        systolic_bp,
                        heart_rate,
                        symptom_level,
                        score,
                        category,
                        explanation
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        st.session_state.user_id,
                        label.strip()[:80],
                        int(age),
                        int(systolic),
                        int(heart_rate),
                        int(symptom),
                        score,
                        category,
                        explanation
                    )
                )

            # RESULT

            st.divider()

            st.markdown(
                "## 🫀 Assessment Result"
            )

            st.metric(
                "Illustrative Risk Score",
                f"{score}/100"
            )

            if category == "Low Risk":

                st.success("🟢 LOW RISK")

            elif category == "Moderate Risk":

                st.warning("🟡 MODERATE RISK")

            else:

                st.error("🔴 HIGH RISK")

            st.subheader(
                f"Category: {category}"
            )

            # Safety flag

            if systolic >= 180 or heart_rate >= 150:

                st.error(
                    "Extreme input value detected. "
                    "If these are real measurements, seek "
                    "immediate medical assessment. "
                    "A low demo score does not establish safety."
                )

            st.write(explanation)

            st.markdown(
                "### 📊 Fuzzy Membership Values"
            )

            st.bar_chart(memberships)

            st.success(
                "Assessment saved successfully!"
            )

            st.caption(
                "This score must not be interpreted "
                "as actual cardiovascular risk."
            )


# ==========================================
# FUZZY LOGIC EXPLORER
# ==========================================

elif page == "Fuzzy Logic Explorer":

    st.markdown("## 🧠 Fuzzy Logic Explorer")

    st.write(
        "Explore Low, Medium and High membership functions."
    )

    x = st.slider(
        "Choose an example input value",
        0,
        100,
        50
    )

    low = fuzzy_low(x, 20, 60)

    medium = fuzzy_medium(
        x, 20, 50, 80
    )

    high = fuzzy_high(x, 40, 80)

    st.write({
        "Low": round(low, 2),
        "Medium": round(medium, 2),
        "High": round(high, 2)
    })

    st.bar_chart({
        "Membership Degree": {
            "Low": low,
            "Medium": medium,
            "High": high
        }
    })

    st.info(
        "Membership values represent the degree "
        "of belonging to a fuzzy set between 0 and 1."
    )


# ==========================================
# LEARNING CHATBOT
# ==========================================

elif page == "Learning Chatbot":

    st.markdown("## 💬 Fuzzy Logic Learning Chatbot")

    question = st.text_input(
        "Ask a question",
        placeholder="What is a membership function?"
    )

    if st.button("Ask Chatbot"):

        q = question.lower()

        if "membership" in q:

            answer = (
                "A membership function maps an input "
                "to a degree between 0 and 1. "
                "It represents fuzzy sets such as "
                "Low, Medium and High."
            )

        elif "rule" in q:

            answer = (
                "A fuzzy rule is an IF-THEN statement. "
                "Example: IF temperature is HIGH, "
                "THEN the output is HIGH."
            )

        elif "defuzz" in q:

            answer = (
                "Defuzzification converts a fuzzy output "
                "into a crisp numerical value. "
                "Centroid is a commonly used method."
            )

        elif "heart" in q or "risk" in q:

            answer = (
                "This project demonstrates fuzzy-inspired "
                "heart-risk categorization for learning. "
                "It cannot diagnose heart disease or "
                "estimate actual clinical risk."
            )

        else:

            answer = (
                "Fuzzy Logic handles uncertainty using "
                "degrees of membership between 0 and 1. "
                "Ask about membership functions, "
                "fuzzy rules or defuzzification."
            )

        st.chat_message("assistant").write(answer)


# ==========================================
# ABOUT
# ==========================================

elif page == "About":

    st.markdown("## ℹ️ About AI Hospital Detective")

    st.write(
        "AI Hospital Detective is a fuzzy-logic-inspired "
        "educational heart-health assessment application."
    )

    st.markdown("""
    ### Project Features

    - User Registration and Login
    - SQLite Database
    - Simulated Heart-Health Case Entry
    - Fuzzy Membership Functions
    - Low, Moderate and High Demo Categories
    - Assessment Dashboard
    - Fuzzy Logic Explorer
    - Learning Chatbot

    ### Technologies Used

    - Python
    - Streamlit
    - SQLite
    - Fuzzy Logic Concepts
    - HTML and CSS
    """)

    
