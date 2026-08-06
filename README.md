<div align="center">

# 🎵 Music Galaxy

### <b>✨ The Ultimate Telegram Music Bot with Web Dashboard ✨</b>

[![](https://img.shields.io/badge/Discord-Support%20Server-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/e8CS6Qt8q)
[![](https://img.shields.io/badge/YouTube-Channel-FF0000?style=for-the-badge&logo=youtube&logoColor=white)](https://www.youtube.com/@DevVersehq)
[![](https://img.shields.io/badge/Twitter-Follow-1DA1F2?style=for-the-badge&logo=twitter&logoColor=white)](https://x.com/Delete_ee7)

[![](https://img.shields.io/github/stars/anonymous/MusicGalaxy?style=social)](https://github.com/DevVerse0/Music-Galaxy.git)
[![](https://img.shields.io/github/forks/anonymous/MusicGalaxy?style=social)](https://github.com/DevVerse0/Music-Galaxy.git)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

</div>

## 🔥 What is Music Galaxy?

Music Galaxy is a premium Telegram music bot featuring **YouTube audio/video streaming**, a **real-time web dashboard**, **multi-assistant support**, **premium tiers**, and **advanced group management**. Built for high-quality, buffer-free music experiences in voice chats with comprehensive admin controls and analytics.

---

## ✨ Premium Features

<div align="center">

| 🎵 **Music Playback** | 📋 **Queue System** | ⏱️ **Live Timer** |
|----------------------|--------------------|------------------|
| YouTube Search & Play | Multiple Song Queue | Real-Time Progress Bar |
| Playlist Support | Force Play | 10s Seek Control |
| 128kbps MP3 Audio | Loop/Repeat | Timer Button |
| Video Streaming | Adjustable Limits |  |

| 🎮 **Controls** | 🌐 **Web Dashboard** | 🛡️ **Admin System** |
|-----------------|----------------------|---------------------|
| Play/Pause/Skip | Full Browser Panel | Sudo Users |
| Stop/Replay | Live Now Playing | Global Ban |
|  | Queue Manager | User Restrictions |
|  | System Monitoring | Admin Mode |

</div>

---

## 🚀 Premium Modules

### 💎 Premium System
- **Pro Tier** 🚀 — Basic premium features
- **Elite Tier** 💎 — Advanced features unlocked
- **Infinite Tier** 🌠 — Full access with maximum benefits

### 🤖 Multi Assistant
- Up to **3 Userbot Assistants** for load balancing
- Auto distribution across groups
- Independent VC control per group

### 🌐 Web Dashboard
- Complete control panel in your browser
- Live now playing with progress synchronization
- Queue viewer & manager
- System monitoring (CPU/RAM/Disk usage)
- Broadcast messaging to groups/users
- Remote admin tools (ban, mute, kick, promote)
- Group settings management
- User database with advanced search
- Song request history & analytics
- Audit logs with terminal interface
- Assistant management panel
- Spy system for monitoring
- Premium management interface
- Real-time configuration settings

### 🔧 Advanced Features
- Multi-language support (13 languages)
- Interactive help menu
- Ping & speed testing
- Per-group settings
- Auto leave when idle
- Auto end on inactivity
- Command cleanup

---

## 📦 Quick Deploy

### 🎯 Option 1: Deploy to Railway (Recommended)

<div align="center">

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=your-template-id&envs=API_ID,API_HASH,BOT_TOKEN,SESSION1&optionalEnvs=SESSION2,SESSION3&plugin=docs.railway.app reference: railway-plugin-docs.env)

</div>

### 🎯 Option 2: Deploy to Render

<div align="center">

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/anonymous/MusicGalaxy)

</div>

---

## 💻 Local Deployment

### Prerequisites
- Python 3.11 or higher
- FFmpeg installed and in PATH
- Telegram API credentials (get from [my.telegram.org](https://my.telegram.org))
- At least one session string (optional but recommended for VC support)

### Step-by-Step Guide

#### 1. Clone the repository
```bash
git clone https://github.com/anonymous/MusicGalaxy.git
cd MusicGalaxy
```

#### 2. Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate       # Linux/macOS
venv\Scripts\activate          # Windows
```

#### 3. Install dependencies
```bash
pip install -r requirements.txt
```

#### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env file with your credentials
```

Required values:
| Variable | Description | Required |
|----------|-------------|----------|
| `API_ID` | Your Telegram API ID | ✅ |
| `API_HASH` | Your Telegram API Hash | ✅ |
| `BOT_TOKEN` | Your bot token from @BotFather | ✅ |
| `SESSION1` | Userbot session string | ❌ (but recommended) |
| `OWNER_ID` | Your Telegram user ID | ✅ |
| `LOGGER_ID` | Logger group ID (e.g., -100...) | ✅ |

#### 5. Generate session string (optional)
```bash
python gen_session.py
```
This will generate a session string for your userbot. Copy it to `.env` under `SESSION1`.

#### 6. Install FFmpeg
- **Ubuntu/Debian**: `apt install ffmpeg`
- **macOS**: `brew install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

#### 7. Start the bot
```bash
python3 -m devverse
```

On Windows:
```bash
python devverse
```

---

## ⚙️ Configuration

All environment variables (in `.env`):

```env
# ── Core Credentials ──
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=123456789:AA your_bot_token
OWNER_ID=your_user_id
LOGGER_ID=-100your_logger_group_id

# ── Session Strings ──
SESSION1=your_session_string  # Assistant 1
SESSION2=your_session_string  # Assistant 2 (optional)
SESSION3=your_session_string  # Assistant 3 (optional)

# ── Server ──
PORT=8080
DATABASE_URL=database.db

# ── Media ──
DURATION_LIMIT=60  # Max audio duration in minutes
QUEUE_LIMIT=20
PLAYLIST_LIMIT=20

# ── Features ──
AUTO_LEAVE=True
AUTO_END=True
THUMB_GEN=True
VIDEO_PLAY=True

# ── Content ──
COOKIES_URL=
DEFAULT_THUMB=https://graph.org/file/...
PING_IMG=https://files.catbox.moe/...
START_IMG=https://graph.org/file/...

# ── Links ──
SUPPORT_CHANNEL=https://t.me/delete_tee7
SUPPORT_CHAT=https://t.me/+joinlink

# ── Dashboard ──
DASHBOARD_URL=
DASHBOARD_PASSWORD=your_password

# ── Misc ──
MAINTENANCE=False
LANG_CODE=en
OWNER_USERNAME=Delete_ee
```

---

## 🎮 Usage

### Basic Commands
| Command | Description |
|---------|-------------|
| `/play [song]` or `.play [song]` | Play a song from YouTube |
| `/vplay [song]` | Play video stream |
| `/skip` or `/next` | Skip current song |
| `/pause` | Pause playback |
| `/resume` | Resume playback |
| `/stop` | Stop and clear queue |
| `/replay` | Replay current song |
| `/loop` or `/repeat` | Loop current song |
| `/shuffle` | Shuffle queue |
| `/seek [sec]` | Seek forward |
| `/seekback [sec]` | Seek backward |
| `/playlist` | View current queue |
| `/ping` | Check bot latency |
| `/stats` | View bot statistics |

Add `-f` flag to force play (e.g., `/play -f song`).

### Admin Commands
| Command | Description |
|---------|-------------|
| `/settings` | Configure group settings |
| `/auth` | Grant play access to a user |
| `/unauth` | Revoke play access |
| `/blacklist [id]` | Blacklist user/chat |
| `/gblacklist [id]` | Global ban user |
| `/restart` | Restart the bot |
| `/logs` | Get log file |
| `/eval` | Execute Python code (sudo only) |
| `/broadcast` | Broadcast to all chats |

---

## 🛠️ Troubleshooting

### Bot doesn't respond
- Check that all environment variables are set in `.env`
- Verify your bot token is correct
- Check console logs for errors

### No audio in voice chat
- Ensure FFmpeg is installed and accessible
- Verify session strings are valid
- Make sure the bot is promoted as admin with "Voice Chat" permission

### Dashboard not loading
- Verify `PORT` is not already in use
- Check that `DASHBOARD_PASSWORD` is set in `.env`
- Default credentials: username is any, password from config

### YouTube downloads failing
- Add `COOKIES_URL` with valid cookies for age-restricted content
- Or place a `cookies.txt` file in the bot directory

---

## 📊 Architecture

```
Music Galaxy/
├── devverse/                    # Main bot package
│   ├── __init__.py              # Core initialization
│   ├── __main__.py              # Entry point
│   ├── core/
│   │   ├── bot.py               # Main bot Client
│   │   ├── userbot.py           # Userbot assistants
│   │   ├── calls.py             # Voice chat integration
│   │   ├── database.py          # SQLite database
│   │   ├── web.py               # FastAPI dashboard
│   │   ├── youtube.py           # YouTube integration
│   │   ├── dir.py
│   │   ├── lang.py
│   │   ├── telegram.py
│   │   └── templates/           # Dashboard HTML templates
│   ├── helpers/
│   │   ├── _queue.py            # Queue management
│   │   ├── _thumbnails.py       # Thumbnail generation
│   │   └── ...
│   ├── plugins/                 # All bot commands
│   │   ├── play.py
│   │   ├── start.py
│   │   └── ...
│   └── locales/                 # Multi-language JSON files
├── gen_session.py               # Session string generator
├── config.py                    # Configuration class
├── start                        # Startup script (Railway)
├── requirements.txt
└── .env.example
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add: description'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

## ⭐ Support the Project

If you find Music Galaxy useful, please consider:
- ⭐ Starring the repository
- 🍪 Buying me a coffee
- 📢 Sharing with other community owners
- 🐛 Reporting bugs or submitting PRs

---

<div align="center">

---

### 🔧 Created & Maintained by

<a href="https://github.com/DevVerse0">
  <img src="https://avatars.githubusercontent.com/u/anonymous?v=4" width="100" style="border-radius: 50%;"/>
</a>

### 📱 Stay Connected

| Platform | Link |
|----------|------|
| YouTube | [@DevverseOfficial](https://www.youtube.com/@DevVerseOfficial0) |
| Telegram | [@delete_tee7](https://t.me/delete_tee7) |

---

**🎧 Power your group voice chats with Music Galaxy! 🎧**

</div>
