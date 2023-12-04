import sys
sys.path.append('../pkgs/')
import streamlit as st
import os
import pytube as pt
import pandas as pd

def print_playlist_detail(plst, if_streamlit = False):
    if not if_streamlit:
        print("URL: ", plst.playlist_url)
        print("Playlist Title: ",plst.title)
        print("Playlist Description: ",plst.description)
        print(f"Number of videos in {plst.title} playlist: ", len(plst.video_urls))
        print("Channel: ",plst.owner)
    else:
        header = ['URL','Playlist Title','Playlist Description',
                  f"Number of videos in {plst.title} playlist: ",'Channel']
        
        values = [[str(plst.playlist_url),str(plst.title),str(plst.description),
                  str(plst.video_urls),str(plst.owner)]]

        return pd.DataFrame(values,columns = header)

    return

def download_videos(plst, num,data_dir, file_ = None):
    folder_path = os.path.join(data_dir,'Videos')
    if(not os.path.isdir(folder_path)):
        os.mkdir(folder_path)

    if num==-1:
        num = len(list(plst))
    
    if file_:
        file_list = [file_]
    else:
        file_list = list(plst)[:num]

    for video in file_list:
        video   = pt.YouTube(video, use_oauth=True, allow_oauth_cache=True)
        print("Downloading Video: ",video.title)
        video.streams.first().download(folder_path)
        print('---------------------')
    return

def download_captions(plst, num,data_dir, file_ = None):
    folder_path = os.path.join(data_dir,'Captions')
    if(not os.path.isdir(folder_path)):
        os.mkdir(folder_path)
    
    if num==-1:
        num = len(list(plst))

    if file_:
        file_list = [file_]
    else:
        file_list = list(plst)[:num]

    for video in file_list:
        video   = pt.YouTube(video, use_oauth=True, allow_oauth_cache=True)
        print("Downloading Captions for: ",video.title)
        init = video.streams.first()
        try:
            caption = video.captions['a.en']
            caption.download(title=video.title, output_path= folder_path)
        except KeyError:
            try:
                caption = video.captions['en']
                caption.download(title=video.title, output_path= folder_path)
            except KeyError:
                print("English Caption does not exist!")  
        print('---------------------')
    return


def save_text_file(folder_path, file, text):
    text_file = open(os.path.join(folder_path,f"{file}.txt"), "w")
    text_file.write(text.strip())
    text_file.close()

def save_srt_file(folder_path, file, text):
    srt_file = open(os.path.join(folder_path,f"{file}.srt"), "w")

    for idx_val in text:
        ins_srt = str(idx_val['id']+1)+'\n'
        ins_srt += f"{round(idx_val['start'],2)} --> {round(idx_val['end'],2)}\n"
        ins_srt += idx_val['text'].strip() + "\n"
        ins_srt+='\n'

        srt_file.write(ins_srt)

    srt_file.close()
                
    

def formatting_transcripts(file, val, data_dir,return_srt = False,  save_text = True, save_srt = True):
    '''
    Parameters: 
    file: name of the video
    val: text content of the video generated via whisper
    data_dir: path of the data directory
    return_srt: True if the output of the function be time-stamped text; False for plain text
    save_txt: save the plain text transcription; creates a .txt file in the data_dir/Transcript folder
    save_srt: save the time-stamped text transcription; creates a .srt file in the data_dir/Transcript folder
    '''

    folder_path = os.path.join(data_dir,'Transcript')
    if(not os.path.isdir(folder_path)):
        os.mkdir(folder_path)

    if(save_text):
        save_text_file(folder_path,file,val['text'])
    if(save_srt):
        save_srt_file(folder_path,file,val['segments'])        
    
    if(return_srt):

        return [{k:v for k,v in dic.items() if k in ['id','start','end','text']} for dic in val['segments']]
    
    return val['text'].strip()


def read_srt(srt_filepath):
    '''Reads a srt file and returns a dictionary of dictionaries.
    idx is the key, value is a dictionary - containing timestamped sentences'''
    srt_dic = {}

    with open(srt_filepath,'r') as file:
        lines = file.readlines()
        file.close()
    
    block_dic = {}

    for idx,line in enumerate(lines):
        if(line == '\n'):
            srt_dic[dic_key] = block_dic
            block_dic = {}
        if(idx%4==0):
            dic_key = line.strip('\n')
        elif(idx%4==1):
            times = line.strip('\n ').split(' ')
            block_dic['start_time'],block_dic['end_time'] = times[0],times[-1]
        elif(idx%4==2):
            statement = line.strip('\n')
            block_dic['statement'] = statement
        else:
            continue
    
    return srt_dic