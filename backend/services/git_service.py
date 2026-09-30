"""Git 追踪服务 — 提供文件级变更追踪和提交分析"""

import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Git 仓库配置
GIT_REPOS: Dict[str, str] = {
    "github": r"D:\研\土木水利\论文\代码\github",
    "backend": r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\backend",
    "frontend": r"D:\python\pythonProject\AI\AI agent\cpdv-dashboard-web\frontend",
}


def get_commit_files(repo_path: str, commit_sha: str) -> List[str]:
    """获取提交修改的文件列表"""
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'diff', '--name-only', f'{commit_sha}^', commit_sha],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        return [f.strip() for f in result.stdout.split('\n') if f.strip()]
    except Exception:
        return []


def get_recent_commits(repo_path: str, max_commits: int = 20) -> List[Dict[str, Any]]:
    """获取最近提交及文件变更"""
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'log', f'--max-count={max_commits}',
             '--pretty=format:%H|%an|%ad|%s', '--date=iso'],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('|', 3)
            if len(parts) >= 4:
                sha, author, date, message = parts[0], parts[1], parts[2], '|'.join(parts[3:])
                files = get_commit_files(repo_path, sha)
                commits.append({
                    'sha': sha,
                    'short_sha': sha[:8],
                    'author': author,
                    'date': date,
                    'message': message.strip(),
                    'files': files,
                    'file_count': len(files),
                })
        return commits
    except Exception as e:
        return []


def get_file_history(repo_path: str, file_path: str, max_commits: int = 10) -> List[Dict[str, Any]]:
    """获取单个文件的提交历史"""
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'log', f'--max-count={max_commits}',
             '--pretty=format:%H|%an|%ad|%s', '--date=iso', '--', file_path],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        commits = []
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('|', 3)
            if len(parts) >= 4:
                sha, author, date, message = parts[0], parts[1], parts[2], '|'.join(parts[3:])
                commits.append({
                    'sha': sha,
                    'short_sha': sha[:8],
                    'author': author,
                    'date': date,
                    'message': message.strip(),
                })
        return commits
    except Exception:
        return []


def compare_commits(repo_path: str, sha1: str, sha2: str) -> Dict[str, Any]:
    """比较两个提交的差异"""
    try:
        # Get diff stats
        stats_result = subprocess.run(
            ['git', '-C', repo_path, 'diff', '--stat', f'{sha1}..{sha2}'],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        
        # Get actual diff
        diff_result = subprocess.run(
            ['git', '-C', repo_path, 'diff', f'{sha1}..{sha2}'],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        
        # Parse stats
        lines = stats_result.stdout.strip().split('\n')
        total_insertions = 0
        total_deletions = 0
        files_changed = []
        
        for line in lines:
            if 'file' in line.lower() or '.' in line:
                parts = line.split('|')
                if len(parts) >= 2:
                    file_part = parts[0].strip()
                    if file_part and not file_part.startswith('---'):
                        files_changed.append(file_part)
        
        return {
            'base': sha1[:8],
            'target': sha2[:8],
            'files_changed': len(files_changed),
            'insertions': total_insertions,
            'deletions': total_deletions,
            'diff': diff_result.stdout[:5000],
        }
    except Exception as e:
        return {'error': str(e)}


def get_repo_status(repo_path: str) -> Dict[str, Any]:
    """获取仓库状态（是否有未提交的更改）"""
    try:
        status_result = subprocess.run(
            ['git', '-C', repo_path, 'status', '--porcelain'],
            capture_output=True,
            text=True,
            timeout=10,
            encoding='utf-8',
            errors='replace'
        )
        
        lines = [l for l in status_result.stdout.split('\n') if l.strip()]
        
        modified = []
        added = []
        deleted = []
        untracked = []
        
        for line in lines:
            if len(line) >= 2:
                status = line[:2]
                filepath = line[3:]
                if status.startswith('M'):
                    modified.append(filepath)
                elif status.startswith('A'):
                    added.append(filepath)
                elif status.startswith('D'):
                    deleted.append(filepath)
                elif status.startswith('??'):
                    untracked.append(filepath)
        
        branch_result = subprocess.run(
            ['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )
        branch = branch_result.stdout.strip()
        
        latest_result = subprocess.run(
            ['git', '-C', repo_path, 'log', '-1', '--pretty=format:%H|%ad|%s', '--date=short'],
            capture_output=True,
            text=True,
            timeout=5,
            encoding='utf-8',
            errors='replace'
        )
        latest_parts = latest_result.stdout.split('|') if latest_result.stdout.strip() else ['', '', '']
        
        return {
            'branch': branch,
            'latest_commit': latest_parts[0][:8] if latest_parts[0] else '',
            'latest_date': latest_parts[1] if len(latest_parts) > 1 else '',
            'latest_message': latest_parts[2].strip() if len(latest_parts) > 2 else '',
            'modified': modified,
            'added': added,
            'deleted': deleted,
            'untracked': untracked,
            'total_changes': len(modified) + len(added) + len(deleted) + len(untracked),
        }
    except Exception as e:
        return {'error': str(e)}


def get_all_repo_statuses() -> Dict[str, Any]:
    """获取所有仓库的状态"""
    result = {'repos': {}, 'summary': {}}
    
    total_modified = 0
    total_added = 0
    total_untracked = 0
    
    for name, path in GIT_REPOS.items():
        if not Path(path).exists():
            continue
        status = get_repo_status(path)
        result['repos'][name] = status
        
        if 'error' not in status:
            total_modified += len(status.get('modified', []))
            total_added += len(status.get('added', []))
            total_untracked += len(status.get('untracked', []))
    
    result['summary'] = {
        'total_repos': len(result['repos']),
        'total_modified': total_modified,
        'total_added': total_added,
        'total_untracked': total_untracked,
    }
    
    return result
