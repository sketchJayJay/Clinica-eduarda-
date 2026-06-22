import os, sqlite3, datetime, json
from functools import wraps
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, g, jsonify

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, 'instance', 'clinica.db')

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret')


def db():
    if 'db' not in g:
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exc):
    con = g.pop('db', None)
    if con:
        con.close()


def init_db():
    con = db()
    cur = con.cursor()
    cur.executescript('''
    CREATE TABLE IF NOT EXISTS patients(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      phone TEXT,
      cpf TEXT,
      birthdate TEXT,
      address TEXT,
      notes TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS professionals(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      role TEXT,
      commission_percent REAL DEFAULT 40,
      phone TEXT
    );
    CREATE TABLE IF NOT EXISTS appointments(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER,
      professional_id INTEGER,
      start_at TEXT NOT NULL,
      end_at TEXT,
      service TEXT,
      status TEXT DEFAULT 'Agendado',
      notes TEXT,
      FOREIGN KEY(patient_id) REFERENCES patients(id),
      FOREIGN KEY(professional_id) REFERENCES professionals(id)
    );
    CREATE TABLE IF NOT EXISTS anamnesis(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER,
      answers TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(patient_id) REFERENCES patients(id)
    );
    CREATE TABLE IF NOT EXISTS treatment_plans(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER,
      professional_id INTEGER,
      title TEXT,
      description TEXT,
      total REAL DEFAULT 0,
      status TEXT DEFAULT 'Aberto',
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(patient_id) REFERENCES patients(id),
      FOREIGN KEY(professional_id) REFERENCES professionals(id)
    );
    CREATE TABLE IF NOT EXISTS finance(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER,
      professional_id INTEGER,
      description TEXT NOT NULL,
      type TEXT DEFAULT 'entrada',
      amount REAL NOT NULL,
      due_date TEXT,
      paid_date TEXT,
      status TEXT DEFAULT 'Pendente',
      payment_method TEXT,
      asaas_id TEXT,
      asaas_invoice_url TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(patient_id) REFERENCES patients(id),
      FOREIGN KEY(professional_id) REFERENCES professionals(id)
    );
    CREATE TABLE IF NOT EXISTS orthodontics(
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      patient_id INTEGER,
      professional_id INTEGER,
      maintenance_date TEXT,
      procedure_done TEXT,
      amount REAL DEFAULT 0,
      payment_status TEXT DEFAULT 'Pendente',
      next_maintenance TEXT,
      notes TEXT,
      created_at TEXT DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY(patient_id) REFERENCES patients(id),
      FOREIGN KEY(professional_id) REFERENCES professionals(id)
    );
    ''')
    cur.execute('SELECT COUNT(*) c FROM professionals')
    if cur.fetchone()['c'] == 0:
        cur.executemany('INSERT INTO professionals(name, role, commission_percent) VALUES(?,?,?)', [
            ('Eduarda Imbelloni', 'Clínica Especializada', 40),
            ('Profissional 2', 'Dentista', 40),
        ])
    con.commit()

@app.before_request
def ensure_db():
    init_db()


def rows(query, args=()):
    return db().execute(query, args).fetchall()

def one(query, args=()):
    return db().execute(query, args).fetchone()

@app.context_processor
def inject_globals():
    return dict(
        clinic_name='Eduarda Imbelloni',
        clinic_subtitle='Clínica Especializada',
        today=datetime.date.today().isoformat(),
        whatsapp=os.getenv('CLINIC_WHATSAPP', '5599999999999')
    )

