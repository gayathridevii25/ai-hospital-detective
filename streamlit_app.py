import streamlit as st
import sqlite3, hashlib, secrets
from pathlib import Path

st.set_page_config(page_title="AI Hospital Detective", page_icon="🫀", layout="wide")

DB_PATH = Path("heart_assessment_demo.db")

def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

with get_conn() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS assessments (
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
    )""")

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 150000).hex()

def create_user(username, password):
    salt = secrets.token_hex(16)
    try:
        with get_conn() as c:
            c.execute("INSERT INTO users(username,password_hash,salt) VALUES(?,?,?)",
                      (username, password_hash(password, salt), salt))
        return True
    except sqlite3.IntegrityError:
        return False

def check_user(username, password):
    with get_conn() as c:
        row = c.execute("SELECT id,password_hash,salt FROM users WHERE username=?", (username,)).fetchone()
    if row and secrets.compare_digest(row[1], password_hash(password, row[2])):
        st.session_state.user_id = row[0]
        st.session_state.username = username
        return True
    return False

def fuzzy_membership_low(x, a, b):
    if x <= a: return 1.0
    if x >= b: return 0.0
    return (b-x)/(b-a)

def fuzzy_membership_high(x, a, b):
    if x <= a: return 0.0
    if x >= b: return 1.0
    return (x-a)/(b-a)

def demo_score(age, systolic, heart_rate, symptom_level):
    # Illustrative fuzzy-inspired weighted score. Not a validated medical algorithm.
    age_component = fuzzy_membership_high(age, 35, 75)
    bp_component = fuzzy_membership_high(systolic, 120, 180)
    hr_component = max(fuzzy_membership_high(heart_rate, 100, 150),
                       fuzzy_membership_low(heart_rate, 45, 30))
    symptom_component = symptom_level / 10.0
    score = round(100 * (0.15*age_component + 0.30*bp_component +
                         0.20*hr_component + 0.35*symptom_component))
    return max(0, min(100, score)), {
        "Age input (illustrative)": age_component,
        "Systolic BP input (illustrative)": bp_component,
        "Heart rate input (illustrative)": hr_component,
        "Reported symptom level": symptom_component
    }

if "user_id" not in st.session_state:
    st.session_state.user_id = None

# Custom styling
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#0b1220 0%,#101d33 55%,#102b3a 100%); color:#f4f7fb}
section[data-testid="stSidebar"] {background:#111c2d}
div[data-testid="stMetric"] {background:#16263a;padding:16px;border-radius:14px;border:1px solid #2c4660}
div.stButton>button,div.stFormSubmitButton>button {border-radius:10px;font-weight:700}
.small-note {font-size:0.9rem;color:#b7c5d8}
</style>
""", unsafe_allow_html=True)

st.markdown("# 🫀 AI Hospital Detective")
st.caption("Heart Risk Decision-Support Prototype • Fuzzy Logic • Educational use only")

if not st.session_state.user_id:
    st.markdown("### Welcome")
    st.write("Sign in or create an account to explore a simulated heart-risk assessment workflow.")
    st.warning("Safety: this prototype is not clinically validated, cannot diagnose heart disease, and must not be used for real patient care. Use fictional sample data only.")
    login_tab, signup_tab = st.tabs(["🔐 Login", "✨ Create account"])
    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Login", use_container_width=True)
        if submitted:
            if check_user(username.strip(), password):
                st.rerun()
            else:
                st.error("Login failed. Check your username and password.")
    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Choose username", key="signup_username")
            new_password = st.text_input("Choose password (minimum 8 characters)", type="password", key="signup_password")
            confirm = st.text_input("Confirm password", type="password", key="signup_confirm")
            submitted = st.form_submit_button("Create account", use_container_width=True)
        if submitted:
            if len(new_username.strip()) < 3:
                st.error("Username must have at least 3 characters.")
            elif len(new_password) < 8:
                st.error("Password must have at least 8 characters.")
            elif new_password != confirm:
                st.error("Passwords do not match.")
            elif create_user(new_username.strip(), new_password):
                st.success("Account created. Open the Login tab to sign in.")
            else:
                st.error("That username is already registered.")
    st.stop()

with st.sidebar:
    st.markdown("## 🩺 Menu")
    st.write(f"Signed in as **{st.session_state.username}**")
    page = st.radio("Go to", ["Dashboard", "New Assessment", "Fuzzy Logic Explorer", "Learning Chatbot", "About"])
    st.divider()
    if st.button("Log out", use_container_width=True):
        st.session_state.user_id = None
        st.session_state.username = None
        st.rerun()

if page == "Dashboard":
    st.markdown("## 📊 Dashboard")
    st.write("Your saved **fictional demo assessments**.")
    with get_conn() as c:
        rows = c.execute("""SELECT case_label,age,systolic_bp,heart_rate,symptom_level,score,category,explanation,created_at
                            FROM assessments WHERE user_id=? ORDER BY id DESC""",
                         (st.session_state.user_id,)).fetchall()
    m1, m2 = st.columns(2)
    m1.metric("Saved demo cases", len(rows))
    m2.metric("Purpose", "Learning only")
    if rows:
        for r in rows:
            with st.expander(f"{r[0]} • Demo score {r[5]}/100 • {r[6]}"):
                st.write(f"Age: {r[1]} | Systolic BP: {r[2]} mmHg | Heart rate: {r[3]} bpm")
                st.write(f"Reported symptom level: {r[4]}/10")
                st.write(r[7])
                st.caption(f"Saved at {r[8]}")
    else:
        st.info("No saved cases yet. Choose **New Assessment** from the menu.")

