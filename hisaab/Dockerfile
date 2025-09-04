FROM python:3.11-slim

WORKDIR /code

# Copy requirements from hisaab folder
COPY hisaab/requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app folder from inside hisaab
COPY hisaab/app ./app

# Run FastAPI app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
