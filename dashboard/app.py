import os
import sqlite3
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="BEIET Admin | Command Center",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Load default env file and keep legacy support for bot.env
load_dotenv(".env")
load_dotenv("bot.env")

# Base URL from env, or default /tmp/ location
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////tmp/beiet_final.db")
if "sqlite+aiosqlite:///" in DATABASE_URL:
    DB_PATH = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
else:
    DB_PATH = "/tmp/beiet_final.db"

LOGO_URL = "dashboard/assets/logo.png"

# --- UTILS & DB ---
@st.cache_resource
def get_connection(path: str):
    if not path or not os.path.exists(path):
        return None
    try:
        return sqlite3.connect(path, check_same_thread=False)
    except Exception as e:
        st.sidebar.error(f"⚠️ Access Error: {e}")
        return None


def check_db_schema(conn) -> bool:
    try:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(conversation_messages)")
        columns = [row[1] for row in cursor.fetchall()]
        return "input_tokens" in columns
    except Exception:
        return False


def style_figure(fig):
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=30, b=20),
        font=dict(family="IBM Plex Sans, sans-serif", color="#0f172a"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#d6dce6",
        linecolor="#64748b",
        tickfont=dict(size=12, color="#0f172a"),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor="#d6dce6",
        linecolor="#64748b",
        tickfont=dict(size=12, color="#0f172a"),
    )
    return fig


# --- STYLING ---
st.markdown(
    """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=IBM+Plex+Sans:wght@400;500;600&display=swap');

  :root {
    --bg-a: #f8fafc;
    --bg-b: #edf2f7;
    --panel: #ffffff;
    --panel-strong: #ffffff;
    --ink: #0b1320;
    --muted: #334155;
    --brand: #0f766e;
    --brand-2: #c2410c;
    --line: rgba(15, 23, 42, 0.24);
    --ok: #0d9488;
    --warn: #ea580c;
  }

  html, body, [data-testid="stAppViewContainer"] {
    background:
      radial-gradient(1200px 500px at 10% -10%, rgba(15, 118, 110, 0.12), transparent 60%),
      radial-gradient(1000px 420px at 100% 0%, rgba(194, 65, 12, 0.10), transparent 55%),
      linear-gradient(160deg, var(--bg-a), var(--bg-b));
    color: var(--ink);
    font-family: "IBM Plex Sans", sans-serif;
  }

  h1, h2, h3, h4, h5, p, label, span {
    color: var(--ink);
  }

  [data-testid="stHeader"] {
    background: rgba(248, 250, 252, 0.92);
    backdrop-filter: blur(8px);
    border-bottom: 1px solid var(--line);
  }

  [data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b2c3a, #0f3a4a 70%, #114556);
    border-right: 1px solid rgba(255, 255, 255, 0.15);
  }

  [data-testid="stSidebar"] * {
    color: #f8fcff !important;
  }

  .brand-block {
    background: rgba(255, 255, 255, 0.10);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 14px;
    padding: 14px 14px 10px;
    margin-bottom: 14px;
  }

  .brand-title {
    font-family: "Space Grotesk", sans-serif;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    margin: 0;
  }

  .brand-subtitle {
    margin: 4px 0 0;
    font-size: 0.8rem;
    opacity: 0.9;
  }

  .status-pill {
    border-radius: 999px;
    padding: 7px 12px;
    font-size: 0.75rem;
    font-weight: 600;
    display: inline-block;
    margin-top: 8px;
  }

  .status-good { background: rgba(13, 148, 136, 0.2); border: 1px solid rgba(13, 148, 136, 0.5); }
  .status-bad { background: rgba(234, 88, 12, 0.2); border: 1px solid rgba(234, 88, 12, 0.5); }

  .hero-title {
    font-family: "Space Grotesk", sans-serif;
    color: var(--ink);
    font-size: clamp(1.6rem, 2.5vw, 2.35rem);
    letter-spacing: -0.02em;
    margin-bottom: 2px;
    animation: fadeUp 420ms ease-out both;
  }

  .hero-sub {
    color: var(--muted);
    font-size: 1.02rem;
    margin-bottom: 12px;
    animation: fadeUp 500ms ease-out both;
  }

  .hero-accent {
    height: 4px;
    width: 130px;
    border-radius: 999px;
    background: linear-gradient(90deg, var(--brand), var(--brand-2));
    margin-bottom: 22px;
  }

  .kpi-card {
    background: linear-gradient(145deg, var(--panel-strong), #f8fafc);
    border: 1.5px solid var(--line);
    border-radius: 16px;
    padding: 16px 16px 14px;
    min-height: 134px;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.08);
    transition: transform 0.24s ease, box-shadow 0.24s ease;
    animation: fadeUp 450ms ease-out both;
  }

  .kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 18px 36px rgba(18, 37, 34, 0.12);
  }

  .kpi-label {
    color: #1e293b;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    font-weight: 700;
  }

  .kpi-value {
    color: var(--ink);
    font-family: "Space Grotesk", sans-serif;
    font-size: clamp(1.75rem, 2.9vw, 2.45rem);
    line-height: 1.08;
    margin-top: 8px;
    font-weight: 700;
  }

  .kpi-delta {
    margin-top: 12px;
    color: #065f46;
    font-size: 0.85rem;
    font-weight: 600;
  }

  .kpi-delta.warn { color: var(--warn); }

  .glass-panel {
    background: #ffffff;
    border: 1.5px solid var(--line);
    border-radius: 16px;
    padding: 12px 14px 8px;
    margin-bottom: 14px;
  }

  .log-meta {
    color: #0b5f8a;
    font-size: 0.77rem;
    font-weight: 700;
    margin-bottom: 6px;
  }

  .log-bubble {
    background: #ffffff;
    border: 1.5px solid var(--line);
    border-radius: 14px;
    padding: 13px 14px;
    color: var(--ink);
    line-height: 1.45;
    margin-bottom: 14px;
  }

  .badge {
    display: inline-flex;
    align-items: center;
    border-radius: 999px;
    padding: 2px 8px;
    font-size: 0.70rem;
    margin-left: 6px;
    background: rgba(15, 118, 110, 0.18);
    border: 1px solid rgba(15, 118, 110, 0.38);
    color: #0f172a;
  }

  [data-testid="stDataFrame"] {
    border: 1.5px solid var(--line);
    border-radius: 12px;
    overflow: hidden;
  }

  @keyframes fadeUp {
    from { opacity: 0; transform: translateY(6px); }
    to { opacity: 1; transform: translateY(0); }
  }

  @media (max-width: 900px) {
    .kpi-card { min-height: 110px; padding: 13px 13px 12px; }
    .hero-sub { font-size: 0.95rem; }
  }
</style>
""",
    unsafe_allow_html=True,
)


