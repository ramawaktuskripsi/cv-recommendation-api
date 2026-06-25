# 🚀 Railway Deployment Guide

## Deployment Method: GitHub + Railway Dashboard

Karena Railway CLI belum terinstall, kita akan deploy via GitHub + Railway Dashboard (lebih mudah).

---

## 📋 Prerequisites

✅ Git repository initialized
✅ Code committed
⏳ GitHub repository (need to create/push)
⏳ Railway account

---

## 🔧 Step-by-Step Deployment

### **Step 1: Push to GitHub**

#### **Option A: Jika sudah ada GitHub repo**

```bash
# Check remote
git remote -v

# Push ke GitHub
git push origin main
```

#### **Option B: Jika belum ada GitHub repo**

1. Buka https://github.com/new
2. Buat repository baru (nama: `cv-parser-api`)
3. **JANGAN** centang "Initialize with README"
4. Click "Create repository"

5. Jalankan commands:
```bash
git remote add origin https://github.com/YOUR_USERNAME/cv-parser-api.git
git branch -M main
git push -u origin main
```

---

### **Step 2: Deploy ke Railway**

1. **Buka Railway Dashboard**
   - Go to: https://railway.app/
   - Login/Sign up (bisa pakai GitHub account)

2. **Create New Project**
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access GitHub
   - Select repository: `cv-parser-api`

3. **Railway Auto-Detect**
   - Railway akan auto-detect Python project
   - Akan menggunakan `railway.toml` config yang sudah kita buat
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app --bind 0.0.0.0:$PORT`

4. **Wait for Deployment**
   - Railway akan build & deploy (~3-5 minutes)
   - Watch logs untuk progress

5. **Get Deployment URL**
   - Setelah deploy selesai, Railway akan kasih URL
   - Format: `https://cv-parser-api-production.up.railway.app`

---

### **Step 3: Configure Environment Variables (Optional)**

Di Railway Dashboard → Settings → Variables:

```
FLASK_ENV=production
PORT=5000
```

(PORT biasanya auto-set oleh Railway)

---

### **Step 4: Test Deployment**

#### **Health Check:**
```bash
curl https://your-app.railway.app/api/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-12-10T...",
  "version": "1.0.0"
}
```

#### **Test Process Endpoint:**
```bash
curl -X POST https://your-app.railway.app/api/process-complete \
  -H "Content-Type: application/json" \
  -d '{
    "cv_url": "https://example.com/sample.pdf",
    "job_id": "test-123",
    "application_id": "app-456",
    "job_title": "Test Position",
    "required_skills": ["Quality Control", "Leadership"]
  }'
```

---

## 🔍 Troubleshooting

### **Build Fails:**

**Check Railway Logs:**
- Railway Dashboard → Deployments → View Logs

**Common Issues:**

1. **Missing dependencies:**
   - Pastikan `requirements.txt` complete
   - Check Python version di `runtime.txt`

2. **spaCy model download fails:**
   - Sudah handled di `railway.toml`:
   ```toml
   cmds = [
     "pip install -r requirements.txt",
     "python -m spacy download en_core_web_sm",
     "python -c 'import nltk; nltk.download(\"punkt\")'"
   ]
   ```

3. **Port binding error:**
   - Railway auto-set `$PORT` environment variable
   - App sudah configured: `PORT = int(os.environ.get('PORT', 5000))`

---

## 📊 Deployment Files

Pastikan files ini ada di repository:

- ✅ `app.py` - Main application
- ✅ `requirements.txt` - Dependencies
- ✅ `runtime.txt` - Python version (3.9.13)
- ✅ `Procfile` - Process command (backup)
- ✅ `railway.toml` - Railway config (primary)
- ✅ `.gitignore` - Ignore venv, temp files

---

## 🎯 Alternative: Railway CLI (Optional)

Jika ingin install Railway CLI:

### **Windows (PowerShell):**
```powershell
iwr https://railway.app/install.ps1 | iex
```

### **Deploy via CLI:**
```bash
railway login
railway init
railway up
```

---

## 📝 Post-Deployment

### **1. Get API URL**
Copy URL dari Railway dashboard, contoh:
```
https://cv-parser-api-production-xxxx.up.railway.app
```

### **2. Share dengan Frontend Team**

Kirim ke rekan:
- ✅ API Base URL
- ✅ `INTEGRATION_GUIDE.md`
- ✅ API endpoints documentation

### **3. Update Frontend Code**

Frontend perlu update API URL:
```typescript
const API_URL = 'https://cv-parser-api-production-xxxx.up.railway.app'

const response = await fetch(`${API_URL}/api/process-complete`, {
  method: 'POST',
  // ...
})
```

---

## 🔄 Future Updates

Untuk update code:

```bash
# 1. Make changes
# 2. Commit
git add .
git commit -m "Update: ..."

# 3. Push
git push origin main

# 4. Railway auto-deploy! 🚀
```

Railway akan auto-deploy setiap kali ada push ke `main` branch.

---

## 📊 Monitoring

**Railway Dashboard:**
- Metrics: CPU, Memory, Network
- Logs: Real-time application logs
- Deployments: History & rollback

**Health Check Endpoint:**
```
GET /api/health
```

Monitor ini secara berkala untuk ensure API running.

---

## 💰 Railway Pricing

**Free Tier:**
- $5 credit per month
- Enough untuk development/testing
- ~500 hours runtime

**Pro Plan:**
- $20/month
- Untuk production use

---

## ✅ Checklist

- [ ] Push code to GitHub
- [ ] Create Railway project
- [ ] Connect GitHub repo
- [ ] Wait for deployment
- [ ] Test health endpoint
- [ ] Test process endpoint
- [ ] Share API URL with team
- [ ] Update frontend API URL

---

## 🎉 Success Indicators

✅ Railway deployment status: "Active"
✅ Health check returns 200 OK
✅ Process endpoint accepts requests
✅ Logs show no errors

---

**Ready to deploy!** 🚀

Pilih salah satu:
1. **GitHub + Railway Dashboard** (Recommended - easier)
2. **Railway CLI** (Install dulu)
