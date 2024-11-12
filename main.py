from app import app

if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=5000,  # Using port 5000 as per flask_website guidelines
        debug=True  # Enable debug mode for development
    )
