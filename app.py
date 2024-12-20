import streamlit as st
import mysql.connector
import os
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pandas as pd
# Configure API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyClJbhIDfcpaTen4doNAJd9cM0OjAMUUSg"  # Replace with your API key

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.2)

# Database configuration
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Chaithu@9515",  # Replace with your password
    database="learning_assistant"
)
cursor = db.cursor(dictionary=True)

# Database initialization
def init_db():
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) UNIQUE,
            password VARCHAR(255),
            interests TEXT,
            learning_style TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS learning_paths (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            subject VARCHAR(100),
            progress FLOAT,
            difficulty_level VARCHAR(20),
            content JSON,
            target_completion_date DATE,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assessments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT,
            subject VARCHAR(100),
            topic VARCHAR(100),
            score FLOAT,
            feedback TEXT,
            taken_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')
    
    db.commit()

def authenticate_user(username, password):
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    return cursor.fetchone()

def evaluate_answer(topic, question, user_answer):
    prompt = f"""
    Evaluate this answer for the topic '{topic}':
    
    Question: {question}
    User's Answer: {user_answer}
    
    Provide evaluation in JSON format:
    {{
        "score": <float between 0 and 1>,
        "feedback": "<detailed feedback>",
        "correct_answer": "<explanation of the correct approach>"
    }}
    """
    
    response = llm.invoke(prompt)
    try:
        content_str = response.content.split("```json")[-1].split("```")[0].strip()
        return json.loads(content_str)
    except:
        return {
            "score": 0.5,
            "feedback": "Unable to evaluate answer",
            "correct_answer": "Please try again"
        }

def generate_assessment(topic):
    prompt = f"""
    Create an assessment question for the topic: {topic}
    
    Format as JSON:
    {{
        "question": "<question text>",
        "type": "open_ended",
        "expected_concepts": ["concept1", "concept2"]
    }}
    """
    
    response = llm.invoke(prompt)
    try:
        content_str = response.content.split("```json")[-1].split("```")[0].strip()
        return json.loads(content_str)
    except:
        return {
            "question": f"Explain the key concepts of {topic}",
            "type": "open_ended",
            "expected_concepts": ["basic understanding", "application"]
        }

def generate_learning_path(subject, user_interests, learning_style, target_days):
    prompt = f"""
    Create a detailed {target_days}-day learning path for {subject} considering:
    - User interests: {user_interests}
    - Learning style: {learning_style}
    
    Generate a learning path with educational resources. Each resource must have a title, 
    type (video/article/exercise/course), and description. URLs and platforms are optional.
    
    Format as JSON:
    {{
        "topics": [
            {{
                "name": "<topic name>",
                "description": "<detailed topic description>",
                "duration_days": <number>,
                "resources": [
                    {{
                        "title": "<specific course/resource title>",
                        "type": "<video/article/exercise/course>",
                        "description": "<detailed description>",
                        "url": "<resource URL or null>",
                        "platform": "<platform name or null>"
                    }}
                ],
                "practice_exercises": [
                    {{
                        "description": "<specific exercise description>",
                        "difficulty": "<beginner/intermediate/advanced>",
                        "url": "<exercise URL or null>"
                    }}
                ]
            }}
        ],
        "milestones": [
            {{
                "name": "<specific milestone name>",
                "expected_completion_day": <day_number>,
                "assessment_criteria": "<detailed criteria>"
            }}
        ]
    }}
    """
    
    response = llm.invoke(prompt)
    try:
        content_str = response.content.split("```json")[-1].split("```")[0].strip()
        path_content = json.loads(content_str)
        
        # Ensure all required fields exist and provide defaults if missing
        for topic in path_content['topics']:
            for resource in topic['resources']:
                if 'url' not in resource:
                    resource['url'] = '#'
                if 'platform' not in resource:
                    resource['platform'] = 'General'
                    
            for exercise in topic['practice_exercises']:
                if 'url' not in exercise:
                    exercise['url'] = '#'
        
        return path_content
    except Exception as e:
        st.error(f"Failed to generate learning path: {str(e)}")
        return None    

def display_learning_path(path):
    if not path:
        return
        
    st.subheader(f"{path['subject']} - {path['difficulty_level']}")
    
    # Progress and timeline
    col1, col2 = st.columns(2)
    with col1:
        st.progress(path['progress'])
        st.write(f"Progress: {path['progress']*100:.1f}%")
    with col2:
        days_remaining = (path['target_completion_date'] - datetime.now().date()).days
        st.write(f"Target completion: {path['target_completion_date']}")
        st.write(f"Days remaining: {days_remaining}")
    
    try:
        content = json.loads(path['content'])
        
        # Topics and resources using tabs
        topics = content.get('topics', [])
        topic_tabs = st.tabs([f"📚 {topic.get('name', 'Unnamed Topic')}" for topic in topics])
        
        for i, topic in enumerate(topics):
            with topic_tabs[i]:
                st.write(f"**Duration:** {topic.get('duration_days', 'N/A')} days")
                st.markdown(f"**Description:** {topic.get('description', 'No description available')}")
                
                st.subheader("📚 Resources")
                resources = topic.get('resources', [])
                if resources:
                    for resource in resources:
                        # Ensure resource is a dictionary
                        if not isinstance(resource, dict):
                            continue
                            
                        with st.expander(f"{resource.get('title', 'Untitled')} ({resource.get('type', 'Resource')})"):
                            st.markdown(f"**Description:** {resource.get('description', 'No description available')}")
                            
                            platform = resource.get('platform')
                            if platform:
                                st.markdown(f"**Platform:** {platform}")
                                
                            resource_url = resource.get('url')
                            if resource_url and resource_url != '#':
                                try:
                                    st.link_button("Open Resource", resource_url)
                                except Exception:
                                    st.warning("Resource link unavailable")
                else:
                    st.write("No resources available for this topic")
                
                st.subheader("💪 Practice Exercises")
                exercises = topic.get('practice_exercises', [])
                if exercises:
                    for exercise in exercises:
                        # Ensure exercise is a dictionary
                        if not isinstance(exercise, dict):
                            continue
                            
                        with st.expander(f"{exercise.get('difficulty', 'General').title()} Level Exercise"):
                            st.markdown(exercise.get('description', 'No description available'))
                            
                            exercise_url = exercise.get('url')
                            if exercise_url and exercise_url != '#':
                                try:
                                    st.link_button("Start Exercise", exercise_url)
                                except Exception:
                                    st.warning("Exercise link unavailable")
                else:
                    st.write("No practice exercises available for this topic")
                
                if st.button(f"Take Assessment: {topic.get('name', 'Unnamed Topic')}", 
                           key=f"assess_{path['id']}_{topic.get('name', 'unnamed')}"):
                    assessment = generate_assessment(topic.get('name', 'General Topic'))
                    st.session_state.current_assessment = {
                        'topic': topic.get('name', 'General Topic'),
                        'question': assessment['question'],
                        'path_id': path['id']
                    }
        
        # Milestones section
        milestones = content.get('milestones', [])
        if milestones:
            st.subheader("🎯 Milestones")
            for milestone in milestones:
                # Ensure milestone is a dictionary
                if not isinstance(milestone, dict):
                    continue
                    
                with st.expander(
                    f"Day {milestone.get('expected_completion_day', 'N/A')}: {milestone.get('name', 'Unnamed Milestone')}"
                ):
                    st.markdown(
                        f"**Assessment Criteria:** {milestone.get('assessment_criteria', 'No criteria specified')}"
                    )
                    
        # Progress update section
        st.subheader("📈 Update Progress")
        new_progress = st.slider(
            "Update your progress",
            0.0,
            1.0,
            path['progress'],
            key=f"slider_{path['id']}"
        )
        
        if st.button("Save Progress", key=f"save_{path['id']}"):
            cursor.execute("""
                UPDATE learning_paths 
                SET progress = %s, last_updated = NOW()
                WHERE id = %s
            """, (new_progress, path['id']))
            db.commit()
            st.success("Progress updated successfully!")
            
    except Exception as e:
        st.error(f"Error displaying learning path: {str(e)}")
        # Print the full error for debugging
        import traceback
        st.error(traceback.format_exc())

def display_analytics(progress_data, user_id):
    # Convert to DataFrame for easier analysis
    df = pd.DataFrame(progress_data)
    
    # Overall Progress Section
    st.subheader("📊 Overall Learning Progress")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Subjects", len(df))
    with col2:
        avg_progress = df['progress'].mean() * 100
        st.metric("Average Progress", f"{avg_progress:.1f}%")
    with col3:
        if not df.empty:
            top_subject = df.loc[df['progress'].idxmax(), 'subject']
            top_progress = df['progress'].max() * 100
            st.metric("Best Performing Subject", f"{top_subject} ({top_progress:.1f}%)")

    # Progress Heatmap
    if not df.empty:
        st.subheader("🔥 Progress Intensity")
        df['day_of_week'] = pd.to_datetime(df['last_updated']).dt.strftime('%A')
        df['hour_of_day'] = pd.to_datetime(df['last_updated']).dt.hour
        
        fig_heatmap = px.density_heatmap(
            df,
            x='day_of_week',
            y='hour_of_day',
            title="Learning Activity Patterns",
            labels={'day_of_week': 'Day of Week', 'hour_of_day': 'Hour of Day'}
        )
        st.plotly_chart(fig_heatmap, use_container_width=True)

    # Progress Over Time
    st.subheader("📈 Progress Timeline")
    # Get assessment data
    cursor.execute("""
        SELECT subject, score, taken_at 
        FROM assessments 
        WHERE user_id = %s
        ORDER BY taken_at
    """, (user_id,))
    assessment_data = cursor.fetchall()
    assessment_df = pd.DataFrame(assessment_data)

    if not df.empty:
        # Create timeline of progress updates
        fig_timeline = px.line(
            df,
            x='last_updated',
            y='progress',
            color='subject',
            title="Learning Progress Over Time",
            labels={
                'last_updated': 'Date',
                'progress': 'Progress (%)',
                'subject': 'Subject'
            }
        )
        
        # Update progress values to percentage
        fig_timeline.update_traces(y=df['progress'] * 100)
        
        # Add assessment scores if available
        if not assessment_df.empty:
            assessment_scatter = px.scatter(
                assessment_df,
                x='taken_at',
                y='score',
                title="Assessment Scores",
                labels={
                    'taken_at': 'Date',
                    'score': 'Score (%)'
                }
            )
            # Update score values to percentage
            assessment_scatter.update_traces(y=assessment_df['score'] * 100, mode='markers', 
                                          marker=dict(symbol='star', size=12))
            
            for trace in assessment_scatter.data:
                fig_timeline.add_trace(trace)

        fig_timeline.update_layout(
            hovermode='x unified',
            yaxis_title="Progress/Score (%)"
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

    # Learning Pace Analysis
    st.subheader("⚡ Learning Pace Analysis")
    if not df.empty:
        df['days_since_start'] = (pd.to_datetime(df['last_updated']) - 
                                 pd.to_datetime(df['last_updated']).min()).dt.days
        
        pace_fig = px.scatter(
            df,
            x='days_since_start',
            y='progress',
            color='subject',
            size='progress',
            trendline="ols",
            title="Learning Pace by Subject",
            labels={
                'days_since_start': 'Days Since Starting',
                'progress': 'Progress (%)',
                'subject': 'Subject'
            }
        )
        # Update progress values to percentage
        pace_fig.update_traces(y=df['progress'] * 100)
        pace_fig.update_layout(yaxis_title="Progress (%)")
        st.plotly_chart(pace_fig, use_container_width=True)

    # Assessment Performance
    if not assessment_df.empty:
        st.subheader("📝 Assessment Performance")
        
        # Average scores by subject
        avg_scores = assessment_df.groupby('subject')['score'].agg(['mean', 'count']).reset_index()
        avg_scores['mean'] = avg_scores['mean'] * 100
        
        fig_scores = px.bar(
            avg_scores,
            x='subject',
            y='mean',
            color='count',
            title="Average Assessment Scores by Subject",
            labels={
                'subject': 'Subject',
                'mean': 'Average Score (%)',
                'count': 'Number of Assessments'
            }
        )
        st.plotly_chart(fig_scores, use_container_width=True)

    # Time Management
    st.subheader("⏰ Time Management Insights")
    if not df.empty:
        df['hour'] = pd.to_datetime(df['last_updated']).dt.hour
        df['day'] = pd.to_datetime(df['last_updated']).dt.day_name()
        
        col1, col2 = st.columns(2)
        with col1:
            # Most productive hours
            productive_hours = df.groupby('hour')['progress'].mean().sort_values(ascending=False)
            st.write("Most Productive Hours:")
            for hour, progress in productive_hours.head(3).items():
                st.write(f"• {hour:02d}:00 - {progress*100:.1f}% average progress")
        
        with col2:
            # Most active days
            active_days = df.groupby('day')['progress'].mean().sort_values(ascending=False)
            st.write("Most Active Days:")
            for day, progress in active_days.head(3).items():
                st.write(f"• {day} - {progress*100:.1f}% average progress")

    # Recommendations
    st.subheader("💡 Personalized Recommendations")
    if not df.empty:
        # Generate recommendations based on analysis
        low_progress_subjects = df[df['progress'] < 0.5]['subject'].tolist()
        inactive_subjects = df[pd.to_datetime(df['last_updated']) < 
                             (datetime.now() - timedelta(days=7))]['subject'].tolist()
        
        if low_progress_subjects:
            st.write("Subjects needing attention:")
            for subject in low_progress_subjects:
                st.write(f"• Focus more on {subject}")
        
        if inactive_subjects:
            st.write("Subjects to revisit:")
            for subject in inactive_subjects:
                st.write(f"• Resume learning {subject}")

        # Best performing times
        if not productive_hours.empty and not active_days.empty:
            best_hour = productive_hours.index[0]
            best_day = active_days.index[0]
            st.write(f"💪 You perform best on {best_day}s at {best_hour:02d}:00")

def main():
    st.set_page_config(page_title="AI Learning Assistant", layout="wide")
    
    # Initialize session states
    if 'user' not in st.session_state:
        st.session_state.user = None
    if 'current_assessment' not in st.session_state:
        st.session_state.current_assessment = None
    
    # Sidebar
    with st.sidebar:
        st.title("🎓 AI Learning Assistant")
        if st.session_state.user:
            st.write(f"Welcome, {st.session_state.user['username']}!")
            if st.button("Logout"):
                st.session_state.user = None
                st.rerun()
    
    # Login/Register page
    if not st.session_state.user:
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.user = user
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid credentials")
        
        with col2:
            st.header("Register")
            new_username = st.text_input("Choose Username", key="reg_username")
            new_password = st.text_input("Choose Password", type="password", key="reg_password")
            interests = st.text_area("Your Interests (comma-separated)")
            learning_style = st.selectbox("Preferred Learning Style", 
                                        ["Visual", "Auditory", "Reading/Writing", "Kinesthetic"])
            
            if st.button("Register"):
                try:
                    cursor.execute("""
                        INSERT INTO users (username, password, interests, learning_style)
                        VALUES (%s, %s, %s, %s)
                    """, (new_username, new_password, interests, learning_style))
                    db.commit()
                    st.success("Registration successful! Please login.")
                except mysql.connector.Error as err:
                    st.error(f"Registration failed: {err}")
    
    # Main application interface
    else:
        tabs = st.tabs(["Learning Dashboard", "Create New Path", "Progress Analytics", "Assessments"])
        
        # Dashboard Tab
        with tabs[0]:
            st.header("Your Learning Dashboard")
            
            cursor.execute("""
                SELECT * FROM learning_paths 
                WHERE user_id = %s
                ORDER BY last_updated DESC
            """, (st.session_state.user['id'],))
            paths = cursor.fetchall()
            
            if paths:
                for path in paths:
                    display_learning_path(path)
            else:
                st.info("No learning paths yet. Create one in the 'Create New Path' tab!")
        
        # Create New Path Tab
        with tabs[1]:
            st.header("Create New Learning Path")
            
            col1, col2 = st.columns(2)
            with col1:
                subject = st.text_input("Subject you want to learn")
                difficulty = st.select_slider("Difficulty Level", 
                                           options=["Beginner", "Intermediate", "Advanced"])
                target_days = st.number_input("Target completion (days)", min_value=1, value=30)
            
            with col2:
                st.write("Current Settings:")
                st.write(f"Learning Style: {st.session_state.user['learning_style']}")
                st.write(f"Interests: {st.session_state.user['interests']}")
            
            if st.button("Generate Learning Path"):
                with st.spinner("Generating personalized learning path..."):
                    target_date = datetime.now().date() + timedelta(days=target_days)
                    path_content = generate_learning_path(
                        subject,
                        st.session_state.user['interests'],
                        st.session_state.user['learning_style'],
                        target_days
                    )
                    
                    cursor.execute("""
                        INSERT INTO learning_paths 
                        (user_id, subject, progress, difficulty_level, content, target_completion_date)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        st.session_state.user['id'],
                        subject,
                        0.0,
                        difficulty,
                        json.dumps(path_content),
                        target_date
                    ))
                    db.commit()
                    
                    st.success("Learning path created successfully!")
                    st.rerun()
        
        with tabs[2]:
            st.header("Progress Analytics")
            
            cursor.execute("""
                SELECT subject, progress, last_updated 
                FROM learning_paths 
                WHERE user_id = %s
            """, (st.session_state.user['id'],))
            progress_data = cursor.fetchall()
            
            if progress_data:
                display_analytics(progress_data, st.session_state.user['id'])
            else:
                st.info("Start learning to see your progress analytics!")
        # Assessment Tab
        with tabs[3]:
            st.header("Assessments")
            
            if st.session_state.current_assessment:
                assessment = st.session_state.current_assessment
                st.subheader(f"Assessment for: {assessment['topic']}")
                st.write(assessment['question'])
                
                user_answer = st.text_area("Your Answer")
                if st.button("Submit Assessment"):
                    evaluation = evaluate_answer(assessment['topic'], 
                                              assessment['question'], 
                                              user_answer)
                    
                    cursor.execute("""
                        INSERT INTO assessments 
                        (user_id, subject, topic, score, feedback)
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        st.session_state.user['id'],
                        assessment['topic'],
                        assessment['topic'],
                        evaluation['score'],
                        evaluation['feedback']
                    ))
                    db.commit()
                    
                    st.write("Score:", f"{evaluation['score']*100:.1f}%")
                    st.write("Feedback:", evaluation['feedback'])
                    st.write("Correct Approach:", evaluation['correct_answer'])
                    
                    if st.button("Clear Assessment"):
                        st.session_state.current_assessment = None
                        st.rerun()
            
            # Display past assessments
            cursor.execute("""
                SELECT * FROM assessments 
                WHERE user_id = %s 
                ORDER BY taken_at DESC
            """, (st.session_state.user['id'],))
            past_assessments = cursor.fetchall()
            
            if past_assessments:
                st.subheader("Past Assessments")
                for assessment in past_assessments:
                    with st.expander(f"{assessment['subject']} - {assessment['taken_at']}"):
                        st.write(f"Score: {assessment['score']*100:.1f}%")
                        st.write("Feedback:", assessment['feedback'])


if __name__ == "__main__":
    init_db()
    main()
