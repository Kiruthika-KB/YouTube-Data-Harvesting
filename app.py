import streamlit as st
from googleapiclient.discovery import build
import mysql.connector
from sqlalchemy import create_engine
import pandas as pd

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
        playlist_id = channel['contentDetails']['relatedPlaylists']['uploads']

        return {
            "channel_id": channel_id,
            "channel_name": channel_name,
            "subscribers": subscriber_count,
            "total_videos": video_count,
            "playlist_id": playlist_id
        }
    except Exception as e:
        st.error(f"Error fetching channel data: {e}")
        return None

# Function to get video details
def get_video_data(api_key, playlist_id):
    youtube = build('youtube', 'v3', developerKey=api_key)
    try:
        request = youtube.playlistItems().list(
            part='snippet,contentDetails',
            playlistId=playlist_id,
            maxResults=10
        )
        response = request.execute()
        if 'items' not in response or len(response['items']) == 0:
            st.error("No videos found for the given playlist.")
            return []

        videos = []
        for item in response['items']:
            video_id = item['contentDetails']['videoId']
            title = item['snippet']['title']
            video_request = youtube.videos().list(
                part='statistics',
                id=video_id
            )
            video_response = video_request.execute()
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

# Store channel data
def store_channel_data(channel_data, engine):
    try:
        df = pd.DataFrame([channel_data])
        df.to_sql('channels', con=engine, if_exists='append', index=False)
        st.success("Channel data successfully stored.")
    except Exception as e:
        st.error(f"Error storing channel data: {e}")

# Store video data
def store_video_data(engine, channel_id, video_data):
    try:
        for video in video_data:
            video['channel_id'] = channel_id
        df = pd.DataFrame(video_data)
        df.to_sql('videos', con=engine, if_exists='append', index=False)
        st.success("Video data successfully stored.")
    except Exception as e:
        st.error(f"Error storing video data: {e}")

# Create database engine
def create_db_engine(user, password, host, database):
    return create_engine(f'mysql+mysqlconnector://{user}:{password}@{host}/{database}')

# Streamlit app
st.title("YouTube Channel Data Analyzer")

# Input: YouTube API Key and Channel ID
api_key = 'AIzaSyB8uUcN8GmTC55doQqwT9eOwGz5W_CGUJo'
channel_id = st.text_input("Enter YouTube Channel ID")

# Button to fetch and store data
if st.button("Fetch and Store Data"):
    if api_key and channel_id:
        engine = create_db_engine('root', 'root', 'localhost', 'youtube_data')
        channel_data = get_channel_data(api_key, channel_id)
        if channel_data:
            store_channel_data(channel_data, engine)
            video_data = get_video_data(api_key, channel_data['playlist_id'])
            store_video_data(engine, channel_data['channel_id'], video_data)
        else:
            st.error("Failed to fetch channel data.")
    else:
        st.error("Please provide API Key and Channel ID.")

# Search functionality
search_query = st.text_input("Search (Channel Name or Video Title)")
if st.button("Search"):
    if search_query:
        engine = create_db_engine('root', 'root', 'localhost', 'youtube_data')
        query = f"""
        SELECT c.channel_name, c.subscribers, c.total_videos, 
               v.title AS video_title, v.likes, v.dislikes, v.comments
        FROM channels c
        LEFT JOIN videos v ON c.channel_id = v.channel_id
        WHERE c.channel_name LIKE '%{search_query}%' 
           OR v.title LIKE '%{search_query}%';
        """
        try:
            result = pd.read_sql(query, con=engine)
            if not result.empty:
                st.write(result)
            else:
                st.error("No results found.")
        except Exception as e:
            st.error(f"Error during search: {e}")
    else:
        st.error("Please enter a search query.")
