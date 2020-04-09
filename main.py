import matplotlib.pyplot as plt
import csv
import os
import discord
from dotenv import load_dotenv
from discord.ext import commands
from datetime import datetime
import glob
import json
import pytz

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
COMMAND = os.getenv('DISCORD_CMD')
TURNIP_FORECAST_CMD = os.getenv('TURNIP_FORECAST_CMD')

DAYZERO = int(os.getenv('DAY_ZERO'))
ZFILL_LEN = 4
default_timezone:str = "America/New_York"
current_date_no: int = -1
is_sunday:bool = False
MOD_SUNDAY = 2

price_forecast_csv_path:str = "turnip_forecast.csv"
NUM_CSV_ELEMENTS = 2 * 2 * 6 + 1 # pattern, Mon AM min, Mon AM max, Mon PM min, Mon PM max, Tue AM min...
NUM_RESULT_ELEMENTS = 2 * 6 # [ [ Mon AM min, Mon AM max ] , [ Mon PM min, Mon PM max ], ... ]
MIN_INDEX = 0
MAX_INDEX = 1


bot = commands.Bot(command_prefix='!')


def tally() ->str:
    global current_date_no
    global is_sunday

    result:str = "Last updated Turnip Prices (Bells per Turnip):\n"
    today_entries:dict = {}
    old_entries:dict = {}
    json_files: list = glob.glob(".\\Users\\*.json")

    for file in json_files:
        x:list = []
        y:list = []

        with open(file, 'r') as jsonfile:
            user_info:dict = json.load(jsonfile)

            same_day: bool = False
            minutes_remaining_till_noon: int = 0

            current_user_datetime: datetime = datetime.now(pytz.timezone(user_info["timezone"]))
            noon_user_datetime: datetime = current_user_datetime.replace(hour=12, minute=0, second=0, microsecond=0)

            before_noon:bool = current_user_datetime < noon_user_datetime
            if before_noon:
                minutes_remaining_till_noon =  int((noon_user_datetime - current_user_datetime).total_seconds() / 60)

            if "prices" in user_info:
                prices:dict = user_info["prices"]
                if len(prices) > 0:
                    last_price:int = list(prices.values())[-1]
                    days_since:int = current_date_no - int(list(prices.keys())[-1][:ZFILL_LEN])
                    last_report_m:str = list(prices.keys())[-1][-1]

                    if last_report_m.isdigit():
                        last_report_m = '' # Sunday price report

                    if days_since == 0:
                        same_day = True
                        today_entries[user_info["username"]] = (last_price, days_since, last_report_m, before_noon, same_day, minutes_remaining_till_noon)
                    elif days_since < 7:
                        old_entries[user_info["username"]] = (last_price, days_since, last_report_m, before_noon, same_day, minutes_remaining_till_noon)

    sort_reverse:bool = not is_sunday
    sorted_today_entries:dict = {k: v for k, v in sorted(today_entries.items(), key=lambda item: item[1][0], reverse=sort_reverse)}
    sorted_old_entries: dict = {k: v for k, v in sorted(old_entries.items(), key=lambda item: item[1][0], reverse=sort_reverse)}

    if not is_sunday:
        result += "--------------------------------------------------------- \n~ ~ ~ :sunrise: PRICES REPORTED TODAY :sunrise: ~ ~ ~\n"

        for entry in sorted_today_entries.items():
            result += entry[0] + ": **" + str(entry[1][0])
            #entry_same_day:bool = entry[1][4]
            entry_before_noon:bool = entry[1][3]
            entry_last_report_m:str = entry[1][2]
            entry_minutes_remaining_till_noon:int = entry[1][5]
            if entry_before_noon and entry_last_report_m == 'A':
                result += "** (this morning, accurate for " + str(entry_minutes_remaining_till_noon) + " more minutes :white_check_mark: ) \n"
            elif not entry_before_noon and entry_last_report_m == 'A':
                result += "** (reported this morning, needs PM update :exclamation: ) \n"
            elif not entry_before_noon and entry_last_report_m == 'P':
                result += "** (reported this afternoon, accurate for rest of day :white_check_mark: ) \n"
            else:
                result = "Something went wrong, please let @eccentricb know"
                return result

        result += "--------------------------------------------------------- \n"
        for entry in sorted_old_entries.items():
            result += entry[0] + ": **" + str(entry[1][0]) + '** (' + str(entry[1][1]) + ' day(s) ago)\n'
    else:
        result += "--------------------------------------------------------- \n~ ~ ~ :sunrise: SUNDAY DAISY MAE PRICES REPORTED TODAY :sunrise: ~ ~ ~\n"

        for entry in sorted_today_entries.items():
            result += entry[0] + ": **" + str(entry[1][0])
            entry_before_noon: bool = entry[1][3]
            entry_minutes_remaining_till_noon: int = entry[1][5]

            if entry_before_noon:
                result += "** (available for " + str(entry_minutes_remaining_till_noon) + " more minutes :white_check_mark: ) \n"
            else:
                result += "** (Daisy Mae have left already :exclamation: ) \n"

    return result


