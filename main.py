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

bpt_update_counter_dict:dict = {}
UPDATE_THRESHOLD = 4

NOTIFY_OFF = -1

tz_command_instructions:str = "\nUse the command `!tz` to specify your island time zone!\n\nYou can use `!tz E`, `!tz C`, `!tz M`, `!tz P` for Eastern, Central, Mountain and Pacific US timezones respectively.\n\n" \
            "Just a one time thing, I promise! :smile: \n\n" \
            "If your timezone is something else, please use `!tz` followed by whichever value matches from this list: <https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568>\n"


bot = commands.Bot(command_prefix='!')


####################### FUNCTIONS #######################

def get_user_data_object(ctx:commands.Context)->dict:
    author_id: str = str(ctx.message.author.id)
    server_id: str = str(ctx.guild.id)
    author_username: str = str(ctx.message.author)

    user_info_path: str = "./Users/{}/{}.json".format(server_id, author_id)
    user_info: dict = load_user_info(user_info_path)

    return { "author_id": author_id, "server_id": server_id, "author_username": author_username, "user_info_path": user_info_path, "user_info": user_info }

def check_if_first_time_user(user_info_path:str)->bool:
    return not os.path.exists(user_info_path)


def get_max_potential_price(user_info:dict) -> tuple:
    user_fc_data:list = update_forecast_data(user_info)
    max_value:int = 0
    max_value_index:int = -1
    if len(user_fc_data) >= NUM_RESULT_ELEMENTS:
        for time_index in range(0, NUM_RESULT_ELEMENTS):
            if user_fc_data[time_index][MAX_INDEX] > max_value:
                max_value = user_fc_data[time_index][MAX_INDEX]
                max_value_index = time_index

    return max_value, max_value_index

def time_index_to_text(index:int)->str:
    result = ['Mon Morning', 'Mon Afternoon', 'Tue Morning', 'Tue Afternoon', 'Wed Morning', 'Wed Afternoon', 'Thu Morning', 'Thu Afternoon', 'Fri Morning', 'Fri Afternoon', 'Sat Morning', 'Sat Afternoon']
    return result[index] if 0 <= index < NUM_RESULT_ELEMENTS else ""

