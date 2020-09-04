"""
Class to deal with properties data (coordinates, values, etc)

COMPLETE THIS

"""

import pandas as pd
import numpy as np

import rasterio
from pyproj import Proj, Transformer
import pyproj

def transform_coordinates(df_coordinates,input_proj,lng_col,lat_col):
    ''' Transforms geo-coordinates to the reference used in this package (epsg:4326).
    
    Parameters
    ----------

    df_coordinates : pandas DataFrame
        pandas DataFrame with coordinates data (id, latitude and longitude)
    input_proj: string
        name of the coordinate system of the input coordinates (eg. 'epsg:4326')
    lng_col: string
        name of the column containing longitudes
    lat_col: string
        name of the column containing latitudes

    Returns
    -------

    df_coordinates : pandas DataFrame
        data frame with two extra columns: Latitude and Longitude in EPSG:4326 coordinates
        The default fill value.
    '''
    
    transformer = Transformer.from_crs(crs_from=input_proj, crs_to="epsg:4326")
    latlng = df_coordinates.apply(lambda row: transformer.transform(row[lng_col],row[lat_col]), axis=1)

    df_coordinates['latitude'] = np.transpose(latlng.tolist())[0]
    df_coordinates['longitude'] = np.transpose(latlng.tolist())[1]
    
    return df_coordinates


def is_in_map(df_coordinates,map_path):
    ''' Checks if properties are located inside a map.'''
    bbox = rasterio.open(maps[1].map_path).bounds
    inside =  [1 if (lng > bbox.left and lng < bbox.right and lat > bbox.bottom and lat < bbox.top) else 0 \
                for (lng,lat) in zip(df_coordinates.longitude,df_coordinates.latitude)]
    return inside
                             

def check_geo_zone(df_coordinates,maps_list,geo_zone_list):
    ''' Given a list of maps, checks in which map each property fall.
    
    Parameters
    ----------

    df_coordinates : pandas DataFrame
        data frame with coordinates data (id, latitude and longitude)
    df_maps: list
        path to geo reference (geotiff) file
        
    Returns
    -------
    
    df_coordinates: pandas DataFrame
        pandas data frame with extra column (geo_zone)
    '''
    
    is_in_map = []
                                      
    for i,map_file in enumerate(maps_list):
        bbox = rasterio.open(map_file).bounds
        is_in_map.append([1 if (lng > bbox.left and lng < bbox.right and lat > bbox.bottom and lat < bbox.top) \
                        else 0 \
                        for (lng,lat) in zip(df_coordinates.longitude,df_coordinates.latitude)]
                        )
    
    if np.any(np.sum(is_in_map, axis=0) > 1):
        print('Some properties are in more than one map. Merge maps.')
        return 0
    else:
        df_coordinates['geo_zone'] = 0
        for i,zone in enumerate(geo_zone_list):
            print(zone)
            if np.sum(is_in_map[i]) > 0:
                df_coordinates.geo_zone[np.where(is_in_map[i])[0]] = zone
            else:
                print(f'No properties {zone}')
                pass
        return df_coordinates
                          

def degrees_to_meter(degrees,raster_file):
    # we need a reference point
    ref_lng, ref_lat = raster_file.lnglat()
    # epsg:3035 has as units meters instead of degrees
    x1, y1 = pyproj.transform(Proj(init=raster_file.crs),Proj(init='epsg:3035'), ref_lng, ref_lat)
    x2, y2 = pyproj.transform(Proj(init=raster_file.crs),Proj(init='epsg:3035'), ref_lng, ref_lat+degrees)
    x3, y3 = pyproj.transform(Proj(init=raster_file.crs),Proj(init='epsg:3035'), ref_lng+degrees, ref_lat)
    distance2_m = np.sqrt((x2-x1)**2 + (y2-y1)**2)
    distance3_m = np.sqrt((x3-x1)**2 + (y3-y1)**2)
    return np.mean((distance2_m,distance3_m))


def meter_to_degree(meters,raster_file):
    # we need a reference point
    x1, y1 = raster_file.lnglat()
    ref_lng, ref_lat = pyproj.transform(Proj(init=raster_file.crs),Proj(init='epsg:3035'), x1, y1)
    # epsg:3035 has as units meters instead of degrees
    x2, y2 = pyproj.transform(Proj(init='epsg:3035'), Proj(init=raster_file.crs), ref_lng, ref_lat+meters)
    x3, y3 = pyproj.transform(Proj(init='epsg:3035'), Proj(init=raster_file.crs), ref_lng+meters, ref_lat)
    distance2_m = np.sqrt((x2-x1)**2 + (y2-y1)**2)
    distance3_m = np.sqrt((x3-x1)**2 + (y3-y1)**2)
    return np.mean((distance2_m,distance3_m))


def meter_to_pixel(meters,raster_file):
    degrees = meter_to_degree(meters,raster_file)
    return degrees/np.mean(raster_file.res)
                          

def latlng_to_xy(raster_map, points_lat, points_lng):
    '''Return image (array) indices correspoonding to a coordinate point'''
    xy = [raster_map.index(lng_p,lat_p) for lat_p,lng_p in zip(points_lat,points_lng)]
    x = np.transpose(xy)[1]
    y = np.transpose(xy)[0]
    return x, y
        
        
def check_value_in_radius(img,point_x,point_y,radius):
    '''Test if point is outside image, giving a marging for the radius (or the cropping fails)'''
    if point_x < radius or point_y < radius or point_x > img.shape[1]-radius or point_y > img.shape[0]-radius:
        return np.nan
    
    else:
        cropped_img = img[point_y-radius:point_y+radius,point_x-radius:point_x+radius]
        y,x = np.ogrid[-radius:radius,-radius:radius]
        mask = x**2 + y**2 <= radius**2
        return np.int(np.nansum(cropped_img[mask]) > 0)
    
    

def check_columns_for_app(df_prop, latitude_col='latitude',longitude_col='longitude',prop_value_col='prop_value',geo_zone_col='geo_zone'):

    df_prop.rename(columns={latitude_col: 'latitude', longitude_col: 'longitude'},inplace=True)
    
    if prop_value_col is not None:
        df_prop.rename(columns={prop_value_col: 'prop_value'},inplace=True)
    else:
        df_prop['prop_value'] = 1e6
        
        
    if geo_zone_col is not None:
        df_prop.rename(columns={geo_zone_col: 'geo_zone'},inplace=True)
    else:
        df_prop['geo_zone'] = 'undefined'
    
    if 'at_risk' not in df_prop.columns:
        df_prop['at_risk'] = -1
        
    print(f'There are {df_prop.AC_KEY.duplicated().sum()} duplicated AC_KEYs')
    
    return df_prop