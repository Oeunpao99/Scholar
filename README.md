# SCHOLAR (ប្រព័ន្ធគ្រប់គ្រងការចុះឈ្មោះសិស្សបាក់ឌុប)

> **Enterprise Daily Student Enrollment Management System for Cambodian High School Diplomas (BacII / បាក់ឌុប)**

SCHOLAR is a specialized university & scholarship enrollment tracking and daily reporting system designed for Cambodian educational institutions and scholarship committees. It tracks applicants across academic categories, BacII grades (A, B, C, D, E), and demographic breakdowns (Total, Female, Phnom Penh, Provinces) with strict mathematical consistency, real-time cumulative projection, automated official Khmer Telegram broadcasts, and OCR/AI ingestion.

---

## 🌟 Key Features

1. **Daily Gain Invariant & Auto-Summing**
   - Staff enter **today's gain only** (new applicants registered today).
   - Real-time client & server validation enforces the fundamental invariant:
     $$\text{Total} = \text{Phnom Penh} + \text{Provinces (KP)}$$
     $$\text{Total} \ge \text{Female}$$
   - Grand totals and category aggregates update live as numbers are typed.

2. **Dynamic Cumulative Projections**
   - Cumulative totals are dynamically derived from ledger history and snapshots.
   - Staff preview running cumulative counts before committing records.

3. **Official Khmer Telegram Broadcast Center**
   - Automatically renders formatted Khmer messages matching official Ministry layouts.
   - Includes Roman numeral categories (`I.`, `II.`, `III.`), grade distribution breakdowns, and grand totals.
   - 1-click clipboard copy with confetti animation, zero-padding toggles, and direct Telegram Bot broadcast via Bot API.

4. **AI & Khmer OCR Assistant**
   - Dual-mode ingestion: paste Telegram message text or upload photos/scans of paper ledger sheets.
   - Powered by built-in regex rules, Tesseract OCR with Khmer language training (`tesseract-ocr-khm`), and LLM extractors.
   - 1-click preview and commit directly into the database.

5. **Multi-Format Export & Analytics**
   - Export filtered ledger data to **Excel (.xlsx)** with multi-tab grade breakdowns.
   - Generate official printable **PDF documents** and raw **CSV datasets**.
   - Interactive cumulative time-series charts and geographic distribution metrics.

6. **Enterprise Governance & Security**
   - Role-Based Access Control (RBAC): `superadmin`, `admin`, `manager`, `staff`, `viewer`.
   - Comprehensive audit logging (`AuditLog`) capturing user, IP, action, entity, timestamp, and JSON diffs.
   - System settings with dynamic Academic Year switching (automatically updating category titles).

---

## 🏗️ Architecture & Tech Stack

```
                   ┌───────────────────────────────────┐
                   │  React 18 + TypeScript + Vite UI  │
                   │ (Khmer OS Muol Light + Siemreap)  │
                   └─────────────────┬─────────────────┘
                                     │ HTTP / REST
                                     ▼
                   ┌───────────────────────────────────┐
                   │       FastAPI Python Backend      │
                   │   (Async SQLAlchemy 2 + Pydantic) │
                   └──────────┬──────────────┬─────────┘
                              │              │
                     ┌────────▼──────┐   ┌───▼───────────┐
                     │ PostgreSQL 17 │   │ Redis 7 Cache │
                     └───────────────┘   └───────────────┘
```

- **Backend:** Python 3.13, FastAPI, SQLAlchemy 2.0 (Asyncpg), Alembic, Pydantic v2, Pytest (70/70 tests passing).
- **Frontend:** React 18, TypeScript, Vite, Vanilla CSS Design System with Luxury Dark Glassmorphism, Lucide Icons, Canvas Confetti.
- **Typography:** `Khmer OS Muol Light` for headings, `Khmer OS Siemreap` for everything else. Both are bundled at `frontend/public/fonts/` (the installed copy is used when available).
- **OCR:** Tesseract 5 with `tesseract-ocr-khm`.
- **Infrastructure:** Docker & Docker Compose with multi-stage production builds and Nginx.

---

## 🚀 Quick Start with Docker

### 1. Configure Environment
Copy the template configuration:
```bash
cp .env.example .env
```

### 2. Start Application
```bash
docker compose up -d --build
```

### 3. Access Services
- **Web Application:** [http://localhost:5173](http://localhost:5173)
- **API Documentation (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)
- **Health Check:** [http://localhost:8000/health](http://localhost:8000/health)

### 4. Default Seed Credentials
- **Email:** `admin@scholar.local`
- **Password:** `ChangeMe123!`
*(A 1-click demo login button is provided on the login page)*

---

## 💻 Local Development Setup

### Backend Setup
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Or on Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Set test database and run migrations
alembic upgrade head

# Run development server
uvicorn app.main:app --reload --port 8000
```

### Running Backend Tests
```bash
cd backend
pytest tests/
```
*Current test suite: **70 passed in 16.66s** (100% passing).*

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
The frontend dev server will launch at [http://localhost:5173](http://localhost:5173).

To build for production:
```bash
npm run build
```

---

## 📊 Domain Categories & BacII Grades

### Categories
- **ផ្នែកទី ១ (Category I):** សិស្សចុះឈ្មោះក្នុងឆ្នាំបច្ចុប្បន្ន (ឧ. ឆ្នាំ២០២៦) (`current_year`)
- **ផ្នែកទី ២ (Category II):** សិស្សចុះឈ្មោះមុនឆ្នាំបច្ចុប្បន្ន (ឧ. មុនឆ្នាំ២០២៦) (`before_current_year`)
- **ផ្នែកទី ៣ (Category III):** សិស្សមកពីបណ្តាខេត្តផ្សេងៗ (`other_province`)

### BacII Grade Levels
- **និទ្ទេស A (Grade A):** ពិន្ទុឆ្នើម
- **និទ្ទេស B (Grade B):** ពិន្ទុល្អណាស់
- **និទ្ទេស C (Grade C):** ពិន្ទុល្អ
- **និទ្ទេស D (Grade D):** ពិន្ទុមធ្យម
- **និទ្ទេស E (Grade E):** ពិន្ទុជាប់កម្រិតមូលដ្ឋាន

---

## 🔒 Security & RBAC Roles

| Role | Permissions |
|---|---|
| `superadmin` | Full control: system settings, user management, audit logs, create/edit/delete records |
| `admin` | System administration, user management, audit logs, ledger operations |
| `manager` | Review, approve, update daily entries, export reports, send Telegram broadcasts |
| `staff` | Create daily entries, view history, preview Telegram format, scan OCR |
| `viewer` | Read-only access to dashboard and reports |

---

## 📄 License
Proprietary & Confidential - Built for University & Scholarship Committee Enrollment Management.
