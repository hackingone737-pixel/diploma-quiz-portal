import os
import tempfile
import importlib

fd, path = tempfile.mkstemp(suffix='.db')
os.close(fd)
os.environ['SQLITE_PATH'] = path
os.environ['SECRET_KEY'] = 'test-secret'

import app
app.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
client = app.app.test_client()

r = client.get('/')
assert r.status_code == 200, r.status_code
assert b'Digital Electronics' in r.data

with client.session_transaction() as sess:
    token = sess['csrf_token']

# Teacher login
r = client.post('/login', data={
    'role':'teacher','teacher_user':'admin','teacher_pass':'QuizPortal#2026!SecureKey99','csrf_token':token
}, follow_redirects=False)
assert r.status_code == 302, r.status_code
r = client.get('/teacher')
assert r.status_code == 200, r.status_code

# Test Teacher Access to MCQ Converter Studio Page
r = client.get('/mcq_converter')
assert r.status_code == 200, r.status_code
assert b'Smart Text-to-MCQ' in r.data

# Test API Parse Text
sample_raw = """What is the capital of India?
A) Mumbai
B) Delhi
C) Chennai
D) Hyderabad
Answer: B"""
r = client.post('/api/parse_mcq_text', json={'raw_text': sample_raw})
assert r.status_code == 200, r.status_code
res_json = r.get_json()
assert res_json['status'] == 'success', res_json
assert res_json['count'] == 1
assert res_json['questions'][0]['correct'] == 'B'

# Test DOCX Export
r = client.post('/api/export_mcq_docx', json={'title': 'Test Exam', 'questions': res_json['questions']})
assert r.status_code == 200, r.status_code
assert r.mimetype == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'

# Test Import to Exam
r = client.post('/api/import_converted_mcqs', json={'exam_id': 1, 'subject': 'Test Subject', 'questions': res_json['questions']})
assert r.status_code == 200, r.status_code
imp_json = r.get_json()
assert imp_json['status'] == 'success'
assert imp_json['added'] == 1

# Test Teacher Update Timer Endpoint
r = client.post('/teacher/exams/1/update_timer', data={'duration_minutes': '25', 'csrf_token': token})
assert r.status_code == 302, r.status_code
conn = app.db_conn()
exam_row = conn.execute("SELECT duration_minutes FROM exams WHERE id=1").fetchone()
assert exam_row[0] == 25, exam_row[0]
conn.close()

# Test Live Exam Broadcast Endpoints
r = client.get('/api/exam_status/1')
assert r.status_code == 200, r.status_code
assert r.get_json()['started'] is False

r = client.post('/teacher/exams/1/start_live', data={'csrf_token': token})
assert r.status_code == 302, r.status_code
r = client.get('/api/exam_status/1')
assert r.get_json()['started'] is True

r = client.post('/teacher/exams/1/reset_lobby', data={'csrf_token': token})
assert r.status_code == 302, r.status_code
r = client.get('/api/exam_status/1')
assert r.get_json()['started'] is False

# Test Toggle Answer Review Endpoint
r = client.post('/teacher/exams/1/toggle_review', data={'csrf_token': token})
assert r.status_code == 302, r.status_code
r = client.get('/api/exam_status/1')
assert r.get_json()['allow_review'] is True

r = client.post('/teacher/exams/1/toggle_review', data={'csrf_token': token})
assert r.status_code == 302, r.status_code
r = client.get('/api/exam_status/1')
assert r.get_json()['allow_review'] is False

# Test Student Submission & Answers JSON
conn = app.db_conn()
conn.execute("INSERT INTO submissions(exam_id,student_pin,student_name,score,total_questions,time_taken_seconds,submitted_at,answers_json) VALUES(1,'STU999','Test Student',1,1,120,'2026-09-13T12:00:00Z','{\"1\":\"B\"}')")
conn.commit()
sub_id = conn.execute("SELECT id FROM submissions WHERE student_pin='STU999'").fetchone()[0]
conn.close()

# Test Teacher Submission Review Endpoint (teacher session still active)
r = client.get(f'/teacher/submissions/{sub_id}/review')
assert r.status_code == 200, r.status_code
rev_json = r.get_json()
assert rev_json['status'] == 'success'
assert rev_json['student_pin'] == 'STU999'

# Test Clear Submissions Endpoint
r = client.post('/teacher/exams/1/clear_submissions', data={'csrf_token': token})
assert r.status_code == 302, r.status_code
conn = app.db_conn()
sub_count = conn.execute("SELECT COUNT(*) FROM submissions WHERE exam_id=1").fetchone()[0]
assert sub_count == 0, sub_count
conn.close()

# Test Clear Questions Endpoint
r = client.post('/teacher/exams/1/clear_questions', data={'csrf_token': token})
assert r.status_code == 302, r.status_code
conn = app.db_conn()
q_count = conn.execute("SELECT COUNT(*) FROM questions WHERE exam_id=1").fetchone()[0]
assert q_count == 0, q_count
conn.close()

# Student login & logout check for security
client.get('/logout')
r = client.get('/mcq_converter')
assert r.status_code == 302, r.status_code

os.unlink(path)
print('SMOKE TEST & MCQ CONVERTER TEST PASSED')
