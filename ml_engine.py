"""
ML Engine for Ship Classification, Augmentation, and Training
Uses ViT (Vision Transformer) model from HuggingFace
"""

import os
import io
import json
import glob
import random
import threading
from datetime import datetime
from PIL import Image

# Model paths
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'models', 'ship_classifier')
AUGMENTED_DIR = os.path.join(os.path.dirname(__file__), 'augmented')
DOWNLOADS_DIR = os.path.join(os.path.dirname(__file__), 'downloads')

# Global state
_model = None
_processor = None
_model_loaded = False
_training_status = {'running': False, 'progress': 0, 'message': '', 'history': []}
_augment_status = {'running': False, 'progress': 0, 'total': 0, 'message': ''}

# Ship type labels from config
SHIP_LABELS = {
    0: "Bulkers",
    1: "Recreational",
    2: "Sailboat",
    3: "DDG",
    4: "Container Ship",
    5: "Tug",
    6: "Aircraft Carrier",
    7: "Cruise",
    8: "Submarine",
    9: "Car Carrier"
}


def load_model():
    """Load the ViT model and processor. Lazy-loaded on first use."""
    global _model, _processor, _model_loaded

    if _model_loaded:
        return True

    try:
        from transformers import ViTForImageClassification, ViTImageProcessor
        import torch

        if os.path.exists(os.path.join(MODEL_DIR, 'model.safetensors')):
            _processor = ViTImageProcessor.from_pretrained(MODEL_DIR)
            _model = ViTForImageClassification.from_pretrained(MODEL_DIR)
            _model.eval()
            _model_loaded = True
            print("Ship classifier model loaded from local files")
            return True
        else:
            # Download from HuggingFace
            model_name = "dima806/10_ship_types_image_detection"
            _processor = ViTImageProcessor.from_pretrained(model_name)
            _model = ViTForImageClassification.from_pretrained(model_name)
            _model.eval()

            # Save locally
            os.makedirs(MODEL_DIR, exist_ok=True)
            _processor.save_pretrained(MODEL_DIR)
            _model.save_pretrained(MODEL_DIR)
            _model_loaded = True
            print("Ship classifier model downloaded and saved")
            return True

    except ImportError as e:
        print(f"ML dependencies not installed: {e}")
        print("Run: pip install torch transformers Pillow")
        return False
    except Exception as e:
        print(f"Error loading model: {e}")
        return False


def classify_image(image_data):
    """
    Classify a ship image.

    Args:
        image_data: bytes (uploaded file) or str (file path)

    Returns:
        list of {label, confidence} sorted by confidence desc
    """
    if not load_model():
        return {'error': 'Model not loaded. Install: pip install torch transformers Pillow'}

    import torch

    try:
        if isinstance(image_data, (bytes, bytearray)):
            image = Image.open(io.BytesIO(image_data)).convert('RGB')
        elif isinstance(image_data, str):
            image = Image.open(image_data).convert('RGB')
        elif isinstance(image_data, Image.Image):
            image = image_data.convert('RGB')
        else:
            return {'error': 'Invalid image data'}

        inputs = _processor(images=image, return_tensors="pt")

        with torch.no_grad():
            outputs = _model(**inputs)
            logits = outputs.logits
            probs = torch.nn.functional.softmax(logits, dim=-1)[0]

        results = []
        for idx, prob in enumerate(probs):
            label = _model.config.id2label.get(str(idx), SHIP_LABELS.get(idx, f"Class {idx}"))
            results.append({
                'label': label,
                'confidence': round(float(prob) * 100, 2)
            })

        results.sort(key=lambda x: x['confidence'], reverse=True)
        return results

    except Exception as e:
        return {'error': f'Classification failed: {str(e)}'}


def get_model_info():
    """Get information about the loaded model."""
    config_path = os.path.join(MODEL_DIR, 'config.json')
    info = {
        'name': 'ViT Ship Classifier',
        'base_model': 'google/vit-base-patch16-224-in21k',
        'source': 'dima806/10_ship_types_image_detection',
        'accuracy': '99.6%',
        'image_size': 224,
        'labels': list(SHIP_LABELS.values()),
        'num_classes': len(SHIP_LABELS),
        'loaded': _model_loaded,
        'model_exists': os.path.exists(os.path.join(MODEL_DIR, 'model.safetensors')),
    }

    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
            info['architecture'] = config.get('architectures', ['Unknown'])[0]
            info['hidden_size'] = config.get('hidden_size', 0)
            info['num_layers'] = config.get('num_hidden_layers', 0)

    # Check checkpoints
    checkpoints = glob.glob(os.path.join(MODEL_DIR, 'checkpoint-*'))
    info['checkpoints'] = [os.path.basename(cp) for cp in checkpoints]

    return info


