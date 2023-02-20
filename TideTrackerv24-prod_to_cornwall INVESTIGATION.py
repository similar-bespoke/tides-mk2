'''
****************************************************************
****************************************************************

                TideTracker for E-Ink Display

                        by Sam Baker

****************************************************************
****************************************************************
'''

import sys
import os
import time
import traceback
import requests, json
from io import BytesIO
import matplotlib.pyplot as plt
import numpy as np
import datetime as dt
import pandas as pd
from matplotlib.dates import DateFormatter

sys.path.append('lib')
from waveshare_epd import epd7in5_V2
from PIL import Image, ImageDraw, ImageFont

picdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'images')
icondir = os.path.join(picdir, 'icon')
fontdir = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'font')

'''
****************************************************************

Location specific info required

****************************************************************
'''


# For weather data
# Create Account on openweathermap.com and get API key
API_KEY = '09af6edfead8f35f9a22092889595955'
# Get LATITUDE and LONGITUDE of location
LATITUDE = '50.15270'
LONGITUDE = '-5.06622'
UNITS = 'metric'
# set location
LOCATION = 'St Mawes'
# Create URL for API call
BASE_URL = 'http://api.openweathermap.org/data/2.5/onecall?'
URL = BASE_URL + 'lat=' + LATITUDE + '&lon=' + LONGITUDE + '&units=' + UNITS +'&appid=' + API_KEY


# Station Code for tide data
code = '0005'

BASE_URL_T = 'https://admiraltyapi.azure-api.net/uktidalapi/api/V1/Stations/'+code + '/TidalEvents?1'
URL_T = BASE_URL_T

headers = {
    # Request headers
    'Ocp-Apim-Subscription-Key': 'b49742963f1444ac918c234bc4c2f091',
}


'''
****************************************************************

Functions and defined variables

****************************************************************
'''

# define funciton for writing image and sleeping for specified time
def write_to_screen(image, sleep_seconds):
    print('Writing to screen.') # for debugging
    # Create new blank image template matching screen resolution
    h_image = Image.new('1', (epd.width, epd.height), 255)
    # Open the template
    screen_output_file = Image.open(os.path.join(picdir, image))
    # Initialize the drawing context with template as background
    h_image.paste(screen_output_file, (0, 0))
    epd.display(epd.getbuffer(h_image))
    # Sleep
    epd.sleep() # Put screen to sleep to prevent damage
    print('Sleeping for ' + str(sleep_seconds) +'.')
    time.sleep(sleep_seconds) # Determines refresh rate on data
    epd.init() # Re-Initialize screen


# define function for displaying error
def display_error(error_source):
    # Display an error
    print('Error in the', error_source, 'request.')
    # Initialize drawing
    error_image = Image.new('1', (epd.width, epd.height), 255)
    # Initialize the drawing
    draw = ImageDraw.Draw(error_image)
    draw.text((100, 150), error_source +' ERROR', font=font50, fill=black)
    draw.text((100, 300), 'Retrying in 30 seconds', font=font22, fill=black)
    current_time = dt.datetime.now().strftime('%H:%M')
    draw.text((300, 365), 'Last Refresh: ' + str(current_time), font = font50, fill=black)
    # Save the error image
    error_image_file = 'error.png'
    error_image.save(os.path.join(picdir, error_image_file))
    # Close error image
    error_image.close()
    # Write error to screen
    write_to_screen(error_image_file, 30)


# define function for getting weather data
def getWeather(URL):
    # Ensure there are no errors with connection
    error_connect = True
    while error_connect == True:
        try:
            # HTTP request
            print('Attempting to connect to OWM.')
            response = requests.get(URL)
            print('Connection to OWM successful.')
            error_connect = None
        except:
            # Call function to display connection error
            print('Connection error.')
            display_error('CONNECTION')

    # Check status of code request
    if response.status_code == 200:
        print('Connection to Open Weather successful.')
        # get data in jason format
        data = response.json()

        with open('data.txt', 'w') as outfile:
            json.dump(data, outfile)

        return data

    else:
        # Call function to display HTTP error
        display_error('HTTP')


# last 24 hour data, add argument for start/end_date
def past24():
    # Create Station Object
    response = requests.get(URL_T, headers=headers)
    data = response.json()
    
    with open('tide_data.txt', 'w') as outfile:
          json.dump(data, outfile)    
    
    
    # Get today date string
    today = dt.datetime.now()
    #get date
    #dt.datetime.strptime(a[0]['Date'], '20%y-%m-%dT%H:%M:%S')
    # Get yesterday date string
    yesterday = today + dt.timedelta(days=1)

    
    #get data
    WaterLevel = list()
    for i in data:
        if(dt.datetime.strptime(i['DateTime'], '20%y-%m-%dT%H:%M:%S') >= yesterday):
            WaterLevel.append([dt.datetime.strptime(i['DateTime'], '20%y-%m-%dT%H:%M:%S'), i['Height']])
            return pd.DataFrame(WaterLevel,columns=['date_time','water_level'])
        else:
            WaterLevel.append([dt.datetime.strptime(i['DateTime'], '20%y-%m-%dT%H:%M:%S'), i['Height']])
    


