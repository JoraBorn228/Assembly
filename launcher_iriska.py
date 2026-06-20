import os
import json
import shutil
import subprocess
import sys
import zipfile
import tempfile
from pathlib import Path
import urllib.request
import time

# ==========================================
# НАСТРОЙКИ
# ==========================================
GITHUB_REPO = "JoraBorn228/Assembly"
REPO_ZIP = f"https://github.com/{GITHUB_REPO}/archive/refs/heads/main.zip"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/commits/main"

# Путь к .minecraft (автоматически)
MINECRAFT_DIR = Path(os.environ.get('APPDATA', '')) / '.minecraft'
if not MINECRAFT_DIR.exists():
    MINECRAFT_DIR = Path.home() / 'AppData' / 'Roaming' / '.minecraft'

VERSION_FILE = "version.txt"

# ==========================================
# ФУНКЦИИ
# ==========================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=" * 55)
    print("  🎮 МАЙНКРАФТ СБОРКА - ОБНОВЛЯТОР")
    print("=" * 55)
    print()

def get_remote_version_via_api():
    """Пытается получить версию через GitHub API"""
    try:
        req = urllib.request.Request(GITHUB_API)
        # Добавляем User-Agent, чтобы GitHub не блокировал
        req.add_header('User-Agent', 'Minecraft-Updater/1.0')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            # Берём первые 7 символов SHA
            return data['sha'][:7]
    except urllib.error.HTTPError as e:
        if e.code == 403:
            # Лимит API превышен
            return None, "rate_limit"
        return None, "http_error"
    except Exception as e:
        return None, str(e)

def get_remote_version_via_zip():
    """Получает версию через Last-Modified ZIP (fallback)"""
    try:
        req = urllib.request.Request(REPO_ZIP, method='HEAD')
        req.add_header('User-Agent', 'Minecraft-Updater/1.0')
        
        with urllib.request.urlopen(req) as response:
            last_modified = response.headers.get('Last-Modified')
            if last_modified:
                return f"zip-{last_modified}"
            return f"zip-{int(time.time())}"
    except:
        return None

def get_remote_version():
    """Главная функция получения версии: сначала API, потом ZIP"""
    print("📡 Проверка обновлений...")
    
    # Пробуем API
    api_result = get_remote_version_via_api()
    
    if isinstance(api_result, tuple):
        version, error = api_result
        if error == "rate_limit":
            print("⚠️  Лимит API GitHub превышен, переключаюсь на резервный метод...")
            return get_remote_version_via_zip()
        elif version is None:
            print(f"⚠️  Ошибка API: {error}, переключаюсь на резервный метод...")
            return get_remote_version_via_zip()
        return version
    else:
        # Если вернулась строка (SHA)
        return api_result

def get_local_version():
    """Читает локальную версию"""
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return "0.0.0"

def save_local_version(version):
    """Сохраняет локальную версию"""
    with open(VERSION_FILE, 'w') as f:
        f.write(version)

def download_update():
    """Скачивает обновление с GitHub"""
    print("📥 Скачивание обновления...")
    
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "update.zip")
    
    try:
        # Скачиваем ZIP
        req = urllib.request.Request(REPO_ZIP)
        req.add_header('User-Agent', 'Minecraft-Updater/1.0')
        
        with urllib.request.urlopen(req) as response:
            with open(zip_path, 'wb') as f:
                f.write(response.read())
        
        # Распаковываем
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        # Находим распакованную папку
        extracted_dir = None
        for item in os.listdir(temp_dir):
            if item.endswith('-main') or 'Assembly' in item:
                extracted_dir = os.path.join(temp_dir, item)
                break
        
        if not extracted_dir:
            raise Exception("Не удалось найти распакованные файлы")
        
        return extracted_dir
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
        shutil.rmtree(temp_dir)
        return None

def apply_update(update_dir):
    """Устанавливает обновление в .minecraft"""
    print("\n📦 Установка обновления...")
    
    update_mods = os.path.join(update_dir, 'client', 'minecraft', 'mods')
    update_config = os.path.join(update_dir, 'client', 'minecraft', 'config')
    
    target_mods = MINECRAFT_DIR / 'mods'
    target_config = MINECRAFT_DIR / 'config'
    
    target_mods.mkdir(exist_ok=True)
    target_config.mkdir(exist_ok=True)
    
    if os.path.exists(update_mods):
        mod_files = os.listdir(update_mods)
        if mod_files:
            print("   📁 Моды:")
            for file in mod_files:
                src = os.path.join(update_mods, file)
                dst = target_mods / file
                print(f"      ✅ {file}")
                shutil.copy2(src, dst)
        else:
            print("   📁 Моды: нет новых")
    
    if os.path.exists(update_config):
        config_files = os.listdir(update_config)
        if config_files:
            print("   ⚙️ Конфиги:")
            for file in config_files:
                src = os.path.join(update_config, file)
                dst = target_config / file
                print(f"      ✅ {file}")
                shutil.copy2(src, dst)
        else:
            print("   ⚙️ Конфиги: нет новых")
    
    print("\n✅ Обновление установлено!")

def launch_minecraft():
    """Запускает Minecraft"""
    print("\n🚀 Запуск Minecraft...")
    subprocess.Popen(["start", "minecraft://"], shell=True)

def check_installation():
    """Проверяет, установлен ли NeoForge"""
    versions_dir = MINECRAFT_DIR / 'versions'
    if not versions_dir.exists():
        return False
    
    for item in versions_dir.iterdir():
        if item.is_dir() and ('neoforge' in item.name.lower() or 'forge' in item.name.lower()):
            return True
    return False

def show_instructions():
    """Показывает инструкцию по установке"""
    print("\n" + "=" * 55)
    print("  ⚠️  NeoForge не найден!")
    print("=" * 55)
    print()
    print("Чтобы играть на сервере, нужно установить NeoForge:")
    print()
    print("1. Скачай установщик:")
    print("   https://maven.neoforged.net/releases/net/neoforged/neoforge/21.4.111-beta/neoforge-21.4.111-beta-installer.jar")
    print()
    print("2. Запусти установщик, выбери 'Install Client'")
    print()
    print("3. В поле 'Minecraft directory' оставь путь по умолчанию")
    print()
    print("4. Нажми OK и дождись установки")
    print()
    print("5. Запусти этот обновлятор снова")
    print()
    input("Нажми Enter, чтобы продолжить...")

def main():
    try:
        print_header()
        
        if not check_installation():
            show_instructions()
            return
        
        remote_version = get_remote_version()
        
        if not remote_version:
            print("❌ Не удалось проверить обновления.")
            print("   Проверь подключение к интернету.")
            input("\nНажми Enter для выхода...")
            return
        
        local_version = get_local_version()
        print(f"📌 Локальная версия: {local_version}")
        print(f"📌 Актуальная версия: {remote_version}")
        print()
        
        if remote_version != local_version:
            print("🔄 Доступно обновление!")
            answer = input("Установить обновление? (y/n): ").strip().lower()
            
            if answer == 'y':
                update_dir = download_update()
                if update_dir:
                    apply_update(update_dir)
                    save_local_version(remote_version)
                    print(f"\n✅ Обновлено до версии {remote_version}")
                else:
                    print("\n❌ Ошибка при обновлении")
            else:
                print("\n❌ Обновление отменено")
        else:
            print("✅ У вас последняя версия!")
        
        print("\n" + "=" * 55)
        launch_minecraft()
        print()
        input("Нажми Enter для выхода...")
        
    except KeyboardInterrupt:
        print("\n❌ Отменено пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("\nНажми Enter для выхода...")

if __name__ == "__main__":
    main()