def get_available_datasets():
    """List available image datasets from downloads directory."""
    datasets = []

    if not os.path.exists(DOWNLOADS_DIR):
        return datasets

    for job_dir in os.listdir(DOWNLOADS_DIR):
        job_path = os.path.join(DOWNLOADS_DIR, job_dir)
        if os.path.isdir(job_path):
            images = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                images.extend(glob.glob(os.path.join(job_path, ext)))
            if images:
                datasets.append({
                    'name': f'Job {job_dir}',
                    'path': job_path,
                    'count': len(images),
                    'source': 'scraper'
                })

    # Check augmented directory
    if os.path.exists(AUGMENTED_DIR):
        for aug_dir in os.listdir(AUGMENTED_DIR):
            aug_path = os.path.join(AUGMENTED_DIR, aug_dir)
            if os.path.isdir(aug_path):
                images = []
                for ext in ['*.jpg', '*.jpeg', '*.png']:
                    images.extend(glob.glob(os.path.join(aug_path, ext)))
                if images:
                    datasets.append({
                        'name': f'Augmented: {aug_dir}',
                        'path': aug_path,
                        'count': len(images),
                        'source': 'augmented'
                    })

    return datasets


def augment_images(source_dir, num_per_image=5, transforms_config=None):
    """
    Generate synthetic images via augmentation.

    Args:
        source_dir: Directory with source images
        num_per_image: How many augmented versions per image
        transforms_config: Dict with enabled transforms

    Returns:
        dict with status and output directory
    """
    global _augment_status

    if _augment_status['running']:
        return {'error': 'Augmentation already running'}

    default_config = {
        'horizontal_flip': True,
        'rotation': True,
        'rotation_degrees': 15,
        'color_jitter': True,
        'random_crop': True,
        'gaussian_blur': True,
        'perspective': True,
    }

    config = {**default_config, **(transforms_config or {})}

    def _run_augmentation():
        global _augment_status
        _augment_status = {'running': True, 'progress': 0, 'total': 0, 'message': 'Starting...'}

        try:
            from torchvision import transforms as T

            # Build transform pipeline
            transform_list = []
            if config['horizontal_flip']:
                transform_list.append(T.RandomHorizontalFlip(p=0.5))
            if config['rotation']:
                transform_list.append(T.RandomRotation(degrees=config['rotation_degrees']))
            if config['color_jitter']:
                transform_list.append(T.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.3, hue=0.1))
            if config['random_crop']:
                transform_list.append(T.RandomResizedCrop(224, scale=(0.7, 1.0)))
            if config['gaussian_blur']:
                transform_list.append(T.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)))
            if config['perspective']:
                transform_list.append(T.RandomPerspective(distortion_scale=0.2, p=0.5))

            augment_transform = T.Compose(transform_list)

            # Find source images
            source_images = []
            for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                source_images.extend(glob.glob(os.path.join(source_dir, ext)))

            if not source_images:
                _augment_status = {'running': False, 'progress': 0, 'total': 0, 'message': 'No images found in source directory'}
                return

            total = len(source_images) * num_per_image
            _augment_status['total'] = total

            # Create output directory
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = os.path.join(AUGMENTED_DIR, f'aug_{timestamp}')
            os.makedirs(output_dir, exist_ok=True)

            generated = 0
            for img_path in source_images:
                try:
                    img = Image.open(img_path).convert('RGB')
                    base_name = os.path.splitext(os.path.basename(img_path))[0]

                    for i in range(num_per_image):
                        aug_img = augment_transform(img)
                        if not isinstance(aug_img, Image.Image):
                            from torchvision.transforms.functional import to_pil_image
                            aug_img = to_pil_image(aug_img)

                        save_path = os.path.join(output_dir, f'{base_name}_aug{i+1}.jpg')
                        aug_img.save(save_path, quality=90)
                        generated += 1
                        _augment_status['progress'] = generated
                        _augment_status['message'] = f'Generated {generated}/{total}'

                except Exception as e:
                    print(f"Augmentation error for {img_path}: {e}")

            _augment_status = {
                'running': False,
                'progress': generated,
                'total': total,
                'message': f'Done! Generated {generated} images in {output_dir}',
                'output_dir': output_dir
            }

        except ImportError:
            _augment_status = {'running': False, 'progress': 0, 'total': 0,
                               'message': 'torchvision not installed. Run: pip install torchvision'}
        except Exception as e:
            _augment_status = {'running': False, 'progress': 0, 'total': 0,
                               'message': f'Error: {str(e)}'}

    thread = threading.Thread(target=_run_augmentation)
    thread.daemon = True
    thread.start()

    return {'status': 'started', 'source': source_dir, 'num_per_image': num_per_image}


def get_augment_status():
    """Get current augmentation status."""
    return _augment_status


