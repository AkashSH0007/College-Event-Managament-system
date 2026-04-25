from flask import Flask, render_template, request, redirect
import psycopg2

app = Flask(__name__)

conn = psycopg2.connect(
    dbname="College Events Info",
    user="postgres",
    password="9611280690",
    host="localhost",
    port="5432"
)

cur = conn.cursor()

@app.route('/')
def home():
    
    return render_template('add_event.html')

@app.route('/submit', methods=['POST'])
def submit():
    event_name = request.form['event_name']
    department = request.form['department']
    category = request.form['category']
    event_date = request.form['event_date']
    venue = request.form['venue']
    organizer_name = request.form['organizer_name']

    cur.execute(
        "INSERT INTO events (event_name, department, category, event_date, venue, organizer_name) VALUES (%s,%s,%s,%s,%s,%s)",
        (event_name, department, category, event_date, venue, organizer_name)
    )

    conn.commit()

    return redirect('/events')

@app.route('/events')
def show_events():
    search = request.args.get('search')

    if search:
        cur.execute(
            "SELECT * FROM events WHERE event_name ILIKE %s",
            ('%' + search + '%',)
        )
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

if __name__ == '__main__':
    app.run(debug=True)
