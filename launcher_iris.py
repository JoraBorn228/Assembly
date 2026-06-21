import os
import sys
import json
import shutil
import subprocess
import zipfile
import tempfile
import urllib.request
from pathlib import Path
import time
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox

# ==========================================
# НАСТРОЙКИ
# ==========================================
GITHUB_REPO = "JoraBorn228/Assembly"
def get_github_token():
    """Читает токен из файла .env (если он есть)"""
    try:
        env_path = Path(__file__).parent / '.env'
        if env_path.exists():
            with open(env_path, 'r') as f:
                for line in f:
                    if line.startswith('GITHUB_TOKEN='):
                        return line.strip().split('=', 1)[1]
    except:
        pass
    return None

GITHUB_TOKEN = get_github_token()

# Если токен есть — используем его, если нет — работаем без него
if GITHUB_TOKEN:
    print("🔑 Токен найден, лимит API увеличен")
else:
    print("ℹ️  Токен не найден, работаем с ограничениями API")

MINECRAFT_DIR = Path(os.environ.get('APPDATA', '')) / '.minecraft'
MC_VERSION = "1.21.1"
NEOFORGE_VERSION = "21.4.156"

# Папки внутри .minecraft
MODS_DIR = MINECRAFT_DIR / 'mods'
CONFIG_DIR = MINECRAFT_DIR / 'config'
FTBQUESTS_DIR = MINECRAFT_DIR / 'ftbquests'

# Версия сборки (локальная)
VERSION_FILE = MINECRAFT_DIR / 'assembly_version.txt'

LAUNCHER_VERSION = "1.0.0"
LAUNCHER_REPO = "JoraBorn228/Assembly"
LAUNCHER_RELEASE_URL = f"https://api.github.com/repos/{LAUNCHER_REPO}/releases/latest"

# ==========================================
# ФУНКЦИИ
# ==========================================

def get_github_headers():
    """Возвращает заголовки для GitHub API"""
    headers = {'User-Agent': 'Minecraft-Installer/1.0'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'token {GITHUB_TOKEN}'
    return headers

def log_message(msg):
    """Добавляет сообщение в лог"""
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)
    root.update_idletasks()

def get_remote_version():
    """Получает последнюю версию из тегов GitHub"""
    try:
        tags_url = f"https://api.github.com/repos/{GITHUB_REPO}/tags"
        req = urllib.request.Request(tags_url, headers=get_github_headers())
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data:
                return data[0]['name']  # Например, v2.0.0
    except Exception as e:
        log_message(f"⚠️  Ошибка получения версии: {e}")
    return None

def get_local_version():
    """Читает локальную версию сборки"""
    if VERSION_FILE.exists():
        try:
            with open(VERSION_FILE, 'r') as f:
                return f.read().strip()
        except:
            pass
    return "0.0.0"

def save_local_version(version):
    """Сохраняет локальную версию"""
    try:
        with open(VERSION_FILE, 'w') as f:
            f.write(version)
    except:
        pass

def file_changed(url, local_path):
    """Проверяет, изменился ли файл на сервере"""
    try:
        req = urllib.request.Request(url, headers=get_github_headers(), method='HEAD')
        with urllib.request.urlopen(req) as response:
            remote_size = int(response.headers.get('Content-Length', 0))
        
        if local_path.exists():
            local_size = local_path.stat().st_size
            if remote_size == local_size:
                return False, remote_size
        
        return True, remote_size
    except:
        return True, 0

