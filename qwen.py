from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, GenerationConfig, BitsAndBytesConfig
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import SimpleJsonOutputParser, JsonOutputParser
from langchain_huggingface import HuggingFacePipeline
from pydantic import BaseModel, Field
import time
import os
import accelerate
import torch

class Qwen:


    class _JsonParser(BaseModel):
        action: int = Field(description="어떤 동작을 할지, 0: 행동 안함, 1,-1: ")

    def __init__(self, model_name = "Qwen3-0.6B"):
        self.model_name = model_name
        self._message = ""
        target_folder = "../models/models--Qwen--" + self.model_name
        model_path = target_folder+"/snapshots/"

        # check if the model exists 

        if os.path.exists(target_folder) and os.path.isdir(target_folder):
            with open("file_path.data", 'r') as f:
                model_folder = f.read().strip()
                #model_folder = "c1899de289a04d12100db370d81485cdf75e47ca"
            self.model = AutoModelForCausalLM.from_pretrained(model_path+model_folder, local_files_only = True)
            self.tokenizer = AutoTokenizer.from_pretrained(model_path+model_folder, local_files_only = True)
        else:
            self.tokenizer = AutoTokenizer.from_pretrained("Qwen/" + self.model_name, cache_dir = "../models")
            self.model = AutoModelForCausalLM.from_pretrained("Qwen/" + self.model_name, cache_dir = "../models")
            
        with open("file_path.data", 'w') as f:
                f.write(os.listdir(model_path)[0])

        self._pipe = pipeline(
            "text-generation",
            model=self.model,
            tokenizer=self.tokenizer,
            max_new_tokens=128,           # 길이를 줄여서 헛소리 방지
            return_full_text=False,
            repetition_penalty=1.5,      # 반복 방지
            do_sample=False,
        )
        pipline_kwargs = {
            "return_full_text" : False,
            #"stop": ["}"]
        }

        self._llm = HuggingFacePipeline(pipeline=self._pipe, pipeline_kwargs=pipline_kwargs)

        parser = SimpleJsonOutputParser(pydantic_object=self._JsonParser)

        template = """Without any explanation answer with ONLY JSON
        turn on the light -> {{"action": 1}}
        turn off the light -> {{"action": -1}}
        else -> {{"action": 0}}

        Input will be Korean, you need to understand the meaning and only answer in JSON
        User: {message}
        Result : {{"action": (-1 or 0 or 1)}}
        """

        prompt = PromptTemplate(
            template=template,
            input_variables=["message"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )
        self._chain = prompt | self._llm | parser

    def __call__(self, message = "불 켜 봐"):
        result = self._chain.invoke({"message":message})
        print(result)



def main():
    qwen = Qwen()
    qwen()

if __name__ == "__main__":
    main()