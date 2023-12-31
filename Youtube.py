from googleapiclient.discovery import build
import pymongo
import psycopg2
import pandas as pd
import streamlit as st
import numpy as np
import altair as alt


#Youtube API Key Connection
def api_connect():
    api_id="AIzaSyAf8t63J8EaSMUMAQ8H6rfKpSa1IL2BAfY"
    api_service_name="youtube"
    api_version="v3"

    youtube=build(api_service_name, api_version, developerKey=api_id)
    return youtube

youtube=api_connect()


#get channels information:
def get_channel_info(channel_id):
    request=youtube.channels().list(
                    part="Snippet, ContentDetails, Statistics",
                    id=channel_id
    )
    response=request.execute()

    for i in response['items']:
        data=dict(Channel_Name=i['snippet']['title'],
                Channel_Id=i['id'],
                Subscribers=i['statistics']['subscriberCount'],
                Views=i['statistics']['viewCount'],
                Total_Videos=i['statistics']['videoCount'],
                Channel_Description=i['snippet']['description'],
                Playlist_id=i['contentDetails']['relatedPlaylists']['uploads'])
        
    return data


#get video id's
def get_videos_ids(channel_id):
    video_ids=[]
    response=youtube.channels().list(id=channel_id,
                                    part='contentDetails').execute()
    Playlist_Id=response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

    next_page_token=None

    while True:
        response1=youtube.playlistItems().list(
                                            part='snippet',
                                            playlistId=Playlist_Id,
                                            maxResults=50,
                                            pageToken=next_page_token).execute()
        for i in range(len(response1['items'])):
            video_ids.append(response1['items'][i]['snippet']['resourceId']['videoId'])
        next_page_token=response1.get('nextPageToken')

        if next_page_token is None:
            break
    return video_ids


#get video information
def get_video_info(video_ids):
    video_data=[]
    for video_id in video_ids:
        request=youtube.videos().list(
            part="snippet,ContentDetails,statistics",
            id=video_id)
        response=request.execute()

        for item in response["items"]:
            data=dict(Channel_Name=item['snippet']['channelTitle'],
                    Channel_Id=item['snippet']['channelId'],
                    Video_Id=item['id'],
                    Title=item['snippet']['title'],
                    Tags=item['snippet'].get('tags'),
                    Thumbnail=item['snippet']['thumbnails']['default']['url'],
                    Description=item['snippet'].get('description'),
                    Published_Date=item['snippet']['publishedAt'],
                    Duration=item['contentDetails']['duration'],
                    Views=item['statistics'].get('viewCount'),
                    Likes=item['statistics'].get('likeCount'),
                    Comments=item['statistics'].get('commentCount'),
                    Favorite_Count=item['statistics']['favoriteCount'],
                    Definition=item['contentDetails']['definition'],
                    Caption_Status=item['contentDetails']['caption']
                    )
            
            video_data.append(data)
    return video_data


#get comment information
def get_comment_info(video_ids):
    comment_data=[]
    try:
        for video_id in video_ids:
            request=youtube.commentThreads().list(
                part="snippet",
                videoId=video_id,
                maxResults=50
            )
            response=request.execute()

            for item in response['items']:
                data=dict(Comment_Id=item['snippet']['topLevelComment']['id'],
                        Video_Id=item['snippet']['topLevelComment']['snippet']['videoId'],
                        Comment_Text=item['snippet']['topLevelComment']['snippet']['textDisplay'],
                        Comment_Author=item['snippet']['topLevelComment']['snippet']['authorDisplayName'],
                        Comment_Published=item['snippet']['topLevelComment']['snippet']['publishedAt'])
                comment_data.append(data)
                
    except:
        pass
    return comment_data


#get playlist details
def get_playlist_details(channel_id):
    next_page_token=None
    playlist_data=[]
    while True:
        request=youtube.playlists().list(
            part='snippet,contentDetails',
            channelId=channel_id,
            maxResults=50,
            pageToken=next_page_token
        )
        response=request.execute()

        for item in response['items']:
            data=dict(Playlist_Id=item['id'],
                    Title=item['snippet']['title'],
                    Channel_Id=item['snippet']['channelId'],
                    Channel_Name=item['snippet']['channelTitle'],
                    PublishedAt=item['snippet']['publishedAt'],
                    Video_Count=item['contentDetails']['itemCount'])
            playlist_data.append(data)

        next_page_token=response.get('nextPageToken')
        if next_page_token is None:
            break
    return playlist_data


