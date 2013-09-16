#!/usr/bin/env python

import os
import re
import sys
import urllib
import yaml

import reportlab.pdfgen.canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import reportlab.lib.utils
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter


from PIL import Image

# get_defaults()
#_________________________________________________________________________________________
def get_defaults():
    config = {
        'margin': {
            'top':      1.0*inch,
            'bottom':   1.5*inch,
            'left':     1.0*inch,
            'right':    1.0*inch,
        },

        'pagesize': {
            'width':    letter[0],
            'height':   letter[1],
        },

        'caption': {
            'size':   72,
            'font':  'Times-Roman',
            'color': [0.6, 0.6, 0.6],
        },

        'padding': 0.25*inch,

        'layouts': [
            [['x']],

            [['x','x']],

            [['x','x','x']],

            [['x','x'],
             ['x','x']],

             [['x','x'],
            ['x','x','x']],

            [['x','x','x'],
             ['x','x','x']],

              [['x','x','x'],
             ['x','x','x','x']],

            [['x','x','x','x'],
             ['x','x','x','x']],

            [['x','x','x'],
             ['x','x','x'],
             ['x','x','x']],

            [['x','x','x','x','x'],
             ['x','x','x','x','x']],
        ],
    }

    return config


# read_config()
#_________________________________________________________________________________________
def read_config(config_filename):
    if not os.path.exists(config_filename):
        raise IOError, 'Config file "' + config_filename + '" not found'

    with open(config_filename) as f:
        config_updates = yaml.safe_load(f)

    config = get_defaults()
    config.update(config_updates)
    return config


# get_canvas()
#_________________________________________________________________________________________
def get_canvas(config):
    name = config['name']
    pagesize = (config['pagesize']['width'], config['pagesize']['height'])

    #register fonts
    if 'fonts' in config:
        for font in config['fonts']:
            pdfmetrics.registerFont(TTFont(font['name'], font['file']))

    canvas = reportlab.pdfgen.canvas.Canvas(name, pagesize=pagesize)
    return canvas, name


# place_caption()
#_________________________________________________________________________________________
def place_caption(canvas, config, caption):
    caption_size  = caption.get('size',  config['caption']['size'])
    caption_font  = caption.get('font',  config['caption']['font'])
    caption_color = caption.get('color', config['caption']['color'])

    canvas.setFont(caption_font, caption_size)
    canvas.setFillColorRGB(*caption_color)

    margin   = config['margin']
    boxwidth = config['pagesize']['width'] - margin['left'] - margin['right']
    center_x = margin['left'] + boxwidth*0.5

    #asc_des = pdfmetrics.getAscentDescent(caption_font, fontSize=caption_size)
    #caption_height = asc_des[0] - asc_des[1]

    #descenders may extend below margin['bottom']
    canvas.drawCentredString(center_x, margin['bottom'], caption['text'])

    return caption_size #not taking descenders into account


#download_image()
#_________________________________________________________________________________________
def download_image(url):
    image_cache_dir = 'image_cache'
    if not os.path.exists(image_cache_dir):
        os.mkdir(image_cache_dir)

    match = re.match('https?://openclipart.org/detail/(.*)', url)
    if match:
        detail_path = match.group(1).rstrip('/')
        url = 'http://openclipart.org/image/600px/svg_to_png/' + detail_path + '.png'
    elif not url.endswith('.png'):
        raise IOError, 'Image URL must either end with .png or point to an openclipart details page'

    file_path = os.path.join(image_cache_dir, re.sub('^https?://', '', url))

    if not os.path.exists(file_path):
        parent_dirs = os.path.dirname(file_path)
        if not os.path.exists(parent_dirs):
            os.makedirs(parent_dirs)
        print '    downloading', url
        urllib.urlretrieve(url, file_path)
    else:
        print '    already downloaded', url

    return file_path


#place_images()
#_________________________________________________________________________________________
def place_images(canvas, config, page, caption_height):
    file_path = download_image(page['image']['url'])

    image = Image.open(file_path)
    #print image.format, image.size, image.mode

    margin   = config['margin']
    box_w = config['pagesize']['width']  - margin['left'] - margin['right']
    box_h = config['pagesize']['height'] - margin['top'] - margin['bottom'] - caption_height

    num_images = page['image'].get('number', 1)
    layout = config['layouts'][num_images-1]

    num_rows = len(layout)
    num_cols = 1
    for row in layout:
        if len(row) > num_cols:
            num_cols = len(row)

    box_w_split = box_w / num_cols
    box_h_split = box_h / num_rows

    percent_w = float(image.size[0]) / box_w_split
    percent_h = float(image.size[1]) / box_h_split

    if percent_w < percent_h:
        fit_percent = percent_h
    else:
        fit_percent = percent_w

    rescale_w = float(image.size[0]) / fit_percent
    rescale_h = float(image.size[1]) / fit_percent

    #print 'percent', percent_w, percent_h
    #print 'box', box_w, box_h
    #print 'w, h', rescale_w, rescale_h

    bottom_adjust = (box_h - rescale_h*num_rows) * 0.5
    bottom = margin['bottom'] + caption_height + bottom_adjust

    i=num_rows-1
    for row in layout:
        j=0
        for col in row:
            left_adjust = (box_w - rescale_w*len(row)) * 0.5
            left   = margin['left'] + left_adjust
            #print 'x,y', left+(box_w_split*j), bottom+(box_h_split*i)

            #need mask='auto' or transparent png will show up all black
            canvas.drawImage(file_path, left+(rescale_w*j), bottom+(rescale_h*i), width=rescale_w, height=rescale_h, mask='auto')
            j+=1
        i-=1


# make_page
#_________________________________________________________________________________________
def make_page(canvas, config, page):
    #print '    ', page
    caption_height = place_caption(canvas, config, page['caption'])

    if 'image' in page:
        place_images(canvas, config, page, caption_height)

    canvas.showPage()


# make_pages
#_________________________________________________________________________________________
def make_pages(canvas, config):
    i = 1
    for page in config['pages']:
        print '  creating page', i
        make_page(canvas, config, page)
        i+=1

# main()
#_________________________________________________________________________________________
if len(sys.argv) > 1:
    config_filename = sys.argv[1]
else:
    config_filename = 'sample.yaml'

config = read_config(config_filename)
#print 'config:', config

canvas, output_name = get_canvas(config)

print 'Starting', output_name

make_pages(canvas, config)

canvas.save()
print 'Saved', output_name
