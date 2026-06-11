"""
修仙插件功能测试工具 - 图形化版本
双击运行即可使用
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import requests
import json
import threading
import time
from datetime import datetime


class XiuxianTestTool:
    """修仙插件图形化测试工具"""

    API_URL = "http://localhost:6185/api/v1/chat"
    API_KEY = "abk_Jb6eTa2-i476xssp3mq8X0h0NB_0Id-Uz5O5WXpZCX4"

    # 预定义的测试指令
    TEST_COMMANDS = {
        "基础功能": [
            ("修仙状态", "修仙状态"),
            ("修仙帮助", "修仙帮助"),
            ("签到", "签到"),
            ("签到状态", "签到状态"),
            ("签到排行", "签到排行"),
        ],
        "修炼相关": [
            ("闭关修炼", "闭关修炼"),
            ("深度闭关", "深度闭关"),
            ("查看闭关", "查看闭关"),
        ],
        "物品系统": [
            ("储物袋", "储物袋"),
            ("丹毒", "丹毒"),
            ("使用物品", "使用 聚灵丹"),
            ("服用丹药", "服用 聚灵丹"),
        ],
        "排行榜": [
            ("境界排行", "排行榜 境界"),
            ("发言排行", "排行榜 发言"),
            ("财富排行", "排行榜 财富"),
        ],
        "万宝楼": [
            ("浏览万宝楼", "万宝楼"),
            ("翻页", "万宝楼 2"),
            ("搜索商品", "万宝楼 搜索 聚灵丹"),
            ("筛选商品", "万宝楼 筛选 丹药"),
            ("我的货摊", "我的货摊"),
        ],
        "突破系统": [
            ("尝试突破", "突破"),
        ],
        "和平模式": [
            ("避世", "避世"),
            ("入世", "入世"),
        ],
        "其他功能": [
            ("更改道号", "更改道号 测试道友"),
        ],
    }

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("修仙插件功能测试工具")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # 设置样式
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # 结果记录
        self.results = []
        self.is_running = False

        # 创建界面
        self._create_widgets()

    def _create_widgets(self):
        """创建界面组件"""
        # 顶部框架 - 连接信息
        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="API地址:").pack(side=tk.LEFT)
        self.entry_url = ttk.Entry(top_frame, width=40)
        self.entry_url.insert(0, self.API_URL)
        self.entry_url.pack(side=tk.LEFT, padx=5)

        ttk.Label(top_frame, text="API Key:").pack(side=tk.LEFT, padx=(10, 0))
        self.entry_key = ttk.Entry(top_frame, width=40, show="*")
        self.entry_key.insert(0, self.API_KEY)
        self.entry_key.pack(side=tk.LEFT, padx=5)

        # 中间框架 - 主要内容
        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左侧 - 控制面板
        left_frame = ttk.LabelFrame(main_frame, text="测试控制", padding=10)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))

        # 用户名设置
        ttk.Label(left_frame, text="测试用户名:").pack(anchor=tk.W)
        self.entry_user = ttk.Entry(left_frame, width=20)
        self.entry_user.insert(0, "test")
        self.entry_user.pack(fill=tk.X, pady=(0, 10))

        # 单个指令测试
        ttk.Label(left_frame, text="自定义指令:").pack(anchor=tk.W)
        self.entry_cmd = ttk.Entry(left_frame, width=20)
        self.entry_cmd.pack(fill=tk.X, pady=(0, 5))

        self.btn_send = ttk.Button(left_frame, text="发送指令", command=self._send_custom_command)
        self.btn_send.pack(fill=tk.X, pady=(0, 15))

        # 分隔线
        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 预设测试按钮
        ttk.Label(left_frame, text="预设测试:").pack(anchor=tk.W, pady=(5, 5))

        self.btn_test_all = ttk.Button(left_frame, text="测试全部功能", command=self._test_all)
        self.btn_test_all.pack(fill=tk.X, pady=2)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 分类测试按钮
        for category in self.TEST_COMMANDS:
            btn = ttk.Button(
                left_frame,
                text=f"测试{category}",
                command=lambda c=category: self._test_category(c),
            )
            btn.pack(fill=tk.X, pady=2)

        ttk.Separator(left_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        # 清除按钮
        self.btn_clear = ttk.Button(left_frame, text="清除日志", command=self._clear_log)
        self.btn_clear.pack(fill=tk.X, pady=2)

        # 右侧 - 日志显示
        right_frame = ttk.LabelFrame(main_frame, text="测试日志", padding=10)
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # 日志文本框
        self.log_text = scrolledtext.ScrolledText(
            right_frame, wrap=tk.WORD, font=("Consolas", 10), state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 配置文本标签
        self.log_text.tag_configure("time", foreground="#888888")
        self.log_text.tag_configure("input", foreground="#2196F3", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("output", foreground="#4CAF50")
        self.log_text.tag_configure("error", foreground="#F44336")
        self.log_text.tag_configure("header", foreground="#9C27B0", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("success", foreground="#4CAF50", font=("Consolas", 10, "bold"))
        self.log_text.tag_configure("category", foreground="#FF9800", font=("Consolas", 10, "bold"))

        # 底部 - 状态栏
        bottom_frame = ttk.Frame(self.root, padding=(10, 5))
        bottom_frame.pack(fill=tk.X)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(bottom_frame, textvariable=self.status_var).pack(side=tk.LEFT)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_bar = ttk.Progressbar(bottom_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))

    def _log(self, message, tag=None):
        """向日志框添加消息"""
        self.log_text.config(state=tk.NORMAL)
        timestamp = datetime.now().strftime("%H:%M:%S")

        if tag:
            self.log_text.insert(tk.END, f"[{timestamp}] ", "time")
            self.log_text.insert(tk.END, f"{message}\n", tag)
        else:
            self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")

        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

    def _clear_log(self):
        """清除日志"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.results.clear()
        self.status_var.set("日志已清除")

    def _send_request(self, command, username):
        """发送请求并获取响应"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.entry_key.get()}",
        }
        data = {
            "username": username,
            "message": [{"type": "plain", "text": command}],
        }

        try:
            response = requests.post(
                self.entry_url.get(), headers=headers, json=data, timeout=120, stream=True
            )

            if response.status_code != 200:
                return f"[HTTP错误 {response.status_code}]"

            replies = []
            for line in response.iter_lines():
                if line:
                    line_str = line.decode("utf-8")
                    json_str = line_str.replace("data: ", "")
                    try:
                        parsed = json.loads(json_str)
                        if parsed.get("type") == "plain":
                            replies.append(parsed.get("data", ""))
                    except json.JSONDecodeError:
                        pass

            return "\n".join(replies) if replies else "[无回复]"

        except requests.exceptions.ConnectionError:
            return "[连接失败 - 请检查AstrBot是否运行]"
        except requests.exceptions.Timeout:
            return "[请求超时]"
        except Exception as e:
            return f"[错误: {e}]"

    def _test_command(self, name, command):
        """测试单个指令"""
        username = self.entry_user.get()

        self._log(f"▶ 发送: {command}", "input")

        # 在线程中执行请求，避免界面卡顿
        result = [None]

        def do_request():
            result[0] = self._send_request(command, username)

        thread = threading.Thread(target=do_request)
        thread.start()
        thread.join(timeout=125)

        if result[0] is None:
            response = "[请求超时]"
        else:
            response = result[0]

        # 判断是否成功
        is_error = any(
            x in response
            for x in ["[HTTP错误", "[连接失败", "[请求超时]", "[错误:", "[无回复]", "出现异常"]
        )

        if is_error:
            self._log(f"✗ {response}", "error")
        else:
            self._log(f"✓ {response}", "output")

        return name, command, response, is_error

    def _test_all(self):
        """测试所有功能"""
        if self.is_running:
            messagebox.showwarning("提示", "测试正在进行中，请等待完成")
            return

        self.is_running = True
        self.btn_test_all.config(state=tk.DISABLED)
        self.results.clear()

        # 计算总测试数
        total = sum(len(cmds) for cmds in self.TEST_COMMANDS.values())
        current = [0]

        self._log("=" * 50, "header")
        self._log(f"开始全功能测试 (共 {total} 个指令)", "header")
        self._log("=" * 50, "header")

        def run_tests():
            for category, commands in self.TEST_COMMANDS.items():
                self._log(f"\n【{category}】", "category")

                for name, cmd in commands:
                    current[0] += 1
                    progress = (current[0] / total) * 100
                    self.root.after(0, lambda p=progress: self.progress_var.set(p))
                    self.root.after(
                        0,
                        lambda c=current[0], t=total: self.status_var.set(
                            f"测试中... ({c}/{t})"
                        ),
                    )

                    result = self._test_command(name, cmd)
                    self.results.append(result)

                    time.sleep(0.5)

            # 测试完成
            self.root.after(0, self._show_summary)
            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set("测试完成"))
            self.root.after(0, lambda: self.btn_test_all.config(state=tk.NORMAL))
            self.root.after(0, lambda: setattr(self, "is_running", False))

        thread = threading.Thread(target=run_tests, daemon=True)
        thread.start()

    def _test_category(self, category):
        """测试指定分类"""
        if self.is_running:
            messagebox.showwarning("提示", "测试正在进行中，请等待完成")
            return

        if category not in self.TEST_COMMANDS:
            return

        self.is_running = True
        self.btn_test_all.config(state=tk.DISABLED)
        commands = self.TEST_COMMANDS[category]
        total = len(commands)
        current = [0]

        self._log("=" * 50, "header")
        self._log(f"测试分类: {category} (共 {total} 个指令)", "header")
        self._log("=" * 50, "header")

        def run_tests():
            for name, cmd in commands:
                current[0] += 1
                progress = (current[0] / total) * 100
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                self.root.after(
                    0,
                    lambda c=current[0], t=total: self.status_var.set(
                        f"测试 {category}... ({c}/{t})"
                    ),
                )

                self._test_command(name, cmd)
                time.sleep(0.5)

            self.root.after(0, lambda: self.progress_var.set(100))
            self.root.after(0, lambda: self.status_var.set("测试完成"))
            self.root.after(0, lambda: self.btn_test_all.config(state=tk.NORMAL))
            self.root.after(0, lambda: setattr(self, "is_running", False))

        thread = threading.Thread(target=run_tests, daemon=True)
        thread.start()

    def _send_custom_command(self):
        """发送自定义指令"""
        if self.is_running:
            messagebox.showwarning("提示", "测试正在进行中，请等待完成")
            return

        cmd = self.entry_cmd.get().strip()
        if not cmd:
            messagebox.showwarning("提示", "请输入指令")
            return

        self.is_running = True
        self.btn_send.config(state=tk.DISABLED)

        def run():
            self._test_command("自定义指令", cmd)
            self.root.after(0, lambda: self.btn_send.config(state=tk.NORMAL))
            self.root.after(0, lambda: setattr(self, "is_running", False))

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

    def _show_summary(self):
        """显示测试汇总"""
        if not self.results:
            return

        self._log("\n" + "=" * 50, "header")
        self._log("测试汇总", "header")
        self._log("=" * 50, "header")

        passed = sum(1 for _, _, _, err in self.results if not err)
        failed = sum(1 for _, _, _, err in self.results if err)

        self._log(f"✓ 通过: {passed}", "success")
        if failed > 0:
            self._log(f"✗ 失败: {failed}", "error")
        else:
            self._log(f"✗ 失败: {failed}")
        self._log(f"总计: {len(self.results)}")

        if failed > 0:
            self._log("\n失败项:", "error")
            for name, cmd, result, is_err in self.results:
                if is_err:
                    self._log(f"  ✗ {name} ({cmd})", "error")

    def run(self):
        """启动应用"""
        self.root.mainloop()


if __name__ == "__main__":
    app = XiuxianTestTool()
    app.run()
