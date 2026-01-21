import os

import numpy as np
import png
import tifffile
from PIL import Image, ImageDraw, ImageFont

_FONT_CANDIDATES = (
    "arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed.ttf",
    "DejaVuSans.ttf",
    "Arial Unicode.ttf",
)


def _load_font(font_size):
    for candidate in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(candidate, font_size)
        except OSError:
            continue
    return ImageFont.load_default()

__all__ = [
    "extract_png_chunks",
    "get_scale",
    "cut_panel",
    "tif2np",
    "png2np",
    "get_tags_from_tiff",
    "get_bar",
    "draw_bar",
    "build_output_path",
    "process_file",
]


def _standardize_scale_value(value):
    if value <= 0:
        return value
    exponent = 10 ** np.floor(np.log10(value))
    leading = value / exponent
    if leading < 2:
        standard = 1
    elif leading < 5:
        standard = 2
    else:
        standard = 5
    result = standard * exponent
    if np.isclose(result, round(result)):
        return int(round(result))
    return result


def extract_png_chunks(filename):
    reader = png.Reader(filename)
    chunks = []
    for chunk_type, chunk_data in reader.chunks():
        chunks.append((chunk_type, chunk_data))
    return chunks


def get_scale(tags):
    pixel_size = 0  # for debugging
    if "CZ_SEM" in tags:
        try:  # for Zeiss images
            length = tags["CZ_SEM"]["ap_image_pixel_size"][2]
            if length == "nm":
                pixel_size = float(
                    tags["CZ_SEM"]["ap_image_pixel_size"][1] / 1000
                )  # microns per pixel
            else:  # length == 'pm':
                pixel_size = float(
                    tags["CZ_SEM"]["ap_image_pixel_size"][1] / 1000000
                )  # microns per pixel
        except:  # for LEO images
            n = tags["ImageWidth"] / 1024  # to recalculate image resolution in meter per pixel
            pixel_size = float(tags["CZ_SEM"][""][3] * 1000000) / n  # microns per pixel

    elif "50431" in tags:
        text = tags["50431"].split()  # for Tescan images
        for j in range(len(text)):
            find_pixel_size = str(text[j]).find("PixelSizeX")
            if find_pixel_size != -1:
                pixel_size = (
                    float(str(text[j]).split("=")[1].strip("'")) * 1000000
                )  # microns per pixel
                break

    elif "FEI_HELIOS" in tags:  # for FEI and SM-32 images
        if "¦" in tags["FEI_HELIOS"]["Beam"]["HFW"]:
            pixel_size = (
                float(tags["FEI_HELIOS"]["Beam"]["HFW"].split("¦")[0])
                / tags["ImageWidth"]
            )  # microns per pixel
        else:
            pixel_size = (
                float(tags["FEI_HELIOS"]["Beam"]["HFW"].split("mm")[0])
                / tags["ImageWidth"]
                * 1000
            )  # microns per pixel

    else:
        try:
            if b"gIFx" in tags[1]:  # metadata in png-image from Tescan microscope
                text = tags[1][1].split()
                for j in range(len(text)):
                    find_pixel_size = str(text[j]).find("PixelSizeX")
                    if find_pixel_size != -1:
                        pixel_size = (
                            float(str(text[j]).split("=")[1].strip("'")) * 1000000
                        )  # microns per pixel
                        break
        except:
            print("Unknown metadata format")

    return pixel_size