#Upload to MongoDB
client=pymongo.MongoClient("mongodb+srv://kprajkumar98:rajkumar@youtube.hi0povp.mongodb.net/?retryWrites=true&w=majority")
db=client["Youtube_data"]


#Functions to get Channel_details
def channel_details(channel_id):
    ch_details=get_channel_info(channel_id)
    pl_details=get_playlist_details(channel_id)
    vi_ids=get_videos_ids(channel_id)
    vi_details=get_video_info(vi_ids)
    com_details=get_comment_info(vi_ids)

    collection1=db["Channel_details"]
    collection1.insert_one({"channel_information":ch_details,"playlist_information":pl_details,
                            "video_information":vi_details,"comment_information":com_details})

    return "Upload Completed Successfully!"
    

#Table creation for Channels
def channels_table():
    mydb=psycopg2.connect(host="localhost",
                                user="postgres",
                                password="rajkumar",
                                database="youtube_data",
                                port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists channels'''
    cursor.execute(drop_query)
    mydb.commit()

    create_query='''create table if not exists channels(Channel_Name varchar(100),
                                                            Channel_Id varchar(80) primary key,
                                                            Subscribers bigint,
                                                            Views bigint,
                                                            Total_Videos int,
                                                            Channel_Description text,
                                                            Playlist_id varchar(80))'''
        
    cursor.execute(create_query)
    mydb.commit()


    ch_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for ch_data in collection1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=pd.DataFrame(ch_list)

    for index,row in df.iterrows():
        insert_query='''insert into channels(Channel_Name,
                                            Channel_Id,
                                            Subscribers,
                                            Views,
                                            Total_Videos,
                                            Channel_Description,
                                            Playlist_id)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s)'''
        values=(row['Channel_Name'],
                row['Channel_Id'],
                row['Subscribers'],
                row['Views'],
                row['Total_Videos'],
                row['Channel_Description'],
                row['Playlist_id'])
        
        cursor.execute(insert_query,values)
        mydb.commit()


#Table creation for Playlist
def playlists_table():
    mydb=psycopg2.connect(host="localhost",
                                user="postgres",
                                password="rajkumar",
                                database="youtube_data",
                                port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists playlists'''
    cursor.execute(drop_query)
    mydb.commit()

    create_query='''create table if not exists playlists(Playlist_Id varchar(100) primary key,
                                                    Title varchar(100),
                                                    Channel_Id varchar(100),
                                                    Channel_Name varchar(100),
                                                    PublishedAt timestamp,
                                                    Video_Count bigint)'''

    cursor.execute(create_query)
    mydb.commit()

    pl_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for pl_data in collection1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=pd.DataFrame(pl_list)

    for index,row in df1.iterrows():
        insert_query='''insert into playlists(Playlist_Id,
                                              Title,
                                              Channel_Id,
                                              Channel_Name,
                                              PublishedAt,
                                              Video_Count)
                                            
                                              values(%s,%s,%s,%s,%s,%s)'''
        values=(row['Playlist_Id'],
                row['Title'],
                row['Channel_Id'],
                row['Channel_Name'],
                row['PublishedAt'],
                row['Video_Count'])
        
        cursor.execute(insert_query,values)
        mydb.commit()


