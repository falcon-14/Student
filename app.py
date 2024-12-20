import streamlit as st
import os
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import plotly.graph_objects as go

# Configure API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyC6ivZ-3UtC4R3nZxmPsJGbAEpRuY40LBc"  # Replace with your API key

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.2)

# Initialize session state
def init_session_state():
    if 'users' not in st.session_state:
        st.session_state.users = {}
    if 'current_user' not in st.session_state:
        st.session_state.current_user = None
    if 'learning_paths' not in st.session_state:
        st.session_state.learning_paths = {}
    if 'assessments' not in st.session_state:
        st.session_state.assessments = {}
    if 'current_assessment' not in st.session_state:
        st.session_state.current_assessment = None

def authenticate_user(username, password):
    if username in st.session_state.users:
        if st.session_state.users[username]['password'] == password:
            return st.session_state.users[username]
    return None

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
    type (video/article/exercise/course), and description.
    
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
                        "description": "<detailed description>"
                    }}
                ],
                "practice_exercises": [
                    {{
                        "description": "<specific exercise description>",
                        "difficulty": "<beginner/intermediate/advanced>"
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
        return json.loads(content_str)
    except Exception as e:
        st.error(f"Failed to generate learning path: {str(e)}")
        return None

def display_learning_path(username, path_id, path_data):
    st.subheader(f"{path_data['subject']} - {path_data['difficulty_level']}")
    
    # Progress and timeline
    col1, col2 = st.columns(2)
    with col1:
        st.progress(path_data['progress'])
        st.write(f"Progress: {path_data['progress']*100:.1f}%")
    with col2:
        days_remaining = (datetime.strptime(path_data['target_completion_date'], '%Y-%m-%d').date() - datetime.now().date()).days
        st.write(f"Target completion: {path_data['target_completion_date']}")
        st.write(f"Days remaining: {days_remaining}")
    
    try:
        content = path_data['content']
        
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
                        with st.expander(f"{resource.get('title', 'Untitled')} ({resource.get('type', 'Resource')})"):
                            st.markdown(f"**Description:** {resource.get('description', 'No description available')}")
                
                st.subheader("💪 Practice Exercises")
                exercises = topic.get('practice_exercises', [])
                if exercises:
                    for exercise in exercises:
                        with st.expander(f"{exercise.get('difficulty', 'General').title()} Level Exercise"):
                            st.markdown(exercise.get('description', 'No description available'))
                
                if st.button(f"Take Assessment: {topic.get('name', 'Unnamed Topic')}", 
                           key=f"assess_{path_id}_{topic.get('name', 'unnamed')}"):
                    assessment = generate_assessment(topic.get('name', 'General Topic'))
                    st.session_state.current_assessment = {
                        'topic': topic.get('name', 'General Topic'),
                        'question': assessment['question'],
                        'path_id': path_id
                    }
        
        # Progress update section
        st.subheader("📈 Update Progress")
        new_progress = st.slider(
            "Update your progress",
            0.0,
            1.0,
            path_data['progress'],
            key=f"slider_{path_id}"
        )
        
        if st.button("Save Progress", key=f"save_{path_id}"):
            st.session_state.learning_paths[username][path_id]['progress'] = new_progress
            st.session_state.learning_paths[username][path_id]['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            st.success("Progress updated successfully!")
            
    except Exception as e:
        st.error(f"Error displaying learning path: {str(e)}")

def display_analytics(username):
    # Convert learning paths data to DataFrame
    paths_data = []
    for path_id, path in st.session_state.learning_paths[username].items():
        paths_data.append({
            'subject': path['subject'],
            'progress': path['progress'],
            'last_updated': path['last_updated']
        })
    
    if not paths_data:
        st.info("Start learning to see your progress analytics!")
        return
        
    df = pd.DataFrame(paths_data)
    
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

    # Progress Over Time
    st.subheader("📈 Progress Timeline")
    if not df.empty:
        # Convert last_updated to datetime
        df['last_updated'] = pd.to_datetime(df['last_updated'])
        
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
        if username in st.session_state.assessments and st.session_state.assessments[username]:
            assessment_df = pd.DataFrame(st.session_state.assessments[username])
            assessment_df['taken_at'] = pd.to_datetime(assessment_df['taken_at'])
            
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
            assessment_scatter.update_traces(
                y=assessment_df['score'] * 100, 
                mode='markers',
                marker=dict(symbol='star', size=12)
            )
            
            for trace in assessment_scatter.data:
                fig_timeline.add_trace(trace)

        fig_timeline.update_layout(
            hovermode='x unified',
            yaxis_title="Progress/Score (%)"
        )
        st.plotly_chart(fig_timeline, use_container_width=True)

    # Time Management
    st.subheader("⏰ Time Management Insights")
    if not df.empty:
        df['hour'] = df['last_updated'].dt.hour
        df['day'] = df['last_updated'].dt.day_name()
        
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
        inactive_subjects = df[df['last_updated'] < 
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
    
    # Initialize session state
    init_session_state()
    
    # Sidebar
    with st.sidebar:
        st.title("🎓 AI Learning Assistant")
        if st.session_state.current_user:
            st.write(f"Welcome, {st.session_state.current_user['username']}!")
            if st.button("Logout"):
                st.session_state.current_user = None
                st.rerun()
    
    # Login/Register page
    if not st.session_state.current_user:
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("Login")
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            if st.button("Login"):
                user = authenticate_user(username, password)
                if user:
                    st.session_state.current_user = user
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
                if new_username in st.session_state.users:
                    st.error("Username already exists")
                else:
                    st.session_state.users[new_username] = {
                        'username': new_username,
                        'password': new_password,
                        'interests': interests,
                        'learning_style': learning_style
                    }
                    st.session_state.learning_paths[new_username] = {}
                    st.session_state.assessments[new_username] = []
                    st.success("Registration successful! Please login.")
    
    # Main application interface
    else:
        username = st.session_state.current_user['username']
        tabs = st.tabs(["Learning Dashboard", "Create New Path", "Progress Analytics", "Assessments"])
        
        # Dashboard Tab
        with tabs[0]:
            st.header("Your Learning Dashboard")
            
            if username in st.session_state.learning_paths and st.session_state.learning_paths[username]:
                for path_id, path_data in st.session_state.learning_paths[username].items():
                    display_learning_path(username, path_id, path_data)
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
                st.write(f"Learning Style: {st.session_state.current_user['learning_style']}")
                st.write(f"Interests: {st.session_state.current_user['interests']}")
            
            if st.button("Generate Learning Path"):
                with st.spinner("Generating personalized learning path..."):
                    path_content = generate_learning_path(
                        subject,
                        st.session_state.current_user['interests'],
                        st.session_state.current_user['learning_style'],
                        target_days
                    )
                    
                    if path_content:
                        path_id = f"path_{len(st.session_state.learning_paths[username])}"
                        st.session_state.learning_paths[username][path_id] = {
                            'subject': subject,
                            'progress': 0.0,
                            'difficulty_level': difficulty,
                            'content': path_content,
                            'target_completion_date': (datetime.now() + timedelta(days=target_days)).strftime('%Y-%m-%d'),
                            'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        st.success("Learning path created successfully!")
                        st.rerun()
        
        with tabs[2]:
            st.header("Progress Analytics")
            if st.session_state.current_user:
                username = st.session_state.current_user['username']
                if username in st.session_state.learning_paths:
                    display_analytics(username)
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
                    
                    st.session_state.assessments[username].append({
                        'subject': assessment['topic'],
                        'topic': assessment['topic'],
                        'score': evaluation['score'],
                        'feedback': evaluation['feedback'],
                        'taken_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    })
                    
                    st.write("Score:", f"{evaluation['score']*100:.1f}%")
                    st.write("Feedback:", evaluation['feedback'])
                    st.write("Correct Approach:", evaluation['correct_answer'])
                    
                    if st.button("Clear Assessment"):
                        st.session_state.current_assessment = None
                        st.rerun()
            
            # Display past assessments
            if username in st.session_state.assessments and st.session_state.assessments[username]:
                st.subheader("Past Assessments")
                for assessment in reversed(st.session_state.assessments[username]):
                    with st.expander(f"{assessment['subject']} - {assessment['taken_at']}"):
                        st.write(f"Score: {assessment['score']*100:.1f}%")
                        st.write("Feedback:", assessment['feedback'])

if __name__ == "__main__":
    main()
