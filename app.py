import os
import random
from string import ascii_uppercase
from datetime import datetime
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_socketio import join_room, leave_room, send, SocketIO
from mysql.connector.errors import IntegrityError
import mysql.connector
import google.generativeai as ai
from werkzeug.utils import secure_filename
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv
import tensorflow as tf
import requests

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = "your_secret_key"  # Replace with a strong secret key
socketio = SocketIO(app)

# Load environment variables from .env file
load_dotenv()

# Database connection setup
def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="mindo"
    )

# Retrieve API key from environment variable
API_KEY = os.getenv('GOOGLE_API_KEY')

# Configure the API
ai.configure(api_key=API_KEY)

# Chat application variables
rooms = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)
        
        if code not in rooms:
            break
    
    return code
@app.route("/home1", methods=["POST", "GET"])
def home1():
    session.clear()  # Clear session to reset the state

    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        # Ensure the name is provided
        if not name:
            return render_template("home1.html", error="Please enter a name.", code=code, name=name)

        # If user wants to join, ensure the room code is provided
        if join != False and not code:
            return render_template("home1.html", error="Please enter a room code.", code=code, name=name)

        # Handle the creation of the room
        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": []}
        elif code not in rooms:
            return render_template("home1.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        return redirect(url_for("room1"))  # Redirect to the room page after joining or creating a room

    return render_template("home1.html")

@app.route("/room1")
def room1():
    room = session.get("room")
    name = session.get("name")
    if not room or not name or room not in rooms:
        flash("Invalid room or session. Please try again.")
        return redirect(url_for("home1"))

    return render_template("room1.html", code=room, messages=rooms[room]["messages"])


@socketio.on("message")
def message(data):
    room = session.get("room")
    if room not in rooms:
        return 
    
    content = {
        "name": session.get("name"),
        "message": data["data"]
    }
    send(content, to=room)
    rooms[room]["messages"].append(content)
    print(f"{session.get('name')} said: {data['data']}")

@socketio.on("connect")
def connect(auth):
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return
    
    join_room(room)
    send({"name": name, "message": "has entered the room"}, to=room)
    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")

@socketio.on("disconnect")
def disconnect():
    room = session.get("room")
    name = session.get("name")
    leave_room(room)

    if room in rooms:
        rooms[room]["members"] -= 1
        if rooms[room]["members"] <= 0:
            del rooms[room]
    
    send({"name": name, "message": "has left the room"}, to=room)
    print(f"{name} has left the room {room}")

# Additional routes and logic for your other functionality
@app.route("/api/example", methods=["GET"])
def api_example():
    return jsonify({"message": "This is an example API endpoint."})
@app.route("/exit_room", methods=["POST"])
def exit_room():
    # Clear the session for room and name to "log out" the user from the chat room
    session.pop("room", None)
    session.pop("name", None)
    
    # Redirect the user to the community page
    return redirect(url_for("community"))

def evaluate_overall_mental_state(username):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Fetch reactions from the 'reactions' table for the given user (using 'appname' instead of 'name')
        cursor.execute("SELECT reaction_type FROM reactions WHERE appname = %s", (username,))
        reactions = cursor.fetchall()

        # Log or print fetched reactions to see what data is returned
        print(f"Fetched reactions for {username}: {reactions}")

        if not reactions:
            # If no reactions were found for the user, return an error
            return {
                "status": "error",
                "message": f"No reactions found for user: {username}"
            }

        # Initialize counters for each reaction type
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        # Categorize reactions based on reaction_type
        for reaction in reactions:
            reaction_type = reaction.get("reaction_type", "").lower()

            # Positive reactions
            if reaction_type in ["like", "love", "care"]:
                positive_count += 1
            # Negative reactions
            elif reaction_type in ["angry", "sad", "wow"]:
                negative_count += 1
            # Neutral reactions
            else:
                neutral_count += 1

        # Calculate total number of reactions
        total_reactions = positive_count + negative_count + neutral_count

        if total_reactions == 0:
            # If no reactions are found, return a message
            return {
                "status": "error",
                "message": f"No reactions found for user: {username}"
            }

        # Calculate percentages for each category
        positive_percentage = (positive_count / total_reactions) * 100
        negative_percentage = (negative_count / total_reactions) * 100
        neutral_percentage = (neutral_count / total_reactions) * 100

        # Determine the overall mental state based on majority reactions
        overall_state = "Neutral"  # Default value
        if positive_percentage > 60:
            overall_state = "Positive"
        elif negative_percentage > 60:
            overall_state = "Negative"

        # Return the evaluation result
        return {
            "status": "success",
            "username": username,
            "evaluation": {
                "positive_percentage": positive_percentage,
                "negative_percentage": negative_percentage,
                "neutral_percentage": neutral_percentage,
                "overall_state": overall_state
            }
        }

    except mysql.connector.Error as e:
        # Handle and log database errors
        return {
            "status": "error",
            "message": f"Database error: {e}"
        }
    finally:
        cursor.close()
        conn.close()


# Facebook API details
page_id = '61571664276237'  # Your page ID
post_id = '122100166154722142'  # Your post ID
access_token = 'EAAVR1GpxE6MBO4JNq0ZAZATWoUsT8oaNKvp1ZAmAbmHNQdszycCJhgPAXqzAfMqxkCKbGoxc6VzxTkNJXawx7f5lGPsjETWcvvLxJUwmZAboIXGHKZCTR0mVPFfPYiLeDWIOuPv8GUOG7hq5AoEv1tJAMR7jQ6kV7wY7OSQOGlOZCd9KuglylaSLIwhe2YOeQZAKFFVtl37MsDVjVAq'

# Comments and reactions URL
comments_url = f'https://graph.facebook.com/v16.0/{page_id}_{post_id}/comments?access_token={access_token}'
reactions_url = f'https://graph.facebook.com/v16.0/{page_id}_{post_id}/reactions?access_token={access_token}'

# Functions to process comments and reactions
def get_comment(comment):
    return {
        'name': comment['from']['name'],
        'time': comment['created_time'],
        'message': comment['message']
    }

def get_reaction(reaction):
    return {
        'name': reaction['name'],
        'reaction_type': reaction['type']
    }





# Insert comments into MySQL database
def insert_comment(cursor, comment, appname):
    try:
        # Use a query to insert the comment only if the user hasn't already commented on the post
        cursor.execute(""" 
            INSERT INTO comments (name, time, message, post_id, appname)
            SELECT %s, %s, %s, %s, %s
            WHERE NOT EXISTS (
                SELECT 1 FROM comments WHERE name = %s AND post_id = %s
            );
        """, (comment['name'], comment['time'], comment['message'], post_id, appname, comment['name'], post_id))
    except mysql.connector.Error as err:
        print(f"Error inserting comment: {err}")

# Insert reactions into MySQL database
def insert_reaction(cursor, reaction, appname):
    try:
        cursor.execute("INSERT INTO reactions (name, reaction_type, appname) VALUES (%s, %s, %s)",
                       (reaction['name'], reaction['reaction_type'], appname))
    except mysql.connector.Error as err:
        print(f"Error inserting reaction: {err}")

# Function to fetch and store comments and reactions
def fetch_and_store_data(appname):
    try:
        # Fetch comments and reactions
        comments_response = requests.get(comments_url)
        comments_data = comments_response.json()
        
        reactions_response = requests.get(reactions_url)
        reactions_data = reactions_response.json()

        conn = get_db_connection()
        if conn:
            cursor = conn.cursor()

            # Process and insert comments into the database
            if 'data' in comments_data:
                for comment in comments_data['data']:
                    comment_data = get_comment(comment)
                    insert_comment(cursor, comment_data, appname)

            # Process and insert reactions into the database
            if 'data' in reactions_data:
                for reaction in reactions_data['data']:
                    reaction_data = get_reaction(reaction)
                    insert_reaction(cursor, reaction_data, appname)

            # Commit changes to the database
            conn.commit()

            # Close the cursor and connection
            cursor.close()
            conn.close()

        print("Data fetched and stored successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Facebook API: {e}")
    except mysql.connector.Error as e:
        print(f"Database error: {e}")

# Call the function to fetch and store data as soon as the app starts with the appname (logged-in user)
#fetch_and_store_data(logged_in_user_name)  # Replace logged_in_user_name with the actual variable from your app
# Function to evaluate mental health status
def evaluate_mental_health(responses):
    positive, negative = 0, 0

    # Check each question's response
    if responses["Q1"] == "Happy": positive += 1
    if responses["Q1"] == "Sad": negative += 1

    if responses["Q2"] == "Low": positive += 1
    if responses["Q2"] == "High": negative += 1

    if responses["Q3"] == "Low": positive += 1
    if responses["Q3"] == "High": negative += 1

    if responses["Q4"] in ["Very Satisfied", "Satisfied"]: positive += 1
    if responses["Q4"] == "Dissatisfied": negative += 1

    if responses["Q5"] == "Good": positive += 1
    if responses["Q5"] == "Poor": negative += 1

    if responses["Q6"] == "No": positive += 1
    if responses["Q6"] == "Yes": negative += 1

    if responses["Q7"] == "No": positive += 1
    if responses["Q7"] == "Yes": negative += 1

    if responses["Q8"] == "No": positive += 1
    if responses["Q8"] == "Yes": negative += 1

    if responses["Q9"] == "High": positive += 1
    if responses["Q9"] == "Low": negative += 1

    if responses["Q10"] == "High": positive += 1
    if responses["Q10"] == "Low": negative += 1

    # Determine mental health status
    if positive > negative:
        return "Good Mental Health", "Your responses indicate that your mental health is in a good state. Keep up your healthy habits!"
    elif negative > positive:
        return "Needs Attention", "Your responses suggest some mental health concerns. Consider reaching out for professional help."
    else:
        return "Neutral", "Your mental health seems balanced, but continue monitoring your well-being."
    
@app.route('/community')
def community():
    # Check if the user is logged in
    if 'username' not in session:
        return redirect(url_for('login'))  # Redirect to login if not logged in

    # Example community posts (replace with database or dynamic content)
    posts = [
        {"username": "Alice", "message": "I’ve been feeling much better after completing mindfulness exercises."},
        {"username": "Bob", "message": "Does anyone have tips for managing anxiety before exams?"},
        {"username": "Charlie", "message": "I find journaling helpful for organizing my thoughts."}
    ]
    return render_template('community.html', posts=posts)

@app.route('/community/post', methods=['POST'])
def add_post():
    if 'username' not in session:
        return redirect(url_for('login'))

    username = session['username']  # Get the logged-in user's username
    message = request.form.get('message')

    if message:
        # Here you could save the post to a database; for now, just a placeholder
        print(f"New post by {username}: {message}")
        # Redirect back to the community page after adding the post
    return redirect(url_for('community'))
@app.route('/join_community', methods=['POST'])
def join_community():
    # Check if the user is logged in
    if 'username' not in session:
        return jsonify({"success": False, "error": "User not logged in"})
    
    # Get the logged-in username from the session
    username = session['username']

    # Get task and organization from the frontend
    task = request.form.get('task')
    organization = request.form.get('organization')

    # Validate that both task and organization are provided
    if not task or not organization:
        return jsonify({"success": False, "error": "Task and organization are required"})

    # Establish connection to the database
    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        # Fetch the username from the 'mindot' table (i.e., logged-in user)
        cursor.execute("SELECT username FROM mindot WHERE username = %s", (username,))
        user = cursor.fetchone()

        if not user:
            return jsonify({"success": False, "error": "User not found in mindot table"})

        # Check if the user has already joined the same task
        cursor.execute("SELECT * FROM community WHERE username = %s AND task = %s", (username, task))
        existing_task = cursor.fetchone()

        if existing_task:
            # If the user has already joined the same task, prevent them from joining again
            return jsonify({"success": False, "error": "You have already joined this task."})

        # SQL query to insert data into the "community" table
        query = "INSERT INTO community (username, task, organization) VALUES (%s, %s, %s)"
        cursor.execute(query, (username, task, organization))  # Insert username, task, and organization

        # Commit the transaction
        connection.commit()

        # Close the cursor and connection
        cursor.close()
        connection.close()

        # Return success response
        return jsonify({
            "success": True,
            "message": "You have successfully joined the task!"
        })

    except mysql.connector.Error as err:
        # Handle any errors
        print(f"Error: {err}")
        return jsonify({"success": False, "error": str(err)})
    

@app.route('/send-emergency-alert', methods=['POST'])
def send_emergency_alert():
    data = request.json
    message = data.get('message')

    # Simulate sending a message to the mental health care organization
    # You can integrate Twilio, SMTP, or other services here
    print(f"Emergency Alert: {message}")

    # Return success response
    return jsonify({"status": "success", "message": "Emergency alert sent!"}), 200


@app.route('/members')
def members():
    # Get a connection to the database
    connection = get_db_connection()
    cursor = connection.cursor()

    # Query to fetch data from the mindot table
    cursor.execute("SELECT username, profession FROM mindot")
    members = cursor.fetchall()  # Fetch all rows

    cursor.close()  # Close the cursor
    connection.close()  # Close the connection

    # Render the members template and pass the 'members' data to it
    return render_template('members.html', members=members)


@app.route('/send_message', methods=['POST'])
def send_message():
    sender = 'your_username'  # Replace with the logged-in user's name
    recipient = request.form['recipient']
    message = request.form['message']
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Save the user's message with the recipient in the database
        cursor.execute("""
            INSERT INTO chat_messages (sender, receiver, message)
            VALUES (%s, %s, %s)
        """, (sender, recipient, message))
        conn.commit()

        # Return a response (could be from a bot or a simple acknowledgment)
        return jsonify({
            "status": "success",
            "response": "Message sent!"  # This could be a bot's response or just an acknowledgment
        })
    except Exception as e:
        print(f"Error saving message: {e}")
        return jsonify({"status": "failure", "response": "Error occurred while sending the message"})
    finally:
        cursor.close()
        conn.close()




@app.route('/chat_section', endpoint='chat_section')
def chat_section():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Fetch member names from the `mindot` table (changed to `name` column)
        cursor.execute("SELECT name FROM mindot")
        members = [row[0] for row in cursor.fetchall()]
        
        print(f"Members fetched: {members}")  # Debugging line
        
    except Exception as e:
        members = []  # If there's an error, return an empty list
        print(f"Error fetching members: {e}")
    finally:
        cursor.close()
        conn.close()
    
    # Pass the list of members to the template
    return render_template('chat_section.html', members=members)

@app.route('/fetch_messages', methods=['POST'])
def fetch_messages():
    try:
        selected_member = request.form.get('member')
        conn = get_db_connection()
        cursor = conn.cursor()

        # Fetch messages for the selected member from the `chat_messages` table
        cursor.execute("SELECT message, sender FROM chat_messages WHERE recipient = %s OR sender = %s ORDER BY created_at ASC", (selected_member, selected_member))
        messages = cursor.fetchall()

        # Format messages for JSON response
        formatted_messages = [{"sender": msg[1], "message": msg[0]} for msg in messages]
        return jsonify({"status": "success", "messages": formatted_messages})
    except Exception as e:
        print(f"Error fetching messages: {e}")
        return jsonify({"status": "error", "message": "Failed to fetch messages."})
    finally:
        cursor.close()
        conn.close()

@app.route('/go_to_chat')
def go_to_chat():
    return redirect(url_for('chat'))


@app.route("/profile", methods=["GET"])
def profile():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]

    # Fetch user data from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM mindot WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    conn.close()

    print(user_data)  # Debug print to check the values

    if not user_data:
        return "User profile not found.", 404

    # Render the profile with the user data
    return render_template("profile.html", user_data=user_data)