# Plot next 24 hours of tide
def plotTide(TideData):
    
    plt.close()
    
    # Adjust data for negative values
    # minlevel = TideData['water_level'].min()
    # TideData['water_level'] = TideData['water_level'] - minlevel

    x = [i for i in range(len(TideData['water_level']))]
    x_ = np.linspace(0,max(x),100)
    yinterp = np.interp(x_, x, TideData['water_level'])
   
    #make smooth graph
    z = np.polyfit(x_, yinterp, 13)
    p = np.poly1d(z)

    cur_time = dt.datetime.now()

    #get x axis as time
    now = TideData['date_time'][0]
    
    ##print(cur_time)
    
    rg = TideData['date_time'][len(TideData)-1] - TideData['date_time'][0]
    rg = rg.total_seconds()
    x_1 = [now + dt.timedelta(seconds=rg * i/len(x_)) + diff for i in range(len(x_))]
   
   
 # Create Plot
    fig, axs = plt.subplots(figsize=(12, 4))
    
    axs.plot(x_1,(p(x_)), 'ok')
    
    # start_time = x_1.index(min(x_1, key=lambda x: abs(x - cur_time)))
    # end_time = x_1.index(min(x_1, key=lambda x: abs(x - cur_time+dt.timedelta(hours=24))))
    # axs.fill_between(x_1[start_time:end_time], p(x_[start_time:end_time]), facecolor='black')
    
    
    # axs.fill_between(x_, p(x_), facecolor='black')
    axs.grid()
    
    # add line at current times
    plt.plot([cur_time,cur_time],[6,0], color='black')
    
    plt.title('Tides over the next 24 hours', fontsize=20)
    
    date_form = DateFormatter('%H:%M')
    axs.xaxis.set_major_formatter(date_form)
    
    axs.set_xlim(right=cur_time + dt.timedelta(hours=24), left=now + dt.timedelta(hours=1))
    axs.set_ylim(top=5.75, bottom=0)
     
    #fontweight="bold",
    #axs.xaxis.set_tick_params(labelsize=20)
    #axs.yaxis.set_tick_params(labelsize=20)
    plt.savefig('images/TideLevel.png', dpi=60)
    #plt.show()


# Get High and Low tide info
def HiLo():
    # Call API
    response = requests.get(URL_T, headers=headers)
    data = response.json()
    # Get today date string
    today = dt.datetime.now() - diff
    # Get yesterday date string
    tomorrow = today + dt.timedelta(days=1)
    # Get Hi and Lo Tide info
    WaterLevel = list()
    for i in data:
        if(dt.datetime.strptime(i['DateTime'], '20%y-%m-%dT%H:%M:%S') > tomorrow):
            return pd.DataFrame(WaterLevel,columns=['date_time','predicted_wl','hi_lo'])
        else:
            WaterLevel.append([dt.datetime.strptime(i['DateTime'], '20%y-%m-%dT%H:%M:%S'), i['Height'],i['EventType'][0]])



# Set the font sizes
font15 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 15)
font20 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 20)
font22 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 22)
font30 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 30)
font35 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 35)
font50 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 50)
font60 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 60)
font100 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 100)
font160 = ImageFont.truetype(os.path.join(fontdir, 'Font.ttc'), 160)

# Set the colors
black = 'rgb(0,0,0)'
white = 'rgb(255,255,255)'
grey = 'rgb(235,235,235)'


'''
****************************************************************

Main Loop

****************************************************************
'''

# Initialize and clear screen
print('Initializing and clearing screen.')
epd = epd7in5_V2.EPD() # Create object for display functions
epd.init()
epd.Clear()

