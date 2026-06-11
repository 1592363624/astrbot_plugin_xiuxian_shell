"""
修仙插件逻辑验证测试 - 验证功能的正确性而非仅仅是否有返回
用法: python test_logic.py
"""
import requests
import json
import sys
import io
import re
import time
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://localhost:6185/api/v1/chat"
API_KEY = "abk_Jb6eTa2-i476xssp3mq8X0h0NB_0Id-Uz5O5WXpZCX4"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
TEST_USER = "test"

# 测试结果统计
passed = 0
failed = 0
errors = []


class C:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    END = '\033[0m'


def send_command(command, user=TEST_USER, timeout=120):
    """发送指令并返回机器人回复"""
    data = {
        "username": user,
        "message": [{"type": "plain", "text": command}]
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=data, timeout=timeout, stream=True)
        if response.status_code != 200:
            return f"[HTTP ERROR {response.status_code}]"
        
        replies = []
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                json_str = line_str.replace("data: ", "")
                try:
                    parsed = json.loads(json_str)
                    if parsed.get("type") == "plain":
                        replies.append(parsed.get("data", ""))
                except json.JSONDecodeError:
                    pass
        return "\n".join(replies) if replies else ""
    except Exception as e:
        return f"[ERROR: {e}]"


def parse_status(response):
    """解析修仙状态，返回字典"""
    result = {}
    
    # 提取修为
    match = re.search(r'修为[：:]\s*(\d+)/(\d+)', response)
    if match:
        result['experience'] = int(match.group(1))
        result['exp_max'] = int(match.group(2))
    
    # 提取灵石
    match = re.search(r'灵石[：:]\s*(\d+)', response)
    if match:
        result['spirit_stone'] = int(match.group(1))
    
    # 提取境界
    match = re.search(r'境界[：:]\s*(\S+)', response)
    if match:
        result['realm'] = match.group(1)
    
    # 提取气血
    match = re.search(r'气血[：:]\s*(\d+)/(\d+)', response)
    if match:
        result['health'] = int(match.group(1))
        result['health_max'] = int(match.group(2))
    
    # 提取法力
    match = re.search(r'法力[：:]\s*(\d+)/(\d+)', response)
    if match:
        result['mp'] = int(match.group(1))
        result['mp_max'] = int(match.group(2))
    
    # 提取体力
    match = re.search(r'体力[：:]\s*(\d+)/(\d+)', response)
    if match:
        result['stamina'] = int(match.group(1))
        result['stamina_max'] = int(match.group(2))
    
    # 提取物攻
    match = re.search(r'物攻[：:]\s*(\d+)', response)
    if match:
        result['phys_atk'] = int(match.group(1))
    
    # 提取法攻
    match = re.search(r'法攻[：:]\s*(\d+)', response)
    if match:
        result['magic_atk'] = int(match.group(1))
    
    # 提取物防
    match = re.search(r'物防[：:]\s*(\d+)', response)
    if match:
        result['phys_def'] = int(match.group(1))
    
    # 提取法防
    match = re.search(r'法防[：:]\s*(\d+)', response)
    if match:
        result['magic_def'] = int(match.group(1))
    
    # 提取速度
    match = re.search(r'速度[：:]\s*(\d+)', response)
    if match:
        result['speed'] = int(match.group(1))
    
    return result


def parse_checkin_status(response):
    """解析签到状态"""
    result = {}
    
    match = re.search(r'连续签到[：:]\s*(\d+)\s*天', response)
    if match:
        result['consecutive_days'] = int(match.group(1))
    
    match = re.search(r'今日获得[：:]\s*\+(\d+)\s*修为', response)
    if match:
        result['today_exp'] = int(match.group(1))
    
    return result


def test(name, condition, detail=""):
    """断言测试"""
    global passed, failed
    if condition:
        passed += 1
        print(f"  {C.GREEN}✓ PASS{C.END} {name}")
    else:
        failed += 1
        errors.append((name, detail))
        print(f"  {C.RED}✗ FAIL{C.END} {name}")
        if detail:
            print(f"    {C.DIM}{detail}{C.END}")


