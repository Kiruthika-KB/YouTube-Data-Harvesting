import streamlit as st
from googleapiclient.discovery import build
import mysql.connector
from sqlalchemy import create_engine, text, exc
import pandas as pd
import re
from datetime import datetime, timedelta

# Function to get YouTube channel details
def get_channel_data(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    try:
        request = youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=channel_id
        )
        response = request.execute()
        if 'items' not in response or len(response['items']) == 0:
            st.error("No data found for the given channel ID.")
            return None

        channel = response['items'][0]
        channel_name = channel['snippet']['title']
        subscriber_count = channel['statistics']['subscriberCount']
        video_count = channel['statistics']['videoCount']
        view_count = channel['statistics'].get('viewCount', 0)  # Added view count
        playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']

        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "subscribers": subscriber_count,
            "total_videos": video_count,
            "view_count": view_count,  # Added view count
            "playlist_id": playlist_id
        }
    except Exception as e:
        st.error(f"Error fetching channel data: {e}")
        return None

# Function to get video details - updated to include more data
def get_video_data(api_key, playlist_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    try:
        videos = []
        next_page_token = None
        
        # Get up to 50 videos (5 pages of 10 results)
        for _ in range(5):
            request = youtube.playlistItems().list(
                part='snippet,contentDetails',
                playlistId=playlist_id,
                maxResults=10,
                pageToken=next_page_token
            )
            response = request.execute()
            if 'items' not in response or len(response['items']) == 0:
                break

            video_ids = [item['contentDetails']['videoId'] for item in response['items']]
            
            # Get detailed video information
            video_request = youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(video_ids)
            )
            video_response = video_request.execute()
            
            for item in video_response.get('items', []):
                video_id = item['id']
                stats = item.get('statistics', {})
                snippet = item.get('snippet', {})
                content_details = item.get('contentDetails', {})
                
                # Extract duration
                duration_str = content_details.get('duration', 'PT0S')  # Default to 0 seconds
                # Convert ISO 8601 duration to seconds
                duration_seconds = parse_duration(duration_str)
                
                # Get published date
                published_at = snippet.get('publishedAt', '')
                
                videos.append({
                    "video_id": video_id,
                    "title": snippet.get('title', ''),
                    "published_at": published_at,
                    "published_year": published_at[:4] if published_at else '',
                    "view_count": int(stats.get('viewCount', 0)),
                    "likes": int(stats.get('likeCount', 0)),
                    "dislikes": int(stats.get('dislikeCount', 0)) if 'dislikeCount' in stats else 0,
                    "comments": int(stats.get('commentCount', 0)),
                    "duration": duration_seconds,
                    "channel_id": snippet.get('channelId', '')
                })
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
                
        return videos
    except Exception as e:
        st.error(f"Error fetching video data: {e}")
        return []

# Parse YouTube duration format (ISO 8601)
def parse_duration(duration_str):
    # Extract hours, minutes, seconds
    hours = re.search(r'(\d+)H', duration_str)
    minutes = re.search(r'(\d+)M', duration_str)
    seconds = re.search(r'(\d+)S', duration_str)
    
    hours = int(hours.group(1)) if hours else 0
    minutes = int(minutes.group(1)) if minutes else 0
    seconds = int(seconds.group(1)) if seconds else 0
    
    return hours * 3600 + minutes * 60 + seconds

# Format seconds to HH:MM:SS
def format_duration(seconds):
    return str(timedelta(seconds=seconds))

# Check if channel exists in database
def channel_exists(engine, channel_id):
    try:
        query = f"SELECT 1 FROM channels WHERE channel_id = '{channel_id}' LIMIT 1"
        result = pd.read_sql(query, con=engine)
        return not result.empty
    except Exception as e:
        st.error(f"Error checking if channel exists: {e}")
        return False

# Store channel data
def store_channel_data(channel_data, engine):
    try:
        # Check if channel already exists
        if channel_exists(engine, channel_data['channel_id']):
            st.warning(f"Channel '{channel_data['channel_name']}' already exists in the database. Data will be updated.")
            # Delete existing channel data
            with engine.connect() as conn:
                # First delete related videos since they reference the channel
                conn.execute(text(f"DELETE FROM videos WHERE channel_id = '{channel_data['channel_id']}'"))
                # Then delete the channel
                conn.execute(text(f"DELETE FROM channels WHERE channel_id = '{channel_data['channel_id']}'"))
                conn.commit()
        
        df = pd.DataFrame([channel_data])
        df.to_sql('channels', con=engine, if_exists='append', index=False)
        st.success("Channel data successfully stored.")
        
        # Display the stored channel data
        st.subheader("Channel Data Stored:")
        display_df = df.copy()
        # Format subscriber count and view count for display
        display_df['subscribers'] = display_df['subscribers'].apply(lambda x: f"{int(x):,}")
        display_df['view_count'] = display_df['view_count'].apply(lambda x: f"{int(x):,}")
        st.dataframe(display_df)
        
        return True
    except exc.IntegrityError:
        st.error(f"Channel ID '{channel_data['channel_id']}' already exists in the database. Try using a different channel ID.")
        return False
    except Exception as e:
        st.error(f"Error storing channel data: {e}")
        return False

