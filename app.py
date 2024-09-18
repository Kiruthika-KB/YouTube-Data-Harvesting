import streamlit as st
from googleapiclient.discovery import build
import mysql.connector
from sqlalchemy import create_engine
import pandas as pd

# Function to get YouTube channel details with error handling
def get_channel_data(api_key, channel_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    try:
        request = youtube.channels().list(
            part='snippet,statistics,contentDetails',
            id=channel_id
        )
        response = request.execute()

        # Check if 'items' exists in the response
        if 'items' not in response or len(response['items']) == 0:
            st.error("No data found for the given channel ID.")
            return None

        channel = response['items'][0]
        channel_name = channel['snippet']['title']
        subscriber_count = channel['statistics']['subscriberCount']
        video_count = channel['statistics']['videoCount']
        playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']

        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "subscribers": subscriber_count,
            "total_videos": video_count,
            "playlist_id": playlist_id
        }
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return None

# Function to get video details from a playlist with error handling
def get_video_data(api_key, playlist_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    try:
        request = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=playlist_id,
            maxResults=10  # Limiting to 10 videos for demo
        )
        response = request.execute()

        if 'items' not in response or len(response['items']) == 0:
            st.error("No videos found for the given playlist.")
            return []

        videos = []
        for item in response['items']:
            video_id = item['contentDetails']['videoId']
            title = item['snippet']['title']

            # Fetch video statistics
            video_request = youtube.videos().list(
                part='statistics',
                id=video_id
            )
            video_response = video_request.execute()

            # Check if 'items' exists in the video response
            if 'items' in video_response and len(video_response['items']) > 0:
                stats = video_response['items'][0]['statistics']
                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "likes": stats.get('likeCount', 0),
                    "dislikes": stats.get('dislikeCount', 0),
                    "comments": stats.get('commentCount', 0)
                })
        return videos
    except Exception as e:
        st.error(f"Error fetching video data: {e}")
        return []
            
        
def store_channel_data(channel_data, engine, table_name):
    try:
        with engine.connect() as conn:
            #st.write(f"Storing channel data: {channel_data}")
            # Ensure channel_data is a list of dictionaries
            if isinstance(channel_data, dict):
                channel_data = [channel_data]
            
            df = pd.DataFrame(channel_data)
            df.to_sql(table_name, con=engine, if_exists='append', index=False)
            
            st.success("Channel data successfully stored.")
    except Exception as e:
        st.error(f"Error storing channel data: {e}")

# Function to create a database engine connection
def create_db_engine(mysql, user, password, host, database):
    engine = create_engine(f'mysql+mysqlconnector://root:root@localhost/youtube_data')
    
    return engine

# Streamlit app
st.title("YouTube Channel Data Analyzer")

# Input: YouTube API Key and Channel ID
api_key = 'AIzaSyB8uUcN8GmTC55doQqwT9eOwGz5W_CGUJo'
channel_id = st.text_input("Enter YouTube Channel ID")

        
# Button to fetch and display data
if st.button("Fetch Data"):
    if api_key and channel_id:
        # Fetch the data and store it in session state
        st.session_state['channel_data'] = get_channel_data(api_key, channel_id)
        
        if st.session_state['channel_data']:  # Check if channel_data is not None
            channel_data = st.session_state['channel_data']
            st.write(f"Channel Name: {channel_data['channel_name']}")
            st.write(f"Subscribers: {channel_data['subscribers']}")
            st.write(f"Total Videos: {channel_data['total_videos']}")
            playlist_id = channel_data['playlist_id']
            st.write(f"Playlist ID: {playlist_id}")

            video_data = get_video_data(api_key, playlist_id)
            st.write("Video Data")
            st.write(pd.DataFrame(video_data))
        else:
            st.error("Failed to fetch channel data.")
    else:
        st.error("Please provide Channel ID")

# Database connection details
#db_type = st.selectbox("Choose Database", ["mysql", "postgresql"])
db_user = 'root'
db_password = 'root'
db_host = 'localhost'
db_name = 'youtube_data'

        
# Store data in MySQL/PostgreSQL when "Store Data" button is clicked
if st.button("Store Data"):
    if 'channel_data' in st.session_state:
        # Establish database connection
        engine = create_engine('mysql+mysqlconnector://root:root@localhost/youtube_data')
        store_channel_data(st.session_state['channel_data'], engine, 'channels')
    else:
        st.error("No channel data to store. Please fetch the data first.")

# Search functionality
search_query = st.text_input("Search Channel or Video")
if st.button("Search"):
    if search_query:
        engine = create_db_engine('mysql', db_user, db_password, db_host, db_name)
        query = f"SELECT * FROM channels WHERE channel_id LIKE '%{search_query}%'"
        result = pd.read_sql(query, con=engine)
        st.write(result)
    else:
        st.error("Please provide a search query")