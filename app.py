from flask import Flask, render_template, request, redirect, url_for, jsonify
import pandas as pd
import os
from datetime import datetime, timedelta
import shutil
import time
import threading
from functools import wraps
import re

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
        
        # 启动定时检查任务
        self._start_periodic_check()
    
    def init_excel_files(self):
        columns_9755 = ['时间', '姓名', '占用节点', '占用GPU', '是否使用远程桌面', '任务类型', '预计使用时间', '实际使用时间', '是否完成']
        columns_5520 = ['时间', '姓名', '使用核数', '占用GPU', '是否使用远程桌面', '任务类型', '预计使用时间', '实际使用时间', '是否完成']
        
        if not os.path.exists(self.excel_9755):
            df = pd.DataFrame(columns=columns_9755)
            df.to_excel(self.excel_9755, index=False)
        else:
            # 检查并添加新列
            self._add_missing_columns(self.excel_9755, columns_9755)
        
        if not os.path.exists(self.excel_5520):
            df = pd.DataFrame(columns=columns_5520)
            df.to_excel(self.excel_5520, index=False)
        else:
            # 检查并添加新列
            self._add_missing_columns(self.excel_5520, columns_5520)
    
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
    
    def _add_missing_columns(self, filename, expected_columns):
        """为现有Excel文件添加缺失的列"""
        df = pd.read_excel(filename)
        current_columns = list(df.columns)
        
        # 检查是否需要添加新列
        missing_columns = [col for col in expected_columns if col not in current_columns]
        
        if missing_columns:
            for col in missing_columns:
                if col == '实际使用时间':
                    # 如果没有实际使用时间列，用预计使用时间填充
                    df[col] = df.get('预计使用时间', '')
                else:
                    df[col] = ''
            
            # 按照期望的列顺序重新排列
            df = df.reindex(columns=expected_columns)
            df.to_excel(filename, index=False)
    
    def _parse_time_duration(self, time_str):
        """解析时间字符串，返回小时数"""
        if not time_str or pd.isna(time_str):
            return 0
        
        time_str = str(time_str).strip().lower()
        
        # 首先检查是否是日期范围格式
        date_range_patterns = [
            r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*[~\-到至]\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})',  # 2025.6.10~2025.6.12
            r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*[~\-到至]\s*(\d{1,2})[.\-/](\d{1,2})',  # 2025.6.10~6.12
        ]
        
        for pattern in date_range_patterns:
            match = re.search(pattern, time_str)
            if match:
                try:
                    groups = match.groups()
                    if len(groups) == 6:  # 完整日期范围
                        start_year, start_month, start_day, end_year, end_month, end_day = groups
                        start_date = datetime(int(start_year), int(start_month), int(start_day))
                        end_date = datetime(int(end_year), int(end_month), int(end_day))
                    else:  # 简化日期范围 (同年)
                        start_year, start_month, start_day, end_month, end_day = groups
                        start_date = datetime(int(start_year), int(start_month), int(start_day))
                        end_date = datetime(int(start_year), int(end_month), int(end_day))
                    
                    # 计算天数差异并转换为小时
                    delta = end_date - start_date
                    return max(delta.days * 24, 24)  # 至少1天(24小时)
                except (ValueError, TypeError):
                    continue
        
        # 匹配单一日期格式 (默认为1天)
        single_date_pattern = r'(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})'
        match = re.search(single_date_pattern, time_str)
        if match:
            return 24  # 单日使用默认为24小时
        
        # 匹配各种时间单位格式
        time_unit_patterns = [
            (r'(\d+(?:\.\d+)?)\s*小时', 1),
            (r'(\d+(?:\.\d+)?)\s*h', 1),
            (r'(\d+(?:\.\d+)?)\s*hour', 1),
            (r'(\d+(?:\.\d+)?)\s*天', 24),
            (r'(\d+(?:\.\d+)?)\s*day', 24),
            (r'(\d+(?:\.\d+)?)\s*分钟', 1/60),
            (r'(\d+(?:\.\d+)?)\s*min', 1/60),
            (r'(\d+(?:\.\d+)?)\s*minute', 1/60),
        ]
        
        for pattern, multiplier in time_unit_patterns:
            match = re.search(pattern, time_str)
            if match:
                return float(match.group(1)) * multiplier
        
        # 如果没有匹配到单位，尝试解析纯数字（默认为小时）
        try:
            return float(time_str)
        except ValueError:
            return 0
    
    def _can_change_to_in_progress(self, record):
        """检查是否可以将状态改为进行中"""
        if pd.isna(record.get('是否完成')) or record.get('是否完成') != 'Yes':
            return True
        
        # 如果已经完成，检查是否是因为超时自动完成的
        start_time_str = record.get('时间', '')
        estimated_time_str = record.get('预计使用时间', '')
        
        if start_time_str and estimated_time_str:
            try:
                start_time = datetime.strptime(str(start_time_str), '%Y-%m-%d %H:%M:%S')
                estimated_hours = self._parse_time_duration(estimated_time_str)
                end_time = start_time + timedelta(hours=estimated_hours)
                current_time = datetime.now()
                
                # 如果当前时间已经超过预计结束时间，不允许改为进行中
                if current_time >= end_time:
                    return False
            except (ValueError, TypeError):
                pass
        
        return True
    
    def _check_remote_desktop_conflict(self, server_type, exclude_index=None):
        """检查远程桌面是否已被占用"""
        if server_type == '9755':
            records = self.get_records_9755()
        else:
            records = self.get_records_5520()
        
        for idx, record in enumerate(records):
            if exclude_index is not None and idx == exclude_index:
                continue
            
            if (pd.isna(record.get('是否完成')) or record.get('是否完成') != 'Yes') and \
               record.get('是否使用远程桌面') == 'Yes':
                return True
        
        return False

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
        # 立即清除资源缓存以强制刷新
        self._clear_cache('remaining_resources')
    
    def add_record_5520(self, data):
        self.backup_file(self.excel_5520)
        df = pd.read_excel(self.excel_5520)
        new_row = pd.DataFrame([data])
        df = pd.concat([df, new_row], ignore_index=True)
        df.to_excel(self.excel_5520, index=False)
        # 清除相关缓存
        self._clear_cache('5520')
        # 立即清除资源缓存以强制刷新
        self._clear_cache('remaining_resources')
    
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
            df = pd.read_excel(self.excel_9755)
            if 0 <= row_index < len(df):
                record = df.iloc[row_index].to_dict()
                
                # 如果要设置为进行中，检查是否允许
                if status == 'No' and not self._can_change_to_in_progress(record):
                    return False
                
                self.backup_file(self.excel_9755)
                df.at[row_index, '是否完成'] = status
                
                # 如果用户手动设置为已完成，自动计算实际使用时间
                if status == 'Yes':
                    start_time_str = record.get('时间', '')
                    if start_time_str:
                        try:
                            start_time = datetime.strptime(str(start_time_str), '%Y-%m-%d %H:%M:%S')
                            current_time = datetime.now()
                            duration = current_time - start_time
                            
                            # 计算实际使用时间（小时）
                            hours = duration.total_seconds() / 3600
                            if hours < 1:
                                actual_time = f"{int(duration.total_seconds() / 60)}分钟"
                            elif hours < 24:
                                actual_time = f"{hours:.1f}小时"
                            else:
                                days = int(hours / 24)
                                remaining_hours = hours % 24
                                if remaining_hours > 0:
                                    actual_time = f"{days}天{remaining_hours:.1f}小时"
                                else:
                                    actual_time = f"{days}天"
                            
                            df.at[row_index, '实际使用时间'] = actual_time
                        except (ValueError, TypeError):
                            pass
                
                df.to_excel(self.excel_9755, index=False)
                # 清除相关缓存
                self._clear_cache('9755')
                # 立即清除资源缓存以强制刷新
                self._clear_cache('remaining_resources')
                return True
        return False
    
    def update_completion_status_5520(self, row_index, status):
        if os.path.exists(self.excel_5520):
            df = pd.read_excel(self.excel_5520)
            if 0 <= row_index < len(df):
                record = df.iloc[row_index].to_dict()
                
                # 如果要设置为进行中，检查是否允许
                if status == 'No' and not self._can_change_to_in_progress(record):
                    return False
                
                self.backup_file(self.excel_5520)
                df.at[row_index, '是否完成'] = status
                
                # 如果用户手动设置为已完成，自动计算实际使用时间
                if status == 'Yes':
                    start_time_str = record.get('时间', '')
                    if start_time_str:
                        try:
                            start_time = datetime.strptime(str(start_time_str), '%Y-%m-%d %H:%M:%S')
                            current_time = datetime.now()
                            duration = current_time - start_time
                            
                            # 计算实际使用时间（小时）
                            hours = duration.total_seconds() / 3600
                            if hours < 1:
                                actual_time = f"{int(duration.total_seconds() / 60)}分钟"
                            elif hours < 24:
                                actual_time = f"{hours:.1f}小时"
                            else:
                                days = int(hours / 24)
                                remaining_hours = hours % 24
                                if remaining_hours > 0:
                                    actual_time = f"{days}天{remaining_hours:.1f}小时"
                                else:
                                    actual_time = f"{days}天"
                            
                            df.at[row_index, '实际使用时间'] = actual_time
                        except (ValueError, TypeError):
                            pass
                
                df.to_excel(self.excel_5520, index=False)
                # 清除相关缓存
                self._clear_cache('5520')
                # 立即清除资源缓存以强制刷新
                self._clear_cache('remaining_resources')
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
    
    def update_actual_time_9755(self, row_index, actual_time):
        """更新9755服务器的实际使用时间"""
        if os.path.exists(self.excel_9755):
            self.backup_file(self.excel_9755)
            df = pd.read_excel(self.excel_9755)
            if 0 <= row_index < len(df):
                df.at[row_index, '实际使用时间'] = actual_time
                df.to_excel(self.excel_9755, index=False)
                # 清除相关缓存
                self._clear_cache('9755')
                return True
        return False
    
    def update_actual_time_5520(self, row_index, actual_time):
        """更新5520服务器的实际使用时间"""
        if os.path.exists(self.excel_5520):
            self.backup_file(self.excel_5520)
            df = pd.read_excel(self.excel_5520)
            if 0 <= row_index < len(df):
                df.at[row_index, '实际使用时间'] = actual_time
                df.to_excel(self.excel_5520, index=False)
                # 清除相关缓存
                self._clear_cache('5520')
                return True
        return False
    
    def _start_periodic_check(self):
        """启动定时检查任务"""
        def periodic_check():
            while True:
                try:
                    self._periodic_status_check()
                except Exception as e:
                    print(f"定时检查任务出错: {str(e)}")
                time.sleep(300)  # 5分钟 = 300秒
        
        check_thread = threading.Thread(target=periodic_check)
        check_thread.daemon = True
        check_thread.start()
    
    def _periodic_status_check(self):
        """每5分钟执行的状态检查"""
        current_time = datetime.now()
        
        # 检查9755服务器
        self._check_and_update_records(self.excel_9755, '9755', current_time)
        
        # 检查5520服务器
        self._check_and_update_records(self.excel_5520, '5520', current_time)
    
    def _check_and_update_records(self, excel_file, server_type, current_time):
        """检查并更新记录状态"""
        if not os.path.exists(excel_file):
            return
        
        df = pd.read_excel(excel_file)
        if df.empty:
            return
        
        updated = False
        
        for idx, row in df.iterrows():
            start_time_str = row.get('时间', '')
            estimated_time_str = row.get('预计使用时间', '')
            completion_status = row.get('是否完成', '')
            
            if not start_time_str or not estimated_time_str:
                continue
            
            try:
                start_time = datetime.strptime(str(start_time_str), '%Y-%m-%d %H:%M:%S')
                estimated_hours = self._parse_time_duration(estimated_time_str)
                end_time = start_time + timedelta(hours=estimated_hours)
                
                # 首先检查是否超时
                if current_time >= end_time and (pd.isna(completion_status) or completion_status != 'Yes'):
                    # 任务超时，自动标记为已完成
                    df.at[idx, '是否完成'] = 'Yes'
                    # 设置实际使用时间为预计使用时间
                    if pd.isna(df.at[idx, '实际使用时间']) or df.at[idx, '实际使用时间'] == '':
                        df.at[idx, '实际使用时间'] = estimated_time_str
                    updated = True
                    
                # 如果没有超时但状态为已完成，更新实际使用时间为当前时间
                elif current_time < end_time and completion_status == 'Yes':
                    duration = current_time - start_time
                    hours = duration.total_seconds() / 3600
                    
                    if hours < 1:
                        actual_time = f"{max(1, int(duration.total_seconds() / 60))}分钟"
                    elif hours < 24:
                        actual_time = f"{hours:.1f}小时"
                    else:
                        days = int(hours / 24)
                        remaining_hours = hours % 24
                        if remaining_hours > 0:
                            actual_time = f"{days}天{remaining_hours:.1f}小时"
                        else:
                            actual_time = f"{days}天"
                    
                    df.at[idx, '实际使用时间'] = actual_time
                    updated = True
                    
            except (ValueError, TypeError):
                continue
        
        # 如果有更新，保存文件并清除缓存
        if updated:
            self.backup_file(excel_file)
            df.to_excel(excel_file, index=False)
            self._clear_cache(server_type)
            self._clear_cache('remaining_resources')

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
    try:
        # 获取表单数据
        remote = request.form['remote']
        nodes_str = request.form['nodes']
        gpu_str = request.form['gpu']
        
        # 获取当前资源状态
        resources = server_manager.calculate_remaining_resources()
        errors = []
        
        # 检查远程桌面冲突
        if remote == 'Yes' and server_manager._check_remote_desktop_conflict('9755'):
            errors.append('远程桌面已被占用，请等待当前任务完成')
        
        # 检查节点冲突
        if nodes_str:
            try:
                requested_nodes = [int(n.strip()) for n in nodes_str.split(',') if n.strip().isdigit()]
                occupied_nodes = resources['9755']['nodes_occupied']
                conflict_nodes = [n for n in requested_nodes if n in occupied_nodes]
                
                if conflict_nodes:
                    errors.append(f'节点 {",".join(map(str, conflict_nodes))} 已被占用')
                
                if len(requested_nodes) > resources['9755']['nodes_remaining']:
                    errors.append(f'请求节点数 ({len(requested_nodes)}) 超过剩余节点数 ({resources["9755"]["nodes_remaining"]})')
            except ValueError:
                errors.append('节点格式错误，请输入有效的节点编号')
        
        # 检查GPU冲突
        if gpu_str and gpu_str != 'No':
            try:
                if gpu_str.isdigit():
                    requested_gpus = [int(gpu_str)]
                elif ',' in gpu_str:
                    requested_gpus = [int(g.strip()) for g in gpu_str.split(',') if g.strip().isdigit()]
                else:
                    requested_gpus = []
                
                occupied_gpus = resources['9755']['gpu_occupied']
                conflict_gpus = [g for g in requested_gpus if g in occupied_gpus]
                
                if conflict_gpus:
                    errors.append(f'GPU {",".join(map(str, conflict_gpus))} 已被占用')
                
                if len(requested_gpus) > resources['9755']['gpu_remaining']:
                    errors.append(f'请求GPU数 ({len(requested_gpus)}) 超过剩余GPU数 ({resources["9755"]["gpu_remaining"]})')
            except ValueError:
                errors.append('GPU格式错误，请选择有效的GPU')
        
        if errors:
            return jsonify({'success': False, 'error': '\n'.join(errors)}), 400
        
        # 如果验证通过，添加记录
        data = {
            '时间': request.form['time'],
            '姓名': request.form['name'],
            '占用节点': request.form['nodes'],
            '占用GPU': request.form['gpu'],
            '是否使用远程桌面': request.form['remote'],
            '任务类型': request.form['task_type'],
            '预计使用时间': request.form['estimated_time'],
            '实际使用时间': request.form.get('actual_time', ''),
            '是否完成': request.form.get('completed', '')
        }
        server_manager.add_record_9755(data)
        return redirect(url_for('server_9755'))
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'系统错误: {str(e)}'}), 500