while True:
    #march start date of daylight saving
    year=dt.datetime.today().year
    month=3

    start=dt.datetime(year,month,1)
    first_w=start.isoweekday()
    saturday2=7-first_w
    start=dt.datetime(year,month,saturday2)

    #October end date of daylight saving
    year=dt.datetime.today().year
    month=10

    end=dt.datetime(year,month,1)
    first_w=end.isoweekday()
    saturday2=7-first_w
    end=dt.datetime(year,month,saturday2)

    diff = dt.timedelta(hours=0)
    if(start < dt.datetime.today() < end):
        diff = dt.timedelta(hours=1)


    # Get weather data
    data = getWeather(URL)

    # get current dict block
    current = data['current']
    # get current temp
    temp_current = current['temp']
    # get feels like
    ## feels_like = current['feels_like']
    # get humidity
    ## humidity = current['humidity']
    # get wind speed
    wind = current['wind_speed']
    # get wind direction
    wind_deg = current['wind_deg']

    # Convert wind into integers
    today_wind = wind * 100
    today_wind_int = int(today_wind)
    
    wind_dir_int = int(wind_deg)
    
    ##print(today_wind)
    ##print(today_wind_int)
    
    # Check on Force Level
    if today_wind_int in range(0, 388):
        today_force_value = 'Force 1'
    elif today_wind_int in range(389, 777):
        today_force_value = 'Force 2'
    elif today_wind_int in range(778, 1360):
        today_force_value = 'Force 3'
    elif today_wind_int in range(1361, 2137):
        today_force_value = 'Force 4'
    elif today_wind_int in range(2138, 3304):
        today_force_value = 'Force 5'
    elif today_wind_int in range(3305, 4276):
        today_force_value = 'Force 6'
    elif today_wind_int in range(4277, 5442):
        today_force_value = 'Force 7'
    elif today_wind_int in range(5443, 6609):
        today_force_value = 'Force 8'
    elif today_wind_int in range(6610, 7969):
        today_force_value = 'Force 9'
    elif today_wind_int in range(7970, 9330):
        today_force_value = 'Force 10'
    elif today_wind_int in range(9331, 10885):
        today_force_value = 'Force 11'
    else:
        today_force_value = 'Force 12'

	# Check on Wind Direction
    if wind_dir_int in range(0, 23):
        compass_dir = 'Northerly'
    elif wind_dir_int in range(24, 67):
        compass_dir = 'North Easterly'
    elif wind_dir_int in range(68, 112):
        compass_dir = 'Easterly'
    elif wind_dir_int in range(113, 157):
        compass_dir = 'South Easterly'
    elif wind_dir_int in range(158, 202):
        compass_dir = 'Southerly'
    elif wind_dir_int in range(203, 247):
        compass_dir = 'South Westerly'
    elif wind_dir_int in range(248, 292):
        compass_dir = 'Westerly'
    elif wind_dir_int in range(293, 337):
        compass_dir = 'North Westerly'
    else:
        compass_dir = 'Northerly'

    # get description
    weather = current['weather']
    report = weather[0]['description']
    # get icon url
    icon_code = weather[0]['icon']
    #icon_URL = 'http://openweathermap.org/img/wn/'+ icon_code +'@4x.png'

    # get daily dict block
    daily = data['daily']
    # get daily precip
    daily_precip_float = daily[0]['pop']
    #format daily precip
    daily_precip_percent = daily_precip_float * 100
    # get min and max temp
    daily_temp = daily[0]['temp']
    temp_max = daily_temp['max']
    temp_min = daily_temp['min']

    # Set strings to be printed to screen
    string_location = LOCATION
    string_temp_current = format(temp_current, '.0f') + u'\N{DEGREE SIGN}C'

    ## string_feels_like = 'Feels like: ' + format(feels_like, '.0f') +  u'\N{DEGREE SIGN}C'
    ## string_humidity = 'Humidity: ' + str(humidity) + '%'

    string_wind = 'Wind: ' + format(wind, '.1f') + ' m/s'
    string_wind_deg = 'Wind Dir: ' + format(wind_deg, '.1f') + u'\N{DEGREE SIGN}'
    string_report = report.title()
    string_temp_max = 'High: ' + format(temp_max, '>.0f') + u'\N{DEGREE SIGN}C'
    string_temp_min = 'Low:  ' + format(temp_min, '>.0f') + u'\N{DEGREE SIGN}C'
    string_precip_percent = 'Precip: ' + str(format(daily_precip_percent, '.0f'))  + '%'

    # NEXT DAY (TOMORROW) DATA
    # get wind speed
    nx_wind_speed = daily[1]['wind_speed']
    nx_wind_dir = daily[1]['wind_deg']
    
    # Convert wind into integer
    nx_wind = nx_wind_speed * 100
    nx_wind_int = int(nx_wind)
    nx_wind_dir_int = int(nx_wind_dir)

    ##print(nx_wind_int)

    # Check on Force Level
    if nx_wind_int in range(0, 388):
        nx_force_value = 'Force 1'
    elif nx_wind_int in range(389, 777):
        nx_force_value = 'Force 2'
    elif nx_wind_int in range(778, 1360):
        nx_force_value = 'Force 3'
    elif nx_wind_int in range(1361, 2137):
        nx_force_value = 'Force 4'
    elif nx_wind_int in range(2138, 3304):
        nx_force_value = 'Force 5'
    elif nx_wind_int in range(3305, 4276):
        nx_force_value = 'Force 6'
    elif nx_wind_int in range(4277, 5442):
        nx_force_value = 'Force 7'
    elif nx_wind_int in range(5443, 6609):
        nx_force_value = 'Force 8'
    elif nx_wind_int in range(6610, 7969):
        nx_force_value = 'Force 9'
    elif nx_wind_int in range(7970, 9330):
        nx_force_value = 'Force 10'
    elif nx_wind_int in range(9331, 10885):
        nx_force_value = 'Force 11'
    else:
        nx_force_value = 'Force 12'

    # Check on Wind Direction
    if nx_wind_dir_int in range(0, 23):
        nx_compass_dir = 'Northerly'
    elif nx_wind_dir_int in range(24, 67):
        nx_compass_dir = 'North Easterly'
    elif nx_wind_dir_int in range(68, 112):
        nx_compass_dir = 'Easterly'
    elif nx_wind_dir_int in range(113, 157):
        nx_compass_dir = 'South Easterly'
    elif nx_wind_dir_int in range(158, 202):
        nx_compass_dir = 'Southerly'
    elif nx_wind_dir_int in range(203, 247):
        nx_compass_dir = 'South Westerly'
    elif nx_wind_dir_int in range(248, 292):
        nx_compass_dir = 'Westerly'
    elif nx_wind_dir_int in range(293, 337):
        nx_compass_dir = 'North Westerly'
    else:
        nx_compass_dir = 'Northerly'

    # get min and max temp
    nx_daily_temp = daily[1]['temp']
    ## nx_temp_max = nx_daily_temp['max']
    ## nx_temp_min = nx_daily_temp['min']
    nx_temp_day = nx_daily_temp['day']

    # get daily precip
    nx_daily_precip_float = daily[1]['pop']
    #format daily precip
    nx_daily_precip_percent = nx_daily_precip_float * 100

    # NEXT NEXT DAY (DAY AFTER TOM) DATA
    
    # get wind speed
    nx_nx_wind_speed = daily[2]['wind_speed']
    nx_nx_wind_dir = daily[2]['wind_deg']
   
   
    # Convert wind into integers
    nx_nx_wind = nx_nx_wind_speed * 100
    nx_nx_wind_int = int(nx_nx_wind)
    nx_nx_wind_dir_int = int(nx_nx_wind_dir)
    
    ##print(nx_nx_wind_int)
    
    nx_nx_dt = daily[2]['dt']
    nx_nx_dow = time.strftime('%A', time.localtime(nx_nx_dt))

   # Check on Force Level
    if nx_nx_wind_int in range(0, 388):
        nx_nx_force_value = 'Force 1'
    elif nx_nx_wind_int in range(389, 777):
        nx_nx_force_value = 'Force 2'
    elif nx_nx_wind_int in range(778, 1360):
        nx_nx_force_value = 'Force 3'
    elif nx_nx_wind_int in range(1361, 2137):
        nx_nx_force_value = 'Force 4'
    elif nx_nx_wind_int in range(2138, 3304):
        nx_nx_force_value = 'Force 5'
    elif nx_nx_wind_int in range(3305, 4276):
        nx_nx_force_value = 'Force 6'
    elif nx_nx_wind_int in range(4277, 5442):
        nx_nx_force_value = 'Force 7'
    elif nx_nx_wind_int in range(5443, 6609):
        nx_nx_force_value = 'Force 8'
    elif nx_nx_wind_int in range(6610, 7969):
        nx_nx_force_value = 'Force 9'
    elif nx_nx_wind_int in range(7970, 9330):
        nx_nx_force_value = 'Force 10'
    elif nx_nx_wind_int in range(9331, 10885):
        nx_nx_force_value = 'Force 11'
    else:
        nx_nx_force_value = 'Force 12'
        
