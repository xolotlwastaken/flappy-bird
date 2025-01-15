# Use an official Python runtime as a base image
FROM python:3.9-slim

# Set the working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY . .

# Ensure the templates directory is copied
COPY templates/ templates/

# Expose the port Flask will run on
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
