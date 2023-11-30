import os

from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from urllib.error import HTTPError

class Languages():
    def __init__(self,lang_dictionary):
        self.lang_list = lang_dictionary.keys()
        self.lang_map = lang_dictionary
    
    def is_available(self,lang):
        if(lang not in self.lang_list):
            print("Language not available, please choose one of the languages in the following list: ", *list(self.lang_list))
            return 0
        else:
            print(self.lang_map[lang])
            return 1
    
    def opus_model(self, lang):
        if(self.is_available(lang)):
            model_name =  f"Helsinki-NLP/opus-mt-en-{self.lang_map[lang]}"
            try:
                model = AutoTokenizer.from_pretrained(model_name)
                return model, model_name
            except HTTPError:
                print("Model not available in Opus-MT")
                return None, model_name
            
def chunkwise_translate(model,sentences,tokenizer,num_sen_per_chunk = 10, device = 'mps'):
    res_sen = []

    for count in range(0,len(sentences),num_sen_per_chunk):
        target_sen = sentences[count:min(count+num_sen_per_chunk,len(sentences))]
        translated = model.generate(**tokenizer(target_sen, return_tensors="pt", padding=True).to(device))
            
        for t in translated:
            res_sen.append(' '.join([_ for _ in [tokenizer.decode(_) for _ in t] if _ not in ['<pad>','</s>','.']]))
        
    return res_sen


def save_translate_srt_file(data_dir, filename, model,language,tokenizer, save = False):
    folder_path = os.path.join(data_dir,'Transcript')
    translate_folder = os.path.join(folder_path,f'translate_{language}')
    
    if(not os.path.isdir(translate_folder)):
        os.mkdir(translate_folder)

    

    with open(os.path.join(folder_path,filename),'r') as file:
        lines = file.readlines()
        file.close()

    line = [_.strip('\n') for _ in lines[2::4]]
    translate_lines = chunkwise_translate(model,line,tokenizer)

    ins_srt = ''

    for idx,l in enumerate(lines):
        if((idx-2)%4==0):
            ins_srt+=translate_lines[idx//4]+'\n'
        else:
            ins_srt += l

    if(save):
        srt_file = open(os.path.join(translate_folder,filename), "w")
        srt_file.write(ins_srt)
        srt_file.close()
        print("Translated file saved at: ", os.path.join(translate_folder,filename))

    return ins_srt