# AvitoHunter 🎯

**Automatic monitor (parser) of new listings on Avito with AI-powered text and media analysis, tailored for specific products with full characteristic matching and Telegram notifications.**


---

## ✨ Features

- 🔍 **Avito parsing** via Playwright with anti-detection
- 🤖 **AI analysis** of listing text and photos (quality, characteristic matching)
- 🎯 **Smart filtering** by all product parameters (brand, size, condition, price)
- ⚡ **Instant Telegram notifications** with photos and descriptions
- 🐳 **Docker-ready** — deploy in 2 commands
- 🌐 **Proxy support** (HTTP/SOCKS5) for bypassing RF blocks
- 💾 **SQLite database** — track viewed listings
- 🔄 **Auto-restart** on network errors

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/kihaas/AvitoHunter.git
cd AvitoHunter
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```bash
# ==================== TELEGRAM (REQUIRED) ====================
TELEGRAM_BOT_TOKEN=1234567890:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw
TELEGRAM_CHAT_ID=-1001234567890

# ==================== AVITO (REQUIRED) ====================
# Avito search URLs (space-separated)
AVITO_SEARCH_URLS="https://www.avito.ru/samara?q=ракетка+падел https://www.avito.ru/moskva?q=padel"

# ==================== PROXY (RECOMMENDED FOR RF) ====================
HTTP_PROXY=http://user:pass@proxy-server:port
SOCKS_PROXY=socks5://user:pass@proxy-server:1080

# ==================== PRODUCT PARAMETERS (CUSTOMIZE FOR YOURS!) ====================
TARGET_PRICE_MAX=15000          # Maximum price (RUB)
TARGET_PRICE_MIN=5000           # Minimum price (RUB)
TARGET_BRAND="Wilson,Babolat,Head"  # Brands (comma-separated)
TARGET_CONDITION="новая,отличное"   # Condition
TARGET_SIZE="3/8"               # Size/characteristic
TARGET_KEYWORDS="карбон,графен,Pro Staff"  # Keywords
AI_MIN_SCORE=0.85               # Minimum AI-score (0.0-1.0)

# ==================== INTERVAL & LOGGING ====================
CHECK_INTERVAL_SECONDS=120      # Check interval (seconds)
LOG_LEVEL=INFO                  # Log level (DEBUG/INFO/WARNING/ERROR)
```

> **⚠️ IMPORTANT:** Be sure to customize `TARGET_*` parameters for YOUR product!

### 3. Run with Docker Compose

```bash
docker compose up -d --build
```

### 4. View logs

```bash
docker compose logs -f avitohunter
```

---

## 🛠 Customize for Your Product

### Main parameters in `.env`:

| Parameter | Description | Tennis Racket Example | iPhone Example |
|-----------|-------------|----------------------|----------------|
| `TARGET_PRICE_MAX` | Maximum price | `15000` | `80000` |
| `TARGET_PRICE_MIN` | Minimum price | `5000` | `50000` |
| `TARGET_BRAND` | Brands (comma-separated) | `"Wilson,Babolat,Head"` | `"Apple"` |
| `TARGET_CONDITION` | Condition | `"новая,отличное"` | `"новый,идеальное"` |
| `TARGET_SIZE` | Size/characteristic | `"98in2,3/8"` | `"128GB,256GB"` |
| `TARGET_KEYWORDS` | Keywords | `"карбон,Pro Staff"` | `"iPhone 15 Pro,A17"` |
| `AI_MIN_SCORE` | Minimum AI-score | `0.85` | `0.90` |

### Configuration Examples:

#### 🎾 Tennis Racket:
```bash
TARGET_PRICE_MAX=12000
TARGET_BRAND="Wilson,Babolat,Head,Yonex"
TARGET_CONDITION="новая,отличное"
TARGET_SIZE="98in2,100in2"
TARGET_KEYWORDS="карбон,графен,Pro Staff,Blade"
AI_MIN_SCORE=0.85
```

#### 📱 iPhone:
```bash
TARGET_PRICE_MAX=80000
TARGET_BRAND="Apple"
TARGET_CONDITION="новый,идеальное"
TARGET_SIZE="128GB,256GB"
TARGET_KEYWORDS="iPhone 15 Pro,A17 Pro,титан"
AI_MIN_SCORE=0.90
```

#### 🚴 Bicycle:
```bash
TARGET_PRICE_MAX=45000
TARGET_BRAND="Merida,Giant,Trek"
TARGET_CONDITION="отличное,хорошее"
TARGET_SIZE="M,L"
TARGET_KEYWORDS="карбон,29 колёс,XT"
AI_MIN_SCORE=0.80
```

## 📱 Telegram Setup

### 1. Create a bot:
1. Open [@BotFather](https://t.me/BotFather) in Telegram
2. Send `/newbot` command
3. Choose a name and username (must end with `bot`)
4. Copy the token to `TELEGRAM_BOT_TOKEN`

### 2. Get Chat ID:
1. Add bot to your chat (or start a DM)
2. Send any message to the bot
3. Open in browser: `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
4. Find `"chat":{"id":-1001234567890}` — this is your `TELEGRAM_CHAT_ID`

> For private chats ID is positive, for groups/channels — negative.

---

## 🤖 AI Filtering

The bot automatically analyzes each listing by criteria:

| Criterion | Description | Weight |
|-----------|-------------|--------|
| ✅ Brand match | Check against `TARGET_BRAND` list | 25% |
| ✅ Price range | Check `TARGET_PRICE_MIN` – `TARGET_PRICE_MAX` | 20% |
| ✅ Condition | Text analysis for `TARGET_CONDITION` match | 15% |
| ✅ Characteristics | Size, model, parameters check | 25% |
| ✅ Photo quality | Image defect analysis | 10% |
| ✅ Description completeness | Text length and informativeness | 5% |

**Notification is sent ONLY if AI-score ≥ `AI_MIN_SCORE`**