@app.route('/update_profile', methods=['GET', 'POST'])
def update_profile():
    if "username" not in session:
        return redirect(url_for("login"))
    
    username = session["username"]
    
    # Fetch user data from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM mindot WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    conn.close()

    # If no data found for the user, redirect to profile page
    if not user_data:
        return "User profile not found.", 404

    if request.method == "POST":
        # Get updated user data from the form
        updated_name = request.form.get("name", user_data["name"])
        updated_email = request.form.get("email", user_data["email"])
        updated_gender = request.form.get("gender", user_data["Gender"])
        updated_age = request.form.get("age", user_data["Age"])
        updated_profession = request.form.get("profession", user_data["Profession"])

        # Update the user data in the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE mindot SET name = %s, email = %s, Gender = %s, Age = %s, Profession = %s WHERE username = %s",
            (updated_name, updated_email, updated_gender, updated_age, updated_profession, username)
        )
        conn.commit()
        conn.close()

        # Redirect back to profile page after updating
        return redirect(url_for('profile'))  # Redirect to the profile page after update
    
    # For GET request, render the update profile form
    return render_template('update_profile.html', user_data=user_data)




# Route for the guideline agreement page
@app.route("/guidelines", methods=["GET", "POST"])
def guidelines():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Redirect to the mental health questionnaire if the user agrees
        if "agree" in request.form:
            return redirect(url_for("mental_health"))
        else:
            flash("You must agree to the guidelines to proceed.")
            return redirect(url_for("guidelines"))

    return render_template("guidelines.html")


