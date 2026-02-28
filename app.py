import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
import sqlite3
import bcrypt
import os
from datetime import datetime

# ---------------- CONFIG ----------------
genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
model = genai.GenerativeModel("models/gemini-2.5-flash")

st.set_page_config(page_title="NovaLead AI", layout="wide")

# ---------------- MODERN AI UI STYLE ----------------
st.markdown("""
<style>
.block-container {
    padding-top: 2rem;
    padding-left: 3rem;
    padding-right: 3rem;
}

div[data-testid="metric-container"] {
    background: rgba(17, 24, 39, 0.6);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 20px;
    border: 1px solid rgba(255,255,255,0.05);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
}

.stButton>button {
    background: linear-gradient(90deg, #7C3AED, #06B6D4);
    color: white;
    border-radius: 12px;
    height: 3em;
    border: none;
    font-weight: 600;
    transition: 0.3s;
}

.stButton>button:hover {
    transform: scale(1.03);
    box-shadow: 0 0 15px rgba(124,58,237,0.6);
}

section[data-testid="stSidebar"] {
    background-color: #0F172A;
}
</style>
""", unsafe_allow_html=True)

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password BLOB
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            company TEXT,
            role TEXT,
            industry TEXT,
            score INTEGER,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()

def register_user(username, password):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
              (username, hashed_pw))

    conn.commit()
    conn.close()

def login_user(username, password):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    c.execute("SELECT password FROM users WHERE username=?", (username,))
    result = c.fetchone()

    conn.close()

    if result:
        stored_pw = result[0]
        return bcrypt.checkpw(password.encode(), stored_pw)

    return False

def save_lead(username, company, role, industry, score):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    c.execute("""
        INSERT INTO leads (username, company, role, industry, score, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, company, role, industry, score, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

    conn.commit()
    conn.close()

def get_user_leads(username):
    conn = sqlite3.connect("app.db")
    c = conn.cursor()

    c.execute("""
        SELECT company, role, industry, score, created_at 
        FROM leads WHERE username=?
    """, (username,))

    data = c.fetchall()
    conn.close()
    return data

init_db()

# ---------------- SESSION ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# ---------------- LOGIN ----------------
if not st.session_state.logged_in:

    st.markdown("<h1 style='font-size:48px;'>🚀 NovaLead AI</h1>", unsafe_allow_html=True)
    st.markdown("<p style='color:#9CA3AF;'>AI-Powered B2B Lead Intelligence Platform</p>", unsafe_allow_html=True)

    tab1, tab2 = st.tabs(["Login", "Register"])

    with tab1:
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login"):
            if login_user(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("Invalid credentials")

    with tab2:
        new_user = st.text_input("New Username")
        new_pass = st.text_input("New Password", type="password")

        if st.button("Register"):
            try:
                register_user(new_user, new_pass)
                st.success("Account created. Please login.")
            except:
                st.error("Username already exists.")

    st.stop()

# ---------------- SIDEBAR ----------------
st.sidebar.title("NovaLead AI")
page = st.sidebar.radio("Navigation", ["Dashboard", "Lead Database", "Analytics"])

# ---------------- DASHBOARD ----------------
if page == "Dashboard":

    st.title("📊 AI Sales Dashboard")

    col1, col2, col3 = st.columns(3)
    col1.metric("🔥 Total Leads", "120")
    col2.metric("⭐ High Intent Leads", "38")
    col3.metric("📈 Avg Lead Score", "87")

# ---------------- LEAD DATABASE ----------------
if page == "Lead Database":

    st.title("🔍 AI Lead Discovery")

    industry = st.sidebar.text_input("Industry", "SaaS")
    role = st.sidebar.text_input("Target Role", "CTO")
    region = st.sidebar.text_input("Region", "Global")

    if st.sidebar.button("Generate Leads"):

        prompt = f"""
        Generate 8 realistic {industry} companies operating in {region}.
        Provide only company names separated by commas.
        """

        with st.spinner("Generating AI leads..."):
            response = model.generate_content(prompt)

        companies = response.text.split(",")

        leads = []

        for company in companies:
            score = random.randint(70, 95)
            leads.append({
                "Company": company.strip(),
                "Role": role,
                "Industry": industry,
                "Region": region,
                "Score": score
            })

        df = pd.DataFrame(leads)
        df = df.sort_values(by="Score", ascending=False)

        st.dataframe(df, use_container_width=True)

        selected = st.selectbox("Select Company", df["Company"])

        if selected:

            detail_prompt = f"""
            Company: {selected}
            Industry: {industry}
            Target Role: {role}

            Generate:
            1. Company overview
            2. Decision maker insights
            3. Outreach strategy
            4. Personalized cold email
            """

            with st.spinner("Generating AI report..."):
                detail = model.generate_content(detail_prompt)

            st.markdown("## 📄 AI Intelligence Report")
            st.markdown(detail.text)

            score = int(df[df["Company"] == selected]["Score"].values[0])

            if st.button("💾 Save Lead"):
                save_lead(st.session_state.username, selected, role, industry, score)
                st.success("Lead saved successfully!")

# ---------------- ANALYTICS ----------------
if page == "Analytics":

    st.title("📊 Lead Intelligence Analytics")

    leads = get_user_leads(st.session_state.username)

    if leads:
        df = pd.DataFrame(leads, columns=["Company", "Role", "Industry", "Score", "Created"])

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Lead Score Distribution")
            st.bar_chart(df["Score"])

        with col2:
            st.subheader("Industry Breakdown")
            st.bar_chart(df["Industry"].value_counts())

        st.metric("Average Score", round(df["Score"].mean(), 1))
        st.metric("Total Saved Leads", len(df))

    else:
        st.info("No leads saved yet.")