from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import os
from datetime import datetime
import shutil

app = Flask(__name__)

class ServerManager:
    def __init__(self):
        self.excel_9755 = "9755_records.xlsx"
        self.excel_5520 = "5520_records.xlsx"
        self.backup_dir = "backups"
        
        if not os.path.exists(self.backup_dir):
            os.makedirs(self.backup_dir)
        
        self.init_excel_files()
    
    def init_excel_files(self):
        columns_9755 = ['时间', '姓名', '占用节点', '占用GPU', '是否使用远程桌面', '任务类型', '预计使用时间', '是否完成']
        columns_5520 = ['时间', '姓名', '使用核数', '占用GPU', '是否使用远程桌面', '任务类型', '预计使用时间', '是否完成']
        
        if not os.path.exists(self.excel_9755):
            df = pd.DataFrame(columns=columns_9755)
            df.to_excel(self.excel_9755, index=False)
        
        if not os.path.exists(self.excel_5520):
            df = pd.DataFrame(columns=columns_5520)
            df.to_excel(self.excel_5520, index=False)
    
    def backup_file(self, filename):
        if os.path.exists(filename):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.backup_dir}/{filename.split('.')[0]}_{timestamp}.xlsx"
            shutil.copy2(filename, backup_name)
    
    def add_record_9755(self, data):
        self.backup_file(self.excel_9755)
        df = pd.read_excel(self.excel_9755)
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(self.excel_9755, index=False)
    
    def add_record_5520(self, data):
        self.backup_file(self.excel_5520)
        df = pd.read_excel(self.excel_5520)
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(self.excel_5520, index=False)
    
    def get_records_9755(self):
        if os.path.exists(self.excel_9755):
            df = pd.read_excel(self.excel_9755)
            return df.to_dict('records')
        return []
    
    def get_records_5520(self):
        if os.path.exists(self.excel_5520):
            df = pd.read_excel(self.excel_5520)
            return df.to_dict('records')
        return []
    
    def update_completion_status_9755(self, row_index, status):
        if os.path.exists(self.excel_9755):
            self.backup_file(self.excel_9755)
            df = pd.read_excel(self.excel_9755)
            if 0 <= row_index < len(df):
                df.at[row_index, '是否完成'] = status
                df.to_excel(self.excel_9755, index=False)
                return True
        return False
    
    def update_completion_status_5520(self, row_index, status):
        if os.path.exists(self.excel_5520):
            self.backup_file(self.excel_5520)
            df = pd.read_excel(self.excel_5520)
            if 0 <= row_index < len(df):
                df.at[row_index, '是否完成'] = status
                df.to_excel(self.excel_5520, index=False)
                return True
        return False
    
    def calculate_remaining_resources(self):
        records_9755 = self.get_records_9755()
        records_5520 = self.get_records_5520()
        
        # 9755服务器资源：4个节点(0,1,2,3)，2张GPU(0,1)
        all_nodes_9755 = {0, 1, 2, 3}
        all_gpus_9755 = {0, 1}
        used_nodes_9755 = set()
        used_gpus_9755 = set()
        remote_desktop_9755_count = 0
        
        # 5520+服务器资源：56个核，1张GPU
        cores_5520_total = 56
        gpu_5520_total = 1
        cores_5520_used = 0
        gpu_5520_used = 0
        remote_desktop_5520_count = 0
        
        # 计算9755使用情况（只计算未完成的任务）
        for record in records_9755:
            if pd.isna(record.get('是否完成')) or record.get('是否完成') != 'Yes':
                nodes = record.get('占用节点', '')
                if nodes and str(nodes) != 'nan':
                    node_str = str(nodes).strip()
                    if ',' in node_str:
                        # 多个节点，如 "0,1,2"
                        for node in node_str.split(','):
                            try:
                                node_num = int(node.strip())
                                if 0 <= node_num <= 3:
                                    used_nodes_9755.add(node_num)
                            except ValueError:
                                pass
                    else:
                        # 单个节点
                        try:
                            node_num = int(node_str)
                            if 0 <= node_num <= 3:
                                used_nodes_9755.add(node_num)
                        except ValueError:
                            pass
                
                gpu_usage = record.get('占用GPU', '')
                if gpu_usage and str(gpu_usage) not in ['', 'nan', 'No']:
                    gpu_str = str(gpu_usage).strip()
                    if ',' in gpu_str:
                        # 多个GPU，如 "0,1"
                        for gpu in gpu_str.split(','):
                            try:
                                gpu_num = int(gpu.strip())
                                if 0 <= gpu_num <= 1:
                                    used_gpus_9755.add(gpu_num)
                            except ValueError:
                                pass
                    else:
                        # 单个GPU
                        try:
                            gpu_num = int(gpu_str)
                            if 0 <= gpu_num <= 1:
                                used_gpus_9755.add(gpu_num)
                        except ValueError:
                            # 处理旧数据中的 "Yes" 值
                            if gpu_str == 'Yes':
                                if 0 not in used_gpus_9755:
                                    used_gpus_9755.add(0)
                                elif 1 not in used_gpus_9755:
                                    used_gpus_9755.add(1)
                
                if record.get('是否使用远程桌面') == 'Yes':
                    remote_desktop_9755_count += 1
        
        # 计算5520+使用情况（只计算未完成的任务）
        for record in records_5520:
            if pd.isna(record.get('是否完成')) or record.get('是否完成') != 'Yes':
                cores = record.get('使用核数', '')
                if cores and str(cores) != 'nan':
                    if str(cores).lower() == 'all':
                        cores_5520_used = cores_5520_total
                    else:
                        try:
                            cores_5520_used += int(cores)
                        except:
                            pass
                
                if record.get('占用GPU') == 'Yes':
                    gpu_5520_used += 1
                
                if record.get('是否使用远程桌面') == 'Yes':
                    remote_desktop_5520_count += 1
        
        # 计算9755剩余资源
        remaining_nodes_9755 = all_nodes_9755 - used_nodes_9755
        remaining_gpus_9755 = all_gpus_9755 - used_gpus_9755
        
        return {
            '9755': {
                'nodes_remaining': len(remaining_nodes_9755),
                'nodes_total': len(all_nodes_9755),
                'nodes_used': len(used_nodes_9755),
                'nodes_available': sorted(list(remaining_nodes_9755)),
                'nodes_occupied': sorted(list(used_nodes_9755)),
                'gpu_remaining': len(remaining_gpus_9755),
                'gpu_total': len(all_gpus_9755),
                'gpu_used': len(used_gpus_9755),
                'gpu_available': sorted(list(remaining_gpus_9755)),
                'gpu_occupied': sorted(list(used_gpus_9755)),
                'remote_desktop_used': remote_desktop_9755_count
            },
            '5520': {
                'cores_remaining': max(0, cores_5520_total - cores_5520_used),
                'cores_total': cores_5520_total,
                'cores_used': cores_5520_used,
                'gpu_remaining': max(0, gpu_5520_total - gpu_5520_used),
                'gpu_total': gpu_5520_total,
                'gpu_used': gpu_5520_used,
                'remote_desktop_used': remote_desktop_5520_count
            }
        }

