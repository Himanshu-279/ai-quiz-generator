import streamlit as st
import pymongo
import pandas as pd
import shortuuid
import time
import hashlib
import json
import os
# Remove: from streamlit_autorefresh import st_autorefresh # ऑटो-रिफ्रेश हटा दिया
import smtplib
from email.mime.text import MIMEText
import logging

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- 1. Page Configuration ---
st.set_page_config(page_title="Quiz Conductor", page_icon="🧠", layout="wide")

# --- Admin Code ---
ADMIN_CODE = "ADMIN123"

# --- 2. API Key Checker ---
IS_API_CONFIGURED = False
GEMINI_API_KEY = None
genai = None
try:
    import google.generativeai as genai_imported
    genai = genai_imported
    if os.environ.get("GOOGLE_API_KEY"):
        GEMINI_API_KEY = os.environ.get("GOOGLE_API_KEY")
        genai.configure(api_key=GEMINI_API_KEY)
        IS_API_CONFIGURED = True
        logging.info("✅ Google (Gemini) API Key found.")
    else:
         logging.warning("⚠️ Gemini API Key not found.")
except ImportError:
    st.warning("`google-generativeai` library not found.")
    IS_API_CONFIGURED = False
except Exception as e:
    st.error(f"🚨 Failed to configure Gemini API: {e}")
    logging.error(f"🚨 Failed to configure Gemini API: {e}", exc_info=True)
    IS_API_CONFIGURED = False

# --- 3. Database Connection ---
@st.cache_resource
def connect_to_db():
    try:
        uri = os.environ.get("MONGO_URI")
        if not uri: st.error("🚨 MONGO_URI missing."); st.stop()
        client = pymongo.MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        logging.info("✅ MongoDB Connected.")
        return client.quiz_app_db
    except Exception as e: st.error(f"🚨 DB Connection Failed: {e}"); logging.error(f"🚨 DB Error: {e}", exc_info=True); st.stop()

db = connect_to_db()
try:
    users_collection = db.users
    quizzes_collection = db.quizzes
    results_collection = db.results
    active_sessions_collection = db.active_sessions
    users_collection.create_index("username", unique=True)
    logging.info("✅ Database collections ready.")
except Exception as e: st.error(f"🚨 DB Collection Error: {e}"); logging.error(f"🚨 DB Collection Error: {e}", exc_info=True); st.stop()

# --- 4. Helper Functions ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if not hashed_text: return False
    return make_hashes(password) == hashed_text

def generate_quiz_with_ai(topic, difficulty, num_questions):
    if not IS_API_CONFIGURED or genai is None: st.error("Gemini API not configured."); return None
    st.info("Generating quiz using Gemini AI... 🧠")
    prompt = f'Generate a multiple-choice quiz about "{topic}" (difficulty: {difficulty}) with exactly {num_questions} questions. Output ONLY a valid JSON list (RFC 8259) of objects. Each object must have keys: "question", "options" (list of 4 strings), "answer".'
    try:
        model = genai.GenerativeModel('gemini-pro-latest')
        response = model.generate_content(prompt, generation_config=genai.types.GenerationConfig(temperature=0.6), safety_settings={'HARASSMENT':'block_none','HATE_SPEECH':'block_none','SEXUAL':'block_none','DANGEROUS':'block_none'})
        if not response.candidates or not response.candidates[0].content.parts: st.error("AI returned no content."); logging.error(f"AI No candidates/parts. Feedback: {response.prompt_feedback}"); return None
        text_response = response.candidates[0].content.parts[0].text.strip().replace("```json", "").replace("```", "").strip()
        if not text_response: st.error("AI returned empty response."); return None
        parsed_json = json.loads(text_response)
        if not isinstance(parsed_json, list): st.error("AI did not return a list."); return None
        logging.info("✅ AI Quiz Generated")
        return parsed_json
    except Exception as e:
        st.error(f"Gemini AI failed: {e}")
        logging.error(f"🚨 Gemini Exception: {e}", exc_info=True)
        return None

def generate_demo_quiz(num_questions):
    st.info("API key issue or AI failed. Generating demo quiz. 📚")
    demo_questions = [{"question": "What is the capital of India?", "options": ["Mumbai", "Kolkata", "Chennai", "New Delhi"], "answer": "New Delhi"}, {"question": "Closest planet to Sun?", "options": ["Earth", "Mars", "Mercury", "Venus"], "answer": "Mercury"}, {"question": "Python list bracket?", "options": ["{}", "()", "[]", "<>"], "answer": "[]"}]
    return demo_questions[:min(num_questions, len(demo_questions))]