# --- SIDEBAR ---
if os.path.exists(LOGO_URL):
    st.sidebar.image(LOGO_URL, width="stretch")

st.sidebar.markdown(
    """
<div class="brand-block">
  <p class="brand-title">BEIET Command Center</p>
  <p class="brand-subtitle">Academic Intelligence + Tutor Operations</p>
</div>
""",
    unsafe_allow_html=True,
)

page = st.sidebar.radio(
    "Navigation",
    ["General Analytics", "Academic Performance", "Operations Hub"],
)

conn = get_connection(DB_PATH)
has_token_metrics = check_db_schema(conn) if conn else False

st.sidebar.markdown("---")
if conn:
    st.sidebar.markdown('<span class="status-pill status-good">● Database Online</span>', unsafe_allow_html=True)
    st.sidebar.caption(f"Linked file: `{os.path.basename(DB_PATH)}`")
    st.sidebar.caption(f"Updated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
else:
    st.sidebar.markdown('<span class="status-pill status-bad">● Database Offline</span>', unsafe_allow_html=True)
    st.sidebar.caption("Check DATABASE_URL or initialize the DB.")


# --- HELPERS ---
def render_header(title: str, subtitle: str):
    st.markdown(f'<div class="hero-title">{title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="hero-sub">{subtitle}</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-accent"></div>', unsafe_allow_html=True)


def kpi_card(label: str, value, delta: str | None = None, warning: bool = False):
    delta_css = "kpi-delta warn" if warning else "kpi-delta"
    delta_html = f'<div class="{delta_css}">{delta}</div>' if delta else ""
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


if not conn:
    render_header("Connectivity Error", "The dashboard cannot read the analytics database.")
    st.warning("Start the bot first (`python -m bot.main`) or verify `DATABASE_URL`.")
    st.stop()


# --- PAGES ---
if page == "General Analytics":
    render_header("Ecosystem Metrics", "Snapshot of adoption, interaction volume, and operational cost.")

    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*) FROM conversation_messages")
    total_msgs = cur.fetchone()[0] or 0

    avg_msgs_per_student = (total_msgs / total_students) if total_students else 0

    cost_val = "$0.0000"
    token_val = "0"
    if has_token_metrics:
        cur.execute("SELECT SUM(cost), (SUM(input_tokens) + SUM(output_tokens)) FROM conversation_messages")
        res = cur.fetchone()
        cost_num = res[0] or 0.0
        tok_num = res[1] or 0
        cost_val = f"${cost_num:.4f}"
        token_val = f"{tok_num:,d}"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        kpi_card("Registered Students", total_students, "Current cohort")
    with k2:
        kpi_card("Total Interactions", total_msgs, "Messages processed")
    with k3:
        kpi_card("Avg Msg / Student", f"{avg_msgs_per_student:.1f}", "Engagement intensity")
    with k4:
        kpi_card("Estimated Cost", cost_val, "Accumulated usage")

    c1, c2 = st.columns([1.55, 1])

    with c1:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("Interaction Trend by Role")

        df_msgs = pd.read_sql("SELECT timestamp, role FROM conversation_messages", conn)
        if not df_msgs.empty:
            df_msgs["timestamp"] = pd.to_datetime(df_msgs["timestamp"])
            df_msgs["date"] = df_msgs["timestamp"].dt.date
            daily = df_msgs.groupby(["date", "role"]).size().reset_index(name="count")

            fig = px.line(
                daily,
                x="date",
                y="count",
                color="role",
                line_shape="spline",
                markers=True,
                color_discrete_map={
                    "user": "#0f766e",
                    "assistant": "#ea580c",
                    "system": "#64748b",
                },
            )
            style_figure(fig)
            fig.update_traces(line=dict(width=3), marker=dict(size=6))
            st.plotly_chart(fig, width="stretch")
        else:
            st.info("No conversation data yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with c2:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("Student Distribution")

        df_students = pd.read_sql(
            "SELECT subject, COUNT(*) as count FROM students GROUP BY subject", conn
        )
        if not df_students.empty:
            fig_pie = px.pie(
                df_students,
                values="count",
                names="subject",
                hole=0.58,
                color="subject",
                color_discrete_sequence=["#0f766e", "#ea580c", "#1d4ed8", "#65a30d"],
            )
            style_figure(fig_pie)
            fig_pie.update_traces(textposition="inside", textinfo="percent+label")
            st.plotly_chart(fig_pie, width="stretch")
        else:
            st.info("No registered students found.")
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "Academic Performance":
    render_header("Outcome Analytics", "Student-level mastery, quiz rhythm, and cost footprint.")

    students_df = pd.read_sql("SELECT id, name, subject, rut FROM students", conn)
    if students_df.empty:
        st.warning("No students registered in the platform yet.")
        st.stop()

    query_input = st.sidebar.text_input("Filter students", "").strip().lower()
    if query_input:
        name_filter = students_df["name"].fillna("").str.lower().str.contains(query_input)
        rut_filter = students_df["rut"].fillna("").astype(str).str.lower().str.contains(query_input)
        students_df = students_df[name_filter | rut_filter]

    if students_df.empty:
        st.info("No students match that filter.")
        st.stop()

    s_list = students_df.apply(lambda x: f"{x['name']} | ID:{x['id']}", axis=1).tolist()
    selected_student = st.selectbox("Select student", s_list)
    sid = int(selected_student.rsplit("ID:", 1)[1])

    cur = conn.cursor()

    cur.execute(
        "SELECT COUNT(*) FROM conversation_messages WHERE student_id = ? AND role = 'user'",
        (sid,),
    )
    user_msgs = cur.fetchone()[0] or 0

    cur.execute("SELECT COUNT(*), AVG(score) FROM quiz_results WHERE student_id = ?", (sid,))
    q_stats = cur.fetchone()
    quiz_count = q_stats[0] or 0
    avg_score = (q_stats[1] or 0) * 100

    cur.execute(
        "SELECT SUM(cost), SUM(input_tokens + output_tokens) FROM conversation_messages WHERE student_id = ?",
        (sid,),
    )
    f_stats = cur.fetchone()
    student_cost = f_stats[0] or 0.0
    student_tokens = f_stats[1] or 0

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        kpi_card("Student Queries", f"{user_msgs}", "Direct prompts")
    with m2:
        kpi_card("Quiz Attempts", f"{quiz_count}", "Recorded in DB")
    with m3:
        kpi_card("Average Score", f"{avg_score:.1f}%", "Quiz performance")
    with m4:
        kpi_card("Usage Cost", f"${student_cost:.4f}", f"{student_tokens:,} tokens")

    left, right = st.columns([1.2, 1])

    with left:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("Learning Outcome Mastery")

        df_lo = pd.read_sql(
            "SELECT lo_code, score, attempts FROM lo_progress WHERE student_id = ?",
            conn,
            params=[sid],
        )
        if not df_lo.empty:
            fig_lo = px.line_polar(
                df_lo,
                r="score",
                theta="lo_code",
                line_close=True,
                color_discrete_sequence=["#0f766e"],
            )
            fig_lo.update_traces(fill="toself")
            style_figure(fig_lo)
            fig_lo.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])))
            st.plotly_chart(fig_lo, width="stretch")

            df_lo_show = df_lo.copy()
            df_lo_show["score_pct"] = (df_lo_show["score"] * 100).round(1)
            st.dataframe(df_lo_show[["lo_code", "score_pct", "attempts"]], width="stretch")
        else:
            st.info("No learning outcome data for this student yet.")
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        st.markdown('<div class="glass-panel">', unsafe_allow_html=True)
        st.subheader("Quiz Performance Timeline")

        df_quizzes = pd.read_sql(
            "SELECT created_at, subject, score, correct_answers, total_questions FROM quiz_results WHERE student_id = ? ORDER BY created_at DESC",
            conn,
            params=[sid],
        )
        if not df_quizzes.empty:
            df_quizzes["created_at"] = pd.to_datetime(df_quizzes["created_at"])
            fig_q = px.scatter(
                df_quizzes,
                x="created_at",
                y="score",
                size="total_questions",
                color="score",
                color_continuous_scale=["#ea580c", "#f59e0b", "#10b981"],
            )
            style_figure(fig_q)
            fig_q.update_yaxes(tickformat=".0%", range=[0, 1])
            st.plotly_chart(fig_q, width="stretch")

            st.markdown("Recent attempts")
            for _, row in df_quizzes.head(5).iterrows():
                st.write(
                    f"• `{row['created_at'].strftime('%Y-%m-%d')}` — **{row['score'] * 100:.0f}%** "
                    f"({row['correct_answers']}/{row['total_questions']})"
                )
        else:
            st.info("No quiz results logged.")
        st.markdown("</div>", unsafe_allow_html=True)

