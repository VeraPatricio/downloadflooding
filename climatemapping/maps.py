"""
Class to deal with maps

COMPLETE THIS

"""
import numpy as np
import re

from owslib.wms import WebMapService
import rasterio
from rasterio import merge
from pyproj import Proj, transform
import pyproj


##### Download functions - Not working in Danske Bank's computer ######

def check_layer_number(url,layer_name):
    '''Given a WMS url and a checks what is the number of the layer in layer_name'''
    wms = WebMapService(url+'/WmsServer')
    layer_titles = [wms[layer_nb].title for layer_nb in wms.contents]
    layer_number = [layer_nb for layer_nb in wms.contents if re.match(layer_name,wms[layer_nb].title) ]
    return layer_number


def download_map(url,layer,size,crs,output_dir):
    ''' Download maps and save them as georeferenced images (i.e. with metadata refering to their coordinates)

    Parameters
    ----------

    url: string
        url to the WmsServer
    layer: int
        number of the layer to be downloaded
    size: (int,int)
       size of the image
    crs: string
        CRS of the image (check first waht is available)
   output_dir: string
       directory where to save image
   '''
   
    wms = WebMapService(url+'/WmsServer')
    srs = wms[layer].crsOptions
    bbox = wms[layer].boundingBoxWGS84 
    output_name = wms[layer].title
        
    if crs not in srs:
        print('CRS not available (available options:)',srs)
        pass
        
    # Get the image from the server
    img = wms.getmap(layers=[layer],
                     styles=['default'],
                     srs=crs,
                     bbox=bbox,
                     size=size,
                     transparent=True,
                     format='image/png8'
                    )
    
    # Save the array as an image
    print('Saved', output_dir+output_name+'.png')
    with open(output_dir+output_name+'.png', 'wb') as out:
        out.write(img.read())
       
    # Re-open the same image in rasterio to georeference it
    img_array = rasterio.open(output_dir+output_name+'.png').read().squeeze()
    img_shape = img_array.shape
    dst_transform = rasterio.transform.from_bounds(west = bbox[0],
                                                   south = bbox[1],
                                                   east = bbox[2],
                                                   north = bbox[3],
                                                   width=img_shape[1], height=img_shape[0])
    # Write it out to a file.
    with rasterio.open(output_dir+output_name+'_georef.png', 'w', driver='GTiff',
                       width=img_shape[1], height=img_shape[0],
                       count=1, dtype=np.uint8, #nodata=0,
                       transform=dst_transform, crs=crs,
                       compress='lzw') as dst:
        dst.write(img_array.astype(np.uint8), indexes=1)
        
    return output_dir+output_name+'.png',bbox
        
        
        
########## Dealing with map images #################
def merge_maps(map_list,resolution):
    
    maps = [rasterio.open(map_path) for map_path in map_list]
    new_image, new_transform = merge.merge(maps,res=resolution,nodata=0)
    return new_image, new_transform

def save_merged_map(map_list, resolution, out_file):
   
    mosaic_img, mosaic_transform = merge_maps(map_list,resolution=resolution)
        
    out_meta = rasterio.open(map_list[0]).meta.copy()
    out_meta.update({"height": mosaic_img.shape[1],
                     "width": mosaic_img.shape[2],
                     "transform": mosaic_transform,
                     'compress':'lzw'
                     }
                    )
    with open(out_file+'.png', 'wb') as out:
        out.write(mosaic_img)
        
    with rasterio.open(out_file+'_georef.png', "w", **out_meta) as dest:
        dest.write(mosaic_img)
        return dest.bounds
    
    return mosaic_transform