def get_first_key_value_this_week(xaxis:list, prices:dict)->str:
    for key in xaxis:
        if key in list(prices.keys()):
            return key
    return ""


def genplot(json_glob:str, forecast_data:list = []) -> bool:
    global current_date_no

    success:bool = True

    json_files:list = glob.glob(json_glob)
    plt.clf()

    xaxis: list = []
    xtickslist:list = []

    past_sunday_date_no:int = current_date_no - ((current_date_no - 3) % 7)

    forecast_data_size: int = len(forecast_data)

    for i in range(past_sunday_date_no+1, past_sunday_date_no+7):

        xaxis.append(str(i).zfill(ZFILL_LEN) + 'A')
        xaxis.append(str(i).zfill(ZFILL_LEN) + 'P')
        xtickslist.append(str(i).zfill(ZFILL_LEN) + 'A')

    for file in json_files:
        x:list = []
        y:list = []
        xp:list = []
        yp_min:list = []
        yp_max:list = []
        user_info: dict = {}

        try:
            with open(file, 'r') as jsonfile:
                user_info:dict = json.load(jsonfile)
        except Exception as e:
            print("genplot error occurred loading json " + str(e))

        if "prices" in user_info:
            prices:dict = user_info["prices"]
            #ordered_price_dates:dict = {k: v for k, v in sorted(prices.items(), key=lambda item: item[0])}

            if len(prices.items()) > 0:

                #prices_list:list = list(prices.values())
                prices_list_keys:list = list(prices.keys())
                first_key_value_this_week:str = get_first_key_value_this_week(xaxis, prices)

                if first_key_value_this_week != "":

                    price = int(prices[first_key_value_this_week])

                    time_index:int = 0
                    prev_xtick:str = ""
                    xtick_index:int = 0
                    last_price_entry:str = prices_list_keys[-1]
                    reached_first_entry:bool = False

                    while xtick_index < len(xaxis):

                        xtick = xaxis[xtick_index]

                        if xtick in prices:
                            reached_first_entry = True
                            price = int(prices[xtick])

                            x.append(xtick)
                            y.append(price)
                        elif not reached_first_entry:
                            x.append(xtick)
                            y.append(price)
                        elif forecast_data_size > 0:
                            if prev_xtick == last_price_entry:
                                xp.append(prev_xtick)
                                yp_min.append(price)
                                yp_max.append(price)

                                # Lame way of preventing step forward
                                time_index -= 1
                                xtick_index -= 1
                            elif time_index < forecast_data_size and len(xp) > 0 and int(xtick[:ZFILL_LEN]) >= current_date_no:
                                # Plot price prediction
                                xp.append(xtick)
                                yp_min.append(forecast_data[time_index][MIN_INDEX])
                                yp_max.append(forecast_data[time_index][MAX_INDEX])

                        time_index += 1
                        xtick_index += 1
                        prev_xtick = xtick
                else: # first_key_value_this_week is empty
                    success = False

            if success:
                plt.plot(x, y, label=user_info["username"])

                if forecast_data_size > 0 and len(xp) > 0:
                    plt.plot(xp, yp_min, 'g--')
                    plt.plot(xp, yp_max, 'g--')
                    plt.fill_between(xp, yp_min, yp_max, alpha=0.3)

                #plt.xticks(xtickslist, list(range(len(xtickslist))))
                plt.xticks(xtickslist, ['Mo','Tu','W','Th','F','Sa'])

                plt.xlabel('day')
                plt.ylabel('BPT')
                plt.title('Stalk Market\nTurnip Prices')
                plt.legend()
                #plt.show()

                plt.savefig('result.png')
            else:
                success = False
    return success