@app.route('/add_5520', methods=['POST'])
def add_5520():
    try:
        # 获取表单数据
        remote = request.form['remote']
        cores_str = request.form['cores']
        gpu_str = request.form['gpu']
        
        # 获取当前资源状态
        resources = server_manager.calculate_remaining_resources()
        errors = []
        
        # 检查远程桌面冲突
        if remote == 'Yes' and server_manager._check_remote_desktop_conflict('5520'):
            errors.append('远程桌面已被占用，请等待当前任务完成')
        
        # 检查核数资源
        if cores_str:
            try:
                if cores_str.lower() == 'all':
                    requested_cores = resources['5520']['cores_total']
                else:
                    requested_cores = int(cores_str)
                    if requested_cores <= 0:
                        errors.append('核数必须大于0')
                
                if requested_cores > resources['5520']['cores_remaining']:
                    errors.append(f'请求核数 ({requested_cores}) 超过剩余核数 ({resources["5520"]["cores_remaining"]})')
            except ValueError:
                errors.append('核数格式错误，请输入数字或"all"')
        
        # 检查GPU资源
        if gpu_str == 'Yes' and resources['5520']['gpu_remaining'] == 0:
            errors.append('GPU已被占用，请等待当前任务完成')
        
        if errors:
            return jsonify({'success': False, 'error': '\n'.join(errors)}), 400
        
        # 如果验证通过，添加记录
        data = {
            '时间': request.form['time'],
            '姓名': request.form['name'],
            '使用核数': request.form['cores'],
            '占用GPU': request.form['gpu'],
            '是否使用远程桌面': request.form['remote'],
            '任务类型': request.form['task_type'],
            '预计使用时间': request.form['estimated_time'],
            '实际使用时间': request.form.get('actual_time', ''),
            '是否完成': request.form.get('completed', '')
        }
        server_manager.add_record_5520(data)
        return redirect(url_for('server_5520'))
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'系统错误: {str(e)}'}), 500