def submit_quiz(quiz_id, student_username, user_answers, questions):
    score = sum(1 for i, q in enumerate(questions) if isinstance(q,dict) and user_answers.get(str(i)) == q.get('answer'))
    result_data = {"quizId": quiz_id, "studentUsername": student_username, "score": score, "totalQuestions": len(questions), "submittedAt": time.time()}
    try:
        results_collection.insert_one(result_data)
        st.session_state[f'submitted_{quiz_id}_{student_username}'] = True
        st.session_state[f'final_score_{quiz_id}_{student_username}'] = f"{score}/{len(questions)}"
        logging.info(f"✅ Submitted result for {student_username}")
        active_sessions_collection.delete_one({"quizId": quiz_id, "studentUsername": student_username})
        logging.info(f"✅ Removed active session for {student_username}")
    except Exception as e:
        st.error("Failed to save result/remove session.")
        logging.error(f"🚨 ERROR in submit_quiz DB: {e}", exc_info=True)

def send_quiz_invites(quiz_id, quiz_topic, student_emails):
    sender_email = os.environ.get("SENDER_EMAIL"); sender_password = os.environ.get("SENDER_PASSWORD"); app_base_url = os.environ.get("APP_BASE_URL")
    if not sender_email or not sender_password: st.error("Email credentials missing."); return 0
    if not app_base_url: st.error("APP_BASE_URL missing."); return 0
    quiz_link = f"{app_base_url.strip('/')}?quiz_id={quiz_id}"
    subject = f"Quiz Invitation: {quiz_topic}"
    body_html = f"<html><body><p>Hello,</p><p>Invitation for quiz on '<b>{quiz_topic}</b>'.</p><p>Click link:</p><p><a href=\"{quiz_link}\">Start Quiz</a></p><p>Or copy URL:</p><p>{quiz_link}</p><p>Good luck!</p></body></html>"
    sent_count = 0; failed = []
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465); server.ehlo(); server.login(sender_email, sender_password)
        logging.info("✅ SMTP Connected.")
        for email in student_emails:
            email = email.strip()
            if email and '@' in email:
                msg = MIMEText(body_html, 'html'); msg['Subject'] = subject; msg['From'] = sender_email; msg['To'] = email
                try: server.sendmail(sender_email, [email], msg.as_string()); sent_count += 1; logging.info(f"✉️ Email sent to {email}")
                except Exception as send_e: logging.error(f"🚨 ERROR sending to {email}: {send_e}", exc_info=True); failed.append(email)
        server.close(); logging.info("✅ SMTP Closed.")
    except Exception as e: st.error(f"Email sending failed: {e}"); logging.error(f"🚨 SMTP Error: {e}", exc_info=True); return 0
    if failed: st.warning(f"Could not send to: {', '.join(failed)}")
    return sent_count