# Store video data
def store_video_data(engine, channel_id, video_data):
    try:
        for video in video_data:
            video['channel_id'] = channel_id
        
        # Check for existing videos
        existing_videos = []
        for video in video_data:
            if video_exists(engine, video['video_id']):
                existing_videos.append(video['video_id'])
        
        # Delete existing videos if any
        if existing_videos:
            with engine.connect() as conn:
                for video_id in existing_videos:
                    conn.execute(text(f"DELETE FROM videos WHERE video_id = '{video_id}'"))
                conn.commit()
                
        df = pd.DataFrame(video_data)
        df.to_sql('videos', con=engine, if_exists='append', index=False)
        st.success(f"Video data successfully stored. Total videos: {len(video_data)}")
        
        # Display a sample of stored video data
        if not df.empty:
            st.subheader("Sample of Videos Stored:")
            sample_df = df.head(5).copy()
            # Format view count and duration for display
            sample_df['view_count'] = sample_df['view_count'].apply(lambda x: f"{int(x):,}")
            sample_df['duration'] = sample_df['duration'].apply(lambda x: format_duration(int(x)))
            # Select only the most relevant columns
            display_columns = ['title', 'published_year', 'view_count', 'likes', 'comments', 'duration']
            st.dataframe(sample_df[display_columns])
            
            if len(df) > 5:
                st.info(f"Showing 5 of {len(df)} videos. Use the Analysis Queries tab to explore all data.")
        
        return True
    except Exception as e:
        st.error(f"Error storing video data: {e}")
        return False

# Check if video exists in database
def video_exists(engine, video_id):
    try:
        query = f"SELECT 1 FROM videos WHERE video_id = '{video_id}' LIMIT 1"
        result = pd.read_sql(query, con=engine)
        return not result.empty
    except Exception:
        return False

# Create database engine
def create_db_engine():
    # Default database credentials
    db_user = "root"
    db_password = "root"
    db_host = "localhost"
    db_name = "youtube_data"
    return create_engine(f'mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}')

# Run SQL Query and display results
def run_query(engine, query):
    try:
        result = pd.read_sql(query, con=engine)
        if not result.empty:
            st.dataframe(result)
        else:
            st.info("No results found for this query.")
    except Exception as e:
        st.error(f"Error executing query: {e}")

# Define SQL queries
def get_sql_queries():
    return {
        "1. Videos and their channels": """
            SELECT v.title AS video_name, c.channel_name
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            ORDER BY c.channel_name, v.title;
        """,
        
        "2. Channels with most videos": """
            SELECT c.channel_name, COUNT(v.video_id) AS video_count
            FROM channels c
            JOIN videos v ON c.channel_id = v.channel_id
            GROUP BY c.channel_name
            ORDER BY video_count DESC;
        """,
        
        "3. Top 10 most viewed videos": """
            SELECT v.title AS video_name, c.channel_name, v.view_count
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            ORDER BY v.view_count DESC
            LIMIT 10;
        """,
        
        "4. Comments on each video": """
            SELECT v.title AS video_name, v.comments
            FROM videos v
            ORDER BY v.comments DESC;
        """,
        
        "5. Videos with highest likes": """
            SELECT v.title AS video_name, c.channel_name, v.likes
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            ORDER BY v.likes DESC;
        """,
        
        "6. Total likes and dislikes by video": """
            SELECT v.title AS video_name, v.likes, v.dislikes
            FROM videos v
            ORDER BY (v.likes + v.dislikes) DESC;
        """,
        
        "7. Total views by channel": """
            SELECT c.channel_name, c.view_count
            FROM channels c
            ORDER BY c.view_count DESC;
        """,
        
        "8. Channels with videos in 2022": """
            SELECT DISTINCT c.channel_name
            FROM channels c
            JOIN videos v ON c.channel_id = v.channel_id
            WHERE v.published_year = '2022';
        """,
        
        "9. Average video duration by channel": """
            SELECT c.channel_name, AVG(v.duration) AS avg_duration_seconds
            FROM channels c
            JOIN videos v ON c.channel_id = v.channel_id
            GROUP BY c.channel_name
            ORDER BY avg_duration_seconds DESC;
        """,
        
        "10. Videos with most comments": """
            SELECT v.title AS video_name, c.channel_name, v.comments
            FROM videos v
            JOIN channels c ON v.channel_id = c.channel_id
            ORDER BY v.comments DESC;
        """
    }

