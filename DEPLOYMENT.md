# Deployment Guide - Insight2Dynasty League

This guide walks you through deploying the Insight2Dynasty League application to production using Railway.

## Prerequisites

- GitHub account (for CI/CD)
- Railway account (sign up at [railway.app](https://railway.app))
- Your code pushed to GitHub

---

## Option 1: Railway Deployment (Recommended)

### Step 1: Create Railway Account & Project

1. Go to [railway.app](https://railway.app) and sign up with GitHub
2. Click **"New Project"**
3. Choose **"Deploy from GitHub repo"**
4. Select your `Insight2DynastyLeague` repository
5. Railway will create a project

### Step 2: Add MySQL Database

1. In your Railway project dashboard, click **"+ New"**
2. Select **"Database"** → **"Add MySQL"**
3. Railway will provision a MySQL 8.0 database
4. The `DATABASE_URL` environment variable will be auto-populated

### Step 3: Deploy Backend Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repository again (for backend service)
3. In service settings:
   - **Name**: `insight2dynasty-backend`
   - **Root Directory**: Leave empty (railway.toml handles this)
   - **Start Command**: Will use railway.toml configuration

4. Add environment variables (Settings → Variables):
   ```
   DATABASE_URL=mysql+aiomysql://${{MySQL.USER}}:${{MySQL.PASSWORD}}@${{MySQL.HOST}}:${{MySQL.PORT}}/${{MySQL.DATABASE}}
   SLEEPER_LEAGUE_ID=1313933992642220032
   CORS_ORIGINS=http://localhost:5173,https://your-frontend-url.railway.app
   CRON_SECRET=<generate-secure-random-string>
   DEBUG=False
   APP_VERSION=1.0.0
   ```

   **To generate CRON_SECRET:**
   ```bash
   # On Linux/Mac
   openssl rand -base64 32

   # On Windows PowerShell
   -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | % {[char]$_})
   ```

5. Railway will automatically deploy when you push to `main` branch

### Step 4: Deploy Frontend Service

1. Click **"+ New"** → **"GitHub Repo"**
2. Select your repository again (for frontend service)
3. In service settings:
   - **Name**: `insight2dynasty-frontend`
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Start Command**: `npx serve -s dist -p $PORT`

4. Add environment variable:
   ```
   VITE_API_URL=https://your-backend-url.railway.app
   ```

5. Install serve package for static hosting:
   ```bash
   cd frontend
   npm install --save-dev serve
   ```

### Step 5: Run Database Migrations

1. In Railway backend service, click **"Settings"** → **"Deploy"**
2. Find the deployed service URL
3. Open Railway CLI or use the web-based shell:
   ```bash
   cd backend
   alembic upgrade head
   ```

   Or run locally against production database:
   ```bash
   # Set production DATABASE_URL temporarily
   export DATABASE_URL="<railway-database-url>"
   cd backend
   alembic upgrade head
   ```

### Step 6: Initial Data Sync

Trigger the initial data sync to populate your database:

```bash
curl -X POST https://your-backend-url.railway.app/api/sync/history
```

This will sync all historical data from Sleeper API.

### Step 7: Set Up Scheduled Sync (Railway Cron)

1. In Railway backend service, click **"Settings"** → **"Cron Jobs"**
2. Click **"Add Cron Job"**
3. Configure:
   - **Schedule**: `0 6 * * *` (6 AM UTC daily)
   - **Command**:
     ```bash
     curl -X POST ${{self.url}}/api/cron/sync -H "Authorization: Bearer ${{CRON_SECRET}}"
     ```

Alternatively, use GitHub Actions (already configured in `.github/workflows/scheduled-sync.yml`).

### Step 8: Update CORS Origins

After frontend deployment, update backend CORS_ORIGINS:

1. Go to backend service → **Variables**
2. Update `CORS_ORIGINS` to include your frontend URL:
   ```
   CORS_ORIGINS=https://your-frontend-url.railway.app,http://localhost:5173
   ```
3. Redeploy backend service

---

## GitHub Actions Setup

### Step 1: Add GitHub Secrets

1. Go to your GitHub repository
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add the following secrets:

   | Secret Name | Value | Description |
   |-------------|-------|-------------|
   | `RAILWAY_API_URL` | `https://your-backend.railway.app` | Your Railway backend URL |
   | `CRON_SECRET` | `<same-as-railway>` | Same secret used in Railway |

### Step 2: Verify Workflows

The repository includes two GitHub Actions workflows:

1. **[.github/workflows/deploy.yml](file:///d:/Projects/Insight2DynastyLeague/.github/workflows/deploy.yml)** - Runs on every push to `main`
   - Tests backend (pytest)
   - Builds frontend
   - Railway auto-deploys after tests pass

2. **[.github/workflows/scheduled-sync.yml](file:///d:/Projects/Insight2DynastyLeague/.github/workflows/scheduled-sync.yml)** - Runs daily at 6 AM UTC
   - Triggers `/api/cron/sync` endpoint
   - Syncs latest data from Sleeper API

### Step 3: Enable Workflows

Workflows are automatically enabled. You can manually trigger them from the **Actions** tab in GitHub.

---

## Alternative: Render Deployment

If you prefer Render over Railway:

### Backend (Web Service)

1. Create new **Web Service**
2. Connect GitHub repository
3. Configure:
   - **Name**: `insight2dynasty-backend`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. Add environment variables (same as Railway)

### Frontend (Static Site)

1. Create new **Static Site**
2. Connect GitHub repository
3. Configure:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm install && npm run build`
   - **Publish Directory**: `dist`

### Database

1. Create new **PostgreSQL** or **MySQL** database
2. Copy connection URL to backend environment variables

---

## Monitoring & Maintenance

### Health Checks

- Backend: `https://your-backend.railway.app/api/health`
- Frontend: `https://your-frontend.railway.app/`

### Logs

- Railway: View logs in service dashboard
- GitHub Actions: Check workflow runs in Actions tab

### Database Backups

Railway MySQL includes automatic daily backups. Access them from:
- Database service → **Backups** tab

### Manual Sync

Trigger a manual sync anytime:

```bash
curl -X POST https://your-backend.railway.app/api/cron/sync \
  -H "Authorization: Bearer YOUR_CRON_SECRET"
```

### Updating Code

1. Make changes locally
2. Commit and push to a feature branch
3. Create pull request
4. Merge to `main` after review
5. GitHub Actions runs tests
6. Railway auto-deploys if tests pass

---

## Troubleshooting

### Deployment Fails

- Check Railway build logs
- Verify all environment variables are set
- Ensure `requirements.txt` includes all dependencies

### Database Connection Issues

- Verify `DATABASE_URL` format: `mysql+aiomysql://user:pass@host:port/db`
- Check if MySQL service is running
- Run `alembic upgrade head` to apply migrations

### CORS Errors

- Update `CORS_ORIGINS` in backend to include frontend URL
- Redeploy backend after updating

### Scheduled Sync Not Running

- Check GitHub Actions workflow status
- Verify `CRON_SECRET` matches in GitHub and Railway
- Check Railway cron job configuration

---

## Cost Estimates

### Railway (Recommended)
- **Hobby Plan**: $5/month per service (backend + frontend)
- **MySQL**: ~$5/month
- **Total**: ~$15/month

### Render
- **Backend**: $7/month (Starter)
- **Frontend**: Free (Static site)
- **MySQL**: $7/month
- **Total**: ~$14/month

### Free Tier Options
- Railway: $5 free credit monthly (enough for low-traffic hobby projects)
- Render: Free tier available with limitations (spins down after inactivity)

---

## Security Checklist

- ✅ `CRON_SECRET` is strong and random (32+ characters)
- ✅ `DEBUG=False` in production
- ✅ `CORS_ORIGINS` only includes your domains
- ✅ Database credentials are not in git
- ✅ GitHub secrets are properly configured
- ✅ Health check endpoint is accessible
- ✅ HTTPS is enabled (automatic with Railway/Render)

---

## Next Steps

1. ✅ Deploy backend to Railway
2. ✅ Deploy frontend to Railway
3. ✅ Run database migrations
4. ✅ Perform initial data sync
5. ✅ Configure scheduled sync
6. ✅ Add GitHub secrets
7. ✅ Test deployment
8. ✅ Share your site!

For support, check:
- [Railway Docs](https://docs.railway.app)
- [FastAPI Docs](https://fastapi.tiangolo.com/deployment/)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