# Check on Wind Direction
    if nx_nx_wind_dir_int in range(0, 23):
        nx_nx_compass_dir = 'Northerly'
    elif nx_nx_wind_dir_int in range(24, 67):
        nx_nx_compass_dir = 'North Easterly'
    elif nx_nx_wind_dir_int in range(68, 112):
        nx_nx_compass_dir = 'Easterly'
    elif nx_nx_wind_dir_int in range(113, 157):
        nx_nx_compass_dir = 'South Easterly'
    elif nx_nx_wind_dir_int in range(158, 202):
        nx_nx_compass_dir = 'Southerly'
    elif nx_nx_wind_dir_int in range(203, 247):
        nx_nx_compass_dir = 'South Westerly'
    elif nx_nx_wind_dir_int in range(248, 292):
        nx_nx_compass_dir = 'Westerly'
    elif nx_nx_wind_dir_int in range(293, 337):
        nx_nx_compass_dir = 'North Westerly'
    else:
        nx_nx_compass_dir = 'Northerly'

    # get min and max temp
    nx_nx_daily_temp = daily[2]['temp']
    ## nx_nx_temp_max = nx_nx_daily_temp['max']
    ## nx_nx_temp_min = nx_nx_daily_temp['min']
    nx_nx_temp_day = nx_nx_daily_temp['day']
    # get daily precip
    nx_nx_daily_precip_float = daily[2]['pop']
    #format daily precip
    nx_nx_daily_precip_percent = nx_nx_daily_precip_float * 100

    # Tomorrow Forcast Strings
    ## nx_day_high = 'High: ' + format(nx_temp_max, '>.0f') + u'\N{DEGREE SIGN}C'
    ## nx_day_low = 'Low: ' + format(nx_temp_min, '>.0f') + u'\N{DEGREE SIGN}C'
    nx_temp_day = 'Temp: ' + format(nx_temp_day, '>.0f') + u'\N{DEGREE SIGN}C'
    ## nx_wind_speed = 'Wind: ' + format(nx_wind_speed, '.1f') + ' m/s'
    ## nx_wind_dir = '@ ' + format(nx_wind_dir, '.0f') + u'\N{DEGREE SIGN}'
    nx_precip_percent = 'Precip: ' + str(format(nx_daily_precip_percent, '.0f'))  + '%'
    nx_weather_icon = daily[1]['weather']
    nx_icon = nx_weather_icon[0]['icon']

    # Day after Tom Forcast Strings
    ## nx_nx_day_high = 'High: ' + format(nx_nx_temp_max, '>.0f') + u'\N{DEGREE SIGN}C'
    ## nx_nx_day_low = 'Low: ' + format(nx_nx_temp_min, '>.0f') + u'\N{DEGREE SIGN}C'
    nx_nx_temp_day = 'Temp: ' + format(nx_nx_temp_day, '>.0f') + u'\N{DEGREE SIGN}C'
    ## nx_nx_wind_speed = 'Wind: ' + format(nx_nx_wind_speed, '.1f') + ' m/s'
    ## nx_nx_wind_dir = '@ ' + format(nx_nx_wind_dir, '.0f') + u'\N{DEGREE SIGN}'
    nx_nx_precip_percent = 'Precip: ' + str(format(nx_nx_daily_precip_percent, '.0f'))  + '%'
    nx_nx_weather_icon = daily[2]['weather']
    nx_nx_icon = nx_nx_weather_icon[0]['icon']

    # Day 3

    # get wind speed
    day3_wind_speed = daily[3]['wind_speed']
    day3_wind_dir = daily[3]['wind_deg']
    
    # Convert wind into integer
    day3_wind_dir_int = int(day3_wind_dir)
    
    day3_wind = day3_wind_speed * 100
    day3_int = int(day3_wind)
    
    ##print(day3_int)
    
    day3_dt = daily[3]['dt']
    day3_dow = time.strftime('%a', time.localtime(day3_dt))

    # Check on Force Level
    if day3_int in range(0, 388):
        day3_force_value = 'F 1'
    elif day3_int in range(389, 777):
        day3_force_value = 'F 2'
    elif day3_int in range(778, 1360):
        day3_force_value = 'F 3'
    elif day3_int in range(1361, 2137):
        day3_force_value = 'F 4'
    elif day3_int in range(2138, 3304):
        day3_force_value = 'F 5'
    elif day3_int in range(3305, 4276):
        day3_force_value = 'F 6'
    elif day3_int in range(4277, 5442):
        day3_force_value = 'F 7'
    elif day3_int in range(5443, 6609):
        day3_force_value = 'F 8'
    elif day3_int in range(6610, 7969):
        day3_force_value = 'F 9'
    elif day3_int in range(7970, 9330):
        day3_force_value = 'F 10'
    elif day3_int in range(9331, 10885):
        day3_force_value = 'F 11'
    else:
        day3_force_value = 'F 12'

    # Check on Wind Direction
    if day3_wind_dir_int in range(0, 23):
        day3_compass_dir = 'Northerly'
    elif day3_wind_dir_int in range(24, 67):
        day3_compass_dir = 'North Easterly'
    elif day3_wind_dir_int in range(68, 112):
        day3_compass_dir = 'Easterly'
    elif day3_wind_dir_int in range(113, 157):
        day3_compass_dir = 'South Easterly'
    elif day3_wind_dir_int in range(158, 202):
        day3_compass_dir = 'Southerly'
    elif day3_wind_dir_int in range(203, 247):
        day3_compass_dir = 'South Westerly'
    elif day3_wind_dir_int in range(248, 292):
        day3_compass_dir = 'Westerly'
    elif day3_wind_dir_int in range(293, 337):
        day3_compass_dir = 'North Westerly'
    else:
        day3_compass_dir = 'Northerly'

    # Day 4