# --- 5. Views ---
def student_quiz_view(quiz_id):
    st.title("🧠 Take Quiz")
    if not st.session_state.get('logged_in') or st.session_state.get('role') != 'student': st.warning("Login as student."); st.stop()
    student_username = st.session_state['username']; st.sidebar.success(f"Welcome, {st.session_state['name']} (Student)")
    quiz_data = quizzes_collection.find_one({"quizId": quiz_id});
    if not quiz_data: st.error("Invalid Quiz ID."); return
    submitted_key = f'submitted_{quiz_id}_{student_username}'; score_key = f'final_score_{quiz_id}_{student_username}'
    prev_result = results_collection.find_one({"quizId": quiz_id, "studentUsername": student_username})
    if prev_result: st.success(f"Completed! Score: {prev_result['score']}/{prev_result['totalQuestions']}"); st.balloons(); return
    elif st.session_state.get(submitted_key): st.success(f"Completed! Score: {st.session_state.get(score_key, 'N/A')}"); st.balloons(); return

    started_key = f'quiz_started_{quiz_id}_{student_username}'; start_time_key = f'start_time_{quiz_id}_{student_username}'
    if not st.session_state.get(started_key):
        st.subheader(f"Topic: {quiz_data.get('topic', 'N/A')}")
        st.info(f"Student: {student_username}")
        if st.button("🚀 Start Quiz"):
            st.session_state[started_key] = True; st.session_state[start_time_key] = time.time()
            try:
                logging.info(f"Recording active session for {student_username}")
                active_sessions_collection.update_one({"quizId": quiz_id, "studentUsername": student_username},{"$set": {"startTime": time.time(), "quizId": quiz_id, "studentUsername": student_username}},upsert=True)
            except Exception as e: st.error("Could not record session start."); logging.error(f"🚨 ERROR recording active session: {e}", exc_info=True); return
            st.rerun()
    else: # Quiz in progress
        start_time = st.session_state.get(start_time_key, time.time())
        # ** FIX: Read duration correctly from DB **
        duration_seconds = quiz_data.get('durationInSeconds', 60) # Read the correct key name from DB
        time_left = max(0, duration_seconds - (time.time() - start_time))
        st.markdown(f"### **Time Left: {int(time_left // 60):02d}:{int(time_left % 60):02d}**")

        user_answers = {}; questions = quiz_data.get("questions", [])
        if not isinstance(questions, list): st.error("Quiz data error."); return
        col1, col2 = st.columns(2)
        for i, q in enumerate(questions):
            if isinstance(q, dict) and "question" in q and "options" in q:
                target_col = col1 if i % 2 == 0 else col2
                with target_col:
                    st.markdown(f"**Q {i+1}: {q['question']}**")
                    options = q.get("options", [])
                    if isinstance(options, list) and len(options) == 4:
                         user_answers[str(i)] = st.radio(f"Options Q{i+1}", options, key=f"q_{i}_{quiz_id}", label_visibility="collapsed")
                    else: st.warning(f"Skipping Q{i+1}: Invalid options.")
            else: st.warning(f"Skipping Q{i+1}: Invalid format.")

        if st.button("✅ Submit Quiz"): submit_quiz(quiz_id, student_username, user_answers, questions); st.rerun()
        if time_left <= 0: st.warning("Time's up! Auto-submitting..."); time.sleep(2); submit_quiz(quiz_id, student_username, user_answers, questions); st.rerun()
        # ** FIX: Timer update relies on Streamlit's natural rerun on interaction, remove sleep/rerun loop **
        # else: time.sleep(1); st.rerun() # Removed for stability

