from flask import Flask, render_template, request, redirect, session, url_for
from werkzeug.security import check_password_hash
import psycopg2
import os

app = Flask(__name__)
app.secret_key = 'collegeeventsecret'

conn = psycopg2.connect(
    dbname="postgres",
    user="postgres.vjtvstmfkzoyauotmqzv",
    password="AkashSH0710.#",
    host="aws-1-ap-south-1.pooler.supabase.com",
    port="5432"
)

cur = conn.cursor()

# LOGIN
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cur.execute("SELECT password, role FROM users WHERE email=%s", (email,))
        user = cur.fetchone()

        if user and check_password_hash(user[0], password):
            session['user'] = email
            session['role'] = user[1]
            return redirect('/dashboard')
        else:
            return "Invalid Login"

    return render_template('login.html')

# DASHBOARD AFTER LOGIN
@app.route('/dashboard')
def dashboard():
    return render_template('add_event.html')

# EVENTS
@app.route('/submit', methods=['POST'])
def submit():
    fest_name = request.form.get('fest_name')
    event_name = request.form['event_name']
    department = request.form['department']
    category = request.form['category']
    event_date = request.form['event_date']
    venue = request.form['venue']
    organizer_name = request.form['organizer_name']

    cur.execute(
    "INSERT INTO events (fest_name, event_name, department, category, event_date, venue, organizer_name) VALUES (%s,%s,%s,%s,%s,%s,%s)",
    (fest_name, event_name, department, category, event_date, venue, organizer_name)
)

    conn.commit()
    return redirect('/events')

@app.route('/events')
def show_events():
    search = request.args.get('search')

    if search:
        cur.execute("SELECT * FROM events WHERE event_name ILIKE %s", ('%' + search + '%',))
    else:
        cur.execute("SELECT * FROM events")

    events = cur.fetchall()
    return render_template('events.html', events=events)

@app.route('/delete/<int:id>')
def delete_event(id):
    cur.execute("DELETE FROM events WHERE event_id = %s", (id,))
    conn.commit()
    return redirect('/events')

@app.route('/edit/<int:id>')
def edit_event(id):
    cur.execute("SELECT * FROM events WHERE event_id = %s", (id,))
    event = cur.fetchone()
    return render_template('edit_event.html', event=event)

@app.route('/update/<int:id>', methods=['POST'])
def update_event(id):
    event_name = request.form['event_name']
    department = request.form['department']
    category = request.form['category']

    cur.execute("""
        UPDATE events
        SET event_name = %s, department = %s, category = %s
        WHERE event_id = %s
    """, (event_name, department, category, id))

    conn.commit()
    return redirect('/events')

# PARTICIPANTS
@app.route('/participant')
def participant():
    return render_template('add_participant.html')

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

@app.route('/participants')
def show_participants():
    cur.execute("SELECT * FROM participants")
    participants = cur.fetchall()
    return render_template('participants.html', participants=participants)

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

@app.route('/results')
def results():
    cur.execute("""
        SELECT r.result_id, e.event_name, p.participant_name, r.rank, r.prize
        FROM results r
        JOIN events e ON r.event_id = e.event_id
        JOIN participants p ON r.participant_id = p.participant_id
    """)
    
    results_data = cur.fetchall()
    return render_template('results.html', results=results_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