elif page == "Operations Hub":
    render_header("Operations Hub", "Audit trail of tutor interactions, filtered in real time.")

    students_ops_df = pd.read_sql(
        "SELECT id, name FROM students ORDER BY name COLLATE NOCASE",
        conn,
    )
    student_options = {"All students": None}
    for _, row in students_ops_df.iterrows():
        label = f"{row['name']} | ID:{row['id']}"
        student_options[label] = int(row["id"])

    f1, f2, f3, f4 = st.columns([2, 1, 1, 1.4])
    with f1:
        search_content = st.text_input("Search message content", "")
    with f2:
        role_filter = st.selectbox("Role", ["All", "user", "assistant", "system"])
    with f3:
        has_file = st.checkbox("Only attachments")
    with f4:
        selected_student_label = st.selectbox("Student", list(student_options.keys()))
        selected_student_id = student_options[selected_student_label]

    query = (
        "SELECT m.timestamp, s.name as student, m.role, m.content, m.attachment_type, m.cost "
        "FROM conversation_messages m JOIN students s ON m.student_id = s.id"
    )
    conditions = []
    params = []

    if search_content:
        conditions.append("m.content LIKE ?")
        params.append(f"%{search_content}%")
    if role_filter != "All":
        conditions.append("m.role = ?")
        params.append(role_filter)
    if has_file:
        conditions.append("m.has_attachment = 1")
    if selected_student_id is not None:
        conditions.append("m.student_id = ?")
        params.append(selected_student_id)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY m.timestamp DESC LIMIT 50"

    chat_df = pd.read_sql(query, conn, params=params)
    if chat_df.empty:
        st.info("No interactions matched your filters.")
        st.stop()

    st.caption(f"Showing {len(chat_df)} most recent rows")
    for _, row in chat_df.iterrows():
        badge = ""
        if row["attachment_type"]:
            icon = "🖼️" if row["attachment_type"] == "image" else "🎤" if row["attachment_type"] == "voice" else "📎"
            badge = f"<span class='badge'>{icon} {str(row['attachment_type']).upper()}</span>"

        safe_student = str(row["student"]).strip()
        safe_role = str(row["role"]).upper()
        safe_ts = str(row["timestamp"])
        safe_content = str(row["content"])
        safe_cost = float(row["cost"] or 0.0)

        st.markdown(
            f"""
<div class="log-meta">
  {safe_ts} · <strong>{safe_student}</strong> → {safe_role} {badge}
  <span style="float:right; color:#64748b;">Cost: ${safe_cost:.5f}</span>
</div>
<div class="log-bubble">{safe_content}</div>
""",
            unsafe_allow_html=True,
        )
