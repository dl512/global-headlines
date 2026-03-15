# DigitalOcean Droplet Setup for Newsletter Pipeline

Run the newsletter pipeline daily on an Ubuntu droplet. Use a **Singapore** region so API access (OpenAI/OpenRouter, etc.) works without VPN.

---

## 1. Create the Droplet

1. In [DigitalOcean](https://cloud.digitalocean.com/droplets/new):
   - **Image**: Ubuntu 22.04 LTS
   - **Plan**: Basic → **Regular** → **$6/mo** (1 GB RAM / 1 vCPU) or **$12/mo** (2 GB) if you prefer headroom
   - **Region**: **Singapore**
   - **Authentication**: SSH key (recommended) or password
   - **Hostname**: e.g. `newsletter-pipeline`

2. Create Droplet, then note the **IP address**.

---

## 2. First Login and System Setup

From your local machine (with VPN off if you like; droplet uses its own IP):

```bash
ssh root@YOUR_DROPLET_IP
```

Update the system and install Python, git, and a few basics:

```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv git
```

Optional: create a non-root user (recommended for long-term):

```bash
adduser newsletter
usermod -aG sudo newsletter
# Switch to that user: su - newsletter
# Use newsletter@... for the steps below, or keep using root
```

---

## 3. Get Your Code onto the Droplet

**Option A – Git (if your repo is on GitHub/GitLab)**

```bash
cd /opt   # or home: cd ~
git clone https://github.com/YOUR_USERNAME/global_headlines.git
cd global_headlines
```

**Option B – Copy from your Windows machine (no git on server)**

On your **Windows PC** (in PowerShell, from your project folder):

```powershell
scp -r . root@YOUR_DROPLET_IP:/opt/global_headlines
```

Or use **rsync** if you have it (e.g. WSL or Git Bash):

```bash
rsync -avz --exclude '.git' --exclude 'venv' --exclude '__pycache__' . root@YOUR_DROPLET_IP:/opt/global_headlines/
```

Then on the droplet:

```bash
cd /opt/global_headlines
```

---

## 4. Python Environment and Dependencies

On the droplet:

```bash
cd /opt/global_headlines
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

If Playwright is used for any crawler and you see browser-related errors, install its browsers once:

```bash
# Only if your pipeline uses Playwright
playwright install chromium
```

---

## 5. Environment Variables (`.env`)

Create a `.env` file at the **project root** (same folder as `workflow/`):

```bash
cd /opt/global_headlines
nano .env
```

Add (replace with your real values; keep the same variable names your code uses):

```env
# OpenAI / OpenRouter
OPENAI_API_KEY=your_openrouter_or_openai_key
BASE_URL=https://openrouter.ai/api/v1

# Mailjet
MAILJET_API_KEY=your_mailjet_api_key
MAILJET_API_SECRET=your_mailjet_api_secret
```

Save and exit (`Ctrl+O`, `Enter`, `Ctrl+X`). Restrict permissions:

```bash
chmod 600 .env
```

---

## 6. Google Sheets Service Account

Your code expects a JSON key file. From your **local** machine, copy it to the droplet:

```powershell
scp "C:\path\to\global-headlines-474905-9494f258e0a5.json" root@YOUR_DROPLET_IP:/opt/global_headlines/
```

Or place it under `workflow/` if that’s where your code looks:

```bash
scp "C:\path\to\global-headlines-474905-9494f258e0a5.json" root@YOUR_DROPLET_IP:/opt/global_headlines/workflow/
```

On the droplet, fix ownership and permissions:

```bash
chmod 600 /opt/global_headlines/global-headlines-474905-9494f258e0a5.json
```

---

## 7. Test Run

From project root, with the venv activated:

```bash
cd /opt/global_headlines
source venv/bin/activate
python workflow/run_newsletter_pipeline.py
```

- If you see import errors, ensure you’re in `/opt/global_headlines` and `workflow` is there.
- If Google/Mailjet/OpenAI errors appear, double-check `.env` and the service account JSON path.

---

## 8. Schedule Daily Run with Cron

Edit root’s crontab:

```bash
crontab -e
```

Add one line (example: run every day at **8:00 AM Singapore time**):

```cron
0 8 * * * cd /opt/global_headlines && /opt/global_headlines/venv/bin/python workflow/run_newsletter_pipeline.py >> /var/log/newsletter_pipeline.log 2>&1
```

- To use **Hong Kong time** (UTC+8, same as Singapore): `0 8 * * *` is already 08:00 local.
- To run at 7:00 AM: use `0 7 * * *`.

Create the log file and allow writes:

```bash
touch /var/log/newsletter_pipeline.log
chmod 644 /var/log/newsletter_pipeline.log
```

Check that cron is running:

```bash
systemctl status cron
```

Optional: log with a date in the filename (e.g. one log per day):

```cron
0 8 * * * cd /opt/global_headlines && /opt/global_headlines/venv/bin/python workflow/run_newsletter_pipeline.py >> /var/log/newsletter_pipeline_$(date +\%Y-\%m-\%d).log 2>&1
```

---

## 9. Quick Reference

| Item | Path / command |
|------|----------------|
| Project root | `/opt/global_headlines` |
| Run pipeline | `cd /opt/global_headlines && venv/bin/python workflow/run_newsletter_pipeline.py` |
| Activate venv | `source /opt/global_headlines/venv/bin/activate` |
| Logs | `/var/log/newsletter_pipeline.log` |
| Edit cron | `crontab -e` |

---

## 10. Optional: Run Only Summarize + Send (No Crawl)

If you ever want the droplet to only re-summarize from existing CSV and send (e.g. a second run without re-crawling), you’d need a separate script or a flag in your pipeline; the current `run_newsletter_pipeline.py` runs full crawl + summarize + send. You can add a small wrapper script that calls only the parts you need and schedule that in cron instead.

---

## Troubleshooting

- **“OPENAI_API_KEY not found”**  
  Ensure `.env` is in `/opt/global_headlines` and that you run `python workflow/run_newsletter_pipeline.py` from `/opt/global_headlines`.

- **“Google credentials file not found”**  
  Put `global-headlines-474905-9494f258e0a5.json` in `/opt/global_headlines` or `/opt/global_headlines/workflow` (depending where `get_credentials_path()` looks).

- **Cron doesn’t run**  
  Use absolute paths in the cron line (as above). Check logs: `tail -f /var/log/newsletter_pipeline.log` after the scheduled time.

- **Permission denied**  
  Ensure the user that runs cron (e.g. root) owns the project dir and can read `.env` and the Google JSON.
