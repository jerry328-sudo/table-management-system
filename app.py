from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import os
from datetime import datetime
import shutil
import time
import threading
from functools import wraps

app = Flask(__name__)

class ServerManager:
    def __init__(self):
        self.excel_9755 = "9755_records.xlsx"
        self.excel_5520 = "5520_records.xlsx"
        self.backup_dir = "backups"
        
        # 缓存相关
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._last_modified = {}
        self._data_cache = {}
        self.cache_timeout = 30  # 30秒缓存
        
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
    
    def _get_file_modified_time(self, filename):
        if os.path.exists(filename):
            return os.path.getmtime(filename)
        return 0
    
    def _is_cache_valid(self, cache_key):
        with self._cache_lock:
            if cache_key not in self._cache:
                return False
            cache_time, _ = self._cache[cache_key]
            return time.time() - cache_time < self.cache_timeout
    
    def _get_cached_data(self, cache_key):
        with self._cache_lock:
            if cache_key in self._cache:
                _, data = self._cache[cache_key]
                return data
        return None
    
    def _set_cache(self, cache_key, data):
        with self._cache_lock:
            self._cache[cache_key] = (time.time(), data)
    
    def _clear_cache(self, pattern=None):
        with self._cache_lock:
            if pattern:
                keys_to_remove = [k for k in self._cache.keys() if pattern in k]
                for key in keys_to_remove:
                    del self._cache[key]
            else:
                self._cache.clear()

    def backup_file(self, filename):
        if os.path.exists(filename):
            # 异步备份以提高性能
            def async_backup():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"{self.backup_dir}/{filename.split('.')[0]}_{timestamp}.xlsx"
                shutil.copy2(filename, backup_name)
            
            backup_thread = threading.Thread(target=async_backup)
            backup_thread.daemon = True
            backup_thread.start()
    
    def add_record_9755(self, data):
        self.backup_file(self.excel_9755)
        df = pd.read_excel(self.excel_9755)
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(self.excel_9755, index=False)
        # 清除相关缓存
        self._clear_cache('9755')
    
    def add_record_5520(self, data):
        self.backup_file(self.excel_5520)
        df = pd.read_excel(self.excel_5520)
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(self.excel_5520, index=False)
        # 清除相关缓存
        self._clear_cache('5520')
    
    def get_records_9755(self):
        cache_key = 'records_9755'
        
        # 检查缓存
        if self._is_cache_valid(cache_key):
            current_modified = self._get_file_modified_time(self.excel_9755)
            if cache_key in self._last_modified and self._last_modified[cache_key] == current_modified:
                cached_data = self._get_cached_data(cache_key)
                if cached_data is not None:
                    return cached_data
        
        # 读取文件并缓存
        if os.path.exists(self.excel_9755):
            df = pd.read_excel(self.excel_9755)
            records = df.to_dict('records')
            self._set_cache(cache_key, records)
            self._last_modified[cache_key] = self._get_file_modified_time(self.excel_9755)
            return records
        return []
    
    def get_records_5520(self):
        cache_key = 'records_5520'
        
        # 检查缓存
        if self._is_cache_valid(cache_key):
            current_modified = self._get_file_modified_time(self.excel_5520)
            if cache_key in self._last_modified and self._last_modified[cache_key] == current_modified:
                cached_data = self._get_cached_data(cache_key)
                if cached_data is not None:
                    return cached_data
        
        # 读取文件并缓存
        if os.path.exists(self.excel_5520):
            df = pd.read_excel(self.excel_5520)
            records = df.to_dict('records')
            self._set_cache(cache_key, records)
            self._last_modified[cache_key] = self._get_file_modified_time(self.excel_5520)
            return records
        return []
    
    def update_completion_status_9755(self, row_index, status):
        if os.path.exists(self.excel_9755):
            self.backup_file(self.excel_9755)
            df = pd.read_excel(self.excel_9755)
            if 0 <= row_index < len(df):
                df.at[row_index, '是否完成'] = status
                df.to_excel(self.excel_9755, index=False)
                # 清除相关缓存
                self._clear_cache('9755')
                return True
        return False
    
    def update_completion_status_5520(self, row_index, status):
        if os.path.exists(self.excel_5520):
            self.backup_file(self.excel_5520)
            df = pd.read_excel(self.excel_5520)
            if 0 <= row_index < len(df):
                df.at[row_index, '是否完成'] = status
                df.to_excel(self.excel_5520, index=False)
                # 清除相关缓存
                self._clear_cache('5520')
                return True
        return False
    
    def calculate_remaining_resources(self):
        cache_key = 'remaining_resources'
        
        # 检查缓存
        if self._is_cache_valid(cache_key):
            cached_data = self._get_cached_data(cache_key)
            if cached_data is not None:
                return cached_data
        
        # 计算资源使用情况
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
                # 优化节点解析
                nodes = record.get('占用节点', '')
                if nodes and str(nodes) not in ('', 'nan'):
                    node_str = str(nodes).strip()
                    try:
                        if ',' in node_str:
                            # 多个节点，如 "0,1,2"
                            for node in node_str.split(','):
                                node_num = int(node.strip())
                                if 0 <= node_num <= 3:
                                    used_nodes_9755.add(node_num)
                        else:
                            # 单个节点
                            node_num = int(node_str)
                            if 0 <= node_num <= 3:
                                used_nodes_9755.add(node_num)
                    except (ValueError, AttributeError):
                        continue
                
                # 优化GPU解析
                gpu_usage = record.get('占用GPU', '')
                if gpu_usage and str(gpu_usage) not in ('', 'nan', 'No'):
                    gpu_str = str(gpu_usage).strip()
                    try:
                        if ',' in gpu_str:
                            # 多个GPU，如 "0,1"
                            for gpu in gpu_str.split(','):
                                gpu_num = int(gpu.strip())
                                if 0 <= gpu_num <= 1:
                                    used_gpus_9755.add(gpu_num)
                        elif gpu_str.isdigit():
                            # 单个GPU
                            gpu_num = int(gpu_str)
                            if 0 <= gpu_num <= 1:
                                used_gpus_9755.add(gpu_num)
                        elif gpu_str == 'Yes':
                            # 处理旧数据中的 "Yes" 值
                            if 0 not in used_gpus_9755:
                                used_gpus_9755.add(0)
                            elif 1 not in used_gpus_9755:
                                used_gpus_9755.add(1)
                    except (ValueError, AttributeError):
                        continue
                
                if record.get('是否使用远程桌面') == 'Yes':
                    remote_desktop_9755_count += 1
        
        # 计算5520+使用情况（只计算未完成的任务）
        for record in records_5520:
            if pd.isna(record.get('是否完成')) or record.get('是否完成') != 'Yes':
                # 优化核数计算
                cores = record.get('使用核数', '')
                if cores and str(cores) not in ('', 'nan'):
                    cores_str = str(cores).strip().lower()
                    if cores_str == 'all':
                        cores_5520_used = cores_5520_total
                    else:
                        try:
                            cores_5520_used += int(cores)
                        except (ValueError, TypeError):
                            continue
                
                if record.get('占用GPU') == 'Yes':
                    gpu_5520_used += 1
                
                if record.get('是否使用远程桌面') == 'Yes':
                    remote_desktop_5520_count += 1
        
        # 计算9755剩余资源
        remaining_nodes_9755 = all_nodes_9755 - used_nodes_9755
        remaining_gpus_9755 = all_gpus_9755 - used_gpus_9755
        
        result = {
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
        
        # 缓存结果
        self._set_cache(cache_key, result)
        return result

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