# Initialize database
def initialize_database():
    try:
        # Connect to MySQL and create database if it doesn't exist
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="root"
        )
        cursor = conn.cursor()
        
        # Create database if it doesn't exist
        cursor.execute("CREATE DATABASE IF NOT EXISTS youtube_data")
        cursor.execute("USE youtube_data")
        
        # Create channels table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS channels (
                channel_id VARCHAR(255) PRIMARY KEY,
                channel_name VARCHAR(255),
                subscribers INT,
                total_videos INT,
                view_count BIGINT,
                playlist_id VARCHAR(255)
            )
        """)
        
        # Create videos table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id VARCHAR(255) PRIMARY KEY,
                channel_id VARCHAR(255),
                title VARCHAR(255),
                published_at VARCHAR(255),
                published_year VARCHAR(4),
                view_count BIGINT,
                likes INT,
                dislikes INT,
                comments INT,
                duration INT,
                FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return True
    except Exception as e:
        st.error(f"Error initializing database: {e}")
        return False

# Streamlit app
st.title("YouTube Channel Data Analyzer")

# Initialize database
if 'db_initialized' not in st.session_state:
    st.session_state.db_initialized = initialize_database()

# Fixed API key - you can replace this with your actual API key
api_key = 'AIzaSyB8uUcN8GmTC55doQqwT9eOwGz5W_CGUJo'
channel_id = st.text_input("Enter YouTube Channel ID")

# Button to fetch and store data
if st.button("Fetch and Store Data"):
    if channel_id:
        try:
            engine = create_db_engine()
            channel_data = get_channel_data(api_key, channel_id)
            if channel_data:
                # Store channel data and display it
                if store_channel_data(channel_data, engine):
                    video_data = get_video_data(api_key, channel_data['playlist_id'])
                    if video_data:
                        store_video_data(engine, channel_data['channel_id'], video_data)
                    else:
                        st.warning("No videos found for this channel.")
            else:
                st.error("Failed to fetch channel data. Please check if the Channel ID is correct.")
        except Exception as e:
            st.error(f"Error: {e}")
    else:
        st.error("Please provide a YouTube Channel ID.")

# Create tabs for different functionalities
tab1, tab2 = st.tabs(["Search", "Analysis Queries"])

with tab1:
    st.header("Search YouTube Data")
    search_query = st.text_input("Search (Channel Name or Video Title)")
    if st.button("Search"):
        if search_query:
            engine = create_db_engine()
            query = f"""
            SELECT c.channel_name, c.subscribers, c.total_videos, 
                   v.title AS video_title, v.view_count, v.likes, v.comments
            FROM channels c
            LEFT JOIN videos v ON c.channel_id = v.channel_id
            WHERE c.channel_name LIKE '%{search_query}%' 
               OR v.title LIKE '%{search_query}%';
            """
            run_query(engine, query)
        else:
            st.error("Please enter a search query.")

with tab2:
    st.header("YouTube Data Analysis")
    
    # Get SQL queries
    queries = get_sql_queries()
    
    # Create a selectbox for queries
    query_option = st.selectbox(
        "Select an analysis query:", 
        list(queries.keys())
    )
    
    if st.button("Run Analysis"):
        engine = create_db_engine()
        selected_query = queries[query_option]
        
        st.subheader(query_option)
        
        # Hide the query display - removed the st.code() line
        
        # Run the query and display results
        st.subheader("Results:")
        
        # Special handling for the 9th query (average duration)
        if "9. Average video duration by channel" in query_option:
            try:
                result = pd.read_sql(selected_query, con=engine)
                if not result.empty:
                    # Create a new dataframe with formatted durations and renamed column
                    formatted_result = pd.DataFrame()
                    formatted_result['channel_name'] = result['channel_name']
                    formatted_result['average duration'] = result['avg_duration_seconds'].apply(
                        lambda x: format_duration(int(x))
                    )
                    st.dataframe(formatted_result)
                else:
                    st.info("No results found for this query.")
            except Exception as e:
                st.error(f"Error executing query: {e}")
        else:
            # For all other queries, use the standard run_query function
            run_query(engine, selected_query)