def tally(server_id:str,get_potential_fc:bool=False,full_update:bool=False) ->str:
    global current_date_no
    global is_sunday

    result:str = "\n"
    today_entries:dict = {}
    old_entries:dict = {}
    fc_entries:dict = {}
    json_files: list = glob.glob("./Users/{}/*.json".format(server_id))


    for file in json_files:
        x:list = []
        y:list = []



        user_info:dict = load_user_info(file)

        same_day: bool = False
        minutes_remaining_till_noon: int = 0
        minutes_remaining_till_cranny_event:int = 0

        current_user_datetime: datetime = datetime.now(pytz.timezone(user_info["timezone"]))
        noon_user_datetime: datetime = current_user_datetime.replace(hour=12, minute=0, second=0, microsecond=0)
        open_user_datetime: datetime = current_user_datetime.replace(hour=8, minute=0, second=0, microsecond=0)
        close_user_datetime:datetime = current_user_datetime.replace(hour=22, minute=0, second=0, microsecond=0)

        before_noon:bool = current_user_datetime < noon_user_datetime
        is_cranny_open:bool = open_user_datetime < current_user_datetime < close_user_datetime

        if before_noon:
            minutes_remaining_till_noon =  int((noon_user_datetime - current_user_datetime).total_seconds() / 60)

            if is_cranny_open:
                minutes_remaining_till_cranny_event = 0
            else:
                minutes_remaining_till_cranny_event = int((open_user_datetime - current_user_datetime).total_seconds() / 60)

        else:

            if is_cranny_open:
                minutes_remaining_till_cranny_event = int((close_user_datetime - current_user_datetime).total_seconds() / 60)
            else:
                minutes_remaining_till_cranny_event = 0

        if "prices" in user_info and "username" in user_info:
            prices:dict = user_info["prices"]
            if len(prices) > 0:
                last_price:int = list(prices.values())[-1]
                days_since:int = current_date_no - int(list(prices.keys())[-1][:ZFILL_LEN])
                last_report_m:str = list(prices.keys())[-1][-1]

                if last_report_m.isdigit():
                    last_report_m = '' # Sunday price report

                if days_since == 0:
                    same_day = True
                    today_entries[user_info["username"]] = (last_price, days_since, last_report_m, before_noon, same_day, minutes_remaining_till_noon, is_cranny_open, minutes_remaining_till_cranny_event)
                elif days_since < 5:
                    old_entries[user_info["username"]] = (last_price, days_since, last_report_m, before_noon, same_day, minutes_remaining_till_noon, is_cranny_open, minutes_remaining_till_cranny_event)

            if get_potential_fc:
                user_max_price = get_max_potential_price(user_info)
                if user_max_price[1] != -1 and user_max_price[0] > 300: # Add to fc_entries assuming we found a valid max potential
                    fc_entries[user_info["username"]] = user_max_price

    sort_reverse:bool = not is_sunday
    sorted_today_entries:dict = {k: v for k, v in sorted(today_entries.items(), key=lambda item: item[1][0], reverse=sort_reverse)}
    sorted_old_entries: dict = {k: v for k, v in sorted(old_entries.items(), key=lambda item: item[1][0], reverse=sort_reverse)}
    sorted_fc_entries:dict = {k: v for k, v in sorted(fc_entries.items(), key=lambda item: item[1][0], reverse=sort_reverse)}

    if not is_sunday:
        result += "\n~\t~\t~\t~\t~\t~ :sunrise: **PRICES REPORTED TODAY** :sunrise: ~\t~\t~\t~\t~\t~\n"

        for entry in sorted_today_entries.items():
            result += entry[0] + ": __**" + str(entry[1][0])
            #entry_same_day:bool = entry[1][4]
            entry_before_noon:bool = entry[1][3]
            entry_last_report_m:str = entry[1][2]
            entry_minutes_remaining_till_noon:int = entry[1][5]
            entry_is_cranny_open:bool = entry[1][6]
            entry_minutes_remaining_till_cranny_event:int = entry[1][7]
            if entry_before_noon and entry_last_report_m == 'A':
                result += "**__ (this morning, accurate for " + str(entry_minutes_remaining_till_noon) + " more minutes :white_check_mark: ) \n"
            elif not entry_before_noon and entry_last_report_m == 'A':
                result += "**__ (this morning, needs PM update :exclamation: ) \n"
            elif not entry_before_noon and entry_last_report_m == 'P':
                if entry_is_cranny_open:
                    result += "**__ (this afternoon, store closes in " + str(entry_minutes_remaining_till_cranny_event) + " minutes :white_check_mark: ) \n"
                else:
                    result += "**__ (this afternoon :white_check_mark:, but Nook's Cranny is closed now! :exclamation:)\n"

            else:
                result += "**__ \n"
                #TODO FIXME This scenario can happen when price is reported and there's ambiguity on what day it is
                #result = "Whoops, something went wrong, please let @eccentricb know"
                #return result

        if full_update:
            result += "--------------------------------------\n_Prices reported earlier days:_"
            result += '\n```'
            for entry in sorted_old_entries.items():
                result += entry[0] + ": " + str(entry[1][0]) + ' (' + str(entry[1][1]) + 'd ago)\t'
            result += '\n```'

            if get_potential_fc and len(fc_entries) > 0:
                result += "\n\n~\t~\t~\t~\t~\t~ :crystal_ball: **NOOK TURNIP PRICE FORECAST** :crystal_ball: ~\t~\t~\t~\t~\t~\n_Highest Maximum Potential Future Prices This Week:_\n"

                MAX_FC_ENTRIES:int = 20
                fc_count:int = 0
                for entry in sorted_fc_entries.items():
                    if fc_count < MAX_FC_ENTRIES:
                        result += entry[0] + ": **" + str(entry[1][0]) + '** as soon as ' + time_index_to_text(entry[1][1]) + '... \n'
                        fc_count += 1
                    else:
                        break

    else:
        result += "-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\t-\n~\t~\t~\t:sunrise: SUNDAY DAISY MAE PRICES REPORTED TODAY :sunrise: ~\t~\t~\t\n"

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


def check_who_to_notify(json_glob:str, price:int)->str:
    global NOTIFY_OFF

    result:str = "\n:bell: :"
    json_files: list = glob.glob(json_glob)
    count_notify:int = 0

    for file in json_files:
        user_info: dict = load_user_info(file)
        user_id:str = file[-23:-5] #Hacky way to get the user id
        
        if "notify" in user_info and "username_discord" in user_info:
            if user_info["notify"] != NOTIFY_OFF and price >= user_info["notify"]:
                result += " <@" + user_id + "> "
                count_notify += 1

    return "" if count_notify == 0 else result + "\n\n"

