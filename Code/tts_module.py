import os
import subprocess
from pydub import AudioSegment
from data_module import read_srt
from tqdm import tqdm
import sys
import contextlib
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip


def convert_video_to_audio(data_dir, file_ = None, ar=44100, ac=2, b_a="192k", ext = '.3gpp'):
    '''
    Creating an audio (.mp3) file for every given video file and saving it in the data_dir/Audios folder
    Parameters:
    data_dir: path of the data directory
    ar, ac, b_a: are ffmpeg parameters
    ext: extension of the video files
    '''


    folder_path = os.path.join(data_dir,'Audios')
    if(not os.path.isdir(folder_path)):
        os.mkdir(folder_path)

    folder_path_video = os.path.join(data_dir,'Videos')
    
    candidate_files = []

    if file_:
        candidate_files = [_ for _ in os.listdir(folder_path_video) if file_ in _]
    else:
        candidate_files = [_ for _ in os.listdir(folder_path_video) if ext in _]
    
    print(candidate_files)

    for f in candidate_files:

        video_file_path = os.path.join(os.path.join(data_dir,'Videos'),f).replace(' ','\ ')
        audio_file_path = os.path.join(os.path.join(data_dir,'Audios'),f.split(ext)[0]).replace(' ','\ ')

        if(not os.path.isfile(os.path.normpath(audio_file_path+'.mp3'))):
            command = f"ffmpeg -y -i {video_file_path} -vn -ar {ar} -ac {ac} -b:a {b_a} {audio_file_path + '.mp3'}"
            # print(command)
            try:
                subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
                print(f"Successfully converted {video_file_path} to {audio_file_path}")
            except subprocess.CalledProcessError as e:
                print(f"An error occurred while converting {video_file_path} to {audio_file_path}")
                print(f"Error message: {e.output.decode()}")
                break
        else:
            print("Audio File already exists!")


def speed_change(sound, speed=1.0):
    # Manually override the frame_rate. This tells the computer how many
    # samples to play per second
    sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
        "frame_rate": int(sound.frame_rate * speed)
    })

    return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

def generate_audio(data_dir,srt_filepath,language, blockwiseadd = 1):
    '''Generated audio for the given srt file.
    One block of srt is converted to speech at a time. 
    We add pause time if the time of translation is lower than the time of srt block
    Saves the output in a wav file

    data_dir: directory of containing the raw data
    srt_filepath: path of the translated srt
    language: name of the target translation language
    '''
    translate_audio_folder = os.path.join(os.path.join(data_dir,'Audios'),f'translate_{language}')
    # audio_folder = os.path.join(data_dir,'Audios')
    audio_name = srt_filepath.split('/')[-1].replace('.srt','')
    
    if(not os.path.isdir(translate_audio_folder)):
        os.mkdir(translate_audio_folder)
        print("Folder Created: ", translate_audio_folder)
    else:
        print("Folder already present!")
    
    if(not os.path.exists(os.path.join(translate_audio_folder,audio_name) + '.wav')):

    
        srt_out = read_srt(srt_filepath)
        audio_sum = AudioSegment.empty()
        statement = ''

        block_cntr= 0

        for idx,sub in tqdm(srt_out.items()):
            if(len(sub['statement'].strip())>0):

                statement += ' '+ sub['statement']
                if(block_cntr%blockwiseadd==0):
                    if(block_cntr==0):
                        start_time = sub['start_time']
                        audio_sum = AudioSegment.silent(duration=float(start_time)*1000)+audio_sum
                    else:
                        subprocess.call(['tts', '--text', statement,'--model_name', 'tts_models/de/thorsten/vits',
                                        '--out_path', 'temp.wav'])
                
                        sub_audio = AudioSegment.from_wav('temp.wav')
                        silence_time = (float(sub['end_time']) - float(start_time))*1000 - len(sub_audio)

                        if(silence_time<0):
                            audio_sum = audio_sum + speed_change(sub_audio,speed = len(sub_audio)/((float(sub['end_time']) - float(sub['start_time']))*1000))
                        else:
                            audio_sum = audio_sum + AudioSegment.silent(duration=silence_time) + sub_audio
                        
                        start_time = sub['end_time']

                        statement = ''
                        os.remove('temp.wav')

                block_cntr+=1
                

        if(statement.strip()):
            temp = subprocess.call(['tts', '--text', statement,'--model_name', 'tts_models/de/thorsten/vits',
                                        '--out_path', 'temp.wav'])
                
            sub_audio = AudioSegment.from_wav('temp.wav')
            silence_time = (float(sub['end_time']) - float(start_time))*1000 - len(sub_audio)

            if(silence_time<0):
                audio_sum = audio_sum + speed_change(sub_audio,speed = len(sub_audio)/((float(sub['end_time']) - float(start_time))*1000))
            else:
                audio_sum = audio_sum + sub_audio + AudioSegment.silent(duration=silence_time)

            os.remove('temp.wav')

        # orig_length = len(AudioSegment.from_mp3(f'{audio_folder}/{audio_name}.mp3'))
        # new_length = len(audio_sum)
        
        with open(os.path.join(translate_audio_folder,audio_name) + '.wav', 'wb') as out_f:
            audio_sum.export(out_f, format='wav',) 
            print('TTS complete')

    else:
        print('TTS already done!')
        
    
    return os.path.join(translate_audio_folder,audio_name) + '.wav'

