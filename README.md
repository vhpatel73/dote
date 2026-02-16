# DOTE - Department of Technology Efficiency

DOTE is a modern enterprise web application designed to track and analyze AI initiatives, capabilities, and realized benefits across the organization.

## Tech Stack
- **Backend**: Django (Python 3.11)
- **Database**: AlloyDB (PostgreSQL)
- **Frontend**: Django Templates + Chart.js + CSS Glassmorphism
- **Hosting**: Google Cloud Run
- **CI/CD**: Cloud Build

## Local Development
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Set up environment:
   Create a `.env` file with `DEBUG=True`, `SECRET_KEY`, and `DATABASE_URL`.
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Start dev server:
   ```bash
   python manage.py runserver
   ```

## GCP Deployment
1. Enable Cloud Run, Cloud Build, and AlloyDB APIs.
2. Create an AlloyDB instance and cluster.
3. Deploy using the provided `cloudbuild.yaml`:
   ```bash
   gcloud builds submit --config cloudbuild.yaml .
   ```
4. Set the `DATABASE_URL` environment variable in the Cloud Run service.
