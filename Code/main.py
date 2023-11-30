import sys
sys.path.append('../pkgs/')

import pytube as pt
import whisper
import argparse
from data_module import *
from tts_module import *
from text_module import *

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--playlist_url", type=str, default= 'https://www.youtube.com/playlist?list=PLI1yx5Z0Lrv77D_g1tvF9u3FVqnrNbCRL',
                    help="Playlist URL (Youtube)")
    
    parser.add_argument("--num_videos_download", type=int, default= 10,
                    help="Num of videos to download from the playlist, -1 for all")
    
    parser.add_argument("--caption", type=bool, default= True,
                    help="If Caption should also be downloaded")
    
    parser.add_argument("--data_dir", type=str, default= '../../../../ForeignWhisperscopy/Data/',
                    help="Data directory for I/O")
    
    parser.add_argument("--select_lang", type=str, default= 'German',
                    help="Target Language")
    
    parser.add_argument("--device", type=str, default= 'mps',
                    help="Device to run the translation and TTS module")
    
    args = parser.parse_args()
     
    playlist_url = args.playlist_url
    num_videos_download = args.num_videos_download
    caption = args.caption
    data_dir = args.data_dir

    if(not os.path.isdir(data_dir)):
        os.mkdir(data_dir)

    print("Starting data download!")
    playlst = pt.Playlist(playlist_url)
    print_playlist_detail(playlst)

    #Downloading videos and captions
    download_videos(playlst,num_videos_download, data_dir)
    download_captions(playlst,num_videos_download, data_dir)

    print("Extracting audio from video")
    # High-quality mono audio - To be run only once
    convert_video_to_audio(data_dir, ac=1)

    #initializing trancription model
    model = whisper.load_model("base")

    #Transcribing the audio
    data_dir_ = os.path.join(data_dir,'Audios')
    cc_gen = {} #Stores the transcription of every audio file in the data directory

    for file in os.listdir(data_dir_):
        if(file.endswith('.mp3')):
            audio = os.path.join(data_dir_,file)

            cc_gen[file.replace('.mp3','')] = model.transcribe(audio)
    
    extracted_txt_arr = []

    for name, data in cc_gen.items():
        extracted_txt_arr.append(formatting_transcripts(name, data,  data_dir,False, True, True))


    
    #Text translation
    lang_dict={'Arabic':'ar','Danish':'da','Filipino':'fil','Finnish':'fi','French':'fr',
           'German':'de','Greek':'el','Gujarati':'gu','Hebrew':'iw','Hindi':'hi','Hungarian':'hu','Italian':'it',
           'Japanese':'jap','Russian':'ru','Spanish':'es','Thai':'th','Urdu':'ur'} #List of supported language
    
    lang_obj = Languages(lang_dict)

    select_lang = args.select_lang #Chosen language
    print(f"Starting text translation in {select_lang}!")
    lang_obj.opus_model(select_lang)    

    tokenizer, model_name = lang_obj.opus_model(select_lang)
    model_text = AutoModelForSeq2SeqLM.from_pretrained(model_name,device_map='mps')

    file_to_translate = []
    for file in os.listdir(os.path.join(data_dir,'Transcript')):
        if(file.endswith('.srt')):
            file_to_translate.append(file)

    #Saving translated srts of all audios
    for file in file_to_translate:
        print("Translating: ",file)
        translated_srt = save_translate_srt_file(data_dir,file,model_text, select_lang,tokenizer,save = True)
    

    #TTS in Selected Language
    print("Starting TTS!")
    audio_srts = []
    for file in os.listdir(f'{data_dir}Transcript/translate_{select_lang}'):
        if(file.endswith('.srt')):
            audio_srts.append(file)

    for file in audio_srts:
        srt_file = os.path.join(f'{data_dir}Transcript/translate_{select_lang}',file)
        print("TTS for: ", srt_file)
        temp = generate_audio(data_dir,srt_file,select_lang, blockwiseadd=5)


    


