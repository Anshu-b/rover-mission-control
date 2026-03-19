#!/usr/bin/env python3

import argparse
import random
from pathlib import Path

import cv2
import numpy as np
import onnx
import torch
import torch.nn as nn
from onnxruntime.quantization import CalibrationDataReader
from onnxruntime.quantization import QuantFormat
from onnxruntime.quantization import QuantType
from onnxruntime.quantization import quantize_static
from torch.utils.data import DataLoader
from torch.utils.data import Dataset


CLASS_NAMES = ["soil", "carpet", "wood"]
IMAGE_WIDTH = 96
IMAGE_HEIGHT = 96
CHANNELS = 3
CALIBRATION_IMAGES_PER_CLASS = 64
TRAIN_SPLIT = 0.70
VAL_SPLIT = 0.15
TEST_SPLIT = 0.15


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def load_and_preprocess_image(image_path):
    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(
        image,
        (IMAGE_WIDTH, IMAGE_HEIGHT),
        interpolation=cv2.INTER_AREA
    )

    image = image.astype(np.float32) / 255.0
    image = np.transpose(image, (2, 0, 1))
    return image


class GroundDataset(Dataset):
    def __init__(self, root_dir, class_names, split_name):
        self.samples = []

        for class_index, class_name in enumerate(class_names):
            class_dir = Path(root_dir) / class_name
            if not class_dir.exists():
                continue

            image_paths = sorted(
                [
                    path for path in class_dir.iterdir()
                    if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
                ]
            )

            random.shuffle(image_paths)

            total_images = len(image_paths)
            train_end = int(total_images * TRAIN_SPLIT)
            val_end = train_end + int(total_images * VAL_SPLIT)

            if split_name == "train":
                selected = image_paths[:train_end]
            elif split_name == "val":
                selected = image_paths[train_end:val_end]
            elif split_name == "test":
                selected = image_paths[val_end:]
            else:
                raise ValueError(f"Unknown split_name: {split_name}")

            for image_path in selected:
                self.samples.append((str(image_path), class_index))

        random.shuffle(self.samples)

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, index):
        image_path, label = self.samples[index]
        image = load_and_preprocess_image(image_path)
        return torch.tensor(image), torch.tensor(label, dtype=torch.long)