def cut_panel(img, tags):
    height, width = img.shape[:2]
    if "CZ_SEM" in tags:
        i = 0
        if "ap_image_pixel_size" in tags["CZ_SEM"]:  # for Zeiss images
            for row in img:
                if np.all(
                    row[2 : row.size - 3] == img[-2][2 : row.size - 3]
                ):  # img[-2] is a lower part of the infopanel frame; we want to find the upper part of the frame
                    strip_pixel_size = height - i
                    break
                i += 1
        else:  # for LEO images
            black_row = np.zeros(width - 6)
            for row in img:
                if np.all(black_row == row[3 : row.size - 3]):
                    strip_pixel_size = height - i
                    break
                i += 1

    elif "50431" in tags:
        text = tags["50431"].split()  # for Tescan images
        for j in range(len(text)):
            start_strip = str(text[j]).find(
                "ImageStripSize"
            )  # Tescan writes the infopanel height (in pixels) to the metadata parameter "ImageStripSize"
            if start_strip != -1:
                strip_pixel_size = int(str(text[j]).split("=")[1].strip("'"))
                break

    elif "FEI_HELIOS" in tags:  # for FEI and SM-32 images
        short_height = tags["FEI_HELIOS"]["Scan"]["ResolutionY"]
        full_height = tags["ImageLength"]
        strip_pixel_size = full_height - short_height

    else:
        try:
            if b"gIFx" in tags[1]:  # metadata in png-image from Tescan microscope
                text = tags[1][1].split()
                for j in range(len(text)):
                    start_strip = str(text[j]).find(
                        "ImageStripSize"
                    )  # Tescan writes the infopanel height (in pixels) to the metadata parameter "ImageStripSize"
                    if start_strip != -1:
                        strip_pixel_size = int(str(text[j]).split("=")[1].strip("'"))
                        break
        except:
            print(
                "Unknown metadata format. Only Zeiss, Tescan or LEO SEM initial images can be processed."
            )

    h = height - strip_pixel_size
    crop = img[0:h, 0:width]

    return crop


def tif2np(tif, name):
    img = tif.pages[0].asarray()
    if len(img.shape) > 2:
        img = img.mean(axis=0)
    assert len(img.shape) == 2
    if img.max() > 255:
        img = img / 255
    return img.astype(np.float32)


def png2np(filename):
    reader = png.Reader(filename)
    _, _, pixels, _ = reader.read()
    img = np.vstack([row for row in pixels])
    if len(img.shape) > 2:
        img = img.mean(axis=0)
    assert len(img.shape) == 2
    if img.max() > 255:
        img = img / 255
    return img.astype(np.float32)


def get_tags_from_tiff(tif):
    tif_tags = {}
    for tag in tif.pages[0].tags.values():
        name, value = tag.name, tag.value
        tif_tags[name] = value
    return tif_tags


def get_bar(img, pixel_size, lang, use_standard_sizes):
    _, width = img.shape[:2]
    bar = (
        width * pixel_size / 6
    )  # bar lenght is about 1/6 of image width, microns, not an integer
    if bar >= 0.55:
        if use_standard_sizes:
            bar = _standardize_scale_value(bar)
        else:
            if bar >= 100:
                bar = round(bar / 100) * 100
            elif 100 > bar >= 10:
                bar = round(bar / 10) * 10
            else:
                bar = round(bar)
        bar_pixel_size = bar / pixel_size
        if lang == "Russian":
            scale = "мкм"
        else:
            scale = "\u03BCm"

    else:
        bar = bar * 1000
        if use_standard_sizes:
            bar = _standardize_scale_value(bar)
        else:
            if bar >= 100:
                bar = round(bar / 100) * 100
            elif 100 > bar >= 10:
                bar = round(bar / 10) * 10
            else:
                bar = round(bar)
        bar_pixel_size = bar / (pixel_size * 1000)
        if lang == "Russian":
            scale = "нм"
        else:
            scale = "nm"

    return (bar, bar_pixel_size, scale)


