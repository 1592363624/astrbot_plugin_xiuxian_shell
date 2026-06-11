"""
修仙插件功能测试工具 - 可视化版本
用法: python test_tool.py [指令]
示例: python test_tool.py 签到
      python test_tool.py 全部
      python test_tool.py status
"""
import requests
import json
import sys
import io
import time
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

API_URL = "http://localhost:6185/api/v1/chat"
API_KEY = "abk_Jb6eTa2-i476xssp3mq8X0h0NB_0Id-Uz5O5WXpZCX4"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {API_KEY}"
}

# 颜色定义
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

def banner():
    print(f"""
{C.CYAN}╔══════════════════════════════════════════════╗
║     修仙插件功能测试工具 v1.0               ║
╚══════════════════════════════════════════════╝{C.END}

{C.DIM}用法:
  python test_tool.py <指令>       测试单个指令
  python test_tool.py 全部         测试所有功能
  python test_tool.py status       查看当前状态
  python test_tool.py 注册 <ID>    注册新玩家
  python test_tool.py 给予 <物品ID> <数量>  给玩家物品{C.END}
""")

def send_command(command, user="test", timeout=120, show_raw=False):
    """发送指令并返回机器人回复"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    
    print(f"\n{C.DIM}[{timestamp}]{C.END} {C.BLUE}▶ 发送指令:{C.END} {C.BOLD}{command}{C.END}")
    print(f"{C.DIM}{'─'*50}{C.END}")
    
    data = {
        "username": user,
        "message": [{"type": "plain", "text": command}]
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(API_URL, headers=HEADERS, json=data, timeout=timeout, stream=True)
        elapsed = time.time() - start_time
        
        if response.status_code != 200:
            print(f"{C.RED}✗ HTTP错误 {response.status_code}{C.END}")
            return f"[ERROR] HTTP {response.status_code}"
        
        replies = []
        raw_messages = []
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                json_str = line_str.replace("data: ", "")
                try:
                    parsed = json.loads(json_str)
                    raw_messages.append(parsed)
                    msg_type = parsed.get("type")
                    
                    if msg_type == "session_id":
                        if show_raw:
                            print(f"{C.DIM}  ↳ 会话ID: {parsed.get('session_id')}{C.END}")
                    elif msg_type == "user_message_saved":
                        if show_raw:
                            print(f"{C.DIM}  ↳ 用户消息已保存{C.END}")
                    elif msg_type == "plain":
                        text = parsed.get("data", "")
                        replies.append(text)
                    elif msg_type == "message_saved":
                        if show_raw:
                            print(f"{C.DIM}  ↳ 机器人消息已保存{C.END}")
                    elif msg_type == "end":
                        pass
                    elif msg_type == "error":
                        print(f"{C.RED}  ✗ 错误: {parsed.get('data', '')}{C.END}")
                except json.JSONDecodeError:
                    pass
        
        elapsed = time.time() - start_time
        
        # 输出回复
        reply_text = "\n".join(replies) if replies else "[无回复]"
        
        # 检测错误
        if "出现异常" in reply_text or "[ERROR]" in reply_text:
            print(f"{C.RED}{reply_text}{C.END}")
            return f"[ERROR] {reply_text}"
        elif reply_text == "[无回复]":
            print(f"{C.YELLOW}  ⚠ 无回复{C.END}")
            return reply_text
        else:
            print(f"{C.GREEN}{reply_text}{C.END}")
        
        print(f"{C.DIM}{'─'*50}{C.END}")
        print(f"{C.DIM}  ⏱ 耗时: {elapsed:.2f}s{C.END}")
        
        return reply_text
        
    except requests.exceptions.Timeout:
        print(f"{C.RED}✗ 请求超时 ({timeout}s){C.END}")
        return "[TIMEOUT]"
    except requests.exceptions.ConnectionError:
        print(f"{C.RED}✗ 无法连接到 AstrBot (http://localhost:6185){C.END}")
        return "[CONNECTION_ERROR]"
    except Exception as e:
        print(f"{C.RED}✗ 错误: {e}{C.END}")
        return f"[ERROR] {e}"

def test_all():
    """测试所有功能"""
    test_cases = [
        ("基础功能", [
            ("修仙状态", "修仙状态"),
            ("修仙帮助", "修仙帮助"),
            ("签到", "签到"),
            ("签到状态", "签到状态"),
            ("签到排行", "签到排行"),
        ]),
        ("修炼相关", [
            ("闭关修炼", "闭关修炼"),
            ("深度闭关", "深度闭关"),
            ("查看闭关", "查看闭关"),
        ]),
        ("物品系统", [
            ("储物袋", "储物袋"),
            ("丹毒", "丹毒"),
            ("使用物品", "使用 聚灵丹"),
            ("服用丹药", "服用 聚灵丹"),
        ]),
        ("排行榜", [
            ("境界排行", "排行榜 境界"),
            ("发言排行", "排行榜 发言"),
            ("财富排行", "排行榜 财富"),
        ]),
        ("万宝楼", [
            ("浏览万宝楼", "万宝楼"),
            ("翻页", "万宝楼 2"),
            ("搜索商品", "万宝楼 搜索 聚灵丹"),
            ("筛选商品", "万宝楼 筛选 丹药"),
            ("我的货摊", "我的货摊"),
        ]),
        ("突破系统", [
            ("尝试突破", "突破"),
        ]),
        ("和平模式", [
            ("避世", "避世"),
            ("入世", "入世"),
        ]),
        ("其他功能", [
            ("更改道号", "更改道号 测试道友"),
        ]),
    ]
    
    results = []
    total = sum(len(cmds) for _, cmds in test_cases)
    current = 0
    
    print(f"\n{C.CYAN}{'═'*60}{C.END}")
    print(f"{C.CYAN}  开始全功能测试 (共{total}个指令){C.END}")
    print(f"{C.CYAN}{'═'*60}{C.END}")
    
    for category, commands in test_cases:
        print(f"\n{C.HEADER}【{category}】{C.END}")
        
        for name, cmd in commands:
            current += 1
            print(f"\n{C.BOLD}[{current}/{total}]{C.END}", end="")
            result = send_command(cmd, show_raw=False)
            
            is_error = "[ERROR]" in result or "[TIMEOUT]" in result or "[无回复]" in result
            status = f"{C.RED}✗{C.END}" if is_error else f"{C.GREEN}✓{C.END}"
            results.append((name, cmd, result, is_error))
            
            time.sleep(0.5)  # 避免请求过快
    
    # 汇总报告
    print(f"\n\n{C.CYAN}{'═'*60}{C.END}")
    print(f"{C.CYAN}  测试报告{C.END}")
    print(f"{C.CYAN}{'═'*60}{C.END}\n")
    
    passed = sum(1 for _, _, _, err in results if not err)
    failed = sum(1 for _, _, _, err in results if err)
    
    print(f"  {C.GREEN}✓ 通过: {passed}{C.END}")
    print(f"  {C.RED}✗ 失败: {failed}{C.END}")
    print(f"  总计: {total}")
    
    if failed > 0:
        print(f"\n{C.RED}{'─'*60}{C.END}")
        print(f"{C.RED}  失败项:{C.END}")
        for name, cmd, result, is_error in results:
            if is_error:
                print(f"  {C.RED}✗ {name} ({cmd}){C.END}")
                # 截取错误信息
                error_msg = result[:100] if len(result) > 100 else result
                print(f"    {C.DIM}{error_msg}{C.END}")
    
    print(f"\n{C.CYAN}{'═'*60}{C.END}\n")

def test_status():
    """查看当前状态"""
    send_command("修仙状态")
    send_command("储物袋")
    send_command("签到状态")
    send_command("查看闭关")

def main():
    banner()
    
    if len(sys.argv) < 2:
        print(f"{C.YELLOW}请输入指令，例如: python test_tool.py 签到{C.END}")
        print(f"{C.DIM}输入 'help' 查看帮助{C.END}")
        
        # 交互模式
        while True:
            try:
                cmd = input(f"\n{C.CYAN}修仙> {C.END}").strip()
                if not cmd:
                    continue
                if cmd in ("quit", "exit", "q"):
                    print("再见！")
                    break
                elif cmd == "help":
                    banner()
                elif cmd == "全部":
                    test_all()
                elif cmd == "status":
                    test_status()
                else:
                    send_command(cmd)
            except KeyboardInterrupt:
                print("\n再见！")
                break
        return
    
    # 命令行模式
    arg = sys.argv[1]
    
    if arg == "全部":
        test_all()
    elif arg == "status":
        test_status()
    elif arg == "help":
        banner()
    else:
        # 测试单个指令
        send_command(arg, show_raw=True)

if __name__ == "__main__":
    main()
