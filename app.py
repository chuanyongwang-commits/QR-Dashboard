from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
import os
import json

app = Flask(__name__, static_url_path='', static_folder='.')
CORS(app) # Enable CORS for development convenience

# DB Config
DB_CONFIG = {
    "host": "10.246.97.159",
    "user": "root",
    "password": "root",
    "database": "QREP",
    "port": 3306
}

try:
    connection_pool = pooling.MySQLConnectionPool(pool_name="qr_pool", pool_size=5, **DB_CONFIG)
except Exception as e:
    print(f"Error creating connection pool: {e}")
    # Fallback to single connection if pooling fails
    connection_pool = None

def get_connection():
    if connection_pool:
        return connection_pool.get_connection()
    return mysql.connector.connect(**DB_CONFIG)

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@app.route('/')
def home():
    return send_from_directory('.', 'index.html')

@app.route('/uploads/<path:filename>')
def custom_static(filename):
    return send_from_directory('uploads', filename)

@app.route('/api/upload', methods=['POST'])
def upload_file_api():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
        
    if file:
        os.makedirs('uploads', exist_ok=True)
        filename = file.filename
        filepath = os.path.join('uploads', filename)
        # Handle duplicate filenames securely simply overwriting for now
        file.save(filepath)
        return jsonify({"url": f"/uploads/{filename}"})

# API for Dashboard
@app.route('/api/dashboard')
def dashboard_api():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True) # or use dict_factory manually if not supported
    try:
        # Total
        cursor.execute("SELECT COUNT(*) as cnt FROM qr_cases")
        total = cursor.fetchone()['cnt']
        
        # Status Counts
        cursor.execute("SELECT qr_status, COUNT(*) as cnt FROM qr_cases GROUP BY qr_status")
        status_counts = cursor.fetchall()
        completed = next((x['cnt'] for x in status_counts if x['qr_status'] == 'Completed'), 0)
        failed = next((x['cnt'] for x in status_counts if x['qr_status'] == 'Failed'), 0)
        ongoing = next((x['cnt'] for x in status_counts if x['qr_status'] == 'Ongoing'), 0)
        
        # Avg Duration
        cursor.execute("SELECT AVG(duration) as avg_dur FROM qr_cases WHERE qr_status = 'Completed' AND duration > 0")
        avg_dur = cursor.fetchone()['avg_dur']
        avg_dur = float(avg_dur) if avg_dur else 0
        
        # Area Distribution
        cursor.execute("SELECT trigger_area, COUNT(*) as cnt FROM qr_cases GROUP BY trigger_area")
        area_dist = cursor.fetchall()
        
        # Scope Distribution
        cursor.execute("SELECT scope, COUNT(*) as cnt FROM qr_cases GROUP BY scope")
        scope_dist = cursor.fetchall()
        
        # Recent Cases (Sorted DESC already)
        cursor.execute("SELECT qr_number, title, qr_status, trigger_area, trigger_date, qr_owner FROM qr_cases ORDER BY trigger_date DESC, qr_number DESC LIMIT 10")
        recent = cursor.fetchall()
        for r in recent:
            if r['trigger_date']: r['trigger_date'] = str(r['trigger_date'])

        return jsonify({
            "kpis": {
                "total": total,
                "completed": completed,
                "failed": failed,
                "ongoing": ongoing,
                "completedRate": f"{((completed/total)*100):.1f}" if total > 0 else "0",
                "failedRate": f"{((failed/total)*100):.1f}" if total > 0 else "0",
                "ongoingRate": f"{((ongoing/total)*100):.1f}" if total > 0 else "0",
                "avgDuration": f"{avg_dur:.1f}"
            },
            "areaDistribution": { x['trigger_area'] or 'Unknown': x['cnt'] for x in area_dist },
            "scopeDistribution": { x['scope'] or 'Unknown': x['cnt'] for x in scope_dist },
            "recentCases": recent
        })
    finally:
        cursor.close()
        conn.close()

# API for List
@app.route('/api/cases')
def cases_api():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        search = request.args.get('search', '').strip().lower()
        status = request.args.get('status', '')
        area = request.args.get('area', '')
        scope = request.args.get('scope', '')
        owner = request.args.get('owner', '')
        sort_asc = request.args.get('sortAsc', 'false') == 'true'

        query = "SELECT qr_number, title, qr_status, trigger_area, scope, trigger_date, qr_owner FROM qr_cases WHERE 1=1"
        params = []

        if search:
            query += " AND (LOWER(title) LIKE %s OR LOWER(phenomenon) LIKE %s OR LOWER(action) LIKE %s)"
            search_param = f"%{search}%"
            params.extend([search_param, search_param, search_param])
            
        if status:
            query += " AND qr_status = %s"
            params.append(status)
        if area:
            query += " AND trigger_area = %s"
            params.append(area)
        if scope:
            query += " AND scope = %s"
            params.append(scope)
        if owner:
            query += " AND qr_owner = %s"
            params.append(owner)

        # Dynamic Sort
        sort_by = request.args.get('sortBy', 'qr_number')
        allowed_sorts = ['qr_number', 'title', 'qr_status', 'trigger_area', 'scope', 'trigger_date', 'qr_owner']
        if sort_by not in allowed_sorts:
            sort_by = 'qr_number'

        order_dir = "ASC" if sort_asc else "DESC"
        query += f" ORDER BY {sort_by} {order_dir}"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        for r in rows:
            if r['trigger_date']: r['trigger_date'] = str(r['trigger_date'])

        return jsonify(rows)
    finally:
        cursor.close()
        conn.close()