def draw_bar(
    img,
    tags,
    lang,
    rect_color,
    corner,
    label,
    label_corner,
    use_standard_sizes,
    end_ticks=False,
):
    img1 = Image.fromarray(img)
    img1 = img1.convert("RGB")
    img2 = ImageDraw.Draw(img1)
    height = img.shape[0]

    pixel_size = get_scale(tags)
    bar_data = get_bar(img, pixel_size, lang, use_standard_sizes)
    bar = round(bar_data[1])
    scale_text = f"{bar_data[0]} {bar_data[2]}"

    n = img.shape[1] / 2048  # make font size and bar size match image size
    font_size = round(80 * n)
    font = _load_font(font_size)
    text_length = img2.textlength(scale_text, font=font)
    bbox = img2.textbbox((0, 0), scale_text, font=font)
    text_height = bbox[3] - bbox[1]

    label_box = img2.textbbox((0, 0), label, font=font)
    label_text_height = label_box[3] - label_box[1] + round(40 * n)

    rect_height = text_height + round(67 * n)
    rect_bar_width = round(img.shape[1] / 6) if use_standard_sizes else bar
    rect_width = rect_bar_width + round(45 * n)  # bar width, pixels

    transparent_background = rect_color == "transparent"
    if transparent_background:
        bar_color = "white"
        outline_color = "black"
    elif rect_color == "black":
        bar_color = "white"
        outline_color = rect_color
    else:
        bar_color = "black"
        outline_color = rect_color

    outline_width = max(1, round(3 * n))

    if corner == "right":
        width = img.shape[1]
        # draw filled rectangle at the down right corner
        rect_left = width - rect_width
        rect_right = width
        if not transparent_background:
            img2.rectangle(
                [
                    (rect_left, height - rect_height),  # left upside corner
                    (rect_right, height),  # right downside corner
                ],
                fill=rect_color,
                outline=rect_color,
            )
    else:
        width = 0
        # draw filled rectangle at the down left corner
        rect_left = 0
        rect_right = rect_width
        if not transparent_background:
            img2.rectangle(
                [
                    (rect_left, height - rect_height),  # left upside corner
                    (rect_right, height),  # right downside corner
                ],
                fill=rect_color,
                outline=rect_color,
            )

    # draw contrast bar in the rectangle
    if use_standard_sizes:
        bar_area_left = (
            rect_left + round(20 * n)
            if corner == "left"
            else rect_right - rect_bar_width - round(20 * n)
        )
        bar_area_start = bar_area_left + (rect_bar_width - bar) / 2
        bar_start = bar_area_start
        bar_end = bar_area_start + bar
    else:
        bar_start = abs(width - bar - round(20 * n))
        bar_end = abs(width - round(20 * n))
    bar_y = height - round(30 * n)
    bar_thickness = round(20 * n)
    tick_thickness = max(1, round(bar_thickness / 3))
    tick_height = round(40 * n)
    if transparent_background and end_ticks:
        tick_half_height = tick_height / 2
        tick_half_width = tick_thickness / 2
        tick_positions = [
            bar_start + tick_half_width,
            bar_end - tick_half_width,
        ]
        outline_pad = outline_width / 2
        img2.rectangle(
            [
                (bar_start - outline_pad, bar_y - bar_thickness / 2 - outline_pad),
                (bar_end + outline_pad, bar_y + bar_thickness / 2 + outline_pad),
            ],
            fill=None,
            outline=outline_color,
            width=outline_width,
        )
        for tick_x in tick_positions:
            img2.rectangle(
                [
                    (
                        tick_x - tick_half_width - outline_pad,
                        bar_y - tick_half_height - outline_pad,
                    ),
                    (
                        tick_x + tick_half_width + outline_pad,
                        bar_y + tick_half_height + outline_pad,
                    ),
                ],
                fill=None,
                outline=outline_color,
                width=outline_width,
            )
        img2.rectangle(
            [
                (bar_start, bar_y - bar_thickness / 2),
                (bar_end, bar_y + bar_thickness / 2),
            ],
            fill=bar_color,
            outline=None,
        )
        for tick_x in tick_positions:
            img2.rectangle(
                [
                    (tick_x - tick_half_width, bar_y - tick_half_height),
                    (tick_x + tick_half_width, bar_y + tick_half_height),
                ],
                fill=bar_color,
                outline=None,
            )
    else:
        if transparent_background:
            outline_pad = outline_width / 2
            img2.rectangle(
                [
                    (bar_start - outline_pad, bar_y - bar_thickness / 2 - outline_pad),
                    (bar_end + outline_pad, bar_y + bar_thickness / 2 + outline_pad),
                ],
                fill=None,
                outline=outline_color,
                width=outline_width,
            )
            img2.rectangle(
                [
                    (bar_start, bar_y - bar_thickness / 2),
                    (bar_end, bar_y + bar_thickness / 2),
                ],
                fill=bar_color,
                outline=None,
            )
        else:
            img2.line(
                [
                    (bar_start, bar_y),
                    (bar_end, bar_y),
                ],
                fill=bar_color,
                width=bar_thickness,
            )
        if end_ticks:
            tick_half_height = tick_height / 2
            tick_positions = [
                bar_start + tick_thickness / 2,
                bar_end - tick_thickness / 2,
            ]
            if transparent_background:
                outline_pad = outline_width / 2
                tick_half_width = tick_thickness / 2
                for tick_x in tick_positions:
                    img2.rectangle(
                        [
                            (
                                tick_x - tick_half_width - outline_pad,
                                bar_y - tick_half_height - outline_pad,
                            ),
                            (
                                tick_x + tick_half_width + outline_pad,
                                bar_y + tick_half_height + outline_pad,
                            ),
                        ],
                        fill=None,
                        outline=outline_color,
                        width=outline_width,
                    )
                    img2.rectangle(
                        [
                            (tick_x - tick_half_width, bar_y - tick_half_height),
                            (tick_x + tick_half_width, bar_y + tick_half_height),
                        ],
                        fill=bar_color,
                        outline=None,
                    )
            else:
                for tick_x in tick_positions:
                    img2.line(
                        [
                            (tick_x, bar_y - tick_half_height),
                            (tick_x, bar_y + tick_half_height),
                        ],
                        fill=bar_color,
                        width=tick_thickness,
                    )

    # label box
    if label != "":
        if label_corner == "left":
            # draw filled rectangle at the up left corner
            label_width = 0
            x_label = round(50 * n) / 2
            if not transparent_background:
                img2.rectangle(
                    [
                        (0, 0),  # left upside corner
                        (
                            label_box[2] + round(50 * n),
                            label_text_height,
                        ),  # right downside corner
                    ],
                    fill=rect_color,
                    outline=rect_color,
                )
        else:
            label_width = img.shape[1]
            x_label = label_width - label_box[2] - round(50 * n) / 2
            # draw filled rectangle at the up right corner
            if not transparent_background:
                img2.rectangle(
                    [
                        (
                            label_width - label_box[2] - round(50 * n),
                            0,
                        ),  # left upside corner
                        (label_width, label_text_height),  # right downside corner
                    ],
                    fill=rect_color,
                    outline=rect_color,
                )

    x = abs(width - rect_width / 2) - text_length / 2
    y = height - rect_height

    # draw scale text
    img2.text(
        (x, y),
        scale_text,
        fill=bar_color,
        font=font,
        stroke_width=outline_width if transparent_background else 0,
        stroke_fill=outline_color if transparent_background else None,
    )

    # draw label text
    if label != "":
        img2.text(
            (x_label, 0),
            label,
            fill=bar_color,
            font=font,
            stroke_width=outline_width if transparent_background else 0,
            stroke_fill=outline_color if transparent_background else None,
        )

    return img1