def download_file(url, path, description=""):
    """Скачивает файл"""
    try:
        req = urllib.request.Request(url, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            with open(path, 'wb') as f:
                f.write(response.read())
        return True
    except Exception as e:
        log_message(f"   ❌ Ошибка: {e}")
        return False

def check_java():
    """Проверяет Java"""
    try:
        result = subprocess.run(['java', '-version'], capture_output=True, text=True)
        version = result.stderr.split('\n')[0] if result.stderr else result.stdout.split('\n')[0]
        return True, version
    except:
        return False, None

def check_game_files():
    """Проверяет, что все игровые файлы на месте"""
    log_message("🔍 Проверка игровых файлов...")
    
    versions_dir = MINECRAFT_DIR / 'versions'
    
    # Проверка Minecraft
    mc_dir = versions_dir / MC_VERSION
    mc_ok = mc_dir.exists() and (mc_dir / f"{MC_VERSION}.jar").exists()
    if not mc_ok:
        log_message(f"   ❌ Minecraft {MC_VERSION} не установлен или неполный")
        return False
    log_message(f"   ✅ Minecraft {MC_VERSION} установлен")
    
    # Проверка NeoForge
    nf_dir = versions_dir / f"neoforge-{NEOFORGE_VERSION}"
    nf_ok = nf_dir.exists() and (nf_dir / f"neoforge-{NEOFORGE_VERSION}.jar").exists()
    if not nf_ok:
        log_message(f"   ❌ NeoForge {NEOFORGE_VERSION} не установлен или неполный")
        return False
    log_message(f"   ✅ NeoForge {NEOFORGE_VERSION} установлен")
    
    return True

def check_integrity():
    """Проверяет, все ли файлы на месте (по списку с GitHub)"""
    missing = []
    
    try:
        # 1. Проверяем моды
        log_message("   📦 Проверка модов...")
        mods_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/mods"
        req = urllib.request.Request(mods_url, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            expected_mods = [item['name'] for item in data if item['name'].endswith('.jar')]
        
        mods_found = 0
        for mod in expected_mods:
            if (MODS_DIR / mod).exists():
                mods_found += 1
            else:
                missing.append(f"Мод: {mod}")
        log_message(f"      Найдено {mods_found} из {len(expected_mods)} модов")
        
        # 2. Проверяем конфиги
        log_message("   ⚙️  Проверка конфигов...")
        configs_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/config"
        req = urllib.request.Request(configs_url, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            expected_configs = [item['name'] for item in data if not item.get('type') == 'dir']
        
        configs_found = 0
        for config in expected_configs:
            if (CONFIG_DIR / config).exists():
                configs_found += 1
            else:
                missing.append(f"Конфиг: {config}")
        log_message(f"      Найдено {configs_found} из {len(expected_configs)} конфигов")
        
        # 3. Проверяем квесты (если есть)
        try:
            ftbquests_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/ftbquests"
            req = urllib.request.Request(ftbquests_url, headers=get_github_headers())
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                expected_quests = [item['name'] for item in data if item['name'].endswith('.snbt')]
            
            if expected_quests:
                log_message("   📁 Проверка квестов...")
                quests_found = 0
                for quest in expected_quests:
                    if (FTBQUESTS_DIR / quest).exists():
                        quests_found += 1
                    else:
                        missing.append(f"Квест: {quest}")
                log_message(f"      Найдено {quests_found} из {len(expected_quests)} квестов")
        except:
            pass
        
        if missing:
            log_message(f"   ⚠️  Всего отсутствует: {len(missing)} файлов")
        else:
            log_message("   ✅ Все файлы на месте!")
        
        return missing
            
    except Exception as e:
        log_message(f"   ❌ Ошибка проверки целостности: {e}")
        return None

def install_minecraft():
    """Проверяет установку Minecraft"""
    log_message("📥 Проверка Minecraft...")
    versions_dir = MINECRAFT_DIR / 'versions'
    mc_version_dir = versions_dir / MC_VERSION
    
    if mc_version_dir.exists() and mc_version_dir.is_dir():
        required_files = [
            mc_version_dir / f"{MC_VERSION}.jar",
            mc_version_dir / f"{MC_VERSION}.json",
        ]
        all_exists = all(f.exists() for f in required_files)
        
        if all_exists:
            log_message(f"   ✅ Minecraft {MC_VERSION} установлен")
            return True
        else:
            log_message(f"   ⚠️  Папка версии есть, но не хватает файлов")
    
    log_message("   ❌ Minecraft 1.21.1 не найден или неполный!")
    log_message("   Установи Minecraft 1.21.1 через официальный лаунчер:")
    log_message("   1. Запусти Minecraft Launcher")
    log_message("   2. Выбери версию 1.21.1 и запусти игру хотя бы раз")
    log_message("   3. Закрой игру и нажми 'Проверить' снова")
    return False

def install_neoforge():
    """Проверяет установку NeoForge"""
    log_message(f"🔧 Проверка NeoForge {NEOFORGE_VERSION}...")
    
    versions_dir = MINECRAFT_DIR / 'versions'
    neoforge_version_name = f"neoforge-{NEOFORGE_VERSION}"
    neoforge_dir = versions_dir / neoforge_version_name
    
    if neoforge_dir.exists() and neoforge_dir.is_dir():
        required_files = [
            neoforge_dir / f"{neoforge_version_name}.jar",
            neoforge_dir / f"{neoforge_version_name}.json",
        ]
        all_exists = all(f.exists() for f in required_files)
        
        if all_exists:
            log_message(f"   ✅ NeoForge {NEOFORGE_VERSION} установлен")
            return True
        else:
            log_message(f"   ⚠️  Папка NeoForge есть, но не хватает файлов")
    
    log_message(f"   ❌ NeoForge {NEOFORGE_VERSION} не найден или неполный")
    log_message("   Установи NeoForge через установщик с сайта")
    return False

def download_mods():
    """Скачивает только новые моды"""
    log_message("📦 Проверка модов...")
    MODS_DIR.mkdir(parents=True, exist_ok=True)
    
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/mods"
    try:
        req = urllib.request.Request(api_url, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            mods = [item['name'] for item in data if item['name'].endswith('.jar')]
        
        if not mods:
            log_message("   ⚠️  Модов нет")
            return True
        
        updated = 0
        for mod_name in mods:
            target_path = MODS_DIR / mod_name
            download_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/client/minecraft/mods/{mod_name}"
            
            needs_update, size = file_changed(download_url, target_path)
            
            if not needs_update:
                log_message(f"   ✅ {mod_name} (актуален)")
                continue
            
            log_message(f"   📥 {mod_name}...")
            if download_file(download_url, target_path):
                log_message(f"      ✅ {mod_name} (обновлён)")
                updated += 1
            else:
                log_message(f"      ❌ Ошибка: {mod_name}")
        
        if updated == 0:
            log_message("   ✅ Все моды актуальны")
        else:
            log_message(f"   📥 Обновлено модов: {updated}")
        
        return True
    except Exception as e:
        log_message(f"   ❌ Ошибка: {e}")
        return False

def download_configs():
    """Скачивает только изменённые конфиги"""
    log_message("⚙️  Проверка конфигов...")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/config"
    try:
        req = urllib.request.Request(api_url, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            configs = [item['name'] for item in data if not item.get('type') == 'dir']
        
        if not configs:
            log_message("   ℹ️  Конфигов нет")
            return True
        
        updated = 0
        for config_name in configs:
            target_path = CONFIG_DIR / config_name
            download_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/client/minecraft/config/{config_name}"
            
            needs_update, size = file_changed(download_url, target_path)
            
            if not needs_update:
                log_message(f"   ✅ {config_name} (актуален)")
                continue
            
            if download_file(download_url, target_path):
                log_message(f"   📥 {config_name} (обновлён)")
                updated += 1
            else:
                log_message(f"   ⚠️  {config_name} (ошибка)")
        
        if updated == 0:
            log_message("   ✅ Все конфиги актуальны")
        else:
            log_message(f"   📥 Обновлено конфигов: {updated}")
        
        return True
    except Exception as e:
        log_message(f"   ❌ Ошибка: {e}")
        return False

def setup_ftbquests():
    """Устанавливает только новые квесты"""
    log_message("📁 Проверка квестов FTB Quests...")
    
    ftbquests_found = False
    for f in MODS_DIR.glob('*ftbquests*.jar'):
        ftbquests_found = True
        break
    
    if not ftbquests_found:
        log_message("   ℹ️  FTB Quests не найден, пропускаем")
        return True
    
    FTBQUESTS_DIR.mkdir(parents=True, exist_ok=True)
    
    api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/ftbquests"
    try:
        req = urllib.request.Request(api_url, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            quest_files = [item['name'] for item in data if item['name'].endswith('.snbt')]
        
        if not quest_files:
            log_message("   ℹ️  Квестов нет")
            return True
        
        updated = 0
        for quest_file in quest_files:
            target_path = FTBQUESTS_DIR / quest_file
            download_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/client/minecraft/ftbquests/{quest_file}"
            
            needs_update, size = file_changed(download_url, target_path)
            
            if not needs_update:
                log_message(f"   ✅ {quest_file} (актуален)")
                continue
            
            if download_file(download_url, target_path):
                log_message(f"   📥 {quest_file} (обновлён)")
                updated += 1
            else:
                log_message(f"   ⚠️  {quest_file} (ошибка)")
        
        if updated == 0:
            log_message("   ✅ Все квесты актуальны")
        else:
            log_message(f"   📥 Обновлено квестов: {updated}")
        
        return True
    except:
        log_message("   ℹ️  Квестов нет в репозитории")
        return True

def run_repair():
    """Восстанавливает недостающие файлы"""
    btn_check.config(state=tk.DISABLED, text="⏳ Восстановление...")
    log_text.delete(1.0, tk.END)
    
    def repair_thread():
        try:
            log_message("=" * 55)
            log_message("  🔧 ВОССТАНОВЛЕНИЕ СБОРКИ")
            log_message("=" * 55)
            log_message("")
            
            # Скачиваем только недостающие файлы
            log_message("📥 Восстановление модов...")
            MODS_DIR.mkdir(parents=True, exist_ok=True)
            
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/mods"
            req = urllib.request.Request(api_url, headers=get_github_headers())
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                mods = [item['name'] for item in data if item['name'].endswith('.jar')]
            
            for mod in mods:
                target_path = MODS_DIR / mod
                if target_path.exists():
                    continue
                
                download_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/client/minecraft/mods/{mod}"
                log_message(f"   📥 {mod}...")
                if download_file(download_url, target_path):
                    log_message(f"      ✅ {mod}")
            
            log_message("")
            log_message("📥 Восстановление конфигов...")
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            api_url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/client/minecraft/config"
            req = urllib.request.Request(api_url, headers=get_github_headers())
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                configs = [item['name'] for item in data if not item.get('type') == 'dir']
            
            for config in configs:
                target_path = CONFIG_DIR / config
                if target_path.exists():
                    continue
                
                download_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/client/minecraft/config/{config}"
                log_message(f"   📥 {config}...")
                if download_file(download_url, target_path):
                    log_message(f"      ✅ {config}")
            
            log_message("")
            log_message("=" * 55)
            log_message("  ✅ ВОССТАНОВЛЕНИЕ ЗАВЕРШЕНО!")
            log_message("=" * 55)
            
            version_label.config(text=f"✅ {get_local_version()}")
            
            messagebox.showinfo("Готово", "Восстановление завершено! Все файлы на месте.")
            
        except Exception as e:
            log_message(f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))
        finally:
            btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
    
    threading.Thread(target=repair_thread, daemon=True).start()

def get_latest_launcher_version():
    """Получает последнюю версию лаунчера из Releases"""
    try:
        req = urllib.request.Request(LAUNCHER_RELEASE_URL, headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            for asset in data.get('assets', []):
                if asset['name'] == 'launcher_iris.zip' or asset['name'] == 'launcher_iris.exe':
                    return {
                        'version': data['tag_name'],
                        'download_url': asset['browser_download_url']
                    }
            if data.get('assets'):
                return {
                    'version': data['tag_name'],
                    'download_url': data['assets'][0]['browser_download_url']
                }
    except Exception as e:
        log_message(f"⚠️  Ошибка проверки версии лаунчера: {e}")
    return None

def check_launcher_update():
    """Проверяет, есть ли обновление лаунчера"""
    log_message("🔍 Проверка обновлений лаунчера...")
    
    latest = get_latest_launcher_version()
    if not latest:
        log_message("   ❌ Не удалось проверить")
        return False
    
    log_message(f"   📌 Текущая версия: v{LAUNCHER_VERSION}")
    log_message(f"   📌 Актуальная версия: {latest['version']}")
    
    if latest['version'] == f"v{LAUNCHER_VERSION}":
        log_message("   ✅ Лаунчер актуален")
        return False
    
    log_message(f"   🔄 Доступно обновление лаунчера!")
    return latest

def update_launcher():
    """Обновляет сам лаунчер"""
    log_message("=" * 55)
    log_message("  🔄 ОБНОВЛЕНИЕ ЛАУНЧЕРА")
    log_message("=" * 55)
    
    latest = check_launcher_update()
    if not latest:
        return
    
    answer = messagebox.askyesno(
        "Обновление лаунчера",
        f"Доступна новая версия лаунчера!\n\n"
        f"Текущая: v{LAUNCHER_VERSION}\n"
        f"Новая: {latest['version']}\n\n"
        f"Обновить лаунчер?"
    )
    
    if not answer:
        log_message("❌ Обновление отменено")
        return
    
    log_message(f"📥 Скачивание новой версии...")
    
    temp_dir = tempfile.gettempdir()
    download_path = Path(temp_dir) / 'launcher_iris_download.zip'
    new_launcher_path = Path(temp_dir) / 'launcher_iris_new.exe'
    
    try:
        req = urllib.request.Request(latest['download_url'], headers=get_github_headers())
        with urllib.request.urlopen(req) as response:
            with open(download_path, 'wb') as f:
                f.write(response.read())
        
        log_message("   ✅ Скачано")
        
        if download_path.suffix == '.zip':
            log_message("   📦 Распаковка...")
            import zipfile
            with zipfile.ZipFile(download_path, 'r') as zip_ref:
                exe_in_zip = None
                for file in zip_ref.namelist():
                    if file.endswith('launcher_iris.exe'):
                        exe_in_zip = file
                        break
                if exe_in_zip:
                    with zip_ref.open(exe_in_zip) as source, open(new_launcher_path, 'wb') as target:
                        target.write(source.read())
                else:
                    raise Exception("В архиве не найден launcher_iris.exe")
            download_path.unlink()
        else:
            download_path.rename(new_launcher_path)
        
        log_message("   ✅ Подготовлено к обновлению")
        log_message("🔄 Замена лаунчера...")
        
        bat_path = Path(temp_dir) / 'update_launcher.bat'
        current_exe = sys.argv[0] if getattr(sys, 'frozen', False) else sys.executable
        
        with open(bat_path, 'w') as f:
            f.write(f'''@echo off
timeout /t 2 /nobreak >nul
copy /Y "{new_launcher_path}" "{current_exe}"
start "" "{current_exe}"
del "{bat_path}"
''')
        
        subprocess.Popen([str(bat_path)], shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
        
        log_message("✅ Лаунчер будет обновлён при следующем запуске!")
        log_message("   Закрываю лаунчер...")
        
        messagebox.showinfo("Обновление", 
            "Лаунчер будет обновлён.\n"
            "Закройте и откройте его снова.")
        
        root.quit()
        
    except Exception as e:
        log_message(f"❌ Ошибка обновления: {e}")
        messagebox.showerror("Ошибка", f"Не удалось обновить лаунчер:\n{e}")
        if download_path.exists():
            download_path.unlink()
        if new_launcher_path.exists():
            new_launcher_path.unlink()

def run_update(version):
    """Запускает установку обновления"""
    if not version:
        log_message("❌ Нет версии для обновления")
        return
    
    btn_check.config(state=tk.DISABLED, text="⏳ Обновление...")
    log_text.delete(1.0, tk.END)
    
    def update_thread():
        try:
            log_message("=" * 55)
            log_message(f"  📦 ОБНОВЛЕНИЕ ДО {version}")
            log_message("=" * 55)
            log_message("")
            
            steps = [
                ("Проверка Java", check_java),
                ("Проверка Minecraft", install_minecraft),
                ("Проверка NeoForge", install_neoforge),
                ("Обновление модов", download_mods),
                ("Обновление конфигов", download_configs),
                ("Обновление квестов", setup_ftbquests),
            ]
            
            for step_name, step_func in steps:
                result = step_func()
                log_message("")
            
            save_local_version(version)
            
            log_message("=" * 55)
            log_message(f"  🎉 ОБНОВЛЕНИЕ ДО {version} ЗАВЕРШЕНО!")
            log_message("=" * 55)
            
            version_label.config(text=f"✅ {version}")
            
            messagebox.showinfo("Готово", f"Обновление до {version} завершено!")
            
        except Exception as e:
            log_message(f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", str(e))
        finally:
            btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
    
    threading.Thread(target=update_thread, daemon=True).start()

def check_updates():
    """Проверяет обновления и целостность сборки"""
    log_message("=" * 55)
    log_message("  🔍 ПРОВЕРКА ОБНОВЛЕНИЙ")
    log_message("=" * 55)
    
    btn_check.config(state=tk.DISABLED, text="⏳ Проверка...")
    root.update_idletasks()
    
    # 0. Проверяем игровые файлы
    if not check_game_files():
        log_message("")
        log_message("⚠️  Проблемы с установкой Minecraft или NeoForge!")
        log_message("   Установите их через официальный лаунчер и перезапустите проверку.")
        btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
        return
    
    # 1. Проверяем версию
    remote_version = get_remote_version()
    if not remote_version:
        log_message("❌ Не удалось получить версию с GitHub")
        log_message("   Проверь подключение к интернету.")
        btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
        return
    
    local_version = get_local_version()
    
    log_message(f"📌 Локальная версия: {local_version}")
    log_message(f"📌 Актуальная версия: {remote_version}")
    log_message("")
    
    # 2. Проверяем целостность (ВСЕГДА!)
    log_message("🔍 Проверка целостности файлов...")
    missing = check_integrity()
    
    # 3. Если есть недостающие файлы — сразу предлагаем восстановить
    if missing:
        log_message("")
        log_message(f"⚠️  Найдено {len(missing)} отсутствующих файлов!")
        if remote_version == local_version:
            log_message("   Версия актуальна, но не хватает файлов.")
            log_message("   Возможно, кто-то случайно удалил мод или конфиг.")
        else:
            log_message("   Обновление будет включать восстановление недостающих файлов.")
        log_message("")
        
        for item in missing[:10]:
            log_message(f"   🗑️  {item}")
        if len(missing) > 10:
            log_message(f"   ... и ещё {len(missing) - 10} файлов")
        log_message("")
        
        answer = messagebox.askyesno(
            "⚠️ Обнаружены проблемы", 
            f"Найдено {len(missing)} отсутствующих файлов!\n\n"
            "Это может быть из-за случайного удаления модов или конфигов.\n\n"
            "Восстановить недостающие файлы?",
            icon='warning'
        )
        
        if answer:
            log_message("🔄 Запуск восстановления...")
            run_repair()
        else:
            log_message("❌ Восстановление отменено")
            version_label.config(text=f"⚠️ {remote_version} (неполная)")
            btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
            return
        return
    
    # 4. Если версии отличаются — предлагаем обновление
    if remote_version != local_version:
        log_message("🔄 Доступно обновление!")
        version_label.config(text=f"🔄 {remote_version} (доступно)")
        
        answer = messagebox.askyesno("Обновление", 
            f"Доступна новая версия сборки!\n\n"
            f"Текущая: {local_version}\n"
            f"Новая: {remote_version}\n\n"
            f"Установить обновление?")
        
        if answer:
            run_update(remote_version)
        else:
            log_message("❌ Обновление отменено")
            btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
            return
    
    # 5. Если всё хорошо
    if remote_version == local_version:
        log_message("✅ У вас последняя версия сборки!")
        log_message("✅ Все файлы на месте!")
        version_label.config(text=f"✅ {remote_version}")
        btn_check.config(state=tk.NORMAL, text="🔍 Проверить")
        return

def fake_delete():
    """Шутка про удаление Program Files"""
    result = messagebox.askyesno(
        "⚠️ ВНИМАНИЕ!",
        "Вы уверены, что хотите удалить папку Program Files?\n\n"
        "Это действие НЕОБРАТИМО!\n"
        "Все программы будут удалены!\n\n"
        "Ладно, нихуя не спасёт",
        icon='warning'
    )
    root.quit()

# ==========================================
# GUI
# ==========================================
root = tk.Tk()
root.title("🎮 Лаунчер сборки Minecraft")
root.geometry("700x600")
root.configure(bg='#1e1e2f')
root.resizable(True, True)

# ==========================================
# Заголовок
# ==========================================
title_frame = tk.Frame(root, bg='#2a2a3e', pady=10)
title_frame.pack(fill=tk.X, padx=10, pady=5)

title_label = tk.Label(title_frame, text="🎮 Лаунчер сборки Minecraft", 
                       font=('Arial', 16, 'bold'), bg='#2a2a3e', fg='white')
title_label.pack()

subtitle_label = tk.Label(title_frame, text=f"Версия {MC_VERSION} | NeoForge {NEOFORGE_VERSION}", 
                          font=('Arial', 10), bg='#2a2a3e', fg='#8be9fd')
subtitle_label.pack()

# ==========================================
# Информация о версии
# ==========================================
version_frame = tk.Frame(root, bg='#1e1e2f', pady=10)
version_frame.pack(fill=tk.X, padx=10)

version_label = tk.Label(version_frame, text="⏳ Проверка версии...", 
                         font=('Arial', 12, 'bold'), bg='#1e1e2f', fg='#50fa7b')
version_label.pack()

info_label = tk.Label(version_frame, text=f"📁 .minecraft: {MINECRAFT_DIR}", 
                      font=('Arial', 9), bg='#1e1e2f', fg='#8be9fd')
info_label.pack()

# ==========================================
# Кнопки
# ==========================================
btn_frame = tk.Frame(root, bg='#1e1e2f', pady=10)
btn_frame.pack(fill=tk.X, padx=10)

btn_check = tk.Button(btn_frame, text="🔍 Проверить", command=check_updates,
                      bg='#50fa7b', fg='black', font=('Arial', 12, 'bold'), padx=30)
btn_check.pack(side=tk.LEFT, padx=5)

btn_update_launcher = tk.Button(btn_frame, text="🔄 Обновить лаунчер", 
                                command=update_launcher,
                                bg='#bd93f9', fg='black', font=('Arial', 10), padx=15)
btn_update_launcher.pack(side=tk.LEFT, padx=5)

btn_exit = tk.Button(btn_frame, text="💀 Удалить Program Files", 
                     command=fake_delete,
                     bg='#ff5555', fg='white', font=('Arial', 10, 'bold'), padx=20)
btn_exit.pack(side=tk.RIGHT, padx=5)

# ==========================================
# Лог
# ==========================================
log_frame = tk.LabelFrame(root, text="📋 Лог", 
                          bg='#2a2a3e', fg='white', font=('Arial', 10, 'bold'))
log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

log_text = scrolledtext.ScrolledText(log_frame, bg='#0f0f1a', fg='#8be9fd',
                                     font=('Consolas', 9), wrap=tk.WORD)
log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

# ==========================================
# Запуск
# ==========================================
log_message("Добро пожаловать в лаунчер сборки!")
log_message("Нажмите 'Проверить' для поиска обновлений.")
log_message("")

# Проверяем версию при старте
local_version = get_local_version()
if local_version and local_version != "0.0.0":
    version_label.config(text=f"📌 {local_version}")
    log_message(f"Текущая версия: {local_version}")
else:
    version_label.config(text="⚠️ Версия не установлена")
    log_message("⚠️ Версия сборки не найдена")
    log_message("   Нажмите 'Проверить' для установки")

# Автоматически проверяем обновления
def auto_check():
    try:
        remote_version = get_remote_version()
        if remote_version:
            local_version = get_local_version()
            if remote_version != local_version:
                log_message(f"🔄 Доступно обновление: {remote_version}")
                version_label.config(text=f"🔄 {remote_version}")
            else:
                version_label.config(text=f"✅ {remote_version}")
    except:
        pass

threading.Thread(target=auto_check, daemon=True).start()

root.mainloop()