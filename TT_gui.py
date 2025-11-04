import csv
from nicegui import ui
from datetime import datetime
from TT_task import *
from TT_yaml import *
from TT_task_selector import TT_TaskSelector
import locale

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


if __name__ in {"__main__", "__mp_main__"}:    
    # --- Initialisation ---
    initialize()
    
    # --- Interface graphique ---
    ui.label(f'📝 Tâches du {today.strftime('%d %B %Y')}').classes('text-2xl font-bold mt-4')

    with ui.grid(columns='auto auto auto auto').style('align-items: center; justify-content: center'):
        ui.label("Tâche").classes('text-base font-bold')
        ui.label("Durée (min)").classes('text-base font-bold')
        ui.label("Fréquence (j)").classes('text-base font-bold')
        ui.label("Priorité").classes('text-base font-bold')
        for task in today_tasks:
            checkbox = ui.checkbox(task.name)
            ui.label(task.duration)
            ui.label(task.frequency)
            ui.label(task.priority)


    # with ui.row().classes('w-full items-center'):
    #     task_input = ui.input(placeholder='Nouvelle tâche...').classes('w-full')
    #     ui.button('Ajouter', on_click=add_task).classes('bg-blue-500 text-white')

    # with ui.row().classes('mt-2'):
    #     sort_select = ui.select(['Nom', 'Statut'], value='Nom', label='Trier par')
    #     ui.button('Trier', on_click=sort_tasks).classes('bg-gray-300')

    # task_container = ui.column().classes('w-full mt-4')

    
    ui.run()
