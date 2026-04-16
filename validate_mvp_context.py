#!/usr/bin/env python3
"""
MVP Context System Validator

驗證新結構是否正確建立及可用性。
"""

import os
import json
from pathlib import Path

def validate_structure():
    """驗證 .github/ 結構完整性"""
    
    required_files = {
        '.github/copilot-instructions.md': 'Global instructions',
        '.github/prompts/memory-bank.instructions.md': 'Memory bank rules',
        '.github/prompts/pack-context.prompt.md': 'Context packing tool',
        '.github/prompts/always-ask-next.skill.md': 'Always-ask-next skill',
        '.github/skills/always-ask-next/SKILL.md': 'Skill metadata',
        '.github/memory-bank/README.md': 'Memory bank index',
        '.github/memory-bank/artifact-rules.md': 'Artifact rules',
        '.github/memory-bank/workflow-gates.md': 'Guard validator rules',
        '.github/memory-bank/prompt-patterns.md': 'Prompt patterns',
        '.github/memory-bank/project-facts.md': 'Project facts',
    }
    
    root = Path('.')
    results = {'pass': [], 'fail': []}
    
    for file, desc in required_files.items():
        path = root / file
        if path.exists():
            results['pass'].append(f'✅ {file} ({desc})')
        else:
            results['fail'].append(f'❌ {file} ({desc})')
    
    return results

def check_claude_optimization():
    """驗證 CLAUDE.md 是否已優化"""
    
    path = Path('CLAUDE.md')
    if not path.exists():
        return False, "CLAUDE.md not found"
    
    content = path.read_text(encoding='utf-8')
    lines = content.split('\n')
    
    # 檢查長度
    if len(lines) > 500:
        status = "⚠️ CLAUDE.md 仍過厚（建議 <400 行）"
        return False, status
    
    # 檢查關鍵指標已存在
    checks = [
        ('# CLAUDE.md — 協調者入口檔', 'Header rewrite'),
        ('見 .github/memory-bank/', 'Memory bank references'),
        ('見 docs/', 'Proper doc delegation'),
    ]
    
    for check_str, desc in checks:
        if check_str not in content:
            return False, f"Missing: {desc}"
    
    return True, f"✅ CLAUDE.md 優化完成（{len(lines)} 行）"

def main():
    print("=" * 60)
    print("MVP Context System Validator")
    print("=" * 60)
    
    # 1. Check structure
    print("\n[1/3] 檢查檔案結構...")
    results = validate_structure()
    
    for item in results['pass']:
        print(f"      {item}")
    
    if results['fail']:
        print("\n      ❌ 缺失檔案：")
        for item in results['fail']:
            print(f"      {item}")
        return False
    
    # 2. Check CLAUDE.md
    print("\n[2/3] 檢查 CLAUDE.md 優化...")
    passed, msg = check_claude_optimization()
    print(f"      {msg}")
    
    if not passed:
        return False
    
    # 3. Summary
    print("\n[3/3] 驗證摘要...")
    print(f"""
    ✅ 所有新檔案已建立
    ✅ CLAUDE.md 已優化
    ✅ .github/ 結構完整
    
    後續步驟：
    1. 在 VS Code 中重新載入窗口（Cmd+Shift+P → Developer: Reload Window）
    2. 測試 copilot-instructions.md 是否被載入
    3. 在 Chat 中試試：
       - "read /memories/repo/artifact-rules.md"
       - "use pack-context to organize TASK-950"
       - "show me the always-ask-next skill"
    4. git add，commit，push
    """)
    
    return True

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