class TinyGroundCNN(nn.Module):
    def __init__(self, num_classes):
        super().__init__()

        self.features = nn.Sequential(
            nn.Conv2d(CHANNELS, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(16, 32, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv2d(64, 96, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.AdaptiveAvgPool2d((1, 1))
        )

        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(96, 48),
            nn.ReLU(),
            nn.Linear(48, num_classes)
        )

    def forward(self, x):
        x = self.features(x)
        x = self.classifier(x)
        return x


class GroundCalibrationReader(CalibrationDataReader):
    def __init__(self, image_paths):
        self.image_paths = list(image_paths)
        self.index = 0

    def get_next(self):
        if self.index >= len(self.image_paths):
            return None

        image = load_and_preprocess_image(self.image_paths[self.index])
        image = np.expand_dims(image, axis=0).astype(np.float32)
        self.index += 1
        return {"input": image}


def evaluate_model(model, loader, device):
    model.eval()

    total = 0
    correct = 0
    running_loss = 0.0
    criterion = nn.CrossEntropyLoss()

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            loss = criterion(outputs, labels)

            predictions = torch.argmax(outputs, dim=1)

            total += labels.size(0)
            correct += (predictions == labels).sum().item()
            running_loss += loss.item() * labels.size(0)

    if total == 0:
        return 0.0, 0.0

    avg_loss = running_loss / total
    accuracy = correct / total
    return avg_loss, accuracy

def compute_confusion_matrix(model, loader, device):
    model.eval()

    num_classes = len(CLASS_NAMES)
    matrix = np.zeros((num_classes, num_classes), dtype=int)

    with torch.no_grad():
        for images, labels in loader:
            images = images.to(device)
            labels = labels.to(device)

            outputs = model(images)
            preds = torch.argmax(outputs, dim=1)

            for t, p in zip(labels.cpu().numpy(), preds.cpu().numpy()):
                matrix[t][p] += 1

    print("\nConfusion Matrix")
    print("rows = true class, cols = predicted class\n")

    header = "      " + " ".join(f"{c:>8}" for c in CLASS_NAMES)
    print(header)

    for i, row in enumerate(matrix):
        row_str = " ".join(f"{v:8d}" for v in row)
        print(f"{CLASS_NAMES[i]:>6} {row_str}")

    return matrix

def collect_calibration_images(data_dir):
    calibration_paths = []

    for class_name in CLASS_NAMES:
        class_dir = Path(data_dir) / class_name
        if not class_dir.exists():
            continue

        image_paths = sorted(
            [
                path for path in class_dir.iterdir()
                if path.suffix.lower() in [".jpg", ".jpeg", ".png"]
            ]
        )

        random.shuffle(image_paths)
        calibration_paths.extend(
            image_paths[:CALIBRATION_IMAGES_PER_CLASS]
        )

    random.shuffle(calibration_paths)
    return calibration_paths


def export_plain_onnx(model, device, output_path):
    model.eval()

    dummy_input = torch.randn(
        1,
        CHANNELS,
        IMAGE_HEIGHT,
        IMAGE_WIDTH,
        device=device
    )

    with torch.no_grad():
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=13,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes=None,
            dynamo=False
        )

    onnx_model = onnx.load(str(output_path))
    onnx.checker.check_model(onnx_model)


def export_quantized_onnx(model, device, data_dir, output_dir):
    output_dir = Path(output_dir)
    float_path = output_dir / "ground_classifier.onnx"
    int8_path = output_dir / "ground_classifier_int8.onnx"

    export_plain_onnx(model, device, float_path)

    calibration_paths = collect_calibration_images(data_dir)
    if not calibration_paths:
        raise ValueError("No calibration images found for quantization.")

    calibration_reader = GroundCalibrationReader(calibration_paths)

    quantize_static(
        model_input=str(float_path),
        model_output=str(int8_path),
        calibration_data_reader=calibration_reader,
        quant_format=QuantFormat.QOperator,
        activation_type=QuantType.QUInt8,
        weight_type=QuantType.QInt8,
        per_channel=False
    )

    float_size = float_path.stat().st_size
    int8_size = int8_path.stat().st_size

    print(f"Saved ONNX float32: {float_path}")
    print(f"Saved ONNX int8:    {int8_path}")
    print(
        f"Size float32: {float_size / 1024:.1f} KB | "
        f"int8: {int8_size / 1024:.1f} KB"
    )

    return float_path, int8_path


def train_model(data_dir, output_dir, epochs, batch_size, learning_rate, seed):
    set_seed(seed)

    train_dataset = GroundDataset(data_dir, CLASS_NAMES, "train")
    val_dataset = GroundDataset(data_dir, CLASS_NAMES, "val")
    test_dataset = GroundDataset(data_dir, CLASS_NAMES, "test")

    if len(train_dataset) == 0:
        raise ValueError("No training images found.")

    if len(val_dataset) == 0:
        raise ValueError(
            "Validation split is empty. Collect more images per class."
        )

    if len(test_dataset) == 0:
        raise ValueError(
            "Test split is empty. Collect more images per class."
        )

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0
    )

    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    test_loader = DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=0
    )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = TinyGroundCNN(num_classes=len(CLASS_NAMES)).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    criterion = nn.CrossEntropyLoss()

    best_val_accuracy = 0.0
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    best_weights_path = output_dir / "best_ground_model.pt"

    print(f"Device: {device}")
    print(f"Train samples: {len(train_dataset)}")
    print(f"Validation samples: {len(val_dataset)}")
    print(f"Test samples: {len(test_dataset)}")
    print()

    for epoch in range(epochs):
        model.train()

        running_loss = 0.0
        total = 0
        correct = 0

        for images, labels in train_loader:
            images = images.to(device)
            labels = labels.to(device)

            optimizer.zero_grad()

            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()

            predictions = torch.argmax(outputs, dim=1)

            batch_size_now = labels.size(0)
            total += batch_size_now
            correct += (predictions == labels).sum().item()
            running_loss += loss.item() * batch_size_now

        train_loss = running_loss / total
        train_accuracy = correct / total

        val_loss, val_accuracy = evaluate_model(model, val_loader, device)

        print(
            f"Epoch {epoch + 1:02d}/{epochs} | "
            f"train_loss={train_loss:.4f} "
            f"train_acc={train_accuracy:.4f} | "
            f"val_loss={val_loss:.4f} "
            f"val_acc={val_accuracy:.4f}"
        )

        if val_accuracy > best_val_accuracy:
            best_val_accuracy = val_accuracy
            torch.save(model.state_dict(), best_weights_path)

    print()
    print(f"Best validation accuracy: {best_val_accuracy:.4f}")

    model.load_state_dict(
        torch.load(best_weights_path, map_location=device)
    )
    model.eval()

    test_loss, test_accuracy = evaluate_model(model, test_loader, device)

    print(f"Final test loss: {test_loss:.4f}")
    print(f"Final test accuracy: {test_accuracy:.4f}")

    conf_matrix = compute_confusion_matrix(model, test_loader, device)

    labels_path = output_dir / "labels.txt"
    with open(labels_path, "w", encoding="utf-8") as file_obj:
        for class_name in CLASS_NAMES:
            file_obj.write(class_name + "\n")

    print(f"Saved weights: {best_weights_path}")
    print(f"Saved labels:  {labels_path}")

    export_quantized_onnx(
        model=model,
        device=device,
        data_dir=data_dir,
        output_dir=output_dir
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/train"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="model_out"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=20
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=32
    )
    parser.add_argument(
        "--lr",
        type=float,
        default=0.001
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42
    )

    args = parser.parse_args()

    train_model(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        seed=args.seed
    )


if __name__ == "__main__":
    main()