def genplot(json_glob:str, get_forecast_data:bool=False, all_data:bool=False) -> bool:
    global current_date_no

    success:bool = True

    json_files:list = glob.glob(json_glob)
    plt.clf()

    xaxis: list = []
    xtickslist:list = []

    past_sunday_date_no:int = current_date_no - ((current_date_no - 3) % 7)

    min_range:int = past_sunday_date_no+1 if not all_data else 4
    max_range:int = past_sunday_date_no+7 if not all_data else current_date_no
    for i in range(min_range, max_range):

        if not (all_data and (i - 3) % 7 == 0):
            xaxis.append(str(i).zfill(ZFILL_LEN) + 'A')
            xaxis.append(str(i).zfill(ZFILL_LEN) + 'P')
            xtickslist.append(str(i).zfill(ZFILL_LEN) + 'A')

    for file in json_files:
        x:list = []
        y:list = []
        xp:list = []
        yp_min:list = []
        yp_max:list = []

        user_info: dict = load_user_info(file)

        forecast_data: list = update_forecast_data(user_info) if get_forecast_data else []
        forecast_data_size: int = len(forecast_data)

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
                plt.xticks(xtickslist, ['Mo','Tu','W','Th','F','Sa'] if not all_data else [''])

                plt.xlabel('day')
                plt.ylabel('BPT')
                plt.title('Stalk Market\nTurnip Prices')
                plt.legend()
                #plt.show()

                plt.savefig('result.png')
            else:
                success = False
    return success


def generate_forecast_data(user_info:dict)->bool:

    user_entry_this_week:bool = False

    if "prices" in user_info:
        gen_cmd: str = str(TURNIP_FORECAST_CMD) + ' ' + price_forecast_csv_path + ' '

        prices: dict = user_info["prices"]
        past_sunday_date_no: int = current_date_no - ((current_date_no - 3) % 7)

        # Add Daisy Mae sell price
        daisy_mae_price:int = 0
        past_sunday_date_key:str = str(past_sunday_date_no).zfill(ZFILL_LEN)

        if past_sunday_date_key in prices:
            daisy_mae_price = prices[past_sunday_date_key]
            user_entry_this_week = True

        gen_cmd += str(daisy_mae_price) + ' '

        # Add Nook buy price data
        for i in range(past_sunday_date_no + 1, past_sunday_date_no + 7):
            am_key:str = str(i).zfill(ZFILL_LEN) + 'A'
            am_value:int = 0
            pm_key:str = str(i).zfill(ZFILL_LEN) + 'P'
            pm_value:int = 0

            if am_key in prices:
                am_value = prices[am_key]
                user_entry_this_week = True
            if pm_key in prices:
                pm_value = prices[pm_key]
                user_entry_this_week = True

            gen_cmd += str(am_value) + ' ' + str(pm_value) + ' '

        if user_entry_this_week:
            try:
                os.system(gen_cmd)
            except Exception as e:
                print("Error calling command in generate_forecast_data " + str(e))

    else:
        print("Error reading price data from user_info")

    return user_entry_this_week


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
            csvfile.close()
            return []

        csvfile.close()

    #for res in result:
    #    print(res)

    return result


def update_forecast_data(user_info:dict)->list:
    if generate_forecast_data(user_info):
        return read_forecast_data()
    else:
        return []


def load_user_info(file_path:str)->dict:
    user_info: dict = {"username": "None", "username_discord": "None", "timezone": default_timezone, "notify": NOTIFY_OFF, "prices": {}}
    try:
        with open(file_path, 'r') as jsonfile:
            user_info = json.load(jsonfile)
            jsonfile.close()
    except Exception as e:
        print("load_user_info error occurred loading json " + str(e))

    return user_info


def update_user_json(user_info:dict, user_info_path:str):
    with open(user_info_path, 'w+') as wf:
        json.dump(user_info, wf, indent=4, sort_keys=True)
        wf.close()


def update_user_data(user_data:dict):
    if "user_info" in user_data and "user_info_path" in user_data:
        update_user_json(user_data["user_info"], user_data["user_info_path"])


####################### HELP TEXT #######################

def name_help_text()->str:
    return "\nSpecify the name of your island using `!name`\n\n" \
            "For example if the name of your island is Myland, use `!name Myland` and your island name will be updated accordingly!\n\n" \
            "If your island name has a space in it you'll need to use the quotation marks around the name eg `!name ❝My land❞`\n\n"


