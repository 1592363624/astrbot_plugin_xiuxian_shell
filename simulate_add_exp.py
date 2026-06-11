"""完整模拟 add_experience 逻辑"""
import sqlite3
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

db_path = r'D:\WorkSpace\PyCharmWorkspace\AstrBot\data\plugin_data\astrbot_plugin_xiuxian_shell\xiuxian.db'

print("=" * 60)
print("完整模拟 add_experience 逻辑")
print("=" * 60)

# 模拟 add_experience 的完整逻辑
async def simulate_add_experience():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 获取玩家当前状态
    player_id = 'a5f67c5a-d583-4971-ab3c-06e5ce8e438a'
    cursor.execute("SELECT experience, temp_experience, realm_id FROM players WHERE id = ?", (player_id,))
    player = cursor.fetchone()
    
    if not player:
        print("未找到玩家")
        return
    
    old_exp = player[0]
    old_temp = player[1]
    realm_id = player[2]
    
    print(f"\n1. 获取玩家状态:")
    print(f"   修为: {old_exp}")
    print(f"   临时修为: {old_temp}")
    print(f"   境界ID: {realm_id}")
    
    # 模拟 get_exp_cap_for_realm
    # realm_001 (凡人) 的下一境界是 realm_002 (炼气初期)，需要 100 修为
    exp_cap = 100
    
    print(f"\n2. 修为上限: {exp_cap}")
    
    # 模拟 add_experience
    exp_change = 1
    
    print(f"\n3. 执行 add_experience: exp_change={exp_change}")
    
    # 执行与 add_experience 相同的 SQL
    cursor.execute("""
        UPDATE players
        SET experience = MIN(MAX(0, experience + ?), ?),
            temp_experience = temp_experience + MAX(0, experience + ? - ?),
            updated_at = datetime('now')
        WHERE id = ?
    """, (exp_change, exp_cap, exp_change, exp_cap, player_id))
    
    conn.commit()
    
    # 验证结果
    cursor.execute("SELECT experience, temp_experience FROM players WHERE id = ?", (player_id,))
    updated = cursor.fetchone()
    new_exp = updated[0]
    new_temp = updated[1]
    
    print(f"\n4. 更新后:")
    print(f"   修为: {new_exp} (差值: {new_exp - old_exp})")
    print(f"   临时修为: {new_temp} (差值: {new_temp - old_temp})")
    
    # 回滚测试
    cursor.execute("""
        UPDATE players
        SET experience = ?,
            temp_experience = ?,
            updated_at = datetime('now')
        WHERE id = ?
    """, (old_exp, old_temp, player_id))
    conn.commit()
    
    print(f"\n5. 已回滚到原始值: 修为={old_exp}, 临时修为={old_temp}")
    
    conn.close()

simulate_add_experience()