@app.route('/')
def dashboard():
    total_patients = one('SELECT COUNT(*) c FROM patients')['c']
    today = datetime.date.today().isoformat()
    appointments_today = rows('''SELECT a.*, p.name patient, pr.name professional FROM appointments a
      LEFT JOIN patients p ON p.id=a.patient_id LEFT JOIN professionals pr ON pr.id=a.professional_id
      WHERE date(a.start_at)=? ORDER BY a.start_at''', (today,))
    pending = one("SELECT COALESCE(SUM(amount),0) s FROM finance WHERE status='Pendente'")['s']
    received = one("SELECT COALESCE(SUM(amount),0) s FROM finance WHERE status='Pago' AND strftime('%Y-%m', paid_date)=strftime('%Y-%m','now')")['s']
    month_count = one("SELECT COUNT(*) c FROM appointments WHERE strftime('%Y-%m', start_at)=strftime('%Y-%m','now')")['c']
    return render_template('dashboard.html', total_patients=total_patients, appointments_today=appointments_today, pending=pending, received=received, month_count=month_count)

@app.route('/patients', methods=['GET','POST'])
def patients():
    if request.method == 'POST':
        data = request.form
        db().execute('INSERT INTO patients(name, phone, cpf, birthdate, address, notes) VALUES(?,?,?,?,?,?)',
            (data['name'], data.get('phone'), data.get('cpf'), data.get('birthdate'), data.get('address'), data.get('notes')))
        db().commit(); flash('Paciente cadastrado com sucesso.'); return redirect(url_for('patients'))
    q = request.args.get('q','')
    if q:
        pats = rows('SELECT * FROM patients WHERE name LIKE ? OR phone LIKE ? OR cpf LIKE ? ORDER BY name', (f'%{q}%', f'%{q}%', f'%{q}%'))
    else:
        pats = rows('SELECT * FROM patients ORDER BY id DESC LIMIT 80')
    return render_template('patients.html', patients=pats, q=q)

@app.route('/patients/<int:pid>')
def patient_detail(pid):
    p = one('SELECT * FROM patients WHERE id=?', (pid,))
    if not p: flash('Paciente não encontrado.'); return redirect(url_for('patients'))
    appts = rows('SELECT a.*, pr.name professional FROM appointments a LEFT JOIN professionals pr ON pr.id=a.professional_id WHERE patient_id=? ORDER BY start_at DESC', (pid,))
    fins = rows('SELECT * FROM finance WHERE patient_id=? ORDER BY due_date DESC, id DESC', (pid,))
    ortho = rows('SELECT * FROM orthodontics WHERE patient_id=? ORDER BY maintenance_date DESC', (pid,))
    plans = rows('SELECT * FROM treatment_plans WHERE patient_id=? ORDER BY id DESC', (pid,))
    return render_template('patient_detail.html', p=p, appts=appts, fins=fins, ortho=ortho, plans=plans)

@app.route('/agenda', methods=['GET','POST'])
def agenda():
    if request.method == 'POST':
        data = request.form
        db().execute('INSERT INTO appointments(patient_id, professional_id, start_at, end_at, service, status, notes) VALUES(?,?,?,?,?,?,?)',
            (data.get('patient_id') or None, data.get('professional_id') or None, data['start_at'], data.get('end_at'), data.get('service'), data.get('status','Agendado'), data.get('notes')))
        db().commit(); flash('Consulta agendada.'); return redirect(url_for('agenda'))
    date = request.args.get('date', datetime.date.today().isoformat())
    appts = rows('''SELECT a.*, p.name patient, p.phone phone, pr.name professional FROM appointments a
      LEFT JOIN patients p ON p.id=a.patient_id LEFT JOIN professionals pr ON pr.id=a.professional_id
      WHERE date(a.start_at)=? ORDER BY a.start_at''', (date,))
    return render_template('agenda.html', appts=appts, patients=rows('SELECT * FROM patients ORDER BY name'), professionals=rows('SELECT * FROM professionals ORDER BY name'), date=date)

