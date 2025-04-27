from transformers import AutoModelForCausalLM, AutoProcessor
import torch
from PIL import Image

def load_model():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    model = AutoModelForCausalLM.from_pretrained("microsoft/Florence-2-large", torch_dtype=torch_dtype,  trust_remote_code=True).to(device).eval()
    processor = AutoProcessor.from_pretrained("microsoft/Florence-2-large", trust_remote_code=True)
    return device, model, processor

# Function to run the model on an example
def run_example(task_prompt, text_input, image, processor, model, device):
    prompt = task_prompt
    torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32
    
    inputs = processor(text=prompt, images=image, return_tensors="pt").to(device, torch_dtype)
    generated_ids = model.generate(
        input_ids=inputs["input_ids"],
        pixel_values=inputs["pixel_values"],
        max_new_tokens=1024,
        do_sample=False,
        num_beams=3
    )
    generated_text = processor.batch_decode(generated_ids, skip_special_tokens=False)[0]
    parsed_answer = processor.post_process_generation(generated_text, task=task_prompt, image_size=(image.width, image.height))
    return parsed_answer

def main(img_path, device, model, processor):
    image = Image.open(img_path)
    answer = run_example("<MORE_DETAILED_CAPTION>", 
                         "Describe only the main furniture object in the image using a short, clear sentence. Focus on key features such as material, shape, color, and distinct design elements. Avoid mentioning the background, scene, or accessories unless they are part of the object.",
                        image,
                        processor,
                        model,
                        device
                        )
    final_answer = answer['<MORE_DETAILED_CAPTION>']
    return final_answer