def bpt_help_text()->str:
    return "\nThere are handful of things you can do with the bpt command! :smile: \n\n" \
                "Use `!bpt <n>` to specify the current Bells Per Turnip (BPT) rate on your island, whether it's Sunday and you're buying from Daisy Mae or it's M-Sa and you're selling your turnips to the Nooks!\n\n" \
                "For example `!bpt 99` tells the bot that the current BPT rate at that time is 99 bells per turnip!\n\n" \
                "You can also use `!bpt check` to check in on the current prices and times to determine if the prices are still accurate at the moment as well as how much time is left until it changes\n\n"


def notify_help_txt()->str:
    return "\nUse the `!notify <n>` command to be notified by the bot when someone reports prices above a certain BPT rate! :bell: :chart_with_upwards_trend:\n\n" \
                "For example if you wish to be notified when someone reports prices above 300 BPT, use the command `!notify 300` and you will be tagged by the bot when someone reports prices at or above that level!\n\n" \
                ":no_bell: If you wish to turn off notifications from this bot, you can use the command `!notify off`"

####################### BOT COMMAND CALLS #######################

@bot.command(name=COMMAND+"notify", help='Updates username for user')
async def set_notify(ctx:commands.Context, arg:str=""):
    if len(arg) == 0 or arg.lower() == "help":
        await ctx.send(notify_help_txt())
    else:
        user_data:dict = get_user_data_object(ctx)
        user_info:dict = user_data["user_info"]
        has_updated_info:bool = False

        if check_if_first_time_user(user_data["user_info_path"]):
            await ctx.send("Hello there! I see this is your first time using JVTurnipPriceBot! I just need one thing before I can work with you! \n" + tz_command_instructions)
        elif arg.lower() == "off" or arg.lower() == "stop":
            user_info["notify"] = NOTIFY_OFF
            has_updated_info = True
            await ctx.send("Got it, I've turned off price notify alerts for you :no_bell: :thumbsup:")
        elif arg.isdigit():
            user_info["notify"] = int(arg)
            has_updated_info = True
            await ctx.send("Okay, I will ping you when someone's prices go at or above {}! :bell: :thumbsup:".format(arg))

        if has_updated_info:
            user_info["username_discord"] = user_data["author_username"]
            update_user_data(user_data)



@bot.command(name=COMMAND+"change", help='Changes price for this week')
async def set_past_price(ctx:commands.Context, arg:str=""):
    #TODO
    if len(arg) == 0 or arg.lower() == "help":
        await ctx.send("\nChange or set the price entry for an earlier time for this week by using `!change <Time>:<Price> command!\n\n" \
                       "<Time> format is first 3 letters of day of week, dash, then AM/PM. DO NOT USE SPACES!\n\n" \
                       "For example if you want to set the Monday evening price to 85, enter the command `!change Mon-PM:85`")



@bot.command(name=COMMAND+"name", help='Updates username for user')
async def set_username(ctx:commands.Context, arg:str=""):
    user_data:dict = get_user_data_object(ctx)
    new_username:str = arg

    if len(new_username) == 0:
        await ctx.send(":exclamation: Oh hey you didn't follow with a name! :exclamation: \n"+name_help_text())
    elif new_username.upper() == "HELP":
        await ctx.send(name_help_text())
    elif len(new_username) > 32:
        await ctx.send(":exclamation: Well there's a mouthful! :exclamation:\nSorry, I can only store up to 32 characters for the island name (AC limits to 10 but I've given you some legroom)\nTry again!")
    else:
        user_data["user_info"]["username"] = new_username
        update_user_data(user_data)
        await ctx.send(":thumbsup: Got it! I've updated your island's name to **" + new_username + "**!\n\n"+bpt_help_text())


@bot.command(name=COMMAND+"tz", help='Updates timezone for user')
async def set_tz(ctx:commands.Context, arg:str):
    global tz_command_instructions

    user_data:dict = get_user_data_object(ctx)
    user_info:dict = user_data["user_info"]

    time_zone_str: str = arg

    arg_upper:str = arg.upper()
    if arg_upper == "E":
        time_zone_str = "America/New_York"
    elif arg_upper == "C":
        time_zone_str = "America/Chicago"
    elif arg_upper == "M":
        time_zone_str = "America/Denver"
    elif arg_upper == "P":
        time_zone_str = "America/Los_Angeles"

    if time_zone_str in pytz.all_timezones:
        user_info["timezone"] = time_zone_str

        update_user_data(user_data)

        await ctx.send("Okay! I've updated " + user_info["username"] + "'s time zone to " + time_zone_str + "! :thumbsup:\nNext you can set your island name!\n"+name_help_text())
    else:
        await ctx.send(":exclamation: Sorry I couldn't find a valid time zone for what you entered :exclamation: \n" + tz_command_instructions)