@app.route('/api/resources')
def api_resources():
    return jsonify(server_manager.calculate_remaining_resources())

@app.route('/api/update_status_9755/<int:row_index>', methods=['POST'])
def update_status_9755(row_index):
    data = request.get_json()
    status = data.get('status', '')
    if server_manager.update_completion_status_9755(row_index, status):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '无法更新状态，可能是因为任务已超时自动完成'}), 400

@app.route('/api/update_status_5520/<int:row_index>', methods=['POST'])
def update_status_5520(row_index):
    data = request.get_json()
    status = data.get('status', '')
    if server_manager.update_completion_status_5520(row_index, status):
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': '无法更新状态，可能是因为任务已超时自动完成'}), 400

@app.route('/api/update_actual_time_9755/<int:row_index>', methods=['POST'])
def update_actual_time_9755(row_index):
    data = request.get_json()
    actual_time = data.get('actual_time', '')
    if server_manager.update_actual_time_9755(row_index, actual_time):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

@app.route('/api/update_actual_time_5520/<int:row_index>', methods=['POST'])
def update_actual_time_5520(row_index):
    data = request.get_json()
    actual_time = data.get('actual_time', '')
    if server_manager.update_actual_time_5520(row_index, actual_time):
        return jsonify({'success': True})
    return jsonify({'success': False}), 400

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)