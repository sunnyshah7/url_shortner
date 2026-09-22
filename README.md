# URL Shortener

A full-stack URL shortener built with React, FastAPI, and SQLite. Paste a long URL into the web interface to create a compact link, copy it, search previously created links, or remove links that are no longer needed.

The repository also includes shell scripts for deploying the application to an Ubuntu EC2 instance behind Nginx.

![URL Shortener interface](URL_frontend/src/assets/hero.png)

## Features

- Creates six-character, alphanumeric short codes for valid HTTP(S) URLs.
- Redirects a short code to its original URL.
- Returns an existing code when the same original URL is shortened again.
- Lists, filters, copies, refreshes, and deletes shortened URLs from the UI.
- Validates submitted URLs through the browser and FastAPI/Pydantic.
- Supports a configurable frontend API endpoint using `VITE_API_URL`.
- Includes EC2 setup scripts for FastAPI as a systemd service and React behind Nginx.

## Architecture

```text
Browser
  │
  ├── React + Vite frontend
  │     └── /api/* in production
  │
  └── Nginx (production)
          ├── serves the React build
          └── proxies /api/* to FastAPI on port 8000
                                      │
                                      └── SQLite database (urls.db)
```

For local development, the frontend defaults to `http://127.0.0.1:8000` and calls FastAPI directly. In the included Nginx deployment configuration, the frontend uses `/api`, which Nginx forwards to the FastAPI service.

## Tech stack

| Area | Technology |
| --- | --- |
| Frontend | React 19, Vite 8, Lucide React |
| Backend | FastAPI, Pydantic, SQLAlchemy |
| Database | SQLite |
| Production web server | Nginx |
| Process manager | systemd |
| AWS adapter | Mangum (included for Lambda-compatible deployments) |

## Repository layout

```text
.
├── URL_backend/
│   ├── main.py                 # FastAPI routes, database model, and redirect logic
│   └── requirements.txt        # Backend dependencies
├── URL_frontend/
│   ├── src/App.jsx             # Main React interface and API calls
│   ├── src/App.css             # Application styling
│   ├── public/                 # Static assets
│   ├── package.json            # Frontend scripts and dependencies
│   └── vite.config.js          # Vite configuration
├── aws_setup/
│   ├── ec2_setup.sh            # Ubuntu prerequisites and repository checkout
│   ├── backend_setup.sh        # Python environment and systemd service setup
│   ├── frontend_setup.sh       # Nginx configuration and frontend deployment
│   ├── deploy_frontend.sh      # Rebuild and copy the frontend to Nginx
│   └── Lambda_function.py      # Alternative DynamoDB-backed Lambda prototype
├── requirements.txt            # Root-level Python dependency snapshot
└── README.md
```

## Prerequisites

For local development, install:

- Python 3.10 or later
- Node.js 20 or later (Node.js 22 is used by the EC2 setup script)
- npm

## Run locally

### 1. Start the backend

From the repository root:

```bash
cd URL_backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

FastAPI starts at `http://127.0.0.1:8000`. The interactive API documentation is available at `http://127.0.0.1:8000/docs`.

On first startup, SQLAlchemy creates `URL_backend/urls.db`. This is the local SQLite database containing the shortened URL records.

### 2. Start the frontend

Open a second terminal:

```bash
cd URL_frontend
npm install
npm run dev
```

Vite prints the local address (normally `http://localhost:5173`). Open it in a browser and submit a URL such as `https://www.example.com`.

The frontend's default API endpoint is `http://127.0.0.1:8000`, so no environment file is required for this local setup.

## Configuration

The frontend reads its API base URL from `VITE_API_URL`:

```bash
# URL_frontend/.env.local
VITE_API_URL=http://127.0.0.1:8000
```

Vite environment values are baked into the build. Restart the development server after changing `.env.local`, and rebuild before deploying a production change.

For the provided Nginx setup, create or use the production value below:

```bash
# URL_frontend/.env.production
VITE_API_URL=/api
```

## API reference

