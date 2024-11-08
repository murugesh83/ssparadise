import json
import requests
from flask import redirect, request, url_for, flash, current_app
from flask_login import login_user
from app import app, db
from models import User
from oauth_config import client, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_DISCOVERY_URL
from urllib.parse import urlencode, urljoin

def get_google_provider_cfg():
    try:
        return requests.get(GOOGLE_DISCOVERY_URL).json()
    except Exception as e:
        app.logger.error(f"Error fetching Google provider config: {str(e)}")
        return None

@app.route("/login/google")
def google_login():
    try:
        # Check if we have the required credentials
        if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
            flash("Google OAuth is not configured properly.", "error")
            return redirect(url_for("login"))

        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            raise Exception("Unable to fetch Google provider configuration")
            
        authorization_endpoint = google_provider_cfg["authorization_endpoint"]
        
        # Get the base URL from the current request
        base_url = request.url_root.rstrip('/')
        redirect_uri = f"{base_url}/login/google/callback"
        
        # Generate state parameter for security
        request_uri = client.prepare_request_uri(
            authorization_endpoint,
            redirect_uri=redirect_uri,
            scope=["openid", "email", "profile"]
        )
        return redirect(request_uri)
    except Exception as e:
        app.logger.error(f"Google login error: {str(e)}")
        flash("Unable to initialize Google login. Please try again later.", "error")
        return redirect(url_for("login"))

@app.route("/login/google/callback")
def google_callback():
    try:
        # Get authorization code Google sent back
        code = request.args.get("code")
        if not code:
            flash("Authentication failed - No authorization code received", "error")
            return redirect(url_for("login"))

        google_provider_cfg = get_google_provider_cfg()
        if not google_provider_cfg:
            flash("Authentication failed - Unable to fetch provider configuration", "error")
            return redirect(url_for("login"))

        token_endpoint = google_provider_cfg["token_endpoint"]
        
        # Get the base URL from the current request for the callback
        base_url = request.url_root.rstrip('/')
        redirect_uri = f"{base_url}/login/google/callback"

        # Prepare and send request to get tokens
        token_url, headers, body = client.prepare_token_request(
            token_endpoint,
            authorization_response=request.url,
            redirect_url=redirect_uri,
            code=code
        )

        token_response = requests.post(
            token_url,
            headers=headers,
            data=body,
            auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET),
        )

        # Parse the tokens
        client.parse_request_body_response(json.dumps(token_response.json()))

        # Get user info from Google
        userinfo_endpoint = google_provider_cfg["userinfo_endpoint"]
        uri, headers, body = client.add_token(userinfo_endpoint)
        userinfo_response = requests.get(uri, headers=headers)

        if userinfo_response.json().get("email_verified"):
            google_id = userinfo_response.json()["sub"]
            email = userinfo_response.json()["email"]
            name = userinfo_response.json().get("name", email.split('@')[0])

            # Check if user exists
            user = User.query.filter_by(email=email).first()
            if not user:
                # Create new user
                user = User(
                    email=email,
                    name=name,
                    is_admin=False
                )
                # Set a secure random password
                user.set_password(google_id + email)
                db.session.add(user)
                db.session.commit()

            # Begin user session
            login_user(user)
            flash('Successfully signed in with Google!', 'success')
            return redirect(url_for('index'))
        else:
            flash("Google authentication failed - Email not verified", "error")
            return redirect(url_for("login"))
            
    except Exception as e:
        app.logger.error(f"Google callback error: {str(e)}")
        flash("Authentication failed. Please try again later.", "error")
        return redirect(url_for("login"))
