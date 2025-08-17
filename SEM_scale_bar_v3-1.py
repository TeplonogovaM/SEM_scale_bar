# %%
import numpy as np
import os
import tifffile   # DOI: 10.5281/zenodo.6795860
from PIL import Image, ImageDraw, ImageFont
import FreeSimpleGUI as sg

# %%
def get_scale(tif_tags):
    pixel_size = 0 # for debugging
    if 'CZ_SEM' in tif_tags:
        try: #for Zeiss images
            length = tif_tags['CZ_SEM']['ap_image_pixel_size'][2] 
            if length == "nm":
                pixel_size = float(
                    tif_tags['CZ_SEM']['ap_image_pixel_size'][1] / 1000)  # microns per pixel
            else: #length == 'pm':
                pixel_size = float(
                    tif_tags['CZ_SEM']['ap_image_pixel_size'][1] / 1000000)  # microns per pixel
        except: #for LEO images
            n = tif_tags['ImageWidth']/1024 # to recalculate image resolution in meter per pixel
            pixel_size = float(
                    tif_tags['CZ_SEM'][''][3]*1000000)/n # microns per pixel
    
    elif '50431' in tif_tags:
        text = tif_tags['50431'].split()  # for Tescan images
        for j in range(len(text)):
            find_pixel_size = str(text[j]).find("PixelSizeX")
            if find_pixel_size != -1:
                pixel_size = float(str(text[j]).split('=')[1].strip("'")) * 1000000  # microns per pixel
                break #?
    else:
        print('Unknown metadata format')
    
    return pixel_size

def cut_panel(img, tif_tags):
    height, width = img.shape[:2]
    if 'CZ_SEM' in tif_tags:
        i = 0
        if 'ap_image_pixel_size' in tif_tags['CZ_SEM']: #for Zeiss images
            for row in img:
                if np.all(row[2:row.size - 3] == img[-2][2:row.size - 3]): # img[-2] is a lower part of the infopanel frame; we want to find the upper part of the frame
                    strip_pixel_size = height - i
                    break
                i += 1
        else: # for LEO images
            black_row = np.zeros(width-6)
            for row in img:
                if np.all(black_row == row[3:row.size - 3]):
                    strip_pixel_size = height - i
                    break
                i += 1

    elif '50431' in tif_tags:
        text = tif_tags['50431'].split()      # for Tescan images
        for j in range(len(text)):
            start_strip = str(text[j]).find("ImageStripSize") #Tescan writes the infopanel height (in pixels) to the metadata parameter "ImageStripSize"
            if start_strip != -1:
                strip_pixel_size = int(str(text[j]).split('=')[1].strip("'"))
                break
        
    else:
        print("Unknown metadata format. Only Zeiss, Tescan or LEO SEM initial images can be processed.")
    
    h = height-strip_pixel_size
    crop = img[0:h, 0:width]

    return crop

def tif2np(tif, name):
      img = tif.pages[0].asarray()
      if len(img.shape) > 2:
        img=img.mean(axis = 0)
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

def get_bar(img, pixel_size, lang):
    _, width = img.shape[:2]
    bar = width*pixel_size/6 # bar lenght is about 1/6 of image width, microns, not an integer
    if bar >=1:
        if bar >= 100:
            bar = round(bar/100)*100
        elif 100 > bar >= 10:
            bar = round(bar/10)*10
        else:
            bar = round(bar)
        bar_pixel_size = bar/pixel_size
        if lang == "Russian":
            scale = "мкм"
        else:
            scale = "\u03BCm"

    else:
        if bar >= 0.1:
            bar = round(bar*10)*100
        else:
            bar = round(bar*100)*10
        bar_pixel_size = bar/(pixel_size*1000)
        if lang == "Russian":
            scale = "нм"
        else:
            scale = "nm"
    
    return(bar, bar_pixel_size, scale)

def draw_bar(img, tif_tags, lang, rect_color, corner):
        img1 = Image.fromarray(img)
        img1 = img1.convert('RGB')
        img2 = ImageDraw.Draw(img1)
        height = img.shape[0]

        pixel_size = get_scale(tif_tags)
        bar_data = get_bar(img, pixel_size, lang)
        bar = round(bar_data[1])
        scale_text = f"{bar_data[0]} {bar_data[2]}"

        n = img.shape[1]/2048 # make font size and bar size match image size
        font_size = round(80*n)
        font = ImageFont.truetype("arial.ttf", font_size)
        text_length = img2.textlength(scale_text, font=font)
        bbox = img2.textbbox((0, 0), scale_text, font=font)
        text_height = bbox[3] - bbox[1]

        rect_height = text_height + round(65*n)
        rect_width = bar + round(40*n) #bar width, pixels

        if rect_color == "black":
            bar_color = "white"
        else:
            bar_color = "black"

        if corner == 'right':
            width = img.shape[1]
            # draw filled rectangle at the down right corner
            img2.rectangle([(width - rect_width, height - rect_height),       # left upside corner
                        (width, height)],                                 # right downside corner
                        fill = rect_color,
                        outline = rect_color
                        )
        else:
            width = 0
            # draw filled rectangle at the down left corner
            img2.rectangle([(0, height - rect_height),       # left upside corner
                        (rect_width, height)],               # right downside corner
                        fill = rect_color,
                        outline = rect_color
                        )

        # draw contrast bar in the rectangle
        img2.line([(abs(width - bar - round(20*n)), height - round(30*n)),
                (abs(width - round(20*n)), height - round(30*n))],
                fill = bar_color,
                width = round(20*n)
        )

        x = abs(width - rect_width/2) - text_length/2
        y = height -  rect_height

        # draw scale text
        img2.text((x, y),
                scale_text,
                fill = bar_color,
                font = ImageFont.truetype("arial.ttf", font_size)
        )
        return(img1)