@bot.command(name=COMMAND.upper()+"BPT", help='Stores the Bells Per Turnip for the user')
async def bptcap_proc(ctx:commands.Context, arg:str):
    await bpt_proc(ctx, arg)


@bot.command(name=COMMAND+"bpt", help='Stores the Bells Per Turnip for the user')
async def bpt_proc(ctx:commands.Context, arg:str):
    global current_date_no
    global is_sunday
    global DAYZERO
    global UPDATE_THRESHOLD
    global tz_command_instructions
    global bpt_update_counter_dict

    server_id:str = str(ctx.guild.id)

    update_count:int = 0
    do_full_update:bool = False

    # Every so often print additional price information including entries from earlier this week and forecast data
    if server_id in bpt_update_counter_dict:
        update_count = bpt_update_counter_dict[server_id] + 1
        if update_count >= UPDATE_THRESHOLD:
            update_count = 0
            do_full_update = True

    user_data_path:str = "./Users/{}".format(server_id)
    if not os.path.exists(user_data_path):
        os.mkdir(user_data_path)

    user_data: dict = get_user_data_object(ctx)
    user_info_path: str = user_data["user_info_path"]
    user_info: dict = user_data["user_info"]
    first_time_user: bool = check_if_first_time_user(user_info_path)

    if first_time_user:
        await ctx.send("Hello there! I see this is your first time using JVTurnipPriceBot! I just need one thing before I can work with you! \n" + tz_command_instructions)

    else:
        current_date_no = datetime.now(pytz.timezone(user_info["timezone"])).timetuple().tm_yday - DAYZERO
        is_sunday = datetime.now(pytz.timezone(user_info["timezone"])).weekday() == 6
        server_glob_path:str = "./Users/{}/*.json".format(server_id)

        if arg.lower() == "chart" or arg.lower() == "charts" or arg.lower() == "graph" or arg.lower() == "plot":
            #TODO differentiate chart "me" vs chart "all"
            genplot(server_glob_path)
            await ctx.send(file=discord.File('result.png'))
        elif arg.lower() == "help":
            await ctx.send(bpt_help_text())
        elif arg.lower() == "history":
            genplot(user_info_path, get_forecast_data=False, all_data=True)
            await ctx.send(file=discord.File('result.png'))
        elif arg.lower() == "check":
            await ctx.send(tally(server_id, full_update=do_full_update))
            update_count = 0
        elif arg.isdigit():

            current_user_datetime:datetime = datetime.now(pytz.timezone(user_info["timezone"]))
            noon_user_datetime:datetime = current_user_datetime.replace(hour=12,minute=0)

            m_letter:str = 'A' if current_user_datetime < noon_user_datetime else 'P'
            if is_sunday:
                m_letter = ''

            # Write user price data back to json file
            user_info["prices"][str(current_date_no).zfill(ZFILL_LEN)+m_letter] = int(arg)
            update_user_json(user_info, user_info_path)

            if not is_sunday:
                # Generate forecast data, create graph, send tally with resulting graph
                genplot(user_info_path, get_forecast_data=True)
                user_max_price:tuple = get_max_potential_price(user_info)
                message_txt:str = "Cool, got the bpt rate of **" + arg + "** for " + user_info["username"] + "!\n"

                if user_max_price[1] >= 0:
                    message_txt += "Your Nook's maximum potential bpt rate this week is :crystal_ball: **" \
                                   + str(user_max_price[0]) + "** bells per turnip as early as {}".format(time_index_to_text(user_max_price[1])) + "!\n"
                else:
                    message_txt += "Couldn't get forecast data for your island, sorry!! :man_bowing: \n"

                await ctx.send(message_txt + check_who_to_notify(server_glob_path, int(arg)), file=discord.File('result.png'))
                # TODO Optimize this so that it doesn't call update_forecast_data twice!
                await ctx.send(tally(server_id, True, do_full_update))
            else:
                await ctx.send(tally(server_id, False, do_full_update))

    bpt_update_counter_dict[server_id] = update_count

bot.run(TOKEN)
