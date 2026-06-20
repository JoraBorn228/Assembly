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
GITHUB_TAGS_API = f"https://api.github.com/repos/{GITHUB_REPO}/tags"

# ==========================================
# ПУТЬ К .MINECRAFT
# ==========================================
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
    print("  🎮 ОБНОВЛЯТОР MC СБОРКИ")
    print("=" * 55)
    print()

def get_remote_version_via_tags():
    """Получает последний тег (БЕЗ ТОКЕНА!)"""
    try:
        req = urllib.request.Request(GITHUB_TAGS_API)
        req.add_header('User-Agent', 'Minecraft-Updater/1.0')
        # ТОКЕН НЕ НУЖЕН! Публичный API
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            if data:
                return data[0]['name']  # v1.0.0, v1.2.0
    except Exception as e:
        print(f"⚠️  Ошибка получения тегов: {e}")
    return None

def get_remote_version_via_zip():
    """Запасной вариант: дата ZIP"""
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
    print("📡 Проверка обновлений...")
    
    # Сначала пробуем теги (красивая версия)
    version = get_remote_version_via_tags()
    if version:
        print(f"   📌 Версия: {version}")
        return version
    
    # Запасной вариант — ZIP
    print("   ⚠️  Использую резервный метод (ZIP)...")
    return get_remote_version_via_zip()

def get_local_version():
    if os.path.exists(VERSION_FILE):
        with open(VERSION_FILE, 'r') as f:
            return f.read().strip()
    return "0.0.0"

def save_local_version(version):
    with open(VERSION_FILE, 'w') as f:
        f.write(version)

def download_update():
    print("📥 Скачивание обновления...")
    temp_dir = tempfile.mkdtemp()
    zip_path = os.path.join(temp_dir, "update.zip")
    
    try:
        req = urllib.request.Request(REPO_ZIP)
        req.add_header('User-Agent', 'Minecraft-Updater/1.0')
        
        with urllib.request.urlopen(req) as response:
            with open(zip_path, 'wb') as f:
                f.write(response.read())
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        extracted_dir = None
        for item in os.listdir(temp_dir):
            if item.endswith('-main') or 'Assembly' in item:
                extracted_dir = os.path.join(temp_dir, item)
                break
        
        if not extracted_dir:
            raise Exception("Не удалось найти распакованные файлы")
        return extracted_dir
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        shutil.rmtree(temp_dir)
        return None

def apply_update(update_dir):
    print("\n📦 Установка обновления...")
    
    update_mods = os.path.join(update_dir, 'client', 'minecraft', 'mods')
    target_mods = MINECRAFT_DIR / 'mods'
    target_mods.mkdir(exist_ok=True)
    
    current_mods = set()
    if target_mods.exists():
        current_mods = {f.name for f in target_mods.glob('*.jar')}
    
    if os.path.exists(update_mods):
        new_mods = set(os.listdir(update_mods))
        for mod in current_mods - new_mods:
            (target_mods / mod).unlink()
            print(f"   🗑️  Удалён: {mod}")
    
    if os.path.exists(update_mods):
        for file in os.listdir(update_mods):
            src = os.path.join(update_mods, file)
            dst = target_mods / file
            shutil.copy2(src, dst)
            print(f"   ✅ {file}")
    
    print("\n✅ Обновление установлено!")

def main():
    try:
        print_header()
        
        remote_version = get_remote_version()
        if not remote_version:
            print("❌ Не удалось проверить обновления.")
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
        print("✅ Готово! Запусти Minecraft вручную.")
        print("=" * 55)
        
        input("\nНажми Enter для выхода...")
        
    except KeyboardInterrupt:
        print("\n❌ Отменено")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("\nНажми Enter для выхода...")

if __name__ == "__main__":
    main()