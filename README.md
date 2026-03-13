# LangGeek Telegram Vocab Bot 🎓

Bot Telegram giúp học từ vựng tiếng Anh từ dữ liệu LangGeek.

## Tính năng
- 📚 **Học theo Level/Subcategory** — chọn từ A1 đến C2
- 📋 **Bộ từ cá nhân** — tạo và học bộ từ riêng
- 🃏 **Flashcard** — Biết / Chưa biết
- 🎯 **Trắc nghiệm** — 4 đáp án
- ⌨️ **Gõ đáp án** — từ gợi ý ảnh/nghĩa/phiên âm
- 📊 **Tiến độ** — thống kê known/learning/new
- 🔍 **Tìm từ** — tra nghĩa và thêm vào bộ

## Cài đặt

### Yêu cầu
- Python 3.11+
- Node.js 18+ (cho Convex CLI)
- Tài khoản [Convex](https://convex.dev)
- Telegram Bot Token (từ [@BotFather](https://t.me/BotFather))

### 1. Clone & cài dependencies

```bash
cd langeek-bot
pip install -r requirements.txt
npm install
```

### 2. Cấu hình Convex

```bash
npx convex dev   # Lần đầu sẽ hỏi login và tạo project
```

Copy `CONVEX_URL` từ output (dạng `https://xxx.convex.cloud`).

### 3. Tạo file `.env`

```bash
cp .env.example .env
# Điền BOT_TOKEN và CONVEX_URL vào .env
```

### 4. Chạy local (polling mode)

```bash
# Terminal 1: Convex backend
npx convex dev

# Terminal 2: Python bot
python -m bot.main
```

## Deploy lên Render/Railway

1. Push code lên GitHub
2. Tạo project mới trên Render/Railway, trỏ vào repo
3. Set environment variables: `BOT_TOKEN`, `CONVEX_URL`, `WEBHOOK_URL`, `VOCAB_DB_PATH`
4. Render tự đọc `Procfile` và chạy `python -m bot.main`
5. Deploy Convex: `npx convex deploy`

> **Lưu ý:** File `langeek_vocab.db` phải có mặt trên server. Upload lên hoặc set `VOCAB_DB_PATH` trỏ đến đúng vị trí.

## Cấu trúc project

```
langeek-bot/
├── bot/
│   ├── main.py              # Entry point
│   ├── config.py            # Env vars
│   ├── handlers/            # Telegram handlers
│   ├── services/            # Business logic
│   └── db/                  # DB clients
├── convex/                  # Backend TypeScript
│   ├── schema.ts
│   ├── users.ts
│   ├── progress.ts
│   └── customSets.ts
├── requirements.txt
├── package.json
├── Procfile
└── .env.example
```

## Commands

| Command | Mô tả |
|---|---|
| `/start` | Bắt đầu & đăng ký |
| `/study` | Chọn chủ đề và học |
| `/myset` | Quản lý bộ từ cá nhân |
| `/progress` | Xem tiến độ |
| `/search <từ>` | Tìm kiếm từ vựng |
| `/stop` | Dừng phiên học hiện tại |
