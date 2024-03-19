import os
import shutil
import random
import json
from PIL import Image, ExifTags
from safety_checker import SafetyChecker
from typing import List
from cog import BasePredictor, Input, Path
from helpers.comfyui import ComfyUI

OUTPUT_DIR = "/tmp/outputs"
INPUT_DIR = "/tmp/inputs"
COMFYUI_TEMP_OUTPUT_DIR = "ComfyUI/temp"

with open("become-image-api.json", "r") as file:
    workflow_json = file.read()


class Predictor(BasePredictor):
    def setup(self):
        self.safetyChecker = SafetyChecker()
        self.comfyUI = ComfyUI("127.0.0.1:8188")
        self.comfyUI.start_server(OUTPUT_DIR, INPUT_DIR)
        self.comfyUI.load_workflow(workflow_json, check_inputs=False)

    def cleanup(self):
        self.comfyUI.clear_queue()
        for directory in [OUTPUT_DIR, INPUT_DIR, COMFYUI_TEMP_OUTPUT_DIR]:
            if os.path.exists(directory):
                shutil.rmtree(directory)
            os.makedirs(directory)

    def handle_input_file(self, input_file: Path, filename: str):
        file_extension = os.path.splitext(input_file)[1].lower()
        if file_extension in [".jpg", ".jpeg"]:
            final_filename = f"{filename}.png"
            image = Image.open(input_file)

            try:
                for orientation in ExifTags.TAGS.keys():
                    if ExifTags.TAGS[orientation] == "Orientation":
                        break
                exif = dict(image._getexif().items())

                if exif[orientation] == 3:
                    image = image.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    image = image.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    image = image.rotate(90, expand=True)
            except (KeyError, AttributeError):
                # EXIF data does not have orientation
                # Do not rotate
                pass

            image.save(os.path.join(INPUT_DIR, final_filename))
        elif file_extension in [".png", ".webp"]:
            final_filename = filename + file_extension
            shutil.copy(input_file, os.path.join(INPUT_DIR, final_filename))
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

        return final_filename

    def log_and_collect_files(self, directory, prefix=""):
        files = []
        for f in os.listdir(directory):
            if f == "__MACOSX":
                continue
            path = os.path.join(directory, f)
            if os.path.isfile(path):
                print(f"{prefix}{f}")
                files.append(Path(path))
            elif os.path.isdir(path):
                print(f"{prefix}{f}/")
                files.extend(self.log_and_collect_files(path, prefix=f"{prefix}{f}/"))
        return files

    def update_workflow(self, workflow, **kwargs):
        prompt = kwargs["prompt"]
        negative_prompt = kwargs["negative_prompt"]

        load_image_person = workflow["22"]["inputs"]
        load_image_person["image"] = kwargs["filename"]

        load_image_to_become = workflow["83"]["inputs"]
        load_image_to_become["image"] = kwargs["image_to_become_filename"]

        loader = workflow["2"]["inputs"]
        loader["positive"] = f"{prompt}, sharp, high quality"

        if negative_prompt:
            loader["negative"] = (
                f"nsfw, nude, {negative_prompt}, soft, blurry, ugly, broken, watermark"
            )
        else:
            loader["negative"] = "nsfw, nude, soft, blurry, ugly, broken, watermark"

        controlnet = workflow["79"]["inputs"]
        controlnet["strength"] = kwargs["control_depth_strength"]

        instant_id = workflow["41"]["inputs"]
        instant_id["weight"] = kwargs["instant_id_strength"]

        ip_adapter = workflow["81"]["inputs"]
        ip_adapter["weight"] = kwargs["image_to_become_strength"]
        ip_adapter["noise"] = kwargs["image_to_become_noise"]

        sampler = workflow["75"]["inputs"]
        sampler["denoise"] = kwargs["denoising_strength"]
        sampler["seed"] = kwargs["seed"]
        sampler["cfg"] = kwargs["prompt_strength"]

        batcher = workflow["85"]["inputs"]
        batcher["multiply_by"] = kwargs["number_of_images"]

    def predict(
        self,
        image: Path = Input(
            description="An image of a person to be converted",
            default=None,
        ),
        image_to_become: Path = Input(
            description="Any image to convert the person to",
            default=None,
        ),
        prompt: str = Input(default="a person"),
        negative_prompt: str = Input(
            default="",
            description="Things you do not want in the image",
        ),
        number_of_images: int = Input(
            default=2,
            ge=1,
            le=10,
            description="Number of images to generate",
        ),
        denoising_strength: float = Input(
            default=1,
            ge=0,
            le=1,
            description="How much of the original image of the person to keep. 1 is the complete destruction of the original image, 0 is the original image",
        ),
        prompt_strength: float = Input(
            default=2.0,
            ge=0,
            le=3,
            description="Strength of the prompt. This is the CFG scale, higher numbers lead to stronger prompt, lower numbers will keep more of a likeness to the original.",
        ),
        control_depth_strength: float = Input(
            default=0.8,
            ge=0,
            le=1,
            description="Strength of depth controlnet. The bigger this is, the more controlnet affects the output.",
        ),
        instant_id_strength: float = Input(
            default=1, description="How strong the InstantID will be.", ge=0, le=1
        ),
        image_to_become_strength: float = Input(
            default=0.75, description="How strong the style will be applied", ge=0, le=1
        ),
        image_to_become_noise: float = Input(
            default=0.3,
            description="How much noise to add to the style image before processing. An alternative way of controlling stength.",
            ge=0,
            le=1,
        ),
        seed: int = Input(
            default=None, description="Fix the random seed for reproducibility"
        ),
        disable_safety_checker: bool = Input(
            description="Disable safety checker for generated images", default=False
        ),
    ) -> List[Path]:
        """Run a single prediction on the model"""
        self.cleanup()

        if image is None or image_to_become is None:
            missing_images = []
            if image is None:
                missing_images.append("image")
            if image_to_become is None:
                missing_images.append("image_to_become")
            raise ValueError(f"No {' and '.join(missing_images)} provided")

        filename = self.handle_input_file(image, "image_of_face")
        image_to_become_filename = self.handle_input_file(
            image_to_become, "image_to_become"
        )

        input_files = [image, image_to_become]
        if not disable_safety_checker:
            has_nsfw_content_input = self.safetyChecker.run(input_files)
            if any(has_nsfw_content_input):
                raise ValueError("NSFW content detected in input images")

        if seed is None:
            seed = random.randint(0, 2**32 - 1)
            print(f"Random seed set to: {seed}")

        workflow = json.loads(workflow_json)
        self.update_workflow(
            workflow,
            filename=filename,
            image_to_become_filename=image_to_become_filename,
            prompt=prompt,
            negative_prompt=negative_prompt,
            number_of_images=number_of_images,
            prompt_strength=prompt_strength,
            control_depth_strength=control_depth_strength,
            instant_id_strength=instant_id_strength,
            image_to_become_strength=image_to_become_strength,
            image_to_become_noise=image_to_become_noise,
            denoising_strength=denoising_strength,
            seed=seed,
        )

        wf = self.comfyUI.load_workflow(workflow, check_weights=False)
        self.comfyUI.connect()
        self.comfyUI.run_workflow(wf)

        files = []
        output_directories = [OUTPUT_DIR]

        for directory in output_directories:
            print(f"Contents of {directory}:")
            files.extend(self.log_and_collect_files(directory))

        if not disable_safety_checker:
            has_nsfw_content = self.safetyChecker.run(files)
            if any(has_nsfw_content):
                print("Removing NSFW images")
                files = [f for i, f in enumerate(files) if not has_nsfw_content[i]]

        return files
