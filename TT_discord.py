import sys
import discord
from discord.ext import commands, tasks
from discord import ui
from datetime import datetime
from TT_task import *
from TT_yaml import *
from TT_task_selector import TT_TaskSelector
import locale

locale.setlocale(locale.LC_TIME, "fr_FR") 

today_tasks = None
today = datetime.today().date()
TOKEN = "MTMyOTE2ODUzMjk5MDMyODk1Ng.G0ONtS.impquBGO5IUKdrux9or16K1wDwRyFSmmN1_fBw"
selector = TT_TaskSelector(daily_time_limit=180)

def initialize():
    if not os.path.exists(TASKS_YAML_FOLDER):
        all_tasks = read_tasks(TASKLIST_FILE_NAME)
        serialize_all_tasks(TASKS_YAML_FOLDER, all_tasks)
        
    selector.update_tasks_serialized(TASKLIST_FILE_NAME, TASKS_YAML_FOLDER)

    # Load tasks from the CSV file
    task_list = deserialize_all_tasks(TASKS_YAML_FOLDER)
    if task_list == None or len(task_list) == 0: 
        print("Erreur: liste de tâches vide")
        return False
    
    selector.reset_and_update_task(today, task_list, TASKS_YAML_FOLDER)
    
    global today_tasks
    today_tasks = selector.get_daily_tasks(task_list, today)
    if today_tasks == None or len(today_tasks) == 0: 
        print("Erreur: liste de tâches du jour vide")
        return False
                                
    return True

# =============================================

# Intents and Bot Setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class TaskButton(ui.Button):
    def __init__(self, task):
        super().__init__(label=f"{task.name}", 
                         style=discord.ButtonStyle.primary)
        self.task = task

    async def callback(self, interaction: discord.Interaction):
        """Mark task as completed when clicked."""    
        if self.task.completed:
            self.task.uncomplete_task()
            self.style = discord.ButtonStyle.primary  # Change background
        else:
            self.task.complete_task(today)
            self.style = discord.ButtonStyle.secondary  # Change background

        # Update the message with the modified view
        await interaction.response.edit_message(view=self.view)
        

class TaskView(ui.View):
    def __init__(self, tasks):
        super().__init__(timeout=None)
        for task in tasks:
            self.add_item(TaskButton(task))
                
@tasks.loop(hours=24)
async def daily_task_post():
    """Post daily tasks to the Discord channel."""
    if not today_tasks:
        return

    channel = discord.utils.get(bot.get_all_channels(), name="daily-tasks")  # Change to your channel name
    if channel:
        view = TaskView(today_tasks)
        total_duration = sum(task.duration for task in today_tasks)
        await channel.send(f"Tâches du **{today.strftime('%d %B %Y')}**. Durée totale prévue: {total_duration}min", view=view)

@bot.event
async def on_ready():
    if not initialize(): 
        print("Error: Initialization failed")
        sys.exit(-1)

    print(f"{bot.user} is now online!")
    daily_task_post.start()        
            
@bot.command()
async def tasks(ctx):
    """Manually display today's tasks."""
    if not today_tasks:
        await ctx.send("No tasks for today!")
        return

    view = TaskView(today_tasks)
    await ctx.send(f"Tâches du **{today.strftime('%d %B %Y')}**", view=view)

@bot.command()
async def update(ctx): 
    selector.update_tasks_serialized(TASKLIST_FILE_NAME, TASKS_YAML_FOLDER)
    await ctx.send("Mise à jour des fichiers.")

if __name__ == "__main__":
    bot.run(TOKEN)