@app.route('/finance', methods=['GET','POST'])
def finance():
    if request.method == 'POST':
        data = request.form
        db().execute('''INSERT INTO finance(patient_id, professional_id, description, type, amount, due_date, paid_date, status, payment_method)
          VALUES(?,?,?,?,?,?,?,?,?)''', (data.get('patient_id') or None, data.get('professional_id') or None, data['description'], data.get('type','entrada'), float(data.get('amount') or 0), data.get('due_date'), data.get('paid_date'), data.get('status','Pendente'), data.get('payment_method')))
        db().commit(); flash('Lançamento salvo.'); return redirect(url_for('finance'))
    status = request.args.get('status','')
    query = '''SELECT f.*, p.name patient, p.phone phone, pr.name professional FROM finance f
      LEFT JOIN patients p ON p.id=f.patient_id LEFT JOIN professionals pr ON pr.id=f.professional_id'''
    args=[]
    if status:
        query += ' WHERE f.status=?'; args.append(status)
    query += ' ORDER BY f.due_date IS NULL, f.due_date DESC, f.id DESC LIMIT 150'
    data = rows(query,args)
    return render_template('finance.html', finance=data, patients=rows('SELECT * FROM patients ORDER BY name'), professionals=rows('SELECT * FROM professionals ORDER BY name'), status=status)

@app.route('/finance/<int:fid>/paid')
def mark_paid(fid):
    db().execute("UPDATE finance SET status='Pago', paid_date=? WHERE id=?", (datetime.date.today().isoformat(), fid)); db().commit(); flash('Pagamento marcado como pago.'); return redirect(url_for('finance'))

@app.route('/asaas/create/<int:fid>')
def asaas_create(fid):
    f = one('SELECT f.*, p.name patient, p.cpf cpf, p.phone phone FROM finance f LEFT JOIN patients p ON p.id=f.patient_id WHERE f.id=?', (fid,))
    if not f: flash('Lançamento não encontrado.'); return redirect(url_for('finance'))
    api_key = os.getenv('ASAAS_API_KEY','').strip()
    env = os.getenv('ASAAS_ENV','sandbox')
    if not api_key:
        flash('Lugar do Asaas já está pronto. Para emitir cobrança real, configure ASAAS_API_KEY nas variáveis do servidor.')
        return redirect(url_for('finance'))
    base = 'https://sandbox.asaas.com/api/v3' if env == 'sandbox' else 'https://www.asaas.com/api/v3'
    headers = {'access_token': api_key, 'content-type': 'application/json'}
    try:
        customer_payload = {'name': f['patient'] or 'Cliente da Clínica', 'cpfCnpj': ''.join(filter(str.isdigit, f['cpf'] or '')) or None, 'mobilePhone': ''.join(filter(str.isdigit, f['phone'] or '')) or None}
        customer_payload = {k:v for k,v in customer_payload.items() if v}
        c = requests.post(base + '/customers', headers=headers, json=customer_payload, timeout=20).json()
        payment_payload = {'customer': c.get('id'), 'billingType': 'BOLETO', 'value': float(f['amount']), 'dueDate': f['due_date'] or datetime.date.today().isoformat(), 'description': f['description']}
        pay = requests.post(base + '/payments', headers=headers, json=payment_payload, timeout=20).json()
        db().execute('UPDATE finance SET asaas_id=?, asaas_invoice_url=? WHERE id=?', (pay.get('id'), pay.get('invoiceUrl') or pay.get('bankSlipUrl'), fid)); db().commit()
        flash('Cobrança enviada ao Asaas. Confira o link no lançamento.')
    except Exception as e:
        flash('Erro ao comunicar com Asaas: ' + str(e))
    return redirect(url_for('finance'))

@app.route('/orthodontics', methods=['GET','POST'])
def orthodontics():
    if request.method == 'POST':
        d=request.form
        db().execute('''INSERT INTO orthodontics(patient_id, professional_id, maintenance_date, procedure_done, amount, payment_status, next_maintenance, notes)
          VALUES(?,?,?,?,?,?,?,?)''', (d.get('patient_id') or None, d.get('professional_id') or None, d.get('maintenance_date'), d.get('procedure_done'), float(d.get('amount') or 0), d.get('payment_status','Pendente'), d.get('next_maintenance'), d.get('notes')))
        if d.get('amount'):
            db().execute('INSERT INTO finance(patient_id, professional_id, description, amount, due_date, status, payment_method) VALUES(?,?,?,?,?,?,?)',
                (d.get('patient_id') or None, d.get('professional_id') or None, 'Manutenção ortodôntica', float(d.get('amount') or 0), d.get('maintenance_date'), 'Pago' if d.get('payment_status')=='Pago' else 'Pendente', d.get('payment_method')))
        db().commit(); flash('Manutenção registrada.'); return redirect(url_for('orthodontics'))
    regs = rows('''SELECT o.*, p.name patient, pr.name professional FROM orthodontics o LEFT JOIN patients p ON p.id=o.patient_id LEFT JOIN professionals pr ON pr.id=o.professional_id ORDER BY o.maintenance_date DESC LIMIT 100''')
    return render_template('orthodontics.html', regs=regs, patients=rows('SELECT * FROM patients ORDER BY name'), professionals=rows('SELECT * FROM professionals ORDER BY name'))

