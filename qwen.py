from transformers import AutoTokenizer, AutoModelForCausalLM
import os
import torch


class Qwen:
    def __init__(self, model_name="Qwen3-0.6B"):
        self.model_name = model_name
        target_folder = "../models/models--Qwen--" + self.model_name
        model_path = target_folder + "/snapshots/"

        if os.path.exists(target_folder) and os.path.isdir(target_folder):
            with open("file_path.data", "r") as f:
                model_folder = f.read().strip()
            self.model = AutoModelForCausalLM.from_pretrained(
                model_path + model_folder,
                local_files_only=True,
            )
            self.tokenizer = AutoTokenizer.from_pretrained(
                model_path + model_folder,
                local_files_only=True,
            )
        else:
            self.tokenizer = AutoTokenizer.from_pretrained(
                "Qwen/" + self.model_name,
                cache_dir="../models",
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                "Qwen/" + self.model_name,
                cache_dir="../models",
            )

        with open("file_path.data", "w") as f:
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
Korean: 불 좀 켜줄래?
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
Korean: 음악 틀어줘
Label: OTHER

Korean: {message}
Label:"""
        self._label_actions = {
            "LIGHT_ON": 1,
            "LIGHT_OFF": -1,
            "OTHER": 0,
        }
        self._labels = tuple(self._label_actions.keys())
        self._last_label_scores = {}

    def _score_label(self, prompt, label):
        continuation = " " + label
        prompt_inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        continuation_ids = self.tokenizer(
            continuation,
            add_special_tokens=False,
            return_tensors="pt",
        ).input_ids.to(self.model.device)

        input_ids = torch.cat([prompt_inputs.input_ids, continuation_ids], dim=1)
        attention_mask = torch.ones_like(input_ids)
        prompt_length = prompt_inputs.input_ids.shape[1]

        with torch.no_grad():
            logits = self.model(input_ids=input_ids, attention_mask=attention_mask).logits

        log_probs = torch.log_softmax(logits, dim=-1)
        token_scores = []
        for offset, token_id in enumerate(continuation_ids[0]):
            logit_position = prompt_length + offset - 1
            token_scores.append(log_probs[0, logit_position, token_id])

        return torch.stack(token_scores).mean().item()

    def _classify(self, message):
        prompt = self._template.format(message=message)
        scores = {
            label: self._score_label(prompt, label)
            for label in self._labels
        }
        probabilities = torch.softmax(torch.tensor(list(scores.values())), dim=0)
        self._last_label_scores = {
            label: float(probability)
            for label, probability in zip(scores.keys(), probabilities)
        }
        return max(scores, key=scores.get)

    def __call__(self, message="불 꺼 줘"):
        label = self._classify(message)
        result = {"action": self._label_actions[label]}
        print(result)
        return result


def main():
    qwen = Qwen()
    qwen()


if __name__ == "__main__":
    main()
