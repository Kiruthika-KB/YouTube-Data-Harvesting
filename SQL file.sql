USE youtube_data;  -- Make sure you're using the correct database

CREATE TABLE channels (
    channel_id VARCHAR(255) PRIMARY KEY,
    channel_name VARCHAR(255),
    subscribers INT,
    total_videos INT,
    playlist_id VARCHAR(255)
);

CREATE TABLE videos (
    video_id VARCHAR(255) PRIMARY KEY,
    channel_id VARCHAR(255),
    video_title VARCHAR(255),
    likes INT,
    dislikes INT,
    comments INT,
    FOREIGN KEY (channel_id) REFERENCES channels(channel_id)
);
