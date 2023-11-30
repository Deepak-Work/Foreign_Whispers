import os
import subprocess
from pydub import AudioSegment
from data_module import read_srt
from tqdm import tqdm
import sys
import contextlib

class DummyFile(object):
    def write(self, x): pass

@contextlib.contextmanager
def nostdout():
    save_stdout = sys.stdout
    sys.stdout = DummyFile()
    yield
    sys.stdout = save_stdout

def convert_video_to_audio(data_dir, ar=44100, ac=2, b_a="192k", ext = '.3gpp'):
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

    for file in os.listdir(os.path.join(data_dir,'Videos')):

        video_file_path = os.path.join(os.path.join(data_dir,'Videos'),file).replace(' ','\ ')
        audio_file_path = os.path.join(os.path.join(data_dir,'Audios'),file.split(ext)[0]).replace(' ','\ ')

        if(not os.path.isfile(os.path.normpath(audio_file_path+'.mp3'))):
            command = f"ffmpeg -i {video_file_path} -vn -ar {ar} -ac {ac} -b:a {b_a} {audio_file_path + '.mp3'}"
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
                        audio_sum = audio_sum + AudioSegment.silent(duration=float(start_time)*1000)
                    else:
                        subprocess.call(['tts', '--text', statement,'--model_name', 'tts_models/de/thorsten/vits',
                                        '--out_path', 'temp.wav'])
                
                        sub_audio = AudioSegment.from_wav('temp.wav')
                        silence_time = (float(sub['end_time']) - float(start_time))*1000 - len(sub_audio)

                        if(silence_time<0):
                            audio_sum = audio_sum + speed_change(sub_audio,speed = len(sub_audio)/((float(sub['end_time']) - float(start_time))*1000))
                        else:
                            audio_sum = audio_sum + sub_audio + AudioSegment.silent(duration=silence_time)
                        
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
        
    return