# %%
# read full file path, process file (read tif metadata, cut panel, draw scale bar) and save result
def process_file(full_file_name, lan, rect_color, corner, k):
    folder, filename_ext = os.path.split(full_file_name)
    short_file_name, extension = os.path.splitext(filename_ext)
    _, extension = extension.split('.')
    if extension == 'tif' or extension == "TIF":
        try:
            tif = tifffile.TiffFile(full_file_name)
            img = tif2np(tif,full_file_name)
            tif_tags = get_tags_from_tiff(tif)
            img_cropped = cut_panel(img,tif_tags)
            result = draw_bar(img_cropped, tif_tags, lan, rect_color, corner)
            result.save(f"{folder}/{short_file_name}_cut_{k}.{extension}")
        except:
            print("Error during procession ", full_file_name, ".")
    else:
            print("File ", full_file_name, " extension isn't 'tif' ('tiff'); file can't be processed.")

# %%
sg.theme('NeonYellow1') # window colours (theme); 'NeonGreen1' is fine, also

# All the stuff inside the window:
layout = [  [sg.B('Choose folder with SEM images'), sg.B('Choose one SEM image')],
          
            [sg.T("Background colour:"), sg.B('white', button_color=('orange', 'gray'), tooltip='Default'), 
             sg.B('black', button_color=(sg.theme_background_color()))],

            [sg.T("Language:"), sg.B('English', button_color=('orange', 'gray'), tooltip='Default'),
             sg.B('Russian', button_color=(sg.theme_background_color()))],

            [sg.T("Location:"), sg.B('left', button_color=(sg.theme_background_color())),
             sg.B('right', button_color=('orange', 'gray'), tooltip='Default')],
            
            [sg.Push(), sg.B('Process'), sg.Push()],

            [sg.Output(size=(60, 10))],

            [sg.Push(), sg.B('Exit'), sg.Push()],
        ]

# Create the window:
window = sg.Window('SEM scale bar - version 3.1', layout)

# default parameters
rect_color = 'white'
language = 'English'
corner = 'right'

# fix start buttons (to change their color futher)
chosen_color = 'white'
chosen_language = 'English'
chosen_corner = 'right'

k = 1 # index for processed images
folder = None
file = None

# %%
# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read() #text_input = values[0]

    # get the path to the folder to process all images in a folder:
    if event == 'Choose folder with SEM images':
        folder = sg.popup_get_folder('Select a folder', no_window=True)

    if event == 'Choose one SEM image':
        file = sg.popup_get_file('Select an image', no_window=True)

    # ask user about colour of background box
    if event in ['white', 'black']:
        rect_color = event
        # Reset the color of the previously chosen button
        if chosen_color:
            window[chosen_color].update(button_color=(sg.theme_background_color()))
        # Highlight the newly chosen button
        window[event].update(button_color=('orange', 'gray')) # Change text color to white, background to blue
        chosen_color = event # Update the chosen button key
    
    # ask user about language of the scale
    if event in ['English', 'Russian']:
        language = event
        if chosen_language:
            window[chosen_language].update(button_color=(sg.theme_background_color()))
        window[event].update(button_color=('orange', 'gray'))
        chosen_language = event

    # ask user about place for the scale bar
    if event in ['left', 'right']: #== 'right':
        corner = event
        if chosen_corner:
            window[chosen_corner].update(button_color=(sg.theme_background_color()))
        window[event].update(button_color=('orange', 'gray'))
        chosen_corner = event

    if event == 'Process':
        if folder is not None:
            for root, dirs, files in os.walk(folder):
                for i, file in enumerate(files):
                    full_file_name = root + '/' + file
                    process_file(full_file_name, language, rect_color, corner, k)
            k +=1
            folder = None
            print('Process is complete. Check initial folder.')
        elif file is not None:
            process_file(file, language, rect_color, corner, k)
            k +=1
            file = None
            print('Process is complete. Check initial folder.')
        else:
            print('Choose folder or an image.')
        window.refresh()

    # if user closes window or clicks Exit
    if event == sg.WIN_CLOSED or event == 'Exit':
        break

window.close()


