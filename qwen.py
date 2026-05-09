from transformers import AutoTokenizer, AutoModelForCausalLM
import os
import torch

class Qwen:
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

        self.model.eval()
        self._template = """Classify the Korean command into exactly one label.
Allowed labels: LIGHT_ON, LIGHT_OFF, OTHER

Meaning:
- LIGHT_ON: turn on the light
- LIGHT_OFF: turn off the light
- OTHER: not a light on/off command

Examples:
Korean: 불 켜 줘
Label: LIGHT_ON
Korean: 불 켜
Label: LIGHT_ON
Korean: 불 좀 켜줄래
Label: LIGHT_ON
Korean: 전등 켜 줘
Label: LIGHT_ON
Korean: 불 꺼 줘
Label: LIGHT_OFF
Korean: 불 꺼
Label: LIGHT_OFF
Korean: 전등 꺼 줘
Label: LIGHT_OFF
Korean: 안녕
Label: OTHER
Korean: 날씨 알려줘
Label: OTHER

Korean: {message}
Label:
        """
        self._label_actions = {
            "LIGHT_ON": 1,
            "LIGHT_OFF": -1,
            "OTHER": 0,
        }
        base_prompt = self._template.format(message="N/A")
        self._base_scores = {
            label: self._score_label(base_prompt, label)
            for label in self._label_actions
        }

    def _score_label(self, prompt, label):
        prompt_ids = self.tokenizer(prompt, return_tensors="pt").input_ids
        label_ids = self.tokenizer(" " + label, return_tensors="pt", add_special_tokens=False).input_ids
        input_ids = torch.cat([prompt_ids, label_ids], dim=1).to(self.model.device)

        with torch.no_grad():
            logits = self.model(input_ids).logits

        log_probs = torch.log_softmax(logits[:, :-1, :], dim=-1)
        target_ids = input_ids[:, 1:]
        label_start = prompt_ids.shape[1] - 1
        label_log_probs = log_probs[:, label_start:, :].gather(
            2,
            target_ids[:, label_start:].unsqueeze(-1),
        ).squeeze(-1)

        return label_log_probs.mean().item()

    def _classify(self, message):
        prompt = self._template.format(message=message)
        raw_scores = {
            label: self._score_label(prompt, label)
            for label in self._label_actions
        }
        scores = {
            label: raw_scores[label] - self._base_scores[label]
            for label in self._label_actions
        }

        label = max(scores, key=scores.get)
        if label != "OTHER" and scores[label] - scores["OTHER"] < 0.5:
            label = "OTHER"
        return label, scores

    def __call__(self, message = "불 켜 봐"):
        label, scores = self._classify(message)
        result = {"action": self._label_actions[label]}
        print(result)
        return result



def main():
    qwen = Qwen()
    qwen()

if __name__ == "__main__":
    main()
