from app import app

if __name__ == "__main__":
    app.run(
        host='0.0.0.0',
        port=5000,  # Changed to port 5000 as per flask_website guidelines
        debug=True
    )
