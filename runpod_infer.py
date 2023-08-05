import os
import predict

import runpod
from runpod.serverless.utils import rp_download, rp_upload, rp_cleanup
from runpod.serverless.utils.rp_validator import validate


MODEL = predict.Predictor()
MODEL.setup()


INPUT_SCHEMA = {
    'prompt': {
        'type': str,
        'required': True
    },
    'negative_prompt': {
        'type': str,
        'required': False,
        'default': None
    },
    'image' : {
        'type': str,
        'required': False
    },
    'mask': {
        'type': str,
        'required': False
    },
    'width': {
        'type': int,
        'required': False,
        'default': 1024,
        'constraints': lambda width: width in [128, 256, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024]
    },
    'height': {
        'type': int,
        'required': False,
        'default': 1024,
        'constraints': lambda height: height in [128, 256, 384, 448, 512, 576, 640, 704, 768, 832, 896, 960, 1024]
    },
    'prompt_strength': {
        'type': float,
        'required': False,
        'default': 0.8,
        'constraints': lambda prompt_strength: 0 <= prompt_strength <= 1
    },
    'num_outputs': {
        'type': int,
        'required': False,
        'default': 1,
        'constraints': lambda num_outputs: 10 > num_outputs > 0
    },
    'num_inference_steps': {
        'type': int,
        'required': False,
        'default': 50,
        'constraints': lambda num_inference_steps: 0 < num_inference_steps < 500
    },
    'guidance_scale': {
        'type': float,
        'required': False,
        'default': 7.5,
        'constraints': lambda guidance_scale: 0 < guidance_scale < 50
    },
    'scheduler': {
        'type': str,
        'required': False,
        'default': 'DPMSolverMultistep',
        'constraints': lambda scheduler: scheduler in ['DDIM', 'K_EULER', 'DPMSolverMultistep', 'K_EULER_ANCESTRAL', 'PNDM', 'KLMS']
    },
    'seed': {
        'type': int,
        'required': False,
        'default': None
    },
    'refine':{
        'type' : str,
        'required' : False,
        'constraints' : lambda refine : refine in ["no_refiner", "expert_ensemble_refiner", "base_image_refiner"],
    },
    'high_noise_frac': {
        'type': float,
        'required': False,
        'default': 0.8,
        'constraints': lambda high_noise_frac: 0 <= high_noise_frac <= 1
    },
    'refine_steps': {
        'type': int,
        'required': False
    }
}


def run(job):
    '''
    Run inference on the model.
    Returns output path, width the seed used to generate the image.
    '''
    job_input = job['input']

    # Input validation
    validated_input = validate(job_input, INPUT_SCHEMA)

    if 'errors' in validated_input:
        return {"error": validated_input['errors']}
    validated_input = validated_input['validated_input']

    # Download input objects
    job_input['image'], job_input['mask'] = rp_download.download_input_objects(
        [job_input.get('image', None), job_input.get('mask', None)]
    )  # pylint: disable=unbalanced-tuple-unpacking

    if validated_input['seed'] is None:
        validated_input['seed'] = int.from_bytes(os.urandom(2), "big")

    img_paths = MODEL.predict(
        prompt=validated_input["prompt"],
        negative_prompt=validated_input["negative_prompt"],
        width=validated_input['width'],
        height=validated_input['height'],
        prompt_strength=validated_input['prompt_strength'],
        num_outputs=validated_input['num_outputs'],
        num_inference_steps=validated_input['num_inference_steps'],
        guidance_scale=validated_input['guidance_scale'],
        scheduler=validated_input['scheduler'],
        seed=validated_input['seed'],
        high_noise_frac = validated_input['high_noise_frac'],
        refine = validated_input['refine'],
        refine_steps = validated_input['refine_steps'],
        image=job_input['image'],
        mask=job_input['mask']
    )

    job_output = []

    for index, img_path in enumerate(img_paths):
        image_url = rp_upload.upload_image(job['id'], img_path, index)

        job_output.append({
            "image": image_url,
            "seed": job_input['seed'] + index
        })

    # Remove downloaded input objects
    rp_cleanup.clean(['input_objects'])

    return job_output


runpod.serverless.start({"handler": run})