All responses use `original_url`, `short_code`, and `short_url` unless otherwise noted.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/shorten` | Create or retrieve a short URL |
| `GET` | `/all` | List all stored URLs |
| `GET` | `/{short_code}` | Redirect to the original URL |
| `DELETE` | `/delete/{short_code}` | Delete a short URL |

### Create a short URL

```bash
curl -X POST http://127.0.0.1:8000/shorten \
  -H 'Content-Type: application/json' \
  -d '{"original_url":"https://www.example.com/a/long/path"}'
```

Example response:

```json
{
  "original_url": "https://www.example.com/a/long/path",
  "short_code": "aB72xQ",
  "short_url": "http://localhost:8000/aB72xQ"
}
```

### List URLs

```bash
curl http://127.0.0.1:8000/all
```

### Follow a redirect

```bash
curl -I http://127.0.0.1:8000/aB72xQ
```

### Delete a URL

```bash
curl -X DELETE http://127.0.0.1:8000/delete/aB72xQ
```

## Frontend commands

Run these from `URL_frontend/`:

| Command | Description |
| --- | --- |
| `npm run dev` | Start the Vite development server with hot reload |
| `npm run build` | Create a production build in `dist/` |
| `npm run preview` | Preview the production build locally |
| `npm run lint` | Run Oxlint |

## EC2 and Nginx deployment

The `aws_setup/` scripts target Ubuntu and assume the repository is cloned to `$HOME/URL_Shortner`. If you clone it elsewhere, update `PROJECT_DIR` in the scripts before running them.

1. Launch an Ubuntu EC2 instance and allow inbound TCP port 80 in its security group. For direct backend access, additionally allow port 8000 only when required.
2. Copy the repository to the instance or run `aws_setup/ec2_setup.sh`. The script installs Git and Python, then clones the repository configured within it.
3. Run `aws_setup/backend_setup.sh`. It creates a backend virtual environment, installs dependencies, and creates the `url-shortener` systemd service listening on port 8000.
4. Run `aws_setup/frontend_setup.sh`. It installs Nginx and Node.js, writes `URL_frontend/.env.production` with `VITE_API_URL=/api`, builds the frontend, and configures Nginx to serve the app and proxy `/api/` to FastAPI.
5. On subsequent frontend-only releases, run `aws_setup/deploy_frontend.sh` to rebuild and copy `dist/` into `/var/www/url-shortener`.

Useful service commands:

```bash
sudo systemctl status url-shortener
sudo systemctl restart url-shortener
sudo journalctl -u url-shortener -f

sudo nginx -t
sudo systemctl status nginx
sudo systemctl restart nginx
```

## Important production notes

- **Set the public short-link base URL.** The FastAPI API currently returns short URLs in the form `http://localhost:8000/{short_code}`. That works locally, but a public deployment should derive this value from an environment-configured public base URL (for example, `https://short.example.com`).
- **SQLite is local to one server.** It is suitable for development or a small single-instance deployment. Use a managed relational database such as PostgreSQL for multi-instance production deployments, backups, and durable storage.
- **Restrict CORS.** The backend currently permits all origins, methods, and headers. Replace this with the production frontend origin(s).
- **Use HTTPS.** The included Nginx configuration listens on HTTP only. Add a TLS certificate and redirect HTTP traffic before exposing the service publicly.
- **Protect management endpoints.** `/all` and `/delete/{short_code}` have no authentication. Add account ownership and authorization before using the application for shared or sensitive data.
- **Avoid committing local data and environments.** Do not commit `urls.db`, Python virtual environments, frontend `node_modules`, or private `.env` files.

## Alternative AWS Lambda prototype

`aws_setup/Lambda_function.py` is a separate, DynamoDB-backed Lambda prototype. It is not wired into the React application or the FastAPI deployment scripts. It handles `POST` and `DELETE` requests and expects a DynamoDB table named `urls` keyed by `short_code`.

Use this path only after configuring API Gateway routes, Lambda permissions, DynamoDB table design, CORS, and a public redirect strategy. The main supported local and EC2 workflow is the FastAPI application in `URL_backend/main.py`.

## Current limitations

- Short codes are randomly generated and are six characters long; collisions are checked before FastAPI records are inserted.
- There are no user accounts, analytics, expiration dates, rate limits, or custom aliases.
- The backend returns every stored URL from `/all`; it does not paginate results.
- The displayed theme button is currently visual only.

## License

No license file is included. Add a license before distributing or open-sourcing the project.
