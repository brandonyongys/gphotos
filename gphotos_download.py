import os
import requests
import json
import pandas as pd 
from config import *
from datetime import datetime 
from gphotos import *


def remove_ignore_dates(download_date_list):
    """
    Function:   Remove all download dates that are in the ignore_date range.
    """
    for date_range in ignore_dates:
        if len(date_range) > 0:
            start_date = datetime.strptime(date_range[0], '%Y-%m-%d').date()
            end_date = datetime.strptime(date_range[1], '%Y-%m-%d').date()
            ignore_ranges = pd.date_range(start_date, end_date, freq = "d")

            download_date_list = [dt for dt in download_date_list if dt not in ignore_ranges]
    return download_date_list

def get_download_date_range(start_date, end_date):
    """
    Function:   Get a range of dates and remove dates that shouldn't be downloaded.
    start_date / end_date in the format : YYYY-MM-DD
    """
    # Download date range
    start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
    download_date_list = pd.date_range(start_date, end_date, freq = "d")

    # Remove ignore date ranges
    download_date_list = remove_ignore_dates(download_date_list)

    return download_date_list


def get_response_from_medium_api(year, month, day, creds):
    """
    Function:   Using the authorization and date, try to get responses from Google Photos API (limited to 100 media)
    """
    url = 'https://photoslibrary.googleapis.com/v1/mediaItems:search'
    
    payload = {
                  "filters": {
                    "dateFilter": {
                      "dates": [
                        {
                          "day": day,
                          "month": month,
                          "year": year
                        }
                      ]
                    }
                  }
                }
    
    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(creds.token)
    }
    
    try:
        responses = requests.request("POST", url, data=json.dumps(payload), headers=headers)
    except:
        print('Request error') 
    
    return responses


def create_items_dictionary_df():
    """
    Function:   Create an empty dictionary, key : []
    """
    items_dict = {}
    cols = ["id", "productUrl", "baseUrl", "mimeType", "creationTime", "width", "height", "fileType", "videoStatus", "filename"]
    for col in cols:
        items_dict[col] = []
    return items_dict


def get_basicData(item, items_dict):
    """
    Function:   Add on basicData to item dict
    """
    cols = ["id", "productUrl", "baseUrl", "mimeType", "filename"]
    for col in cols:
        items_dict[col].append(item[col])
    items_dict["creationTime"].append(item["mediaMetadata"]["creationTime"])

    return items_dict

def get_mediaMetadata(metadata_item, items_dict):
    """
    Function:   Add on metaData to item dict
    """
    items_dict["width"].append(metadata_item["width"])
    items_dict["height"].append(metadata_item["height"])
    items_dict["fileType"].append(identify_filetype(metadata_item))
    items_dict["videoStatus"].append(get_video_status(metadata_item))

    return items_dict

def identify_filetype(metadata_item):
    if "photo" in metadata_item.keys():
        return "photo"
    else:
        return "video"
    
def get_video_status(metadata_item):
    if "video" in metadata_item.keys():
        return metadata_item["video"]["status"]
    else:
        return None
    
def remove_unwanted_media(items_df, download_video, download_images):
    """
    Function: Remove video/image media if undesired
    """
    criteria_video = items_df["fileType"] == "video"
    if not download_video:
        items_df = items_df[~criteria_video] # Not videos 

    if not download_images:
        items_df = items_df[criteria_video] # Not images
    return items_df

def list_of_media_items(year, month, day, creds, download_video = True, download_images = True):
    '''
    Function:   Given the date, get the list of media on specified date.
                Remove unwanted media and return the df.
    Args:
        year, month, day: integer, date of the media  
        download_video, download_images: boolean
    Return:
        items_df: media items uploaded on specified date
    '''
    # Create empty key:list dict
    items_dict = create_items_dictionary_df()

    # create request for specified date
    responses = get_response_from_medium_api(year, month, day, creds)
    try:
        for item in responses.json()['mediaItems']:
            # Add on to dictionary
            items_dict = get_basicData(item, items_dict)
            items_dict = get_mediaMetadata(item["mediaMetadata"], items_dict)

        # Convert to df
        items_list_df = pd.DataFrame.from_dict(items_dict)

        # Remove unwanted media (image / video)
        items_list_df = remove_unwanted_media(items_list_df, download_video, download_images)

    except:
        items_list_df = pd.DataFrame()
        pass

    return items_list_df


def get_url(item):
    """
    Function:   Update the URL depending on filetype:
                - Photos: add in the original width and height
                - Video: add in video parameter
    """
    url = item.baseUrl
    if item["fileType"] == "photo":
        url += f"=w{item['width']}-h{item['height']}"
    else:
        url += f"=dv"

    return url


def download_media(items_list_df, destination_folder):
    """
    Function:   Download all the media in the df to the destination folder
    """
    # download all items in items_not_yet_downloaded
    for _, item in items_list_df.iterrows():
        # Get actual details
        file_name = item["filename"]
        url = get_url(item)
        response = requests.get(url)
        
        with open(os.path.join(destination_folder, file_name), 'wb') as f:
            f.write(response.content)
            f.close()


def download_my_media(client_secret_file, start_date, end_date, download_video = True, download_images = True,
                      destination_folder = './downloads/'):
    """
    Function:   Main function.
                Initialize the google api and then get the download dates (after removing dates to ignore). 
                After that, proceed to download all media (max 100 per date).
                Finally, delete the pickle file
    """
    # initialize photos api and create service
    google_photos_api = GooglePhotosApi(client_secret_file = client_secret_file)
    creds = google_photos_api.run_local_server()

    # Get download dates
    download_date_list = get_download_date_range(start_date, end_date)

    for date in download_date_list:
        # get a list with all media items for specified date (year, month, day)
        items_list_df = list_of_media_items(year = date.year, month = date.month, day = date.day, creds = creds,
                                                          download_video = download_video, download_images = download_images)

        if len(items_list_df) > 0:
            download_media(items_list_df, destination_folder = destination_folder)
            print(f'{date.day}/{date.month}/{date.year}: Downloaded {len(items_list_df)} items')

        else:
            print(f'{date.day}/{date.month}/{date.year}: No media items found for date')

    # Delete pickle file once done
    google_photos_api.delete_pickle_file()
