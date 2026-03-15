# Git sync: local ↔ VM (you already copied files to VM)

Use this once you have a Git repo locally and the same files on the VM at `/opt/global_headlines`.

---

## One-time: Connect your repo to GitHub and prepare the VM

### On your laptop (PowerShell)

1. Go to your project folder:
   ```powershell
   cd C:\Users\User\Desktop\AI\agents\global_headlines
   ```

2. See if a remote is already set:
   ```powershell
   git remote -v
   ```
   - If you see `origin` and a GitHub URL, skip to step 4.
   - If you see nothing or “not a git repository”, run:
     ```powershell
     git init
     git branch -M main
     ```

3. Create a repo on GitHub (if you don’t have one):
   - GitHub → **New repository** → name e.g. `global_headlines` → **Private** → Create (no README).
   - Copy the URL: `https://github.com/YOUR_USERNAME/global_headlines.git`

4. Add the remote and push (only if you didn’t already have `origin`):
   ```powershell
   git remote add origin https://github.com/YOUR_USERNAME/global_headlines.git
   ```
   If it says “origin already exists”, use:
   ```powershell
   git remote set-url origin https://github.com/YOUR_USERNAME/global_headlines.git
   ```

5. Commit everything and push:
   ```powershell
   git add .
   git status
   ```
   Confirm **.env** and **global-headlines-474905-9494f258e0a5.json** are **not** in the list. Then:
   ```powershell
   git commit -m "Initial commit"   # or "Sync with VM setup"
   git push -u origin main
   ```
   (Use `master` instead of `main` if that’s your branch name.)

---

### On the VM (one-time: make the copied folder a Git repo)

You already have `/opt/global_headlines` with code, `.env`, `venv`, and the Google JSON. We’ll turn it into a clone of the same repo **without** overwriting `.env`, `venv`, or the JSON.

1. SSH in:
   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. Back up secrets and venv (they are not in Git):
   ```bash
   cp /opt/global_headlines/.env /root/.env.backup
   cp /opt/global_headlines/global-headlines-474905-9494f258e0a5.json /root/ 2>/dev/null || true
   ```

3. Remove only the project code (keep `.env` and `venv`):
   ```bash
   cd /opt/global_headlines
   find . -maxdepth 1 ! -name '.' ! -name '.env' ! -name 'venv' ! -name '..' -exec rm -rf {} + 2>/dev/null
   rm -rf workflow config docs requirements.txt helper.py send_semi_ai_newsletter.py 2>/dev/null
   ```

4. Clone your repo into a temp dir and move its contents into `/opt/global_headlines`:
   ```bash
   git clone https://github.com/YOUR_USERNAME/global_headlines.git /tmp/gh
   mv /tmp/gh/.git /opt/global_headlines/
   mv /tmp/gh/* /opt/global_headlines/
   mv /tmp/gh/.gitignore /opt/global_headlines/ 2>/dev/null || true
   rm -rf /tmp/gh
   ```

5. Restore `.env` and the Google JSON:
   ```bash
   cp /root/.env.backup /opt/global_headlines/.env
   cp /root/global-headlines-474905-9494f258e0a5.json /opt/global_headlines/ 2>/dev/null || true
   ```

6. Confirm you’re on the right branch and up to date:
   ```bash
   cd /opt/global_headlines
   git status
   git branch
   ```

Replace `YOUR_USERNAME` with your GitHub username. If the repo is **private**, when `git clone` asks for a password, use a **GitHub Personal Access Token** (not your GitHub password).

---

## From now on: every time you change code

### 1. On your laptop (after editing)

In your project folder:

```powershell
cd C:\Users\User\Desktop\AI\agents\global_headlines
git add .
git status
```

Check that only the files you changed are staged (no `.env`, no `global-headlines-*-*.json`). Then:

```powershell
git commit -m "Brief description of the change"
git push origin main
```

(Use `master` if that’s your branch.)

---

### 2. On the VM (to get your latest code)

SSH in, then:

```bash
cd /opt/global_headlines
git pull origin main
```

If the repo is private, use your **Personal Access Token** when Git asks for a password.

No need to touch `.env`, `venv`, or the Google JSON; they stay on the VM and are not in the repo. The 10am cron job will use the new code on the next run.

---

## Summary

| Where   | When              | Command |
|--------|-------------------|--------|
| Laptop | After you edit    | `git add .` → `git commit -m "..."` → `git push origin main` |
| VM     | When you want VM updated | `cd /opt/global_headlines` → `git pull origin main` |

You do **not** need to keep your laptop on for the 10am run; the VM runs it on its own.