# --- 5a. Host Dashboard View ---
def host_dashboard_view():
    if st.session_state.get('role') != 'host': st.error("Access Denied."); st.stop()
    st.sidebar.success(f"Welcome, **{st.session_state['name']}** (Host)!")
    st.sidebar.button("Logout", on_click=lambda: st.session_state.clear())
    st.title("Host Dashboard")

    host_tab, results_tab, invite_tab = st.tabs(["👨‍🏫 Create Quiz", "📊 Live Results", "📧 Invite Students"])

    # --- Create Quiz Tab ---
    with host_tab:
        with st.form("quiz_creation_form"):
            st.header("Create a New Quiz")
            if not IS_API_CONFIGURED: st.caption("Running in Demo Mode")
            topic = st.text_input("Topic", placeholder="e.g., Indian History", disabled=not IS_API_CONFIGURED, key="host_topic")
            difficulty = st.selectbox("Difficulty", ["Easy", "Medium", "Hard"], disabled=not IS_API_CONFIGURED, key="host_difficulty")
            # Number input for questions
            num_questions = st.number_input("Number of Questions", min_value=1, max_value=20, value=5, step=1, key="host_num_q")
            # Minute input for duration
            duration_minutes = st.number_input("Duration (Minutes)", min_value=1, value=5, step=1, key="host_duration_min")
            submitted = st.form_submit_button("🚀 Generate Quiz")

            if submitted:
                duration_seconds = int(duration_minutes * 60) # Convert to seconds
                with st.spinner("Generating quiz..."):
                    generated_topic = topic
                    if IS_API_CONFIGURED and generated_topic:
                        questions = generate_quiz_with_ai(generated_topic, difficulty, int(num_questions))
                        if questions is None: questions = generate_demo_quiz(int(num_questions)); generated_topic = "Demo (AI Failed)"
                    else: questions = generate_demo_quiz(int(num_questions)); generated_topic = "Demo"

                if questions and isinstance(questions, list):
                    try:
                        quiz_id = shortuuid.uuid()[:6]
                        quiz_data = {"quizId": quiz_id, "topic": generated_topic, "durationInSeconds": duration_seconds, "questions": questions, "host": st.session_state["username"]}
                        quizzes_collection.insert_one(quiz_data)
                        share_link = f"{st.get_option('server.baseUrlPath')}?quiz_id={quiz_id}"
                        st.success("Quiz created! Invite students.")
                        st.code(share_link)
                        st.session_state['last_quiz_id'] = quiz_id; st.session_state['last_quiz_topic'] = generated_topic
                    except Exception as e: st.error(f"Error saving quiz: {e}")
                else: st.error("Failed to get valid questions.")

    # --- Live Results Tab ---
    with results_tab:
        st.header("Live Leaderboard & Progress")
        # ** ऑटो-रिफ्रेश हटाया **
        # refresh_count = st_autorefresh(interval=5000, limit=None, key="results_refresh") 

        host_quizzes = list(quizzes_collection.find({"host": st.session_state["username"]}, {"topic": 1, "quizId": 1, "_id": 0}))

        if not host_quizzes: st.info("Create a quiz first.")
        else:
            quiz_options = {f"{q.get('topic', 'N/A')} ({q.get('quizId', 'N/A')})": q.get('quizId', None) for q in host_quizzes}
            quiz_options = {k: v for k, v in quiz_options.items() if v is not None}
            if not quiz_options: st.warning("Cannot read quiz IDs."); return

            selected_quiz_display = st.selectbox("Select quiz to view results:", quiz_options.keys(), key="results_quiz_select")
            if not selected_quiz_display: return
            selected_quiz_id = quiz_options[selected_quiz_display]
            st.caption(f"Showing results for **{selected_quiz_id}**")

            # ** मैनुअल रिफ्रेश बटन वापस लगाया **
            if st.button("🔄 Refresh Results", key="manual_refresh_button"):
                 st.rerun() # Rerun the script to fetch fresh data

            if selected_quiz_id:
                # Active Students
                st.subheader("Students Taking Quiz")
                try:
                    active_students = list(active_sessions_collection.find({"quizId": selected_quiz_id}, {"_id": 0, "studentUsername": 1}))
                    if active_students:
                        active_names = [s.get('studentUsername', 'N/A') for s in active_students]
                        st.info(f"Active Now: **{', '.join(active_names)}**")
                    else: st.info("No students currently taking this quiz.")
                except Exception as e: st.error(f"Could not fetch active students: {e}")
                st.markdown("---")

                # Submitted Results
                st.subheader("Submitted Results")
                try:
                    results = list(results_collection.find({"quizId": selected_quiz_id}, {"_id": 0}))
                    if results:
                        df_results = pd.DataFrame(results).sort_values(by="score", ascending=False).reset_index(drop=True)
                        st.dataframe(df_results, use_container_width=True)
                        st.download_button("Export CSV", df_results.to_csv(index=False).encode('utf-8'), f"results_{selected_quiz_id}.csv")
                        st.subheader("Scores Chart")
                        if 'studentUsername' in df_results.columns and 'score' in df_results.columns:
                            df_chart = df_results[['studentUsername', 'score']].set_index('studentUsername')
                            try: st.bar_chart(df_chart)
                            except Exception as e: st.warning(f"Chart error: {e}")
                        else: st.warning("Cannot create chart, missing columns.")
                    else: st.info("No results submitted yet.")
                except Exception as e: st.error(f"Could not fetch submitted results: {e}")

    # --- Invite Students Tab ---
    with invite_tab:
         st.header("Invite Students via Email")
         host_quizzes_invite = list(quizzes_collection.find({"host": st.session_state["username"]}, {"topic": 1, "quizId": 1, "_id": 0}))
         if not host_quizzes_invite: st.info("Create a quiz first.")
         else:
              quiz_options_invite = {f"{q.get('topic', 'N/A')} ({q.get('quizId', 'N/A')})": q.get('quizId', None) for q in host_quizzes_invite}
              quiz_options_invite = {k: v for k, v in quiz_options_invite.items() if v is not None}
              last_quiz_id = st.session_state.get('last_quiz_id'); default_index = 0
              if last_quiz_id:
                   try: default_index = list(quiz_options_invite.values()).index(last_quiz_id)
                   except ValueError: default_index = 0
              selected_quiz_display_invite = st.selectbox("Select quiz to send invites for:", quiz_options_invite.keys(), index=default_index, key="invite_quiz_select")

              if selected_quiz_display_invite:
                   actual_quiz_id = quiz_options_invite[selected_quiz_display_invite]
                   quiz_topic_invite = selected_quiz_display_invite.split(' (')[0]
                   st.subheader(f"Enter emails for '{quiz_topic_invite}' ({actual_quiz_id})")
                   emails_input = st.text_area("Emails (one per line or comma-separated):", height=150, key="invite_emails")
                   if st.button("✉️ Send Invites", key="invite_send_button"):
                       if not emails_input: st.warning("Please enter emails.")
                       else:
                            emails = [e.strip() for e in emails_input.replace(',', '\n').split('\n') if e.strip() and '@' in e]
                            if not emails: st.warning("No valid emails found.")
                            else:
                                 with st.spinner(f"Sending invites..."):
                                     sent_count = send_quiz_invites(actual_quiz_id, quiz_topic_invite, emails)
                                 if sent_count > 0: st.success(f"Sent {sent_count} invites!")
                                 else: st.error("Failed to send. Check secrets.toml & logs.")

