#!/usr/bin/env python3
"""
Скрипт для сравнения версий локализации игры Drova
Сравнивает папки en1 (старая версия) и en2 (новая версия)
Генерирует markdown отчет с изменениями
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def parse_loc_file(file_path):
    """Парсит .loc файл и возвращает словарь с ключами и значениями с сохранением порядка"""
    entries = {}
    order = []  # Сохраняем порядок ключей
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Регулярное выражение для поиска записей типа "key { value }"
        pattern = r'(\w+)\s*\{\s*([^}]*)\s*\}'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        for key, value in matches:
            # Очищаем значение от лишних пробелов и переносов
            clean_value = value.strip()
            entries[key] = clean_value
            order.append(key)
    
    except Exception as e:
        print(f"Ошибка при чтении файла {file_path}: {e}")
    
    return entries, order

def get_all_loc_files(directory):
    """Получает все .loc файлы из директории"""
    loc_files = {}
    file_orders = {}
    directory_path = Path(directory)
    
    if not directory_path.exists():
        print(f"Папка {directory} не найдена!")
        return loc_files, file_orders
    
    for file_path in directory_path.rglob("*.loc"):
        # Используем относительный путь как ключ
        relative_path = file_path.relative_to(directory_path)
        entries, order = parse_loc_file(file_path)
        loc_files[str(relative_path)] = entries
        file_orders[str(relative_path)] = order
    
    return loc_files, file_orders

def compare_localization(en1_dir, en2_dir):
    """Сравнивает две версии локализации"""
    print("Загружаем файлы из en1...")
    old_files, old_orders = get_all_loc_files(en1_dir)
    
    print("Загружаем файлы из en2...")
    new_files, new_orders = get_all_loc_files(en2_dir)
    
    # Результаты сравнения
    results = {
        'new_files': {},      # Новые файлы
        'deleted_files': {},  # Удаленные файлы
        'modified_files': {}, # Измененные файлы
        'unchanged_files': []  # Неизмененные файлы
    }
    
    # Все уникальные файлы
    all_files = set(old_files.keys()) | set(new_files.keys())
    
    for file_name in sorted(all_files):
        old_entries = old_files.get(file_name, {})
        new_entries = new_files.get(file_name, {})
        
        if file_name not in old_files:
            # Новый файл
            results['new_files'][file_name] = new_entries
        elif file_name not in new_files:
            # Удаленный файл
            results['deleted_files'][file_name] = old_entries
        else:
            # Сравниваем содержимое
            old_order = old_orders.get(file_name, [])
            new_order = new_orders.get(file_name, [])
            changes = compare_file_entries(old_entries, new_entries, old_order, new_order)
            if changes['added'] or changes['modified'] or changes['deleted']:
                results['modified_files'][file_name] = changes
            else:
                results['unchanged_files'].append(file_name)
    
    return results

def compare_file_entries(old_entries, new_entries, old_order, new_order):
    """Сравнивает записи в двух версиях файла с сохранением порядка"""
    changes = {
        'added': [],     # Новые записи (список кортежей для сохранения порядка)
        'modified': [],  # Измененные записи
        'deleted': []    # Удаленные записи
    }
    
    # Добавленные записи (в порядке их появления в новом файле)
    for key in new_order:
        if key not in old_entries:
            changes['added'].append((key, new_entries[key]))
    
    # Удаленные записи (в порядке их появления в старом файле)
    for key in old_order:
        if key not in new_entries:
            changes['deleted'].append((key, old_entries[key]))
    
    # Измененные записи (в порядке их появления в новом файле)
    for key in new_order:
        if key in old_entries and old_entries[key] != new_entries[key]:
            changes['modified'].append((key, {
                'old': old_entries[key],
                'new': new_entries[key]
            }))
    
    return changes

def generate_markdown_report(results, output_file):
    """Генерирует markdown отчет"""
    
    total_new_entries = sum(len(entries) for entries in results['new_files'].values())
    total_modified_entries = sum(
        len(changes['added']) + len(changes['modified']) + len(changes['deleted'])
        for changes in results['modified_files'].values()
    )
    total_deleted_entries = sum(len(entries) for entries in results['deleted_files'].values())
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# Отчет сравнения локализации Drova\n\n")
        f.write(f"**Дата создания:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Краткая статистика
        f.write("## 📊 Краткая статистика\n\n")
        f.write("| Тип изменения | Количество |\n")
        f.write("|---------------|------------|\n")
        f.write(f"| 🆕 Новые файлы | {len(results['new_files'])} |\n")
        f.write(f"| ❌ Удаленные файлы | {len(results['deleted_files'])} |\n")
        f.write(f"| 📝 Измененные файлы | {len(results['modified_files'])} |\n")
        f.write(f"| ✅ Неизмененные файлы | {len(results['unchanged_files'])} |\n")
        f.write(f"| 🔤 Всего новых записей | {total_new_entries} |\n")
        f.write(f"| 🔄 Всего изменений в записях | {total_modified_entries} |\n")
        f.write(f"| 🗑️ Всего удаленных записей | {total_deleted_entries} |\n\n")
        
        # Новые файлы
        if results['new_files']:
            f.write("## 🆕 Новые файлы\n\n")
            for file_name, entries in sorted(results['new_files'].items()):
                f.write(f"### `{file_name}`\n\n")
                f.write(f"**Количество записей:** {len(entries)}\n\n")
                
                if entries:
                    f.write("| Ключ | Текст |\n")
                    f.write("|------|-------|\n")
                    for key, value in sorted(entries.items()):
                        # Экранируем спецсимволы для markdown
                        safe_value = value.replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_value} |\n")
                    f.write("\n")
        
        # Измененные файлы
        if results['modified_files']:
            f.write("## 📝 Измененные файлы\n\n")
            for file_name, changes in sorted(results['modified_files'].items()):
                f.write(f"### `{file_name}`\n\n")
                
                # Новые записи в файле
                if changes['added']:
                    f.write(f"#### ➕ Добавленные записи ({len(changes['added'])})\n\n")
                    f.write("| Ключ | Новый текст |\n")
                    f.write("|------|-------------|\n")
                    for key, value in changes['added']:
                        safe_value = value.replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_value} |\n")
                    f.write("\n")
                
                # Измененные записи
                if changes['modified']:
                    f.write(f"#### 🔄 Измененные записи ({len(changes['modified'])})\n\n")
                    f.write("| Ключ | Старый текст | Новый текст |\n")
                    f.write("|------|-------------|-------------|\n")
                    for key, change in changes['modified']:
                        safe_old = change['old'].replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        safe_new = change['new'].replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_old} | {safe_new} |\n")
                    f.write("\n")
                
                # Удаленные записи
                if changes['deleted']:
                    f.write(f"#### ➖ Удаленные записи ({len(changes['deleted'])})\n\n")
                    f.write("| Ключ | Удаленный текст |\n")
                    f.write("|------|----------------|\n")
                    for key, value in changes['deleted']:
                        safe_value = value.replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_value} |\n")
                    f.write("\n")
        
        # Удаленные файлы
        if results['deleted_files']:
            f.write("## ❌ Удаленные файлы\n\n")
            for file_name, entries in sorted(results['deleted_files'].items()):
                f.write(f"### `{file_name}`\n\n")
                f.write(f"**Количество записей:** {len(entries)}\n\n")
                
                if entries:
                    f.write("| Ключ | Текст |\n")
                    f.write("|------|-------|\n")
                    for key, value in sorted(entries.items()):
                        safe_value = value.replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_value} |\n")
                    f.write("\n")
        
        # Неизмененные файлы
        if results['unchanged_files']:
            f.write("## ✅ Неизмененные файлы\n\n")
            for file_name in sorted(results['unchanged_files']):
                f.write(f"- `{file_name}`\n")
            f.write("\n")

def main():
    """Основная функция"""
    print("🎮 Скрипт сравнения локализации Drova")
    print("=" * 50)
    
    # Проверяем наличие папок
    en1_dir = "en1"
    en2_dir = "en2"
    
    if not os.path.exists(en1_dir):
        print(f"❌ Папка {en1_dir} не найдена!")
        print(f"Создайте папку {en1_dir} и поместите туда старые .loc файлы")
        return
    
    if not os.path.exists(en2_dir):
        print(f"❌ Папка {en2_dir} не найдена!")
        print(f"Создайте папку {en2_dir} и поместите туда новые .loc файлы")
        return
    
    print(f"📁 Сравниваем:")
    print(f"   Старая версия: {en1_dir}/")
    print(f"   Новая версия:  {en2_dir}/")
    print()
    
    # Выполняем сравнение
    results = compare_localization(en1_dir, en2_dir)
    
    # Генерируем отчет
    output_file = "localization_diff_report.md"
    print(f"📝 Генерируем отчет: {output_file}")
    generate_markdown_report(results, output_file)
    
    print(f"✅ Готово! Отчет сохранен в {output_file}")
    print(f"📊 Найдено изменений:")
    print(f"   🆕 Новых файлов: {len(results['new_files'])}")
    print(f"   📝 Измененных файлов: {len(results['modified_files'])}")
    print(f"   ❌ Удаленных файлов: {len(results['deleted_files'])}")

if __name__ == "__main__":
    main() 