server_manager = ServerManager()

@app.route('/')
def index():
    resources = server_manager.calculate_remaining_resources()
    return render_template('index.html', resources=resources)

@app.route('/9755')
def server_9755():
    records = server_manager.get_records_9755()
    return render_template('9755.html', records=records)

@app.route('/5520')
def server_5520():
    records = server_manager.get_records_5520()
    return render_template('5520.html', records=records)

@app.route('/add_9755', methods=['POST'])
def add_9755():
    data = {
        '时间': request.form['time'],
        '姓名': request.form['name'],
        '占用节点': request.form['nodes'],
        '占用GPU': request.form['gpu'],
        '是否使用远程桌面': request.form['remote'],
        '任务类型': request.form['task_type'],
        '预计使用时间': request.form['estimated_time'],
        '是否完成': request.form.get('completed', '')
    }
    server_manager.add_record_9755(data)
    return redirect(url_for('server_9755'))

@app.route('/add_5520', methods=['POST'])
def add_5520():
    data = {
        '时间': request.form['time'],
        '姓名': request.form['name'],
        '使用核数': request.form['cores'],
        '占用GPU': request.form['gpu'],
        '是否使用远程桌面': request.form['remote'],
        '任务类型': request.form['task_type'],
        '预计使用时间': request.form['estimated_time'],
        '是否完成': request.form.get('completed', '')
    }
    server_manager.add_record_5520(data)
    return redirect(url_for('server_5520'))

@app.route('/api/resources')
def api_resources():
    return jsonify(server_manager.calculate_remaining_resources())

@app.route('/api/update_status_9755/<int:row_index>', methods=['POST'])
def update_status_9755(row_index):
    data = request.get_json()
    status = data.get('status', '')
    if server_manager.update_completion_status_9755(row_index, status):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/update_status_5520/<int:row_index>', methods=['POST'])
def update_status_5520(row_index):
    data = request.get_json()
    status = data.get('status', '')
    if server_manager.update_completion_status_5520(row_index, status):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)