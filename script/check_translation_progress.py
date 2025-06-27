#!/usr/bin/env python3
"""
Скрипт для проверки прогресса перевода игры Drova
Сравнивает папки en/ (оригинал) и ru/ (перевод)
Находит непереведенные файлы и строки
Генерирует markdown отчет с детализацией по переводу
"""

import os
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime

def has_cyrillic(text):
    """Проверяет, содержит ли текст кириллические символы"""
    return bool(re.search('[а-яё]', text.lower()))

def is_technical_untranslatable(en_text, ru_text):
    """Проверяет, является ли строка технической и не требующей перевода"""
    en_clean = en_text.strip()
    ru_clean = ru_text.strip()
    
    # Пустые строки в английском
    if not en_clean:
        return True
    
    # Клавиши клавиатуры
    keyboard_keys = {
        'shift', 'ctrl', 'alt', 'tab', 'enter', 'return', 'space', 'escape', 'esc',
        'lctrl', 'rctrl', 'lalt', 'ralt', 'lshift', 'rshift', 'control',
        'leftcontrol', 'rightcontrol', 'leftalt', 'rightalt', 'leftshift', 'rightshift'
    }
    if en_clean.lower() in keyboard_keys:
        return True
    
    # Названия компаний и брендов
    company_names = {
        'deck13', 'deck13 spotlight', 'bxdxo', 'unity', 'nvidia', 'amd'
    }
    if en_clean.lower() in company_names:
        return True
    
    # Debug строки
    if 'debug' in en_clean.lower() and '/ignore' in en_clean.lower():
        return True
    
    # Технические ID строки
    if en_clean.startswith('Id: ') and ru_clean.startswith('Id: '):
        return True
    
    # Placeholder строки
    placeholders = {'...', '???', '-', 'n/a', 'tbd', 'todo'}
    if en_clean.lower() in placeholders and ru_clean.lower() in placeholders:
        return True
    
    # Технические переменные игрового движка
    if 'G V A R :' in en_clean and 'G V A R :' in ru_clean:
        return True
    
    # Строки вида "recipe_name_description" когда они одинаковые
    if en_clean == ru_clean and ('_description' in en_clean or '_name' in en_clean):
        return True
    
    return False

def is_likely_translated(ru_text, en_text):
    """Определяет, переведен ли текст на основе различных критериев"""
    if not ru_text or not en_text:
        return False
    
    # Проверяем, не является ли это технической строкой
    if is_technical_untranslatable(en_text, ru_text):
        return True  # Считаем техническую строку "переведенной" (не требует перевода)
    
    # Если тексты идентичны, то не переведено
    if ru_text.strip().lower() == en_text.strip().lower():
        return False
    
    # Если в русском тексте есть кириллица, вероятно переведено
    if has_cyrillic(ru_text):
        return True
    
    # Если нет кириллицы, но тексты разные, может быть частичный перевод
    # Проверим, не является ли это просто пустой строкой или placeholder'ом
    ru_clean = ru_text.strip()
    if not ru_clean or ru_clean in ['', '...', '-', 'TODO', 'TBD']:
        return False
    
    return False

def parse_loc_file(file_path):
    """Парсит .loc файл и возвращает словарь с ключами и значениями с сохранением порядка"""
    entries = {}
    order = []  # Сохраняем порядок ключей
    
    # Список кодировок для попытки чтения
    encodings = ['utf-8', 'windows-1251', 'cp1252', 'iso-8859-1']
    
    content = None
    used_encoding = None
    
    # Пытаемся открыть файл с разными кодировками
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
            used_encoding = encoding
            break
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"Ошибка при чтении файла {file_path}: {e}")
            return entries, order
    
    if content is None:
        print(f"Не удалось прочитать файл {file_path} ни с одной из кодировок: {encodings}")
        return entries, order
    
    # Если файл был прочитан не в UTF-8, показываем предупреждение
    if used_encoding != 'utf-8':
        print(f"⚠️  Файл {file_path} прочитан в кодировке {used_encoding} (рекомендуется UTF-8)")
    
    try:
        # Регулярное выражение для поиска записей типа "key { value }"
        pattern = r'(\w+)\s*\{\s*([^}]*)\s*\}'
        matches = re.findall(pattern, content, re.MULTILINE | re.DOTALL)
        
        for key, value in matches:
            # Очищаем значение от лишних пробелов и переносов
            clean_value = value.strip()
            entries[key] = clean_value
            order.append(key)
    
    except Exception as e:
        print(f"Ошибка при парсинге файла {file_path}: {e}")
    
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

def get_russian_file_path(en_file_path):
    """Преобразует путь английского файла в путь русского файла"""
    # Заменяем _en.loc на _ru.loc
    return en_file_path.replace('_en.loc', '_ru.loc')

