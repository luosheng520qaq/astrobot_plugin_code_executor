import asyncio
import socket
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn
from typing import Optional
import os
from datetime import datetime
from .database import ExecutionHistoryDB
from astrbot.api import logger


class CodeExecutorWebUI:
    """代码执行器WebUI服务"""
    
    def __init__(self, db: ExecutionHistoryDB, port: int = 10000, file_output_dir: str = None, enable_file_serving: bool = False):
        self.db = db
        self.port = port
        self.file_output_dir = file_output_dir
        self.enable_file_serving = enable_file_serving
        self.app = FastAPI(title="代码执行器历史记录", description="查看AI代码执行历史记录")
        self.server = None
        self.setup_routes()
    
    def is_port_in_use(self, port: int) -> bool:
        """检查端口是否被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('0.0.0.0', port))
                return False
            except OSError:
                return True
    
    def find_available_port(self, start_port: int, max_attempts: int = 10) -> int:
        """寻找可用端口"""
        for i in range(max_attempts):
            test_port = start_port + i
            if not self.is_port_in_use(test_port):
                return test_port
        raise OSError(f"无法在 {start_port}-{start_port + max_attempts - 1} 范围内找到可用端口")
    
    def setup_routes(self):
        """设置路由"""
        
        @self.app.get("/", response_class=HTMLResponse)
        async def index(request: Request):
            """主页"""
            return HTMLResponse(content=self.get_index_html())
        
        @self.app.get("/api/history")
        async def get_history(
            page: int = Query(1, ge=1),
            page_size: int = Query(20, ge=1, le=100),
            sender_id: Optional[str] = Query(None),
            search: Optional[str] = Query(None),
            success_filter: Optional[bool] = Query(None),
            start_time: Optional[str] = Query(None),
            end_time: Optional[str] = Query(None)
        ):
            """获取历史记录API"""
            try:
                result = await self.db.get_execution_history(
                    page=page,
                    page_size=page_size,
                    sender_id=sender_id,
                    search_keyword=search,
                    success_filter=success_filter,
                    start_time=start_time,
                    end_time=end_time
                )
                return JSONResponse(content=result)
            except Exception as e:
                logger.error(f"获取历史记录失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.delete("/api/history/{record_id}")
        async def delete_record(record_id: int):
            """删除单条记录API"""
            try:
                success = await self.db.delete_execution_record(record_id)
                if not success:
                     raise HTTPException(status_code=404, detail="记录不存在")
                return JSONResponse(content={"success": True})
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"删除记录失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/history")
        async def delete_records(type: str = Query(..., regex="^(all|success|fail)$")):
            """批量删除记录API"""
            try:
                count = await self.db.delete_execution_records(type)
                return JSONResponse(content={"success": True, "deleted_count": count})
            except Exception as e:
                logger.error(f"批量删除记录失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/detail/{record_id}")
        async def get_detail(record_id: int):
            """获取执行详情API"""
            try:
                result = await self.db.get_execution_detail(record_id)
                if not result:
                    raise HTTPException(status_code=404, detail="记录不存在")
                return JSONResponse(content=result)
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"获取执行详情失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        @self.app.get("/api/statistics")
        async def get_statistics():
            """获取统计信息API"""
            try:
                result = await self.db.get_statistics()
                return JSONResponse(content=result)
            except Exception as e:
                logger.error(f"获取统计信息失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))
        
        # 文件服务路由（用于本地路由发送）
        if self.enable_file_serving and self.file_output_dir:
            @self.app.get("/files/{file_name}")
            async def serve_file(file_name: str):
                """提供文件下载服务"""
                try:
                    file_path = os.path.join(self.file_output_dir, file_name)
                    if not os.path.exists(file_path) or not os.path.isfile(file_path):
                        raise HTTPException(status_code=404, detail="文件不存在")
                    
                    # 安全检查：确保文件在指定目录内
                    real_file_path = os.path.realpath(file_path)
                    real_output_dir = os.path.realpath(self.file_output_dir)
                    if not real_file_path.startswith(real_output_dir):
                        raise HTTPException(status_code=403, detail="访问被拒绝")
                    
                    return FileResponse(file_path, filename=file_name)
                except HTTPException:
                    raise
                except Exception as e:
                    logger.error(f"文件服务失败: {e}", exc_info=True)
                    raise HTTPException(status_code=500, detail=str(e))
    
    def get_index_html(self) -> str:
        """获取主页HTML"""
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Executor History</title>
    <!-- PrismJS for Syntax Highlighting -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/themes/prism-tomorrow.min.css" rel="stylesheet" />
    <style>
        :root {
            --primary-color: #00a8ff;
            --primary-hover: #0097e6;
            --danger-color: #ff7675;
            --danger-hover: #d63031;
            --success-color: #55efc4;
            --text-main: #2d3436;
            --text-secondary: #636e72;
            --glass-bg: rgba(255, 255, 255, 0.7);
            --glass-border: 1px solid rgba(255, 255, 255, 0.6);
            --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.1);
        }

        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #e0f7fa;
            background-image: 
                radial-gradient(at 0% 0%, hsla(192,95%,90%,1) 0, transparent 50%), 
                radial-gradient(at 50% 100%, hsla(225,95%,90%,1) 0, transparent 50%),
                radial-gradient(at 100% 0%, hsla(180,95%,90%,1) 0, transparent 50%);
            background-attachment: fixed;
            color: var(--text-main);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
        }

        .glass {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: var(--glass-border);
            border-radius: 20px;
            box-shadow: var(--glass-shadow);
        }

        .container {
            max-width: 1200px;
            margin: 0 auto;
        }

        /* Header */
        .header {
            text-align: center;
            padding: 40px;
            margin-bottom: 30px;
            animation: fadeInDown 0.8s ease-out;
        }

        .header h1 {
            font-size: 2.5rem;
            font-weight: 300;
            background: linear-gradient(45deg, #0984e3, #00cec9);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 10px;
        }

        .header p { color: var(--text-secondary); }

        /* Stats */
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .stat-card {
            padding: 20px;
            text-align: center;
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            animation: fadeInUp 0.6s ease-out forwards;
            opacity: 0;
        }

        .stat-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 12px 40px 0 rgba(31, 38, 135, 0.15);
            background: rgba(255, 255, 255, 0.85);
        }

        .stat-number {
            font-size: 2rem;
            font-weight: bold;
            color: var(--primary-color);
        }

        .stat-label {
            font-size: 0.9rem;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-top: 5px;
        }

        /* Controls */
        .controls {
            padding: 25px;
            margin-bottom: 30px;
            animation: fadeIn 0.8s ease-out;
        }

        .controls-row {
            display: flex;
            gap: 15px;
            flex-wrap: wrap;
            align-items: flex-end;
        }

        .form-group {
            display: flex;
            flex-direction: column;
            flex: 1;
            min-width: 150px;
        }

        .form-group label {
            font-size: 0.85rem;
            color: var(--text-secondary);
            margin-bottom: 8px;
            font-weight: 500;
        }

        input, select {
            padding: 12px;
            border: 1px solid rgba(255,255,255,0.8);
            background: rgba(255,255,255,0.5);
            border-radius: 10px;
            font-size: 14px;
            transition: all 0.3s ease;
            outline: none;
            color: var(--text-main);
        }

        input:focus, select:focus {
            background: rgba(255,255,255,0.9);
            border-color: var(--primary-color);
            box-shadow: 0 0 0 3px rgba(0, 168, 255, 0.1);
        }

        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 10px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s ease;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
            color: white;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }

        .btn-primary {
            background: linear-gradient(45deg, #00a8ff, #0097e6);
        }
        .btn-primary:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0, 168, 255, 0.3); }

        .btn-secondary {
            background: rgba(255,255,255,0.6);
            color: var(--text-secondary);
            border: 1px solid rgba(0,0,0,0.05);
        }
        .btn-secondary:hover { background: rgba(255,255,255,0.9); transform: translateY(-2px); }

        .btn-danger {
            background: linear-gradient(45deg, #ff7675, #d63031);
        }
        .btn-danger:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(214, 48, 49, 0.3); }

        /* Records List */
        .records-container {
            padding: 0;
            overflow: hidden;
            animation: fadeIn 1s ease-out;
        }

        .records-header-title {
            padding: 25px;
            border-bottom: 1px solid rgba(0,0,0,0.05);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .records-header-title h2 {
            font-weight: 400;
            color: var(--text-main);
        }

        .record-item {
            padding: 20px 25px;
            border-bottom: 1px solid rgba(0,0,0,0.03);
            transition: background 0.3s ease;
            display: grid;
            grid-template-columns: 50px 1fr auto;
            gap: 20px;
            align-items: center;
            cursor: pointer;
        }

        .record-item:hover {
            background: rgba(255,255,255,0.4);
        }

        .record-status-icon {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.2rem;
            color: white;
        }

        .status-success { background: linear-gradient(45deg, #55efc4, #00b894); box-shadow: 0 4px 10px rgba(0, 184, 148, 0.2); }
        .status-error { background: linear-gradient(45deg, #ff7675, #d63031); box-shadow: 0 4px 10px rgba(214, 48, 49, 0.2); }

        .record-info h3 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 5px;
            color: var(--text-main);
        }

        .record-meta {
            font-size: 0.85rem;
            color: var(--text-secondary);
            display: flex;
            gap: 15px;
            align-items: center;
        }

        .record-actions {
            opacity: 0.6;
            transition: opacity 0.3s;
        }
        .record-item:hover .record-actions { opacity: 1; }

        .btn-icon {
            width: 36px;
            height: 36px;
            border-radius: 8px;
            border: none;
            background: rgba(255,255,255,0.5);
            color: var(--text-secondary);
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }
        .btn-icon:hover { background: white; color: var(--danger-hover); transform: scale(1.1); }

        /* Pagination */
        .pagination {
            margin-top: 30px;
            display: flex;
            justify-content: center;
            gap: 10px;
        }

        .page-btn {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            border: none;
            background: var(--glass-bg);
            cursor: pointer;
            transition: all 0.3s;
            color: var(--text-secondary);
        }
        .page-btn:hover:not(:disabled) { background: white; color: var(--primary-color); transform: translateY(-2px); }
        .page-btn.active { background: var(--primary-color); color: white; box-shadow: 0 4px 10px rgba(0, 168, 255, 0.3); }
        .page-btn:disabled { opacity: 0.5; cursor: not-allowed; }

        /* Modal */
        .modal {
            display: none;
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.2);
            backdrop-filter: blur(5px);
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        .modal.show { opacity: 1; }

        .modal-content {
            position: absolute;
            top: 50%; left: 50%;
            transform: translate(-50%, -50%) scale(0.9);
            width: 90%; max-width: 900px;
            max-height: 90vh;
            overflow-y: auto;
            background: rgba(255, 255, 255, 0.9);
            backdrop-filter: blur(20px);
            border: 1px solid rgba(255, 255, 255, 0.8);
            box-shadow: 0 20px 50px rgba(0,0,0,0.1);
            border-radius: 20px;
            transition: transform 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }
        .modal.show .modal-content { transform: translate(-50%, -50%) scale(1); }

        /* Code Block & Details */
        .detail-section-title {
            font-size: 0.95rem;
            font-weight: 600;
            color: var(--text-secondary);
            margin-bottom: 10px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .code-block-wrapper {
            border-radius: 10px;
            overflow: hidden;
            border: 1px solid rgba(0,0,0,0.1);
            margin-bottom: 20px;
            background: #2d2d2d; /* Dark theme for code */
        }

        /* PrismJS Override */
        pre[class*="language-"] {
            margin: 0 !important;
            border-radius: 0 !important;
            padding: 20px !important;
            font-size: 0.9rem !important;
            background: transparent !important;
            text-shadow: none !important;
        }

        .file-list {
            list-style: none;
            padding: 0;
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 10px;
        }

        .file-item {
            background: rgba(255, 255, 255, 0.6);
            border: 1px solid rgba(255, 255, 255, 0.8);
            padding: 12px 15px;
            border-radius: 10px;
            font-family: monospace;
            font-size: 0.9em;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 10px;
            transition: all 0.2s;
            cursor: pointer;
        }

        .file-item:hover {
            background: white;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.05);
            border-color: var(--primary-color);
            color: var(--primary-color);
        }

        .file-icon {
            font-size: 1.2em;
        }

        /* Animations */
        @keyframes fadeInDown { from { opacity: 0; transform: translateY(-30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeInUp { from { opacity: 0; transform: translateY(30px); } to { opacity: 1; transform: translateY(0); } }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

        /* Responsive */
        @media (max-width: 768px) {
            .record-item { grid-template-columns: 1fr auto; }
            .record-status-icon { display: none; }
            .controls-row { flex-direction: column; align-items: stretch; }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header glass">
            <h1>🤖 Code Executor History</h1>
            <p>AI代码执行历史记录看板</p>
        </div>
        
        <div class="stats-grid" id="statsGrid">
            <!-- Stats loaded via JS -->
        </div>
        
        <div class="controls glass">
            <div class="controls-row">
                <div class="form-group">
                    <label>搜索</label>
                    <input type="text" id="searchInput" placeholder="搜索代码、描述...">
                </div>
                <div class="form-group">
                    <label>用户ID</label>
                    <input type="text" id="senderIdInput" placeholder="筛选用户...">
                </div>
                <div class="form-group" style="flex: 0 0 120px;">
                    <label>状态</label>
                    <select id="successFilter">
                        <option value="">全部</option>
                        <option value="true">成功</option>
                        <option value="false">失败</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>开始时间</label>
                    <input type="datetime-local" id="startTime">
                </div>
                <div class="form-group">
                    <label>结束时间</label>
                    <input type="datetime-local" id="endTime">
                </div>
            </div>
            <div class="controls-row" style="margin-top: 15px; justify-content: space-between;">
                <div style="display: flex; gap: 10px;">
                    <button class="btn btn-secondary" onclick="resetFilters()">重置筛选</button>
                    <button class="btn btn-primary" onclick="searchRecords()">🔍 搜索记录</button>
                </div>
                <div style="display: flex; gap: 10px;">
                     <select id="bulkDeleteType" style="width: 120px;">
                        <option value="all">全部记录</option>
                        <option value="success">成功记录</option>
                        <option value="fail">失败记录</option>
                    </select>
                    <button class="btn btn-danger" onclick="confirmBulkDelete()">🗑️ 批量删除</button>
                </div>
            </div>
        </div>
        
        <div class="records-container glass">
            <div class="records-header-title">
                <h2>执行列表</h2>
                <span id="totalCount" style="color: var(--text-secondary); font-size: 0.9rem;"></span>
            </div>
            <div id="recordsList">
                <div style="padding: 40px; text-align: center; color: var(--text-secondary);">加载中...</div>
            </div>
            <div class="pagination" id="pagination"></div>
            <div style="height: 20px;"></div>
        </div>
    </div>

    <!-- Modal -->
    <div class="modal" id="detailModal">
        <div class="modal-content glass">
            <div class="records-header-title">
                <h2>执行详情</h2>
                <button class="btn-icon" onclick="closeModal()">✕</button>
            </div>
            <div style="padding: 25px;" id="modalBody"></div>
        </div>
    </div>

    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/prism.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/prism/1.29.0/components/prism-python.min.js"></script>
    <script>
        let currentPage = 1;
        let currentFilters = {};
        
        document.addEventListener('DOMContentLoaded', () => {
            loadStatistics();
            loadRecords();
            
            document.getElementById('detailModal').addEventListener('click', (e) => {
                if (e.target.classList.contains('modal')) closeModal();
            });
        });

        async function loadStatistics() {
            try {
                const res = await fetch('/api/statistics');
                const stats = await res.json();
                const grid = document.getElementById('statsGrid');
                const items = [
                    { label: '总执行次数', val: stats.total_executions },
                    { label: '成功执行', val: stats.successful_executions },
                    { label: '失败执行', val: stats.failed_executions },
                    { label: '成功率', val: stats.success_rate + '%' },
                    { label: '用户数量', val: stats.unique_users },
                    { label: '近7天', val: stats.recent_executions }
                ];
                
                grid.innerHTML = items.map((item, index) => `
                    <div class="glass stat-card" style="animation-delay: ${index * 0.1}s">
                        <div class="stat-number">${item.val}</div>
                        <div class="stat-label">${item.label}</div>
                    </div>
                `).join('');
            } catch (e) { console.error(e); }
        }

        async function loadRecords(page = 1) {
            try {
                const params = new URLSearchParams({ page, page_size: 20, ...currentFilters });
                const res = await fetch(`/api/history?${params}`);
                const data = await res.json();
                
                displayRecords(data.records);
                displayPagination(data);
                document.getElementById('totalCount').textContent = `共 ${data.total_count} 条`;
                currentPage = page;
            } catch (e) {
                document.getElementById('recordsList').innerHTML = '<div style="padding:20px;text-align:center;color:red">加载失败</div>';
            }
        }

        function displayRecords(records) {
            const list = document.getElementById('recordsList');
            if (!records.length) {
                list.innerHTML = '<div style="padding:40px;text-align:center;color:#999">暂无数据</div>';
                return;
            }
            
            list.innerHTML = records.map((r, i) => `
                <div class="record-item" onclick="showDetail(${r.id})">
                    <div class="record-status-icon ${r.success ? 'status-success' : 'status-error'}">
                        ${r.success ? '✓' : '✕'}
                    </div>
                    <div class="record-info">
                        <h3>${escapeHtml(r.sender_name)} <span style="font-weight:normal;color:#999;font-size:0.8em">(${r.sender_id})</span></h3>
                        <div class="record-meta">
                            <span>📅 ${formatTime(r.created_at)}</span>
                            <span>⏱ ${r.execution_time ? r.execution_time.toFixed(2)+'s' : '-'}</span>
                            <span style="color:${r.success?'#00b894':'#ff7675'}">${r.success?'成功':'失败'}</span>
                        </div>
                        ${r.description ? `<div style="margin-top:5px;color:#666;font-size:0.9em">${escapeHtml(r.description)}</div>` : ''}
                    </div>
                    <div class="record-actions">
                        <button class="btn-icon" onclick="event.stopPropagation(); deleteRecord(${r.id})" title="删除">🗑️</button>
                    </div>
                </div>
            `).join('');
        }

        function displayPagination(data) {
            const p = document.getElementById('pagination');
            if (data.total_pages <= 1) { p.innerHTML = ''; return; }
            
            let html = `<button class="page-btn" ${data.page<=1?'disabled':''} onclick="loadRecords(${data.page-1})">←</button>`;
            
            const start = Math.max(1, data.page - 2);
            const end = Math.min(data.total_pages, data.page + 2);
            
            for (let i = start; i <= end; i++) {
                html += `<button class="page-btn ${i===data.page?'active':''}" onclick="loadRecords(${i})">${i}</button>`;
            }
            
            html += `<button class="page-btn" ${data.page>=data.total_pages?'disabled':''} onclick="loadRecords(${data.page+1})">→</button>`;
            p.innerHTML = html;
        }

        function searchRecords() {
            const getVal = id => document.getElementById(id).value.trim();
            currentFilters = {
                search: getVal('searchInput'),
                sender_id: getVal('senderIdInput'),
                success_filter: getVal('successFilter'),
                start_time: getVal('startTime'),
                end_time: getVal('endTime')
            };
            // Clean empty
            Object.keys(currentFilters).forEach(k => !currentFilters[k] && delete currentFilters[k]);
            loadRecords(1);
        }

        function resetFilters() {
            ['searchInput','senderIdInput','successFilter','startTime','endTime'].forEach(id => document.getElementById(id).value = '');
            currentFilters = {};
            loadRecords(1);
        }

        async function deleteRecord(id) {
            if (!confirm('确定要删除这条记录吗？')) return;
            try {
                const res = await fetch(`/api/history/${id}`, { method: 'DELETE' });
                if (res.ok) {
                    loadRecords(currentPage);
                    loadStatistics();
                } else alert('删除失败');
            } catch (e) { alert('错误: ' + e); }
        }

        async function confirmBulkDelete() {
            const type = document.getElementById('bulkDeleteType').value;
            const map = { 'all': '全部', 'success': '成功', 'fail': '失败' };
            if (!confirm(`确定要删除【${map[type]}】记录吗？此操作不可恢复！`)) return;
            
            try {
                const res = await fetch(`/api/history?type=${type}`, { method: 'DELETE' });
                const data = await res.json();
                if (res.ok) {
                    alert(`已删除 ${data.deleted_count} 条记录`);
                    loadRecords(1);
                    loadStatistics();
                } else alert('删除失败');
            } catch (e) { alert('错误: ' + e); }
        }

        async function showDetail(id) {
            try {
                const res = await fetch(`/api/detail/${id}`);
                const r = await res.json();
                
                const html = `
                    <div style="margin-bottom:25px">
                        <div class="detail-section-title">💻 执行代码</div>
                        <div class="code-block-wrapper">
                            <pre class="language-python"><code>${escapeHtml(r.code)}</code></pre>
                        </div>
                    </div>
                    ${r.output ? `
                    <div style="margin-bottom:25px">
                        <div class="detail-section-title">📝 输出</div>
                        <div class="code-block-wrapper">
                            <pre class="language-none"><code>${escapeHtml(r.output)}</code></pre>
                        </div>
                    </div>` : ''}
                    ${r.error_msg ? `
                    <div style="margin-bottom:25px">
                        <div class="detail-section-title" style="color: var(--danger-color)">❌ 错误信息</div>
                        <div class="code-block-wrapper" style="border-color: var(--danger-color); background: #fff5f5">
                            <pre class="language-none" style="color: #c0392b"><code>${escapeHtml(r.error_msg)}</code></pre>
                        </div>
                    </div>` : ''}
                    ${r.file_paths?.length ? `
                    <div style="margin-bottom:25px">
                        <div class="detail-section-title">📂 生成文件</div>
                        <ul class="file-list">
                            ${r.file_paths.map(f=>`
                                <li class="file-item" onclick="window.open('/files/${f}', '_blank')">
                                    <span class="file-icon">📄</span> ${escapeHtml(f)}
                                </li>
                            `).join('')}
                        </ul>
                    </div>` : ''}
                `;
                
                document.getElementById('modalBody').innerHTML = html;
                const modal = document.getElementById('detailModal');
                modal.style.display = 'block';
                setTimeout(() => {
                    modal.classList.add('show');
                    Prism.highlightAllUnder(document.getElementById('modalBody'));
                }, 10);
            } catch (e) { console.error(e); }
        }

        function closeModal() {
            const modal = document.getElementById('detailModal');
            modal.classList.remove('show');
            setTimeout(() => modal.style.display = 'none', 300);
        }

        function escapeHtml(text) {
            if (!text) return '';
            return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
                       .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }

        function formatTime(str) {
            return new Date(str).toLocaleString('zh-CN');
        }
    </script>
</body>
</html>
        """
    
    async def start_server(self):
        """启动WebUI服务器"""
        try:
            # 如果服务器已经存在，先停止它
            if self.server:
                await self.stop_server()
            
            # 动态端口分配：如果配置端口被占用，自动寻找可用端口
            original_port = self.port
            if self.is_port_in_use(self.port):
                logger.warning(f"配置端口 {self.port} 已被占用，正在寻找可用端口...")
                try:
                    available_port = self.find_available_port(self.port)
                    self.port = available_port
                    logger.info(f"找到可用端口: {self.port} (原配置端口: {original_port})")
                except OSError as port_error:
                    logger.error(f"无法找到可用端口: {port_error}")
                    logger.info("建议：1) 重启AstrBot 2) 修改WebUI端口配置到更高的端口号")
                    raise
            
            config = uvicorn.Config(
                app=self.app,
                host="0.0.0.0",
                port=self.port,
                log_level="info",
                access_log=False
            )
            self.server = uvicorn.Server(config)
            
            logger.info(f"WebUI服务器启动中，端口: {self.port}")
            logger.info(f"访问地址: http://localhost:{self.port}")
            
            if self.port != original_port:
                logger.warning(f"注意：WebUI端口已从 {original_port} 自动调整为 {self.port}")
                logger.info("如需固定端口，请确保该端口未被占用或修改配置文件")
            
            # 在后台运行服务器
            await self.server.serve()
        except OSError as e:
            if "Address already in use" in str(e) or "Only one usage of each socket address" in str(e):
                logger.error(f"端口 {self.port} 被占用，WebUI服务器启动失败")
                logger.info("这通常是由于插件热重载时端口未完全释放导致的")
                self.server = None
                raise
            else:
                logger.error(f"WebUI服务器启动失败: {e}", exc_info=True)
                raise
        except Exception as e:
            logger.error(f"WebUI服务器启动失败: {e}", exc_info=True)
            raise
    
    async def stop_server(self):
        """停止WebUI服务器"""
        if self.server:
            logger.info("正在停止WebUI服务器...")
            try:
                # 设置退出标志
                self.server.should_exit = True
                
                # 如果服务器正在运行，强制关闭
                if hasattr(self.server, 'servers') and self.server.servers:
                    for server in self.server.servers:
                        server.close()
                        await server.wait_closed()
                
                # 等待服务器完全关闭
                await asyncio.sleep(0.5)
                
                # 清理服务器引用
                self.server = None
                
                logger.info("WebUI服务器已停止")
            except Exception as e:
                logger.warning(f"停止WebUI服务器时出现异常: {e}")
                # 强制清理
                self.server = None