def add_subtitle_video(subtitles, videosize,fontsize=10, font='Arial', color='yellow', debug = False):
    subtitle_clips = []

    for idx,subtitle in subtitles.items():
        start_time = float(subtitle['start_time'])
        end_time = float(subtitle['end_time']) 
        duration = end_time - start_time

        video_width, video_height = videosize
        
        text_clip = TextClip(subtitle['statement'], fontsize=fontsize, font=font, color=color, bg_color = 'black',
                             size=(video_width, None), method='caption').set_start(start_time).set_duration(duration)
        
        subtitle_x_position = 'center'
        subtitle_y_position = video_height* 4 / 5 

        text_position = (subtitle_x_position, subtitle_y_position)                    
        subtitle_clips.append(text_clip.set_position(text_position))

    return subtitle_clips


def gen_translated_video(og_video_filepath,tr_video_filepath,tr_audio_filepath, tr_srt_filepath = None, burn_subtitle = True, select_lang = 'German'):
    '''If burn subtitle is True, Adds subtitle over the video. 
       Replace the original audio with translated one for the video

       og_video_filepath: original video path
       tr_video_filepath: translated video path
       tr_audio_filepath: translated audio path
       tr_srt_filepath: translated srt path
       burn_subtitle: Whether to add the subtitle or not
    '''
    if burn_subtitle:
        video = VideoFileClip(og_video_filepath)
        subtitles = read_srt(tr_srt_filepath)

        begin,end= og_video_filepath.split(".3gpp")
        temp_video_file = begin+'_subtitled'+".mp4"       

        # Create subtitle clips
        subtitle_clips = add_subtitle_video(subtitles,video.size)

        # Add subtitles to the video
        final_video = CompositeVideoClip([video] + subtitle_clips)

        # Write output video file
        final_video.write_videofile(temp_video_file)
        og_video_filepath = temp_video_file

    og_video_filepath = og_video_filepath.replace(' ','\ ')
    tr_audio_filepath = tr_audio_filepath.replace(' ','\ ')
    tr_video_filepath = tr_video_filepath.replace(' ','\ ')

    
    command = f"ffmpeg -y -i {og_video_filepath} -i {tr_audio_filepath} -map 0:v -map 1:a -c:v copy {tr_video_filepath}"
    subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
    if(burn_subtitle):
        os.remove(temp_video_file)
    
    return tr_video_filepath.replace('\ ',' ')