def generate_forecast_data(user_info:dict):

    if "prices" in user_info:
        gen_cmd: str = str(TURNIP_FORECAST_CMD) + ' ' + price_forecast_csv_path + ' '

        prices: dict = user_info["prices"]
        past_sunday_date_no: int = current_date_no - ((current_date_no - 3) % 7)

        # Add Daisy Mae sell price
        daisy_mae_price:int = 0
        past_sunday_date_key:str = str(past_sunday_date_no).zfill(ZFILL_LEN)

        if past_sunday_date_key in prices:
            daisy_mae_price = prices[past_sunday_date_key]

        gen_cmd += str(daisy_mae_price) + ' '

        # Add Nook buy price data
        for i in range(past_sunday_date_no + 1, past_sunday_date_no + 7):
            am_key:str = str(i).zfill(ZFILL_LEN) + 'A'
            am_value:int = 0
            pm_key:str = str(i).zfill(ZFILL_LEN) + 'P'
            pm_value:int = 0

            if am_key in prices:
                am_value = prices[am_key]
            if pm_key in prices:
                pm_value = prices[pm_key]

            gen_cmd += str(am_value) + ' ' + str(pm_value) + ' '

        try:
            os.system(gen_cmd)
        except Exception as e:
            print("Error calling command in generate_forecast_data " + str(e))

    else:
        print("Error reading price data from user_info")


def read_forecast_data()->list:
    fields = []
    rows = []
    result = []

    # First initialize function output list
    for index in range(0, NUM_RESULT_ELEMENTS):
        result.append([10000, 0])
        #result[index][MIN_INDEX] = 10000
        #result[index][MAX_INDEX] = 0

    # Next, open and parse csv file
    with open(price_forecast_csv_path, 'r') as csvfile:
        csvreader = csv.reader(csvfile)

        # Each row contains a possible pattern scenario
        for row in csvreader:
            rows.append(row)


        if len(rows) > 0:
            for row in rows:
                csv_row_index:int = 1
                result_index:int = 0

                while csv_row_index < NUM_CSV_ELEMENTS and result_index < NUM_RESULT_ELEMENTS:

                    cur_min:int = int(row[csv_row_index+MIN_INDEX])
                    cur_max:int = int(row[csv_row_index+MAX_INDEX])

                    # Set new min value if needed
                    if cur_min < result[result_index][MIN_INDEX]:
                        result[result_index][MIN_INDEX] = cur_min

                    # Set new max value if needed
                    if cur_max > result[result_index][MAX_INDEX]:
                        result[result_index][MAX_INDEX] = cur_max

                    csv_row_index += 2
                    result_index += 1
        else:
            # No forecast data available
            return []

    #for res in result:
    #    print(res)

    return result

def update_forecast_data(user_info:dict)->list:
    generate_forecast_data(user_info)
    return read_forecast_data()


@bot.command(name=COMMAND.upper(), help='Stores the Bells Per Turnip for the user')
async def bptcap_proc(ctx, arg:str):
    await bpt_proc(ctx, arg)


@bot.command(name=COMMAND, help='Stores the Bells Per Turnip for the user')
async def bpt_proc(ctx, arg:str):
    global current_date_no
    global is_sunday
    global default_timezone
    global DAYZERO

    current_date_no = datetime.now(pytz.timezone(default_timezone)).timetuple().tm_yday - DAYZERO
    is_sunday = datetime.now(pytz.timezone(default_timezone)).weekday() == 6

    author_username:str = str(ctx.message.author)
    author_id:str = str(ctx.message.author.id)

    if arg.lower() == "chart" or arg.lower() == "charts" or arg.lower() == "graph" or arg.lower() == "plot":
        #TODO differentiate chart "me" vs chart "all"
        genplot(".\\Users\\*.json")
        await ctx.send(file=discord.File('result.png'))
    elif arg.lower() == "check":
        await ctx.send(tally())
    elif arg.isdigit():

        user_info:dict = {"username": author_username, "timezone": default_timezone, "prices": { } }
        user_info_path:str = ".\\Users\\{}.json".format(author_id)

        if os.path.exists(user_info_path):
            with open(user_info_path) as f:
                user_info = json.load(f)

        current_user_datetime:datetime = datetime.now(pytz.timezone(user_info["timezone"]))
        noon_user_datetime:datetime = current_user_datetime.replace(hour=12,minute=0)

        m_letter:str = 'A' if current_user_datetime < noon_user_datetime else 'P'
        if is_sunday:
            m_letter = ''

        # Write user price data back to json file
        user_info["prices"][str(current_date_no).zfill(ZFILL_LEN)+m_letter] = int(arg)
        with open(user_info_path, 'w+') as wf:
            json.dump(user_info, wf, indent = 4, sort_keys=True)

        if not is_sunday:
            # Generate forecast data, create graph, send tally with resulting graph
            forecast_data:list = update_forecast_data(user_info)
            genplot(user_info_path, forecast_data)
            await ctx.send(tally(), file=discord.File('result.png'))
        else:
            await ctx.send(tally())

bot.run(TOKEN)



