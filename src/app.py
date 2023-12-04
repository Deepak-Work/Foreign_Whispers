import streamlit as st
import pandas as pd
import numpy as np
import sys
sys.path.insert(1,'../Code')
sys.path.insert(2,'../pkgs/')
from data_module import *
from tts_module import *
from text_module import *
import pytube as pt
import whisper
import os
import time

if __name__ == "__main__":

    st.title('Translate video to any foreign language!')

    supported_languages = ['German']

    ## Util functions

    def srt_compare(og_srt, tr_srt):
        out_og_srt = read_srt(og_srt)
        out_tr_srt = read_srt(tr_srt)

        df_srt_comp = pd.DataFrame(out_og_srt).T.merge(pd.DataFrame(out_tr_srt).T, on = ['start_time','end_time'],suffixes=('_og' ,'_translated'))

        return df_srt_comp


    ## Flags for checks    
    if 'tts_flag' not in st.session_state:
        st.session_state.tts_flag = False

    if 'translated_flag' not in st.session_state:
        st.session_state.translated_flag = False

    if 'data_dir' not in st.session_state:
        st.session_state.data_dir = '../Data/'

    if 'file_loc' not in st.session_state:
        st.session_state.file_loc = ''

    if 'video_selected' not in st.session_state:
        st.session_state.video_selected = False

    if 'translated_srt' not in st.session_state:
        st.session_state.translated_srt = ''

    if 'iter_completed' not in st.session_state:
        st.session_state.iter_completed = False




    ## UI building
    lang_dict={'Arabic':'ar','Danish':'da','Filipino':'fil','Finnish':'fi','French':'fr',
            'German':'de','Greek':'el','Gujarati':'gu','Hebrew':'iw','Hindi':'hi','Hungarian':'hu','Italian':'it',
            'Japanese':'jap','Russian':'ru','Spanish':'es','Thai':'th','Urdu':'ur'} #List of supported language | Still in work, Only German Supported for now.

    select_lang = st.selectbox(
        'Select a target language',
        options = supported_languages, index = None)

    language = select_lang #Chosen language

    playlist_url = st.text_input(
            "Youtube Playlist URL 👇", placeholder = "Playlist URL")

    num_videos_download = st.number_input(
            "#Videos to download from the playlist", value = 0, format = '%d', help = 'Type -1 to translate all videos in the playlist')

    translate_sub, download_sub, translate_video = st.columns([1,1,1])

    ## Interaction Actions

    if(playlist_url):
        try:
            playlst = pt.Playlist(playlist_url)
            dict_videos = {"".join(x for x in pt.YouTube(_).title if x.isalnum() or x==' '): _ for _ in list(playlst)[:num_videos_download]}

            select_video = st.selectbox('Select a video',options = dict_videos.keys(), 
                                        index = None)
            if select_video:
                st.session_state.video_selected = True
            st.write("PLAYLIST DETAILS!")
            st.dataframe(print_playlist_detail(playlst,if_streamlit=True), hide_index = True)
        
        except:
            st.write("Unable to access the Playlist. Check if you entered the correct URL or if the video is public!!")

        

    with translate_sub:
        tr_sub = st.button("Translate Subtitles", type="primary", disabled = not (playlist_url and num_videos_download and st.session_state.video_selected))
        


    if(tr_sub and playlist_url):
        t = st.empty()
        t.markdown("**Translating subtitles!** \n This step takes few minutes. Meanwhle :rainbow[***MEDITATE...***]")

        #Downloading videos and captions
        download_videos(playlst,num_videos_download, st.session_state.data_dir, file_ = dict_videos[select_video])
        download_captions(playlst,num_videos_download, st.session_state.data_dir, file_ = dict_videos[select_video])

        t.markdown("**Extracting audio from video!** This should be quick. Meanwhle :rainbow[***MEDITATE...***]")
        # High-quality mono audio - To be run only once
        convert_video_to_audio(st.session_state.data_dir, file_ = select_video,ac=1)


        t.markdown("**Extracting subtitle from audio!** This step takes few minutes. Meanwhle :rainbow[***MEDITATE...***]")

        #Transcribing the audio
        model = whisper.load_model("base")
        data_dir_ = os.path.join(st.session_state.data_dir,'Audios')
        cc_gen = {} #Stores the transcription of every audio file in the data directory

        source_audio_file = select_video+'.mp3'
        
        print("Source Audio File:", source_audio_file)

        audio = os.path.join(data_dir_,source_audio_file)
        cc_gen = model.transcribe(audio)
        extracted_txt = formatting_transcripts(source_audio_file.replace('.mp3',''), cc_gen, st.session_state.data_dir,False, True, True)

        
        #Text translation
        t.markdown(f"**Starting text translation in {language}!** \n This step takes few minutes. Meanwhle :rainbow[***MEDITATE...***]")
        lang_obj = Languages(lang_dict)
        lang_obj.opus_model(language)    

        tokenizer, model_name = lang_obj.opus_model(language)
        model_text = AutoModelForSeq2SeqLM.from_pretrained(model_name,device_map='mps')

        if select_video:
            file_to_translate = select_video+'.srt'
        
        print(file_to_translate)

        #Saving translated srts of all audios
        t.markdown(f"**Translating: {file_to_translate}!** \n This step takes few minutes. Meanwhle :rainbow[***MEDITATE...***]")
        st.session_state.translated_srt = save_translate_srt_file(st.session_state.data_dir,file_to_translate,model_text, language,tokenizer,save = True)
        
        num_videos_download = None
        st.session_state.translated_flag = True
        # tr_sub = False

        if(os.path.isfile(os.path.join(os.path.join(st.session_state.data_dir,f'Transcript/translate_{language}'),st.session_state.translated_srt))):
            t.markdown(f"**Translation Complete** Press \"Download {language} Subtitle\" button to view the subtitles!")
        else:
            t.markdown(f"**Some error in translation, Check logs**")

    with download_sub:
        dw_sub = st.button(f"Download {language} Subtitles", type="primary", disabled = not (st.session_state.translated_flag))

    if(st.session_state.translated_flag and dw_sub):
        st.dataframe(srt_compare(os.path.join(os.path.join(st.session_state.data_dir,f'Transcript'),st.session_state.translated_srt),
            os.path.join(os.path.join(st.session_state.data_dir,f'Transcript/translate_{language}'),st.session_state.translated_srt)),
                    hide_index = True)


        t = st.empty()
        t.markdown("**Starting TTS!** \n This step takes 6-7 minutes. Meanwhle :rainbow[***MEDITATE...***]")

        srt_file = os.path.join(f'{st.session_state.data_dir}Transcript/translate_{language}',st.session_state.translated_srt)
        print("TTS for: ", srt_file)
        st.session_state.file_loc = generate_audio(st.session_state.data_dir,srt_file,language, blockwiseadd=5)
        
        translated_videopath = os.path.join(f'{st.session_state.data_dir}Videos/translate_{language}',st.session_state.translated_srt.replace('.srt','.mp4'))
        og_videopath = os.path.join(f'{st.session_state.data_dir}Videos',st.session_state.translated_srt.replace('.srt','.3gpp'))


        st.session_state.file_loc = gen_translated_video(og_videopath,translated_videopath,st.session_state.file_loc,srt_file,True,language)
        t.markdown("Download your translated video now. Ciao!")
        st.session_state.tts_flag = True
        

    with translate_video:
        if(st.session_state.file_loc):
            with open(st.session_state.file_loc, "rb") as file:
                tr_video = st.download_button("Download Translated Video", type="primary", data = file, 
                                            file_name = st.session_state.file_loc.split('/')[-1], mime = 'audio/wav')
                if(tr_video):
                    st.session_state.iter_completed = True
        else:
            tr_video = st.button("Download Translated Video", type="primary", disabled = True)

    if(st.session_state.iter_completed):
        st.session_state.video_selected = False
        st.session_state.translated_flag = False
        st.session_state.tts_flag = False
        select_video = None
        st.session_state.iter_completed = False
        dw_sub = False