# Updated mental health assessment route
@app.route("/mental_health", methods=["GET", "POST"])
def mental_health():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect responses for each question
        username = session["username"]
        Q1 = request.form.get("Q1")
        Q2 = request.form.get("Q2")
        Q3 = request.form.get("Q3")
        Q4 = request.form.get("Q4")
        Q5 = request.form.get("Q5")
        Q6 = request.form.get("Q6")
        Q7 = request.form.get("Q7")
        Q8 = request.form.get("Q8")
        Q9 = request.form.get("Q9")
        Q10 = request.form.get("Q10")

        # Calculate scores for each factor
        depression_score = calculate_depression(Q1, Q5, Q7, Q8)
        anxiety_score = calculate_anxiety(Q2, Q3, Q6)
        anger_score = calculate_anger(Q2, Q3)
        loneliness_score = calculate_loneliness(Q7, Q8)

        # Save responses to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO response 
               (username, Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10, depression_score, anxiety_score, anger_score, loneliness_score)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (username, Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10,
             depression_score, anxiety_score, anger_score, loneliness_score)
        )
        conn.commit()
        conn.close()

        # Fetch user data
        user_data = get_user_data(username)
        if not user_data:
            user_data = {"username": username, "message": "User data not found"}

        # Fetch manual activity logs
        activity = [
            {"date": "2024-12-10", "action": "Logged in to the system"},
            {"date": "2024-12-11", "action": "Updated profile information"},
            {"date": "2024-12-12", "action": "Sent a message to chatbot"},
        ]

        # Evaluate mental health status
        analysis = {
            "depression": evaluate_condition(depression_score),
            "anxiety": evaluate_condition(anxiety_score),
            "anger": evaluate_condition(anger_score),
            "loneliness": evaluate_condition(loneliness_score)
        }

        # Redirect to assessment2 after successful submission
        return redirect(url_for("assessment2"))

    return render_template("mental_health.html")

