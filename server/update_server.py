import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
import signal

# ==========================================
# ПУТИ
# ==========================================
SERVER_DIR = Path(__file__).parent.absolute()
PROJECT_DIR = SERVER_DIR.parent
MINECRAFT_DIR = Path(os.environ.get('APPDATA', '')) / '.minecraft'

# ==========================================
# ФУНКЦИИ
# ==========================================

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    clear_screen()
    print("=" * 55)
    print("  🔄 ОБНОВЛЕНИЕ СЕРВЕРА")
    print("=" * 55)
    print()

def stop_server():
    """Останавливает сервер"""
    print("⏹️  Остановка сервера...")
    
    # Ищем процесс сервера
    try:
        # Находим PID сервера
        result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq java.exe'], 
                               capture_output=True, text=True)
        
        if 'java.exe' in result.stdout:
            # Завершаем процесс (мягко)
            subprocess.run(['taskkill', '/IM', 'java.exe', '/FI', 'MEMUSAGE gt 100000'], 
                          capture_output=True)
            time.sleep(3)
            print("   ✅ Сервер остановлен")
            return True
        else:
            print("   ℹ️  Сервер не запущен")
            return True
    except Exception as e:
        print(f"   ⚠️  Ошибка остановки: {e}")
        return False

def update_from_git():
    """Обновляет код с GitHub"""
    print("\n📥 Обновление с GitHub...")
    try:
        # Pull изменений
        result = subprocess.run(['git', 'pull'], cwd=PROJECT_DIR, capture_output=True, text=True)
        print(f"   {result.stdout}")
        if 'Already up to date' in result.stdout:
            print("   ℹ️  Сервер уже обновлён")
            return False
        print("   ✅ Код обновлён")
        return True
    except Exception as e:
        print(f"   ❌ Ошибка git pull: {e}")
        return False

def copy_mods_to_server():
    """Копирует новые моды на сервер"""
    print("\n📦 Копирование модов на сервер...")
    
    # Путь к модам в проекте (клиентская сборка)
    source_mods = PROJECT_DIR / 'client' / 'minecraft' / 'mods'
    target_mods = SERVER_DIR / 'mods'
    
    if not source_mods.exists():
        print("   ⚠️  Папка с модами не найдена")
        return False
    
    # Создаём папку если нет
    target_mods.mkdir(exist_ok=True)
    
    # Копируем моды
    copied = 0
    for file in source_mods.glob('*.jar'):
        shutil.copy2(file, target_mods / file.name)
        print(f"   ✅ {file.name}")
        copied += 1
    
    if copied == 0:
        print("   ℹ️  Новых модов нет")
    else:
        print(f"   ✅ Скопировано {copied} модов")
    
    return True

def start_server():
    """Запускает сервер"""
    print("\n🚀 Запуск сервера...")
    
    # Ищем server.jar
    server_jar = SERVER_DIR / 'server.jar'
    if not server_jar.exists():
        # Ищем другие jar-файлы
        for f in SERVER_DIR.glob('*.jar'):
            if 'server' in f.name or 'neoforge' in f.name:
                server_jar = f
                break
    
    if not server_jar.exists():
        print("   ❌ Не найден server.jar")
        return
    
    # Запускаем сервер в новом окне
    java_path = r"C:\Users\NIKITA\AppData\Local\Programs\Eclipse Adoptium\jdk-25.0.2.10-hotspot\bin\java.exe"
    
    if os.name == 'nt':
        # Windows
        subprocess.Popen(
            ['start', 'cmd', '/k', 
             f'"{java_path}" -Xmx4G -Xms2G -jar "{server_jar}" nogui'],
            shell=True,
            cwd=SERVER_DIR
        )
        print(f"   ✅ Сервер запущен в новом окне")
    else:
        # Linux/Mac
        subprocess.Popen(
            ['java', '-Xmx4G', '-Xms2G', '-jar', str(server_jar), 'nogui'],
            cwd=SERVER_DIR
        )
        print(f"   ✅ Сервер запущен")

def main():
    try:
        print_header()
        
        print(f"📍 Папка сервера: {SERVER_DIR}")
        print()
        
        # Спрашиваем подтверждение
        print("⚠️  Это действие остановит сервер, обновит его и запустит снова.")
        print()
        answer = input("Продолжить? (y/n): ").strip().lower()
        if answer != 'y':
            print("❌ Отменено")
            return
        
        # 1. Останавливаем сервер
        stop_server()
        time.sleep(2)
        
        # 2. Обновляем с GitHub
        updated = update_from_git()
        
        # 3. Копируем новые моды (если есть)
        if updated:
            copy_mods_to_server()
        else:
            # Даже если нет обновлений, проверяем моды на всякий случай
            copy_mods_to_server()
        
        # 4. Запускаем сервер
        start_server()
        
        print("\n" + "=" * 55)
        print("✅ Сервер обновлён и запущен!")
        print("   Можешь закрыть это окно.")
        print("=" * 55)
        
        time.sleep(2)
        
    except KeyboardInterrupt:
        print("\n❌ Отменено")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        input("\nНажми Enter для выхода...")

if __name__ == "__main__":
    main()