#Table creation for Videos
def videos_table():
    mydb=psycopg2.connect(host="localhost",
                                user="postgres",
                                password="rajkumar",
                                database="youtube_data",
                                port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists videos'''
    cursor.execute(drop_query)
    mydb.commit()

    create_query='''create table if not exists videos(Channel_Name varchar(100),
                                                    Channel_Id varchar(100),
                                                    Video_Id varchar(30) primary key,
                                                    Title varchar(150),
                                                    Tags text,
                                                    Thumbnail varchar(200),
                                                    Description text,
                                                    Published_Date timestamp,
                                                    Duration interval,
                                                    Views bigint,
                                                    Likes bigint,
                                                    Comments int,
                                                    Favorite_Count int,
                                                    Definition varchar(10),
                                                    Caption_Status varchar(50))'''

    cursor.execute(create_query)
    mydb.commit()

    vi_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for vi_data in collection1.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    df2=pd.DataFrame(vi_list)

    for index,row in df2.iterrows():
        insert_query='''insert into videos(Channel_Name,
                                           Channel_Id,
                                           Video_Id,
                                           Title,
                                           Tags,
                                           Thumbnail,
                                           Description,
                                           Published_Date,
                                           Duration,
                                           Views,
                                           Likes,
                                           Comments,
                                           Favorite_Count,
                                           Definition,
                                           Caption_Status)
                                            
                                            values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
        values=(row['Channel_Name'],
                row['Channel_Id'],
                row['Video_Id'],
                row['Title'],
                row['Tags'],
                row['Thumbnail'],
                row['Description'],
                row['Published_Date'],
                row['Duration'],
                row['Views'],
                row['Likes'],
                row['Comments'],
                row['Favorite_Count'],
                row['Definition'],
                row['Caption_Status'])
        
        cursor.execute(insert_query,values)
        mydb.commit()


#Table creation for Comments
def comments_table():
    mydb=psycopg2.connect(host="localhost",
                                user="postgres",
                                password="rajkumar",
                                database="youtube_data",
                                port="5432")
    cursor=mydb.cursor()

    drop_query='''drop table if exists comments'''
    cursor.execute(drop_query)
    mydb.commit()

    create_query='''create table if not exists comments(Comment_Id varchar(100) primary key,
                                                    Video_Id varchar(100),
                                                    Comment_Text text,
                                                    Comment_Author varchar(100),
                                                    Comment_Published timestamp)'''

    cursor.execute(create_query)
    mydb.commit()

    cm_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for cm_data in collection1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(cm_data["comment_information"])):
            cm_list.append(cm_data["comment_information"][i])
    df3=pd.DataFrame(cm_list)

    for index,row in df3.iterrows():
        insert_query='''insert into comments(Comment_Id,
                                              Video_Id,
                                              Comment_Text,
                                              Comment_Author,
                                              Comment_Published)
                                            
                                              values(%s,%s,%s,%s,%s)'''
        values=(row['Comment_Id'],
                row['Video_Id'],
                row['Comment_Text'],
                row['Comment_Author'],
                row['Comment_Published'])
        
        cursor.execute(insert_query,values)
        mydb.commit()


#Table Creation of all tables
def tables():
    channels_table()
    playlists_table()
    videos_table()
    comments_table()

    return "Tables Created Successfully"


#Channels Dataframe
def show_channels_table():
    ch_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for ch_data in collection1.find({},{"_id":0,"channel_information":1}):
        ch_list.append(ch_data["channel_information"])
    df=st.dataframe(ch_list)

    return df


#Playlists Dataframe
def show_playlists_table():
    pl_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for pl_data in collection1.find({},{"_id":0,"playlist_information":1}):
        for i in range(len(pl_data["playlist_information"])):
            pl_list.append(pl_data["playlist_information"][i])
    df1=st.dataframe(pl_list)

    return df1


#Videos Dataframe
def show_videos_table():
    vi_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for vi_data in collection1.find({},{"_id":0,"video_information":1}):
        for i in range(len(vi_data["video_information"])):
            vi_list.append(vi_data["video_information"][i])
    df2=st.dataframe(vi_list)

    return df2


#Comments Dataframe
def show_comments_table():
    cm_list=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for cm_data in collection1.find({},{"_id":0,"comment_information":1}):
        for i in range(len(cm_data["comment_information"])):
            cm_list.append(cm_data["comment_information"][i])
    df3=st.dataframe(cm_list)

    return df3


#Streamlit part
with st.sidebar:
    st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
    st.header("Skill Take Away")
    st.caption("Python Scripting")
    st.caption("Data Collection")
    st.caption("Mongo DB")
    st.caption("API Integration")
    st.caption("Data Management using MongoDB and SQL")

