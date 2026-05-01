from flask import Flask, render_template, request, redirect, session, url_for, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
import os
from datetime import date

app = Flask(__name__)
app.secret_key = 'collegeeventsecret'

# DB CONNECTION
conn = psycopg2.connect(
    dbname="postgres",
    user="postgres.vjtvstmfkzoyauotmqzv",
    password="AkashSH0710.#",
    host="aws-1-ap-south-1.pooler.supabase.com",
    port="5432"
)

conn.autocommit = True   # 🔥 VERY IMPORTANT
cur = conn.cursor()

# ---------------- LOGIN ----------------
@app.route('/', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'POST':
            email = request.form['email']
            password = request.form['password']

            cur.execute(
                "SELECT user_id, password, role FROM users WHERE email=%s",
                (email,)
            )
            user = cur.fetchone()

            if not user:
                return "Invalid Login"

            if check_password_hash(user[1], password):
                session['user'] = email
                session['user_id'] = user[0]
                session['role'] = user[2]

                if user[2].strip().lower() == 'coordinator':
                    return redirect('/dashboard')
                else:
                    return redirect('/events')
            else:
                return "Invalid Login"

        return render_template('login.html')

    except Exception as e:
        print("LOGIN ERROR:", e)
        return str(e)


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        roll_no = request.form['roll_no']
        department = request.form['department']
        year = request.form['year']
        ptype = request.form['type']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])

        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        if cur.fetchone():
            return "Email already exists"

        cur.execute("""
            INSERT INTO participants 
            (participant_name, roll_no, department, year_of_study, participant_type)
            VALUES (%s,%s,%s,%s,%s)
        """, (name, roll_no, department, year, ptype))

        cur.execute("""
            INSERT INTO users (email, password, role)
            VALUES (%s,%s,%s)
        """, (email, password, 'participant'))

        return "Account created successfully"

    return render_template('signup.html')


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM participants")
    total_participants = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM results")
    total_results = cur.fetchone()[0]

    return render_template('dashboard.html',
        total_events=total_events,
        total_participants=total_participants,
        total_results=total_results
    )


# ---------------- EVENTS ----------------

@app.route('/events')
def show_events():
    fest = request.args.get('fest')
    today = date.today()

    # Fest cards (keep as it is)
    cur.execute("""
        SELECT 
            e.fest_name,
            COUNT(DISTINCT e.event_id),
            COUNT(DISTINCT pa.participant_id)
        FROM events e
        LEFT JOIN participation pa ON e.event_id = pa.event_id
        GROUP BY e.fest_name
    """)

    raw_fests = cur.fetchall()

    fests = []
    for fest_row in raw_fests:
        fest_name = fest_row[0]
        total_events = fest_row[1]
        total_participants = fest_row[2]
        progress = min(total_participants * 10, 100)

        fests.append((fest_name, total_events, total_participants, progress))

    # 🔥 NEW LOGIC (replace old events query)
    upcoming = []
    ongoing = []
    past = []

    if fest:
        cur.execute("""
            SELECT * FROM events 
            WHERE fest_name=%s AND event_date > %s
        """, (fest, today))
        upcoming = cur.fetchall()

        cur.execute("""
            SELECT * FROM events 
            WHERE fest_name=%s AND event_date = %s
        """, (fest, today))
        ongoing = cur.fetchall()

        cur.execute("""
            SELECT * FROM events 
            WHERE fest_name=%s AND event_date < %s
        """, (fest, today))
        past = cur.fetchall()

    # Registered events (keep same)
    registered_events = []

    if session['role'].strip().lower() == 'participant':
        participant_id = session['user_id']

        cur.execute(
            "SELECT event_id FROM participation WHERE participant_id=%s",
            (participant_id,)
        )

        registered_events = [row[0] for row in cur.fetchall()]

    return render_template(
        'events.html',
        fests=fests,
        selected_fest=fest,
        upcoming=upcoming,
        ongoing=ongoing,
        past=past,
        registered_events=registered_events
    )

@app.route('/add_event')
def add_event():
    cur.execute("SELECT fest_name, COUNT(*) FROM events GROUP BY fest_name")
    fests = cur.fetchall()
    return render_template('add_event.html', fests=fests, selected_fest=None)


@app.route('/delete/<int:id>')
def delete_event(id):
    try:
        cur.execute("DELETE FROM events WHERE event_id = %s", (id,))
        conn.commit()
    except Exception as e:
        print("DELETE ERROR:", e)
    return redirect('/events')