# Filters Configuration options helper API
@app.route('/api/filters')
def filters_config():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT DISTINCT trigger_area FROM qr_cases WHERE trigger_area IS NOT NULL AND trigger_area != ''")
        areas = [x['trigger_area'] for x in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT scope FROM qr_cases WHERE scope IS NOT NULL AND scope != ''")
        scopes = [x['scope'] for x in cursor.fetchall()]
        
        cursor.execute("SELECT DISTINCT qr_owner FROM qr_cases WHERE qr_owner IS NOT NULL AND qr_owner != ''")
        owners = [x['qr_owner'] for x in cursor.fetchall()]

        return jsonify({ "areas": sorted(areas), "scopes": sorted(scopes), "owners": sorted(owners) })
    finally:
        cursor.close()
        conn.close()

# API for Detail
@app.route('/api/cases/<int:id>')
def detail_api(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT * FROM qr_cases WHERE qr_number = %s", (id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Not Found"}), 404
            
        # Format Dates
        if row['trigger_date']: row['trigger_date'] = str(row['trigger_date'])
        if row['close_date']: row['close_date'] = str(row['close_date'])

        # Fetch Audit History
        cursor.execute("SELECT field_name, old_value, new_value, changed_at FROM qr_history WHERE qr_number = %s ORDER BY changed_at ASC", (id,))
        history = cursor.fetchall()
        for h in history:
             h['changed_at'] = str(h['changed_at'])
        row['history'] = history

        return jsonify(row)
    finally:
        cursor.close()
        conn.close()

# API to Add Case (CREATE)
@app.route('/api/cases', methods=['POST'])
def add_case_api():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        data = request.json
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Auto-generate QR Number
        cursor.execute("SELECT MAX(qr_number) as max_num FROM qr_cases")
        max_num = cursor.fetchone()['max_num'] or 0
        new_qr_number = max_num + 1

        title = data.get('title', 'Untitled')
        trigger_area = data.get('trigger_area', '')
        scope = data.get('scope', '')
        qr_owner = data.get('qr_owner', '')
        trigger_date = data.get('trigger_date') # expects 'YYYY-MM-DD'
        qr_status = data.get('qr_status', 'Ongoing')

        sql = """
        INSERT INTO qr_cases (qr_number, title, qr_status, trigger_area, scope, trigger_date, qr_owner)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(sql, (new_qr_number, title, qr_status, trigger_area, scope, trigger_date, qr_owner))
        conn.commit()

        return jsonify({"message": "Created successfully", "qr_number": new_qr_number}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# API to Update Case (UPDATE)
@app.route('/api/cases/<int:id>', methods=['PUT'])
def update_case_api(id):
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        data = request.json
        if not data:
             return jsonify({"error": "No data provided"}), 400

        # Fetch original configuration setting
        cursor.execute("SELECT * FROM qr_cases WHERE qr_number = %s", (id,))
        current = cursor.fetchone()
        if not current:
             return jsonify({"error": "Case not found"}), 404

        fields = []
        params = []
        
        # All columns except keys
        cursor.execute("DESCRIBE qr_cases")
        columns = [x['Field'] for x in cursor.fetchall()]
        
        for key in data.keys():
             if key in columns and key != 'qr_number':
                  fields.append(f"{key} = %s")
                  params.append(data[key])
                  
                  # Log History Diffs
                  current_val = str(current[key]) if current[key] is not None else ""
                  new_val = str(data[key]) if data[key] is not None else ""
                  if current_val != new_val:
                       cursor.execute("INSERT INTO qr_history (qr_number, field_name, old_value, new_value) VALUES (%s, %s, %s, %s)", (id, key, current_val, new_val))
                  
        if not fields:
             return jsonify({"error": "No valid fields to update"}), 400
             
        params.append(id)
        sql = f"UPDATE qr_cases SET {', '.join(fields)} WHERE qr_number = %s"
        cursor.execute(sql, params)
        conn.commit()

        return jsonify({"message": "Updated successfully"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    # Run on Port 5000 index
    app.run(host='0.0.0.0', port=5000, debug=True)
