import discord
from discord.ext import commands, tasks
from discord import ui
from datetime import datetime, timedelta
from TT_scheduler import schedule_tasks  # Your scheduler logic
from TT_csv_utils import read_tasks, write_tasks

# Load tasks from the CSV file
FILE_NAME = "tasklist.csv"
task_list = read_tasks(FILE_NAME)
today = datetime.today().date()
today_tasks = [task for task in task_list if task.due_date.date() == today]

# Intents and Bot Setup
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

class TaskButton(ui.Button):
    def __init__(self, task):
        super().__init__(label=task.name, style=discord.ButtonStyle.primary)
        self.task = task

    async def callback(self, interaction: discord.Interaction):
        """Mark task as completed when clicked."""
        self.task.completed = not self.task.completed
        # self.disabled = True  # Disable the button after clicking
        
        if self.task.completed:
            self.style = discord.ButtonStyle.primary  # Change background
            self.label = f"{self.task.name}"  # Line-through text
        else:
            self.style = discord.ButtonStyle.secondary  # Change background
            self.label = f"{self.task.name}"  # Line-through text

        # Update the message with the modified view
        await interaction.response.edit_message(view=self.view)

        write_tasks(FILE_NAME, task_list)  # Save updated tasks

class TaskView(ui.View):
    def __init__(self, tasks):
        super().__init__()
        for task in tasks:
            if not task.completed:  # Only add buttons for incomplete tasks
                self.add_item(TaskButton(task))
                
# @tasks.loop(hours=24)
async def daily_task_post():
    """Post daily tasks to the Discord channel."""
    if not today_tasks:
        return

    channel = discord.utils.get(bot.get_all_channels(), name="daily-tasks")  # Change to your channel name
    if channel:
        view = TaskView(today_tasks)
        await channel.send(f"Tâches du {today.strftime('%d %B %Y')}", view=view)

@bot.event
async def on_ready():
    print(f"{bot.user} is now online!")
    daily_task_post.start()

@bot.command()
async def tasks(ctx):
    """Manually display today's tasks."""
    if not today_tasks:
        await ctx.send("No tasks for today!")
        return

    view = TaskView(today_tasks)
    await ctx.send(f"Tâches du {today.strftime('%d %B %Y')}", view=view)

# Run the bot
TOKEN = "MTMyOTE2ODUzMjk5MDMyODk1Ng.GNZQcC.w3RX7Jib-PlrVCzEsj8ZbKyU_NBtE0hDNjtpgs"
bot.run(TOKEN)