@app.route('/professionals', methods=['GET','POST'])
def professionals():
    if request.method == 'POST':
        d=request.form
        db().execute('INSERT INTO professionals(name, role, commission_percent, phone) VALUES(?,?,?,?)', (d['name'], d.get('role'), float(d.get('commission_percent') or 0), d.get('phone')))
        db().commit(); flash('Profissional cadastrado.'); return redirect(url_for('professionals'))
    profs=rows('SELECT * FROM professionals ORDER BY name')
    reps=rows('''SELECT pr.name, pr.commission_percent, COALESCE(SUM(f.amount),0) gross, COALESCE(SUM(f.amount * pr.commission_percent / 100),0) commission
      FROM professionals pr LEFT JOIN finance f ON f.professional_id=pr.id AND f.status='Pago' AND strftime('%Y-%m', f.paid_date)=strftime('%Y-%m','now') GROUP BY pr.id ORDER BY pr.name''')
    return render_template('professionals.html', professionals=profs, reps=reps)

@app.route('/plans', methods=['GET','POST'])
def plans():
    if request.method == 'POST':
        d=request.form
        db().execute('INSERT INTO treatment_plans(patient_id, professional_id, title, description, total, status) VALUES(?,?,?,?,?,?)', (d.get('patient_id') or None, d.get('professional_id') or None, d.get('title'), d.get('description'), float(d.get('total') or 0), d.get('status','Aberto')))
        db().commit(); flash('Plano salvo.'); return redirect(url_for('plans'))
    plans=rows('''SELECT t.*, p.name patient, pr.name professional FROM treatment_plans t LEFT JOIN patients p ON p.id=t.patient_id LEFT JOIN professionals pr ON pr.id=t.professional_id ORDER BY t.id DESC LIMIT 100''')
    return render_template('plans.html', plans=plans, patients=rows('SELECT * FROM patients ORDER BY name'), professionals=rows('SELECT * FROM professionals ORDER BY name'))

@app.route('/anamnese', methods=['GET','POST'])
def anamnese():
    questions = ['Possui alergias?', 'Faz uso de medicamento?', 'Tem problemas cardíacos?', 'Está gestante?', 'Já teve reação à anestesia?', 'Observações clínicas']
    if request.method == 'POST':
        d=request.form
        answers={q:d.get(q,'') for q in questions}
        db().execute('INSERT INTO anamnesis(patient_id, answers) VALUES(?,?)', (d.get('patient_id'), json.dumps(answers, ensure_ascii=False)))
        db().commit(); flash('Anamnese salva.'); return redirect(url_for('anamnese'))
    items=rows('SELECT a.*, p.name patient FROM anamnesis a LEFT JOIN patients p ON p.id=a.patient_id ORDER BY a.id DESC LIMIT 50')
    return render_template('anamnese.html', questions=questions, patients=rows('SELECT * FROM patients ORDER BY name'), items=items)

@app.route('/print/finance/<int:fid>')
def print_finance(fid):
    f=one('SELECT f.*, p.name patient, p.phone phone FROM finance f LEFT JOIN patients p ON p.id=f.patient_id WHERE f.id=?',(fid,))
    return render_template('print_receipt.html', f=f)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8080)), debug=False)
