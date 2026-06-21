# 需要先安装: pip install textual-autocomplete
from textual.app import App, ComposeResult
from textual.widgets import Input
from textual_autocomplete import AutoComplete, DropdownItem

class PromptApp(App):
    def compose(self) -> ComposeResult:
        input_widget = Input(placeholder="搜索编程语言...")
        yield input_widget
        # 创建带前缀（prefix）的候选列表
        candidates = [
            DropdownItem("Python", prefix="🐍"),
            DropdownItem("JavaScript", prefix="🌐"),
            DropdownItem("Java", prefix="☕"),
        ]
        yield AutoComplete(input_widget, candidates=candidates)

if __name__ == "__main__":
    PromptApp().run()