@app.route('/assessment2', methods=['GET', 'POST'])
def assessment2():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect responses for each question
        username = session["username"]
        Q1 = request.form.get("Q1")
        Q2 = request.form.get("Q2")
        Q3 = request.form.get("Q3")
        Q4 = request.form.get("Q4")
        Q5 = request.form.get("Q5")
        Q6 = request.form.get("Q6")
        Q7 = request.form.get("Q7")
        Q8 = request.form.get("Q8")
        Q9 = request.form.get("Q9")
        Q10 = request.form.get("Q10")

        # Calculate cognitive function score (sum of answers)
        cognitive_function_score = sum([int(Q1), int(Q2), int(Q3), int(Q4), int(Q5), int(Q6), int(Q7), int(Q8), int(Q9), int(Q10)])

        # Categorize the cognitive function score into different statuses
        if cognitive_function_score <= 20:
            cognitive_status = "Severe Cognitive Impairment"
        elif cognitive_function_score <= 30:
            cognitive_status = "Moderate Cognitive Impairment"
        elif cognitive_function_score <= 40:
            cognitive_status = "Mild Cognitive Impairment"
        else:
            cognitive_status = "No Cognitive Impairment"

        # Save responses, score, and status to the database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO response21 
               (username, cognitive_function_score, cognitive_status, timestamp) 
               VALUES (%s, %s, %s, NOW())""", 
            (username, cognitive_function_score, cognitive_status)
        )
        conn.commit()
        conn.close()

        # Redirect to the next assessment (Assessment 3)
        return redirect(url_for('assessment3'))

    # Retrieve the cognitive function data from the database for the logged-in user
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM response21 WHERE username = %s ORDER BY timestamp DESC LIMIT 1", (session["username"],))
    cognitive_data = cursor.fetchone()
    conn.close()

    return render_template('assessment2.html', cognitive_data=cognitive_data)



def calculate_cognitive_function_score(responses):
    """
    Calculate the cognitive function score based on responses.

    Args:
        responses: A list of tuples containing responses for Q1-Q10.

    Returns:
        Cognitive function score as a float or integer.
    """
    # Example scoring logic: Map responses to numeric values
    score_mapping = {
        "1": 1,  # Never
        "2": 2,  # Rarely
        "3": 3,  # Sometimes
        "4": 4,  # Often
        "5": 5   # Always
    }

    total_score = 0
    for response in responses:
        for answer in response:
            total_score += score_mapping.get(answer, 0)  # Default to 0 if answer is invalid

    # Normalize score to a 100-point scale
    max_score = 10 * 5  # 10 questions, max 5 points each
    cognitive_function_score = (total_score / max_score) * 100

    return round(cognitive_function_score, 2)  # Return score rounded to 2 decimal places


@app.route('/assessment3', methods=['GET', 'POST'])
def assessment3():
    if "username" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        # Collect and save Assessment 3 responses
        username = session["username"]
        Q1 = request.form.get("Q1")
        Q2 = request.form.get("Q2")
        Q3 = request.form.get("Q3")
        Q4 = request.form.get("Q4")
        Q5 = request.form.get("Q5")

        # Ensure you have a valid connection to the database
        conn = get_db_connection()
        cursor = conn.cursor()

        # Insert user responses into the response3 table
        try:
            cursor.execute(
                """INSERT INTO response3 (username, Q1, Q2, Q3, Q4, Q5)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (username, Q1, Q2, Q3, Q4, Q5)
            )
            conn.commit()
        except mysql.connector.Error as err:
            print(f"Error: {err}")
            conn.rollback()  # Rollback in case of error
        finally:
            conn.close()

        # Redirect to the dashboard after successfully saving the data
        return redirect(url_for('dashboard'))

    return render_template('assessment3.html')


