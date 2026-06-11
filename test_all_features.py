"""修仙插件全功能测试脚本"""
import requests
import json
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://localhost:6185/api/v1/chat"
API_KEY = "abk_Jb6eTa2-i476xssp3mq8X0h0NB_0Id-Uz5O5WXpZCX4"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}
TEST_USER = "test"

def send_command(command, user=TEST_USER, timeout=120):
    """发送指令并返回机器人回复"""
    data = {
        "username": user,
        "message": [{"type": "plain", "text": command}]
    }
    try:
        response = requests.post(API_URL, headers=HEADERS, json=data, timeout=timeout, stream=True)
        if response.status_code != 200:
            return f"[ERROR] HTTP {response.status_code}: {response.text[:200]}"
        
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
        return "\n".join(replies) if replies else "[无回复]"
    except requests.exceptions.Timeout:
        return "[TIMEOUT]"
    except Exception as e:
        return f"[ERROR] {e}"

def test_command(name, command, user=TEST_USER):
    """测试单个指令"""
    print(f"\n{'='*50}")
    print(f"测试: {name}")
    print(f"指令: {command}")
    print(f"-"*50)
    result = send_command(command, user)
    print(f"回复:\n{result}")
    time.sleep(1)
    return result

def main():
    print("开始修仙插件全功能测试...\n")
    
    results = {}
    
    # 1. 基础功能
    print("\n" + "="*60)
    print("【第一部分：基础功能】")
    print("="*60)
    
    results["修仙状态"] = test_command("修仙状态", "修仙状态")
    results["修仙帮助"] = test_command("修仙帮助", "修仙帮助")
    results["签到"] = test_command("签到", "签到")
    results["签到状态"] = test_command("签到状态", "签到状态")
    results["签到排行"] = test_command("签到排行", "签到排行")
    
    # 2. 修炼相关
    print("\n" + "="*60)
    print("【第二部分：修炼相关】")
    print("="*60)
    
    results["闭关修炼"] = test_command("闭关修炼", "闭关修炼")
    results["深度闭关"] = test_command("深度闭关", "深度闭关")
    results["查看闭关"] = test_command("查看闭关", "查看闭关")
    
    # 3. 物品相关
    print("\n" + "="*60)
    print("【第三部分：物品相关】")
    print("="*60)
    
    results["储物袋"] = test_command("储物袋", "储物袋")
    results["丹毒"] = test_command("丹毒", "丹毒")
    results["使用_聚灵丹"] = test_command("使用聚灵丹", "使用 聚灵丹")
    results["服用_聚灵丹"] = test_command("服用聚灵丹", "服用 聚灵丹")
    
    # 4. 排行榜
    print("\n" + "="*60)
    print("【第四部分：排行榜】")
    print("="*60)
    
    results["排行榜_境界"] = test_command("排行榜_境界", "排行榜 境界")
    results["排行榜_发言"] = test_command("排行榜_发言", "排行榜 发言")
    results["排行榜_财富"] = test_command("排行榜_财富", "排行榜 财富")
    
    # 5. 万宝楼
    print("\n" + "="*60)
    print("【第五部分：万宝楼】")
    print("="*60)
    
    results["万宝楼"] = test_command("万宝楼", "万宝楼")
    results["万宝楼_第2页"] = test_command("万宝楼_第2页", "万宝楼 2")
    results["万宝楼_搜索"] = test_command("万宝楼_搜索", "万宝楼 搜索 聚灵丹")
    results["万宝楼_筛选"] = test_command("万宝楼_筛选", "万宝楼 筛选 丹药")
    results["我的货摊"] = test_command("我的货摊", "我的货摊")
    
    # 6. 突破相关
    print("\n" + "="*60)
    print("【第六部分：突破相关】")
    print("="*60)
    
    results["突破"] = test_command("突破", "突破")
    
    # 7. 和平模式
    print("\n" + "="*60)
    print("【第七部分：和平模式】")
    print("="*60)
    
    results["避世"] = test_command("避世", "避世")
    results["入世"] = test_command("入世", "入世")
    
    # 8. 更改道号
    print("\n" + "="*60)
    print("【第八部分：其他功能】")
    print("="*60)
    
    results["更改道号"] = test_command("更改道号", "更改道号 测试道友")
    
    # 9. 测试完毕，查看最终状态
    print("\n" + "="*60)
    print("【最终状态检查】")
    print("="*60)
    
    results["最终修仙状态"] = test_command("最终修仙状态", "修仙状态")
    results["最终储物袋"] = test_command("最终储物袋", "储物袋")
    
    # 汇总
    print("\n" + "="*60)
    print("【测试汇总】")
    print("="*60)
    
    issues = []
    for name, result in results.items():
        if "[ERROR]" in result or "[TIMEOUT]" in result or "[无回复]" in result:
            issues.append(f"  ❌ {name}: {result}")
        else:
            print(f"  ✅ {name}: 正常")
    
    if issues:
        print("\n发现问题:")
        for issue in issues:
            print(issue)
    else:
        print("\n所有功能测试通过！")
    
    print(f"\n共测试 {len(results)} 个功能")

if __name__ == "__main__":
    main()
