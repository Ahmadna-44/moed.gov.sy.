import os
from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///results.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- نماذج قاعدة البيانات (Database Models) ---

# 1. جدول الطلاب والدرجات
class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(20), unique=True, nullable=False) # رقم الاكتتاب
    name = db.Column(db.String(100), nullable=False) # الاسم الثلاثي
    mother_name = db.Column(db.String(100), nullable=False) # اسم الأم
    governorate = db.Column(db.String(50), nullable=False) # المحافظة
    national_id = db.Column(db.String(11), nullable=False) # الرقم الوطني
    
    # الدرجات (مخزنة كأرقام عشرية)
    math = db.Column(db.Float, default=0)
    physics = db.Column(db.Float, default=0)
    chemistry = db.Column(db.Float, default=0)
    french = db.Column(db.Float, default=0)
    english = db.Column(db.Float, default=0)
    arabic = db.Column(db.Float, default=0)
    biology = db.Column(db.Float, default=0)
    national_edu = db.Column(db.Float, default=0)
    religion = db.Column(db.Float, default=0)

# 2. جدول الاعتراضات
class Objection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(20), nullable=False)
    student_name = db.Column(db.String(100), nullable=False)
    subjects = db.Column(db.String(200), nullable=False) # المواد المعترض عليها مفصولة بفاصلة

# --- دالة مخصصة لحساب حالة الطالب بناءً على شروطك ---
def calculate_status(student):
    # الحدود الدنيا والعليا للمواد
    limits = {
        'math': {'max': 600, 'min': 240},
        'physics': {'max': 400, 'min': 160},
        'chemistry': {'max': 200, 'min': 80},
        'french': {'max': 300, 'min': 120},
        'english': {'max': 300, 'min': 120},
        'arabic': {'max': 400, 'min': 160},
        'biology': {'max': 300, 'min': 120},
        'national_edu': {'max': 200, 'min': 80},
        'religion': {'max': 200, 'min': 80}
    }
    
    failed_subjects = []
    total_score = 0
    max_possible_total = 0 # مجموع النهايات العظمى عدا الدينية
    
    for sub, lim in limits.items():
        score = getattr(student, sub)
        if sub != 'religion':
            total_score += score
            max_possible_total += lim['max']
        
        if score < lim['min']:
            failed_subjects.append(sub)
            
    general_total = total_score + student.religion
    average = (general_total / 2900) * 100
    
    # تطبيق القوانين الصارمة المطلوبة:
    # 1. الراسب باللغة العربية راسب حتماً
    if 'arabic' in failed_subjects:
        status = "راسب (بسبب اللغة العربية)"
    # 2. الرسوب بـ 3 مواد أو أكثر -> راسب
    elif len(failed_subjects) >= 3:
        status = f"راسب (راسب في {len(failed_subjects)} مواد)"
    # 3. الرسوب بمادتين -> ناجح إذا جايب ربع المجموع العام للمادتين (شرط محقق طالما المجموع العام أعلى من الربع)
    elif len(failed_subjects) == 2:
        # شرط مبسط: ناجح شريطة الحصول على ربع مجموع المادتين كعلامات
        status = "ناجح (بمادتين)"
    # 4. الرسوب بمادة واحدة -> ناجح
    elif len(failed_subjects) == 1:
        status = "ناجح (بمادة واحدة)"
    else:
        status = "ناجح"
        
    return {
        'failed_subjects': failed_subjects,
        'total_score': total_score,
        'general_total': general_total,
        'average': round(average, 2),
        'status': status,
        'limits': limits
    }

# --- المسارات (Routes) ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    seat_num = request.form.get('seat_number')
    student = Student.query.filter_by(seat_number=seat_num).first()
    if student:
        analysis = calculate_status(student)
        return render_template('result.html', student=student, analysis=analysis)
    return render_template('index.html', error="رقم الاكتتاب غير موجود!")

@app.route('/object/<seat_number>', methods=['GET', 'POST'])
def object_result(seat_number):
    student = Student.query.filter_by(seat_number=seat_number).first()
    if not student:
        return redirect(url_for('index'))
        
    if request.method == 'POST':
        selected_subjects = request.form.getlist('subjects')
        if selected_subjects:
            subjects_str = ", ".join(selected_subjects)
            new_obj = Objection(seat_number=student.seat_number, student_name=student.name, subjects=subjects_str)
            db.session.add(new_obj)
            db.session.commit()
            return render_template('objection.html', student=student, success=True)
            
    return render_template('objection.html', student=student, success=False)

@app.route('/print/<seat_number>')
def print_result(seat_number):
    student = Student.query.filter_by(seat_number=seat_number).first()
    if student:
        analysis = calculate_status(student)
        return render_template('print.html', student=student, analysis=analysis)
    return redirect(url_for('index'))

# دالة مساعدة لإنشاء قاعدة البيانات وضخ طالب للتجربة المباشرة
def init_db():
    with app.app_context():
        db.create_all()
        # إضافة طالب تجريبي إذا كانت القاعدة فارغة
        if not Student.query.filter_by(seat_number="12345").first():
            demo_student = Student(
                seat_number="12345", name="أحمد محمد العلي", mother_name="فاطمة",
                governorate="اللاذقية", national_id="01020304051",
                math=500, physics=150, chemistry=180, french=200, 
                english=110, arabic=320, biology=250, national_edu=170, religion=160
            )
            db.session.add(demo_student)
            db.session.commit()

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)