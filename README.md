# 🚗 Lumbini EDL Driving Test Slot Checker — GitHub Action

Run your driving license appointment slot monitor 24/7 in the cloud for **100% free** using GitHub Actions with instant **Telegram alerts**.

---

## 📁 Repository Structure

```
.
├── .github/
│   └── workflows/
│       └── slot_checker.yml    # GitHub Actions cron workflow
└── check_slot.py               # Pure Python script (uses standard library)
```

---

## 🚀 Setup Guide (3 Steps)

### Step 1: Create a GitHub Repository & Push Files
1. Go to [github.com/new](https://github.com/new) and create a repository (you can make it **Private**).
2. Push or upload these files to your repository:
   - `check_slot.py`
   - `.github/workflows/slot_checker.yml`

*(Or run from your terminal):*
```bash
cd C:\Users\Shiva-PC\Downloads\AG\edl_github_action
git init
git add .
git commit -m "Add Lumbini EDL slot checker"
git branch -M main
git remote add origin https://github.com/<YOUR_USERNAME>/<YOUR_REPO_NAME>.git
git push -u origin main
```

---

### Step 2: Add Secrets in GitHub
In your GitHub repository:
1. Click **Settings** $\rightarrow$ **Secrets and variables** $\rightarrow$ **Actions**.
2. Click **New repository secret** and add:
   - Name: `TELEGRAM_BOT_TOKEN`
     - Value: *(Your token from @BotFather)*
   - Name: `TELEGRAM_CHAT_ID`
     - Value: *(Your numeric Chat ID from @userinfobot)*
   - *(Optional)* Name: `EDL_UUID`
     - Value: `92a75ad3-4a1a-4ae3-8f10-5435eac485e4`

---

### Step 3: Run & Test
1. Click the **Actions** tab at the top of your GitHub repository.
2. Select **Lumbini Driving License Slot Checker** on the left menu.
3. Click **Run workflow** $\rightarrow$ **Run workflow**.
4. Click on the triggered run to see the live logs scanning your application status and dates!

---

## ⏰ Changing the Check Schedule

In `.github/workflows/slot_checker.yml`, edit the `cron` line under `schedule`:

| Cron Expression | Interval |
| :--- | :--- |
| `*/15 * * * *` | **Every 15 minutes** (Default) |
| `*/30 * * * *` | Every 30 minutes |
| `0 * * * *` | Every 1 hour |
| `*/10 * * * *` | Every 10 minutes |