# --- 6. Main Controller ---
quiz_id_from_url = st.query_params.get("quiz_id")

if quiz_id_from_url:
    # Handle direct link access
    if 'logged_in' in st.session_state and st.session_state.get('role') == 'student':
        student_quiz_view(quiz_id_from_url)
    elif 'logged_in' in st.session_state and st.session_state.get('role') == 'host':
         st.warning("Hosts cannot take quizzes."); st.sidebar.button("Logout", key="link_logout", on_click=lambda: st.session_state.clear())
    else: # Not logged in, show student login/register
        st.warning("Please login or register as a student.")
        login_tab, register_tab = st.tabs(["Student Login", "Register Student"])
        with login_tab:
            username = st.text_input("Username", key="student_link_login_user")
            password = st.text_input("Password", type="password", key="student_link_login_pass")
            if st.button("Login as Student", key="student_link_login_button"):
                user = users_collection.find_one({"username": username})
                if user and check_hashes(password, user.get("password")):
                    if user.get("role") == "student":
                        st.success("Logged in!"); time.sleep(1)
                        st.session_state['logged_in'] = True; st.session_state['username'] = user['username']; st.session_state['name'] = user.get('name', username); st.session_state['role'] = 'student'
                        st.rerun()
                    else: st.error("Not a student account.")
                else: st.error("Incorrect username/password")
        with register_tab:
            st.subheader("Create New Student Account")
            new_name = st.text_input("Full Name", key="student_link_reg_name")
            new_username = st.text_input("Username", key="student_link_reg_user")
            new_password = st.text_input("Password", type="password", key="student_link_reg_pass")
            if st.button("Register as Student", key="student_link_reg_button"):
                if not (new_name and new_username and new_password): st.warning("Fill all fields.")
                elif users_collection.find_one({"username": new_username}): st.warning("Username exists.")
                else:
                    try: users_collection.insert_one({"name": new_name, "username": new_username, "password": make_hashes(new_password), "role": "student"}); st.success("Account created! Go to Login.")
                    except Exception as e: st.error(f"Could not create account: {e}")

elif 'logged_in' in st.session_state:
     # Logged in, but not via direct link
     if st.session_state.get('role') == 'host': host_dashboard_view()
     else: st.info("Logged in as student. Use a quiz link."); st.sidebar.button("Logout", key="student_logout", on_click=lambda: st.session_state.clear())

else:
    # --- Default Login/Register Page ---
    st.title("🧠 Quiz Conductor")
    login_tab, register_tab = st.tabs(["Login", "Register"])
    with login_tab:
        username = st.text_input("Username", key="main_login_user")
        password = st.text_input("Password", type="password", key="main_login_pass")
        if st.button("Login", key="main_login_button"):
            user = users_collection.find_one({"username": username})
            if user and check_hashes(password, user.get("password")):
                st.success("Logged in!"); time.sleep(1)
                st.session_state['logged_in'] = True; st.session_state['username'] = user['username']; st.session_state['name'] = user.get('name', username); st.session_state['role'] = user.get('role', 'student')
                st.rerun()
            else: st.error("Incorrect username/password")
    with register_tab:
        st.subheader("Create New Account")
        new_name = st.text_input("Full Name", key="main_reg_name")
        new_username = st.text_input("Username", key="main_reg_user")
        new_password = st.text_input("Password", type="password", key="main_reg_pass")
        selected_role = st.radio("Register as:", ("Student", "Host"), key="main_reg_role", horizontal=True)
        admin_code_input = ""
        if selected_role == "Host": admin_code_input = st.text_input("Admin Code:", type="password", key="main_reg_admin_code")
        if st.button("Register", key="main_reg_button"):
            if not (new_name and new_username and new_password): st.warning("Fill all fields.")
            elif users_collection.find_one({"username": new_username}): st.warning("Username exists.")
            else:
                if selected_role == "Host" and admin_code_input != ADMIN_CODE: st.error("Incorrect Admin Code.")
                else:
                    try: users_collection.insert_one({"name": new_name, "username": new_username, "password": make_hashes(new_password), "role": selected_role.lower()}); st.success(f"Account created as '{selected_role}'! Go to Login.")
                    except Exception as e: st.error(f"Could not create account: {e}")