elif page == "New Assessment":
    st.markdown("## 🧾 Simulated Heart-Health Case")
    st.warning("Enter fictional values only. Do not enter real patient identifiers or use this score for clinical decisions.")
    with st.form("assessment_form"):
        label = st.text_input("Fictional case label", placeholder="Example: Case A")
        a, b = st.columns(2)
        age = a.number_input("Age (years)", min_value=1, max_value=110, value=40)
        systolic = b.number_input("Systolic blood pressure (mmHg)", min_value=60, max_value=250, value=120)
        c1, c2 = st.columns(2)
        heart_rate = c1.number_input("Heart rate (beats/min)", min_value=20, max_value=250, value=75)
        symptom = c2.slider("Reported symptom level (demo scale)", 0, 10, 0)
        consent = st.checkbox("I understand this is an educational simulation, not a diagnosis.")
        submit = st.form_submit_button("Run fuzzy demo", use_container_width=True)
    if submit:
        if not label.strip():
            st.error("Please enter a fictional case label.")
        elif not consent:
            st.error("Please confirm the educational-use notice.")
        else:
            score, memberships = demo_score(int(age), int(systolic), int(heart_rate), int(symptom))
            category = "Lower demo score" if score < 30 else ("Middle demo score" if score < 65 else "Higher demo score")
            explanation = ("This score comes from an invented teaching formula combining illustrative membership values. "
                           "It is not a clinically validated risk score and cannot diagnose or rule out heart disease.")
            with get_conn() as c:
                c.execute("""INSERT INTO assessments(user_id,case_label,age,systolic_bp,heart_rate,symptom_level,score,category,explanation)
                             VALUES(?,?,?,?,?,?,?,?,?)""",
                          (st.session_state.user_id,label.strip()[:80],int(age),int(systolic),int(heart_rate),int(symptom),score,category,explanation))
            st.markdown("### Demo output")
            st.metric("Illustrative fuzzy score", f"{score}/100")
            st.info(category)
            st.write(explanation)
            st.markdown("**Illustrative membership values**")
            st.bar_chart(memberships)
            st.success("Saved to your demo dashboard.")
            st.caption("Do not interpret the score as an actual estimate of cardiovascular risk.")

elif page == "Fuzzy Logic Explorer":
    st.markdown("## 🧠 Fuzzy Logic Explorer")
    st.write("Explore example membership values. These shapes are for learning, not clinical thresholds.")
    x = st.slider("Choose an example input value", 0, 100, 50)
    low = max(0.0, min(1.0, (60-x)/60))
    medium = max(0.0, 1-abs(x-50)/35)
    high = max(0.0, min(1.0, (x-40)/60))
    st.write({"Low": round(low,2), "Medium": round(medium,2), "High": round(high,2)})
    st.bar_chart({"Membership degree": {"Low":low, "Medium":medium, "High":high}})
    st.markdown("**Example IF–THEN rule:** IF a teaching input is HIGH, THEN the simulated output may increase.")
    st.caption("This generic illustration is not a medical rule.")

elif page == "Learning Chatbot":
    st.markdown("## 💬 Fuzzy Logic Learning Chatbot")
    question = st.text_input("Ask about fuzzy logic", placeholder="What is a membership function?")
    if st.button("Ask chatbot"):
        q = question.lower()
        if "membership" in q:
            answer = "A membership function maps an input to a degree between 0 and 1 in a fuzzy set such as low, medium, or high."
        elif "rule" in q:
            answer = "A fuzzy rule is an IF–THEN statement. In a real clinical tool, rules must be reviewed by qualified clinicians and validated before use."
        elif "defuzz" in q:
            answer = "Defuzzification converts fuzzy output into a crisp numerical value, often using the centroid method."
        elif "heart" in q or "diagnos" in q or "risk" in q:
            answer = "This project is only a classroom prototype. It cannot diagnose heart disease or estimate real clinical risk. For symptoms or concerns, contact a qualified healthcare professional."
        else:
            answer = "Fuzzy logic represents degrees of membership from 0 to 1 instead of only true/false. Try asking about membership functions, rules, or defuzzification."
        st.chat_message("assistant").write(answer)

else:
    st.markdown("## ℹ️ About the Project")
    st.write("AI Hospital Detective demonstrates fuzzy membership concepts in a simulated heart-health workflow.")
    st.markdown("""
    **Project components**
    - Account creation and login
    - Fictional case entry and saved dashboard
    - Illustrative fuzzy-inspired score
    - Membership-value visualization
    - Rule-based learning chatbot
    """)
    st.error("Clinical safety notice: This is not a medical device, has not been clinically validated, and must not be used to diagnose, triage, or treat real patients.")
    st.write("For real-world clinical use, this would require qualified clinical oversight, representative validated data, rigorous evaluation, security/privacy review, and applicable regulatory approval.")
