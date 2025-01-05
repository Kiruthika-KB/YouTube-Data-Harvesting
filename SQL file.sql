-- Create the database
CREATE DATABASE youtube_data;

-- Switch to the database
USE youtube_data;

-- Create the channels table
CREATE TABLE channels (
    id INT AUTO_INCREMENT PRIMARY KEY,
    channel_id VARCHAR(255) NOT NULL,
    channel_name VARCHAR(255) NOT NULL,
    subscribers BIGINT,
    total_videos INT,
    playlist_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE INDEX (channel_id) -- Add index for foreign key
);

-- Create the videos table
CREATE TABLE videos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    video_id VARCHAR(255) NOT NULL,
    title VARCHAR(255),
    likes BIGINT DEFAULT 0,
    dislikes BIGINT DEFAULT 0,
    comments BIGINT DEFAULT 0,
    channel_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id) ON DELETE CASCADE
);