def build_output_path(full_file_name, output_dir, input_root=None):
    if not output_dir:
        return None
    root = input_root if input_root else os.path.dirname(full_file_name)
    relative_path = os.path.relpath(full_file_name, root)
    return os.path.join(output_dir, relative_path)


# read full file path, process file (read tif metadata, cut panel, draw scale bar) and save result
def process_file(
    full_file_name,
    lan,
    rect_color,
    corner,
    label,
    label_corner,
    k,
    use_standard_sizes,
    end_ticks=False,
    lzw_compression=True,
    output_path=None,
):
    folder, filename_ext = os.path.split(full_file_name)
    short_file_name, extension = os.path.splitext(filename_ext)
    _, extension = extension.split(".")
    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if extension == "tif" or extension == "TIF" or extension == "tiff":
        try:
            tif = tifffile.TiffFile(full_file_name)
            img = tif2np(tif, full_file_name)
            tif_tags = get_tags_from_tiff(tif)
            img_cropped = cut_panel(img, tif_tags)
            result = draw_bar(
                img_cropped,
                tif_tags,
                lan,
                rect_color,
                corner,
                label,
                label_corner,
                use_standard_sizes,
                end_ticks,
            )
            if output_path:
                if lzw_compression:
                    result.save(output_path, compression="tiff_lzw")
                else:
                    result.save(output_path)
            else:
                output_file = f"{folder}/{short_file_name}_cut_{k}.{extension}"
                if lzw_compression:
                    result.save(output_file, compression="tiff_lzw")
                else:
                    result.save(output_file)
        except:
            print("Error during procession ", full_file_name, ".")

    elif extension == "png" or extension == "PNG":
        try:
            img = png2np(full_file_name)
            chunks = extract_png_chunks(full_file_name)  # = tif_tags for png
            img_cropped = cut_panel(img, chunks)
            result = draw_bar(
                img_cropped,
                chunks,
                lan,
                rect_color,
                corner,
                label,
                label_corner,
                use_standard_sizes,
                end_ticks,
            )
            if output_path:
                result.save(output_path)
            else:
                result.save(f"{folder}/{short_file_name}_cut_{k}.{extension}")
        except:
            print("Error during procession ", full_file_name, ".")

    else:
        print(
            "File ",
            short_file_name,
            extension,
            " extension isn't 'tif' ('tiff'); it can't be processed.",
        )
