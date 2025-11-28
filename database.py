import sqlite3
import json
import asyncio
import aiosqlite
from datetime import datetime
from typing import List, Dict, Any, Optional
from astrbot.api import logger


class ExecutionHistoryDB:
    """代码执行历史记录数据库管理类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        
    async def init_database(self):
        """初始化数据库表结构"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    CREATE TABLE IF NOT EXISTS execution_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender_id TEXT NOT NULL,
                        sender_name TEXT NOT NULL,
                        code TEXT NOT NULL,
                        description TEXT,
                        success BOOLEAN NOT NULL,
                        output TEXT,
                        error_msg TEXT,
                        file_paths TEXT,  -- JSON格式存储文件路径列表
                        execution_time REAL,  -- 执行耗时（秒）
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # 创建索引提高查询性能
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_sender_id ON execution_history(sender_id)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_created_at ON execution_history(created_at)
                """)
                await db.execute("""
                    CREATE INDEX IF NOT EXISTS idx_success ON execution_history(success)
                """)
                
                await db.commit()
                logger.info(f"数据库初始化完成: {self.db_path}")
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}", exc_info=True)
            raise
    
    async def add_execution_record(self, 
                                 sender_id: str,
                                 sender_name: str, 
                                 code: str,
                                 description: str,
                                 success: bool,
                                 output: str = None,
                                 error_msg: str = None,
                                 file_paths: List[str] = None,
                                 execution_time: float = None) -> int:
        """添加执行记录"""
        try:
            file_paths_json = json.dumps(file_paths or [], ensure_ascii=False)
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("""
                    INSERT INTO execution_history 
                    (sender_id, sender_name, code, description, success, output, error_msg, file_paths, execution_time)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (sender_id, sender_name, code, description, success, output, error_msg, file_paths_json, execution_time))
                
                await db.commit()
                record_id = cursor.lastrowid
                logger.debug(f"添加执行记录成功，ID: {record_id}")
                return record_id
        except Exception as e:
            logger.error(f"添加执行记录失败: {e}", exc_info=True)
            raise
    
    async def delete_execution_record(self, record_id: int) -> bool:
        """删除单条执行记录"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute("DELETE FROM execution_history WHERE id = ?", (record_id,))
                await db.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"删除执行记录失败: {e}", exc_info=True)
            raise

    async def delete_execution_records(self, delete_type: str) -> int:
        """批量删除执行记录
        :param delete_type: 'all' (全部), 'success' (成功), 'fail' (失败)
        :return: 删除的记录数量
        """
        try:
            where_clause = ""
            if delete_type == 'success':
                where_clause = "WHERE success = 1"
            elif delete_type == 'fail':
                where_clause = "WHERE success = 0"
            elif delete_type != 'all':
                raise ValueError(f"无效的删除类型: {delete_type}")
            
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(f"DELETE FROM execution_history {where_clause}")
                await db.commit()
                return cursor.rowcount
        except Exception as e:
            logger.error(f"批量删除执行记录失败: {e}", exc_info=True)
            raise

    async def get_execution_history(self, 
                                  page: int = 1, 
                                  page_size: int = 20,
                                  sender_id: str = None,
                                  search_keyword: str = None,
                                  success_filter: bool = None,
                                  start_time: str = None,
                                  end_time: str = None) -> Dict[str, Any]:
        """获取执行历史记录（分页）"""
        try:
            offset = (page - 1) * page_size
            
            # 构建查询条件
            where_conditions = []
            params = []
            
            if sender_id:
                where_conditions.append("sender_id = ?")
                params.append(sender_id)
            
            if search_keyword:
                where_conditions.append("(code LIKE ? OR description LIKE ? OR sender_name LIKE ?)")
                keyword_pattern = f"%{search_keyword}%"
                params.extend([keyword_pattern, keyword_pattern, keyword_pattern])
            
            if success_filter is not None:
                where_conditions.append("success = ?")
                params.append(success_filter)

            if start_time:
                # 处理 HTML datetime-local 输入格式 (YYYY-MM-DDTHH:mm)
                clean_start = start_time.replace('T', ' ')
                if len(clean_start) == 16: # YYYY-MM-DD HH:mm
                    clean_start += ':00'
                where_conditions.append("created_at >= ?")
                params.append(clean_start)
            
            if end_time:
                clean_end = end_time.replace('T', ' ')
                if len(clean_end) == 16:
                    clean_end += ':59'
                where_conditions.append("created_at <= ?")
                params.append(clean_end)
            
            where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
            
            async with aiosqlite.connect(self.db_path) as db:
                # 获取总记录数
                count_query = f"SELECT COUNT(*) FROM execution_history {where_clause}"
                async with db.execute(count_query, params) as cursor:
                    total_count = (await cursor.fetchone())[0]
                
                # 获取分页数据
                data_query = f"""
                    SELECT id, sender_id, sender_name, code, description, success, 
                           output, error_msg, file_paths, execution_time, created_at
                    FROM execution_history 
                    {where_clause}
                    ORDER BY created_at DESC 
                    LIMIT ? OFFSET ?
                """
                
                async with db.execute(data_query, params + [page_size, offset]) as cursor:
                    rows = await cursor.fetchall()
                
                # 处理结果
                records = []
                for row in rows:
                    record = {
                        'id': row[0],
                        'sender_id': row[1],
                        'sender_name': row[2],
                        'code': row[3],
                        'description': row[4],
                        'success': bool(row[5]),
                        'output': row[6],
                        'error_msg': row[7],
                        'file_paths': json.loads(row[8]) if row[8] else [],
                        'execution_time': row[9],
                        'created_at': row[10]
                    }
                    records.append(record)
                
                return {
                    'records': records,
                    'total_count': total_count,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total_count + page_size - 1) // page_size
                }
        except Exception as e:
            logger.error(f"获取执行历史失败: {e}", exc_info=True)
            raise
    
    async def get_execution_detail(self, record_id: int) -> Optional[Dict[str, Any]]:
        """获取单条执行记录详情"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute("""
                    SELECT id, sender_id, sender_name, code, description, success, 
                           output, error_msg, file_paths, execution_time, created_at
                    FROM execution_history 
                    WHERE id = ?
                """, (record_id,)) as cursor:
                    row = await cursor.fetchone()
                
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'sender_id': row[1],
                    'sender_name': row[2],
                    'code': row[3],
                    'description': row[4],
                    'success': bool(row[5]),
                    'output': row[6],
                    'error_msg': row[7],
                    'file_paths': json.loads(row[8]) if row[8] else [],
                    'execution_time': row[9],
                    'created_at': row[10]
                }
        except Exception as e:
            logger.error(f"获取执行详情失败: {e}", exc_info=True)
            raise
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                # 总执行次数
                async with db.execute("SELECT COUNT(*) FROM execution_history") as cursor:
                    total_executions = (await cursor.fetchone())[0]
                
                # 成功执行次数
                async with db.execute("SELECT COUNT(*) FROM execution_history WHERE success = 1") as cursor:
                    successful_executions = (await cursor.fetchone())[0]
                
                # 失败执行次数
                failed_executions = total_executions - successful_executions
                
                # 用户数量
                async with db.execute("SELECT COUNT(DISTINCT sender_id) FROM execution_history") as cursor:
                    unique_users = (await cursor.fetchone())[0]
                
                # 最近7天执行次数
                async with db.execute("""
                    SELECT COUNT(*) FROM execution_history 
                    WHERE created_at >= datetime('now', '-7 days')
                """) as cursor:
                    recent_executions = (await cursor.fetchone())[0]
                
                return {
                    'total_executions': total_executions,
                    'successful_executions': successful_executions,
                    'failed_executions': failed_executions,
                    'success_rate': round(successful_executions / total_executions * 100, 2) if total_executions > 0 else 0,
                    'unique_users': unique_users,
                    'recent_executions': recent_executions
                }
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}", exc_info=True)
            raise