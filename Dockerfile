# Python version: 3.9
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /usr/src/app

# Create a virtual environment and activate it
RUN python -m venv venv
ENV PATH="/usr/src/app/venv/bin:$PATH"

# Copy the current directory contents into the container at /usr/src/app
COPY . .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run live.py when the container launches
CMD ["gunicorn", "-b", "0.0.0.0:5000", "main:app"]
