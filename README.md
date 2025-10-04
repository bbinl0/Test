# Telegram Info Checker - Vercel Sub-API

This is a lightweight proxy API that forwards requests to the main Railway API.

## Features

- ✅ Serverless deployment on Vercel
- ✅ Same UI as the main application
- ✅ Forwards requests to Railway API
- ✅ No external dependencies

## Deployment to Vercel

1. **Install Vercel CLI** (optional, can also deploy via GitHub):
   ```bash
   npm i -g vercel
   ```

2. **Deploy from this folder**:
   ```bash
   cd vercel-api
   vercel
   ```

3. **Or deploy via GitHub**:
   - Push this folder to a GitHub repository
   - Import the project in Vercel dashboard
   - Deploy

## How it works

1. User visits the Vercel URL
2. User enters a Telegram username
3. Request goes to `/api/get_user_info`
4. Vercel serverless function forwards request to Railway API
5. Response is returned to the user

## API Endpoints

- `GET /` - Main page with the UI
- `GET /api/get_user_info?username={username}` - Get user information

## Main Railway API

The proxy forwards all requests to:
`https://web-production-27209.up.railway.app/get_user_info?username={username}`

## File Structure

```
vercel-api/
├── api/
│   └── get_user_info.py    # Serverless function
├── index.html              # Frontend UI
├── vercel.json             # Vercel configuration
├── requirements.txt        # Python dependencies (empty - using stdlib)
└── README.md              # This file
```