@app.route('/submit_assessment2', methods=['POST'])
def submit_assessment2():
    # Process form data for Assessment 2 here
    return "Assessment 2 submitted successfully!"




# Define scoring functions
def calculate_depression(Q1, Q5, Q7, Q8):
    depression_score = 0
    # Q1 - Mood
    if Q1 == "Sad":
        depression_score += 2
    elif Q1 == "Neutral":
        depression_score += 1
    # Q5 - Sleep Quality
    if Q5 == "Poor":
        depression_score += 2
    elif Q5 == "Average":
        depression_score += 1
    # Q7 - Depression Symptoms
    if Q7 == "Yes":
        depression_score += 2
    # Q8 - Isolation
    if Q8 == "Yes":
        depression_score += 2
    return depression_score


def calculate_anxiety(Q2, Q3, Q6):
    anxiety_score = 0
    # Q2 - Stress Level
    if Q2 == "High":
        anxiety_score += 2
    elif Q2 == "Moderate":
        anxiety_score += 1
    # Q3 - Work Stress
    if Q3 == "High":
        anxiety_score += 2
    elif Q3 == "Moderate":
        anxiety_score += 1
    # Q6 - Anxiety Frequency
    if Q6 == "Yes":
        anxiety_score += 2
    return anxiety_score


def calculate_anger(Q2, Q3):
    anger_score = 0
    # Q2 - Stress Level
    if Q2 == "High":
        anger_score += 2
    elif Q2 == "Moderate":
        anger_score += 1
    # Q3 - Work Stress
    if Q3 == "High":
        anger_score += 2
    elif Q3 == "Moderate":
        anger_score += 1
    return anger_score


def calculate_loneliness(Q7, Q8):
    loneliness_score = 0
    # Q7 - Depression Symptoms
    if Q7 == "Yes":
        loneliness_score += 2
    # Q8 - Isolation
    if Q8 == "Yes":
        loneliness_score += 2
    return loneliness_score


def evaluate_condition(score):
    # Categorize based on score
    if score <= 2:
        return "Low"
    elif score <= 4:
        return "Moderate"
    elif score <= 6:
        return "High"
    else:
        return "Severe"
def get_user_data(username):
    # Fetch user data from the database based on the username
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT name, email, gender, age, profession FROM mindot WHERE username = %s", (username,))
    user_data = cursor.fetchone()
    conn.close()
    return user_data

def get_activity_log(username):
    # Fetch user's activity log from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT date, action FROM activity_log WHERE username = %s ORDER BY date DESC", (username,))
    activity = cursor.fetchall()
    conn.close()
    return activity


@app.route("/mental_health_success")
def mental_health_success():
    return render_template("mental_health_success.html")
def remove_outdated_tasks():
    """Remove outdated tasks (tasks older than 1 day)."""
    conn = None
    cursor = None
    try:
        # Get a new database connection
        conn = get_db_connection()
        cursor = conn.cursor()

        # Execute the deletion query
        cursor.execute("DELETE FROM dailytask WHERE timestamp < NOW() - INTERVAL 1 DAY")

        # Commit the changes
        conn.commit()

        print("Outdated tasks removed successfully.")
    except Exception as e:
        print(f"Error while removing outdated tasks: {e}")
    finally:
        # Close the cursor and the connection if they were created
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# Call the function to remove outdated tasks
remove_outdated_tasks()

@app.route("/daily_tasks", methods=["GET", "POST"])
def daily_tasks():
    if "username" not in session:
        return redirect(url_for("login"))
    
    username = session["username"]
    message = None  # Message to display if submission already exists

    # Get the current day of the month
    current_day = datetime.today().day

    # Determine if it's an odd or even day
    is_odd_day = current_day % 2 != 0

    # Define the tasks for odd and even days (set1: T1-T7, set2: T8-T14)
    if is_odd_day:
        tasks = [
            ("T1", "Meditate for 10 minutes"),
            ("T2", "Drink 8 glasses of water"),
            ("T3", "Exercise or go for a walk"),
            ("T4", "Practice Gratitude"),
            ("T5", "Set Your Intentions for the Day"),
            ("T6", "Declutter Your Space"),
            ("T7", "Spend Quality Time with Loved Ones")
        ]  # Task set for odd days
    else:
        tasks = [
            ("T8", "Journal Your Thoughts"),
            ("T9", "Complete One Productive Task"),
            ("T10", "Read for 15 minutes"),
            ("T11", "Take a Digital Detox"),
            ("T12", "Deep Breathing or Mindful Breathing"),
            ("T13", "Eat a Balanced Meal"),
            ("T14", "Reflect on the Day")
        ]  # Task set for even days

    if request.method == "POST":
        # Fetch checkbox values from the form
        task_values = {}
        for task in tasks:
            task_values[task[0]] = "on" if request.form.get(task[0]) else "off"

        try:
            # Insert the task completion into the database
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Create the query dynamically based on the tasks
            query = f"""INSERT INTO dailytask (username, {', '.join([task[0] for task in tasks])})
                        VALUES (%s, {', '.join(['%s'] * len(tasks))})"""
            cursor.execute(query, (username, *task_values.values()))
            conn.commit()
            
            message = "Your daily tasks have been submitted successfully."

        except mysql.connector.errors.IntegrityError as e:
            if "Duplicate entry" in str(e):
                message = "You have already submitted your daily tasks for today."
            else:
                # Handle other integrity errors
                message = "An error occurred while submitting your tasks."

        finally:
            conn.close()

    return render_template("daily_tasks.html", message=message, tasks=tasks)