# get wind speed
    day4_wind_speed = daily[4]['wind_speed']
    day4_wind_dir = daily[4]['wind_deg']

    # Convert wind into integer
    day4_wind_dir_int = int(day4_wind_dir)
    
    day4_wind = day4_wind_speed * 100
    day4_int = int(day4_wind)
    
    ##print(day4_int)
        
    day4_dt = daily[4]['dt']
    day4_dow = time.strftime('%a', time.localtime(day4_dt))
    
    # Check on Force Level
    if day4_int in range(0, 388):
        day4_force_value = 'F 1'
    elif day4_int in range(389, 777):
        day4_force_value = 'F 2'
    elif day4_int in range(778, 1360):
        day4_force_value = 'F 3'
    elif day4_int in range(1361, 2137):
        day4_force_value = 'F 4'
    elif day4_int in range(2138, 3304):
        day4_force_value = 'F 5'
    elif day4_int in range(3305, 4276):
        day4_force_value = 'F 6'
    elif day4_int in range(4277, 5442):
        day4_force_value = 'F 7'
    elif day4_int in range(5443, 6609):
        day4_force_value = 'F 8'
    elif day4_int in range(6610, 7969):
        day4_force_value = 'F 9'
    elif day4_int in range(7970, 9330):
        day4_force_value = 'F 10'
    elif day4_int in range(9331, 10885):
        day4_force_value = 'F 11'
    else:
        day4_force_value = 'F 12'

    # Check on Wind Direction
    if day4_wind_dir_int in range(0, 23):
        day4_compass_dir = 'Northerly'
    elif day4_wind_dir_int in range(24, 67):
        day4_compass_dir = 'North Easterly'
    elif day4_wind_dir_int in range(68, 112):
        day4_compass_dir = 'Easterly'
    elif day4_wind_dir_int in range(113, 157):
        day4_compass_dir = 'South Easterly'
    elif day4_wind_dir_int in range(158, 202):
        day4_compass_dir = 'Southerly'
    elif day4_wind_dir_int in range(203, 247):
        day4_compass_dir = 'South Westerly'
    elif day4_wind_dir_int in range(248, 292):
        day4_compass_dir = 'Westerly'
    elif day4_wind_dir_int in range(293, 337):
        day4_compass_dir = 'North Westerly'
    else:
        day4_compass_dir = 'Northerly'

    # Day 5

    # get wind speed
    day5_wind_speed = daily[5]['wind_speed']
    day5_wind_dir = daily[5]['wind_deg']

    # Convert wind into integer
    day5_wind_dir_int = int(day5_wind_dir)
    
    day5_wind = day5_wind_speed * 100
    day5_int = int(day5_wind)
    
    ##print(day5_int)
    
    day5_dt = daily[5]['dt']
    day5_dow = time.strftime('%a', time.localtime(day5_dt))

    # Check on Force Level
    if day5_int in range(0, 388):
        day5_force_value = 'F 1'
    elif day5_int in range(389, 777):
        day5_force_value = 'F 2'
    elif day5_int in range(778, 1360):
        day5_force_value = 'F 3'
    elif day5_int in range(1361, 2137):
        day5_force_value = 'F 4'
    elif day5_int in range(2138, 3304):
        day5_force_value = 'F 5'
    elif day5_int in range(3305, 4276):
        day5_force_value = 'F 6'
    elif day5_int in range(4277, 5442):
        day5_force_value = 'F 7'
    elif day5_int in range(5443, 6609):
        day5_force_value = 'F 8'
    elif day5_int in range(6610, 7969):
        day5_force_value = 'F 9'
    elif day5_int in range(7970, 9330):
        day5_force_value = 'F 10'
    elif day5_int in range(9331, 10885):
        day5_force_value = 'F 11'
    else:
        day5_force_value = 'F 12'

    # Check on Wind Direction
    if day5_wind_dir_int in range(0, 23):
        day5_compass_dir = 'Northerly'
    elif day5_wind_dir_int in range(24, 67):
        day5_compass_dir = 'North Easterly'
    elif day5_wind_dir_int in range(68, 112):
        day5_compass_dir = 'Easterly'
    elif day5_wind_dir_int in range(113, 157):
        day5_compass_dir = 'South Easterly'
    elif day5_wind_dir_int in range(158, 202):
        day5_compass_dir = 'Southerly'
    elif day5_wind_dir_int in range(203, 247):
        day5_compass_dir = 'South Westerly'
    elif day5_wind_dir_int in range(248, 292):
        day5_compass_dir = 'Westerly'
    elif day5_wind_dir_int in range(293, 337):
        day5_compass_dir = 'North Westerly'
    else:
        day5_compass_dir = 'Northerly'

    # Day 6

    # get wind speed
    day6_wind_speed = daily[6]['wind_speed']
    day6_wind_dir = daily[6]['wind_deg']

    # Convert wind into integer
    day6_wind_dir_int = int(day6_wind_dir)
    
    day6_wind = day6_wind_speed * 100
    day6_int = int(day6_wind)
    
    ##print(day6_int)
    
    day6_dt = daily[6]['dt']
    day6_dow = time.strftime('%a', time.localtime(day6_dt))
    
    # Check on Force Level
    if day6_int in range(0, 388):
        day6_force_value = 'F 1'
    elif day6_int in range(389, 777):
        day6_force_value = 'F 2'
    elif day6_int in range(778, 1360):
        day6_force_value = 'F 3'
    elif day6_int in range(1361, 2137):
        day6_force_value = 'F 4'
    elif day6_int in range(2138, 3304):
        day6_force_value = 'F 5'
    elif day6_int in range(3305, 4276):
        day6_force_value = 'F 6'
    elif day6_int in range(4277, 5442):
        day6_force_value = 'F 7'
    elif day6_int in range(5443, 6609):
        day6_force_value = 'F 8'
    elif day6_int in range(6610, 7969):
        day6_force_value = 'F 9'
    elif day6_int in range(7970, 9330):
        day6_force_value = 'F 10'
    elif day6_int in range(9331, 10885):
        day6_force_value = 'F 11'
    else:
        day6_force_value = 'F 12'
        
    # Check on Wind Direction
    if day6_wind_dir_int in range(0, 23):
        day6_compass_dir = 'Northerly'
    elif day6_wind_dir_int in range(24, 67):
        day6_compass_dir = 'North Easterly'
    elif day6_wind_dir_int in range(68, 112):
        day6_compass_dir = 'Easterly'
    elif day6_wind_dir_int in range(113, 157):
        day6_compass_dir = 'South Easterly'
    elif day6_wind_dir_int in range(158, 202):
        day6_compass_dir = 'Southerly'
    elif day6_wind_dir_int in range(203, 247):
        day6_compass_dir = 'South Westerly'
    elif day6_wind_dir_int in range(248, 292):
        day6_compass_dir = 'Westerly'
    elif day6_wind_dir_int in range(293, 337):
        day6_compass_dir = 'North Westerly'
    else:
        day6_compass_dir = 'Northerly'

    # Day 7

    # get wind speed
    day7_wind_speed = daily[7]['wind_speed']
    day7_wind_dir = daily[7]['wind_deg']

    # Convert wind into integer
    day7_wind_dir_int = int(day7_wind_dir)
    
    day7_wind = day7_wind_speed * 100
    day7_int = int(day7_wind)
    
    ##print(day7_int)
        
    day7_dt = daily[7]['dt']
    day7_dow = time.strftime('%a', time.localtime(day7_dt))

    # Check on Force Level
    if day7_int in range(0, 388):
        day7_force_value = 'F 1'
    elif day7_int in range(389, 777):
        day7_force_value = 'F 2'
    elif day7_int in range(778, 1360):
        day7_force_value = 'F 3'
    elif day7_int in range(1361, 2137):
        day7_force_value = 'F 4'
    elif day7_int in range(2138, 3304):
        day7_force_value = 'F 5'
    elif day7_int in range(3305, 4276):
        day7_force_value = 'F 6'
    elif day7_int in range(4277, 5442):
        day7_force_value = 'F 7'
    elif day7_int in range(5443, 6609):
        day7_force_value = 'F 8'
    elif day7_int in range(6610, 7969):
        day7_force_value = 'F 9'
    elif day7_int in range(7970, 9330):
        day7_force_value = 'F 10'
    elif day7_int in range(9331, 10885):
        day7_force_value = 'F 11'
    else:
        day7_force_value = 'F 12'

    # Check on Wind Direction
    if day7_wind_dir_int in range(0, 23):
        day7_compass_dir = 'Northerly'
    elif day7_wind_dir_int in range(24, 67):
        day7_compass_dir = 'North Easterly'
    elif day7_wind_dir_int in range(68, 112):
        day7_compass_dir = 'Easterly'
    elif day7_wind_dir_int in range(113, 157):
        day7_compass_dir = 'South Easterly'
    elif day7_wind_dir_int in range(158, 202):
        day7_compass_dir = 'Southerly'
    elif day7_wind_dir_int in range(203, 247):
        day7_compass_dir = 'South Westerly'
    elif day7_wind_dir_int in range(248, 292):
        day7_compass_dir = 'Westerly'
    elif day7_wind_dir_int in range(293, 337):
        day7_compass_dir = 'North Westerly'
    else:
        day7_compass_dir = 'Northerly'


    # Last updated time
    now = dt.datetime.now()
    current_time = now.strftime("%H:%M")
    last_update_string = 'Last Updated: ' + current_time


    # Tide Data
    # Get water level
    wl_error = True
    while wl_error == True:
        try:
            WaterLevel = past24()
            wl_error = False
        except:
            display_error('Tide Data')

    plotTide(WaterLevel)


    # Open template file
    template = Image.open(os.path.join(picdir, 'template.png'))
    # Initialize the drawing context with template as background
    draw = ImageDraw.Draw(template)

    # Current weather
    ## Open icon file
    icon_file = icon_code + '.png'
    icon_image = Image.open(os.path.join(icondir, icon_file))
    icon_image = icon_image.resize((130,130))
    template.paste(icon_image, (50, 50))

    draw.text((110,10), LOCATION, font=font35, fill=black)

    # Center current weather report
    w, h = draw.textsize(string_report, font=font20)
    #print(w)
    if w > 250:
        string_report = report.title()

    center = int(120-(w/2))
    draw.text((center,175), string_report, font=font20, fill=black)

    # Data
    draw.text((240,55), string_temp_current, font=font35, fill=black)
    y = 100
    draw.text((240,y), today_force_value, font=font15, fill=black)
    draw.text((240,y+20), compass_dir, font=font15, fill=black)
    draw.text((240,y+40), string_precip_percent, font=font15, fill=black)
    draw.text((240,y+60), string_temp_max, font=font15, fill=black)
    draw.text((240,y+80), string_temp_min, font=font15, fill=black)

    draw.text((110,218), last_update_string, font=font15, fill=black)

    # Weather Forcast
    # Tomorrow
    icon_file = nx_icon + '.png'
    icon_image = Image.open(os.path.join(icondir, icon_file))
    icon_image = icon_image.resize((130,130))
    template.paste(icon_image, (385, 50))
    draw.text((400,20), 'Tomorrow', font=font22, fill=black)
    ## draw.text((415,180), nx_day_high, font=font15, fill=black)
    ## draw.text((515,180), nx_day_low, font=font15, fill=black)
    draw.text((362,180), nx_temp_day, font=font15, fill=black)
    draw.text((450,180), nx_precip_percent, font=font15, fill=black)
    draw.text((362,200), nx_force_value, font=font15, fill=black)
    draw.text((450,200), nx_compass_dir, font=font15, fill=black)
    
    # Upcoming Days Forcast

    draw.text((622,20), nx_nx_dow, font=font22, fill=black)
    x = 40

    ## draw.text((615,180), nx_nx_day_high, font=font15, fill=black)
    ## draw.text((715,180), nx_nx_day_low, font=font15, fill=black)

    draw.text((572,x+20), nx_nx_temp_day, font=font15, fill=black)
    draw.text((665,x+20), nx_nx_precip_percent, font=font15, fill=black)

    draw.text((572,x+40), nx_nx_force_value, font=font15, fill=black)
    draw.text((665,x+40), nx_nx_compass_dir, font=font15, fill=black)

    # Upcoming days wind only

    draw.text((572,x+80), day3_dow, font=font15, fill=black)
    draw.text((625,x+80), day3_force_value, font=font15, fill=black)
    draw.text((665,x+80), day3_compass_dir, font=font15, fill=black)

    draw.text((572,x+100), day4_dow, font=font15, fill=black)
    draw.text((625,x+100), day4_force_value, font=font15, fill=black)
    draw.text((665,x+100), day4_compass_dir, font=font15, fill=black)

    draw.text((572,x+120), day5_dow, font=font15, fill=black)
    draw.text((625,x+120), day5_force_value, font=font15, fill=black)
    draw.text((665,x+120), day5_compass_dir, font=font15, fill=black)

    draw.text((572,x+140), day6_dow, font=font15, fill=black)
    draw.text((625,x+140), day6_force_value, font=font15, fill=black)
    draw.text((665,x+140), day6_compass_dir, font=font15, fill=black)

    draw.text((572,x+160), day7_dow, font=font15, fill=black)
    draw.text((625,x+160), day7_force_value, font=font15, fill=black)
    draw.text((665,x+160), day7_compass_dir, font=font15, fill=black)

    ## Dividing lines
    draw.line((350,10,350,220), fill='black', width=3)
    draw.line((560,10,560,220), fill='black', width=1)

    #h = 240
    #draw.line((25, h, 775, h), fill='black', width=3)


    # Tide Info
    # Graph
    tidegraph = Image.open('images/TideLevel.png')
    template.paste(tidegraph, (125, 240))

    # Large horizontal dividing line
    h = 240
    draw.line((25, h, 775, h), fill='black', width=3)

    # Daily tide times
    draw.text((30,260), "Today's Tide", font=font22, fill=black)

    # Get tide time predictions
    hilo_error = True
    while hilo_error == True:
        try:
            hilo_daily = HiLo()
            hilo_error = False
        except:
            display_error('Tide Prediction')

    # Display tide preditions
    y_loc = 300 # starting location of list
    # Iterate over preditions
    for index, row in hilo_daily.iterrows():
        # For high tide
        if row['hi_lo'] == 'H':
            tide_time = (row['date_time']+diff).strftime("%H:%M")
            tidestr = "High: " + tide_time + ' - '+str(round(float(row['predicted_wl']),1))+'m'
        # For low tide
        elif row['hi_lo'] == 'L':
            tide_time = (row['date_time']+diff).strftime("%H:%M")
            tidestr = "Low:  " + tide_time + ' - '+str(round(float(row['predicted_wl']),1))+'m'

        # Draw to display image
        draw.text((35,y_loc), tidestr, font=font15, fill=black)
        y_loc += 25 # This bumps the next prediction down a line


    # Save the image for display as PNG
    screen_output_file = os.path.join(picdir, 'screen_output.png')
    template.save(screen_output_file)
    # Close the template file
    template.close()

    write_to_screen(screen_output_file, 3000)
    epd.Clear()
