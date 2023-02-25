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
network = Network()

font_thumb = bitmap_font.load_font('fonts/tom-thumb.bdf')

mtgroup = displayio.Group()
wxgroup = displayio.Group()
lbl_greet = Label(font=terminalio.FONT, x=0, y=3, color=0xFF6600)
lbl_temp = Label(font=terminalio.FONT, x=18, y=15, color=0xBB56FF)
lbl_feel = Label(font=font_thumb, x=8, y=18, color=0xBB56FF)
lbl_hi = Label(font=font_thumb, x=32, y=13)
lbl_lo = Label(font=font_thumb, x=32, y=20)
lbl_time = Label(font=terminalio.FONT, x=0, y=27, color=0xBB56FF)
wxgroup.append(lbl_greet)
wxgroup.append(lbl_temp)
wxgroup.append(lbl_feel)
wxgroup.append(lbl_hi)
wxgroup.append(lbl_lo)
wxgroup.append(lbl_time)
wxgroup.append(displayio.Group()) # for temp graph
wxgroup.append(displayio.Group()) # for rain graph

def update_weather(value, show_today):
    now = time.localtime(time.time() + timezone_offset)
    if show_today:
        for_day = now.tm_wday
        rcolor = 0x5D2B7F
    else:
        for_day = (now.tm_wday + 1) % 7  # tomorrow
        rcolor = 0xBB56FF
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
    lbl_feel.text = '{:2d}'.format(round(value['current']['feels_like']))
    lbl_hi.text = '{:2d}'.format(round(hi))
    lbl_lo.text = '{:2d}'.format(round(lo))
    lbl_hi.color = rcolor
    lbl_lo.color = rcolor

    xoffset = 64 - len(temps)
    tempgroup = displayio.Group(x=xoffset, y=11)
    raingroup = displayio.Group(x=xoffset, y=22)
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
        tempgroup.append(Line(i, 10-n, i, 10-b, rcolor))

    for i, pop in enumerate(poppx):
        raingroup.append(Line(i, 10-pop, i, 10, 0x1E3559))

localtime_refresh = None
weather_refresh = None
weather_hour = None
timezone_offset = None
now = None

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

    # Query the weather, when:
    # - it's the first run, or
    # - the data is older than 10 minutes, or
    # - it's the top of the hour
    if ((not weather_refresh) or
        (time.monotonic() - weather_refresh) > 600 or
        (now and weather_hour != now.tm_hour)):
        try:
            value = network.fetch_data(DATA_SOURCE, json_path=([],))
            timezone_offset = value['timezone_offset']
            now = time.localtime(time.time() + timezone_offset)
            update_weather(value, show_today=now.tm_hour < 17)
            weather_refresh = time.monotonic()
            weather_hour = now.tm_hour
        except RuntimeError as e:
            print('Error fetching weather:', e)
            continue

    now_unix = time.time()
    now = time.localtime(now_unix + timezone_offset)

    # TODO: Sleep smarter.
    if ((now.tm_hour == 22 and now.tm_min >= 45) or
        (now.tm_hour == 23) or
        (now.tm_hour < 7)):
        display.show(mtgroup)
        time.sleep(60)
    else:
      if now.tm_hour < 12:
          lbl_greet.text = [
              'Kali mera!',  # Monday
              'Bonjour!',
              "G'morning!",
              'Bom dia!',
              'Co-brkfst!',
              'Swan time!',
              'Buongiorno!',
          ][now.tm_wday]
      elif now.tm_hour < 17:
          days = ((secrets['event_time'] - now_unix) // (60 * 60 * 24)) + 1
          lbl_greet.text = '{:3d} to {}!'.format(days, secrets['event_name'])
      elif now.tm_hour < 19:
          lbl_greet.text = 'Happy hour!'
      elif now.tm_hour < 20:
          lbl_greet.text = 'Dinnertime!'
      elif now.tm_hour < 22:
          lbl_greet.text = 'Wind down!'
      elif now.tm_hour == 22 and now.tm_min < 45:
          lbl_greet.text = 'Tuck in!'
      else:
          lbl_greet.text = 'Helo world!'
      lbl_time.text = "{:2d}:{:02d}".format(now.tm_hour%12, now.tm_min)
      display.show(wxgroup)
      time.sleep(1)