def analyze_translation_progress(en_dir, ru_dir):
    """Анализирует прогресс перевода между английской и русской версиями"""
    print("Загружаем английские файлы...")
    en_files, en_orders = get_all_loc_files(en_dir)
    
    print("Загружаем русские файлы...")
    ru_files, ru_orders = get_all_loc_files(ru_dir)
    
    # Результаты анализа
    results = {
        'missing_files': {},           # Отсутствующие файлы
        'files_progress': {},          # Прогресс по каждому файлу
        'untranslated_entries': {},    # Непереведенные записи по файлам
        'total_stats': {
            'total_files': len(en_files),
            'translated_files': 0,
            'total_entries': 0,
            'translated_entries': 0,
            'untranslated_entries': 0,
            'missing_entries': 0
        }
    }
    
    for en_file_name in sorted(en_files.keys()):
        en_entries = en_files[en_file_name]
        
        # Получаем соответствующий русский файл
        ru_file_name = get_russian_file_path(en_file_name)
        ru_entries = ru_files.get(ru_file_name, {})
        
        results['total_stats']['total_entries'] += len(en_entries)
        
        if ru_file_name not in ru_files:
            # Файл полностью отсутствует
            results['missing_files'][en_file_name] = en_entries
            results['total_stats']['untranslated_entries'] += len(en_entries)
            continue
        
        # Анализируем файл
        file_analysis = analyze_file_translation(en_entries, ru_entries, en_orders.get(en_file_name, []))
        results['files_progress'][en_file_name] = file_analysis
        
        if file_analysis['untranslated'] or file_analysis['missing']:
            results['untranslated_entries'][en_file_name] = {
                'missing': file_analysis['missing'],
                'untranslated': file_analysis['untranslated']
            }
        
        # Обновляем статистику
        results['total_stats']['translated_entries'] += file_analysis['translated_count']
        results['total_stats']['untranslated_entries'] += file_analysis['untranslated_count']
        results['total_stats']['missing_entries'] += file_analysis['missing_count']
        
        if file_analysis['progress_percent'] > 0:
            results['total_stats']['translated_files'] += 1
    
    return results

def analyze_file_translation(en_entries, ru_entries, en_order):
    """Анализирует перевод одного файла"""
    analysis = {
        'total_count': len(en_entries),
        'translated_count': 0,
        'untranslated_count': 0,
        'missing_count': 0,
        'progress_percent': 0,
        'missing': [],           # Отсутствующие ключи
        'untranslated': [],      # Непереведенные записи
        'translated': []         # Переведенные записи
    }
    
    for key in en_order:
        en_text = en_entries[key]
        ru_text = ru_entries.get(key, '')
        
        if not ru_text:
            # Ключ отсутствует в русском файле
            analysis['missing'].append((key, en_text))
            analysis['missing_count'] += 1
        elif is_likely_translated(ru_text, en_text):
            # Вероятно переведено
            analysis['translated'].append((key, {'en': en_text, 'ru': ru_text}))
            analysis['translated_count'] += 1
        else:
            # Не переведено или переведено некорректно
            analysis['untranslated'].append((key, {'en': en_text, 'ru': ru_text}))
            analysis['untranslated_count'] += 1
    
    # Вычисляем процент перевода
    if analysis['total_count'] > 0:
        analysis['progress_percent'] = round(
            (analysis['translated_count'] / analysis['total_count']) * 100, 1
        )
    
    return analysis

