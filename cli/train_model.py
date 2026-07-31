# cli/train_model.py
import argparse
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent))

from utils.model_manager import ModelManager


def main():
    parser = argparse.ArgumentParser(description='Управление моделью прогнозирования времени')
    subparsers = parser.add_subparsers(dest='command', help='Команда')

    # Команда train
    train_parser = subparsers.add_parser('train', help='Обучить модель')

    # Команда stats
    stats_parser = subparsers.add_parser('stats', help='Показать статистику модели')

    # Команда evaluate
    eval_parser = subparsers.add_parser('evaluate', help='Оценить качество модели')

    # Команда export
    export_parser = subparsers.add_parser('export', help='Экспортировать данные')
    export_parser.add_argument('--output', '-o', default='data/export/training_data.json')

    # Команда import
    import_parser = subparsers.add_parser('import', help='Импортировать данные')
    import_parser.add_argument('file', help='Путь к файлу с данными')

    args = parser.parse_args()

    if args.command == 'train':
        result = ModelManager.train()
        print(f"✅ Модель обучена: {result}")

    elif args.command == 'stats':
        stats = ModelManager.get_stats()
        print("📊 Статистика модели:")
        for key, value in stats.items():
            print(f"  {key}: {value}")

    elif args.command == 'evaluate':
        result = ModelManager.evaluate()
        print("📊 Оценка модели:")
        for key, value in result.items():
            print(f"  {key}: {value}")

    elif args.command == 'export':
        count = ModelManager.export_data(args.output)
        print(f"✅ Экспортировано {count} записей в {args.output}")

    elif args.command == 'import':
        count = ModelManager.import_data(args.file)
        print(f"✅ Импортировано {count} записей из {args.file}")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()