@app.route("/suggestions")
def suggestions():
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Check the current day
    today = datetime.now().day
    if today % 2 == 0:
        # Even days - show first set of suggestions
        suggestions = [
            {"title": "Journaling for Self-Reflection", "description": "Journaling can help you process emotions and clarify thoughts. Start with prompts like: 'What am I grateful for today?' or 'What made me happy this week?'", "link": "https://www.youtube.com/watch?v=4JUuDIwYj6o"},
            {"title": "Breathing Exercises for Calmness", "description": "Controlled breathing can help reduce anxiety and promote relaxation. Try the '4-7-8' method: Inhale for 4 seconds, hold for 7 seconds, exhale for 8 seconds.", "link": "https://www.youtube.com/watch?v=_xQJ2O4b5TM"},
            {"title": "Gratitude Practice", "description": "Listing things you're thankful for can improve mental well-being. Keep a gratitude jar or journal and write down one thing daily.", "link": "https://www.youtube.com/watch?v=U5lZBjWDR_c"},
            {"title": "Digital Detox", "description": "Reducing screen time can improve sleep and decrease stress. Set aside specific times for social media or turn off notifications.", "link": "https://www.youtube.com/watch?v=9WpFG0B1ICM"},
            {"title": "Music Therapy", "description": "Listening to calming music can reduce stress and improve focus. Try binaural beats or classical music for relaxation.", "link": "https://www.youtube.com/watch?v=yjFGWtoCuRg"},
            {"title": "Building a Consistent Sleep Routine", "description": "Sleep is crucial for mental health. Aim for 7-9 hours of sleep per night. Create a bedtime routine, avoid screens an hour before bed, and consider relaxation techniques.", "link": "https://www.youtube.com/watch?v=RYlqAKS-QMg"},
            {"title": "Acts of Kindness", "description": "Helping others can improve your mood and foster connections. Volunteer, help a friend, or perform small acts of kindness daily.", "link": "https://www.youtube.com/watch?v=Mm6FMZ0tYYQ"}
        ]
    else:
        # Odd days - show second set of suggestions
        suggestions = [
            {"title": "Guided Meditation", "description": "Spend 10 minutes in guided meditation to relax your mind.", "link": "https://www.youtube.com/watch?v=inpok4MKVLM"},
            {"title": "Positive Affirmations", "description": "Repeat positive affirmations to boost self-confidence.", "link": "https://www.youtube.com/watch?v=8mnJ2oF6zmc"},
            {"title": "5-Minute Breathing Exercise", "description": "Practice this short exercise to reduce anxiety.", "link": "https://www.youtube.com/watch?v=SEfs5TJZ6Nk"},
            {"title": "Visualization Exercise", "description": "Use this exercise to imagine a peaceful and happy place.", "link": "https://www.youtube.com/watch?v=U3bFoKB4NV4"},
            {"title": "Spend Time in Nature", "description": "A walk in the park or time spent outdoors can refresh your mind and reduce anxiety.", "link": "https://www.youtube.com/watch?v=v7AYKMP6rOE"},
            {"title": "Engage in Physical Activity", "description": "Regular exercise, like walking, yoga, or stretching, boosts your mood and reduces stress.", "link": "https://www.youtube.com/watch?v=2OEL4P1Rz04"},
            {"title": "Relaxing Music", "description": "Listen to relaxing music to unwind and calm your mind.", "link": "https://www.youtube.com/watch?v=2OEL4P1Rz04"}
        ]
    
    return render_template("suggestions.html", suggestions=suggestions)

@app.route("/")
def home():
    if "username" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("index"))

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        conn = get_db_connection()

        # Remove outdated tasks when a user logs in
    

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM mindot WHERE username = %s", (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user["password"] == password:
            # Store user details in the session
            session["username"] = username
            session["user_name"] = user["name"]  # Store the full name (if needed)
            session["user_email"] = user["email"]  # Store the email (if needed)
            
            # Fetch and store data for the logged-in user
            fetch_and_store_data(username)  # Fetch and store data using the logged-in username
            
            # Redirect to the index (which renders chat1.html) after successful login
            return redirect(url_for("index"))
        else:
            error = "Invalid username or password."

    return render_template("login.html", error=error)


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        name = request.form.get("name")
        email = request.form.get("email")
        gender = request.form.get("gender")
        age = request.form.get("age")
        profession = request.form.get("profession")

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mindot WHERE username = %s", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            error = "Username already exists."
        else:
            cursor.execute(
                "INSERT INTO mindot (username, password, name, email, gender, age, profession) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (username, password, name, email, gender, age, profession)
            )
            conn.commit()
            conn.close()
            return redirect(url_for("login"))

    return render_template("register.html", error=error)

