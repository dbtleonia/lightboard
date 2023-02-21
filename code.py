import board
import displayio
import gc
import math
import terminalio
import time
from adafruit_bitmap_font import bitmap_font
from adafruit_display_shapes.line import Line
from adafruit_display_text.label import Label
from adafruit_matrixportal.matrix import Matrix
from adafruit_matrixportal.network import Network

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print('WiFi secrets are kept in secrets.py, please add them there!')
    raise

DATA_SOURCE = '{}?lat={}&lon={}&appid={}&exclude=minutely,daily,alerts&units=imperial'.format(
    secrets['openweather_url'],
    secrets['openweather_lat'],
    secrets['openweather_lon'],
    secrets['openweather_token']
)

# --- Display setup ---
matrix = Matrix()
display = matrix.display
network = Network(status_neopixel=board.NEOPIXEL, debug=False)

font_thumb = bitmap_font.load_font('fonts/tom-thumb.bdf')

wxgroup = displayio.Group()
lbl_greet = Label(font=terminalio.FONT, x=0, y=3, color=0xFF6600, text='Helo world')
lbl_temp = Label(font=terminalio.FONT, x=18, y=15, color=0xFFCC00)
lbl_hi = Label(font=font_thumb, x=32, y=13, color=0xFFCC00)
lbl_lo = Label(font=font_thumb, x=32, y=20, color=0xFFCC00)
lbl_time = Label(font=terminalio.FONT, x=0, y=27, color=0xBB56FF)
wxgroup.append(lbl_greet)
wxgroup.append(lbl_temp)
wxgroup.append(lbl_hi)
wxgroup.append(lbl_lo)
wxgroup.append(lbl_time)
wxgroup.append(displayio.Group()) # for temp graph
wxgroup.append(displayio.Group()) # for rain graph

def update_weather(value):
    now = time.localtime(time.time() + timezone_offset)
    for_day = (now.tm_wday + 1) % 7
    temps = []
    poppx = []
    for hour in value['hourly']:
        t = time.localtime(hour['dt'] + timezone_offset)
        if t.tm_wday == for_day:
            temps.append(hour['temp'])
            poppx.append(round(hour['pop']*10))
    lo = min(temps)
    hi = max(temps)
    bucket = (hi - lo) / 10
    temppx = [max(math.ceil((temp-lo) / bucket), 1) for temp in temps]

    # TODO: Accomodate extra character for extreme temperatures.
    lbl_temp.text = '{:2d}'.format(round(value['current']['temp']))
    lbl_hi.text = '{:2d}'.format(round(hi))
    lbl_lo.text = '{:2d}'.format(round(lo))

    tempgroup = displayio.Group(x=40, y=11)
    raingroup = displayio.Group(x=40, y=22)
    wxgroup[-2] = tempgroup
    wxgroup[-1] = raingroup
    gc.collect()

    for i, n in enumerate(temppx):
        if i == 0:
            b = min(n, temppx[i+1]+1)
        elif i == len(temppx)-1:
            b = min(n, temppx[i-1]+1)
        else:
            b = min(n, temppx[i-1]+1, temppx[i+1]+1)
        tempgroup.append(Line(i, 10-n, i, 10-b, 0xFFCC00))

    for i, pop in enumerate(poppx):
        raingroup.append(Line(i, 10-pop, i, 10, 0x1E3559))

localtime_refresh = None
weather_refresh = None
timezone_offset = None
while True:
    # Only query the online time once per hour (and on first run)
    if (not localtime_refresh) or (time.monotonic() - localtime_refresh) > 3600:
        try:
            print('Getting time from internet!')
            network.get_local_time('Etc/UTC')
            localtime_refresh = time.monotonic()
        except RuntimeError as e:
            print('Error fetching time:', e)
            continue

    # Only query the weather every 10 minutes (and on first run)
    if (not weather_refresh) or (time.monotonic() - weather_refresh) > 600:
        try:
            value = network.fetch_data(DATA_SOURCE, json_path=([],))
            timezone_offset = value['timezone_offset']
            update_weather(value)
            weather_refresh = time.monotonic()
        except RuntimeError as e:
            print('Error fetching weather:', e)
            continue

    now = time.localtime(time.time() + timezone_offset)
    lbl_time.text = "{:2d}:{:02d}".format(now.tm_hour, now.tm_min)
    display.show(wxgroup)
    time.sleep(1)
