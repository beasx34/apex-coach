# apex-coach

Тактический коуч-оверлей для Apex Legends в реальном времени. Захватывает экран,
читает HUD через OCR/CV, выдаёт короткие советы на русском:

- **Мгновенные** (детерминированные правила, <100 мс): «Хились!», «Перезарядка!», «Кольцо через 30 сек».
- **Стратегические** (Google Gemini 2.5 Flash, событийно): ротации, тайминги, тактика на текущую фазу.

## Принцип работы

```
Apex Legends → захват экрана (mss) → OCR/CV (OpenCV + RapidOCR)
            → GameState + EventBus
            ├── RulesEngine ──► мгновенные советы ──┐
            └── AiCoach (Gemini Flash) ──────────────┤
                                                     ▼
                          Прозрачное всегда-сверху окно (PySide6)
```

Никаких инъекций в процесс игры, никаких чтений памяти, никаких DLL —
только захват экрана и поверх-окно. Тот же класс инструмента, что Discord-оверлей или OBS.

## Установка

Требования: **Windows 10/11**, Python 3.11+. На Linux собирается и тестируется,
но реальный геймплей-оверлей предназначен для Windows.

```powershell
git clone https://github.com/your-org/apex-coach.git
cd apex-coach
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .
```

## Настройка

1. Получи бесплатный API-ключ Google Gemini в [Google AI Studio](https://aistudio.google.com/apikey).
2. Сохрани его в переменной окружения:

```powershell
$env:GEMINI_API_KEY = "<твой ключ>"
```

Или создай файл `.env` в корне репозитория с одной строкой:

```
GEMINI_API_KEY=...
```

3. Запусти:

```powershell
apex-coach
```

В дефолте используется пресет HUD для 1920×1080. Для 1440p/4K измени в конфиге
(см. ниже).

## Конфиг

Создай `~/.config/apex-coach/config.toml` (или `%APPDATA%\apex-coach\config.toml` на Windows):

```toml
[capture]
monitor = 1              # номер монитора (1 — основной)
target_fps = 10.0

[layout]
preset = "1080p"         # 1080p | 1440p | 4k
# для тонкой подстройки — секции [layout.regions.<имя>] с x,y,w,h в долях экрана

[ai]
model = "gemini-2.5-flash"
min_interval_s = 8.0     # не чаще 1 совета в N секунд (free tier ~15 RPM)
language = "ru"

[overlay]
opacity = 0.85
position = "bottom-left" # bottom-left | bottom-right | top-left | top-right
tip_ttl_s = 6.0

[hotkeys]
ai_request = "<alt>+`"
toggle     = "<alt>+\\"
calibrate  = "<alt>+<shift>+c"
```

## Хоткеи

| Сочетание | Действие |
|---|---|
| `Alt`+`` ` `` | Запросить совет от AI прямо сейчас |
| `Alt`+`\` | Скрыть / показать оверлей |
| `Alt`+`Shift`+`C` | Запустить мастер калибровки HUD |

## Поддержка нового сезона

Apex обновляется ~раз в патч. Чтобы советы оставались актуальными:

1. **`resources/meta_ru.md`** — обновляй мету (топ-оружие, ребалансы, новые легенды). Файл целиком попадает в системный промпт Gemini.
2. **`apex_coach/tactics/knowledge.py`** — добавь новую легенду в `LEGEND_KB` (имя, КД способностей, тип роли).
3. Если HUD редизайнен — обнови координаты в `apex_coach/config/regions.py` (или перекалибруй через `Alt+Shift+C`).

## Антицит и Fair Play

`apex-coach` **не инжектится в процесс игры**, **не читает память**,
**не модифицирует файлы игры**. Используется только публичный API ОС
(захват экрана и оверлей-окно) — те же механизмы, что у Discord, OBS,
NVIDIA Highlights.

Это допустимая категория софта по EA TOS, однако EA оставляет за собой
право интерпретации. Используй на свой риск. **Не рекомендуется** запускать
в ранкеде/турнирах — это инструмент для тренировки и обучения.

## Разработка

```bash
pip install -e ".[dev]"
ruff check .
ruff format --check .
mypy apex_coach
pytest -q
```

CI запускает то же самое на Linux (Ubuntu 22.04, Python 3.12).
Юнит-тесты используют синтетические скриншоты — игра не нужна.

## Лицензия

MIT.
