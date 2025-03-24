-- Create the database
CREATE DATABASE youtube_data;

-- Switch to the database
USE youtube_data;

-- Create the channels table
CREATE TABLE channels (
    channel_id VARCHAR(255) PRIMARY KEY,
    channel_name VARCHAR(255),
    subscribers INT,
    total_videos INT,
    view_count BIGINT,
    playlist_id VARCHAR(255)
);

-- Create the videos table with foreign key reference to channels
CREATE TABLE videos (
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
);
