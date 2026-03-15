# Step-by-step: Use Git to sync local code with the VM

Use a Git repo so you can edit on your laptop, push, then pull on the VM. Secrets (`.env`, Google JSON) stay off the repo.

---

## Part A: One-time setup

### Step 1. Create a repo on GitHub (or GitLab)

1. Go to [github.com](https://github.com) and sign in.
2. Click **+** → **New repository**.
3. Name it (e.g. `global_headlines`).
4. Choose **Private** if you don’t want it public.
5. **Do not** add a README, .gitignore, or license (you already have a project).
6. Click **Create repository**.
7. Copy the repo URL, e.g. `https://github.com/YOUR_USERNAME/global_headlines.git`.

---

### Step 2. One-time Git setup on your laptop

Open **PowerShell** (or Git Bash) and go to your project folder:

```powershell
cd C:\Users\User\Desktop\AI\agents\global_headlines
```

**If this folder is not yet a Git repo:**

```powershell
git init
git branch -M main
git add .
git status
```

Check that **`.env`** and **`global-headlines-474905-9494f258e0a5.json`** do **not** appear under “Changes to be committed”. If they do, they’re not ignored; tell me and we’ll fix `.gitignore`.

Then:

```powershell
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/global_headlines.git
git push -u origin main
```

Use your **actual repo URL** and branch name if different (e.g. `master`).

**If this folder is already a Git repo** (you see a `.git` folder):

```powershell
git status
git add .
git commit -m "Sync project for VM"
git remote add origin https://github.com/YOUR_USERNAME/global_headlines.git
git push -u origin main
```

If `origin` already exists, use:

```powershell
git remote set-url origin https://github.com/YOUR_USERNAME/global_headlines.git
git push -u origin main
```

---

### Step 3. One-time setup on the VM

SSH into the droplet:

```bash
ssh root@YOUR_DROPLET_IP
```

**Option A – VM already has `/opt/global_headlines` from earlier (e.g. scp)**

Turn it into a Git clone and keep your existing `.env` and `venv`:

```bash
cd /opt/global_headlines

# Back up .env and Google JSON (they are not in Git)
cp .env /root/.env.backup
cp global-headlines-474905-9494f258e0a5.json /root/ 2>/dev/null || true

# Remove everything except .env and venv
find . -maxdepth 1 ! -name '.' ! -name '.env' ! -name 'venv' ! -name '..' -exec rm -rf {} +
rm -rf workflow config docs requirements.txt 2>/dev/null || true

# Clone the repo into a temp folder, then move contents here
git clone https://github.com/YOUR_USERNAME/global_headlines.git /tmp/gh
mv /tmp/gh/.git .
mv /tmp/gh/* .
mv /tmp/gh/.gitignore . 2>/dev/null || true
rm -rf /tmp/gh

# Restore .env and Google JSON
cp /root/.env.backup .env
cp /root/global-headlines-474905-9494f258e0a5.json . 2>/dev/null || true
```

**Option B – Clean VM (no project yet)**

```bash
cd /opt
rm -rf global_headlines
git clone https://github.com/YOUR_USERNAME/global_headlines.git global_headlines
cd global_headlines
```

Then create `.env` and copy the Google JSON onto the VM (as in the droplet setup guide). Create the venv and install deps:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Replace `YOUR_USERNAME` and repo URL with your real values. If the repo is private, use a **Personal Access Token** instead of password when Git asks:

- GitHub: Settings → Developer settings → Personal access tokens → Generate new token (classic), tick `repo`.
- Use the token as the password when you `git clone` or `git pull` on the VM.

---

## Part B: Daily workflow (sync code to VM)

### When you change code on your laptop

1. Save your files.
2. In PowerShell (in your project folder):

   ```powershell
   cd C:\Users\User\Desktop\AI\agents\global_headlines
   git add .
   git status
   ```

   Confirm only the files you changed are listed (no `.env`, no Google JSON).

3. Commit and push:

   ```powershell
   git commit -m "Short description of what you changed"
   git push origin main
   ```

---

### Update the VM with your latest code

1. SSH into the droplet:

   ```bash
   ssh root@YOUR_DROPLET_IP
   ```

2. Pull the latest code:

   ```bash
   cd /opt/global_headlines
   git pull origin main
   ```

3. If the repo is private and it asks for a password, use your **GitHub Personal Access Token**, not your GitHub password.

That’s it. The 10am cron job will run the new code next time.

---

## Quick reference

| Where        | What to do |
|-------------|------------|
| **Laptop**  | Edit code → `git add .` → `git commit -m "message"` → `git push origin main` |
| **VM**      | `cd /opt/global_headlines` → `git pull origin main` |

Never commit `.env` or `global-headlines-*-*.json`; they stay only on your laptop and VM.
