import argparse
import os
import shutil
import tempfile

import numpy as np
from PIL import Image

from sem_scale_bar.cli import process_path
from sem_scale_bar.core import build_output_path, process_file

TEST_CASES = [
    {
        "source": "./images for test/SM-32_1.tiff",
        "options": {
            "lzw": False,
            "language": "English",
            "background-color": "white",
            "scale-bar-corner": "right",
        },
        "reference": "./images for test/reference/White_English_Right_NoLabel.tiff",
    },
    {
        "source": "./images for test/SM-32_2.tiff",
        "options": {
            "lzw": False,
            "language": "English",
            "background-color": "black",
            "scale-bar-corner": "right",
        },
        "reference": "./images for test/reference/Black_English_Right_NoLabel.tiff",
    },
    {
        "source": "./images for test/Tescan_1.TIF",
        "options": {
            "lzw": False,
            "language": "Russian",
            "background-color": "white",
            "scale-bar-corner": "right",
        },
        "reference": "./images for test/reference/White_Russian_Right_NoLabel.TIF",
    },
    {
        "source": "./images for test/Tescan_2.TIF",
        "options": {
            "lzw": False,
            "language": "Russian",
            "background-color": "black",
            "scale-bar-corner": "left",
        },
        "reference": "./images for test/reference/Black_Russian_Left_NoLabel.TIF",
    },
    {
        "source": "./images for test/Tescan_3.TIF",
        "options": {
            "lzw": False,
            "language": "Russian",
            "background-color": "black",
            "scale-bar-corner": "left",
            "label": "a)",
            "label-corner": "left",
        },
        "reference": (
            "./images for test/reference/Black_Russian_Left_Label_a)_Left.TIF"
        ),
    },
    {
        "source": "./images for test/Zeiss_2.tif",
        "options": {
            "lzw": False,
            "language": "English",
            "background-color": "white",
            "scale-bar-corner": "left",
            "label": "b)",
            "label-corner": "right",
        },
        "reference": (
            "./images for test/reference/White_English_Left_Label_b)_Right.tif"
        ),
    },
    {
        "source": "./images for test/Zeiss_3.tif",
        "options": {
            "lzw": False,
            "language": "English",
            "background-color": "white",
            "scale-bar-corner": "right",
            "label": "III)",
            "label-corner": "right",
        },
        "reference": (
            "./images for test/reference/White_English_Right_Label_III)_Right.tif"
        ),
    },
    {
        "source": "./images for test/Zeiss_1.tif",
        "options": {
            "lzw": True,
            "language": "English",
            "background-color": "transparent",
            "scale-bar-corner": "left",
            "standard-sizes": True,
        },
        "reference": (
            "./images for test/reference/"
            "Transparent_English_Left_NoLabel_StandardSizes.tif"
        ),
    },
    {
        "source": "./images for test/Zeiss_3.tif",
        "options": {
            "lzw": True,
            "language": "English",
            "background-color": "white",
            "scale-bar-corner": "right",
            "end-ticks": True,
        },
        "reference": (
            "./images for test/reference/"
            "White_English_Right_EndTicks.tif"
        ),
    },
    {
        "source": "./images for test/Tescan_1.TIF",
        "options": {
            "lzw": False,
            "language": "Russian",
            "background-color": "transparent",
            "scale-bar-corner": "left",
            "end-ticks": True,
        },
        "reference": (
            "./images for test/reference/"
            "Transparent_Russian_Left_EndTicks.TIF"
        ),
    },
    {
        "source": "./images for test/Zeiss_2.tif",
        "options": {
            "lzw": True,
            "language": "English",
            "background-color": "white",
            "scale-bar-corner": "right",
        },
        "reference": "./images for test/reference/output_dir/Zeiss_2.tif",
        "output_mode": "output_dir",
    },
    {
        "source": "./images for test/Tescan_2.TIF",
        "options": {
            "lzw": False,
            "language": "Russian",
            "background-color": "black",
            "scale-bar-corner": "left",
        },
        "reference": "./images for test/reference/output_index/Tescan_2_cut_3.TIF",
        "output_mode": "output_index",
        "output_index": 3,
    },
]


def load_image(path):
    with Image.open(path) as image:
        return np.asarray(image)


