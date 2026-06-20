import os
import shutil
import subprocess
from pathlib import Path
import datetime

# ==========================================
# ПУТИ
# ==========================================
PROJECT_DIR = Path(r"E:\Сервер\minecraft-server-build")
MINECRAFT_DIR = Path(os.environ.get('APPDATA', '')) / '.minecraft'

# Пути в проекте
CLIENT_MODS = PROJECT_DIR / 'client' / 'minecraft' / 'mods'
CLIENT_CONFIG = PROJECT_DIR / 'client' / 'minecraft' / 'config'
SERVER_MODS = PROJECT_DIR / 'server' / 'mods'

# ==========================================
# ФУНКЦИИ
# ==========================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=" * 55)
    print("  🚀 ПУБЛИКАЦИЯ СБОРКИ ИЗ .MINECRAFT")
    print("=" * 55)
    print()

def show_mods():
    """Показывает моды в .minecraft"""
    mods_dir = MINECRAFT_DIR / 'mods'
    if mods_dir.exists():
        mods = list(mods_dir.glob('*.jar'))
        if mods:
            print("📦 Моды в .minecraft:")
            for mod in mods:
                size = mod.stat().st_size / 1024 / 1024
                print(f"   • {mod.name} ({size:.1f} MB)")
            return mods
    print("📦 Модов в .minecraft не найдено")
    return []

def copy_to_project():
    """Копирует моды и конфиги из .minecraft в проект"""
    print("\n📁 Копирование из .minecraft в проект...")
    
    # Создаём папки если нет
    CLIENT_MODS.mkdir(parents=True, exist_ok=True)
    CLIENT_CONFIG.mkdir(parents=True, exist_ok=True)
    SERVER_MODS.mkdir(parents=True, exist_ok=True)
    
    # Копируем моды
    mods_dir = MINECRAFT_DIR / 'mods'
    if mods_dir.exists():
        copied = 0
        for file in mods_dir.glob('*.jar'):
            # Копируем в клиентскую сборку
            shutil.copy2(file, CLIENT_MODS / file.name)
            # Копируем на сервер
            shutil.copy2(file, SERVER_MODS / file.name)
            print(f"   ✅ {file.name}")
            copied += 1
        print(f"\n   Скопировано {copied} модов в клиентскую и серверную сборку")
    
    # Копируем конфиги
    config_dir = MINECRAFT_DIR / 'config'
    if config_dir.exists():
        for file in config_dir.iterdir():
            if file.is_file():
                shutil.copy2(file, CLIENT_CONFIG / file.name)
                print(f"   ⚙️ {file.name}")
    
    print("\n✅ Копирование завершено!")

def git_push():
    """Отправляет изменения на GitHub"""
    print("\n📤 Отправка на GitHub...")
    
    try:
        # Добавляем изменения
        subprocess.run(['git', 'add', 'client/', 'server/'], 
                      cwd=PROJECT_DIR, check=True, capture_output=True)
        
        # Коммит
        timestamp = datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
        subprocess.run(['git', 'commit', '-m', f'Обновление сборки: {timestamp}'], 
                      cwd=PROJECT_DIR, check=True, capture_output=True)
        
        # Пуш
        subprocess.run(['git', 'push'], cwd=PROJECT_DIR, check=True, capture_output=True)
        
        print("✅ Изменения отправлены на GitHub!")
        return True
    except subprocess.CalledProcessError as e:
        if 'nothing to commit' in str(e.stderr):
            print("ℹ️  Нет новых изменений для отправки")
            return True
        print(f"❌ Ошибка Git: {e.stderr.decode()}")
        return False

def main():
    try:
        print_header()
        
        print(f"📍 Папка .minecraft: {MINECRAFT_DIR}")
        print()
        
        mods = show_mods()
        print()
        
        if not mods:
            print("⚠️  В .minecraft нет модов для публикации.")
            print("   Сначала добавь моды в .minecraft/mods/")
            input("\nНажми Enter для выхода...")
            return
        
        print("1. Скопировать моды из .minecraft → проект и отправить на GitHub")
        print("2. Только скопировать (без отправки на GitHub)")
        print("3. Запустить лаунчер (проверить моды перед отправкой)")
        print("4. Выйти")
        print()
        
        choice = input("Выбери действие (1/2/3/4): ").strip()
        
        if choice == '1':
            copy_to_project()
            if git_push():
                print("\n✅ Сборка обновлена на GitHub!")
                print("   Друзья могут запустить обновлятор и получить новые моды.")
            input("\nНажми Enter для выхода...")
        
        elif choice == '2':
            copy_to_project()
            print("\n✅ Файлы скопированы в проект, но не отправлены на GitHub.")
            input("\nНажми Enter для выхода...")
        
        elif choice == '3':
            print("\n🚀 Запуск Minecraft Launcher...")
            subprocess.Popen(["start", "minecraft://"], shell=True)
            input("\nПосле проверки запусти скрипт снова и выбери пункт 1.")
        
        else:
            print("Выход...")
            
    except KeyboardInterrupt:
        print("\n❌ Отменено")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("\nНажми Enter для выхода...")

if __name__ == "__main__":
    main()