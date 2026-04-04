from transformers import AutoTokenizer, AutoModelForCausalLM
#from awq import AutoAWQForCausalLM
import time
import os


class Qwen:
    def __init__(self):
        self._message = ""
        target_folder = "../models/models--Qwen--Qwen3-0.6B"
        folder_path = "../models/models--Qwen--Qwen3-0.6B/snapshots/"
        # check if the model exists 
        if os.path.exists(target_folder) and os.path.isdir(target_folder):
            with open("file_path.data", 'r') as f:
                folder_name = f.read().strip()
            self.model = AutoModelForCausalLM.from_pretrained(folder_path+folder_name, local_files_only = True)
            self.tokenizer = AutoTokenizer.from_pretrained(folder_path+folder_name, local_files_only = True)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen3-0.6B", cache_dir = "../models")
            self.model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen3-0.6B", cache_dir = "../models")
            
        with open("file_path.data", 'w') as f:
                f.write(os.listdir("../models/models--Qwen--Qwen3-0.6B/snapshots/")[0])

    def __call__(self, message = "불을 끄기 위한 거를 json으로 대답해"):
        self._message = message
        messages = [
            {"role": "tool", "content": self._message},
        ]

        inputs = self.tokenizer.apply_chat_template(
            messages,
            add_generation_prompt=True,
            tokenize=True,
            return_dict=True,
            use_cache = True,
            return_tensors="pt",
        ).to(self.model.device)

        outputs = self.model.generate(**inputs, max_new_tokens=960)
        print(self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:]))

def main():
    qwen = Qwen()
    qwen()

if __name__ == "__main__":
    main()