def compare_images(generated_path, reference_path):
    generated = load_image(generated_path)
    reference = load_image(reference_path)
    if generated.shape != reference.shape:
        raise AssertionError(
            "Image shape mismatch: "
            f"generated={generated.shape} reference={reference.shape}"
        )
    if not np.array_equal(generated, reference):
        raise AssertionError("Image pixels differ from reference.")


def process_case_direct(case, output_path):
    options = case["options"]
    process_file(
        case["source"],
        options.get("language", "English"),
        options.get("background-color", "white"),
        options.get("scale-bar-corner", "right"),
        options.get("label", ""),
        options.get("label-corner", "left"),
        case.get("output_index", 1),
        options.get("standard-sizes", False),
        options.get("end-ticks", False),
        lzw_compression=options.get("lzw", True),
        output_path=output_path,
    )


def process_case_output_dir(case, output_dir):
    options = case["options"]
    process_path(
        case["source"],
        options.get("language", "English"),
        options.get("background-color", "white"),
        options.get("scale-bar-corner", "right"),
        options.get("label", ""),
        options.get("label-corner", "left"),
        case.get("output_index", 1),
        options.get("standard-sizes", False),
        options.get("end-ticks", False),
        options.get("lzw", True),
        output_dir=output_dir,
    )


def process_case_output_index(case, work_dir):
    options = case["options"]
    os.makedirs(work_dir, exist_ok=True)
    source_name = os.path.basename(case["source"])
    working_source = os.path.join(work_dir, source_name)
    shutil.copy2(case["source"], working_source)
    process_file(
        working_source,
        options.get("language", "English"),
        options.get("background-color", "white"),
        options.get("scale-bar-corner", "right"),
        options.get("label", ""),
        options.get("label-corner", "left"),
        case.get("output_index", 1),
        options.get("standard-sizes", False),
        options.get("end-ticks", False),
        lzw_compression=options.get("lzw", True),
        output_path=None,
    )
    output_extension = os.path.splitext(source_name)[1]
    output_name = (
        f"{os.path.splitext(source_name)[0]}_cut_{case.get('output_index', 1)}"
        f"{output_extension}"
    )
    return os.path.join(work_dir, output_name)


def generate_references():
    for case in TEST_CASES:
        if not os.path.exists(case["source"]):
            raise FileNotFoundError(f"Missing source image: {case['source']}")
        reference = case["reference"]
        os.makedirs(os.path.dirname(reference), exist_ok=True)
        output_mode = case.get("output_mode", "direct")
        if output_mode == "output_dir":
            process_case_output_dir(case, os.path.dirname(reference))
        elif output_mode == "output_index":
            with tempfile.TemporaryDirectory() as work_dir:
                generated = process_case_output_index(case, work_dir)
                shutil.copy2(generated, reference)
        else:
            process_case_direct(case, reference)


def verify_references():
    for case in TEST_CASES:
        if not os.path.exists(case["source"]):
            raise FileNotFoundError(f"Missing source image: {case['source']}")
        reference = case["reference"]
        if not os.path.exists(reference):
            print(
                "Warning: missing reference image. Run --generate-references to "
                f"create it: {reference}"
            )
            continue
        output_mode = case.get("output_mode", "direct")
        if output_mode == "output_dir":
            with tempfile.TemporaryDirectory() as output_dir:
                process_case_output_dir(case, output_dir)
                generated = build_output_path(
                    case["source"], output_dir, os.path.dirname(case["source"])
                )
                compare_images(generated, reference)
        elif output_mode == "output_index":
            with tempfile.TemporaryDirectory() as work_dir:
                generated = process_case_output_index(case, work_dir)
                compare_images(generated, reference)
        else:
            with tempfile.TemporaryDirectory() as output_dir:
                generated = os.path.join(
                    output_dir, os.path.basename(reference)
                )
                process_case_direct(case, generated)
                try:
                  compare_images(generated, reference)
                except Exception as e:
                  print(case)
                  raise e


def build_parser():
    parser = argparse.ArgumentParser(
        description="Generate or verify image regression references."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--generate-references",
        action="store_true",
        help="Generate reference images defined in TEST_CASES.",
    )
    mode.add_argument(
        "--verify",
        action="store_true",
        help="Generate images and compare them against references.",
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    if args.generate_references:
        generate_references()
    else:
        verify_references()


if __name__ == "__main__":
    main()
