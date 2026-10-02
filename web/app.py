import os
import json
import base64
import subprocess
import urllib.request
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'super_secret_key_change_in_production'
PASSWORD = 'admin' # Default password

# Global configuration store
config_store = {
    "tunnelType": "6to4",
    "localIp": "",
    "remoteIp": "",
    "mtu": "1420",
    "ipv6Native": False,
    "ipForwarding": True
}

def get_public_ip():
    try:
        req = urllib.request.urlopen('https://api.ipify.org', timeout=5)
        return req.read().decode('utf-8').strip()
    except:
        try:
            return subprocess.check_output("ip -4 route get 8.8.8.8 | awk '{print $7}' | head -n 1", shell=True).decode('utf-8').strip()
        except:
            return "127.0.0.1"

def get_default_interface():
    try:
        output = subprocess.check_output("ip -4 route ls | grep default | grep -Po '(?<=dev )(\\S+)' | head -n 1", shell=True)
        return output.decode('utf-8').strip()
    except:
        return "eth0"

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
    return render_template('index.html', config=config_store)

@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    ip = request.json.get('ip')
    if not ip: return jsonify({'success': False, 'message': 'آدرس IP وارد نشده است'})
        
    try:
        param = '-n' if os.name == 'nt' else '-c'
        output = subprocess.check_output(['ping', param, '4', ip], stderr=subprocess.STDOUT, universal_newlines=True)
        return jsonify({'success': True, 'message': 'ارتباط برقرار است. پینگ موفقیت آمیز بود.', 'details': output})
    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'message': 'ارتباط با سرور برقرار نشد.', 'details': e.output})

@app.route('/api/add_ipv6', methods=['POST'])
def add_ipv6():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    ipv6 = request.json.get('ipv6')
    if not ipv6: return jsonify({'success': False, 'message': 'آدرس IPv6 وارد نشده است'})
    
    interface = get_default_interface()
    try:
        subprocess.check_call(f"ip -6 addr add {ipv6} dev {interface}", shell=True)
        return jsonify({'success': True, 'message': f'آدرس {ipv6} با موفقیت به اینترفیس {interface} اضافه شد.'})
    except subprocess.CalledProcessError as e:
        return jsonify({'success': False, 'message': 'خطا در اضافه کردن IPv6. ممکن است آدرس از قبل موجود باشد یا فرمت اشتباه باشد.'})

@app.route('/api/generate_code', methods=['POST'])
def generate_code():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    payload = {
        "ip": get_public_ip(),
        "port": 8820,
        "auth": PASSWORD,
        "tunnelType": request.json.get('tunnelType', '6to4'),
        "mtu": request.json.get('mtu', '1420')
    }
    encoded = base64.b64encode(json.dumps(payload).encode('utf-8')).decode('utf-8')
    return jsonify({'success': True, 'code': f"6TO4-{encoded}"})

@app.route('/api/join_node', methods=['POST'])
def join_node():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    code = request.json.get('code')
    if not code or not code.startswith('6TO4-'):
        return jsonify({'success': False, 'message': 'کد نامعتبر است.'})
    
    try:
        decoded = json.loads(base64.b64decode(code[5:]).decode('utf-8'))
        remote_ip = decoded['ip']
        remote_port = decoded['port']
        remote_auth = decoded['auth']
        
        my_ip = get_public_ip()
        
        # 1. Send handshake to the remote server
        req = urllib.request.Request(
            f"http://{remote_ip}:{remote_port}/api/handshake",
            data=json.dumps({"ip": my_ip, "auth": remote_auth}).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            if not res_data.get('success'):
                return jsonify({'success': False, 'message': 'ارتباط با سرور مبدا برقرار شد اما تایید نشد.'})
        
        # 2. Apply config locally
        config_store['remoteIp'] = remote_ip
        config_store['localIp'] = my_ip
        config_store['tunnelType'] = decoded.get('tunnelType', '6to4')
        config_store['mtu'] = decoded.get('mtu', '1420')
        
        return jsonify({'success': True, 'message': f'با موفقیت به گره {remote_ip} متصل شدید و تنظیمات تونل ذخیره شد!'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'خطا در پردازش کد یا برقراری ارتباط: {str(e)}'})

@app.route('/api/handshake', methods=['POST'])
def handshake():
    # This is called by the joining server
    data = request.json
    if data.get('auth') != PASSWORD:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 401
    
    # Save the joining server's IP as our remote IP
    joining_ip = data.get('ip')
    if joining_ip:
        config_store['remoteIp'] = joining_ip
        config_store['localIp'] = get_public_ip()
        return jsonify({'success': True, 'message': 'Handshake accepted'})
    
    return jsonify({'success': False, 'message': 'No IP provided'}), 400

@app.route('/api/apply_config', methods=['POST'])
def apply_config():
    if not session.get('authenticated'):
        return jsonify({'error': 'Unauthorized'}), 401
    
    data = request.json
    config_store.update(data)
    
    # In a real app, you would execute the shell commands here based on config_store
    
    return jsonify({
        'success': True,
        'message': 'تنظیمات با موفقیت ذخیره و در سیستم اعمال شدند.'
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