st.title(":red[YOUTUBE DATA HARVESTING AND WAREHOUSING]")
channel_id=st.text_input("Enter the Channel id")

if st.button("Collect and Store Data"):
    ch_ids=[]
    db=client["Youtube_data"]
    collection1=db["Channel_details"]
    for ch_data in collection1.find({},{"_id":0,"channel_information":1}):
        ch_ids.append(ch_data["channel_information"])
                    
                     #ch_data["channel_information"]["Channel_Id"]
                     #ch_ids
    if len(ch_ids) == 0:
        insert=channel_details(channel_id)
        st.success(insert)
    elif channel_id in ch_data["channel_information"]["Channel_Id"]:
        st.error("Channel Details of the given channel id already exists")
    else:
        insert=channel_details(channel_id)
        st.success(insert)

if st.button("Migrate to SQL"):
    Table=tables()
    st.success(Table)

show_table=st.radio("SELECT THE TABLE FOR VIEW",("CHANNELS","PLAYLISTS","VIDEOS","COMMENTS"))

if show_table=="CHANNELS":
    show_channels_table()

elif show_table=="PLAYLISTS":
    show_playlists_table()

elif show_table=="VIDEOS":
    show_videos_table()

elif show_table=="COMMENTS":
    show_comments_table()


#SQL Connection
mydb=psycopg2.connect(host="localhost",
                                user="postgres",
                                password="rajkumar",
                                database="youtube_data",
                                port="5432")
cursor=mydb.cursor()

#Questions
question=st.selectbox("Select Your Question",("1. What are the names of all the videos and their corresponding channels?",
                                              "2. Which channels have the most number of videos, and how many videos do they have?",
                                              "3. What are the top 10 most viewed videos and their respective channels?",
                                              "4. How many comments were made on each video, and what are their corresponding video names?",
                                              "5. Which videos have the highest number of likes, and what are their corresponding channel names?",
                                              "6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?",
                                              "7. What is the total number of views for each channel, and what are their corresponding channel names?",
                                              "8. What are the names of all the channels that have published videos in the year 2022?",
                                              "9. What is the average duration of all videos in each channel, and what are their corresponding channel names?",
                                              "10. Which videos have the highest number of comments, and what are their corresponding channel names?"))

#Queries for Questions
if question=="1. What are the names of all the videos and their corresponding channels?":
    query1='''select channel_name as channelname,title as videos from videos'''
    cursor.execute(query1)
    mydb.commit()
    t1=cursor.fetchall()
    df1=pd.DataFrame(t1,columns=["Channel Name","Video Title"])
    df1.index = np.arange(1, len(df1) + 1)
    st.write(df1)

elif question=="2. Which channels have the most number of videos, and how many videos do they have?":
    query2='''select channel_name as channelname,total_videos as no_videos from channels
                order by total_videos desc'''
    cursor.execute(query2)
    mydb.commit()
    t2=cursor.fetchall()
    df2=pd.DataFrame(t2,columns=["Channel Name","Videos Count"])
    df2.index = np.arange(1, len(df2) + 1)
    st.write(df2)
    bar_chart=alt.Chart(df2).mark_bar().encode(
        x='Channel Name',
        y='Videos Count'
    )
    st.altair_chart(bar_chart,use_container_width=True)

elif question=="3. What are the top 10 most viewed videos and their respective channels?":
    query3='''select channel_name as channelname,title as videotitle,views as views from videos
                where views is not null order by views desc limit 10'''
    cursor.execute(query3)
    mydb.commit()
    t3=cursor.fetchall()
    df3=pd.DataFrame(t3,columns=["Channel Name","Video Title","Views Count"])
    df3.index = np.arange(1, len(df3) + 1)
    st.write(df3)
    bar_chart=alt.Chart(df3).mark_bar().encode(
        x='Video Title',
        y='Views Count',
        color='Channel Name'
    )
    st.altair_chart(bar_chart,use_container_width=True)

elif question=="4. How many comments were made on each video, and what are their corresponding video names?":
    query4='''select channel_name as channelname,title as videotitle,comments as no_comments from videos where comments is not null order by comments desc'''
    cursor.execute(query4)
    mydb.commit()
    t4=cursor.fetchall()
    df4=pd.DataFrame(t4,columns=["Channel Name","Video Title","Comments Count"])
    df4.index = np.arange(1, len(df4) + 1)
    st.write(df4)

