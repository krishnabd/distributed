# Use the official Python image as the base image
FROM python:3.9

# Set the working directory in the container
WORKDIR /app


# Copy the content of the local src directory to the working directory
COPY . .

# Expose port 5000 to the outside world
EXPOSE 80

# Command to run the Flask application
CMD ["python", "app.py"]
