# 即時翻譯器

一個面對面對談的即時翻譯器，支援文字及語音輸入，適合跨語言交流使用。

## 功能特點

- 支援多種語言：
  - 中文（繁體）
  - 英文
  - 日文
  - 韓文
  - 泰文
  - 越南文
- 即時文字翻譯
- 語音輸入功能
- 現代化直覺的使用者介面
- 面對面對談設計
- 自動語音朗讀

## Requirements

- Python 3.8+
- quart
- hypercorn
- edge-tts
- python-dotenv

## Installation

1. Clone the repository:
```bash
git clone https://github.com/marmotkit/trainslator-1.git
cd trainslator-1
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python -m hypercorn app:app
```

## 使用方式

1. 從下拉選單中選擇來源語言和目標語言
2. 在左側文字框輸入文字，或使用語音輸入按鈕
3. 翻譯結果會自動顯示在右側文字框

## 系統需求

- Python 3.8 或更新版本
- Deepseek API 金鑰
- 網際網路連線（用於翻譯服務）
- 麥克風（用於語音輸入）