elif question=="5. Which videos have the highest number of likes, and what are their corresponding channel names?":
    query5='''select channel_name as channelname,title as videotitle,likes as likecount from videos
                where likes is not null order by likes desc'''
    cursor.execute(query5)
    mydb.commit()
    t5=cursor.fetchall()
    df5=pd.DataFrame(t5,columns=["Channel Name","Video Title","Likes Count"])
    df5.index = np.arange(1, len(df5) + 1)
    st.write(df5)
    bar_chart=alt.Chart(df5).mark_bar().encode(
        x='Video Title',
        y='Likes Count',
        color='Channel Name'
    )
    st.altair_chart(bar_chart,use_container_width=True)

elif question=="6. What is the total number of likes and dislikes for each video, and what are their corresponding video names?":
    query6='''select title as videotitle,likes as likecount from videos where likes is not null'''
    cursor.execute(query6)
    mydb.commit()
    t6=cursor.fetchall()
    df6=pd.DataFrame(t6,columns=["Video Title","Likes Count"])
    df6.index = np.arange(1, len(df6) + 1)
    st.write(df6)
    bar_chart=alt.Chart(df6).mark_bar().encode(
        x='Video Title',
        y='Likes Count'
    )
    st.altair_chart(bar_chart,use_container_width=True)

elif question=="7. What is the total number of views for each channel, and what are their corresponding channel names?":
    query7='''select channel_name as channelname,views as totalviews from channels'''
    cursor.execute(query7)
    mydb.commit()
    t7=cursor.fetchall()
    df7=pd.DataFrame(t7,columns=["Channel Name","Views Count"])
    df7.index = np.arange(1, len(df7) + 1)
    st.write(df7)
    bar_chart=alt.Chart(df7).mark_bar().encode(
        x='Channel Name',
        y='Views Count'
    )
    st.altair_chart(bar_chart,use_container_width=True)

elif question=="8. What are the names of all the channels that have published videos in the year 2022?":
    query8='''select channel_name as channelname,title as video_title,published_date as videorelease from videos
                where extract(year from published_date)=2022'''
    cursor.execute(query8)
    mydb.commit()
    t8=cursor.fetchall()
    df8=pd.DataFrame(t8,columns=["Channel Name","Video Title","Published Date"])
    df8.index = np.arange(1, len(df8) + 1)
    st.write(df8)

elif question=="9. What is the average duration of all videos in each channel, and what are their corresponding channel names?":
    query9='''select channel_name as channelname,AVG(duration) as averageduration from videos group by channel_name'''
    cursor.execute(query9)
    mydb.commit()
    t9=cursor.fetchall()
    df9=pd.DataFrame(t9,columns=["Channel Name","Average Duration"])

    Avg_time=[]
    for index,row in df9.iterrows():
        channel_title=row["Channel Name"]
        average_duration=row["Average Duration"]
        average_duration_str=str(average_duration)
        Avg_time.append(dict(Channel_Title=channel_title,Average_Duration=average_duration_str))
    df11=pd.DataFrame(Avg_time)
    df11.index = np.arange(1, len(df11) + 1)
    st.write(df11)
    bar_chart=alt.Chart(df11).mark_bar().encode(
        x='Channel_Title',
        y='Average_Duration'
    )
    st.altair_chart(bar_chart,use_container_width=True)

elif question=="10. Which videos have the highest number of comments, and what are their corresponding channel names?":
    query10='''select title as videotitle,channel_name as channelname,comments as comments from videos
                where comments is not null order by comments desc'''
    cursor.execute(query10)
    mydb.commit()
    t10=cursor.fetchall()
    df10=pd.DataFrame(t10,columns=["Video Title","Channel Name","Comments Count"])
    df10.index = np.arange(1, len(df10) + 1)
    st.write(df10)
    bar_chart=alt.Chart(df10).mark_bar().encode(
        x='Video Title',
        y='Comments Count',
        color='Channel Name'
    )
    st.altair_chart(bar_chart,use_container_width=True)