@app.route("/logout")
def logout():
    session.pop("username", None)
    return redirect(url_for("login"))

@app.route("/index")
def index():
    if "username" not in session:
        return redirect(url_for("login"))
    return render_template("chat1.html")


# Function to get response from Gemini
def get_gemini_response(input_text, image):
    model = ai.GenerativeModel("gemini-1.5-flash")
    if input_text != "":
        response = model.generate_content([input_text, image])  # Sending image directly as PIL Image
    else:
        response = model.generate_content(image)  # Sending image directly as PIL Image
    return response.text

@app.route("/upload", methods=["GET", "POST"])
def upload():
    response = None
    if request.method == "POST":
        input_text = request.form["input"]
        uploaded_file = request.files["image"]
        
        if uploaded_file:
            image = Image.open(uploaded_file.stream)
            image = image.convert("RGB")
            response = get_gemini_response(input_text, image)

    return render_template("upload.html", response=response)
@app.route("/get", methods=["POST"])
def chat():
    if "username" not in session:
        return {"error": "Unauthorized"}, 401

    try:
        # Retrieve the user's message from the request
        msg = request.form.get("msg", "").strip()

        # If there's no message, return a default response
        if not msg:
            return {"response": "Hello! I'm your chatbot. Feel free to share how you're feeling, or ask any questions."}

        username = session["username"]
        
        # Connect to the database and retrieve the last few messages for context
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Retrieve the last 3 messages and responses for context
        cursor.execute("""
            SELECT message, response 
            FROM chatbot_memory 
            WHERE username = %s 
            ORDER BY timestamp DESC 
            LIMIT 3
        """, (username,))
        
        # Fetch memory (previous conversations) to provide context
        memory = cursor.fetchall()
        conn.close()

        # Format the memory as a string to be passed to the AI model
        memory_context = ""
        for entry in memory:
            memory_context += f"User: {entry['message']}\nBot: {entry['response']}\n"
        
        # Send the message along with memory context to the AI model for a more personalized response
        response = ai.GenerativeModel("gemini-pro").start_chat().send_message(memory_context + msg)

        # Save the new message and response to the database for future conversations
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO chatbot_memory (username, message, response) 
            VALUES (%s, %s, %s)
        """, (username, msg, response.text))
        conn.commit()
        conn.close()

        # Return the chatbot's response
        return {"response": response.text or "Sorry, I couldn't understand that."}

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"error": "An error occurred while processing the request."}
    
    return render_template("chat1.html")

def evaluate_cognitive_function(score):
    if score is None:
        return "No data"
    elif score < 50:
        return "Low"
    elif 50 <= score <= 75:
        return "Medium"
    else:
        return "High"

def insert_cognitive_data(username, cognitive_score):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO response21 (username, cognitive_function_score, timestamp)
        VALUES (%s, %s, NOW())
    """, (username, cognitive_score))
    conn.commit()
    conn.close()
# Function to get emotional analysis data from the database
def get_emotional_analysis(username):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=True)
    
    # Fetch the responses for the given username
    cursor.execute("SELECT * FROM response3 WHERE username = %s", (username,))
    responses = cursor.fetchall()
    
    # Initialize emotional scores
    emotional_data = {
        "happiness": 0,
        "sadness": 0,
        "fear": 0,
        "confidence": 0
    }

    # Calculate emotional scores based on responses
    for response in responses:
        # Analyze the responses based on the user's selection
        if response['Q1'] == 'happy':
            emotional_data["happiness"] += 1
        elif response['Q1'] == 'sad':
            emotional_data["sadness"] += 1
        elif response['Q1'] == 'angry':
            emotional_data["fear"] += 1
        elif response['Q1'] == 'calm':
            emotional_data["confidence"] += 1

        if response['Q2'] == 'high_energy':
            emotional_data["happiness"] += 1
        elif response['Q2'] == 'low_energy':
            emotional_data["sadness"] += 1
        elif response['Q2'] == 'exhausted':
            emotional_data["fear"] += 1
        elif response['Q2'] == 'balanced':
            emotional_data["confidence"] += 1

        if response['Q3'] == 'clear_mind':
            emotional_data["confidence"] += 1
        elif response['Q3'] == 'cloudy':
            emotional_data["sadness"] += 1
        elif response['Q3'] == 'chaotic':
            emotional_data["fear"] += 1
        elif response['Q3'] == 'focused':
            emotional_data["happiness"] += 1

        if response['Q4'] == 'connected':
            emotional_data["happiness"] += 1
        elif response['Q4'] == 'isolated':
            emotional_data["sadness"] += 1
        elif response['Q4'] == 'neutral':
            emotional_data["fear"] += 1
        elif response['Q4'] == 'social_butterfly':
            emotional_data["confidence"] += 1

        if response['Q5'] == 'focused':
            emotional_data["confidence"] += 1
        elif response['Q5'] == 'foggy':
            emotional_data["sadness"] += 1
        elif response['Q5'] == 'neutral':
            emotional_data["fear"] += 1
        elif response['Q5'] == 'chaotic':
            emotional_data["fear"] += 1

    connection.close()

    # Convert numerical scores to descriptive levels (high, moderate, low)
    def convert_to_level(score):
        if score >= 15:
            return "High"
        elif 8 <= score < 15:
            return "Moderate"
        else:
            return "Low"

    # Map emotional scores to descriptive levels
    emotional_levels = {emotion: convert_to_level(score) for emotion, score in emotional_data.items()}

    # Return the emotional data with descriptive levels
    return emotional_levels

