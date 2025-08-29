from flask import Flask, request, jsonify
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, auth, firestore
import datetime

app = Flask(__name__)
CORS(app)

# 🔹 Firebase setup
cred = credentials.Certificate("firebase-adminsdk.json")  # Your Firebase admin SDK JSON
firebase_admin.initialize_app(cred)
db = firestore.client()

# 🔹 Static admin credentials
ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "admin123"


@app.route("/")
def home():
    return jsonify({"message": "✅ Flask backend is running!"})


# 🔹 Admin login (static)
@app.route("/admin-login", methods=["POST"])
def admin_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
        return jsonify({"success": True, "role": "admin", "message": "Admin login successful"}), 200

    return jsonify({"success": False, "message": "Invalid admin credentials"}), 401


# 🔹 Signup for normal users
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    if email == ADMIN_EMAIL:
        return jsonify({"success": False, "error": "This email is reserved for admin."}), 403

    try:
        # Create Firebase user
        user = auth.create_user(email=email, password=password, display_name=name)

        # Add user to Firestore
        db.collection("users").document(user.uid).set({
            "uid": user.uid,
            "name": name,
            "email": email,
            "role": "user",
            "createdAt": datetime.datetime.utcnow()
        })

        return jsonify({"success": True, "uid": user.uid, "message": "User created successfully"}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# 🔹 Login (normal + Google users)
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    idToken = data.get("idToken")

    if not idToken:
        return jsonify({"success": False, "error": "ID token is required"}), 400

    try:
        # Verify Firebase ID token
        decoded_token = auth.verify_id_token(idToken)
        uid = decoded_token["uid"]
        email = decoded_token.get("email")
        name = decoded_token.get("name") or decoded_token.get("displayName") or "Unknown"

        # Check if user exists in Firestore
        user_ref = db.collection("users").document(uid)
        user_doc = user_ref.get()

        if not user_doc.exists:
            # First time login → create user doc
            user_ref.set({
                "uid": uid,
                "name": name,
                "email": email,
                "role": "user",
                "createdAt": datetime.datetime.utcnow()
            })
            user_data = {"uid": uid, "name": name, "email": email, "role": "user"}
        else:
            user_data = user_doc.to_dict()

        return jsonify({
            "success": True,
            "user": user_data,
            "role": user_data.get("role", "user")
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


# 🔹 Optional: Get all users (Admin only)
@app.route("/users", methods=["GET"])
def get_users():
    try:
        users = []
        docs = db.collection("users").stream()
        for doc in docs:
            users.append(doc.to_dict())
        return jsonify({"success": True, "users": users}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


if __name__ == "__main__":
    app.run(debug=True)