@app.route('/edit/<int:id>')
def edit_event(id):
    cur.execute("SELECT * FROM events WHERE event_id = %s", (id,))
    event = cur.fetchone()

    if not event:
        return "Event not found"

    return render_template('edit_event.html', event=event)


@app.route('/update/<int:id>', methods=['POST'])
def update_event(id):
    try:
        cur.execute("""
            UPDATE events
            SET event_name=%s, department=%s, category=%s
            WHERE event_id=%s
        """, (
            request.form['event_name'],
            request.form['department'],
            request.form['category'],
            id
        ))
        conn.commit()
    except Exception as e:
        print("UPDATE ERROR:", e)

    return redirect('/events')

@app.route('/submit', methods=['POST'])
def submit():
    try:
        cur.execute("""
            INSERT INTO events 
            (fest_name, event_name, department, category, event_date, venue, organizer_name)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            request.form['fest_name'],
            request.form['event_name'],
            request.form['department'],
            request.form['category'],
            request.form['event_date'],
            request.form['venue'],
            request.form['organizer_name']
        ))

        conn.commit()

    except Exception as e:
        print("ERROR:", e)

    return redirect('/events')

@app.route('/participants')
def participants():
    search = request.args.get('search')

    if search:
        cur.execute("""
            SELECT 
                p.participant_id,
                p.participant_name,
                p.roll_no,
                p.department,
                p.year_of_study,
                p.participant_type,
                STRING_AGG(DISTINCT e.fest_name, ', ') AS fest_names,
                STRING_AGG(DISTINCT e.event_name, ', ') AS event_names
            FROM participants p
            LEFT JOIN participation pa ON p.participant_id = pa.participant_id
            LEFT JOIN events e ON pa.event_id = e.event_id
            WHERE 
                p.participant_name ILIKE %s OR
                e.fest_name ILIKE %s OR
                e.event_name ILIKE %s
            GROUP BY 
                p.participant_id,
                p.participant_name,
                p.roll_no,
                p.department,
                p.year_of_study,
                p.participant_type
            ORDER BY p.participant_id
        """, (f'%{search}%', f'%{search}%', f'%{search}%'))

    else:
        cur.execute("""
            SELECT 
                p.participant_id,
                p.participant_name,
                p.roll_no,
                p.department,
                p.year_of_study,
                p.participant_type,
                STRING_AGG(DISTINCT e.fest_name, ', ') AS fest_names,
                STRING_AGG(DISTINCT e.event_name, ', ') AS event_names
            FROM participants p
            LEFT JOIN participation pa ON p.participant_id = pa.participant_id
            LEFT JOIN events e ON pa.event_id = e.event_id
            GROUP BY 
                p.participant_id,
                p.participant_name,
                p.roll_no,
                p.department,
                p.year_of_study,
                p.participant_type
            ORDER BY p.participant_id
        """)

    participants = cur.fetchall()
    return render_template('participants.html', participants=participants)

@app.route('/submit_participant', methods=['POST'])
def submit_participant():
    participant_name = request.form['participant_name']
    roll_no = request.form['roll_no']
    department = request.form['department']
    year_of_study = request.form['year_of_study']
    participant_type = request.form['participant_type']

    conn.rollback()

    cur.execute(
        "INSERT INTO participants (participant_name, roll_no, department, year_of_study, participant_type) VALUES (%s,%s,%s,%s,%s)",
        (participant_name, roll_no, department, year_of_study, participant_type)
    )

    conn.commit()
    return redirect('/participants')

@app.route('/participant')
def add_participant():
    return render_template('add_participant.html')

@app.route('/delete_participant/<int:id>')
def delete_participant(id):
    cur.execute("DELETE FROM participants WHERE participant_id = %s", (id,))
    conn.commit()
    return redirect('/participants')

@app.route('/edit_participant/<int:id>')
def edit_participant(id):
    cur.execute("SELECT * FROM participants WHERE participant_id = %s", (id,))
    participant = cur.fetchone()
    return render_template('edit_participant.html', participant=participant)

@app.route('/update_participant/<int:id>', methods=['POST'])
def update_participant(id):
    participant_name = request.form['participant_name']
    roll_no = request.form['roll_no']
    department = request.form['department']
    year_of_study = request.form['year_of_study']
    participant_type = request.form['participant_type']

    cur.execute("""
        UPDATE participants
        SET participant_name=%s, roll_no=%s, department=%s, year_of_study=%s, participant_type=%s
        WHERE participant_id=%s
    """, (participant_name, roll_no, department, year_of_study, participant_type, id))

    conn.commit()
    return redirect('/participants')

# ANALYTICS
@app.route('/analytics')
def analytics():
    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM participants")
    total_participants = cur.fetchone()[0]

    cur.execute("SELECT department, COUNT(*) FROM events GROUP BY department")
    event_data = cur.fetchall()

    cur.execute("SELECT department, COUNT(*) FROM participants GROUP BY department")
    participant_dept_data = cur.fetchall()

    cur.execute("SELECT participant_type, COUNT(*) FROM participants GROUP BY participant_type")
    participant_type_data = cur.fetchall()

    cur.execute("SELECT category, COUNT(*) FROM events GROUP BY category")
    category_data = cur.fetchall()

    departments = [row[0] for row in event_data]
    event_counts = [row[1] for row in event_data]

    participant_departments = [row[0] for row in participant_dept_data]
    participant_counts = [row[1] for row in participant_dept_data]

    participant_types = [row[0] for row in participant_type_data]
    participant_type_counts = [row[1] for row in participant_type_data]

    categories = [row[0] for row in category_data]
    category_counts = [row[1] for row in category_data]

    return render_template(
        'analytics.html',
        total_events=total_events,
        total_participants=total_participants,
        departments=departments,
        event_counts=event_counts,
        participant_departments=participant_departments,
        participant_counts=participant_counts,
        participant_types=participant_types,
        participant_type_counts=participant_type_counts,
        categories=categories,
        category_counts=category_counts
    )

# ---------------- RESULTS ----------------
@app.route('/results')
def results():
    cur.execute("""
        SELECT r.result_id, e.event_name, p.participant_name, r.rank, r.prize
        FROM results r
        JOIN events e ON r.event_id = e.event_id
        JOIN participants p ON r.participant_id = p.participant_id
    """)
    return render_template('results.html', results=cur.fetchall())


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/register/<int:event_id>')
def register_event(event_id):
    if session['role'].strip().lower() == 'participant':
        participant_id = session['user_id']

        cur.execute(
            "SELECT * FROM participation WHERE event_id=%s AND participant_id=%s",
            (event_id, participant_id)
        )

        existing = cur.fetchone()

        if existing:
            return redirect('/events')

        cur.execute(
            "INSERT INTO participation (event_id, participant_id) VALUES (%s, %s)",
            (event_id, participant_id)
        )
        conn.commit()

    return redirect('/events')

@app.route('/my_events')
def my_events():
    participant_id = session['user_id']

    cur.execute("""
        SELECT e.event_name, e.department, e.category, e.fest_name
        FROM participation pa
        JOIN events e ON pa.event_id = e.event_id
        WHERE pa.participant_id = %s
    """, (participant_id,))

    my_events = cur.fetchall()

    return render_template('my_events.html', my_events=my_events)

@app.route('/add_result')
def add_result():
    try:
        cur.execute("SELECT event_id, event_name FROM events")
        events = cur.fetchall()

        cur.execute("SELECT participant_id, participant_name FROM participants")
        participants = cur.fetchall()

        return render_template('add_result.html', events=events, participants=participants)

    except Exception as e:
        return str(e)

@app.route('/submit_result', methods=['POST'])
def submit_result():
    event_id = request.form['event_id']
    participant_id = request.form['participant_id']
    rank = request.form['rank']
    prize = request.form['prize']

    # 🔒 Check duplicate rank
    cur.execute("""
        SELECT * FROM results 
        WHERE event_id = %s AND rank = %s
    """, (event_id, rank))

    existing = cur.fetchone()

    if existing:
        return redirect('/add_result?error=1')

    # ✅ Insert if no duplicate
    cur.execute("""
        INSERT INTO results (event_id, participant_id, rank, prize)
        VALUES (%s, %s, %s, %s)
    """, (event_id, participant_id, rank, prize))

    conn.commit()

    return redirect('/results?success=1')

@app.route('/get_participants/<int:event_id>')
def get_participants(event_id):
    cur.execute("""
        SELECT p.participant_id, p.participant_name
        FROM participants p
        JOIN participation pa ON p.participant_id = pa.participant_id
        WHERE pa.event_id = %s
    """, (event_id,))
    
    return jsonify(cur.fetchall())

# ---------------- PROFILE ----------------
@app.route('/profile')
def profile():

    user_id = session.get('user_id')

    cur.execute("SELECT COUNT(*) FROM participation WHERE participant_id=%s", (user_id,))
    total_participations = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM results WHERE participant_id=%s", (user_id,))
    total_results = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM events")
    total_events = cur.fetchone()[0]

    return render_template(
        'profile.html',
        total_participations=total_participations,
        total_results=total_results,
        total_events=total_events
    )

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(debug=True)