# EhantiPOS - Restaurant Point of Sale System

A full-featured restaurant POS system built with Django. Designed for managing orders, menu items, tables, inventory, staff, expenses, and reporting — all from a clean, mobile-friendly interface.

## Features

### Core Modules

| Module | Description |
|---|---|
| **Dashboard** | Real-time overview of today's orders, revenue, expenses, profit, popular items, and low stock alerts |
| **Orders** | Create, edit, and track orders through their lifecycle (pending > preparing > served > paid). Supports dine-in, takeaway, and delivery with discounts and multiple payment methods |
| **Menu Management** | Categories and menu items with images, pricing, availability toggle, and ingredient linking for automatic stock deduction |
| **Table Management** | Track table capacity and status (available / occupied / reserved) with active order assignments |
| **Kitchen Display (KDS)** | Real-time kitchen screen showing pending and in-progress orders for kitchen staff |
| **Inventory** | Ingredient tracking with stock movements, cost per unit, minimum stock alerts, and automatic deduction when orders are placed |
| **Staff Management** | Staff profiles with roles, phone numbers, PIN codes for quick login, and avatar images |
| **Expenses** | Track expenses by category with receipt image uploads and payment method tracking |
| **Reports** | Sales reports by period (daily/weekly/monthly) and daily P&L summaries |
| **Settings** | Restaurant configuration (name, logo, currency, tax rate, hours), payment methods, roles & permissions, and user profiles |
| **Audit Logs** | Full action tracking with device, browser, OS, and IP detection |
| **Data Export** | CSV export for orders, expenses, inventory, and sales data |

### Additional Features

- **Role-Based Access Control** — 12 granular permission areas (dashboard, orders, menu, tables, kitchen, inventory, expenses, staff, roles, reports, settings, logs)
- **PIN-Based Quick Login** — Staff can log in with phone number + 4-digit PIN instead of username/password
- **Bilingual Support** — English and Somali language toggle
- **Printable Receipts** — Order receipts with restaurant logo and full details
- **AWS S3 Media Storage** — All uploaded images (menu items, avatars, receipts, logos) stored privately in S3 with pre-signed URLs
- **Low Stock Notifications** — Automatic alerts when ingredients fall below minimum threshold
- **Responsive Design** — Mobile-friendly UI built with Tailwind CSS

## Tech Stack

- **Backend:** Python 3.12 / Django 6.0
- **Database:** SQLite3
- **Frontend:** Django Templates + Tailwind CSS (CDN)
- **Media Storage:** AWS S3 (private, pre-signed URLs)
- **Authentication:** Django auth + custom PIN-based login

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- AWS account with an S3 bucket (for media storage)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd "Resturant POS"
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your AWS credentials:

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=lama-hamar-coffea-storage-app
AWS_S3_REGION_NAME=us-east-1
```

> **Important:** Never commit the `.env` file. It is already listed in `.gitignore`.

### 5. Run Database Migrations

```bash
python manage.py migrate
```

### 6. Create a Superuser (Admin Account)

```bash
python manage.py createsuperuser
```

Follow the prompts to set a username, email, and password.

### 7. Start the Development Server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000** in your browser.

## AWS S3 Setup

Media files (menu item images, staff avatars, expense receipts, restaurant logo) are stored in AWS S3 with private access. Files are served using **pre-signed URLs** that expire after 1 hour.

### S3 Bucket Configuration

1. Create an S3 bucket in the **us-east-1** region
2. Keep **Block Public Access** enabled (all files are private)
3. Create an IAM user with `AmazonS3FullAccess` policy (or a scoped policy for your bucket)
4. Copy the Access Key ID and Secret Access Key into your `.env` file

### Bucket Policy (Optional - Scoped Access)

If you want to restrict access to only the POS bucket, create a custom IAM policy:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:GetObject",
                "s3:PutObject",
                "s3:DeleteObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::lama-hamar-coffea-storage-app",
                "arn:aws:s3:::lama-hamar-coffea-storage-app/*"
            ]
        }
    ]
}
```

## Project Structure

```
Resturant POS/
├── core/                       # Main Django app
│   ├── migrations/             # Database migrations
│   ├── templates/core/         # HTML templates (37 files)
│   ├── templatetags/           # Custom template tags (translations)
│   ├── admin.py                # Django admin config
│   ├── context_processors.py   # Template context (settings, perms, notifications)
│   ├── decorators.py           # Permission checking decorator
│   ├── forms.py                # Django forms
│   ├── logging_utils.py        # Audit & error logging
│   ├── middleware.py            # AuditLog middleware
│   ├── models.py               # Database models (15 models)
│   ├── translations.py         # English-Somali translations
│   ├── urls.py                 # URL routes (104 endpoints)
│   └── views.py                # View functions (64 views)
├── restaurant/                 # Django project settings
│   ├── settings.py             # Main configuration
│   ├── urls.py                 # Root URL config
│   └── wsgi.py                 # WSGI entry point
├── static/                     # Static files (CSS, favicon)
│   ├── css/custom.css
│   └── images/favicon.svg
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── manage.py                   # Django management script
└── requirements.txt            # Python dependencies
```

## Database Models

| Model | Purpose |
|---|---|
| `Order` | Orders with type (dine-in/takeaway/delivery), status, payment, discounts |
| `OrderItem` | Individual items within an order |
| `MenuItem` | Menu items with price, image, category, availability |
| `Category` | Menu categories |
| `Table` | Dine-in tables with capacity and status |
| `Ingredient` | Stock items with quantity, unit, min stock level |
| `MenuItemIngredient` | Links menu items to ingredients with quantity ratios |
| `StockMovement` | Audit trail for stock changes |
| `Staff` | Staff profiles linked to Django users with role, PIN, avatar |
| `Role` | Custom roles with JSON-stored permissions |
| `Attendance` | Daily check-in/out tracking |
| `PaymentMethod` | Payment options (cash, card, mobile, etc.) |
| `Expense` | Expense records with category and receipt |
| `ExpenseCategory` | Expense types |
| `RestaurantSettings` | Global config (name, currency, tax rate, logo, hours) |
| `AuditLog` | User action tracking with device/browser/IP info |
| `ErrorLog` | Application error tracking |

## User Roles & Permissions

The system uses role-based access control with these permission areas:

`dashboard` `orders` `menu` `tables` `kitchen` `inventory` `expenses` `staff` `roles` `reports` `settings` `logs`

- **Superusers** have access to everything
- **Staff members** are assigned a role with specific permissions
- Views are protected with the `@permission_required` decorator

## Default Login

After creating a superuser, log in at **http://127.0.0.1:8000/login/** with your credentials.

To set up PIN-based quick login:
1. Go to **Settings > Profile**
2. Set a 4-digit PIN code
3. Staff can then log in using their phone number + PIN

## Contributing

1. Clone the repository
2. Create a new branch for your feature
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is proprietary software developed by Dhistech.