def generate_translation_report(results, output_file):
    """Генерирует markdown отчет о прогрессе перевода"""
    stats = results['total_stats']
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(f"# 🇷🇺 Отчет о прогрессе перевода Drova\n\n")
        f.write(f"**Дата создания:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        # Общая статистика
        f.write("## 📊 Общая статистика\n\n")
        
        total_progress = 0
        if stats['total_entries'] > 0:
            total_progress = round((stats['translated_entries'] / stats['total_entries']) * 100, 1)
        
        f.write("| Метрика | Значение |\n")
        f.write("|---------|----------|\n")
        f.write(f"| 📁 Всего файлов | {stats['total_files']} |\n")
        f.write(f"| ✅ Файлов с переводом | {stats['translated_files']} |\n")
        f.write(f"| ❌ Файлов без перевода | {len(results['missing_files'])} |\n")
        f.write(f"| 🔤 Всего строк | {stats['total_entries']} |\n")
        f.write(f"| ✅ Переведено строк | {stats['translated_entries']} |\n")
        f.write(f"| ❌ Не переведено | {stats['untranslated_entries']} |\n")
        f.write(f"| ❓ Отсутствующих строк | {stats['missing_entries']} |\n")
        f.write(f"| 📈 **Общий прогресс** | **{total_progress}%** |\n\n")
        
        # Прогресс-бар
        progress_bar_length = 20
        filled_length = int(progress_bar_length * total_progress / 100)
        bar = '█' * filled_length + '░' * (progress_bar_length - filled_length)
        f.write(f"### 📊 Визуальный прогресс\n")
        f.write(f"```\n{bar} {total_progress}%\n```\n\n")
        
        # Отсутствующие файлы
        if results['missing_files']:
            f.write("## ❌ Полностью отсутствующие файлы\n\n")
            f.write("*Эти файлы нужно создать и перевести полностью*\n\n")
            for file_name, entries in sorted(results['missing_files'].items()):
                f.write(f"### `{file_name}`\n")
                f.write(f"**Строк для перевода:** {len(entries)}\n\n")
        
        # Прогресс по файлам
        if results['files_progress']:
            f.write("## 📈 Прогресс по файлам\n\n")
            
            # Сортируем по проценту выполнения
            sorted_files = sorted(
                results['files_progress'].items(),
                key=lambda x: x[1]['progress_percent']
            )
            
            f.write("| Файл | Прогресс | Переведено | Не переведено | Отсутствует |\n")
            f.write("|------|----------|------------|---------------|-------------|\n")
            
            for file_name, progress in sorted_files:
                percent = progress['progress_percent']
                status_emoji = "✅" if percent == 100 else "🔄" if percent > 0 else "❌"
                
                f.write(f"| {status_emoji} `{file_name}` | {percent}% | {progress['translated_count']} | {progress['untranslated_count']} | {progress['missing_count']} |\n")
            
            f.write("\n")
        
        # Детали по непереведенным файлам
        if results['untranslated_entries']:
            f.write("## 🔍 Детали по непереведенным строкам\n\n")
            f.write("*Файлы отсортированы по количеству непереведенных строк*\n\n")
            
            # Сортируем по количеству непереведенных строк
            sorted_untranslated = sorted(
                results['untranslated_entries'].items(),
                key=lambda x: len(x[1]['missing']) + len(x[1]['untranslated']),
                reverse=True
            )
            
            for file_name, issues in sorted_untranslated:
                total_issues = len(issues['missing']) + len(issues['untranslated'])
                f.write(f"### `{file_name}` ({total_issues} проблем)\n\n")
                
                # Отсутствующие ключи
                if issues['missing']:
                    f.write(f"#### ❓ Отсутствующие ключи ({len(issues['missing'])})\n\n")
                    f.write("| Ключ | Английский текст |\n")
                    f.write("|------|------------------|\n")
                    for key, en_text in issues['missing']:  # Показываем все
                        safe_text = en_text.replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_text} |\n")
                    f.write("\n")
                
                # Непереведенные строки
                if issues['untranslated']:
                    f.write(f"#### ❌ Непереведенные строки ({len(issues['untranslated'])})\n\n")
                    f.write("| Ключ | Английский | Русский (проблема) |\n")
                    f.write("|------|------------|--------------------|\n")
                    for key, texts in issues['untranslated']:  # Показываем все
                        safe_en = texts['en'].replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        safe_ru = texts['ru'].replace('|', '\\|').replace('\n', '<br>').replace('*', '\\*')
                        f.write(f"| `{key}` | {safe_en} | {safe_ru} |\n")
                    f.write("\n")

def main():
    """Основная функция"""
    print("🇷🇺 Скрипт проверки прогресса перевода Drova")
    print("=" * 50)
    
    # Проверяем наличие папок
    en_dir = "en"
    ru_dir = "ru"
    
    if not os.path.exists(en_dir):
        print(f"❌ Папка {en_dir} не найдена!")
        print(f"Убедитесь, что папка {en_dir} содержит оригинальные английские .loc файлы")
        return
    
    if not os.path.exists(ru_dir):
        print(f"❌ Папка {ru_dir} не найдена!")
        print(f"Убедитесь, что папка {ru_dir} содержит русские .loc файлы")
        return
    
    print(f"📁 Анализируем:")
    print(f"   Оригинал: {en_dir}/")
    print(f"   Перевод:  {ru_dir}/")
    print()
    
    # Выполняем анализ
    results = analyze_translation_progress(en_dir, ru_dir)
    
    # Генерируем отчет
    output_file = "translation_progress_report.md"
    print(f"📝 Генерируем отчет: {output_file}")
    generate_translation_report(results, output_file)
    
    stats = results['total_stats']
    total_progress = 0
    if stats['total_entries'] > 0:
        total_progress = round((stats['translated_entries'] / stats['total_entries']) * 100, 1)
    
    print(f"✅ Готово! Отчет сохранен в {output_file}")
    print(f"📊 Статистика перевода:")
    print(f"   📁 Файлов: {stats['translated_files']}/{stats['total_files']}")
    print(f"   🔤 Строк переведено: {stats['translated_entries']}/{stats['total_entries']} ({total_progress}%)")
    print(f"   ❌ Требует внимания: {stats['untranslated_entries'] + stats['missing_entries']} строк")

if __name__ == "__main__":
    main() 