import os

from sem_scale_bar.core import build_output_path, process_file


def run_gui():
    import FreeSimpleGUI as sg

    sg.set_options(font=("DejaVu Sans", 12))
    sg.theme("NeonYellow1")  # window colours (theme); 'NeonGreen1' is fine, also

    layout = [
        [sg.B("Choose folder with SEM images"), sg.B("Choose one SEM image")],
        [
            sg.Checkbox("Output to separate folder", key="-UseOutputDir-"),
            sg.Input(key="-OutputDir-", size=(35, 1), disabled=True),
            sg.FolderBrowse("Choose output folder", target="-OutputDir-"),
        ],
        [
            sg.T("Background colour:"),
            sg.B("white", button_color=("orange", "gray"), tooltip="Default"),
            sg.B("black", button_color=(sg.theme_background_color())),
            sg.B("transparent", button_color=(sg.theme_background_color())),
        ],
        [
            sg.T("Language:"),
            sg.B("English", button_color=("orange", "gray"), tooltip="Default"),
            sg.B("Russian", button_color=(sg.theme_background_color())),
        ],
        [
            sg.T("Location:"),
            sg.B("left", button_color=(sg.theme_background_color())),
            sg.B("right", button_color=("orange", "gray"), tooltip="Default"),
        ],
        [
            sg.T("Label on the image, e.g. 'a)' or 'B':"),
            sg.Input(size=(20, 1), key="-Label-"),
            sg.T("(can be empty)"),
        ],
        [
            sg.B("label: left", button_color=("orange", "gray"), tooltip="Default"),
            sg.B("label: right", button_color=(sg.theme_background_color())),
        ],
        [sg.Checkbox("Use standard 1-2-5 bar sizes", key="-StandardSizes-")],
        [
            sg.Checkbox(
                "Use LZW compression for TIFF outputs",
                key="-LzwCompression-",
                default=True,
            )
        ],
        [sg.Checkbox("Add end ticks to scale bar", key="-EndTicks-")],
        [sg.Push(), sg.B("Process"), sg.Push()],
        [sg.Output(size=(60, 10))],
        [sg.Push(), sg.B("Exit"), sg.Push()],
    ]

    window = sg.Window("SEM scale bar - version 4.2", layout)

    rect_color = "white"
    language = "English"
    corner = "right"
    label_corner = "left"
    label = ""
    use_standard_sizes = False
    use_output_dir = False
    lzw_compression = True
    end_ticks = False

    chosen_color = "white"
    chosen_language = "English"
    chosen_corner = "right"
    chosen_label_corner = "label: left"

    k = 1  # index for processed images
    folder = None
    file = None
    output_dir = None

    while True:
        event, values = window.read()

        if event == "Choose folder with SEM images":
            folder = sg.popup_get_folder("Select a folder", no_window=True)

        if event == "Choose one SEM image":
            file = sg.popup_get_file("Select an image", no_window=True)

        if event in ["white", "black", "transparent"]:
            rect_color = event
            if chosen_color:
                window[chosen_color].update(button_color=(sg.theme_background_color()))
            window[event].update(button_color=("orange", "gray"))
            chosen_color = event

        if event in ["English", "Russian"]:
            language = event
            if chosen_language:
                window[chosen_language].update(
                    button_color=(sg.theme_background_color())
                )
            window[event].update(button_color=("orange", "gray"))
            chosen_language = event

        if event in ["left", "right"]:
            corner = event
            if chosen_corner:
                window[chosen_corner].update(button_color=(sg.theme_background_color()))
            window[event].update(button_color=("orange", "gray"))
            chosen_corner = event

        if event in ["label: left", "label: right"]:
            label_corner = "left" if event.endswith("left") else "right"
            if chosen_label_corner:
                window[chosen_label_corner].update(
                    button_color=(sg.theme_background_color())
                )
            window[event].update(button_color=("orange", "gray"))
            chosen_label_corner = event

        try:
            label = values["-Label-"]
        except Exception:
            pass
        try:
            use_standard_sizes = values["-StandardSizes-"]
        except Exception:
            pass
        try:
            lzw_compression = values["-LzwCompression-"]
        except Exception:
            pass
        try:
            end_ticks = values["-EndTicks-"]
        except Exception:
            pass
        try:
            use_output_dir = values["-UseOutputDir-"]
        except Exception:
            pass
        try:
            output_dir = values["-OutputDir-"] or None
        except Exception:
            pass

        if event == "Process":
            if use_output_dir and not output_dir:
                print("Choose an output folder or disable the output option.")
                window.refresh()
                continue
            if folder is not None:
                input_root = folder
                for root, _, files in os.walk(folder):
                    for file_name in files:
                        full_file_name = os.path.join(root, file_name)
                        output_path = (
                            build_output_path(
                                full_file_name, output_dir, input_root
                            )
                            if use_output_dir
                            else None
                        )
                        process_file(
                            full_file_name,
                            language,
                            rect_color,
                            corner,
                            label,
                            label_corner,
                            k,
                            use_standard_sizes,
                            end_ticks,
                            lzw_compression,
                            output_path=output_path,
                        )
                k += 1
                folder = None
                if use_output_dir:
                    print("Process is complete. Check output folder.")
                else:
                    print("Process is complete. Check initial folder.")
            elif file is not None:
                input_root = os.path.dirname(file)
                output_path = (
                    build_output_path(file, output_dir, input_root)
                    if use_output_dir
                    else None
                )
                process_file(
                    file,
                    language,
                    rect_color,
                    corner,
                    label,
                    label_corner,
                    k,
                    use_standard_sizes,
                    end_ticks,
                    lzw_compression,
                    output_path=output_path,
                )
                k += 1
                file = None
                if use_output_dir:
                    print("Process is complete. Check output folder.")
                else:
                    print("Process is complete. Check initial folder.")
            else:
                print("Choose folder or image.")
            window.refresh()

        if event == sg.WIN_CLOSED or event == "Exit":
            break

    window.close()