@app.route("/dashboard", methods=["GET"])
def dashboard():
    if "username" not in session:
        return redirect(url_for("login"))

    username = session["username"]
    
    # Fetch user data from the database
    user_data = get_user_data(username)  # Adjust this as per your DB structure
    
    # Manual activity log data
    activity = [
        {"date": "2024-12-10", "action": "Logged in to the system"},
        {"date": "2024-12-11", "action": "Updated profile information"},
        {"date": "2024-12-12", "action": "Sent a message to chatbot"},
        {"date": "2024-12-13", "action": "Completed mental health assessment"},
        {"date": "2024-12-14", "action": "Reviewed mental health report"}
    ]
    
    # Fetch user responses from the database
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch responses from the response table
    cursor.execute("SELECT Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8, Q9, Q10 FROM response WHERE username = %s ORDER BY timestamp DESC LIMIT 1", (username,))
    responses = cursor.fetchone()

    # Fetch cognitive function data from the response21 table
    cursor.execute("SELECT cognitive_function_score, timestamp FROM response21 WHERE username = %s ORDER BY timestamp DESC LIMIT 1", (username,))
    cognitive_data = cursor.fetchone()

    # Fetch completed daily tasks from the database
    cursor.execute(""" 
    SELECT T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12, T13, T14, timestamp 
    FROM dailytask 
    WHERE username = %s 
    ORDER BY timestamp DESC LIMIT 1
    """, (username,))
    daily_tasks = cursor.fetchone()


    # Fetch joined tasks from the community table
    cursor.execute(""" 
        SELECT task, organization 
        FROM community 
        WHERE username = %s
    """, (username,))
    joined_tasks = cursor.fetchall()

    conn.close()

    # Task descriptions mapped to checkbox values
    task_list = [
        "Meditate for 10 minutes",
        "Exercise or go for a walk",
        "Journal your thoughts",
        "Drink 8 glasses of water",
        "Complete one productive task"
    ]

    # Map "on" and "off" values to task names
    if daily_tasks:
        task_statuses = [
            task_list[i] if daily_tasks[f"T{i+1}"] == "on" else None
            for i in range(5)
        ]
        completed_tasks = [task for task in task_statuses if task]
    else:
        completed_tasks = []

    # If no responses, render with empty analysis and tasks
    if not responses:
        return render_template("dashboard.html", user_data=user_data, activity=activity, analysis=None, completed_tasks=completed_tasks, joined_tasks=joined_tasks, cognitive_data=None, cognitive_status=None, timestamp=None)

    # Calculate scores based on responses
    depression_score = calculate_depression(responses["Q1"], responses["Q5"], responses["Q7"], responses["Q8"])
    anxiety_score = calculate_anxiety(responses["Q2"], responses["Q3"], responses["Q6"])
    anger_score = calculate_anger(responses["Q2"], responses["Q3"])
    loneliness_score = calculate_loneliness(responses["Q7"], responses["Q8"])

    
    # Evaluate mental health status
    analysis = {
        "depression": evaluate_condition(depression_score),
        "anxiety": evaluate_condition(anxiety_score),
        "anger": evaluate_condition(anger_score),
        "loneliness": evaluate_condition(loneliness_score)
    }


    # Evaluate cognitive function status
    cognitive_status = None
    if cognitive_data and cognitive_data["cognitive_function_score"]:
        cognitive_status = evaluate_cognitive_function(cognitive_data["cognitive_function_score"])

    emotional_analysis = get_emotional_analysis(username)

    # Define common issues based on high mental health scores
    common_issues = []

    if analysis["depression"] == "High":
        common_issues.append("Experiencing feelings of sadness and hopelessness.")
    if analysis["anxiety"] == "High":
        common_issues.append("Frequent feelings of nervousness or panic.")
    if analysis["anger"] == "High":
        common_issues.append("Difficulty controlling anger or frustration.")
    if analysis["loneliness"] == "High":
        common_issues.append("Feeling disconnected or isolated from others.")
    
  # Evaluate the overall mental state based on reactions
    overall_evaluation_result = evaluate_overall_mental_state(username)

    overall_evaluation = None
    if overall_evaluation_result["status"] == "success":
        overall_evaluation = overall_evaluation_result["evaluation"]
    else:
        # Log the error message if evaluation fails
        print(overall_evaluation_result["message"])

    return render_template(
        "dashboard.html", 
        user_data=user_data, 
        activity=activity, 
        analysis=analysis,
        emotional_analysis=emotional_analysis,
        common_issues=common_issues,  # Ensure that common_issues is passed correctly
        completed_tasks=completed_tasks, 
        joined_tasks=joined_tasks, 
        cognitive_data=cognitive_data,  
        cognitive_status=cognitive_status, 
        overall_evaluation=overall_evaluation, 
        timestamp=daily_tasks["timestamp"] if daily_tasks else None
    )


@app.route("/feedback")
def feedback():
    return render_template("feedback.html")

@app.route("/emergency", methods=["GET"])
def emergency():
    if "username" not in session:
        return redirect(url_for("login"))
    
    # Sample contacts for psychiatrists
    contacts = {
        "Psychiatrist 1": "123-456-7890",
        "Psychiatrist 2": "987-654-3210"
    }

    return render_template("emergency.html", contacts=contacts)

if __name__ == "__main__":
    socketio.run(app, debug=True)