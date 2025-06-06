#!/bin/bash

# Включаем детальное отслеживание asyncio
export PYTHONASYNCIODEBUG=1

# Включаем предупреждения Python
export PYTHONWARNINGS=default

# Включаем отображение всех предупреждений
export PYTHONDONTWRITEBYTECODE=1

echo "🚀 Запуск бота с полным логированием..."
echo "📊 Включены: tracemalloc, asyncio debug, warnings"

python run.py