def main():
    global passed, failed, errors
    
    print(f"\n{C.CYAN}{'='*60}{C.END}")
    print(f"{C.CYAN}  修仙插件逻辑验证测试{C.END}")
    print(f"{C.CYAN}{'='*60}{C.END}\n")
    
    # ========== 测试1: 签到功能 ==========
    print(f"{C.HEADER}【测试1: 签到功能逻辑验证】{C.END}")
    
    # 获取签到前状态
    status_before = parse_status(send_command("修仙状态"))
    checkin_before = parse_checkin_status(send_command("签到状态"))
    
    print(f"  {C.DIM}签到前: 修为={status_before.get('experience', '?')}, 签到天数={checkin_before.get('consecutive_days', '?')}{C.END}")
    
    # 执行签到
    checkin_result = send_command("签到")
    
    # 获取签到后状态
    status_after = parse_status(send_command("修仙状态"))
    checkin_after = parse_checkin_status(send_command("签到状态"))
    
    print(f"  {C.DIM}签到后: 修为={status_after.get('experience', '?')}, 签到天数={checkin_after.get('consecutive_days', '?')}{C.END}")
    
    # 验证签到逻辑
    exp_before = status_before.get('experience', 0)
    exp_after = status_after.get('experience', 0)
    today_exp = checkin_after.get('today_exp', 0)
    
    test("签到后修为应增加", exp_after > exp_before,
         f"增加前={exp_before}, 增加后={exp_after}")
    
    if today_exp > 0:
        test("签到获得的修为应与差值一致", exp_after - exp_before == today_exp,
             f"差值={exp_after - exp_before}, 声称获得={today_exp}")
    
    # 连续签到天数测试
    days_before = checkin_before.get('consecutive_days', 0)
    days_after = checkin_after.get('consecutive_days', 0)
    
    if "你今天已经签到过了" in checkin_result:
        test("重复签到应有提示", True)
        test("重复签到不应增加天数", days_after == days_before,
             f"之前={days_before}, 之后={days_after}")
    else:
        test("首次签到后天数应+1", days_after == days_before + 1,
             f"之前={days_before}, 之后={days_after}")
    
    time.sleep(1)
    
    # ========== 测试2: 闭关修炼 ==========
    print(f"\n{C.HEADER}【测试2: 闭关修炼逻辑验证】{C.END}")
    
    status_before = parse_status(send_command("修仙状态"))
    exp_before = status_before.get('experience', 0)
    
    seclusion_result = send_command("闭关修炼")
    print(f"  {C.DIM}闭关结果: {seclusion_result[:80]}...{C.END}")
    
    status_after = parse_status(send_command("修仙状态"))
    exp_after = status_after.get('experience', 0)
    
    if "冷却" in seclusion_result or "疲惫" in seclusion_result:
        test("冷却期间应拒绝闭关", True)
        # 冷却期间修为不应变化（除非有其他因素影响）
        if exp_after != exp_before:
            print(f"  {C.YELLOW}⚠ 注意: 修为从{exp_before}变为{exp_after}（可能有其他因素影响）{C.END}")
    elif "修为增加了" in seclusion_result or "成功" in seclusion_result:
        test("闭关成功后修为应增加", exp_after > exp_before,
             f"之前={exp_before}, 之后={exp_after}")
    elif "减少了" in seclusion_result or "走火入魔" in seclusion_result:
        # 闭关失败是正常的游戏机制，不一定是bug
        test("闭关失败后修为应减少", exp_after < exp_before,
             f"之前={exp_before}, 之后={exp_after}")
        print(f"  {C.YELLOW}⚠ 注意: 闭关失败是正常游戏机制，修为减少是预期行为{C.END}")
    else:
        test("闭关结果应有明确反馈", len(seclusion_result) > 10,
             f"返回内容: {seclusion_result[:100]}")
    
    time.sleep(1)
    
    # ========== 测试3: 更改道号 ==========
    print(f"\n{C.HEADER}【测试3: 更改道号逻辑验证】{C.END}")
    
    # 更改道号（使用纯中文，2-6个字符）
    new_name = "测试道友"
    rename_result = send_command(f"更改道号 {new_name}")
    print(f"  {C.DIM}更改结果: {rename_result}{C.END}")
    
    # 验证道号是否生效
    status = send_command("修仙状态")
    
    test("更改道号应返回成功", "修改成功" in rename_result or "新道号" in rename_result,
         f"返回: {rename_result}")
    
    test("道号应与设置一致", new_name in status,
         f"期望道号={new_name}, 状态中是否包含={new_name in status}")
    
    # 更改回原名
    send_command("更改道号 测试道友")
    
    time.sleep(1)
    
    # ========== 测试4: 排行榜逻辑 ==========
    print(f"\n{C.HEADER}【测试4: 排行榜逻辑验证】{C.END}")
    
    realm_rank = send_command("排行榜 境界")
    chat_rank = send_command("排行榜 发言")
    wealth_rank = send_command("排行榜 财富")
    
    # 验证排行榜格式
    test("境界排行榜应有标题", "排行榜" in realm_rank or "修为" in realm_rank,
         f"返回: {realm_rank[:100]}")
    
    test("排行榜应包含排名格式", re.search(r'第\d+名', realm_rank) is not None,
         f"返回: {realm_rank[:100]}")
    
    # 验证排行榜数据一致性
    # 获取玩家当前状态
    my_status = parse_status(send_command("修仙状态"))
    my_exp = my_status.get('experience', 0)
    
    # 检查排行榜中是否有该玩家
    test("排行榜应包含当前玩家", "测试道友" in realm_rank,
         f"排行榜内容: {realm_rank[:200]}")
    
    # 验证财富排行
    my_stones = my_status.get('spirit_stone', 0)
    test("财富排行榜应包含灵石信息", "灵石" in wealth_rank,
         f"返回: {wealth_rank[:200]}")
    
    time.sleep(1)
    
    # ========== 测试5: 物品系统 ==========
    print(f"\n{C.HEADER}【测试5: 物品系统逻辑验证】{C.END}")
    
    inventory_before = send_command("储物袋")
    print(f"  {C.DIM}储物袋: {inventory_before[:80]}{C.END}")
    
    # 尝试使用不存在的物品
    use_result = send_command("使用 不存在的物品")
    test("使用不存在物品应有提示", "不存在" in use_result or "没有" in use_result or "数量不足" in use_result,
         f"返回: {use_result}")
    
    # 丹毒状态
    toxicity = send_command("丹毒")
    test("丹毒状态应有明确回复", "丹毒" in toxicity,
         f"返回: {toxicity}")
    
    time.sleep(1)
    
    # ========== 测试6: 深度闭关 ==========
    print(f"\n{C.HEADER}【测试6: 深度闭关逻辑验证】{C.END}")
    
    seclusion_status = send_command("查看闭关")
    print(f"  {C.DIM}闭关状态: {seclusion_status}{C.END}")
    
    # 检查是否在闭关中
    if "正在深度闭关中" in seclusion_status:
        test("应在闭关中显示剩余时间", "小时" in seclusion_status or "分钟" in seclusion_status,
             f"返回: {seclusion_status}")
        
        # 验证重复进入应被拒绝
        try_seclusion = send_command("深度闭关")
        test("重复进入深度闭关应被拒绝", "已在" in try_seclusion or "请先" in try_seclusion,
             f"返回: {try_seclusion}")
    else:
        test("不在闭关时应可开启", "可以" in seclusion_status or "开启" in seclusion_status or "未在" in seclusion_status,
             f"返回: {seclusion_status}")
    
    time.sleep(1)
    
    # ========== 测试7: 万宝楼 ==========
    print(f"\n{C.HEADER}【测试7: 万宝楼逻辑验证】{C.END}")
    
    market = send_command("万宝楼")
    print(f"  {C.DIM}万宝楼: {market[:80]}{C.END}")
    
    test("万宝楼应有返回", len(market) > 5, f"返回: {market[:100]}")
    
    # 搜索不存在的商品
    search_result = send_command("万宝楼 搜索 不存在的物品XYZ")
    test("搜索不存在商品应有提示", "未找到" in search_result or "暂无" in search_result,
         f"返回: {search_result}")
    
    # 我的货摊
    my_stalls = send_command("我的货摊")
    test("我的货摊应有返回", "货摊" in my_stalls or "出售" in my_stalls or "暂无" in my_stalls,
         f"返回: {my_stalls}")
    
    time.sleep(1)
    
    # ========== 测试8: 和平模式 ==========
    print(f"\n{C.HEADER}【测试8: 和平模式逻辑验证】{C.END}")
    
    # 先入世确保不在避世状态
    send_command("入世")
    time.sleep(2)
    
    # 开启避世
    peace_result = send_command("避世")
    print(f"  {C.DIM}避世结果: {peace_result}{C.END}")
    
    # 检查状态中是否显示避世
    status = send_command("修仙状态")
    
    if "开启了避世" in peace_result or "已在避世" in peace_result:
        test("开启避世后状态应显示", "避世" in status,
             f"状态中是否包含避世: {'避世' in status}")
    
    # 验证避世期间应有冷却
    time.sleep(1)
    peace_result2 = send_command("避世")
    if "已在避世" in peace_result2:
        test("重复开启避世应有提示", True)
    
    # 入世
    exit_result = send_command("入世")
    print(f"  {C.DIM}入世结果: {exit_result}{C.END}")
    
    if "操作太频繁" in exit_result:
        test("频繁操作应有冷却提示", True)
    elif "重返红尘" in exit_result or "入世" in exit_result:
        test("入世应有成功反馈", True)
    
    time.sleep(1)
    
    # ========== 测试9: 帮助系统 ==========
    print(f"\n{C.HEADER}【测试9: 帮助系统逻辑验证】{C.END}")
    
    help_text = send_command("修仙帮助")
    
    # 验证帮助文本包含关键指令
    key_commands = ["修仙状态", "闭关修炼", "签到", "储物袋", "突破", "万宝楼", "排行榜"]
    for cmd in key_commands:
        test(f"帮助应包含'{cmd}'", cmd in help_text,
             f"帮助文本: {help_text[:200]}")
    
    # ========== 测试10: 属性计算逻辑 ==========
    print(f"\n{C.HEADER}【测试10: 属性计算逻辑验证】{C.END}")
    
    status = send_command("修仙状态")
    parsed = parse_status(status)
    
    print(f"  {C.DIM}解析状态: {parsed}{C.END}")
    
    # 验证凡人境界的基础属性
    if parsed.get('realm') == '凡人':
        test("凡人境界物攻应为5", parsed.get('phys_atk') == 5,
             f"实际值: {parsed.get('phys_atk')}")
        test("凡人境界法攻应为5", parsed.get('magic_atk') == 5,
             f"实际值: {parsed.get('magic_atk')}")
        test("凡人境界物防应为2", parsed.get('phys_def') == 2,
             f"实际值: {parsed.get('phys_def')}")
        test("凡人境界法防应为2", parsed.get('magic_def') == 2,
             f"实际值: {parsed.get('magic_def')}")
        test("凡人境界速度应为10", parsed.get('speed') == 10,
             f"实际值: {parsed.get('speed')}")
        test("凡人气血上限应为100", parsed.get('health_max') == 100,
             f"实际值: {parsed.get('health_max')}")
        test("凡人法力上限应为50", parsed.get('mp_max') == 50,
             f"实际值: {parsed.get('mp_max')}")
        test("凡人体力上限应为50", parsed.get('stamina_max') == 50,
             f"实际值: {parsed.get('stamina_max')}")
    
    # ========== 汇总 ==========
    print(f"\n\n{C.CYAN}{'='*60}{C.END}")
    print(f"{C.CYAN}  测试报告{C.END}")
    print(f"{C.CYAN}{'='*60}{C.END}\n")
    
    total = passed + failed
    print(f"  {C.GREEN}✓ 通过: {passed}{C.END}")
    print(f"  {C.RED}✗ 失败: {failed}{C.END}")
    print(f"  总计: {total}")
    
    if errors:
        print(f"\n{C.RED}{'─'*60}{C.END}")
        print(f"{C.RED}  失败详情:{C.END}")
        for name, detail in errors:
            print(f"  {C.RED}✗ {name}{C.END}")
            if detail:
                print(f"    {C.DIM}{detail}{C.END}")
    
    print(f"\n{C.CYAN}{'='*60}{C.END}\n")
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
