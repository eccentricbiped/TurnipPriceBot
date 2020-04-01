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
DAYZERO = 86
ZFILL_LEN = 4
current_date_no: int = datetime.now(pytz.timezone("America/Los_Angeles")).timetuple().tm_yday - DAYZERO


bot = commands.Bot(command_prefix='!')

def tally() ->str:
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
                    if days_since == 0:
                        same_day = True
                        today_entries[user_info["username"]] = (last_price, days_since, last_report_m, before_noon, same_day, minutes_remaining_till_noon)
                    else:
                        old_entries[user_info["username"]] = (last_price, days_since, last_report_m, before_noon, same_day, minutes_remaining_till_noon)

    sorted_today_entries:dict = {k: v for k, v in sorted(today_entries.items(), key=lambda item: item[1][0], reverse=True)}
    sorted_old_entries: dict = {k: v for k, v in sorted(old_entries.items(), key=lambda item: item[1][0], reverse=True)}

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

    return result

def genplot():

    json_files:list = glob.glob(".\\Users\\*.json")
    plt.clf()

    xaxis: list = []
    xtickslist:list = []
    for i in range(1, current_date_no+1):
        xaxis.append(str(i).zfill(ZFILL_LEN) + 'A')
        xaxis.append(str(i).zfill(ZFILL_LEN) + 'P')
        xtickslist.append(str(i).zfill(ZFILL_LEN) + 'A')


    for file in json_files:
        x:list = []
        y:list = []

        with open(file, 'r') as jsonfile:
            user_info:dict = json.load(jsonfile)

            if "prices" in user_info:
                prices:dict = user_info["prices"]
                #ordered_price_dates:dict = {k: v for k, v in sorted(prices.items(), key=lambda item: item[0])}

                if len(prices.items()) > 0:
                    price_index:int = 0
                    prices_list:list = list(prices.values())
                    prices_list_keys:list = list(prices.keys())
                    price: int = int(prices_list[price_index])
                    for xtick in xaxis:

                        if prices_list_keys[price_index] == xtick:
                            price = int(prices_list[price_index])
                            price_index += 1

                        x.append(xtick)
                        y.append(price)

                        if price_index >= len(prices.items()):
                            break

            plt.plot(x, y, label=user_info["username"])

    plt.xticks(xtickslist, list(range(len(xtickslist))))

    plt.xlabel('day')
    plt.ylabel('BPT')
    plt.title('Stalk Market\nTurnip Prices')
    plt.legend()
    #plt.show()

    plt.savefig('result.png')

@bot.command(name='BPT', help='Stores the Bells Per Turnip for the user')
async def bptcap_proc(ctx, arg:str):
    await bpt_proc(ctx, arg)

@bot.command(name='bpt', help='Stores the Bells Per Turnip for the user')
async def bpt_proc(ctx, arg:str):
    author_username:str = str(ctx.message.author)
    author_timezone:str = "UTC"
    author_id:str = str(ctx.message.author.id)

    if arg.lower() == "chart" or arg.lower() == "charts" or arg.lower() == "graph" or arg.lower() == "plot":
        genplot()
        await ctx.send(file=discord.File('result.png'))
    elif arg.lower() == "check":
        await ctx.send(tally())
    elif arg.isdigit():

        user_info:dict = {"username": author_username, "timezone": "UTC", "prices": { } }
        user_info_path:str = ".\\Users\\{}.json".format(author_id)

        if os.path.exists(user_info_path):
            with open(user_info_path) as f:
                user_info = json.load(f)

        current_user_datetime:datetime = datetime.now(pytz.timezone(user_info["timezone"]))
        noon_user_datetime:datetime = current_user_datetime.replace(hour=12,minute=0)

        m_letter:str = 'A' if current_user_datetime < noon_user_datetime else 'P'

        user_info["prices"][str(current_date_no).zfill(ZFILL_LEN)+m_letter] = int(arg)
        with open(user_info_path, 'w+') as wf:
            json.dump(user_info, wf, indent = 4, sort_keys=True)

        await ctx.send(tally())

bot.run(TOKEN)