def start_training(dataset_dir, epochs=5, batch_size=8, learning_rate=5e-5):
    """
    Start fine-tuning the model on custom data.

    Expects dataset_dir to have subdirectories named by class label,
    each containing images of that class.
    """
    global _training_status

    if _training_status['running']:
        return {'error': 'Training already running'}

    def _run_training():
        global _training_status
        _training_status = {'running': True, 'progress': 0, 'message': 'Initializing...', 'history': []}

        try:
            import torch
            from transformers import ViTForImageClassification, ViTImageProcessor, TrainingArguments, Trainer
            from torch.utils.data import Dataset as TorchDataset

            if not load_model():
                _training_status = {'running': False, 'progress': 0, 'message': 'Model could not be loaded', 'history': []}
                return

            # Collect images from subdirectories
            class_dirs = [d for d in os.listdir(dataset_dir)
                          if os.path.isdir(os.path.join(dataset_dir, d))]

            if not class_dirs:
                _training_status = {'running': False, 'progress': 0,
                                    'message': 'No class subdirectories found. Expected: dataset_dir/ClassName/images...',
                                    'history': []}
                return

            _training_status['message'] = f'Found {len(class_dirs)} classes: {", ".join(class_dirs)}'

            # Build label mapping
            label2id = {name: idx for idx, name in enumerate(sorted(class_dirs))}
            id2label = {idx: name for name, idx in label2id.items()}

            # Custom dataset
            class ShipDataset(TorchDataset):
                def __init__(self, image_paths, labels, processor):
                    self.image_paths = image_paths
                    self.labels = labels
                    self.processor = processor

                def __len__(self):
                    return len(self.image_paths)

                def __getitem__(self, idx):
                    image = Image.open(self.image_paths[idx]).convert('RGB')
                    inputs = self.processor(images=image, return_tensors="pt")
                    inputs = {k: v.squeeze(0) for k, v in inputs.items()}
                    inputs['labels'] = torch.tensor(self.labels[idx])
                    return inputs

            # Collect all images
            all_images = []
            all_labels = []
            for class_name in sorted(class_dirs):
                class_path = os.path.join(dataset_dir, class_name)
                for ext in ['*.jpg', '*.jpeg', '*.png', '*.webp']:
                    for img_path in glob.glob(os.path.join(class_path, ext)):
                        all_images.append(img_path)
                        all_labels.append(label2id[class_name])

            if len(all_images) < 10:
                _training_status = {'running': False, 'progress': 0,
                                    'message': f'Only {len(all_images)} images found. Need at least 10.',
                                    'history': []}
                return

            _training_status['message'] = f'Training on {len(all_images)} images across {len(class_dirs)} classes'

            # Split train/val (80/20)
            combined = list(zip(all_images, all_labels))
            random.shuffle(combined)
            split = int(len(combined) * 0.8)
            train_imgs, train_labels = zip(*combined[:split])
            val_imgs, val_labels = zip(*combined[split:])

            train_dataset = ShipDataset(list(train_imgs), list(train_labels), _processor)
            val_dataset = ShipDataset(list(val_imgs), list(val_labels), _processor)

            # Training config
            output_dir = os.path.join(MODEL_DIR, f'finetune_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            training_args = TrainingArguments(
                output_dir=output_dir,
                num_train_epochs=epochs,
                per_device_train_batch_size=batch_size,
                per_device_eval_batch_size=batch_size,
                learning_rate=learning_rate,
                eval_strategy="epoch",
                save_strategy="epoch",
                logging_steps=10,
                load_best_model_at_end=True,
                metric_for_best_model="accuracy",
                remove_unused_columns=False,
            )

            def compute_metrics(eval_pred):
                import numpy as np
                logits, labels = eval_pred
                predictions = np.argmax(logits, axis=-1)
                accuracy = (predictions == labels).mean()
                return {"accuracy": accuracy}

            # Update model for new classes if different
            model = ViTForImageClassification.from_pretrained(
                MODEL_DIR,
                num_labels=len(class_dirs),
                id2label=id2label,
                label2id=label2id,
                ignore_mismatched_sizes=True
            )

            trainer = Trainer(
                model=model,
                args=training_args,
                train_dataset=train_dataset,
                eval_dataset=val_dataset,
                compute_metrics=compute_metrics,
            )

            _training_status['message'] = 'Training started...'
            result = trainer.train()

            # Save the fine-tuned model
            trainer.save_model(output_dir)
            _processor.save_pretrained(output_dir)

            _training_status = {
                'running': False,
                'progress': 100,
                'message': f'Training complete! Model saved to {output_dir}',
                'history': [
                    {'epoch': log.get('epoch', 0), 'loss': log.get('loss', 0), 'accuracy': log.get('eval_accuracy', 0)}
                    for log in trainer.state.log_history if 'loss' in log or 'eval_accuracy' in log
                ],
                'output_dir': output_dir,
                'train_samples': len(train_dataset),
                'val_samples': len(val_dataset),
                'classes': list(id2label.values()),
            }

        except ImportError as e:
            _training_status = {'running': False, 'progress': 0,
                                'message': f'Missing dependency: {e}', 'history': []}
        except Exception as e:
            _training_status = {'running': False, 'progress': 0,
                                'message': f'Training error: {str(e)}', 'history': []}

    thread = threading.Thread(target=_run_training)
    thread.daemon = True
    thread.start()

    return {'status': 'started', 'dataset': dataset_dir, 'epochs': epochs}


def get_training_status():
    """Get current training status."""
    return _training_status
