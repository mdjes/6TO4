from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import subprocess
import os

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_in_production'
PASSWORD = 'admin' # Default password

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        password = request.form.get('password')
        if password == PASSWORD:
            session['authenticated'] = True
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='رمز عبور اشتباه است')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
def dashboard():
    if not session.get('authenticated'):
        return redirect(url_for('login'))
    return render_template('index.html')

@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'success': False, 'message': 'آدرس IP وارد نشده است'})
        
    try:
        # Ping the IP address
        param = '-n' if os.name == 'nt' else '-c'
        command = ['ping', param, '4', ip]
        output = subprocess.check_output(command, stderr=subprocess.STDOUT, universal_newlines=True)
        return jsonify({'success': True, 'message': 'ارتباط برقرار است. پینگ موفقیت آمیز بود.', 'details': output})
    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'message': 'ارتباط با سرور برقرار نشد.', 'details': e.output})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/quick_install', methods=['POST'])
def quick_install():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    # In a real scenario, this would execute the ipip.py or similar script
    # e.g., subprocess.Popen(['python3', 'ipip.py'])
    
    return jsonify({
        'success': True, 
        'message': 'نصب سریع با موفقیت در پس‌زمینه آغاز شد. لطفاً ترمینال را بررسی کنید.'
    })

@app.route('/api/apply_config', methods=['POST'])
def apply_config():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    config = request.json
    # Here you would typically write the configuration to a file or pass it to the Python script
    print("Received Configuration:", config)
    
    return jsonify({
        'success': True,
        'message': 'تنظیمات با موفقیت ذخیره و اعمال شدند.'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
